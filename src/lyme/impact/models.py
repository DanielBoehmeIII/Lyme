from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PersonalMetrics:
    total_commands: int = 0
    commands_automated: int = 0
    sessions_completed: int = 0
    goals_completed: int = 0
    bugs_prevented: int = 0
    suspicious_commits_caught: int = 0
    debt_items_surfaced: int = 0
    flaky_tests_identified: int = 0
    drift_violations_detected: int = 0
    total_warnings_generated: int = 0
    estimated_time_saved_min: float = 0.0
    estimated_cost_saved: float = 0.0
    commands_run: int = 0
    uptime_days: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_commands": self.total_commands,
            "commands_automated": self.commands_automated,
            "sessions_completed": self.sessions_completed,
            "goals_completed": self.goals_completed,
            "bugs_prevented": self.bugs_prevented,
            "suspicious_commits_caught": self.suspicious_commits_caught,
            "debt_items_surfaced": self.debt_items_surfaced,
            "flaky_tests_identified": self.flaky_tests_identified,
            "drift_violations_detected": self.drift_violations_detected,
            "total_warnings_generated": self.total_warnings_generated,
            "estimated_time_saved_min": round(self.estimated_time_saved_min, 1),
            "estimated_cost_saved": round(self.estimated_cost_saved, 2),
            "commands_run": self.commands_run,
            "uptime_days": round(self.uptime_days, 1),
        }
