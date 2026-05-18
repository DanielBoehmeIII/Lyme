"""ContinuousExecutor — sustained execution over long periods."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ExecutionBatch:
    batch_id: int = 0
    task_count: int = 0
    duration_s: float = 0.0
    success_count: int = 0
    fail_count: int = 0

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.task_count, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "tasks": self.task_count,
            "duration_s": round(self.duration_s, 2),
            "success_rate": round(self.success_rate, 4),
        }


class ContinuousExecutor:
    def __init__(self):
        self._batches: List[ExecutionBatch] = []

    def run(self, task_fn: Callable, total_tasks: int = 100,
            batch_size: int = 10) -> List[ExecutionBatch]:
        for batch_id in range(0, total_tasks, batch_size):
            start = time.time()
            batch = ExecutionBatch(batch_id=batch_id)

            for ti in range(batch_size):
                batch.task_count += 1
                try:
                    task_fn(f"continuous_task_{batch_id}_{ti}")
                    batch.success_count += 1
                except Exception:
                    batch.fail_count += 1

            batch.duration_s = time.time() - start
            self._batches.append(batch)

        return self._batches

    def stats(self) -> Dict[str, Any]:
        return {
            "batches": len(self._batches),
            "total_tasks": sum(b.task_count for b in self._batches),
            "total_duration_s": round(sum(b.duration_s for b in self._batches), 2),
            "avg_success_rate": sum(b.success_rate for b in self._batches) / max(len(self._batches), 1),
        }
