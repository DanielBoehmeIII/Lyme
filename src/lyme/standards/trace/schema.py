import time
import uuid
import dataclasses
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class EventType(str, Enum):
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    FILE_READ = "file_read"
    FILE_EDIT = "file_edit"
    TEST_RUN = "test_run"
    FAILED_ATTEMPT = "failed_attempt"
    EVIDENCE_CLAIM = "evidence_claim"
    VERIFICATION_STEP = "verification_step"
    HUMAN_INTERVENTION = "human_intervention"
    CONFIDENCE_CHANGE = "confidence_change"
    ROLLBACK = "rollback"
    PLAN = "plan"
    DECISION = "decision"
    SEARCH = "search"
    METRIC = "metric"
    SYSTEM = "system"
    CHECKPOINT = "checkpoint"
    THOUGHT = "thought"
    CONTEXT_SHIFT = "context_shift"


class RollbackStrategy(str, Enum):
    GIT_REVERT = "git_revert"
    PATCH_INVERSE = "patch_inverse"
    STATE_RESTORE = "state_restore"
    SEMANTIC_ROLLBACK = "semantic_rollback"
    FULL_CHECKPOINT = "full_checkpoint"
    MANUAL = "manual"


class VerificationResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"
    GUESSING = "guessing"


@dataclass
class AgentIdentity:
    name: str = ""
    model: str = ""
    version: str = ""
    framework: str = "lyme"
    capabilities: List[str] = field(default_factory=list)


@dataclass
class SystemMetadata:
    os: str = ""
    python_version: str = ""
    runtime_ms: float = 0.0
    context_window_used: int = 0
    context_window_max: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    git_head: str = ""
    repo_name: str = ""


@dataclass
class TraceHeader:
    trace_id: str = field(default_factory=lambda: f"oat-{uuid.uuid4().hex[:16]}")
    schema_version: str = "0.7.0"
    schema_urn: str = "urn:lyme:standard:open-agent-trace:v1"
    agent: AgentIdentity = field(default_factory=AgentIdentity)
    system: SystemMetadata = field(default_factory=SystemMetadata)
    created_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    parent_trace_id: Optional[str] = None
    session_id: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "schema_version": self.schema_version,
            "schema_urn": self.schema_urn,
            "agent": dataclasses.asdict(self.agent),
            "system": dataclasses.asdict(self.system),
            "created_at": self.created_at,
            "duration_ms": self.duration_ms,
            "parent_trace_id": self.parent_trace_id,
            "session_id": self.session_id,
            "tags": self.tags,
        }


@dataclass
class TraceEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = EventType.SYSTEM
    timestamp: float = field(default_factory=time.time)
    duration_ms: Optional[float] = None
    parent_id: Optional[str] = None
    sequence: int = 0
    status: str = "success"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class ModelCallEvent(TraceEvent):
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    temperature: float = 0.0
    max_tokens: int = 0
    prompt_preview: str = ""
    completion_preview: str = ""
    cost: float = 0.0
    latency_ms: float = 0.0
    num_tool_calls: int = 0

    def __post_init__(self):
        if not self.type or self.type == "system":
            self.type = EventType.MODEL_CALL


@dataclass
class ToolCallEvent(TraceEvent):
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    tool_output_preview: str = ""
    success: bool = True
    result_status: str = "success"
    error_type: Optional[str] = None

    def __post_init__(self):
        self.type = EventType.TOOL_CALL


@dataclass
class FileReadEvent(TraceEvent):
    file_path: str = ""
    bytes_read: int = 0
    lines_read: int = 0
    content_preview: str = ""
    encoding: str = "utf-8"

    def __post_init__(self):
        self.type = EventType.FILE_READ


@dataclass
class FileEditEvent(TraceEvent):
    file_path: str = ""
    edit_type: str = ""  # insert, delete, replace, create, delete_file
    old_text_preview: str = ""
    new_text_preview: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    patch_hash: str = ""
    dry_run: bool = False
    verified: bool = False
    verification_id: Optional[str] = None

    def __post_init__(self):
        self.type = EventType.FILE_EDIT


@dataclass
class TestRunEvent(TraceEvent):
    command: str = ""
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    total_tests: int = 0
    coverage_percent: Optional[float] = None
    duration: float = 0.0
    exit_code: int = 0
    failure_messages: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = EventType.TEST_RUN


@dataclass
class FailedAttemptEvent(TraceEvent):
    attempt_number: int = 1
    max_attempts: int = 3
    failure_reason: str = ""
    failure_category: str = ""
    strategy_change: str = ""
    retry_strategy: str = ""
    lessons_learned: str = ""

    def __post_init__(self):
        self.type = EventType.FAILED_ATTEMPT


@dataclass
class EvidenceClaimEvent(TraceEvent):
    claim: str = ""
    claim_type: str = ""  # observation, inference, prediction, verification
    supporting_evidence: List[dict] = field(default_factory=list)
    confidence: float = 0.0
    source: str = ""
    verified: bool = False
    verification_id: Optional[str] = None
    contradictory_evidence: List[dict] = field(default_factory=list)

    def __post_init__(self):
        self.type = EventType.EVIDENCE_CLAIM


