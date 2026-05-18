from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import subprocess


class BranchReviewer:
    """Review current branch for issues before PR."""

    def review(self, repo_path: str = ".") -> Dict:
        repo = Path(repo_path).resolve()
        issues = []
        suggestions = []

        # 1. Check branch name
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            ).stdout.strip()
            if branch == "main" or branch == "master":
                issues.append("Working on main/master — should create a feature branch")
            elif not branch:
                issues.append("Detached HEAD — not on any branch")
        except Exception:
            pass

        # 2. Check for large diffs
        try:
            diff_stat = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, timeout=10, cwd=str(repo),
            )
            if diff_stat.stdout.strip():
                lines = diff_stat.stdout.strip().split("\n")
                total_insertions = sum(int(s.split()[3]) for s in lines if "insertion" in s) if lines else 0
                if total_insertions > 200:
                    suggestions.append(f"Large diff ({total_insertions}+ insertions) — consider smaller PRs")
        except Exception:
            pass

        # 3. Check for TODO/FIXME
        try:
            diff = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True, timeout=10, cwd=str(repo),
            )
            if "TODO" in diff.stdout:
                issues.append("Diff contains TODO markers — address before PR")
            if "FIXME" in diff.stdout:
                issues.append("Diff contains FIXME markers — fix before commit")
            if "print(" in diff.stdout or "console.log" in diff.stdout:
                suggestions.append("Remove debug print/console.log statements before PR")
        except Exception:
            pass

        # 4. Check for untracked files
        try:
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=5, cwd=str(repo),
            )
            untracked = [l for l in status.stdout.splitlines() if l.startswith("??")]
            if untracked:
                suggestions.append(f"{len(untracked)} untracked files — add to .gitignore or commit")
        except Exception:
            pass

        # 5. Check test status
        try:
            test = subprocess.run(
                ["python3", "-m", "pytest", "--co", "-q"],
                capture_output=True, text=True, timeout=30, cwd=str(repo),
            )
            if test.returncode != 0:
                issues.append("Test collection has errors")
            else:
                suggestions.append("Tests collected successfully")
        except Exception:
            pass

        return {
            "issues": issues,
            "suggestions": suggestions,
            "issue_count": len(issues),
            "suggestion_count": len(suggestions),
            "verdict": "Needs work" if issues else "Ready for PR" if not suggestions else "Ready with suggestions",
        }

    def print_review(self, review: Dict):
        print(f"{'='*60}")
        print(f"  BRANCH REVIEW")
        print(f"{'='*60}")
        print(f"  Verdict: {review['verdict']}")
        if review['issues']:
            print(f"\n  Issues:")
            for i in review['issues']:
                print(f"    ✗ {i}")
        if review['suggestions']:
            print(f"\n  Suggestions:")
            for s in review['suggestions']:
                print(f"    → {s}")
        if not review['issues'] and not review['suggestions']:
            print(f"\n  No issues found. Branch is clean.")
        print(f"{'='*60}")


reviewer = BranchReviewer()
