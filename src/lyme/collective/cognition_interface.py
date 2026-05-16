from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ExplanationFormat(str, Enum):
    NARRATIVE = "narrative"
    CAUSAL_GRAPH = "causal_graph"
    EVIDENCE_LIST = "evidence_list"
    ASSUMPTION_AUDIT = "assumption_audit"
    TIMELINE = "timeline"
    CONFIDENCE_BREAKDOWN = "confidence_breakdown"
    COMPARISON = "comparison"


class ReasoningDepth(str, Enum):
    SHALLOW = "shallow"
    MODERATE = "moderate"
    DEEP = "deep"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ReasoningTrace:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    question: str = ""
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)
    evidence_used: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    confidence: float = 0.0
    depth: ReasoningDepth = ReasoningDepth.MODERATE
    duration_ms: float = 0.0
    conclusion: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "question": self.question,
            "reasoning_steps": self.reasoning_steps,
            "evidence_used": self.evidence_used,
            "assumptions": self.assumptions,
            "alternatives_considered": self.alternatives_considered,
            "confidence": self.confidence,
            "depth": self.depth.value,
            "duration_ms": self.duration_ms,
            "conclusion": self.conclusion,
        }


@dataclass
class UncertaintyEvidence:
    source: str = ""
    claim: str = ""
    confidence: float = 0.0
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    mitigating_assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "claim": self.claim,
            "confidence": self.confidence,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "knowledge_gaps": self.knowledge_gaps,
            "mitigating_assumptions": self.mitigating_assumptions,
        }


@dataclass
class CausalExplanation:
    phenomenon: str = ""
    direct_causes: List[Dict[str, Any]] = field(default_factory=list)
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    mechanisms: List[str] = field(default_factory=list)
    evidence_chain: List[str] = field(default_factory=list)
    confidence: float = 0.0
    alternative_hypotheses: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phenomenon": self.phenomenon,
            "direct_causes": self.direct_causes,
            "contributing_factors": self.contributing_factors,
            "mechanisms": self.mechanisms,
            "evidence_chain": self.evidence_chain,
            "confidence": self.confidence,
            "alternative_hypotheses": self.alternative_hypotheses,
        }


@dataclass
class CoordinationSummary:
    active_collaborators: int = 0
    pending_decisions: List[str] = field(default_factory=list)
    resolved_decisions: List[str] = field(default_factory=list)
    active_disagreements: List[Dict[str, Any]] = field(default_factory=list)
    shared_context_items: List[str] = field(default_factory=list)
    recent_actions: List[Dict[str, Any]] = field(default_factory=list)
    next_suggested_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "active_collaborators": self.active_collaborators,
            "pending_decisions": self.pending_decisions,
            "resolved_decisions": self.resolved_decisions,
            "active_disagreements": self.active_disagreements,
            "shared_context_items": self.shared_context_items,
            "recent_actions": self.recent_actions,
            "next_suggested_steps": self.next_suggested_steps,
        }


@dataclass
class SharedBeliefState:
    topic: str = ""
    shared_understanding: str = ""
    confidence_distribution: Dict[str, float] = field(default_factory=dict)
    unresolved_questions: List[str] = field(default_factory=list)
    agreement_level: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "shared_understanding": self.shared_understanding,
            "confidence_distribution": self.confidence_distribution,
            "unresolved_questions": self.unresolved_questions,
            "agreement_level": self.agreement_level,
            "last_updated": self.last_updated,
        }


