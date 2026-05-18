"""Data models for the paid ticket simulator."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TicketDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class AcceptanceGrade(Enum):
    ACCEPTED = "accepted"
    CONDITIONALLY_ACCEPTED = "conditionally_accepted"
    REJECTED_MINOR = "rejected_minor"
    REJECTED_MAJOR = "rejected_major"


@dataclass
class ArchitectureConstraint:
    description: str
    category: str
    severity: str

    def to_dict(self) -> dict:
        return {"description": self.description, "category": self.category, "severity": self.severity}


@dataclass
class HiddenTest:
    description: str
    test_type: str
    trigger_condition: str
    points: int

    def to_dict(self) -> dict:
        return {"description": self.description, "test_type": self.test_type,
                "trigger_condition": self.trigger_condition, "points": self.points}


@dataclass
class ClientTicket:
    id: str
    title: str
    description: str
    ambiguous_elements: list[str]
    acceptance_criteria: list[str]
    hidden_tests: list[HiddenTest]
    architecture_constraints: list[ArchitectureConstraint]
    difficulty: TicketDifficulty
    difficulty_score: float
    estimated_revenue: float
    estimated_hours: float
    client_context: str
    repo_url: str
    repo_path: str
    hints: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "ambiguous_elements": self.ambiguous_elements,
            "acceptance_criteria": self.acceptance_criteria,
            "hidden_tests": [h.to_dict() for h in self.hidden_tests],
            "architecture_constraints": [c.to_dict() for c in self.architecture_constraints],
            "difficulty": self.difficulty.value,
            "difficulty_score": self.difficulty_score,
            "estimated_revenue": self.estimated_revenue,
            "estimated_hours": self.estimated_hours,
            "client_context": self.client_context,
            "repo_url": self.repo_url,
            "repo_path": self.repo_path,
            "hints": self.hints,
            "tags": self.tags,
        }


@dataclass
class TicketResult:
    ticket_id: str
    title: str
    success: bool
    acceptance_grade: Optional[AcceptanceGrade]
    score: float
    revenue_earned: float
    duration_hours: float
    criteria_met: int
    criteria_total: int
    hidden_tests_passed: int
    hidden_tests_total: int
    constraints_violated: list[str]
    ambiguity_resolved: bool
    errors: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "success": self.success,
            "acceptance_grade": self.acceptance_grade.value if self.acceptance_grade else None,
            "score": self.score,
            "revenue_earned": self.revenue_earned,
            "duration_hours": self.duration_hours,
            "criteria_met": self.criteria_met,
            "criteria_total": self.criteria_total,
            "hidden_tests_passed": self.hidden_tests_passed,
            "hidden_tests_total": self.hidden_tests_total,
            "constraints_violated": self.constraints_violated,
            "ambiguity_resolved": self.ambiguity_resolved,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


@dataclass
class TicketRun:
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    results: list[TicketResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def add_result(self, result: TicketResult) -> None:
        self.results.append(result)

    def compute_summary(self) -> dict:
        total = len(self.results)
        accepted = sum(1 for r in self.results if r.acceptance_grade == AcceptanceGrade.ACCEPTED)
        conditional = sum(1 for r in self.results if r.acceptance_grade == AcceptanceGrade.CONDITIONALLY_ACCEPTED)
        rejected = sum(1 for r in self.results if r.acceptance_grade in (AcceptanceGrade.REJECTED_MINOR, AcceptanceGrade.REJECTED_MAJOR))
        total_revenue = sum(r.revenue_earned for r in self.results)
        total_estimated = sum(self._get_estimated_revenue(r.ticket_id) for r in self.results)
        avg_score = sum(r.score for r in self.results) / max(total, 1)

        self.summary = {
            "total": total,
            "accepted": accepted,
            "conditionally_accepted": conditional,
            "rejected": rejected,
            "acceptance_rate": round(accepted / max(total, 1), 3),
            "total_revenue": round(total_revenue, 2),
            "estimated_revenue": round(total_estimated, 2),
            "revenue_capture_rate": round(total_revenue / max(total_estimated, 1), 3),
            "avg_score": round(avg_score, 3),
            "completed_at": self.completed_at,
        }
        return self.summary

    def _get_estimated_revenue(self, ticket_id: str) -> float:
        from .seeded_tickets import SEEDED_TICKETS
        for t in SEEDED_TICKETS:
            if t.id == ticket_id:
                return t.estimated_revenue
        return 0.0
