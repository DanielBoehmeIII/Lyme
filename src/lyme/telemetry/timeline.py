import time
from dataclasses import dataclass, field
from typing import List, Optional
from .event_log import Event


@dataclass
class TimelineEvent:
    timestamp: float
    type: str
    label: str
    detail: str = ""
    duration_ms: Optional[float] = None
    status: str = "info"
    depth: int = 0
    event_id: str = ""
    span_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "label": self.label,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "depth": self.depth,
            "event_id": self.event_id,
            "span_id": self.span_id,
            "metadata": self.metadata,
        }


class Timeline:
    def __init__(self):
        self._events: List[TimelineEvent] = []

    def add(self, event: TimelineEvent):
        self._events.append(event)

    def add_from_event(self, event: Event, depth: int = 0):
        self.add(TimelineEvent(
            timestamp=event.timestamp,
            type=event.type,
            label=event.type.replace("_", " ").title(),
            detail=str(event.payload.get("description", "")),
            status="error" if event.severity == "error" else "warning" if event.severity == "warning" else "info",
            depth=depth,
            event_id=event.id,
            span_id=event.span_id or "",
            metadata=event.payload,
        ))

    def add_from_span(self, span, include_children: bool = True, depth: int = 0):
        self.add(TimelineEvent(
            timestamp=span.start_time,
            type="span",
            label=span.name,
            detail=f"category={span.category}, status={span.status}",
            duration_ms=span.duration_ms,
            status=span.status,
            depth=depth,
            span_id=span.id,
        ))

    def get_events(self, type_: str = "") -> List[TimelineEvent]:
        result = sorted(self._events, key=lambda e: e.timestamp)
        if type_:
            result = [e for e in result if e.type == type_]
        return result

    def to_dict(self) -> list:
        return [e.to_dict() for e in sorted(self._events, key=lambda e: e.timestamp)]

    def clear(self):
        self._events.clear()

    def __len__(self):
        return len(self._events)
