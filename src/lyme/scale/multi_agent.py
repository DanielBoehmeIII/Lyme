"""MultiAgentStress — stress tests with concurrent agents."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class StressConfig:
    agent_count: int = 5
    tasks_per_agent: int = 10
    concurrency: bool = True
    timeout_s: int = 60


@dataclass
class MultiAgentStress:
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    total_duration_s: float = 0.0
    avg_task_duration_s: float = 0.0
    conflict_count: int = 0
    passed: bool = False

    @property
    def success_rate(self) -> float:
        return self.completed / max(self.total_tasks, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 4),
            "duration_s": round(self.total_duration_s, 2),
            "avg_task_s": round(self.avg_task_duration_s, 2),
            "conflicts": self.conflict_count,
        }


class MultiAgentStressRunner:
    def run(self, config: StressConfig, agent_fn: Callable) -> MultiAgentStress:
        start = time.time()
        result = MultiAgentStress()

        for ai in range(config.agent_count):
            for ti in range(config.tasks_per_agent):
                result.total_tasks += 1
                try:
                    agent_fn(f"task_{ai}_{ti}")
                    result.completed += 1
                except Exception:
                    result.failed += 1

        result.total_duration_s = time.time() - start
        result.avg_task_duration_s = result.total_duration_s / max(result.total_tasks, 1)
        result.passed = result.success_rate > 0.8
        return result
