"""GoalVerifier — tracks completion against original intent."""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum


class GoalStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    IN_PROGRESS = "in_progress"
    DEVIATED = "deviated"
    ABANDONED = "abandoned"
    NOT_STARTED = "not_started"


class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    ARCHITECTURAL = "architectural"
    PERFORMANCE = "performance"
    SECURITY = "security"
    QUALITY = "quality"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


@dataclass
class Requirement:
    id: str
    type: RequirementType
    description: str
    verification: str
    status: GoalStatus = GoalStatus.NOT_STARTED
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description[:100],
            "verification": self.verification,
            "status": self.status.value,
            "evidence": self.evidence[:3],
            "confidence": round(self.confidence, 3),
        }


@dataclass
class Goal:
    id: str
    description: str
    requirements: List[Requirement]
    created_at: float
    status: GoalStatus = GoalStatus.NOT_STARTED
    completion_pct: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description[:100],
            "requirements": [r.to_dict() for r in self.requirements],
            "created_at": self.created_at,
            "status": self.status.value,
            "completion_pct": round(self.completion_pct, 3),
        }


@dataclass
class GoalVerificationReport:
    goal_id: str
    goal_description: str
    status: GoalStatus
    completion_pct: float
    requirements: List[Requirement]
    deviations: List[str]
    unmet_requirements: List[str]
    evidence_summary: Dict[str, List[str]]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "goal_id": self.goal_id,
            "goal_description": self.goal_description[:80],
            "status": self.status.value,
            "completion_pct": round(self.completion_pct, 3),
            "requirements_completed": sum(1 for r in self.requirements if r.status == GoalStatus.COMPLETED),
            "requirements_total": len(self.requirements),
            "deviations": self.deviations,
            "unmet": self.unmet_requirements[:5],
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        icons = {GoalStatus.COMPLETED: "✅", GoalStatus.PARTIALLY_COMPLETED: "🟡",
                 GoalStatus.IN_PROGRESS: "🔄", GoalStatus.DEVIATED: "⚠️",
                 GoalStatus.ABANDONED: "❌", GoalStatus.NOT_STARTED: "⚪"}
        lines = []
        lines.append("=" * 70)
        lines.append("  GOAL VERIFICATION REPORT")
        lines.append("=" * 70)
        lines.append(f"  Goal: {self.goal_description[:60]}")
        lines.append(f"  Status: {icons.get(self.status, '•')} {self.status.value} "
                     f"({self.completion_pct:.0%} complete)")
        lines.append(f"  Requirements: "
                     f"{sum(1 for r in self.requirements if r.status == GoalStatus.COMPLETED)}/"
                     f"{len(self.requirements)} completed")
        lines.append("-" * 70)
        for r in self.requirements:
            icon = icons.get(r.status, "•")
            lines.append(f"  {icon} [{r.type.value}] {r.description[:60]}")
            if r.confidence > 0:
                conf_str = f"conf={r.confidence:.0%}"
                ev_str = f"ev={len(r.evidence)}" if r.evidence else "no evidence"
                lines.append(f"     ({conf_str}, {ev_str})")
        if self.deviations:
            lines.append("-" * 70)
            lines.append("  DEVIATIONS:")
            for d in self.deviations:
                lines.append(f"    ⚠ {d}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class GoalVerifier:
    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._verifiers: Dict[RequirementType, Callable] = {}

    def register_verifier(self, req_type: RequirementType, verifier_fn: Callable) -> None:
        self._verifiers[req_type] = verifier_fn

    def parse_goal(self, description: str) -> Goal:
        reqs = self._extract_requirements(description)
        goal = Goal(
            id=f"goal-{int(time.time())}",
            description=description,
            requirements=reqs,
            created_at=time.time(),
        )
        self._goals[goal.id] = goal
        return goal

    def _extract_requirements(self, description: str) -> List[Requirement]:
        reqs: List[Requirement] = []
        desc_lower = description.lower()

        patterns = [
            (RequirementType.FUNCTIONAL, r"(?:should|must|needs? to|will)\s+(\w[^.,]*)"),
            (RequirementType.FUNCTIONAL, r"(?:implement|add|create|build|make)\s+(\w[^.,]*)"),
            (RequirementType.ARCHITECTURAL, r"(?:refactor|restructure|reorganize|redesign)\s+(\w[^.,]*)"),
            (RequirementType.TESTING, r"(?:test|verify|validate|check)\s+(\w[^.,]*)"),
            (RequirementType.DOCUMENTATION, r"(?:document|documentation|docstring|comment)\s+(\w[^.,]*)"),
        ]
        for req_type, pattern in patterns:
            for match in re.finditer(pattern, desc_lower):
                text = match.group(0).strip()
                req = Requirement(
                    id=f"req-{len(reqs)}",
                    type=req_type,
                    description=text[:100],
                    verification=f"Manual verification: {text[:60]}",
                )
                if text not in [r.description for r in reqs]:
                    reqs.append(req)

        if not reqs:
            reqs.append(Requirement(
                id="req-0",
                type=RequirementType.FUNCTIONAL,
                description=description[:100],
                verification="Manual verification required",
            ))

        return reqs

    def update_requirement(self, goal_id: str, req_id: str, status: GoalStatus,
                           evidence: Optional[List[str]] = None,
                           confidence: float = 0.0) -> None:
        goal = self._goals.get(goal_id)
        if not goal:
            return
        for req in goal.requirements:
            if req.id == req_id:
                req.status = status
                if evidence:
                    req.evidence.extend(evidence)
                if confidence > 0:
                    req.confidence = max(req.confidence, confidence)
                break
        self._recompute_status(goal)

    def _recompute_status(self, goal: Goal) -> None:
        if not goal.requirements:
            goal.status = GoalStatus.NOT_STARTED
            goal.completion_pct = 0.0
            return

        completed = sum(1 for r in goal.requirements if r.status == GoalStatus.COMPLETED)
        deviated = sum(1 for r in goal.requirements if r.status == GoalStatus.DEVIATED)
        abandoned = sum(1 for r in goal.requirements if r.status == GoalStatus.ABANDONED)

        goal.completion_pct = completed / len(goal.requirements)

        if all(r.status == GoalStatus.COMPLETED for r in goal.requirements):
            goal.status = GoalStatus.COMPLETED
        elif abandoned == len(goal.requirements):
            goal.status = GoalStatus.ABANDONED
        elif deviated > 0 or goal.completion_pct < 0.3 and completed > 0:
            goal.status = GoalStatus.DEVIATED
        elif completed > 0:
            goal.status = GoalStatus.PARTIALLY_COMPLETED if goal.completion_pct < 1.0 else GoalStatus.COMPLETED
        elif any(r.status == GoalStatus.IN_PROGRESS for r in goal.requirements):
            goal.status = GoalStatus.IN_PROGRESS
        else:
            goal.status = GoalStatus.NOT_STARTED

    def verify(self, goal_id: str) -> Optional[GoalVerificationReport]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        deviations: List[str] = []
        unmet: List[str] = []

        for req in goal.requirements:
            if req.status == GoalStatus.DEVIATED:
                deviations.append(f"Requirement '{req.description[:50]}' deviated from original intent")
            elif req.status in (GoalStatus.NOT_STARTED, GoalStatus.ABANDONED):
                unmet.append(req.description)

        if goal.completion_pct < 0.5 and sum(1 for r in goal.requirements if r.status != GoalStatus.NOT_STARTED) > 2:
            deviations.append(f"Only {goal.completion_pct:.0%} complete after significant work — possible deviation")

        recommendations = self._generate_recommendations(goal, deviations)

        return GoalVerificationReport(
            goal_id=goal.id,
            goal_description=goal.description,
            status=goal.status,
            completion_pct=goal.completion_pct,
            requirements=goal.requirements,
            deviations=deviations,
            unmet_requirements=unmet,
            evidence_summary={r.id: r.evidence for r in goal.requirements},
            recommendations=recommendations,
        )

    def _generate_recommendations(self, goal: Goal, deviations: List[str]) -> List[str]:
        recs: List[str] = []
        if deviations:
            recs.append("Re-align with original goal before continuing")
            recs.append("Review which requirements have drifted and reset scope")
        if goal.completion_pct < 0.8:
            unmet = [r for r in goal.requirements if r.status in (GoalStatus.NOT_STARTED, GoalStatus.ABANDONED)]
            if unmet:
                recs.append(f"Complete remaining requirements: {len(unmet)} unfinished")
        if goal.completion_pct >= 0.8 and any(r.status != GoalStatus.COMPLETED for r in goal.requirements):
            recs.append("Close remaining low-priority requirements or explicitly defer them")
        if not recs:
            recs.append("Goal verification passed — all requirements met")
        return recs

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def get_all_goals(self) -> List[Goal]:
        return list(self._goals.values())
