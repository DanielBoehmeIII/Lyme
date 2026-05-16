import time
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class ContributionType(str, Enum):
    BENCHMARK_TASK = "benchmark_task"
    MODEL_ADAPTER = "model_adapter"
    TOOL_ROUTER = "tool_router"
    MEMORY_SYSTEM = "memory_system"
    COMPRESSION_STRATEGY = "compression_strategy"
    GOVERNANCE_POLICY = "governance_policy"
    VISUALIZATION_MODULE = "visualization_module"
    STANDARD_EXTENSION = "standard_extension"
    RESEARCH_REPORT = "research_report"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"


class ContributionStatus(str, Enum):
    DRAFT = "draft"
    REVIEW_PENDING = "review_pending"
    REVIEWING = "reviewing"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    MERGED = "merged"
    REJECTED = "rejected"


@dataclass
class ContributionRequirements:
    tests_required: bool = True
    telemetry_impact_required: bool = True
    benchmark_impact_required: bool = True
    failure_modes_required: bool = True
    documentation_required: bool = True
    trace_examples_required: bool = False
    review_level: str = "standard"  # light, standard, full
    min_test_coverage: float = 0.7
    additional_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContributionReview:
    reviewer: str = ""
    status: str = "pending"
    comments: List[str] = field(default_factory=list)
    passed_requirements: List[str] = field(default_factory=list)
    failed_requirements: List[str] = field(default_factory=list)
    score: float = 0.0
    reviewed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Contribution:
    contribution_id: str = ""
    contribution_type: str = ContributionType.BENCHMARK_TASK
    title: str = ""
    description: str = ""
    author: str = ""
    version: str = "0.7.0"
    requirements: ContributionRequirements = field(default_factory=ContributionRequirements)
    files: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    telemetry_impact: dict = field(default_factory=dict)
    benchmark_impact: dict = field(default_factory=dict)
    failure_modes: List[str] = field(default_factory=list)
    documentation: str = ""
    review: Optional[ContributionReview] = None
    status: str = ContributionStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def ready_for_review(self) -> bool:
        checks = []
        if self.requirements.tests_required:
            checks.append(len(self.tests) > 0)
        if self.requirements.telemetry_impact_required:
            checks.append(len(self.telemetry_impact) > 0)
        if self.requirements.benchmark_impact_required:
            checks.append(len(self.benchmark_impact) > 0)
        if self.requirements.failure_modes_required:
            checks.append(len(self.failure_modes) > 0)
        if self.requirements.documentation_required:
            checks.append(bool(self.documentation))
        return all(checks)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ready_for_review"] = self.ready_for_review()
        return d


class ContributionProtocol:
    def __init__(self):
        self.contributions: List[Contribution] = []
        self._reviews: List[ContributionReview] = []
        self._guides: Dict[str, ContributionGuide] = {}
        self._init_guides()

    def _init_guides(self):
        for ct in ContributionType:
            self._guides[ct.value] = ContributionGuide(
                contribution_type=ct.value,
                template_dir=f"templates/{ct.value}",
                example_files=[
                    f"examples/{ct.value}/basic_example.py",
                    f"examples/{ct.value}/test_example.py",
                ],
                review_criteria=self._default_criteria(ct.value),
            )

    def _default_criteria(self, ct: str) -> List[str]:
        base = ["Code quality", "Test coverage > 70%", "Documentation clear"]
        if ct in ("benchmark_task",):
            base += ["Anti-gaming review", "Baseline results provided", "Task is reproducible"]
        elif ct in ("model_adapter",):
            base += ["Supports standard interface", "Error handling complete", "Version compatibility documented"]
        elif ct in ("governance_policy",):
            base += ["Policy is deterministic", "Edge cases handled", "Default behavior is safe"]
        return base

    def submit(self, contribution: Contribution) -> str:
        contribution.contribution_id = f"contrib-{int(time.time())}-{len(self.contributions)}"
        contribution.status = ContributionStatus.REVIEW_PENDING
        self.contributions.append(contribution)
        return contribution.contribution_id

    def review(self, contribution_id: str, review: ContributionReview) -> Optional[ContributionReview]:
        for c in self.contributions:
            if c.contribution_id == contribution_id:
                c.review = review
                c.status = ContributionStatus.REVIEWING
                review.reviewed_at = time.time()
                if review.score >= 0.7 and not review.failed_requirements:
                    c.status = ContributionStatus.APPROVED
                elif review.score < 0.4:
                    c.status = ContributionStatus.REJECTED
                else:
                    c.status = ContributionStatus.CHANGES_REQUESTED
                self._reviews.append(review)
                return review
        return None

    def get_guide(self, contribution_type: str) -> Optional["ContributionGuide"]:
        return self._guides.get(contribution_type)

    def generate_checklist(self, contribution_type: str) -> List[str]:
        guide = self.get_guide(contribution_type)
        if not guide:
            return ["Unknown contribution type"]
        return guide.review_criteria

    def summary(self) -> dict:
        status_counts = {}
        type_counts = {}
        for c in self.contributions:
            status_counts[c.status] = status_counts.get(c.status, 0) + 1
            type_counts[c.contribution_type] = type_counts.get(c.contribution_type, 0) + 1
        return {
            "total": len(self.contributions),
            "by_status": status_counts,
            "by_type": type_counts,
            "available_guides": list(self._guides.keys()),
            "approved": sum(1 for c in self.contributions if c.status == ContributionStatus.APPROVED),
        }

    def to_dict(self) -> dict:
        return {
            "contributions": [c.to_dict() for c in self.contributions],
            "guides": {k: v.to_dict() for k, v in self._guides.items()},
            "summary": self.summary(),
        }


@dataclass
class ContributionGuide:
    contribution_type: str = ""
    template_dir: str = ""
    example_files: List[str] = field(default_factory=list)
    review_criteria: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
