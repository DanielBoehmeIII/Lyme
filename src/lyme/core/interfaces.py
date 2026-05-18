"""Core interfaces — base types for all Lyme components."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


AgentID = str
RunID = str
TraceID = str


class ComponentStatus(Enum):
    UNINITIALIZED = auto()
    INITIALIZED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()


class TaskStatus(Enum):
    PENDING = auto()
    PLANNING = auto()
    EXECUTING = auto()
    VALIDATING = auto()
    SUCCESS = auto()
    FAILED = auto()
    RETRYING = auto()
    CANCELLED = auto()


@dataclass
class Task:
    id: str
    description: str
    repo_path: Optional[str] = None
    files: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    patches: List[Dict[str, Any]] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    reasoning_log: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    completed_at: Optional[datetime] = None


@runtime_checkable
class LymeComponent(Protocol):
    name: str
    version: str
    status: ComponentStatus

    def initialize(self) -> None: ...
    def shutdown(self) -> None: ...


@runtime_checkable
class Configurable(Protocol):
    def load_config(self, path: str) -> None: ...
    def get_config(self) -> Dict[str, Any]: ...


@runtime_checkable
class Runnable(Protocol):
    def run(self, task: Task) -> TaskResult: ...


@runtime_checkable
class Stoppable(Protocol):
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...


@runtime_checkable
class HasMetrics(Protocol):
    def get_metrics(self) -> Dict[str, float]: ...


@runtime_checkable
class HasStatus(Protocol):
    def get_status(self) -> ComponentStatus: ...
