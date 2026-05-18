"""PRReviewAnalyzer — learns review culture patterns from PR history."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class PRReview:
    pr_id: str
    author: str
    files_changed: int
    lines_added: int
    lines_removed: int
    description_length: int
    review_comments: int
    approval_time_hours: float
    approved: bool
    has_test_changes: bool
    has_doc_changes: bool
    reviewers: List[str]

    def to_dict(self) -> Dict:
        return {
            "pr_id": self.pr_id,
            "author": self.author,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "review_comments": self.review_comments,
            "approval_time_hours": round(self.approval_time_hours, 1),
            "approved": self.approved,
            "has_tests": self.has_test_changes,
            "has_docs": self.has_doc_changes,
            "reviewers": self.reviewers[:3],
        }


@dataclass
class ReviewCultureProfile:
    avg_review_comments: float
    avg_approval_time_hours: float
    approval_rate: float
    avg_files_per_pr: float
    test_inclusion_rate: float
    doc_inclusion_rate: float
    avg_description_length: int
    reviewer_count: int

    def to_dict(self) -> Dict:
        return {
            "avg_review_comments": round(self.avg_review_comments, 1),
            "avg_approval_time_hours": round(self.avg_approval_time_hours, 1),
            "approval_rate": round(self.approval_rate, 3),
            "avg_files_per_pr": round(self.avg_files_per_pr, 1),
            "test_inclusion_rate": round(self.test_inclusion_rate, 3),
            "doc_inclusion_rate": round(self.doc_inclusion_rate, 3),
            "reviewer_count": self.reviewer_count,
        }


@dataclass
class PRReviewReport:
    total_prs: int
    profile: ReviewCultureProfile
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_prs": self.total_prs,
            "profile": self.profile.to_dict(),
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  PR REVIEW ANALYZER")
        lines.append("=" * 70)
        lines.append(f"  Total PRs Analyzed: {self.total_prs}")
        lines.append("")
        p = self.profile
        lines.append("  Review Culture Profile:")
        lines.append(f"    Approval Rate:     {p.approval_rate:.0%}")
        lines.append(f"    Avg Comments:      {p.avg_review_comments:.1f}")
        lines.append(f"    Avg Approval Time: {p.avg_approval_time_hours:.1f}h")
        lines.append(f"    Avg Files/PR:      {p.avg_files_per_pr:.1f}")
        lines.append(f"    Test Inclusion:    {p.test_inclusion_rate:.0%}")
        lines.append(f"    Doc Inclusion:     {p.doc_inclusion_rate:.0%}")
        lines.append(f"    Unique Reviewers:  {p.reviewer_count}")
        if self.insights:
            lines.append("-" * 70)
            lines.append("  INSIGHTS:")
            for ins in self.insights:
                lines.append(f"    • {ins}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class PRReviewAnalyzer:
    def __init__(self, storage_path: Optional[str] = None):
        self._reviews: List[PRReview] = []
        self._storage_path = storage_path
        self._load()

    def record(self, pr_id: str, author: str, files_changed: int,
               lines_added: int, lines_removed: int, description_length: int,
               review_comments: int, approval_time_hours: float,
               approved: bool, has_test_changes: bool = False,
               has_doc_changes: bool = False,
               reviewers: Optional[List[str]] = None) -> None:
        self._reviews.append(PRReview(
            pr_id=pr_id, author=author,
            files_changed=files_changed, lines_added=lines_added,
            lines_removed=lines_removed, description_length=description_length,
            review_comments=review_comments,
            approval_time_hours=approval_time_hours,
            approved=approved, has_test_changes=has_test_changes,
            has_doc_changes=has_doc_changes,
            reviewers=reviewers or [],
        ))
        self._save()

    def analyze(self) -> PRReviewReport:
        if not self._reviews:
            return PRReviewReport(
                total_prs=0,
                profile=ReviewCultureProfile(
                    avg_review_comments=0, avg_approval_time_hours=0,
                    approval_rate=0, avg_files_per_pr=0,
                    test_inclusion_rate=0, doc_inclusion_rate=0,
                    avg_description_length=0, reviewer_count=0,
                ),
                insights=["No PR data yet"],
                recommendations=["Record PR reviews to generate insights"],
            )

        all_reviewers: set = set()
        for r in self._reviews:
            all_reviewers.update(r.reviewers)

        profile = ReviewCultureProfile(
            avg_review_comments=sum(r.review_comments for r in self._reviews) / len(self._reviews),
            avg_approval_time_hours=sum(r.approval_time_hours for r in self._reviews) / len(self._reviews),
            approval_rate=sum(1 for r in self._reviews if r.approved) / len(self._reviews),
            avg_files_per_pr=sum(r.files_changed for r in self._reviews) / len(self._reviews),
            test_inclusion_rate=sum(1 for r in self._reviews if r.has_test_changes) / len(self._reviews),
            doc_inclusion_rate=sum(1 for r in self._reviews if r.has_doc_changes) / len(self._reviews),
            avg_description_length=int(sum(r.description_length for r in self._reviews) / len(self._reviews)),
            reviewer_count=len(all_reviewers),
        )

        insights: List[str] = []
        if profile.approval_rate > 0.9:
            insights.append("High approval rate — reviews may be rubber-stamping")
        elif profile.approval_rate < 0.6:
            insights.append("Low approval rate — PRs may need better preparation")

        if profile.test_inclusion_rate > 0.8:
            insights.append("Strong test culture — most PRs include test changes")
        elif profile.test_inclusion_rate < 0.3:
            insights.append("Low test inclusion — tests should accompany code changes")

        if profile.avg_approval_time_hours > 48:
            insights.append(f"Long review cycle ({profile.avg_approval_time_hours:.0f}h) — "
                           f"consider smaller PRs")
        elif profile.avg_approval_time_hours < 2:
            insights.append("Fast reviews — team is responsive")

        if profile.avg_files_per_pr > 10:
            insights.append(f"Large PRs ({profile.avg_files_per_pr:.0f} files avg) — "
                           f"consider splitting")
        elif profile.avg_files_per_pr < 3:
            insights.append("Small, focused PRs — good practice")

        recommendations: List[str] = []
        if profile.test_inclusion_rate < 0.5:
            recommendations.append("Require test changes with all PRs")
        if profile.avg_review_comments < 1:
            recommendations.append("Encourage more thorough code review comments")
        if profile.avg_files_per_pr > 15:
            recommendations.append("Aim for PRs under 10 files for faster, better reviews")
        if profile.avg_approval_time_hours > 72:
            recommendations.append("Set SLA for PR review turnaround time")
        if profile.approval_rate > 0.95 and len(self._reviews) > 10:
            recommendations.append("Review if approvals are substantive or perfunctory")
        if not recommendations:
            recommendations.append("Review culture is healthy")

        return PRReviewReport(
            total_prs=len(self._reviews),
            profile=profile,
            insights=insights,
            recommendations=recommendations,
        )

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.to_dict() for r in self._reviews]
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                self._reviews.append(PRReview(**d))
        except (json.JSONDecodeError, KeyError):
            pass
