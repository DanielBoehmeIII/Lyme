import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Span:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    category: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "pending"  # pending, running, success, failure, error, abandoned
    metadata: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
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
            "metadata": self.metadata,
            "tags": self.tags,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Span":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
