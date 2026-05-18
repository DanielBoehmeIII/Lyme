from __future__ import annotations
from pathlib import Path
import subprocess
import json


class TerminalDashboard:
    """Compact terminal dashboard showing everything at a glance."""

    def render(self, repo_path: str = "."):
        repo = Path(repo_path).resolve()
        print(f"\n{'='*60}")
        print(f"  📊 LYME DASHBOARD — {repo.name}")
        print(f"{'='*60}")

        data = {}

        # Git status
        try:
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            lines = [l for l in status.stdout.splitlines() if l.strip()]
            data["uncommitted"] = len(lines)
        except Exception:
            data["uncommitted"] = "?"

        # Branch
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            ).stdout.strip()
            data["branch"] = branch or "(detached)"
        except Exception:
            data["branch"] = "?"

        # Recent commits
        try:
            log = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            commits = [l.strip() for l in log.stdout.splitlines() if l.strip()]
            data["recent_commits"] = commits
        except Exception:
            data["recent_commits"] = []

        # Test status
        try:
            test = subprocess.run(
                ["python3", "-m", "pytest", "--co", "-q", "--tb=no"],
                capture_output=True, text=True, timeout=30, cwd=str(repo),
            )
            data["tests"] = "pass" if test.returncode == 0 else "fail"
        except Exception:
            data["tests"] = "?"

        # Lyme model server
        try:
            from lyme_model.runtime import server_client
            data["model_server"] = "running" if server_client.health_check() else "stopped"
        except Exception:
            data["model_server"] = "?"

        # Dogfood report
        df_path = Path("lyme-output") / "dogfood" / "dogfood-report.json"
        if df_path.exists():
            try:
                df = json.loads(df_path.read_text())
                t = df.get("totals", {})
                data["dogfood_score"] = t.get("daily_score", "?")
            except Exception:
                pass

        # Render dashboard
        print(f"\n  {'Status':15s} {'Value'}")
        sep = "─" * 14
        sep2 = "─" * 30
        print(f"  {sep:15s} {sep2}")

        branch_display = data.get("branch", "?")
        uncommitted = data.get("uncommitted", "?")
        tests = data.get("tests", "?")
        model_server = data.get("model_server", "?")
        score = data.get("dogfood_score", "N/A")

        print(f"  {'Branch':15s} {branch_display}")
        print(f"  {'Uncommitted':15s} {uncommitted} files")
        print(f"  {'Tests':15s} {'✓ pass' if tests == 'pass' else '✗ fail' if tests == 'fail' else '?'}")
        print(f"  {'Model server':15s} {'✓' if model_server == 'running' else '✗' if model_server == 'stopped' else '?'}")
        if score != "N/A":
            print(f"  {'Dogfood score':15s} {score:.0%}")

        if data.get("recent_commits"):
            print(f"\n  Recent commits:")
            for c in data["recent_commits"][:3]:
                print(f"    {c}")

        # Prompt
        print(f"\n  Quick actions:")
        print(f"    lyme start          — daily startup")
        print(f"    lyme inbox          — pending tasks")
        print(f"    lyme diff-explain   — explain changes")
        print(f"    lyme branch-review  — review current branch")
        print(f"    lyme continue       — resume last task")
        print(f"    lyme suggest        — contextual suggestions")
        print(f"{'='*60}")


dashboard = TerminalDashboard()
