"""ExplainabilityEngine — explains every decision with reasoning chains."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class DecisionType(str, Enum):
    EDIT = "edit"
    REJECT = "reject"
    DEFER = "defer"
    ESCALATE = "escalate"
    APPROVE = "approve"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ReasoningStep:
    order: int
    premise: str
    evidence: List[str]
    confidence: float
    conclusion: str

    def to_dict(self) -> Dict:
        return {
            "order": self.order,
            "premise": self.premise[:80],
            "evidence_count": len(self.evidence),
            "confidence": round(self.confidence, 3),
            "conclusion": self.conclusion[:80],
        }


@dataclass
class Explanation:
    id: str
    decision_type: DecisionType
    description: str
    reasoning_chain: List[ReasoningStep]
    confidence_level: ConfidenceLevel
    alternative_considered: List[str]
    risks_identified: List[str]
    assumptions: List[str]
    timestamp: float
    duration_ms: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.decision_type.value,
            "description": self.description[:80],
            "steps": len(self.reasoning_chain),
            "confidence": self.confidence_level.value,
            "risks": len(self.risks_identified),
        }

    def to_markdown(self) -> str:
        lines = [f"## Decision: {self.description[:60]}"]
        lines.append(f"**Type**: {self.decision_type.value}")
        lines.append(f"**Confidence**: {self.confidence_level.value}")
        lines.append("")
        lines.append("### Reasoning Chain")
        for step in self.reasoning_chain:
            lines.append(f"**Step {step.order}**: {step.premise}")
            for ev in step.evidence[:3]:
                lines.append(f"  - Evidence: {ev[:60]}")
            lines.append(f"  → {step.conclusion[:60]}")
        if self.alternative_considered:
            lines.append("### Alternatives Considered")
            for a in self.alternative_considered:
                lines.append(f"- {a[:60]}")
        if self.risks_identified:
            lines.append("### Risks")
            for r in self.risks_identified:
                lines.append(f"- ⚠️ {r[:60]}")
        return "\n".join(lines)


@dataclass
class ExplainabilityReport:
    total_explanations: int
    by_type: Dict[str, int]
    avg_confidence: float
    avg_reasoning_steps: float
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  EXPLAINABILITY REPORT")
        lines.append("=" * 70)
        lines.append(f"  Total Explanations: {self.total_explanations}")
        lines.append(f"  Avg Confidence: {self.avg_confidence:.0%}")
        lines.append(f"  Avg Reasoning Steps: {self.avg_reasoning_steps:.1f}")
        lines.append("")
        lines.append("  By Type:")
        for dtype, count in sorted(self.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"    {dtype}: {count}")
        if self.recommendations:
            lines.append("-" * 70)
            for r in self.recommendations:
                lines.append(f"  • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ExplainabilityEngine:
    def __init__(self):
        self._explanations: List[Explanation] = []

    def explain(self, decision_type: DecisionType, description: str,
                premises: List[str], evidences: List[List[str]],
                conclusions: List[str],
                alternatives: Optional[List[str]] = None,
                risks: Optional[List[str]] = None,
                assumptions: Optional[List[str]] = None) -> Explanation:
        start = time.time()
        reasoning_chain: List[ReasoningStep] = []
        total_confidence = 0.0

        for i, (premise, evidence, conclusion) in enumerate(zip(premises, evidences, conclusions)):
            step_confidence = min(1.0, len(evidence) * 0.2 + 0.3)
            total_confidence += step_confidence
            reasoning_chain.append(ReasoningStep(
                order=i + 1,
                premise=premise,
                evidence=evidence,
                confidence=step_confidence,
                conclusion=conclusion,
            ))

        avg_confidence = total_confidence / max(len(reasoning_chain), 1)
        if avg_confidence >= 0.9:
            conf_level = ConfidenceLevel.VERY_HIGH
        elif avg_confidence >= 0.7:
            conf_level = ConfidenceLevel.HIGH
        elif avg_confidence >= 0.5:
            conf_level = ConfidenceLevel.MEDIUM
        elif avg_confidence >= 0.3:
            conf_level = ConfidenceLevel.LOW
        else:
            conf_level = ConfidenceLevel.VERY_LOW

        explanation = Explanation(
            id=f"expl-{len(self._explanations)}",
            decision_type=decision_type,
            description=description,
            reasoning_chain=reasoning_chain,
            confidence_level=conf_level,
            alternative_considered=alternatives or [],
            risks_identified=risks or [],
            assumptions=assumptions or [],
            timestamp=time.time(),
            duration_ms=(time.time() - start) * 1000,
        )
        self._explanations.append(explanation)
        return explanation

    def report(self) -> ExplainabilityReport:
        if not self._explanations:
            return ExplainabilityReport(
                total_explanations=0, by_type={}, avg_confidence=0.0,
                avg_reasoning_steps=0.0,
                recommendations=["Record decisions to generate explanations"],
            )

        by_type: Dict[str, int] = {}
        total_conf = 0.0
        total_steps = 0
        for exp in self._explanations:
            by_type[exp.decision_type.value] = by_type.get(exp.decision_type.value, 0) + 1
            conf_map = {ConfidenceLevel.VERY_HIGH: 0.95, ConfidenceLevel.HIGH: 0.8,
                       ConfidenceLevel.MEDIUM: 0.6, ConfidenceLevel.LOW: 0.4,
                       ConfidenceLevel.VERY_LOW: 0.2}
            total_conf += conf_map.get(exp.confidence_level, 0.5)
            total_steps += len(exp.reasoning_chain)

        recommendations: List[str] = []
        if self._explanations:
            recommendations.append(f"Generated {len(self._explanations)} explanations")
        low_conf = [e for e in self._explanations
                   if e.confidence_level in (ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW)]
        if low_conf:
            recommendations.append(f"{len(low_conf)} low-confidence decisions need more evidence")

        return ExplainabilityReport(
            total_explanations=len(self._explanations),
            by_type=by_type,
            avg_confidence=total_conf / max(len(self._explanations), 1),
            avg_reasoning_steps=total_steps / max(len(self._explanations), 1),
            recommendations=recommendations,
        )