class CognitionInterface:
    def __init__(self):
        self._traces: List[ReasoningTrace] = []
        self._explanations: List[CausalExplanation] = []
        self._beliefs: Dict[str, SharedBeliefState] = {}

    def record_reasoning(self, trace: ReasoningTrace):
        self._traces.append(trace)

    def explain(self, explanation: CausalExplanation):
        self._explanations.append(explanation)

    def update_belief(self, belief: SharedBeliefState):
        self._beliefs[belief.topic] = belief

    def format_explanation(self, trace: ReasoningTrace,
                           format: ExplanationFormat = ExplanationFormat.NARRATIVE) -> str:
        formatters = {
            ExplanationFormat.NARRATIVE: self._format_narrative,
            ExplanationFormat.EVIDENCE_LIST: self._format_evidence_list,
            ExplanationFormat.ASSUMPTION_AUDIT: self._format_assumption_audit,
            ExplanationFormat.CONFIDENCE_BREAKDOWN: self._format_confidence_breakdown,
        }
        formatter = formatters.get(format, self._format_narrative)
        return formatter(trace)

    def format_causal_explanation(self, explanation: CausalExplanation) -> str:
        lines = []
        lines.append(f"## Causal Explanation: {explanation.phenomenon}")
        lines.append(f"Confidence: {explanation.confidence:.1%}")
        lines.append("")
        if explanation.direct_causes:
            lines.append("### Direct Causes:")
            for cause in explanation.direct_causes:
                lines.append(f"- {cause.get('description', '')} (confidence: {cause.get('confidence', 0):.1%})")
        if explanation.contributing_factors:
            lines.append("### Contributing Factors:")
            for factor in explanation.contributing_factors:
                lines.append(f"- {factor.get('description', '')}")
        if explanation.mechanisms:
            lines.append("### Mechanisms:")
            for mech in explanation.mechanisms:
                lines.append(f"- {mech}")
        if explanation.evidence_chain:
            lines.append("### Evidence Chain:")
            for i, evidence in enumerate(explanation.evidence_chain, 1):
                lines.append(f"  {i}. {evidence}")
        if explanation.alternative_hypotheses:
            lines.append("### Alternative Hypotheses:")
            for alt in explanation.alternative_hypotheses:
                lines.append(f"- {alt}")
        return "\n".join(lines)

    def format_coordination_summary(self, summary: CoordinationSummary) -> str:
        lines = []
        lines.append(f"## Coordination Summary ({summary.active_collaborators} active)")
        if summary.pending_decisions:
            lines.append("### Pending Decisions:")
            for d in summary.pending_decisions:
                lines.append(f"- {d}")
        if summary.active_disagreements:
            lines.append("### Active Disagreements:")
            for d in summary.active_disagreements:
                lines.append(f"- {d.get('topic', '')}: {d.get('positions', [])}")
        if summary.shared_context_items:
            lines.append(f"Shared context: {len(summary.shared_context_items)} items")
        if summary.recent_actions:
            lines.append("### Recent Actions:")
            for a in summary.recent_actions[-5:]:
                lines.append(f"- {a.get('actor', '')}: {a.get('action', '')}")
        if summary.next_suggested_steps:
            lines.append("### Suggested Next Steps:")
            for s in summary.next_suggested_steps:
                lines.append(f"- {s}")
        return "\n".join(lines)

    def format_belief_state(self, belief: SharedBeliefState) -> str:
        lines = []
        lines.append(f"## Shared Understanding: {belief.topic}")
        lines.append(f"Agreement level: {belief.agreement_level:.1%}")
        lines.append(f"Understanding: {belief.shared_understanding}")
        if belief.confidence_distribution:
            lines.append("### Confidence Distribution:")
            for participant, conf in belief.confidence_distribution.items():
                bars = "█" * int(conf * 20)
                lines.append(f"  {participant}: {bars} {conf:.1%}")
        if belief.unresolved_questions:
            lines.append("### Unresolved Questions:")
            for q in belief.unresolved_questions:
                lines.append(f"- {q}")
        return "\n".join(lines)

    def format_uncertainty_report(self, uncertainties: List[UncertaintyEvidence]) -> str:
        lines = []
        lines.append("## Uncertainty Report")
        for i, u in enumerate(uncertainties, 1):
            lines.append(f"\n### {i}. {u.claim} (confidence: {u.confidence:.1%})")
            lines.append(f"Source: {u.source}")
            if u.supporting_evidence:
                lines.append("Supporting:")
                for e in u.supporting_evidence[:3]:
                    lines.append(f"  + {e}")
            if u.contradicting_evidence:
                lines.append("Contradicting:")
                for e in u.contradicting_evidence[:3]:
                    lines.append(f"  - {e}")
            if u.knowledge_gaps:
                lines.append("Knowledge Gaps:")
                for g in u.knowledge_gaps[:3]:
                    lines.append(f"  ? {g}")
            if u.mitigating_assumptions:
                lines.append("Assumptions:")
                for a in u.mitigating_assumptions[:3]:
                    lines.append(f"  * {a}")
        return "\n".join(lines)

    def _format_narrative(self, trace: ReasoningTrace) -> str:
        lines = [f"## Reasoning: {trace.question}", ""]
        for i, step in enumerate(trace.reasoning_steps, 1):
            desc = step.get("description", step.get("step", ""))
            step_conf = step.get("confidence", trace.confidence)
            lines.append(f"Step {i}: {desc} (confidence: {step_conf:.1%})")
        lines.append("")
        if trace.evidence_used:
            lines.append("Evidence used:")
            for e in trace.evidence_used[:5]:
                lines.append(f"  - {e}")
        lines.append(f"\nConclusion: {trace.conclusion}")
        lines.append(f"Overall confidence: {trace.confidence:.1%}")
        return "\n".join(lines)

    def _format_evidence_list(self, trace: ReasoningTrace) -> str:
        lines = [f"## Evidence: {trace.question}", ""]
        for i, evidence in enumerate(trace.evidence_used, 1):
            lines.append(f"{i}. {evidence}")
        if trace.assumptions:
            lines.append("\nAssumptions made:")
            for a in trace.assumptions:
                lines.append(f"  - {a}")
        return "\n".join(lines)

    def _format_assumption_audit(self, trace: ReasoningTrace) -> str:
        lines = [f"## Assumption Audit: {trace.question}", ""]
        for i, assumption in enumerate(trace.assumptions, 1):
            criticality = "CRITICAL" if i < len(trace.assumptions) * 0.3 else "SUPPORTING"
            lines.append(f"{i}. [{criticality}] {assumption}")
        if trace.alternatives_considered:
            lines.append("\nAlternatives considered:")
            for a in trace.alternatives_considered:
                lines.append(f"  - {a}")
        return "\n".join(lines)

    def _format_confidence_breakdown(self, trace: ReasoningTrace) -> str:
        lines = [f"## Confidence Breakdown: {trace.question}", ""]
        lines.append(f"Overall: {trace.confidence:.1%}")
        lines.append(f"Depth: {trace.depth.value}")
        lines.append(f"Duration: {trace.duration_ms:.0f}ms")
        lines.append("")
        for i, step in enumerate(trace.reasoning_steps, 1):
            desc = step.get("description", step.get("step", ""))
            conf = step.get("confidence", 0.5)
            bars = "█" * int(conf * 20)
            lines.append(f"  Step {i}: {bars} {conf:.1%} - {desc}")
        return "\n".join(lines)

    def get_reasoning_history(self, limit: int = 10) -> List[ReasoningTrace]:
        return sorted(self._traces, key=lambda t: t.timestamp, reverse=True)[:limit]
