from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import time


class DevWorkflowStarter:
    """lyme start — daily startup ritual."""

    def run(self, repo_path: str = ".", auto_watch: bool = True):
        repo = Path(repo_path).resolve()
        print(f"{'='*60}")
        print(f"  LYME START — {repo.name}")
        print(f"{'='*60}")

        results = {}
        start = time.time()

        # 1. Check git status
        print(f"\n  1. Git status...", end=" ")
        try:
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo),
            )
            lines = [l for l in status.stdout.splitlines() if l.strip()]
            results["git_status"] = {"uncommitted_changes": len(lines)}
            print(f"{len(lines)} uncommitted changes")
            for l in lines[:5]:
                print(f"     {l}")
        except Exception as e:
            results["git_status"] = {"error": str(e)}
            print(f"error: {e}")

        # 2. Check for open branches
        print(f"\n  2. Branch status...", end=" ")
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            current = branch.stdout.strip()
            ahead = subprocess.run(
                ["git", "rev-list", "--count", f"@{'{u}'}", "HEAD"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            results["branch"] = {"current": current}
            print(f"on '{current}'")
        except Exception as e:
            results["branch"] = {"error": str(e)}
            print(f"error: {e}")

        # 3. Check test status
        print(f"\n  3. Test status...", end=" ")
        try:
            from lyme_model.cli import _detect_test_command
            cmd = _detect_test_command(repo)
            results["tests"] = {"command": cmd or "none"}
            if cmd:
                print(f"'{cmd}'")
            else:
                print(f"no test command detected")
        except Exception as e:
            results["tests"] = {"error": str(e)}
            print(f"error: {e}")

        # 4. Check recent activity
        print(f"\n  4. Recent activity...", end=" ")
        try:
            log = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            commits = [l for l in log.stdout.splitlines() if l.strip()]
            results["recent_commits"] = len(commits)
            print(f"{len(commits)} recent commits")
            for c in commits[:3]:
                print(f"     {c}")
        except Exception as e:
            results["recent_activity"] = {"error": str(e)}
            print(f"error: {e}")

        # 5. Check lyme model server
        print(f"\n  5. Lyme model server...", end=" ")
        try:
            from lyme_model.runtime import server_client
            ok = server_client.health_check()
            results["lyme_server"] = {"running": ok}
            print(f"{'running' if ok else 'not running'}")
        except Exception:
            results["lyme_server"] = {"running": False}
            print(f"not running")

        # 6. Passive intelligence — quick status
        print(f"\n  6. Repo intelligence...", end=" ")
        try:
            from ..intelligence.engine import IntelligenceEngine
            engine = IntelligenceEngine()
            report = engine.run_fast()
            results["intel"] = {"warnings": report.warning_count}
            if report.warning_count > 0:
                print(f"{report.warning_count} warning(s)")
                for line in report.summary.split("\n"):
                    if line.strip():
                        print(f"     {line}")
            else:
                print("all clear")
        except Exception:
            results["intel"] = {"error": True}
            print("check skipped")

        # 7. Session continuity check
        print(f"\n  7. Session continuity...", end=" ")
        try:
            from ..session.recovery import session_recovery
            if session_recovery.needs_resume():
                prompt = session_recovery.get_resume_prompt()
                if prompt:
                    print("unfinished work detected")
                    for line in prompt.split("\n"):
                        print(f"     {line}")
            else:
                print("clean start")
        except Exception:
            print("check skipped")

        elapsed = time.time() - start
        results["elapsed_s"] = round(elapsed, 2)
        print(f"\n{'='*60}")
        print(f"  Start complete in {elapsed:.1f}s")
        print(f"{'='*60}")
        return results


starter = DevWorkflowStarter()
