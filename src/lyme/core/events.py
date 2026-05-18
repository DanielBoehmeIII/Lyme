"""Event bus — lightweight pub/sub for cross-layer communication."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SystemEventType(Enum):
    TASK_CREATED = "task.created"
    TASK_PLANNED = "task.planned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRYING = "task.retrying"
    MODEL_LOADED = "model.loaded"
    MODEL_UNLOADED = "model.unloaded"
    MEMORY_UPDATED = "memory.updated"
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"
    PATCH_APPLIED = "patch.applied"
    PATCH_ROLLED_BACK = "patch.rolled_back"
    PLUGIN_ACTIVATED = "plugin.activated"
    PLUGIN_DEACTIVATED = "plugin.deactivated"
    ERROR = "system.error"
    WARNING = "system.warning"
    INFO = "system.info"


@dataclass
class Event:
    type: SystemEventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
        }


EventHandler = Callable[[Event], None]


class EventBus:
    _handlers: Dict[SystemEventType, List[EventHandler]] = {}
    _history: List[Event] = []
    _max_history: int = 1000

    @classmethod
    def subscribe(cls, event_type: SystemEventType, handler: EventHandler) -> None:
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    def unsubscribe(cls, event_type: SystemEventType, handler: EventHandler) -> None:
        if event_type in cls._handlers:
            cls._handlers[event_type] = [
                h for h in cls._handlers[event_type] if h != handler
            ]

    @classmethod
    def publish(cls, event: Event) -> None:
        cls._history.append(event)
        if len(cls._history) > cls._max_history:
            cls._history = cls._history[-cls._max_history:]

        for handler in cls._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception:
                pass

    @classmethod
    def publish_simple(cls, event_type: SystemEventType, data: Dict[str, Any] = None) -> None:
        cls.publish(Event(type=event_type, data=data or {}))

    @classmethod
    def history(cls, limit: int = 50, event_type: Optional[SystemEventType] = None) -> List[Event]:
        events = cls._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    @classmethod
    def clear(cls) -> None:
        cls._handlers.clear()
        cls._history.clear()
