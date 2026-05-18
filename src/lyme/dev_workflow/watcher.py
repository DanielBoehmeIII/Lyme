from __future__ import annotations
from pathlib import Path
from typing import Set, Optional
import time
import subprocess


class RepoWatcher:
    """Watch repo for file changes and report what changed."""

    def __init__(self):
        self._known_files: Set[str] = set()
        self._last_check: float = 0

    def scan(self, repo_path: str = ".") -> dict:
        repo = Path(repo_path).resolve()
        changes = {"new_files": [], "modified_files": [], "deleted_files": []}

        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo),
            )
            for line in status.stdout.splitlines():
                if not line.strip():
                    continue
                xy = line[:2]
                filepath = line[3:].strip()
                if xy == "??":
                    changes["new_files"].append(filepath)
                elif xy in (" M", "MM"):
                    changes["modified_files"].append(filepath)
        except Exception as e:
            return {"error": str(e)}

        status = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10, cwd=str(repo),
        )
        changes["diff_summary"] = status.stdout.strip()
        try:
            log = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            changes["recent_commits"] = [l.strip() for l in log.stdout.splitlines() if l.strip()]
        except Exception:
            changes["recent_commits"] = []

        changes["total_changes"] = len(changes["new_files"]) + len(changes["modified_files"])
        return changes

    def print_changes(self, changes: dict):
        total = changes.get("total_changes", 0)
        print(f"\n  Repo changes: {total}")
        for kind, items in [("New", changes.get("new_files", [])), ("Modified", changes.get("modified_files", []))]:
            for f in items[:10]:
                print(f"    [{kind}] {f}")
        if changes.get("diff_summary"):
            print(f"\n  Diff stats:")
            for line in changes["diff_summary"].split("\n")[:5]:
                print(f"    {line}")


watcher = RepoWatcher()
