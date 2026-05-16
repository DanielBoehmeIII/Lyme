"""Experiment Generator for Lyme.

Given a research question, generates:
- hypotheses
- variables
- controls
- benchmark tasks
- expected failure modes
- telemetry needed
- evaluation criteria
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import json
import uuid


class HypothesisType(Enum):
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    EXPLORATORY = "exploratory"
    NULL = "null"
    ABLATION = "ablation"


class VariableRole(Enum):
    INDEPENDENT = "independent"
    DEPENDENT = "dependent"
    CONTROLLED = "controlled"
    CONFOUNDING = "confounding"


class ExpectedDirection(Enum):
    INCREASES = "increases"
    DECREASES = "decreases"
    UNCHANGED = "unchanged"
    NONLINEAR = "nonlinear"
    UNKNOWN = "unknown"


@dataclass
class Hypothesis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: HypothesisType = HypothesisType.CAUSAL
    statement: str = ""
    null_hypothesis: str = ""
    direction: ExpectedDirection = ExpectedDirection.UNKNOWN
    rationale: str = ""
    priors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Variable:
    name: str = ""
    role: VariableRole = VariableRole.INDEPENDENT
    description: str = ""
    levels: List[Any] = field(default_factory=list)
    measurement: str = ""
    unit: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "levels": self.levels[:10],
            "measurement": self.measurement,
            "unit": self.unit,
        }


@dataclass
class BenchmarkTask:
    name: str = ""
    description: str = ""
    task_type: str = ""
    difficulty: float = 0.5
    expected_baseline: float = 0.0
    metric: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FailureMode:
    name: str = ""
    description: str = ""
    likelihood: str = "medium"
    impact: str = "medium"
    mitigation: str = ""
    symptoms: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TelemetryRequirement:
    metric: str = ""
    source: str = ""
    granularity: str = "per_run"
    importance: str = "required"
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationCriterion:
    name: str = ""
    metric: str = ""
    operator: str = ">="
    threshold: float = 0.0
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExperimentPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    research_question: str = ""
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = "0.1.0"

    hypotheses: List[Hypothesis] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    controls: Dict[str, Any] = field(default_factory=dict)
    benchmark_tasks: List[BenchmarkTask] = field(default_factory=list)
    failure_modes: List[FailureMode] = field(default_factory=list)
    telemetry_needed: List[TelemetryRequirement] = field(default_factory=list)
    evaluation_criteria: List[EvaluationCriterion] = field(default_factory=list)
    replication_count: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "research_question": self.research_question,
            "generated_at": self.generated_at,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "variables": [v.to_dict() for v in self.variables],
            "controls": self.controls,
            "benchmark_tasks": [t.to_dict() for t in self.benchmark_tasks],
            "failure_modes": [f.to_dict() for f in self.failure_modes],
            "telemetry_needed": [t.to_dict() for t in self.telemetry_needed],
            "evaluation_criteria": [c.to_dict() for c in self.evaluation_criteria],
            "replication_count": self.replication_count,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Experiment Plan")
        lines.append(f"")
        lines.append(f"**Question**: {self.research_question}")
        lines.append(f"**Generated**: {self.generated_at}")
        lines.append(f"**Replications**: {self.replication_count}")
        lines.append(f"")

        if self.hypotheses:
            lines.append(f"## Hypotheses ({len(self.hypotheses)})")
            for h in self.hypotheses:
                lines.append(f"")
                lines.append(f"### H: {h.statement}")
                lines.append(f"- **Type**: {h.type.value}")
                lines.append(f"- **Direction**: {h.direction.value}")
                if h.null_hypothesis:
                    lines.append(f"- **H0**: {h.null_hypothesis}")
                if h.rationale:
                    lines.append(f"- **Rationale**: {h.rationale}")
            lines.append(f"")

        if self.variables:
            lines.append(f"## Variables ({len(self.variables)})")
            for v in self.variables:
                levels_str = ", ".join(str(l) for l in v.levels[:5]) if v.levels else "(none)"
                lines.append(f"- **{v.name}** ({v.role.value}): {v.description}")
                lines.append(f"  - Levels: {levels_str}")
                lines.append(f"  - Measurement: {v.measurement} ({v.unit})")
            lines.append(f"")

        if self.benchmark_tasks:
            lines.append(f"## Benchmark Tasks ({len(self.benchmark_tasks)})")
            for t in self.benchmark_tasks:
                lines.append(f"- **{t.name}** (diff: {t.difficulty:.1f}): {t.description}")
                lines.append(f"  - Metric: {t.metric}, Baseline: {t.expected_baseline}")
            lines.append(f"")

        if self.failure_modes:
            lines.append(f"## Expected Failure Modes ({len(self.failure_modes)})")
            for f in self.failure_modes:
                lines.append(f"- **{f.name}** [{f.likelihood}/{f.impact}]: {f.description}")
                if f.mitigation:
                    lines.append(f"  - Mitigation: {f.mitigation}")
            lines.append(f"")

        if self.telemetry_needed:
            lines.append(f"## Telemetry Requirements ({len(self.telemetry_needed)})")
            for t in self.telemetry_needed:
                lines.append(f"- **{t.metric}** ({t.importance}): {t.description}")
            lines.append(f"")

        if self.evaluation_criteria:
            lines.append(f"## Evaluation Criteria ({len(self.evaluation_criteria)})")
            for c in self.evaluation_criteria:
                lines.append(f"- {c.name}: {c.metric} {c.operator} {c.threshold} (weight: {c.weight})")
            lines.append(f"")

        return "\n".join(lines)


class ExperimentGenerator:
    """Generate complete experiment plans from research questions."""

    _QUESTION_TEMPLATES = {
        "causal graph": {
            "hypotheses": [
                "Causal graph context improves local model bug fixing accuracy",
                "Causal graph context reduces hallucination rate in code generation",
            ],
            "independent_var": "context_type",
            "levels": ["raw_file", "compressed", "causal_graph", "causal_graph_with_impact"],
            "dependent_var": "fix_accuracy",
            "measurement": "percentage of correct fixes",
            "tasks": ["single_file_bug", "multi_file_bug", "cross_subsystem_bug"],
        },
        "memory": {
            "hypotheses": [
                "Persistent memory improves task completion rate over sequential sessions",
                "Memory distillation prevents context collapse in long sessions",
            ],
            "independent_var": "memory_enabled",
            "levels": [True, False],
            "dependent_var": "task_completion_rate",
            "measurement": "fraction of tasks completed successfully",
            "tasks": ["iterative_edit", "knowledge_retention", "cross_session_task"],
        },
        "compression": {
            "hypotheses": [
                "Compressed context representation matches or exceeds raw context for code understanding",
                "Compression ratio correlates inversely with task performance degradation",
            ],
            "independent_var": "compression_strategy",
            "levels": ["none", "tree_only", "full_pipeline", "adaptive"],
            "dependent_var": "understanding_accuracy",
            "measurement": "correctness score on code comprehension tasks",
            "tasks": ["architecture_question", "impact_analysis", "bug_localization"],
        },
        "ablation": {
            "hypotheses": [
                "Removing causal graph context causes the largest performance degradation",
                "Compression matters more than memory for single-session tasks",
            ],
            "independent_var": "ablated_component",
            "levels": ["none", "memory", "compression", "causal_graph", "tool_router"],
            "dependent_var": "overall_performance",
            "measurement": "composite score across benchmark tasks",
            "tasks": ["all_benchmarks"],
        },
        "multi-agent": {
            "hypotheses": [
                "Adding agents beyond 3 decreases net throughput for tightly coupled codebases",
                "Star topology outperforms mesh topology for coordination efficiency",
            ],
            "independent_var": "agent_count",
            "levels": [1, 2, 3, 5, 10],
            "dependent_var": "throughput",
            "measurement": "tasks completed per unit time",
            "tasks": ["parallel_edit", "coordinated_refactor", "consensus_bug_fix"],
        },
        "default": {
            "hypotheses": [
                "The proposed intervention improves agent performance on codebase tasks",
            ],
            "independent_var": "intervention",
            "levels": ["control", "treatment"],
            "dependent_var": "performance",
            "measurement": "composite score",
            "tasks": ["general_task"],
        },
    }

    def generate(self, research_question: str) -> ExperimentPlan:
        plan = ExperimentPlan(research_question=research_question)
        q_lower = research_question.lower()

        template_key = "default"
        for key in self._QUESTION_TEMPLATES:
            if key in q_lower:
                template_key = key
                break

        template = self._QUESTION_TEMPLATES[template_key]

        for h_text in template["hypotheses"]:
            plan.hypotheses.append(Hypothesis(
                type=HypothesisType.CAUSAL if "improves" in h_text or "reduces" in h_text else HypothesisType.COMPARATIVE,
                statement=h_text,
                null_hypothesis=f"No significant difference: {h_text.replace('improves', 'does not affect').replace('reduces', 'does not affect')}",
                direction=ExpectedDirection.INCREASES if "improves" in h_text else ExpectedDirection.DECREASES,
                rationale=f"Based on prior work in software engineering agent evaluation",
            ))

        plan.variables.append(Variable(
            name=template["independent_var"],
            role=VariableRole.INDEPENDENT,
            description=f"The {template['independent_var']} being manipulated",
            levels=template["levels"],
            measurement=template["dependent_var"],
            unit=template["measurement"],
        ))
        plan.variables.append(Variable(
            name=template["dependent_var"],
            role=VariableRole.DEPENDENT,
            description=f"Measured {template['dependent_var']}",
            measurement=template["measurement"],
            unit="score",
        ))

        plan.controls = {
            "model": "fixed",
            "temperature": 0.0,
            "max_tokens": 4096,
            "random_seed": 42,
        }

        for task_name in template["tasks"]:
            plan.benchmark_tasks.append(BenchmarkTask(
                name=task_name,
                description=f"Benchmark task for {task_name}",
                task_type="code_edit",
                difficulty=0.5,
                expected_baseline=0.6,
                metric="accuracy",
            ))

        plan.failure_modes.append(FailureMode(
            name="measurement_noise",
            description="High variance in scores due to model nondeterminism",
            likelihood="high",
            impact="medium",
            mitigation="Increase replication count, control temperature",
            symptoms=["High confidence intervals", "Inconsistent rankings"],
        ))
        plan.failure_modes.append(FailureMode(
            name="task_leakage",
            description="Tasks inadvertently share information",
            likelihood="medium",
            impact="high",
            mitigation="Isolate task environments, use unique contexts",
            symptoms=["Unusually high scores", "Order effects"],
        ))

        plan.telemetry_needed.append(TelemetryRequirement(
            metric="task_completion_time",
            source="agent_trace",
            granularity="per_step",
            importance="required",
            description="Time to complete each task step",
        ))
        plan.telemetry_needed.append(TelemetryRequirement(
            metric="confidence_score",
            source="cognitive_trace",
            granularity="per_decision",
            importance="required",
            description="Agent confidence at each decision point",
        ))

        plan.evaluation_criteria.append(EvaluationCriterion(
            name="primary_metric",
            metric=template["dependent_var"],
            operator=">=",
            threshold=0.5,
            weight=1.0,
        ))

        plan.metadata = {
            "template_used": template_key,
            "generator_version": "0.1.0",
        }

        return plan
