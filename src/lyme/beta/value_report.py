from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import time


class WeeklyValueReport:
    """Weekly user value report — what did Lyme do for you this week?"""

    REPORT_DIR = Path(".lyme") / "beta" / "weekly-reports"

    def __init__(self):
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self) -> dict:
        report = {
            "week_ending": time.strftime("%Y-%m-%d"),
            "total_commands_run": self._count_commands(),
            "dogfood_runs": self._count_dogfood_runs(),
            "questions_asked": self._count_questions(),
            "bugs_filed": self._count_bugs(),
            "feedback_given": self._count_feedback(),
            "model_runs": self._count_model_runs(),
            "time_saved_estimate_minutes": self._estimate_time_saved(),
        }

        path = self.REPORT_DIR / f"week-{report['week_ending']}.json"
        path.write_text(json.dumps(report, indent=2))
        return report

    def _count_commands(self) -> int:
        telemetry_dir = Path(".lyme") / "telemetry"
        if not telemetry_dir.exists():
            return 0
        return sum(1 for d in telemetry_dir.iterdir() if d.is_dir() for _ in d.glob("*.json"))

    def _count_dogfood_runs(self) -> int:
        df = Path("lyme-output") / "dogfood" / "dogfood-report.json"
        return 1 if df.exists() else 0

    def _count_questions(self) -> int:
        qa_dir = Path("lyme-output")
        return len(list(qa_dir.glob("qa-benchmark*"))) if qa_dir.exists() else 0

    def _count_bugs(self) -> int:
        bug_dir = Path(".lyme") / "beta" / "bug-reports"
        return len(list(bug_dir.glob("*.json"))) if bug_dir.exists() else 0

    def _count_feedback(self) -> int:
        fb_dir = Path(".lyme") / "beta" / "feedback"
        return len(list(fb_dir.glob("*.json"))) if fb_dir.exists() else 0

    def _count_model_runs(self) -> int:
        runs_dir = Path(".lyme") / "model-runs"
        return len(list(runs_dir.glob("*.json"))) if runs_dir.exists() else 0

    def _estimate_time_saved(self) -> float:
        total = self._count_commands()
        return total * 2  # rough estimate: 2 minutes saved per command

    def print_report(self, report: dict):
        print(f"{'='*60}")
        print(f"  WEEKLY VALUE REPORT")
        print(f"{'='*60}")
        print(f"  Week ending: {report['week_ending']}")
        print(f"  Commands run:     {report['total_commands_run']}")
        print(f"  Dogfood runs:     {report['dogfood_runs']}")
        print(f"  Questions asked:  {report['questions_asked']}")
        print(f"  Bugs filed:       {report['bugs_filed']}")
        print(f"  Feedback given:   {report['feedback_given']}")
        print(f"  Model runs:       {report['model_runs']}")
        print(f"  Estimated time saved: {report['time_saved_estimate_minutes']} min")
        print(f"{'='*60}")


weekly_report = WeeklyValueReport()
