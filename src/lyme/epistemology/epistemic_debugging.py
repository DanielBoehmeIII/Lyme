from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import uuid
import time


class FailureCategory(str, Enum):
    FALSE_CLAIM = "false_claim"
    MISSING_EVIDENCE = "missing_evidence"
    IGNORED_CONTRADICTION = "ignored_contradiction"
    FAULTY_INFERENCE = "faulty_inference"
    WRONG_TOOL = "wrong_tool"
    MEMORY_CORRUPTION = "memory_corruption"
    OVERCONFIDENCE = "overconfidence"
    UNDERCONFIDENCE = "underconfidence"
    CONTEXT_OVERSIGHT = "context_oversight"
    HALLUCINATION = "hallucination"


@dataclass
class FailedInference:
    step: str
    expected: str
    actual: str
    reason: str
    recovery: str = ""

    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "expected": self.expected,
            "actual": self.actual,
            "reason": self.reason,
            "recovery": self.recovery,
        }


@dataclass
class EpistemicFailure:
    id: str
    category: FailureCategory
    false_claim: str
    description: str
    what_was_believed: str = ""
    what_was_true: str = ""
    evidence_missing: List[str] = field(default_factory=list)
    contradiction_ignored: List[str] = field(default_factory=list)
    inference_step_failed: Optional[FailedInference] = None
    tool_that_should_have_been_used: str = ""
    memory_that_misled: str = ""
    confidence_at_time: float = 0.0
    corrected_confidence: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "false_claim": self.false_claim,
            "description": self.description,
            "what_was_believed": self.what_was_believed,
            "what_was_true": self.what_was_true,
            "evidence_missing": self.evidence_missing,
            "contradiction_ignored": self.contradiction_ignored,
            "inference_step_failed": self.inference_step_failed.to_dict() if self.inference_step_failed else None,
            "tool_that_should_have_been_used": self.tool_that_should_have_been_used,
            "memory_that_misled": self.memory_that_misled,
            "confidence_at_time": self.confidence_at_time,
            "corrected_confidence": self.corrected_confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class DebugReport:
    report_id: str
    failures: List[EpistemicFailure]
    pattern_summary: Dict
    recommendations: List[str]
    severity: str = "info"

    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "failures": [f.to_dict() for f in self.failures],
            "pattern_summary": self.pattern_summary,
            "recommendations": self.recommendations,
            "severity": self.severity,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Epistemic Debug Report: {self.report_id}")
        lines.append(f"")
        lines.append(f"**Severity**: {self.severity}")
        lines.append(f"**Failures**: {len(self.failures)}")
        lines.append(f"")

        categories: Dict[str, int] = {}
        for f in self.failures:
            cat = f.category.value
            categories[cat] = categories.get(cat, 0) + 1

        lines.append(f"## Failure Pattern Summary")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            icon = {"false_claim": "🧪", "missing_evidence": "🔍", "ignored_contradiction": "⚠️",
                    "faulty_inference": "🔗", "wrong_tool": "🔧", "memory_corruption": "🧠",
                    "overconfidence": "📈", "hallucination": "🌀"}.get(cat, "•")
            lines.append(f"- {icon} **{cat.replace('_', ' ').title()}**: {count}")
        lines.append(f"")

        lines.append(f"## Failure Details")
        for i, failure in enumerate(self.failures, 1):
            lines.append(f"### {i}. {failure.category.value.replace('_', ' ').title()}")
            lines.append(f"**Claim**: {failure.false_claim}")
            lines.append(f"**Believed**: {failure.what_was_believed or 'N/A'}")
            lines.append(f"**Actual**: {failure.what_was_true or 'N/A'}")
            if failure.evidence_missing:
                lines.append(f"**Missing Evidence**: {', '.join(failure.evidence_missing)}")
            if failure.contradiction_ignored:
                lines.append(f"**Contradictions Ignored**: {', '.join(failure.contradiction_ignored)}")
            if failure.inference_step_failed:
                inf = failure.inference_step_failed
                lines.append(f"**Failed Inference**: {inf.step} (expected {inf.expected}, got {inf.actual})")
                lines.append(f"  Reason: {inf.reason}")
            if failure.tool_that_should_have_been_used:
                lines.append(f"**Should have used**: {failure.tool_that_should_have_been_used}")
            lines.append(f"**Confidence**: {failure.confidence_at_time:.0%} → {failure.corrected_confidence:.0%}")
            lines.append(f"")

        lines.append(f"## Recommendations")
        for r in self.recommendations:
            lines.append(f"- {r}")
        lines.append(f"")

        return "\n".join(lines)


