"""AutoAction — automatic responses to watch events."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ActionType(Enum):
    NOTIFY = "notify"
    AUTO_FIX = "auto_fix"
    CREATE_ISSUE = "create_issue"
    RUN_TESTS = "run_tests"
    LOG = "log"


@dataclass
class AutoAction:
    action_type: ActionType = ActionType.LOG
    description: str = ""
    handler: Optional[Callable] = None
    cooldown_s: int = 300
    _last_run: float = 0.0

    def should_run(self) -> bool:
        import time
        return (time.time() - self._last_run) >= self.cooldown_s

    def execute(self, event: Dict[str, Any]) -> None:
        if not self.should_run():
            return
        if self.handler:
            try:
                self.handler(event)
            except Exception:
                pass
        self._last_run = time.time()
