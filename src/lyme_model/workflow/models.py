"""Data models for the Issue→Verified PR workflow."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AcceptanceCriterion:
    description: str
    verified: bool = False
    evidence: str = ""

    def to_dict(self) -> dict:
        return {"description": self.description, "verified": self.verified, "evidence": self.evidence}


@dataclass
class IssueTicket:
    id: str
    title: str
    body: str
    repo_url: str
    author: str
    labels: list[str]
    acceptance_criteria: list[AcceptanceCriterion]
    parsed_requirements: list[str]
    source: str
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body_preview": self.body[:200],
            "repo_url": self.repo_url,
            "author": self.author,
            "labels": self.labels,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "parsed_requirements": self.parsed_requirements,
            "source": self.source,
            "url": self.url,
        }


@dataclass
class ImplementationStep:
    order: int
    action: str
    file: str
    description: str
    risk: str
    completed: bool = False

    def to_dict(self) -> dict:
        return {"order": self.order, "action": self.action, "file": self.file,
                "description": self.description, "risk": self.risk, "completed": self.completed}


@dataclass
class ImplementationPlan:
    ticket_id: str
    title: str
    summary: str
    branch_name: str
    steps: list[ImplementationStep]
    estimated_difficulty: str
    estimated_files: list[str]
    test_strategy: str
    rollback_instructions: list[str]
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "summary": self.summary,
            "branch_name": self.branch_name,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_difficulty": self.estimated_difficulty,
            "estimated_files": self.estimated_files,
            "test_strategy": self.test_strategy,
            "rollback_instructions": self.rollback_instructions,
            "created_at": self.created_at,
        }


@dataclass
class RiskReport:
    overall_risk: str
    risk_score: float
    risks: list[dict]
    mitigations: list[str]
    concerns: list[str]

    def to_dict(self) -> dict:
        return {
            "overall_risk": self.overall_risk,
            "risk_score": self.risk_score,
            "risks": self.risks,
            "mitigations": self.mitigations,
            "concerns": self.concerns,
        }


@dataclass
class VerificationEvidence:
    tests_pass: bool
    test_summary: str
    lint_pass: bool
    lint_output: str
    coverage: Optional[float]
    manual_checks: list[dict]
    evidence_log: list[str]

    def to_dict(self) -> dict:
        return {
            "tests_pass": self.tests_pass,
            "test_summary": self.test_summary,
            "lint_pass": self.lint_pass,
            "lint_output": self.lint_output[:200],
            "coverage": self.coverage,
            "manual_checks": self.manual_checks,
            "evidence_log": self.evidence_log,
        }


@dataclass
class PRResult:
    ticket_id: str
    title: str
    branch_name: str
    pr_url: str
    pr_summary: str
    implementation_plan: ImplementationPlan
    risk_report: RiskReport
    verification: VerificationEvidence
    rollback_instructions: list[str]
    files_changed: list[str]
    duration_s: float
    success: bool
    created_at: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "pr_summary": self.pr_summary,
            "implementation_plan": self.implementation_plan.to_dict(),
            "risk_report": self.risk_report.to_dict(),
            "verification": self.verification.to_dict(),
            "rollback_instructions": self.rollback_instructions,
            "files_changed": self.files_changed,
            "duration_s": self.duration_s,
            "success": self.success,
            "created_at": self.created_at,
            "errors": self.errors,
        }
