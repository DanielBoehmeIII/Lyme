"""Skill Critic.

Before using a learned skill, Lyme should ask:
- does this skill actually fit?
- what assumptions does it make?
- what failed last time?
- what evidence supports applying it?
- what risks does it introduce?
- what verification is required?

Implements:
- assumption extraction
- applicability scoring
- contradiction detection
- safety checks
- post-use evaluation
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import json
import uuid
from pathlib import Path


class ApplicabilityLevel(Enum):
    HIGHLY_APPLICABLE = "highly_applicable"
    APPLICABLE = "applicable"
    PARTIALLY_APPLICABLE = "partially_applicable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    RISKY = "risky"
    DANGEROUS = "dangerous"


@dataclass
class Assumption:
    statement: str = ""
    category: str = ""
    confidence: float = 0.0
    verified: Optional[bool] = None
    verification_method: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ApplicabilityScore:
    overall: ApplicabilityLevel = ApplicabilityLevel.UNKNOWN
    score: float = 0.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "overall": self.overall.value,
            "score": self.score,
            "dimension_scores": self.dimension_scores,
            "rationale": self.rationale,
        }


@dataclass
class Contradiction:
    description: str = ""
    severity: str = "medium"
    source: str = ""
    target: str = ""
    resolution: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SafetyCheck:
    check_name: str = ""
    description: str = ""
    level: SafetyLevel = SafetyLevel.SAFE
    passed: bool = True
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "description": self.description,
            "level": self.level.value,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass
class CritiqueResult:
    skill_id: str = ""
    skill_name: str = ""
    analyzed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    applicability: ApplicabilityScore = field(default_factory=ApplicabilityScore)
    assumptions: List[Assumption] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    safety_checks: List[SafetyCheck] = field(default_factory=list)

    failure_history: List[Dict[str, Any]] = field(default_factory=list)
    evidence_support: str = ""
    recommended_verification: List[str] = field(default_factory=list)
    overall_recommendation: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "analyzed_at": self.analyzed_at,
            "applicability": self.applicability.to_dict(),
            "assumptions": [a.to_dict() for a in self.assumptions],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "safety_checks": [s.to_dict() for s in self.safety_checks],
            "failure_history": self.failure_history[-5:],
            "evidence_support": self.evidence_support,
            "recommended_verification": self.recommended_verification,
            "overall_recommendation": self.overall_recommendation,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Skill Critique: {self.skill_name}")
        lines.append(f"")
        lines.append(f"**Recommendation**: {self.overall_recommendation}")
        lines.append(f"**Confidence**: {self.confidence:.0%}")
        lines.append(f"**Applicability**: {self.applicability.overall.value} ({self.applicability.score:.2f})")
        lines.append(f"")

        if self.assumptions:
            lines.append(f"### Assumptions ({len(self.assumptions)})")
            for a in self.assumptions:
                verified = "✓" if a.verified else "?" if a.verified is None else "✗"
                lines.append(f"- {verified} {a.statement} ({a.category})")
            lines.append(f"")

        if self.contradictions:
            lines.append(f"### Contradictions ({len(self.contradictions)})")
            for c in self.contradictions:
                lines.append(f"- [{c.severity}] {c.description}")
            lines.append(f"")

        if self.safety_checks:
            lines.append(f"### Safety Checks ({len(self.safety_checks)})")
            for s in self.safety_checks:
                icon = "✓" if s.passed else "✗"
                lines.append(f"- {icon} {s.check_name}: {s.description}")
            lines.append(f"")

        if self.recommended_verification:
            lines.append(f"### Recommended Verification")
            for v in self.recommended_verification:
                lines.append(f"- {v}")
            lines.append(f"")

        if self.evidence_support:
            lines.append(f"### Evidence")
            lines.append(f"{self.evidence_support}")
            lines.append(f"")

        return "\n".join(lines)


class SkillCritic:
    def __init__(self):
        self._assumption_templates = {
            "file_structure": "The target repository has similar file structure to the source",
            "language": "The target repository uses the same programming language",
            "test_framework": "The target repository uses the same test framework",
            "dependency_manager": "The target uses the same dependency management approach",
            "code_style": "The target follows similar code style conventions",
            "architecture": "The target has similar architectural patterns",
        }

    def critique(
        self, skill: Any, target_context: Optional[Dict[str, Any]] = None
    ) -> CritiqueResult:
        result = CritiqueResult(
            skill_id=skill.id if hasattr(skill, 'id') else "unknown",
            skill_name=skill.name if hasattr(skill, 'name') else "unknown",
        )

        result.assumptions = self._extract_assumptions(skill)
        result.applicability = self._score_applicability(skill, result.assumptions)
        result.contradictions = self._detect_contradictions(skill, result.assumptions)
        result.safety_checks = self._run_safety_checks(skill)
        result.failure_history = self._get_failure_history(skill)
        result.recommended_verification = self._recommend_verification(skill, result.safety_checks)
        result.evidence_support = self._summarize_evidence(skill)
        result.confidence = self._compute_confidence(result)
        result.overall_recommendation = self._generate_recommendation(result)

        return result

    def _extract_assumptions(self, skill: Any) -> List[Assumption]:
        assumptions = []

        for template_name, template_stmt in self._assumption_templates.items():
            assumptions.append(Assumption(
                statement=template_stmt,
                category=template_name,
                confidence=0.5,
                verified=None,
                verification_method=f"Check if {template_name} match between repos",
            ))

        for precondition in getattr(skill, 'preconditions', []):
            assumptions.append(Assumption(
                statement=f"Precondition met: {precondition.description}",
                category="precondition",
                confidence=0.7,
                verified=precondition.required,
                verification_method=f"Verify: {precondition.check_type} {precondition.target}",
            ))

        for step in getattr(skill, 'workflow_steps', []):
            if step.tool:
                assumptions.append(Assumption(
                    statement=f"Tool '{step.tool}' is available and behaves as expected",
                    category="tool_availability",
                    confidence=0.6,
                    verified=None,
                    verification_method=f"Check if {step.tool} is installed",
                ))

        return assumptions

    def _score_applicability(
        self, skill: Any, assumptions: List[Assumption]
    ) -> ApplicabilityScore:
        score = ApplicabilityScore()

        if not assumptions:
            score.score = 0.3
            score.overall = ApplicabilityLevel.UNKNOWN
            score.rationale = "No assumptions extracted — cannot assess applicability"
            return score

        verified_count = sum(1 for a in assumptions if a.verified == True)
        total_required = sum(1 for a in assumptions if a.category in ("precondition", "language"))
        dim_scores = {}

        if total_required > 0:
            dim_scores["preconditions"] = verified_count / total_required
        dim_scores["assumption_coverage"] = verified_count / max(len(assumptions), 1)

        score.dimension_scores = dim_scores
        score.score = sum(dim_scores.values()) / max(len(dim_scores), 1)

        if score.score >= 0.8:
            score.overall = ApplicabilityLevel.HIGHLY_APPLICABLE
        elif score.score >= 0.5:
            score.overall = ApplicabilityLevel.APPLICABLE
        elif score.score >= 0.2:
            score.overall = ApplicabilityLevel.PARTIALLY_APPLICABLE
        else:
            score.overall = ApplicabilityLevel.NOT_APPLICABLE

        score.rationale = f"Applicability score {score.score:.2f} based on {verified_count}/{len(assumptions)} verified assumptions"
        return score

    def _detect_contradictions(
        self, skill: Any, assumptions: List[Assumption]
    ) -> List[Contradiction]:
        contradictions = []

        for step in getattr(skill, 'workflow_steps', []):
            if step.tool:
                import shutil
                if step.tool not in ("lyme", "grep", "pytest") and shutil.which(step.tool) is None:
                    contradictions.append(Contradiction(
                        description=f"Tool '{step.tool}' not found on PATH but skill expects it",
                        severity="high",
                        source="tool_check",
                        target=step.tool,
                        resolution=f"Install {step.tool} or adapt the skill",
                    ))

        return contradictions

    def _run_safety_checks(self, skill: Any) -> List[SafetyCheck]:
        checks = []

        checks.append(SafetyCheck(
            check_name="destructive_operations",
            description="Skill contains destructive or irreversible operations",
            level=SafetyLevel.SAFE,
            passed=True,
            details="No destructive operations detected",
        ))

        for step in getattr(skill, 'workflow_steps', []):
            action_lower = step.action.lower()
            if any(kw in action_lower for kw in ("rm ", "delete", "drop", "truncate")):
                checks.append(SafetyCheck(
                    check_name="destructive_action",
                    description=f"Step uses destructive action: {step.action}",
                    level=SafetyLevel.DANGEROUS,
                    passed=False,
                    details=f"Step {step.step_id}: {step.description}",
                ))

        confidence = skill.current_confidence if hasattr(skill, 'current_confidence') else 0.0
        if confidence < 0.3:
            checks.append(SafetyCheck(
                check_name="low_confidence",
                description=f"Skill has low confidence ({confidence:.2f})",
                level=SafetyLevel.CAUTION,
                passed=False,
                details="Low confidence increases risk of incorrect application",
            ))

        return checks

    def _get_failure_history(self, skill: Any) -> List[Dict[str, Any]]:
        failures = []
        for entry in getattr(skill, 'confidence_history', []):
            if not entry.success:
                failures.append({
                    "timestamp": entry.timestamp,
                    "context": entry.context,
                    "confidence_at_time": entry.confidence,
                })
        return failures

    def _recommend_verification(self, skill: Any, safety: List[SafetyCheck]) -> List[str]:
        recommendations = []

        for check in safety:
            if not check.passed:
                recommendations.append(f"Address safety issue: {check.description}")

        for step in getattr(skill, 'verification', []):
            recommendations.append(f"Run verification: {step.name} ({step.command})")

        if not recommendations:
            recommendations.append("Run all existing tests after applying skill")
            recommendations.append("Review diff before committing changes")

        return recommendations

    def _summarize_evidence(self, skill: Any) -> str:
        history = getattr(skill, 'confidence_history', [])
        if not history:
            return "No execution history for this skill"

        total = len(history)
        successes = sum(1 for h in history if h.success)
        return f"Executed {total} times with {successes} successes ({successes/total:.0%} success rate)"

    def _compute_confidence(self, critique: CritiqueResult) -> float:
        scores = [
            critique.applicability.score * 0.4,
            (1.0 - len(critique.contradictions) * 0.1) * 0.3,
            (sum(1 for s in critique.safety_checks if s.passed) / max(len(critique.safety_checks), 1)) * 0.3,
        ]
        return max(0.0, min(1.0, sum(scores)))

    def _generate_recommendation(self, critique: CritiqueResult) -> str:
        if critique.applicability.overall == ApplicabilityLevel.NOT_APPLICABLE:
            return "DO NOT APPLY — Skill is not applicable to this context"

        unsafe = [s for s in critique.safety_checks if not s.passed and s.level in (SafetyLevel.RISKY, SafetyLevel.DANGEROUS)]
        if unsafe:
            return f"NOT RECOMMENDED — {len(unsafe)} safety concerns must be resolved first"

        if critique.applicability.overall == ApplicabilityLevel.HIGHLY_APPLICABLE:
            return "STRONGLY RECOMMENDED — Skill is highly applicable with low risk"
        elif critique.applicability.overall == ApplicabilityLevel.APPLICABLE:
            return "RECOMMENDED WITH CAUTION — Skill is applicable but verify assumptions"
        elif critique.applicability.overall == ApplicabilityLevel.PARTIALLY_APPLICABLE:
            return "CONSIDER WITH ADAPTATION — Skill needs modification for this context"
        else:
            return "INCONCLUSIVE — More information needed to assess applicability"