@dataclass
class VerificationStepEvent(TraceEvent):
    verification_type: str = ""  # test, static_analysis, type_check, review, manual
    target: str = ""
    result: str = VerificationResult.INCONCLUSIVE
    evidence_ids: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    coverage_gaps: List[str] = field(default_factory=list)
    verification_depth: str = "fast"

    def __post_init__(self):
        self.type = EventType.VERIFICATION_STEP


@dataclass
class HumanInterventionEvent(TraceEvent):
    intervention_type: str = ""  # approval, rejection, override, guidance, correction
    user_message: str = ""
    context: str = ""
    effect: str = ""  # allowed, blocked, redirected, corrected
    duration_to_respond_ms: float = 0.0
    prior_confidence: float = 0.0
    post_confidence: float = 0.0

    def __post_init__(self):
        self.type = EventType.HUMAN_INTERVENTION


@dataclass
class ConfidenceChangeEvent(TraceEvent):
    prior_confidence: float = 0.0
    post_confidence: float = 0.0
    change_reason: str = ""
    related_event_id: Optional[str] = None
    confidence_level: str = ""
    previous_level: str = ""

    def __post_init__(self):
        self.type = EventType.CONFIDENCE_CHANGE


@dataclass
class RollbackEvent(TraceEvent):
    rollback_strategy: str = RollbackStrategy.GIT_REVERT
    target_event_id: str = ""
    target_description: str = ""
    success: bool = True
    files_affected: List[str] = field(default_factory=list)
    lines_restored: int = 0
    reason: str = ""
    redo_available: bool = False
    redo_event_id: Optional[str] = None

    def __post_init__(self):
        self.type = EventType.ROLLBACK


@dataclass
class OpenAgentTrace:
    header: TraceHeader = field(default_factory=TraceHeader)
    events: List[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def add_event(self, event: TraceEvent):
        event.sequence = len(self.events)
        self.events.append(event.to_dict())

    def finalize(self, status: str = "completed", metrics: dict = None):
        now = time.time()
        self.header.duration_ms = (now - self.header.created_at) * 1000
        model_calls = sum(1 for e in self.events if e.get("type") == EventType.MODEL_CALL)
        tool_calls = sum(1 for e in self.events if e.get("type") == EventType.TOOL_CALL)
        file_reads = sum(1 for e in self.events if e.get("type") == EventType.FILE_READ)
        file_edits = sum(1 for e in self.events if e.get("type") == EventType.FILE_EDIT)
        test_runs = sum(1 for e in self.events if e.get("type") == EventType.TEST_RUN)
        failed = sum(1 for e in self.events if e.get("type") == EventType.FAILED_ATTEMPT)
        rollbacks = sum(1 for e in self.events if e.get("type") == EventType.ROLLBACK)
        interventions = sum(1 for e in self.events if e.get("type") == EventType.HUMAN_INTERVENTION)
        errors = sum(1 for e in self.events if e.get("status") == "error")
        total_tokens = sum(
            e.get("total_tokens", 0) for e in self.events
            if e.get("type") == EventType.MODEL_CALL
        )

        self.summary = {
            "schema": f"{SCHEMA_NAME} v{SCHEMA_VERSION}",
            "schema_urn": SCHEMA_URN,
            "event_count": len(self.events),
            "duration_ms": self.header.duration_ms,
            "status": status,
            "totals": {
                "model_calls": model_calls,
                "tool_calls": tool_calls,
                "file_reads": file_reads,
                "file_edits": file_edits,
                "test_runs": test_runs,
                "failed_attempts": failed,
                "rollbacks": rollbacks,
                "human_interventions": interventions,
                "errors": errors,
                "total_tokens": total_tokens,
            },
            "agent": dataclasses.asdict(self.header.agent),
            **(metrics or {}),
        }

    def to_dict(self) -> dict:
        return {
            "header": self.header.to_dict(),
            "events": self.events,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OpenAgentTrace":
        trace = cls.__new__(cls)
        header_data = d.get("header", {})
        agent_data = header_data.get("agent", {})
        system_data = header_data.get("system", {})
        trace.header = TraceHeader(
            trace_id=header_data.get("trace_id", ""),
            schema_version=header_data.get("schema_version", "0.7.0"),
            schema_urn=header_data.get("schema_urn", SCHEMA_URN),
            agent=AgentIdentity(**agent_data),
            system=SystemMetadata(**system_data),
            created_at=header_data.get("created_at", 0.0),
            duration_ms=header_data.get("duration_ms", 0.0),
            parent_trace_id=header_data.get("parent_trace_id"),
            session_id=header_data.get("session_id", ""),
            tags=header_data.get("tags", {}),
        )
        trace.events = d.get("events", [])
        trace.summary = d.get("summary", {})
        return trace

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_json(cls, s: str) -> "OpenAgentTrace":
        import json
        return cls.from_dict(json.loads(s))


SCHEMA_VERSION = "0.7.0"
SCHEMA_NAME = "open-agent-trace-standard"
SCHEMA_URN = "urn:lyme:standard:open-agent-trace:v1"
