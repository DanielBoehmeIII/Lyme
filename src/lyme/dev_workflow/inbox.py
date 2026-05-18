from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional
import json
import time


class TaskInbox:
    """Show pending tasks from saved dogfood reports, failed tests, etc."""

    def __init__(self):
        self.inbox_dir = Path("lyme-output")

    def scan(self, repo_path: str = ".") -> List[Dict]:
        tasks = []

        # Check lyme run history
        runs_dir = Path(".lyme") / "model-runs"
        if runs_dir.exists():
            for f in sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text())
                        tasks.append({
                            "type": "previous_run",
                            "file": f.name,
                            "summary": str(data)[:100],
                            "time": f.stat().st_mtime,
                        })
                    except Exception:
                        pass

        # Check test failures
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True, text=True, timeout=15, cwd=repo_path,
            )
            if "error" in result.stderr.lower() or "failed" in result.stderr.lower():
                tasks.append({
                    "type": "test_issue",
                    "summary": "Test collection has errors",
                    "detail": result.stderr[:200],
                })
        except Exception:
            pass

        # Check git status for uncommitted work
        try:
            import subprocess
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=5, cwd=repo_path,
            )
            lines = [l for l in status.stdout.splitlines() if l.strip()]
            if lines:
                tasks.append({
                    "type": "uncommitted_changes",
                    "count": len(lines),
                    "summary": f"{len(lines)} uncommitted files",
                })
        except Exception:
            pass

        # Check recent dogfood report for suggestions
        df_path = self.inbox_dir / "dogfood" / "dogfood-report.json"
        if df_path.exists():
            try:
                df = json.loads(df_path.read_text())
                for repo_name, assessment in df.get("repos", {}).items():
                    for suggestion in assessment.get("improvement_suggestions", [])[:2]:
                        tasks.append({
                            "type": "improvement",
                            "repo": repo_name,
                            "summary": suggestion,
                        })
            except Exception:
                pass

        return tasks

    def print_inbox(self, tasks: List[Dict]):
        print(f"{'='*60}")
        print(f"  TASK INBOX")
        print(f"{'='*60}")
        if not tasks:
            print(f"\n  No pending tasks. All clear.")
            print(f"{'='*60}")
            return
        for i, task in enumerate(tasks, 1):
            ttype = task.get("type", "unknown")
            summary = task.get("summary", "")[:80]
            print(f"\n  [{i}] {ttype}:")
            print(f"      {summary}")


inbox = TaskInbox()
