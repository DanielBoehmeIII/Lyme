from __future__ import annotations
from pathlib import Path
from typing import Optional
import subprocess


class DiffExplainer:
    """Explain recent diff in natural language."""

    def get_recent_diff(self, repo_path: str = ".", lines: int = 50) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "diff", f"-U{lines}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo_path),
            )
            if result.stdout.strip():
                return result.stdout
            result = subprocess.run(
                ["git", "diff", "--cached", f"-U{lines}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo_path),
            )
            return result.stdout if result.stdout.strip() else None
        except Exception:
            return None

    def get_last_commit_diff(self, repo_path: str = ".") -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo_path),
            )
            return result.stdout if result.stdout.strip() else None
        except Exception:
            return None

    def classify_diff(self, diff: str) -> str:
        if not diff:
            return "no changes"
        if "test" in diff.lower() and ("def test" in diff or "describe(" in diff):
            return "test changes"
        if "import" in diff:
            return "dependency changes"
        if "def " in diff or "function " in diff:
            return "behavior changes"
        if "class " in diff:
            return "structural changes"
        if "TODO" in diff or "FIXME" in diff or "HACK" in diff:
            return "maintenance markers"
        if "print" in diff or "logger" in diff or "debug" in diff:
            return "debug/logging changes"
        if ".md" in diff[:200] or "#" in diff[:200]:
            return "documentation changes"
        return "unknown"

    def summarize(self, repo_path: str = ".") -> dict:
        diff = self.get_recent_diff(repo_path)
        last_commit = self.get_last_commit_diff(repo_path)

        classification = self.classify_diff(diff or "")
        files_changed = "unknown"
        if diff:
            files = [l for l in diff.split("\n") if l.startswith("+++ ") or l.startswith("--- ")]
            files_changed = str(len([f for f in files if "+++" in f]))

        return {
            "has_uncommitted_changes": diff is not None and bool(diff.strip()),
            "classification": classification,
            "files_changed": files_changed,
            "diff_size_chars": len(diff) if diff else 0,
            "last_commit_diff_chars": len(last_commit) if last_commit else 0,
        }

    def print_summary(self, repo_path: str = "."):
        s = self.summarize(repo_path)
        print(f"{'='*60}")
        print(f"  DIFF EXPLAINER")
        print(f"{'='*60}")
        print(f"  Uncommitted changes: {'Yes' if s['has_uncommitted_changes'] else 'No'}")
        print(f"  Classification:      {s['classification']}")
        print(f"  Files changed:       {s['files_changed']}")
        print(f"  Diff size:           {s['diff_size_chars']} chars")
        if s['has_uncommitted_changes']:
            print(f"\n  Summary: There are uncommitted {s['classification']} in the working directory.")
        else:
            print(f"\n  Summary: Working directory is clean.")

        diff = self.get_recent_diff()
        if diff:
            lines = diff.split("\n")
            print(f"\n  Diff preview (first 10 lines):")
            for line in lines[:10]:
                marker = "+" if line.startswith("+") else "-" if line.startswith("-") else " "
                print(f"    {marker} {line[1:80]}")
        print(f"{'='*60}")


explainer = DiffExplainer()
