"""Week 73 — Detector rules for local coding agent error taxonomy.

Each detector rule maps audit trace signals to failure categories.
Cheap checks run first; expensive checks run only when needed.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import re
import uuid

from .taxonomy import (
    LocalCodingFailureCategory,
    LocalCodingFailureRecord,
    LOCAL_CODING_TAXONOMY,
    LocalCodingFailureAnalysis,
)


@dataclass
class DetectorRule:
    name: str
    description: str
    category: LocalCodingFailureCategory
    check_fn_name: str
    priority: int = 0
    cost: str = "cheap"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "check_fn_name": self.check_fn_name,
            "priority": self.priority,
            "cost": self.cost,
        }


DETECTOR_RULES = [
    DetectorRule(
        name="no_read_before_edit",
        description="Model edited a file without reading it first",
        category=LocalCodingFailureCategory.MISSING_CONTEXT,
        check_fn_name="check_no_read_before_edit",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="output_contradicts_code",
        description="Generated output contradicts existing code patterns",
        category=LocalCodingFailureCategory.MISSING_CONTEXT,
        check_fn_name="check_output_contradicts_code",
        priority=1,
        cost="medium",
    ),
    DetectorRule(
        name="edit_wrong_file",
        description="Edit targeted wrong file based on task intent",
        category=LocalCodingFailureCategory.WRONG_FILE_SELECTED,
        check_fn_name="check_edit_wrong_file",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="nonexistent_import",
        description="Generated code imports modules that don't exist",
        category=LocalCodingFailureCategory.HALLUCINATED_API,
        check_fn_name="check_nonexistent_import",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="nonexistent_function_call",
        description="Generated code calls functions not defined in codebase",
        category=LocalCodingFailureCategory.HALLUCINATED_API,
        check_fn_name="check_nonexistent_function",
        priority=1,
        cost="medium",
    ),
    DetectorRule(
        name="patch_fails_apply",
        description="Generated patch cannot be applied cleanly",
        category=LocalCodingFailureCategory.BAD_PATCH,
        check_fn_name="check_patch_applies",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="syntax_error_after_patch",
        description="File has syntax errors after patch application",
        category=LocalCodingFailureCategory.BAD_PATCH,
        check_fn_name="check_syntax_after_patch",
        priority=1,
        cost="cheap",
    ),
    DetectorRule(
        name="test_still_failing",
        description="Tests still fail after patch was applied",
        category=LocalCodingFailureCategory.INCOMPLETE_PATCH,
        check_fn_name="check_test_still_failing",
        priority=0,
        cost="medium",
    ),
    DetectorRule(
        name="missing_side_effects",
        description="Patch missed related files or side effects",
        category=LocalCodingFailureCategory.INCOMPLETE_PATCH,
        check_fn_name="check_missing_side_effects",
        priority=2,
        cost="expensive",
    ),
    DetectorRule(
        name="wrong_assertion_interpretation",
        description="Model misinterpreted what test assertion checks",
        category=LocalCodingFailureCategory.TEST_MISUNDERSTANDING,
        check_fn_name="check_test_assertion_misread",
        priority=1,
        cost="medium",
    ),
    DetectorRule(
        name="model_modified_test_instead",
        description="Model changed test file instead of source code",
        category=LocalCodingFailureCategory.TEST_MISUNDERSTANDING,
        check_fn_name="check_modified_test_file",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="command_non_zero_exit",
        description="Command exited with non-zero exit code",
        category=LocalCodingFailureCategory.COMMAND_MISUSE,
        check_fn_name="check_command_exit_code",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="command_not_found",
        description="Referenced command does not exist in environment",
        category=LocalCodingFailureCategory.COMMAND_MISUSE,
        check_fn_name="check_command_exists",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="python_syntax_regression",
        description="Edit introduced Python syntax error",
        category=LocalCodingFailureCategory.SYNTAX_REGRESSION,
        check_fn_name="check_python_syntax",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="wrong_pattern_used",
        description="Model used wrong architectural pattern for codebase",
        category=LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING,
        check_fn_name="check_architectural_pattern",
        priority=2,
        cost="expensive",
    ),
    DetectorRule(
        name="change_breaks_layer",
        description="Change crosses architectural layer boundaries incorrectly",
        category=LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING,
        check_fn_name="check_layer_violation",
        priority=2,
        cost="expensive",
    ),
    DetectorRule(
        name="total_time_too_high",
        description="Task took longer than acceptable threshold",
        category=LocalCodingFailureCategory.EXCESSIVE_LATENCY,
        check_fn_name="check_total_time",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="model_load_time_high",
        description="Model loading time dominates total task time",
        category=LocalCodingFailureCategory.EXCESSIVE_LATENCY,
        check_fn_name="check_model_load_time",
        priority=1,
        cost="cheap",
    ),
    DetectorRule(
        name="context_exceeds_window",
        description="Context tokens exceed model's maximum context window",
        category=LocalCodingFailureCategory.CONTEXT_OVERFLOW,
        check_fn_name="check_context_window",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="too_many_files_retrieved",
        description="Retrieval returned too many files for context",
        category=LocalCodingFailureCategory.CONTEXT_OVERFLOW,
        check_fn_name="check_retrieval_count",
        priority=1,
        cost="cheap",
    ),
    DetectorRule(
        name="same_tool_repeated",
        description="Same tool called more than 3 times without file changes",
        category=LocalCodingFailureCategory.TOOL_LOOP_FAILURE,
        check_fn_name="check_repeated_tool_calls",
        priority=0,
        cost="cheap",
    ),
    DetectorRule(
        name="no_progress_after_n_calls",
        description="No files changed after N sequential tool calls",
        category=LocalCodingFailureCategory.TOOL_LOOP_FAILURE,
        check_fn_name="check_no_progress",
        priority=1,
        cost="cheap",
    ),
]


class LocalCodingFailureDetector:
    """Detects local coding agent failures from audit traces and context."""

    def __init__(self):
        self._history: List[LocalCodingFailureRecord] = []
        self._check_fns: Dict[str, Callable] = self._build_checks()

    def _build_checks(self) -> Dict[str, Callable]:
        return {
            "check_no_read_before_edit": self._check_no_read_before_edit,
            "check_output_contradicts_code": self._check_output_contradicts_code,
            "check_edit_wrong_file": self._check_edit_wrong_file,
            "check_nonexistent_import": self._check_nonexistent_import,
            "check_nonexistent_function": self._check_nonexistent_function,
            "check_patch_applies": self._check_patch_applies,
            "check_syntax_after_patch": self._check_syntax_after_patch,
            "check_test_still_failing": self._check_test_still_failing,
            "check_missing_side_effects": self._check_missing_side_effects,
            "check_test_assertion_misread": self._check_test_assertion_misread,
            "check_modified_test_file": self._check_modified_test_file,
            "check_command_exit_code": self._check_command_exit_code,
            "check_command_exists": self._check_command_exists,
            "check_python_syntax": self._check_python_syntax,
            "check_architectural_pattern": self._check_architectural_pattern,
            "check_layer_violation": self._check_layer_violation,
            "check_total_time": self._check_total_time,
            "check_model_load_time": self._check_model_load_time,
            "check_context_window": self._check_context_window,
            "check_retrieval_count": self._check_retrieval_count,
            "check_repeated_tool_calls": self._check_repeated_tool_calls,
            "check_no_progress": self._check_no_progress,
        }

    def detect(self, trace: dict) -> List[LocalCodingFailureRecord]:
        """Run all applicable detector rules against a trace."""
        failures = []
        for rule in DETECTOR_RULES:
            fn = self._check_fns.get(rule.check_fn_name)
            if fn is None:
                continue
            try:
                result = fn(trace)
                if result is not None:
                    failures.append(result)
            except Exception:
                pass
        self._history.extend(failures)
        return failures

    def _check_no_read_before_edit(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        tools = trace.get("tool_calls", [])
        read_files = set()
        edited_files = set()
        for t in tools:
            name = t.get("tool", "")
            if name == "read_file":
                read_files.add(t.get("params", {}).get("path", ""))
            if name == "edit_file":
                edited_files.add(t.get("params", {}).get("path", ""))
        unread_edits = edited_files - read_files
        if unread_edits:
            return self._make_record(
                LocalCodingFailureCategory.MISSING_CONTEXT,
                f"Edited files without reading: {unread_edits}",
                trace,
            )
        return None

    def _check_output_contradicts_code(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        generation = trace.get("output", "")
        existing_patterns = trace.get("code_patterns", {})
        for pattern, expected in existing_patterns.items():
            if pattern in generation and expected not in generation:
                return self._make_record(
                    LocalCodingFailureCategory.MISSING_CONTEXT,
                    f"Output contradicts code pattern '{pattern}'",
                    trace,
                )
        return None

    def _check_edit_wrong_file(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        task = trace.get("task", "").lower()
        tools = trace.get("tool_calls", [])
        task_files = re.findall(r'[\w./-]+\.\w+', task)
        edited_files = [
            t.get("params", {}).get("path", "")
            for t in tools if t.get("tool") == "edit_file"
        ]
        if task_files and edited_files:
            for ef in edited_files:
                if not any(tf in ef for tf in task_files):
                    return self._make_record(
                        LocalCodingFailureCategory.WRONG_FILE_SELECTED,
                        f"Task mentions {task_files} but edited {ef}",
                        trace,
                    )
        return None

    def _check_nonexistent_import(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        generation = trace.get("output", "")
        imports = re.findall(r'^\s*import\s+(\w+)|^\s*from\s+(\w+)', generation, re.MULTILINE)
        existing_modules = set(trace.get("existing_modules", []))
        for imp in imports:
            module = imp[0] or imp[1]
            if module and module not in existing_modules:
                return self._make_record(
                    LocalCodingFailureCategory.HALLUCINATED_API,
                    f"Import '{module}' not found in codebase",
                    trace,
                )
        return None

    def _check_nonexistent_function(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        generation = trace.get("output", "")
        calls = re.findall(r'(\w+)\s*\(', generation)
        existing_fns = set(trace.get("existing_functions", []))
        bad_calls = [c for c in calls if c not in existing_fns
                     and c not in {"if", "for", "while", "with", "def", "class",
                                   "print", "len", "range", "int", "str", "list",
                                   "dict", "set", "open", "isinstance", "hasattr",
                                   "getattr", "setattr", "type", "super", "self"}]
        if bad_calls:
            return self._make_record(
                LocalCodingFailureCategory.HALLUCINATED_API,
                f"Unknown function calls: {bad_calls[:5]}",
                trace,
            )
        return None

    def _check_patch_applies(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("patch_error"):
            return self._make_record(
                LocalCodingFailureCategory.BAD_PATCH,
                trace["patch_error"],
                trace,
            )
        return None

    def _check_syntax_after_patch(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("syntax_error"):
            return self._make_record(
                LocalCodingFailureCategory.SYNTAX_REGRESSION,
                trace["syntax_error"],
                trace,
            )
        return None

    def _check_test_still_failing(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        test_results = trace.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0)
            if failed and failed > 0:
                return self._make_record(
                    LocalCodingFailureCategory.INCOMPLETE_PATCH,
                    f"{failed} test(s) still failing after patch",
                    trace,
                )
        return None

    def _check_missing_side_effects(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        deps = trace.get("dependency_map", {})
        edited = trace.get("edited_files", [])
        for f in edited:
            related = deps.get(f, [])
            for r in related:
                if r not in edited and r not in trace.get("read_files", []):
                    return self._make_record(
                        LocalCodingFailureCategory.INCOMPLETE_PATCH,
                        f"Edited {f} but did not check related file {r}",
                        trace,
                    )
        return None

    def _check_test_assertion_misread(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        test_output = trace.get("test_output", "")
        patch = trace.get("output", "")
        assertions = re.findall(r'assert\s+(\w+)', test_output)
        if assertions:
            for a in assertions:
                if a not in patch:
                    return self._make_record(
                        LocalCodingFailureCategory.TEST_MISUNDERSTANDING,
                        f"Test assertion '{a}' not addressed in patch",
                        trace,
                    )
        return None

    def _check_modified_test_file(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        tools = trace.get("tool_calls", [])
        for t in tools:
            if t.get("tool") == "edit_file":
                path = t.get("params", {}).get("path", "")
                if "test" in path.lower() and "spec" in path.lower():
                    pass
                if path.startswith("test") or "/test_" in path or "tests/" in path:
                    return self._make_record(
                        LocalCodingFailureCategory.TEST_MISUNDERSTANDING,
                        f"Edited test file {path} instead of source",
                        trace,
                    )
        return None

    def _check_command_exit_code(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        for tool in trace.get("tool_calls", []):
            if tool.get("exit_code") is not None and tool["exit_code"] != 0:
                return self._make_record(
                    LocalCodingFailureCategory.COMMAND_MISUSE,
                    f"Command '{tool.get('tool')}' exited with code {tool['exit_code']}",
                    trace,
                )
        return None

    def _check_command_exists(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("command_not_found"):
            return self._make_record(
                LocalCodingFailureCategory.COMMAND_MISUSE,
                trace["command_not_found"],
                trace,
            )
        return None

    def _check_python_syntax(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("syntax_error"):
            return self._make_record(
                LocalCodingFailureCategory.SYNTAX_REGRESSION,
                trace["syntax_error"],
                trace,
            )
        return None

    def _check_architectural_pattern(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("architectural_violation"):
            return self._make_record(
                LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING,
                trace["architectural_violation"],
                trace,
            )
        return None

    def _check_layer_violation(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        if trace.get("layer_violation"):
            return self._make_record(
                LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING,
                trace["layer_violation"],
                trace,
            )
        return None

    def _check_total_time(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        threshold = trace.get("latency_threshold_ms", 30000)
        total = trace.get("total_time_ms", 0)
        if total > threshold:
            return self._make_record(
                LocalCodingFailureCategory.EXCESSIVE_LATENCY,
                f"Total time {total}ms exceeds threshold {threshold}ms",
                trace,
            )
        return None

    def _check_model_load_time(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        load_time = trace.get("model_load_time_ms", 0)
        total = trace.get("total_time_ms", 1)
        if total > 0 and load_time / total > 0.5:
            return self._make_record(
                LocalCodingFailureCategory.EXCESSIVE_LATENCY,
                f"Model load time {load_time}ms is {load_time/total*100:.0f}% of total",
                trace,
            )
        return None

    def _check_context_window(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        context_tokens = trace.get("context_tokens", 0)
        max_tokens = trace.get("model_max_tokens", 4096)
        if context_tokens > max_tokens:
            return self._make_record(
                LocalCodingFailureCategory.CONTEXT_OVERFLOW,
                f"Context {context_tokens} exceeds model limit {max_tokens}",
                trace,
            )
        return None

    def _check_retrieval_count(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        retrieved = trace.get("retrieved_files", [])
        if len(retrieved) > 15:
            return self._make_record(
                LocalCodingFailureCategory.CONTEXT_OVERFLOW,
                f"Retrieved {len(retrieved)} files; likely overflowed context",
                trace,
            )
        return None

    def _check_repeated_tool_calls(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        tools = trace.get("tool_calls", [])
        from collections import Counter
        tool_names = [t.get("tool", "") for t in tools]
        counts = Counter(tool_names)
        for name, count in counts.items():
            if count >= 4:
                params_seen = set()
                for t in tools:
                    if t.get("tool") == name:
                        p = str(t.get("params", {}))
                        params_seen.add(p)
                if len(params_seen) <= 2:
                    return self._make_record(
                        LocalCodingFailureCategory.TOOL_LOOP_FAILURE,
                        f"Same tool '{name}' called {count}x with similar params",
                        trace,
                    )
        return None

    def _check_no_progress(self, trace: dict) -> Optional[LocalCodingFailureRecord]:
        tools = trace.get("tool_calls", [])
        file_changes = [t for t in tools if t.get("tool") == "edit_file"]
        non_edit_calls = [t for t in tools if t.get("tool") != "edit_file"]
        if len(non_edit_calls) >= 6 and len(file_changes) == 0:
            return self._make_record(
                LocalCodingFailureCategory.TOOL_LOOP_FAILURE,
                f"{len(non_edit_calls)} non-edit tool calls without any file changes",
                trace,
            )
        return None

    def _make_record(
        self, category: LocalCodingFailureCategory, description: str, trace: dict
    ) -> LocalCodingFailureRecord:
        info = LOCAL_CODING_TAXONOMY.get(category, {})
        return LocalCodingFailureRecord(
            failure_id=f"lmf_{uuid.uuid4().hex[:12]}",
            category=category,
            description=description,
            severity=info.get("severity", "medium"),
            trace_ref=trace.get("trace_id"),
            audit_ref=trace.get("audit_id"),
            context={
                "tool_calls": len(trace.get("tool_calls", [])),
                "total_time_ms": trace.get("total_time_ms"),
            },
        )

    def analyze(self, records: List[LocalCodingFailureRecord]) -> LocalCodingFailureAnalysis:
        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        mitigated = 0
        for f in records:
            cat = f.category.value.replace("_", " ").title()
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            if f.mitigated_by:
                mitigated += 1
        total = len(records)
        rate = mitigated / total if total > 0 else 0.0
        if total == 0:
            summary = "No local coding agent failures detected."
        else:
            top_cat = max(by_category, key=by_category.get)
            top_sev = max(by_severity, key=by_severity.get)
            summary = (
                f"{total} failure(s) detected. "
                f"Most common: {top_cat} ({by_category[top_cat]}). "
                f"Highest severity: {top_sev} ({by_severity[top_sev]}). "
                f"Mitigation rate: {rate:.0%}."
            )
        return LocalCodingFailureAnalysis(
            failures=records,
            total_count=total,
            by_category=by_category,
            by_severity=by_severity,
            mitigation_rate=rate,
            summary=summary,
        )

    def get_history(self) -> List[LocalCodingFailureRecord]:
        return list(self._history)
