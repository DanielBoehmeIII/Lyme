from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RuntimeEventType(str, Enum):
    LOG = "log"
    STACK_TRACE = "stack_trace"
    TEST_TRACE = "test_trace"
    METRIC = "metric"
    PROFILING_SAMPLE = "profiling_sample"
    EXCEPTION_FLOW = "exception_flow"
    NETWORK_EVENT = "network_event"
    ASYNC_TIMING = "async_timing"
    BROWSER_EVENT = "browser_event"
    API_CALL = "api_call"
    STATE_MUTATION = "state_mutation"
    MEMORY_PRESSURE = "memory_pressure"
    RACE_CONDITION = "race_condition"
    RETRY = "retry"
    CACHE_OPERATION = "cache_operation"
    DB_QUERY = "db_query"
    TIMEOUT = "timeout"
    SYNC_BOUNDARY = "sync_boundary"
    EVENT_PROPAGATION = "event_propagation"
    USER_ACTION = "user_action"
    DEPLOYMENT = "deployment"
    CONFIG_CHANGE = "config_change"


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CorrelationConfidence(str, Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


@dataclass
class StackFrame:
    file: str = ""
    function: str = ""
    line: int = 0
    module: str = ""
    locals: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "function": self.function,
            "line": self.line,
            "module": self.module,
            "locals": self.locals,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StackFrame:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RuntimeTraceEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_id: Optional[str] = None
    event_type: RuntimeEventType = RuntimeEventType.LOG
    timestamp: float = field(default_factory=time.time)
    duration_ms: Optional[float] = None
    severity: EventSeverity = EventSeverity.INFO
    source: str = ""
    source_file: str = ""
    source_line: int = 0
    source_function: str = ""
    subsystem: str = ""
    service: str = ""
    host: str = ""
    environment: str = ""
    version: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_frames: List[StackFrame] = field(default_factory=list)
    related_span_ids: List[str] = field(default_factory=list)
    correlation_id: str = ""
    causal_parent: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "severity": self.severity.value,
            "source": self.source,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "source_function": self.source_function,
            "subsystem": self.subsystem,
            "service": self.service,
            "host": self.host,
            "environment": self.environment,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
            "stack_frames": [f.to_dict() for f in self.stack_frames],
            "related_span_ids": self.related_span_ids,
            "correlation_id": self.correlation_id,
            "causal_parent": self.causal_parent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RuntimeTraceEvent:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "stack_frames"}
        fields["stack_frames"] = [StackFrame.from_dict(f) for f in d.get("stack_frames", [])]
        return cls(**fields)


@dataclass
class TraceSpan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    category: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "pending"
    service: str = ""
    subsystem: str = ""
    events: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def finish(self, status: str = "success", error: Optional[str] = None):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "category": self.category,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "service": self.service,
            "subsystem": self.subsystem,
            "events": self.events,
            "metadata": self.metadata,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TraceSpan:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RuntimeTrace:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    application: str = ""
    environment: str = ""
    version: str = ""
    host: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "in_progress"
    event_count: int = 0
    span_count: int = 0
    error_count: int = 0
    spans: List[TraceSpan] = field(default_factory=list)
    events: List[RuntimeTraceEvent] = field(default_factory=list)
    correlations: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_commit: str = ""
    source_branch: str = ""
    source_repo: str = ""

    def add_event(self, event: RuntimeTraceEvent):
        event.trace_id = self.trace_id
        self.events.append(event)
        self.event_count = len(self.events)
        if event.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
            self.error_count += 1

    def add_span(self, span: TraceSpan):
        span.trace_id = self.trace_id
        self.spans.append(span)
        self.span_count = len(self.spans)

    def finish(self, status: str = "completed"):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "application": self.application,
            "environment": self.environment,
            "version": self.version,
            "host": self.host,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "event_count": self.event_count,
            "span_count": self.span_count,
            "error_count": self.error_count,
            "spans": [s.to_dict() for s in self.spans],
            "events": [e.to_dict() for e in self.events],
            "correlations": self.correlations,
            "metadata": self.metadata,
            "source_commit": self.source_commit,
            "source_branch": self.source_branch,
            "source_repo": self.source_repo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RuntimeTrace:
        trace = cls(
            trace_id=d.get("trace_id", uuid.uuid4().hex[:16]),
            name=d.get("name", ""),
            application=d.get("application", ""),
            environment=d.get("environment", ""),
            version=d.get("version", ""),
            host=d.get("host", ""),
            start_time=d.get("start_time", time.time()),
            end_time=d.get("end_time"),
            duration_ms=d.get("duration_ms"),
            status=d.get("status", "unknown"),
            event_count=d.get("event_count", 0),
            span_count=d.get("span_count", 0),
            error_count=d.get("error_count", 0),
            correlations=d.get("correlations", {}),
            metadata=d.get("metadata", {}),
            source_commit=d.get("source_commit", ""),
            source_branch=d.get("source_branch", ""),
            source_repo=d.get("source_repo", ""),
        )
        for s in d.get("spans", []):
            trace.spans.append(TraceSpan.from_dict(s))
        for e in d.get("events", []):
            trace.events.append(RuntimeTraceEvent.from_dict(e))
        return trace

    def find_events_by_type(self, event_type: RuntimeEventType) -> List[RuntimeTraceEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def find_events_by_file(self, file_path: str) -> List[RuntimeTraceEvent]:
        return [e for e in self.events if e.source_file == file_path]

    def find_events_by_subsystem(self, subsystem: str) -> List[RuntimeTraceEvent]:
        return [e for e in self.events if e.subsystem == subsystem]

    def get_error_events(self) -> List[RuntimeTraceEvent]:
        return [e for e in self.events if e.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL)]

    def get_timeline(self) -> List[RuntimeTraceEvent]:
        return sorted(self.events, key=lambda e: e.timestamp)
