"""Lyme Project Schema: versioned local data format.

Human-inspectable, machine-queryable, portable, privacy-first,
replayable, and compatible with future UI.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import json
import hashlib


SCHEMA_VERSION = "0.1.0"
SCHEMA_URL = "https://lyme.dev/schema/v0.1.0"


class ActionType(Enum):
    QUERY = "query"
    FIX = "fix"
    DIFF = "diff"
    DIAGNOSE = "diagnose"
    BENCHMARK = "benchmark"
    EDIT = "edit"
    UNDO = "undo"
    REPLAY = "replay"
    DISCOVER = "discover"
    LEARN = "learn"


class ActionOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


@dataclass
class LymeSchemaMeta:
    schema_version: str = SCHEMA_VERSION
    schema_url: str = SCHEMA_URL
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    lyme_version: str = "0.1.0"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RepoGraphNode:
    id: str
    path: str
    type: str
    size_bytes: int = 0
    complexity: float = 0.0
    change_frequency: int = 0
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RepoGraph:
    meta: LymeSchemaMeta = field(default_factory=LymeSchemaMeta)
    repo_path: str = ""
    repo_hash: str = ""
    nodes: Dict[str, RepoGraphNode] = field(default_factory=dict)
    edges: List[dict] = field(default_factory=list)
    subsystems: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "meta": self.meta.to_dict(),
            "repo_path": self.repo_path,
            "repo_hash": self.repo_hash,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": self.edges,
            "subsystems": self.subsystems,
        }


@dataclass
class ModelRun:
    run_id: str
    model_name: str
    model_size: str
    task_type: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "pending"
    tokens_in: int = 0
    tokens_out: int = 0
    temperature: float = 0.0
    config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    trace_ref: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class TraceStep:
    step_id: str
    type: str
    timestamp: str
    duration_ms: float
    input_summary: str
    output_summary: str
    confidence: float = 0.0
    parent_id: Optional[str] = None
    branch: str = "main"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentTrace:
    meta: LymeSchemaMeta = field(default_factory=LymeSchemaMeta)
    trace_id: str = ""
    agent_name: str = ""
    scenario: str = ""
    action_type: ActionType = ActionType.QUERY
    outcome: ActionOutcome = ActionOutcome.UNKNOWN
    steps: List[TraceStep] = field(default_factory=list)
    decisions: List[dict] = field(default_factory=list)
    tool_calls: List[dict] = field(default_factory=list)
    anomalies: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "meta": self.meta.to_dict(),
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "scenario": self.scenario,
            "action_type": self.action_type.value,
            "outcome": self.outcome.value,
            "steps": [s.to_dict() for s in self.steps],
            "decisions": self.decisions,
            "tool_calls": self.tool_calls,
            "anomalies": self.anomalies,
        }


@dataclass
class SemanticDiff:
    meta: LymeSchemaMeta = field(default_factory=LymeSchemaMeta)
    diff_id: str = ""
    repo_path: str = ""
    before_commit: str = ""
    after_commit: str = ""
    file_diffs: List[dict] = field(default_factory=list)
    semantic_categories: List[str] = field(default_factory=list)
    classification_confidence: float = 0.0
    risk_score: float = 0.0
    affected_subsystems: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "meta": self.meta.to_dict(),
            "diff_id": self.diff_id,
            "repo_path": self.repo_path,
            "before_commit": self.before_commit,
            "after_commit": self.after_commit,
            "file_diffs": self.file_diffs,
            "semantic_categories": self.semantic_categories,
            "classification_confidence": self.classification_confidence,
            "risk_score": self.risk_score,
            "affected_subsystems": self.affected_subsystems,
            "summary": self.summary,
        }


@dataclass
class MemoryEntry:
    memory_id: str
    type: str
    content_summary: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    access_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_accessed: Optional[str] = None
    source_trace: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkResult:
    benchmark_id: str
    scenario_name: str
    agent_name: str
    model_name: str
    success: bool
    metrics: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    trace_ref: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvariantHypothesis:
    invariant_id: str
    name: str
    type: str
    description: str
    rule: str
    severity: str = "medium"
    confidence: float = 0.0
    scope: str = "global"
    source: str = "inference"
    evidence: List[str] = field(default_factory=list)
    violations: List[dict] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CausalRelationship:
    relation_id: str
    source_node: str
    target_node: str
    relation_type: str
    weight: float = 1.0
    confidence: float = 0.0
    evidence_sources: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TemporalSnapshot:
    period_start: str
    period_end: str
    metrics: dict = field(default_factory=dict)
    events_count: int = 0
    stability_class: str = "stable"
    growth_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UserIntervention:
    intervention_id: str
    action_type: str
    target: str
    description: str
    outcome: str = "unknown"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    trace_ref: Optional[str] = None
    undo_ref: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowEntry:
    workflow_id: str
    name: str
    outcome: str
    steps: List[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    confidence: float = 0.0
    model_name: str = ""
    trace_refs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LymeProject:
    """Canonical Lyme project — all data in one versioned, portable format."""

    meta: LymeSchemaMeta = field(default_factory=LymeSchemaMeta)
    repo_graph: Optional[dict] = None
    model_runs: List[ModelRun] = field(default_factory=list)
    traces: List[AgentTrace] = field(default_factory=list)
    diffs: List[SemanticDiff] = field(default_factory=list)
    memories: List[MemoryEntry] = field(default_factory=list)
    benchmarks: List[BenchmarkResult] = field(default_factory=list)
    invariants: List[InvariantHypothesis] = field(default_factory=list)
    causal_relationships: List[CausalRelationship] = field(default_factory=list)
    temporal_history: List[TemporalSnapshot] = field(default_factory=list)
    interventions: List[UserIntervention] = field(default_factory=list)
    workflows: List[WorkflowEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.meta.schema_version,
            "schema_url": self.meta.schema_url,
            "created_at": self.meta.created_at,
            "lyme_version": self.meta.lyme_version,
            "repo_graph": self.repo_graph,
            "model_runs": [r.to_dict() for r in self.model_runs],
            "traces": [t.to_dict() for t in self.traces],
            "diffs": [d.to_dict() for d in self.diffs],
            "memories": [m.to_dict() for m in self.memories],
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "invariants": [i.to_dict() for i in self.invariants],
            "causal_relationships": [c.to_dict() for c in self.causal_relationships],
            "temporal_history": [t.to_dict() for t in self.temporal_history],
            "interventions": [iv.to_dict() for iv in self.interventions],
            "workflows": [w.to_dict() for w in self.workflows],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "LymeProject":
        project = cls()

        if "repo_graph" in data:
            project.repo_graph = data["repo_graph"]

        if "model_runs" in data:
            for run_data in data["model_runs"]:
                project.model_runs.append(ModelRun(**{
                    k: v for k, v in run_data.items()
                    if k in ModelRun.__dataclass_fields__
                }))

        if "traces" in data:
            for trace_data in data["traces"]:
                trace = AgentTrace()
                trace.trace_id = trace_data.get("trace_id", "")
                trace.agent_name = trace_data.get("agent_name", "")
                trace.scenario = trace_data.get("scenario", "")
                if "action_type" in trace_data:
                    try:
                        trace.action_type = ActionType(trace_data["action_type"])
                    except ValueError:
                        pass
                if "outcome" in trace_data:
                    try:
                        trace.outcome = ActionOutcome(trace_data["outcome"])
                    except ValueError:
                        pass
                if "steps" in trace_data:
                    for step_data in trace_data["steps"]:
                        trace.steps.append(TraceStep(**{
                            k: v for k, v in step_data.items()
                            if k in TraceStep.__dataclass_fields__
                        }))
                trace.decisions = trace_data.get("decisions", [])
                trace.tool_calls = trace_data.get("tool_calls", [])
                trace.anomalies = trace_data.get("anomalies", [])
                project.traces.append(trace)

        for collection_name, cls_type in [
            ("diffs", SemanticDiff),
            ("memories", MemoryEntry),
            ("benchmarks", BenchmarkResult),
            ("invariants", InvariantHypothesis),
            ("causal_relationships", CausalRelationship),
            ("temporal_history", TemporalSnapshot),
            ("interventions", UserIntervention),
            ("workflows", WorkflowEntry),
        ]:
            if collection_name in data:
                collection = getattr(project, collection_name)
                for item_data in data[collection_name]:
                    collection.append(cls_type(**{
                        k: v for k, v in item_data.items()
                        if k in cls_type.__dataclass_fields__
                    }))

        return project

    @classmethod
    def from_json(cls, json_str: str) -> "LymeProject":
        return cls.from_dict(json.loads(json_str))

    @classmethod 
    def from_file(cls, path: Path) -> "LymeProject":
        with open(path) as f:
            return cls.from_dict(json.load(f))


class ProjectSchema:
    """Validator and helper for the Lyme project schema."""

    @staticmethod
    def validate(project: LymeProject) -> List[str]:
        errors = []
        if not project.meta.schema_version:
            errors.append("Missing schema_version")

        try:
            major = int(project.meta.schema_version.split(".")[0])
            expected_major = int(SCHEMA_VERSION.split(".")[0])
            if major != expected_major:
                errors.append(
                    f"Schema major version {major} != expected {expected_major}"
                )
        except ValueError:
            errors.append(f"Invalid schema_version: {project.meta.schema_version}")

        if project.repo_graph:
            if "repo_path" not in project.repo_graph:
                errors.append("repo_graph missing repo_path")

        for i, run in enumerate(project.model_runs):
            if not run.run_id:
                errors.append(f"model_runs[{i}] missing run_id")

        for i, trace in enumerate(project.traces):
            if not trace.trace_id:
                errors.append(f"traces[{i}] missing trace_id")

        return errors

    @staticmethod
    def compute_repo_hash(repo_path: Path) -> str:
        path_str = str(repo_path.resolve())
        return hashlib.sha256(path_str.encode()).hexdigest()[:16]

    @staticmethod
    def summary(project: LymeProject) -> dict:
        return {
            "schema_version": project.meta.schema_version,
            "created_at": project.meta.created_at,
            "repo_graph_present": project.repo_graph is not None,
            "model_runs": len(project.model_runs),
            "traces": len(project.traces),
            "diffs": len(project.diffs),
            "memories": len(project.memories),
            "benchmarks": len(project.benchmarks),
            "invariants": len(project.invariants),
            "causal_relationships": len(project.causal_relationships),
            "temporal_history": len(project.temporal_history),
            "interventions": len(project.interventions),
            "workflows": len(project.workflows),
        }
