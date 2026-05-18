from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import time
import platform
import subprocess


class BugReportGenerator:
    """Auto-generate a comprehensive bug report with system context."""

    REPORT_DIR = Path(".lyme") / "beta" / "bug-reports"

    def __init__(self):
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, description: str, steps: str, expected: str,
                 actual: str, user_id: str = "anonymous") -> dict:
        report = {
            "title": description[:80],
            "description": description,
            "steps_to_reproduce": steps,
            "expected_behavior": expected,
            "actual_behavior": actual,
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system": self._get_system_info(),
            "lyme_version": self._get_lyme_version(),
            "git_info": self._get_git_info(),
            "id": f"BUG-{int(time.time())}",
        }

        path = self.REPORT_DIR / f"{report['id']}.json"
        path.write_text(json.dumps(report, indent=2))
        print(f"  Bug report saved: {path}")
        return report

    def _get_system_info(self) -> dict:
        info = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "architecture": platform.machine(),
        }
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info["gpu"] = result.stdout.strip()
        except Exception:
            pass
        return info

    def _get_lyme_version(self) -> str:
        try:
            import lyme
            return getattr(lyme, "__version__", "unknown")
        except Exception:
            return "unknown"

    def _get_git_info(self) -> dict:
        try:
            git_log = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                capture_output=True, text=True, timeout=5,
            )
            git_diff = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, timeout=5,
            )
            git_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
            )
            return {
                "branch": git_branch.stdout.strip(),
                "recent_commits": git_log.stdout.strip(),
                "uncommitted_diff": git_diff.stdout.strip()[:500],
            }
        except Exception:
            return {"error": "could not get git info"}


bug_report_gen = BugReportGenerator()
