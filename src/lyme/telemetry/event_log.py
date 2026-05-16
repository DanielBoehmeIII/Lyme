import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class EventType(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"
    PLAN = "plan"
    PLAN_ABANDONED = "plan_abandoned"
    RETRY = "retry"
    ERROR = "error"
    HALLUCINATION = "hallucination"
    CONTEXT_FRAGMENT = "context_fragment"
    NAVIGATION = "navigation"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    SEARCH = "search"
    UNCERTAINTY = "uncertainty"
    METRIC = "metric"
    SYSTEM = "system"
    THOUGHT = "thought"
    CHECKPOINT = "checkpoint"
    REPAIR = "repair"


@dataclass
class Event:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = ""
    span_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    type: str = EventType.SYSTEM
    payload: dict = field(default_factory=dict)
    severity: str = "info"
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "timestamp": self.timestamp,
            "type": self.type,
            "payload": self.payload,
            "severity": self.severity,
            "source": self.source,
        }


class EventLog:
    def __init__(self):
        self._events: list = []
        self._listeners: list = []

    def record(self, event: Event):
        self._events.append(event)
        for listener in self._listeners:
            listener(event)

    def emit(self, type_: str, payload: dict = None, trace_id: str = "",
             span_id: str = "", severity: str = "info", source: str = ""):
        from .tracer import TraceContext
        ctx = TraceContext.current()
        event = Event(
            trace_id=trace_id or (ctx.trace_id if ctx else ""),
            span_id=span_id or (ctx.parent_span_id() if ctx else None),
            type=type_,
            payload=payload or {},
            severity=severity,
            source=source,
        )
        self.record(event)
        return event

    def subscribe(self, listener):
        self._listeners.append(listener)

    def get_events(self, trace_id: str = "", type_: str = "", limit: int = 0) -> list:
        result = self._events
        if trace_id:
            result = [e for e in result if e.trace_id == trace_id]
        if type_:
            result = [e for e in result if e.type == type_]
        result.sort(key=lambda e: e.timestamp)
        if limit > 0:
            result = result[-limit:]
        return result

    def clear(self):
        self._events.clear()

    def __len__(self):
        return len(self._events)
