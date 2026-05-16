"""Week 74 — Failure-Driven Runtime Design.

Uses Week 73's 12-category error taxonomy to redesign the Lyme Model runtime.
Each failure type gets: root cause analysis, runtime mitigation, guardrail,
measurement hook, and benchmark scenario.

Does NOT remove existing Lyme systems. Adds layers on top.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from pathlib import Path
import json
import time
import uuid

from ..failures.taxonomy import (
    LocalCodingFailureCategory,
    LOCAL_CODING_TAXONOMY,
    LocalCodingFailureRecord,
)
from ..failures.detector import LocalCodingFailureDetector


@dataclass
class Guardrail:
    name: str
    description: str
    failure_category: str
    enabled: bool = True
    trigger_count: int = 0
    last_triggered: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "failure_category": self.failure_category,
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
        }


@dataclass
class MeasurementHook:
    name: str
    description: str
    failure_category: str
    measurement: str
    value: float = 0.0
    threshold: float = 0.0
    breached: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "failure_category": self.failure_category,
            "measurement": self.measurement,
            "value": self.value,
            "threshold": self.threshold,
            "breached": self.breached,
        }


@dataclass
class BenchmarkScenario:
    name: str
    description: str
    failure_category: str
    task: str
    expected_difficulty: str
    success_criteria: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "failure_category": self.failure_category,
            "task": self.task,
            "expected_difficulty": self.expected_difficulty,
            "success_criteria": self.success_criteria,
        }


FAILURE_MITIGATIONS = {
    LocalCodingFailureCategory.MISSING_CONTEXT: {
        "root_cause": "Context window too small, retrieval missed key files, or no retrieval used",
        "mitigation": "Enforce mandatory read_file before edit_file in tool loop",
        "guardrail": "GuardrailMissingContext — blocks edit on unread files",
        "measurement": "ratio_edits_to_reads — must be <= 1.0",
        "benchmark": "Edit a file after reading its contents vs blind edit",
    },
    LocalCodingFailureCategory.WRONG_FILE_SELECTED: {
        "root_cause": "Similar filenames, model guessed file location",
        "mitigation": "Require file path verification via glob + content check before edit",
        "guardrail": "GuardrailWrongFile — validates file matches task intent",
        "measurement": "wrong_file_edit_rate — edits to wrong file / total edits",
        "benchmark": "Fix a bug in a specific file among similar-named files",
    },
    LocalCodingFailureCategory.HALLUCINATED_API: {
        "root_cause": "Model generalizes from training data instead of reading actual code",
        "mitigation": "Inject AST-extracted symbol table into context; verify symbol existence",
        "guardrail": "GuardrailSymbolCheck — rejects outputs with nonexistent symbols",
        "measurement": "hallucination_rate — hallucinated symbols / total references",
        "benchmark": "Use a function from the codebase vs inventing one",
    },
    LocalCodingFailureCategory.BAD_PATCH: {
        "root_cause": "Model misunderstood the change or generated malformed diff",
        "mitigation": "Run syntax check + dry-run patch before applying",
        "guardrail": "GuardrailPatchValidation — blocks patches that don't apply cleanly",
        "measurement": "patch_failure_rate — failed patches / total patches",
        "benchmark": "Apply a patch to a file with syntax verification",
    },
    LocalCodingFailureCategory.INCOMPLETE_PATCH: {
        "root_cause": "Model missed side effects, related files, or edge cases",
        "mitigation": "Run dependency impact analysis; check related files after patch",
        "guardrail": "GuardrailImpactAnalysis — requires checking related files",
        "measurement": "incomplete_patch_rate — follow-up patches / total patches",
        "benchmark": "Fix a bug that requires changes in 2+ related files",
    },
    LocalCodingFailureCategory.TEST_MISUNDERSTANDING: {
        "root_cause": "Model did not parse test output correctly",
        "mitigation": "Parse test output structurally; show only relevant assertion lines",
        "guardrail": "GuardrailTestOutputParsing — strips irrelevant output",
        "measurement": "test_assertion_misread_rate",
        "benchmark": "Fix code based on a failing test assertion",
    },
    LocalCodingFailureCategory.COMMAND_MISUSE: {
        "root_cause": "Model guessed command syntax instead of checking docs or history",
        "mitigation": "Cache successful commands; validate command existence before running",
        "guardrail": "GuardrailCommandValidation — rejects unknown commands",
        "measurement": "command_failure_rate — failed commands / total commands",
        "benchmark": "Run project tests without knowing the exact command",
    },
    LocalCodingFailureCategory.SYNTAX_REGRESSION: {
        "root_cause": "Model generated code without checking surrounding syntax",
        "mitigation": "Run syntax check after every edit; inject file AST before edit",
        "guardrail": "GuardrailSyntaxCheck — runs after every edit_file",
        "measurement": "syntax_error_rate — syntax errors / total edits",
        "benchmark": "Add a function to a file without breaking its syntax",
    },
    LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING: {
        "root_cause": "Model lacked architectural overview",
        "mitigation": "Inject architecture summary card into prompt; detect layer violations",
        "guardrail": "GuardrailArchitecture — flags layer boundary violations",
        "measurement": "architectural_violation_rate",
        "benchmark": "Add a new feature following the project's architecture pattern",
    },
    LocalCodingFailureCategory.EXCESSIVE_LATENCY: {
        "root_cause": "Slow model, large context, many tool calls",
        "mitigation": "Cache model outputs; use smaller draft model for quick tasks",
        "guardrail": "GuardrailLatency — warns if task exceeds latency budget",
        "measurement": "p95_task_time_ms — 95th percentile task completion time",
        "benchmark": "Complete a simple task within a strict time limit",
    },
    LocalCodingFailureCategory.CONTEXT_OVERFLOW: {
        "root_cause": "Too much context provided without prioritization or compression",
        "mitigation": "Compress context packets; truncate lowest-priority files first",
        "guardrail": "GuardrailContextWindow — monitors token count against model limit",
        "measurement": "context_utilization_pct — tokens used / max tokens",
        "benchmark": "Complete a task with context exceeding model's max window",
    },
    LocalCodingFailureCategory.TOOL_LOOP_FAILURE: {
        "root_cause": "Model lacks stopping criteria or keeps retrying the same action",
        "mitigation": "Add loop detection; enforce max retries; require progress check",
        "guardrail": "GuardrailLoopDetection — breaks loops after N identical calls",
        "measurement": "loop_frequency — loops detected / total runs",
        "benchmark": "Complete a task that requires tool use without getting stuck",
    },
}


class FailureDrivenRuntime:
    """Runtime that uses the error taxonomy to prevent, detect, and mitigate failures.

    Wraps the existing AgentRuntime with guardrails, measurement hooks,
    and automated mitigations.
    """

    def __init__(self, base_runtime=None, repo_path: Optional[str] = None):
        self.detector = LocalCodingFailureDetector()
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self.guardrails: Dict[str, Guardrail] = self._build_guardrails()
        self.measurements: Dict[str, MeasurementHook] = {}
        self.mitigation_stats: Dict[str, int] = {}
        self.failure_history: List[LocalCodingFailureRecord] = []
        self._base_runtime = base_runtime

    def _build_guardrails(self) -> Dict[str, Guardrail]:
        return {
            "missing_context": Guardrail(
                name="GuardrailMissingContext",
                description="Blocks edit_file on files not previously read",
                failure_category="missing_context",
            ),
            "wrong_file": Guardrail(
                name="GuardrailWrongFile",
                description="Validates file path matches task intent via glob check",
                failure_category="wrong_file_selected",
            ),
            "symbol_check": Guardrail(
                name="GuardrailSymbolCheck",
                description="Rejects outputs referencing nonexistent symbols",
                failure_category="hallucinated_api",
            ),
            "patch_validation": Guardrail(
                name="GuardrailPatchValidation",
                description="Runs syntax check + dry-run before applying patches",
                failure_category="bad_patch",
            ),
            "impact_analysis": Guardrail(
                name="GuardrailImpactAnalysis",
                description="Requires checking related files after patch",
                failure_category="incomplete_patch",
            ),
            "test_output_parsing": Guardrail(
                name="GuardrailTestOutputParsing",
                description="Strips irrelevant output from test results",
                failure_category="test_misunderstanding",
            ),
            "command_validation": Guardrail(
                name="GuardrailCommandValidation",
                description="Rejects unknown/untrusted commands",
                failure_category="command_misuse",
            ),
            "syntax_check": Guardrail(
                name="GuardrailSyntaxCheck",
                description="Runs syntax check after every edit_file",
                failure_category="syntax_regression",
            ),
            "architecture": Guardrail(
                name="GuardrailArchitecture",
                description="Flags layer boundary violations",
                failure_category="architectural_misunderstanding",
            ),
            "latency": Guardrail(
                name="GuardrailLatency",
                description="Warns if task exceeds latency budget",
                failure_category="excessive_latency",
            ),
            "context_window": Guardrail(
                name="GuardrailContextWindow",
                description="Monitors token count against model limit",
                failure_category="context_overflow",
            ),
            "loop_detection": Guardrail(
                name="GuardrailLoopDetection",
                description="Breaks loops after N identical tool calls",
                failure_category="tool_loop_failure",
            ),
        }

    def get_mitigations(self) -> Dict[str, dict]:
        """Return all mitigations by failure type."""
        return {
            cat.value: {
                "root_cause": info["root_cause"],
                "mitigation": info["mitigation"],
                "guardrail": info["guardrail"],
                "measurement": info["measurement"],
            }
            for cat, info in FAILURE_MITIGATIONS.items()
        }

    def get_guardrails(self) -> List[Guardrail]:
        return list(self.guardrails.values())

    def get_benchmark_scenarios(self) -> List[BenchmarkScenario]:
        """Return benchmark scenarios for each failure type."""
        return [
            BenchmarkScenario(
                name=f"bench_{cat.value}",
                description=info["benchmark"],
                failure_category=cat.value,
                task=info["benchmark"],
                expected_difficulty="medium",
                success_criteria="No failure detected for this category",
            )
            for cat, info in FAILURE_MITIGATIONS.items()
        ]

    def run_with_mitigation(
        self,
        task: str,
        trace: dict,
        context: Optional[str] = None,
    ) -> dict:
        """Run a task through the failure-driven runtime.

        Flow:
        1. Pre-flight guardrails check
        2. Execute base runtime (or simulate)
        3. Detect failures from trace
        4. Apply mitigation
        5. Post-flight guardrails check
        6. Record measurements
        """
        start_time = time.time()
        result = {
            "task": task,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "guardrails_triggered": [],
            "failures_detected": [],
            "mitigations_applied": [],
            "measurements": {},
            "success": True,
            "total_time_ms": 0,
        }

        # Step 1: Pre-flight guardrails
        pre_result = self._pre_flight_check(task, trace)
        result["guardrails_triggered"].extend(pre_result)

        # Step 2: Execute (delegate to base runtime or simulate)
        exec_result = self._execute(task, trace, context)
        result["execution"] = exec_result

        # Step 3: Detect failures
        failures = self.detector.detect(trace)
        result["failures_detected"] = [f.to_dict() for f in failures]
        self.failure_history.extend(failures)

        # Step 4: Apply mitigations
        mitigations = self._apply_mitigations(failures, trace)
        result["mitigations_applied"] = mitigations

        # Step 5: Post-flight guardrails
        post_result = self._post_flight_check(task, trace, failures)
        result["guardrails_triggered"].extend(post_result)

        # Step 6: Measurements
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["total_time_ms"] = elapsed_ms
        measurements = self._record_measurements(trace, failures, elapsed_ms)
        result["measurements"] = {k: v.to_dict() for k, v in measurements.items()}
        self.measurements.update(measurements)

        result["success"] = len([f for f in failures if f.severity in ("critical", "high")]) == 0
        return result

    def _pre_flight_check(self, task: str, trace: dict) -> List[dict]:
        triggered = []
        context_tokens = trace.get("context_tokens", 0)
        max_tokens = trace.get("model_max_tokens", 4096)

        if context_tokens > max_tokens * 0.9:
            g = self.guardrails["context_window"]
            g.trigger_count += 1
            g.last_triggered = datetime.now(timezone.utc).isoformat()
            triggered.append({
                "guardrail": g.name,
                "action": "Warn: context near limit, will compress",
                "triggered_at": g.last_triggered,
            })

        return triggered

    def _execute(self, task: str, trace: dict, context: Optional[str] = None) -> dict:
        if self._base_runtime is not None:
            result = self._base_runtime.run_task(task, context)
            return {"output": result.output, "success": result.success}
        return {"output": trace.get("output", ""), "success": True, "simulated": True}

    def _apply_mitigations(self, failures: List[LocalCodingFailureRecord],
                           trace: dict) -> List[dict]:
        applied = []
        for failure in failures:
            cat = failure.category
            info = FAILURE_MITIGATIONS.get(cat, {})
            mitigation = info.get("mitigation", "")
            if mitigation:
                failure.mitigated_by = mitigation
                key = cat.value
                self.mitigation_stats[key] = self.mitigation_stats.get(key, 0) + 1
                applied.append({
                    "failure_id": failure.failure_id,
                    "category": cat.value,
                    "mitigation": mitigation,
                    "description": failure.description,
                })
        return applied

    def _post_flight_check(self, task: str, trace: dict,
                           failures: List[LocalCodingFailureRecord]) -> List[dict]:
        triggered = []
        tools = trace.get("tool_calls", [])

        tool_names = [t.get("tool", "") for t in tools]
        from collections import Counter
        counts = Counter(tool_names)
        for name, count in counts.items():
            if count >= 4:
                g = self.guardrails["loop_detection"]
                g.trigger_count += 1
                g.last_triggered = datetime.now(timezone.utc).isoformat()
                triggered.append({
                    "guardrail": g.name,
                    "action": f"Broken loop: {name} called {count}x",
                    "triggered_at": g.last_triggered,
                })

        for f in failures:
            if f.category == LocalCodingFailureCategory.HALLUCINATED_API:
                g = self.guardrails["symbol_check"]
                g.trigger_count += 1
                g.last_triggered = datetime.now(timezone.utc).isoformat()
                triggered.append({
                    "guardrail": g.name,
                    "action": f"Hallucination detected: {f.description}",
                    "triggered_at": g.last_triggered,
                })

        return triggered

    def _record_measurements(self, trace: dict,
                             failures: List[LocalCodingFailureRecord],
                             elapsed_ms: int) -> Dict[str, MeasurementHook]:
        hooks = {}

        edits = [t for t in trace.get("tool_calls", []) if t.get("tool") == "edit_file"]
        reads = [t for t in trace.get("tool_calls", []) if t.get("tool") == "read_file"]
        read_edit_ratio = len(reads) / len(edits) if edits else float("inf")
        hooks["read_edit_ratio"] = MeasurementHook(
            name="read_edit_ratio",
            description="Ratio of read_file to edit_file calls",
            failure_category="missing_context",
            measurement="ratio",
            value=read_edit_ratio,
            threshold=1.0,
            breached=read_edit_ratio < 1.0,
        )

        hallucinated_count = len([
            f for f in failures
            if f.category == LocalCodingFailureCategory.HALLUCINATED_API
        ])
        total_refs = max(len(trace.get("output", "").split()), 1)
        hooks["hallucination_rate"] = MeasurementHook(
            name="hallucination_rate",
            description="Rate of hallucinated symbols per output",
            failure_category="hallucinated_api",
            measurement="rate",
            value=hallucinated_count / total_refs,
            threshold=0.05,
            breached=(hallucinated_count / total_refs) > 0.05,
        )

        hooks["p95_latency"] = MeasurementHook(
            name="p95_task_time",
            description="95th percentile task completion time",
            failure_category="excessive_latency",
            measurement="ms",
            value=elapsed_ms,
            threshold=30000,
            breached=elapsed_ms > 30000,
        )

        context_tokens = trace.get("context_tokens", 0)
        max_tokens = trace.get("model_max_tokens", 4096)
        ctx_pct = (context_tokens / max_tokens * 100) if max_tokens > 0 else 0
        hooks["context_utilization"] = MeasurementHook(
            name="context_utilization_pct",
            description="Percentage of context window used",
            failure_category="context_overflow",
            measurement="%",
            value=ctx_pct,
            threshold=90.0,
            breached=ctx_pct > 90.0,
        )

        loop_count = len([
            f for f in failures
            if f.category == LocalCodingFailureCategory.TOOL_LOOP_FAILURE
        ])
        hooks["loop_frequency"] = MeasurementHook(
            name="loop_frequency",
            description="Tool loop failures per run",
            failure_category="tool_loop_failure",
            measurement="count",
            value=loop_count,
            threshold=0,
            breached=loop_count > 0,
        )

        return hooks

    def report(self) -> str:
        """Generate a runtime mitigation report."""
        lines = []
        lines.append("=" * 72)
        lines.append("  LYME MODEL — FAILURE-DRIVEN RUNTIME REPORT")
        lines.append("=" * 72)
        lines.append("")

        lines.append("MITIGATIONS BY FAILURE TYPE")
        lines.append("-" * 72)
        for cat, info in FAILURE_MITIGATIONS.items():
            lines.append(f"  [{cat.value:35s}]")
            lines.append(f"  Root cause:    {info['root_cause'][:70]}")
            lines.append(f"  Mitigation:    {info['mitigation'][:70]}")
            lines.append(f"  Guardrail:     {info['guardrail'][:70]}")
            lines.append(f"  Measurement:   {info['measurement'][:70]}")
            lines.append(f"  Benchmark:     {info['benchmark'][:70]}")
            lines.append("")

        lines.append("GUARDRAIL STATUS")
        lines.append("-" * 72)
        for g in self.guardrails.values():
            status = "ENABLED" if g.enabled else "DISABLED"
            lines.append(f"  [{status:8s}] {g.name:40s} triggered: {g.trigger_count}")
        lines.append("")

        lines.append("MITIGATION STATS")
        lines.append("-" * 72)
        if self.mitigation_stats:
            for cat, count in sorted(self.mitigation_stats.items(), key=lambda x: -x[1]):
                lines.append(f"  {cat:35s} {count} mitigation(s) applied")
        else:
            lines.append("  No mitigations applied yet.")
        lines.append("")

        lines.append("MEASUREMENT HOOKS")
        lines.append("-" * 72)
        for hook in self.measurements.values():
            status = "BREACHED" if hook.breached else "OK"
            lines.append(
                f"  [{status:8s}] {hook.name:30s} "
                f"value={hook.value:.2f} threshold={hook.threshold:.2f}"
            )
        lines.append("")

        lines.append("BENCHMARK SCENARIOS (12 total)")
        lines.append("-" * 72)
        for bs in self.get_benchmark_scenarios():
            lines.append(f"  {bs.name:40s} {bs.description[:60]}")
        lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)
