"""DaemonScheduler — schedules periodic maintenance tasks."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ScheduledTask:
    name: str = ""
    interval_s: int = 3600
    handler: Optional[Callable] = None
    _last_run: float = 0.0

    @property
    def due(self) -> bool:
        return (time.time() - self._last_run) >= self.interval_s

    def run(self) -> None:
        if self.handler:
            try:
                self.handler()
            except Exception:
                pass
        self._last_run = time.time()


class DaemonScheduler:
    def __init__(self):
        self._tasks: List[ScheduledTask] = []

    def add(self, task: ScheduledTask) -> None:
        self._tasks.append(task)

    def tick(self) -> List[str]:
        ran = []
        for task in self._tasks:
            if task.due:
                task.run()
                ran.append(task.name)
        return ran

    def run_forever(self, tick_interval_s: int = 10) -> None:
        while True:
            self.tick()
            time.sleep(tick_interval_s)
