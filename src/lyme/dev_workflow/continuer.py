from __future__ import annotations
from pathlib import Path
from typing import Optional
from ..session.context import SessionContext
from ..session.timeline import RepoTimeline
from ..session.recovery import SessionRecovery
import json
import time
import subprocess


class TaskContinuer:
    def __init__(self):
        self.context = SessionContext()
        self.timeline = RepoTimeline()
        self.recovery = SessionRecovery()

    def print_status(self):
        session = self.context.current()
        if not session or not self.context.is_active():
            print(f"\n{'='*60}")
            print(f"  CONTINUE")
            print(f"{'='*60}")
            print(f"\n  No active session.")
            print(f"  Run 'lyme start' to begin a new session.")
            print(f"{'='*60}")
            return

        summary = self.context.continuity_summary()
        branch = self._current_branch()
        recovery = self.recovery.recover()
        timeline_summary = self.timeline.summary()

        print(f"\n{'='*60}")
        print(f"  CONTINUE WORK")
        print(f"{'='*60}")

        print(f"\n  {'Session':15s} {summary['session_id']}")
        print(f"  {'Branch':15s} {branch}")
        print(f"  {'Duration':15s} {summary['duration_hours']}h")
        print(f"  {'Commands':15s} {summary['commands_run_count']}")
        print(f"  {'Goals':15s} {summary['goals_completed']}/{summary['goals_total']} completed")

        if recovery["status"] == "interruption_detected":
            interruption = recovery["interruption"]
            print(f"\n  ⚠ INTERRUPTION DETECTED")
            print(f"     Idle: {interruption['idle_minutes']}m")
            if interruption["branch_switched"]:
                print(f"     Branch changed from '{interruption['previous_branch']}'")
                try:
                    git_switch = subprocess.run(
                        ["git", "switch", interruption["previous_branch"]],
                        capture_output=True, text=True, timeout=10,
                    )
                    if git_switch.returncode == 0:
                        branch = interruption["previous_branch"]
                        print(f"     → Auto-switched back to {branch}")
                except Exception:
                    print(f"     → Run 'git switch {interruption['previous_branch']}'")

        active_goal = self.context.active_goal()
        if active_goal:
            print(f"\n  Active Goal: {active_goal.description}")
            print(f"  Progress:    {active_goal.progress_pct():.0f}%")
            next_step = self._next_step(active_goal)
            if next_step:
                print(f"  Next step:   {next_step}")
            if active_goal.steps:
                print(f"\n  Steps:")
                for i, step in enumerate(active_goal.steps, 1):
                    done = step in active_goal.completed_steps
                    prefix = "✓" if done else "○"
                    print(f"    {prefix} {step}")

        unfinished = self.context.unfinished_goals()
        if unfinished and (not active_goal or active_goal not in unfinished):
            print(f"\n  Unfinished goals:")
            for g in unfinished[:3]:
                print(f"    ○ {g.description} ({g.progress_pct():.0f}%)")

        if timeline_summary["today"] > 0:
            print(f"\n  Today: {timeline_summary['today']} events, {timeline_summary['commits']} commits")

        files_modified = self.context.modified_files()
        if files_modified:
            print(f"\n  Files modified this session ({len(files_modified)}):")
            for f in files_modified[:5]:
                print(f"    • {f}")

        print(f"\n  Quick resume:")
        print(f"    lyme continue --status   — show this again")
        print(f"    lyme start               — start fresh session")
        if active_goal:
            print(f"    lyme session goal        — manage goals")
        print(f"{'='*60}")

    def resume(self) -> Optional[str]:
        recovery = self.recovery.recover()
        summary = self.context.continuity_summary()
        active_goal = self.context.active_goal()

        if not summary.get("has_session"):
            return "No active session. Run 'lyme start' to begin."

        if not self.context.is_active():
            return "No active session. Run 'lyme start' to begin."

        has_real_content = (
            summary.get("commands_run_count", 0) > 0
            or summary.get("goals_total", 0) > 0
            or summary.get("files_modified_count", 0) > 0
        )
        if not has_real_content:
            return "No active session. Run 'lyme start' to begin."

        result = []
        if recovery["status"] == "interruption_detected":
            result.append("Resuming interrupted work...")
            interruption = recovery["interruption"]
            result.append(f"Interrupted {interruption['idle_minutes']}m ago")
            self.timeline.record_session_start(branch=summary["branch"])

        if active_goal:
            result.append(f"\nActive goal: {active_goal.description}")
            result.append(f"Progress: {active_goal.progress_pct():.0f}%")
            next_step = self._next_step(active_goal)
            if next_step:
                result.append(f"Next step: {next_step}")
        else:
            unfinished = self.context.unfinished_goals()
            if unfinished:
                result.append(f"\nUnfinished goal: {unfinished[0].description}")

        return "\n".join(result)

    def _next_step(self, goal) -> Optional[str]:
        for step in goal.steps:
            if step not in goal.completed_steps:
                return step
        return None

    def _current_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            return result or "(detached)"
        except Exception:
            return "?"


continuer = TaskContinuer()
