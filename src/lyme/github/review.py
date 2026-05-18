"""AutoReviewer — automated PR review with inline comments."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ReviewComment:
    file_path: str = ""
    line: int = 0
    body: str = ""
    severity: str = "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line,
            "body": self.body[:200],
            "severity": self.severity,
        }


@dataclass
class ReviewResult:
    pr_number: int = 0
    summary: str = ""
    comments: List[ReviewComment] = field(default_factory=list)
    approval: str = "pending"  # approve, comment, request_changes
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pr": self.pr_number,
            "comments": len(self.comments),
            "approval": self.approval,
            "confidence": round(self.confidence, 4),
        }


class AutoReviewer:
    def __init__(self, review_fn: Callable = None):
        self._review_fn = review_fn

    def review(self, pr_number: int, diff_text: str, title: str = "") -> ReviewResult:
        result = ReviewResult(pr_number=pr_number)

        if self._review_fn:
            try:
                output = self._review_fn(f"Review PR #{pr_number}: {title}\n\n{diff_text[:3000]}")
                result.summary = str(output)[:500]
                result.approval = "comment"
                result.confidence = 0.6
            except Exception:
                pass

        # Basic inline checks
        for i, line in enumerate(diff_text.split("\n")):
            if line.startswith("+") and not line.startswith("+++"):
                stripped = line[1:].strip()
                if "print(" in stripped and "debug" not in diff_text.lower():
                    result.comments.append(ReviewComment(
                        file_path="unknown", line=i,
                        body="Remove debug print statement",
                        severity="warning",
                    ))
                if "TODO" in stripped:
                    result.comments.append(ReviewComment(
                        file_path="unknown", line=i,
                        body="TODO left in code — complete before merging",
                        severity="info",
                    ))
                if "except:" in stripped or "except Exception:" in stripped:
                    result.comments.append(ReviewComment(
                        file_path="unknown", line=i,
                        body="Bare except clause — catch specific exceptions",
                        severity="warning",
                    ))

        return result