class EpistemicDebugger:
    def __init__(self):
        self._failures: List[EpistemicFailure] = []
        self._pattern_history: List[EpistemicFailure] = []

    def record_failure(
        self,
        category: FailureCategory,
        false_claim: str,
        description: str,
        what_was_believed: str = "",
        what_was_true: str = "",
        evidence_missing: Optional[List[str]] = None,
        contradiction_ignored: Optional[List[str]] = None,
        inference_step_failed: Optional[FailedInference] = None,
        tool_that_should_have_been_used: str = "",
        memory_that_misled: str = "",
        confidence_at_time: float = 0.0,
        corrected_confidence: float = 0.0,
    ) -> EpistemicFailure:
        failure = EpistemicFailure(
            id=f"ef_{uuid.uuid4().hex[:12]}",
            category=category,
            false_claim=false_claim,
            description=description,
            what_was_believed=what_was_believed,
            what_was_true=what_was_true,
            evidence_missing=evidence_missing or [],
            contradiction_ignored=contradiction_ignored or [],
            inference_step_failed=inference_step_failed,
            tool_that_should_have_been_used=tool_that_should_have_been_used,
            memory_that_misled=memory_that_misled,
            confidence_at_time=confidence_at_time,
            corrected_confidence=corrected_confidence,
            timestamp=time.time(),
        )
        self._failures.append(failure)
        self._pattern_history.append(failure)
        return failure

    def diagnose(self, claim_id: str, assessment, actual_outcome: bool) -> Optional[EpistemicFailure]:
        if not assessment:
            return None

        overall = assessment.overall_confidence
        was_wrong = actual_outcome is False and overall > 0.6
        was_right_but_unsure = actual_outcome and overall < 0.4

        if not was_wrong and not was_right_but_unsure:
            return None

        if was_wrong:
            category = FailureCategory.FALSE_CLAIM
            if len(assessment.claim.evidence) == 0:
                category = FailureCategory.MISSING_EVIDENCE
            elif assessment.contradiction_count > 0:
                category = FailureCategory.IGNORED_CONTRADICTION
            elif assessment.inference_penalty > 0.3:
                category = FailureCategory.FAULTY_INFERENCE
            elif overall > 0.8:
                category = FailureCategory.OVERCONFIDENCE

            return self.record_failure(
                category=category,
                false_claim=assessment.claim.statement,
                description=f"Claim was wrong despite {overall:.0%} confidence",
                what_was_believed=assessment.claim.statement,
                evidence_missing=assessment.claim.missing_evidence,
                contradiction_ignored=assessment.claim.contradicted_by if assessment.contradiction_count > 0 else None,
                inference_step_failed=FailedInference(
                    step="evidence_assessment",
                    expected="correct_claim",
                    actual="incorrect_claim",
                    reason=f"Inference depth {assessment.claim.inference_depth.value} with {assessment.evidence_count} evidence sources"
                ) if assessment.inference_penalty > 0.3 else None,
                confidence_at_time=overall,
                corrected_confidence=max(0.1, overall - 0.5),
            )

        if was_right_but_unsure:
            return self.record_failure(
                category=FailureCategory.UNDERCONFIDENCE,
                false_claim=assessment.claim.statement,
                description=f"Claim was correct but confidence was only {overall:.0%}",
                what_was_believed=assessment.claim.statement,
                confidence_at_time=overall,
                corrected_confidence=min(0.9, overall + 0.4),
            )

        return None

    def detect_patterns(self) -> Dict:
        if not self._pattern_history:
            return {"patterns": [], "dominant": "none"}

        category_counts: Dict[str, int] = {}
        tool_counts: Dict[str, int] = {}
        for f in self._pattern_history:
            cat = f.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if f.tool_that_should_have_been_used:
                tool_counts[f.tool_that_should_have_been_used] = tool_counts.get(f.tool_that_should_have_been_used, 0) + 1

        total = len(self._pattern_history)
        patterns = [{"pattern": cat, "count": count, "rate": round(count / total, 3)}
                     for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])]

        dominant = patterns[0]["pattern"] if patterns else "none"

        return {
            "patterns": patterns,
            "dominant": dominant,
            "total_failures": total,
            "tool_gaps": [{"tool": tool, "missed_count": count}
                          for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1])],
        }

    def generate_report(self, include_history: bool = False) -> DebugReport:
        failures = self._failures
        if include_history:
            failures = self._pattern_history

        patterns = self.detect_patterns()
        total = len(failures)
        severity = "info"
        if total >= 10:
            severity = "critical"
        elif total >= 5:
            severity = "high"
        elif total >= 2:
            severity = "medium"

        recommendations = self._generate_recommendations(patterns, failures)

        return DebugReport(
            report_id=f"edr_{uuid.uuid4().hex[:12]}",
            failures=failures[-20:],
            pattern_summary=patterns,
            recommendations=recommendations,
            severity=severity,
        )

    def _generate_recommendations(self, patterns: Dict, failures: List[EpistemicFailure]) -> List[str]:
        recs = []
        dominant = patterns.get("dominant", "")

        if dominant == "missing_evidence":
            recs.append("Establish minimum evidence threshold before making claims")
            recs.append("Implement automated evidence gathering pipeline")
        elif dominant == "overconfidence":
            recs.append("Apply confidence penalty for claims with <3 evidence sources")
            recs.append("Implement automated contradiction check before high-confidence claims")
        elif dominant == "ignored_contradiction":
            recs.append("Surface contradictions explicitly before finalizing claims")
            recs.append("Require contradiction resolution for high-confidence assessments")
        elif dominant == "faulty_inference":
            recs.append("Limit inference depth to direct evidence for critical claims")
            recs.append("Require multi-hop reasoning to be explicitly traced")
        elif dominant == "hallucination":
            recs.append("Add hallucination detection pre-check before claim generation")
            recs.append("Ground all claims in specific code locations")

        if not recs:
            recs.append("Continue monitoring epistemic failure patterns")
            recs.append("Review individual failures for systemic issues")

        tool_gaps = patterns.get("tool_gaps", [])
        if tool_gaps:
            for tg in tool_gaps[:3]:
                if tg["missed_count"] >= 2:
                    recs.append(f"Prioritize using {tg['tool']} earlier in investigation workflow")

        return recs

    def get_recent_failures(self, limit: int = 10) -> List[EpistemicFailure]:
        return self._failures[-limit:]

    def clear(self):
        self._failures.clear()

    @property
    def failures(self) -> List[EpistemicFailure]:
        return self._failures
