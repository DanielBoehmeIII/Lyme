from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import PersonalMetrics
from .report import ImpactReport


class ImpactEngine:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()

    def calculate(self) -> PersonalMetrics:
        metrics = PersonalMetrics()

        # Aggregate from session context
        try:
            from ..session.context import session_context
            summary = session_context.continuity_summary()
            metrics.total_commands = summary.get("commands_run_count", 0)
            metrics.goals_completed = summary.get("goals_completed", 0)
            metrics.sessions_completed = 1 if summary.get("has_session") else 0
        except Exception:
            pass

        # Aggregate from session history
        try:
            sessions = session_context.list_sessions(limit=100)
            metrics.sessions_completed = len(sessions)
            for s in sessions:
                metrics.commands_run += s.get("commands", 0)
        except Exception:
            pass

        # Aggregate from intelligence
        try:
            intel_path = self._repo / ".lyme" / "intel"
            if intel_path.exists():
                reports_dir = intel_path / "reports"
                if reports_dir.exists():
                    for r_path in reports_dir.glob("report_*.json"):
                        try:
                            data = json.loads(r_path.read_text())
                            if data.get("drift"):
                                metrics.drift_violations_detected += data["drift"].get("total_drift", 0)
                            if data.get("suspicious"):
                                metrics.suspicious_commits_caught += data["suspicious"].get("suspicious_count", 0)
                            if data.get("debt"):
                                metrics.debt_items_surfaced += data["debt"].get("total_debt", 0)
                            if data.get("flaky"):
                                metrics.flaky_tests_identified += data["flaky"].get("flaky_count", 0)
                            metrics.total_warnings_generated += data.get("warning_count", 0)
                        except Exception:
                            pass
        except Exception:
            pass

        # Aggregate from rhythm
        try:
            rhythm_path = self._repo / ".lyme" / "rhythm"
            if rhythm_path.exists():
                profile_path = rhythm_path / "profile.json"
                if profile_path.exists():
                    profile = json.loads(profile_path.read_text())
                    uptime_days = 0
                    if "last_updated" in profile:
                        uptime_days = (time.time() - profile["last_updated"]) / 86400
                    metrics.uptime_days = uptime_days
        except Exception:
            pass

        # Calculate time saved
        # Average: each command takes ~30s to type and run manually
        # Each warning saves ~5min of debugging
        # Each caught suspicious commit saves ~15min
        # Each flaky test identified saves ~10min
        # Each drift violation saves ~20min
        avg_command_time_s = 30
        debug_time_per_warning_min = 5
        suspicious_commit_time_min = 15
        flaky_test_time_min = 10
        drift_time_min = 20
        debt_time_min = 3

        metrics.commands_automated = max(1, metrics.total_commands // 3)

        time_saved = (
            metrics.commands_automated * avg_command_time_s / 60
            + metrics.total_warnings_generated * debug_time_per_warning_min
            + metrics.suspicious_commits_caught * suspicious_commit_time_min
            + metrics.flaky_tests_identified * flaky_test_time_min
            + metrics.drift_violations_detected * drift_time_min
            + metrics.debt_items_surfaced * debt_time_min
        )
        metrics.estimated_time_saved_min = time_saved

        # Cost saved: developer time * hourly rate
        dev_hourly_rate = 100.0
        metrics.estimated_cost_saved = (time_saved / 60) * dev_hourly_rate

        return metrics

    def generate_report(self) -> ImpactReport:
        metrics = self.calculate()
        return ImpactReport(metrics=metrics)
