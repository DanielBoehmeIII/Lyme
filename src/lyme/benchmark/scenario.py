import os
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from abc import ABC, abstractmethod


@dataclass
class ScenarioResult:
    scenario_name: str
    success: bool = False
    duration_ms: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    events_count: int = 0
    tool_calls_count: int = 0
    files_created: int = 0
    files_modified: int = 0
    diff_fidelity: float = 0.0
    hallucination_count: int = 0
    repair_attempts: int = 0
    repair_successes: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    context_windows_used: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
            "errors": self.errors,
            "events_count": self.events_count,
            "tool_calls_count": self.tool_calls_count,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "diff_fidelity": self.diff_fidelity,
            "hallucination_count": self.hallucination_count,
            "repair_attempts": self.repair_attempts,
            "repair_successes": self.repair_successes,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "context_windows_used": self.context_windows_used,
            "metadata": self.metadata,
        }


class BenchmarkScenario(ABC):
    def __init__(self):
        self._id = uuid.uuid4().hex[:8]

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        ...

    @property
    def description(self) -> str:
        return ""

    @property
    def difficulty(self) -> float:
        return 0.5

    @property
    def tags(self) -> list:
        return []

    @property
    def timeout_s(self) -> int:
        return 120

    @abstractmethod
    def setup(self, work_dir: Path) -> dict:
        ...

    @abstractmethod
    def task_prompt(self, context: dict) -> str:
        ...

    @abstractmethod
    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        ...

    def teardown(self, work_dir: Path, context: dict):
        pass

    def create_work_dir(self, base_dir: str = "") -> Path:
        if base_dir:
            path = Path(base_dir) / f"scenario-{self._id}"
        else:
            path = Path(tempfile.mkdtemp(prefix=f"lyme-{self.name}-"))
        path.mkdir(parents=True, exist_ok=True)
        return path
