import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class TaskCategory(str, Enum):
    CAUSAL_REASONING = "causal_reasoning"
    INVARIANT_PRESERVATION = "invariant_preservation"
    TEMPORAL_REASONING = "temporal_reasoning"
    ARCHITECTURE_AWARE_PLANNING = "architecture_aware_planning"
    EVIDENCE_GROUNDING = "evidence_grounding"
    SAFE_AUTONOMY = "safe_autonomy"
    MEMORY_USEFULNESS = "memory_usefulness"
    VERIFICATION_QUALITY = "verification_quality"


class TaskFormat(str, Enum):
    CODE_REPAIR = "code_repair"
    CODE_GENERATION = "code_generation"
    CODE_REFACTOR = "code_refactor"
    QUESTION_ANSWERING = "question_answering"
    DEBUGGING = "debugging"
    TEST_WRITING = "test_writing"
    CODE_REVIEW = "code_review"
    ARCHITECTURE_DECISION = "architecture_decision"
    DEPENDENCY_UPDATE = "dependency_update"
    DOCUMENTATION = "documentation"


class ScoreMetric(str, Enum):
    PASS_FAIL = "pass_fail"
    BINARY_SCORE = "binary_score"
    CONTINUOUS_01 = "continuous_01"
    MULTI_CRITERIA = "multi_criteria"
    COMPARATIVE = "comparative"
    LATENCY = "latency"
    EFFICIENCY = "efficiency"
    ACCURACY = "accuracy"


@dataclass
class ScoringMethod:
    metric: str = ScoreMetric.PASS_FAIL
    formula: str = ""
    thresholds: Dict[str, float] = field(default_factory=dict)
    weight: float = 1.0
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TelemetryRequirements:
    required_events: List[str] = field(default_factory=list)
    required_metrics: List[str] = field(default_factory=list)
    trace_format: str = "open-agent-trace-standard"
    trace_version: str = "0.7.0"
    sampling_rate: float = 1.0
    privacy_filter: str = "default"
    additional_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AntiGamingRules:
    forbidden_patterns: List[str] = field(default_factory=list)
    max_attempts: int = 3
    cooldown_seconds: int = 0
    verification_required: bool = True
    human_verification_threshold: float = 0.95
    memory_wipes_between_tasks: bool = True
    context_budget: int = 0
    tool_restrictions: List[str] = field(default_factory=list)
    rule_description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BaselineSystem:
    name: str = ""
    model: str = ""
    version: str = ""
    framework: str = ""
    expected_performance: Dict[str, float] = field(default_factory=dict)
    known_limitations: List[str] = field(default_factory=list)
    reference_results_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FailureInterpretation:
    failure_categories: List[str] = field(default_factory=list)
    severity_levels: Dict[str, str] = field(default_factory=dict)
    retry_policy: str = ""
    abort_conditions: List[str] = field(default_factory=list)
    classification_guide: str = ""
    interpretation_notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkDimension:
    name: str = ""
    description: str = ""
    tasks: List[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkTask:
    id: str = ""
    category: str = TaskCategory.CAUSAL_REASONING
    format: str = TaskFormat.CODE_REPAIR
    name: str = ""
    description: str = ""
    prompt: str = ""
    success_criteria: str = ""
    scoring: ScoringMethod = field(default_factory=ScoringMethod)
    telemetry: TelemetryRequirements = field(default_factory=TelemetryRequirements)
    anti_gaming: AntiGamingRules = field(default_factory=AntiGamingRules)
    baselines: List[BaselineSystem] = field(default_factory=list)
    failure_interpretation: FailureInterpretation = field(default_factory=FailureInterpretation)
    tags: List[str] = field(default_factory=list)
    estimated_difficulty: str = "medium"
    estimated_duration_seconds: int = 120

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "format": self.format,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "success_criteria": self.success_criteria,
            "scoring": self.scoring.to_dict(),
            "telemetry": self.telemetry.to_dict(),
            "anti_gaming": self.anti_gaming.to_dict(),
            "baselines": [b.to_dict() for b in self.baselines],
            "failure_interpretation": self.failure_interpretation.to_dict(),
            "tags": self.tags,
            "estimated_difficulty": self.estimated_difficulty,
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }


@dataclass
class CognitionBenchmarkSpec:
    name: str = "Lyme Software Cognition Benchmark"
    version: str = "0.7.0"
    schema_urn: str = "urn:lyme:standard:cognition-benchmark:v1"
    description: str = ""
    dimensions: List[BenchmarkDimension] = field(default_factory=list)
    tasks: List[dict] = field(default_factory=list)
    telemetry_defaults: TelemetryRequirements = field(default_factory=TelemetryRequirements)
    anti_gaming_defaults: AntiGamingRules = field(default_factory=AntiGamingRules)
    scoring_rubric: str = ""
    notes: str = ""

    def add_task(self, task: BenchmarkTask):
        self.tasks.append(task.to_dict())

    def add_dimension(self, dim: BenchmarkDimension):
        self.dimensions.append(dim)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "schema_urn": self.schema_urn,
            "description": self.description,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "tasks": self.tasks,
            "telemetry_defaults": self.telemetry_defaults.to_dict(),
            "anti_gaming_defaults": self.anti_gaming_defaults.to_dict(),
            "scoring_rubric": self.scoring_rubric,
            "notes": self.notes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "CognitionBenchmarkSpec":
        spec = cls.__new__(cls)
        spec.name = d.get("name", cls.name)
        spec.version = d.get("version", cls.version)
        spec.schema_urn = d.get("schema_urn", cls.schema_urn)
        spec.description = d.get("description", "")
        spec.tasks = d.get("tasks", [])
        spec.scoring_rubric = d.get("scoring_rubric", "")
        spec.notes = d.get("notes", "")
        spec.telemetry_defaults = TelemetryRequirements(**d.get("telemetry_defaults", {}))
        spec.anti_gaming_defaults = AntiGamingRules(**d.get("anti_gaming_defaults", {}))
        spec.dimensions = []
        for dim in d.get("dimensions", []):
            spec.dimensions.append(BenchmarkDimension(**dim))
        return spec
