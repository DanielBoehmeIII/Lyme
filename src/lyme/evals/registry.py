"""EvalRegistry — centralized registry for evaluation tasks and suites."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EvalStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class EvalTask:
    id: str
    name: str
    description: str
    category: str = "general"
    difficulty: float = 0.5
    requirements: Dict[str, Any] = field(default_factory=dict)
    setup: Optional[Callable] = None
    run: Optional[Callable] = None
    validate: Optional[Callable] = None
    teardown: Optional[Callable] = None


@dataclass
class EvalResult:
    task_id: str
    status: EvalStatus
    score: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "score": self.score,
            "metrics": self.metrics,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class EvalSuite:
    name: str
    description: str
    tasks: List[EvalTask] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def add_task(self, task: EvalTask) -> None:
        self.tasks.append(task)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "task_count": len(self.tasks),
            "tags": self.tags,
        }


class EvalRegistry:
    _tasks: Dict[str, EvalTask] = {}
    _suites: Dict[str, EvalSuite] = {}
    _results: Dict[str, List[EvalResult]] = {}

    @classmethod
    def register_task(cls, task: EvalTask) -> None:
        cls._tasks[task.id] = task

    @classmethod
    def register_suite(cls, suite: EvalSuite) -> None:
        cls._suites[suite.name] = suite
        for task in suite.tasks:
            cls.register_task(task)

    @classmethod
    def get_task(cls, task_id: str) -> Optional[EvalTask]:
        return cls._tasks.get(task_id)

    @classmethod
    def get_suite(cls, name: str) -> Optional[EvalSuite]:
        return cls._suites.get(name)

    @classmethod
    def list_tasks(cls, category: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = cls._tasks.values()
        if category:
            tasks = [t for t in tasks if t.category == category]
        return [{"id": t.id, "name": t.name, "category": t.category, "difficulty": t.difficulty}
                for t in sorted(tasks, key=lambda t: t.id)]

    @classmethod
    def list_suites(cls) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in cls._suites.values()]

    @classmethod
    def record_result(cls, task_id: str, result: EvalResult) -> None:
        if task_id not in cls._results:
            cls._results[task_id] = []
        cls._results[task_id].append(result)

    @classmethod
    def get_results(cls, task_id: str) -> List[EvalResult]:
        return cls._results.get(task_id, [])

    @classmethod
    def clear(cls) -> None:
        cls._tasks.clear()
        cls._suites.clear()
        cls._results.clear()
