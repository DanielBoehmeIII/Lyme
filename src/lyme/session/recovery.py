from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .context import SessionContext, Goal
from .timeline import RepoTimeline
import subprocess
import time


class SessionRecovery:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self.context = SessionContext(str(self._repo))
        self.timeline = RepoTimeline(str(self._repo))

    def detect_interruption(self) -> Optional[Dict[str, Any]]:
        session = self.context.current()
        if not session:
            return None

        goals = self.context.unfinished_goals()
        if not goals:
            return None

        goal = goals[0]
        idle_minutes = (time.time() - goal.updated_at) / 60

        if idle_minutes < 1:
            return None

        branch_switched = self._branch_changed(session.branch)

        return {
            "interrupted": True,
            "idle_minutes": round(idle_minutes, 1),
            "branch_switched": branch_switched,
            "previous_branch": session.branch,
            "goal": goal.to_dict(),
            "progress_pct": goal.progress_pct(),
            "next_step": self._next_step(goal),
        }

    def recover(self) -> Dict[str, Any]:
        interruption = self.detect_interruption()
        if not interruption:
            return {"status": "no_interruption"}

        self.timeline.record_interruption(
            f"Interrupted after {interruption['idle_minutes']}m on {interruption['goal']['description'][:80]}",
            branch=interruption["previous_branch"],
        )

        return {
            "status": "interruption_detected",
            "interruption": interruption,
            "resume_command": self._resume_command(interruption),
        }

    def _branch_changed(self, expected_branch: str) -> bool:
        if not expected_branch:
            return False
        try:
            current = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self._repo),
            ).stdout.strip()
            return current != expected_branch
        except Exception:
            return False

    def _next_step(self, goal: Goal) -> Optional[str]:
        for step in goal.steps:
            if step not in goal.completed_steps:
                return step
        return None

    def _resume_command(self, interruption: Dict[str, Any]) -> str:
        goal = interruption.get("goal", {})
        return f"lyme continue"

    def needs_resume(self) -> bool:
        session = self.context.current()
        if not session:
            return False
        if session.end_time is not None:
            return False
        goals = self.context.unfinished_goals()
        if not goals:
            return False
        idle = (time.time() - goals[0].updated_at) / 60
        return idle > 5

    def get_resume_prompt(self) -> Optional[str]:
        if not self.needs_resume():
            return None
        interruption = self.detect_interruption()
        if not interruption:
            return None
        goal = interruption["goal"]
        next_step = interruption["next_step"]
        idle = interruption["idle_minutes"]

        lines = [
            f"Interrupted {idle:.0f} minutes ago.",
            f"Goal: {goal['description']}",
            f"Progress: {goal['progress_pct']:.0f}%",
        ]
        if next_step:
            lines.append(f"Next: {next_step}")
        if interruption["branch_switched"]:
            lines.append(f"Note: Branch changed from '{interruption['previous_branch']}'")
        lines.append(f"Run `lyme continue` to resume.")
        return "\n".join(lines)


session_recovery = SessionRecovery()
