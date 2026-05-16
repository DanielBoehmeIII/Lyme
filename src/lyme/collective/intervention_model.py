from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class InterventionType(str, Enum):
    CORRECTION = "correction"
    OVERRIDE = "override"
    RE_PROMPT = "re_prompt"
    IGNORED_SUGGESTION = "ignored_suggestion"
    ROLLBACK = "rollback"
    CLARIFICATION_REQUEST = "clarification_request"
    UNCERTAINTY_RESPONSE = "uncertainty_response"
    APPROVAL = "approval"
    REJECTION = "rejection"
    MANUAL_EDIT = "manual_edit"


class FailureCategory(str, Enum):
    INCORRECT_LOGIC = "incorrect_logic"
    HALLUCINATION = "hallucination"
    MISSING_CONTEXT = "missing_context"
    WRONG_TOOL = "wrong_tool"
    OVER_ENGINEERED = "over_engineered"
    TOO_NARROW = "too_narrow"
    BROKEN_EXISTING = "broken_existing"
    STYLE_MISMATCH = "style_mismatch"
    SECURITY_ISSUE = "security_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    UNKNOWN = "unknown"


class TrustLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNESTABLISHED = "unestablished"
    ERODED = "eroded"


@dataclass
class Intervention:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    intervention_type: InterventionType = InterventionType.CORRECTION
    timestamp: float = field(default_factory=time.time)
    agent_action_id: str = ""
    agent_action_description: str = ""
    file_path: str = ""
    user_comment: str = ""
    resolution: str = ""
    time_to_intervention_ms: float = 0.0
    context_length: int = 0
    subsystem: str = ""
    failure_category: FailureCategory = FailureCategory.UNKNOWN
    trust_impact: float = 0.0
    re_prompt_count: int = 0
    was_effective: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "intervention_type": self.intervention_type.value,
            "timestamp": self.timestamp,
            "agent_action_id": self.agent_action_id,
            "agent_action_description": self.agent_action_description[:200],
            "file_path": self.file_path,
            "user_comment": self.user_comment[:200],
            "resolution": self.resolution[:200],
            "time_to_intervention_ms": self.time_to_intervention_ms,
            "context_length": self.context_length,
            "subsystem": self.subsystem,
            "failure_category": self.failure_category.value,
            "trust_impact": self.trust_impact,
            "re_prompt_count": self.re_prompt_count,
            "was_effective": self.was_effective,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Intervention:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class InterventionFeedback:
    intervention_id: str = ""
    user_satisfaction: float = 0.0
    resolved_completely: bool = False
    time_spent_seconds: float = 0.0
    user_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "intervention_id": self.intervention_id,
            "user_satisfaction": self.user_satisfaction,
            "resolved_completely": self.resolved_completely,
            "time_spent_seconds": self.time_spent_seconds,
            "user_notes": self.user_notes[:200],
        }


@dataclass
class TrustMetrics:
    overall_trust: TrustLevel = TrustLevel.UNESTABLISHED
    trust_score: float = 0.0
    intervention_rate: float = 0.0
    correction_rate: float = 0.0
    rollback_rate: float = 0.0
    avg_time_to_intervention_ms: float = 0.0
    total_interventions: int = 0
    recent_trend: str = "stable"
    subsystem_trust: Dict[str, float] = field(default_factory=dict)
    failure_type_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall_trust": self.overall_trust.value,
            "trust_score": self.trust_score,
            "intervention_rate": self.intervention_rate,
            "correction_rate": self.correction_rate,
            "rollback_rate": self.rollback_rate,
            "avg_time_to_intervention_ms": self.avg_time_to_intervention_ms,
            "total_interventions": self.total_interventions,
            "recent_trend": self.recent_trend,
            "subsystem_trust": self.subsystem_trust,
            "failure_type_distribution": self.failure_type_distribution,
        }


@dataclass
class InterventionSummary:
    total_interventions: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_failure_category: Dict[str, int] = field(default_factory=dict)
    by_subsystem: Dict[str, int] = field(default_factory=dict)
    effectiveness_rate: float = 0.0
    most_common_failures: List[Dict[str, Any]] = field(default_factory=list)
    learning_recommendations: List[str] = field(default_factory=list)
    trust_timeline: List[Tuple[float, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_interventions": self.total_interventions,
            "by_type": self.by_type,
            "by_failure_category": self.by_failure_category,
            "by_subsystem": self.by_subsystem,
            "effectiveness_rate": self.effectiveness_rate,
            "most_common_failures": self.most_common_failures,
            "learning_recommendations": self.learning_recommendations,
            "trust_timeline": self.trust_timeline,
        }


class InterventionTracker:
    def __init__(self):
        self._interventions: List[Intervention] = []
        self._feedback: Dict[str, InterventionFeedback] = {}
        self._listeners: List[Callable] = []

    def record(self, intervention: Intervention):
        self._interventions.append(intervention)
        for listener in self._listeners:
            listener(intervention)

    def on_intervention(self, listener: Callable):
        self._listeners.append(listener)

    def add_feedback(self, feedback: InterventionFeedback):
        self._feedback[feedback.intervention_id] = feedback

    def get_interventions(self, intervention_type: InterventionType = None,
                          failure_category: FailureCategory = None,
                          subsystem: str = "", limit: int = 0) -> List[Intervention]:
        result = self._interventions
        if intervention_type:
            result = [i for i in result if i.intervention_type == intervention_type]
        if failure_category:
            result = [i for i in result if i.failure_category == failure_category]
        if subsystem:
            result = [i for i in result if i.subsystem == subsystem]
        result.sort(key=lambda i: i.timestamp, reverse=True)
        if limit > 0:
            result = result[:limit]
        return result

    def compute_trust_metrics(self, window_hours: float = 168.0) -> TrustMetrics:
        if not self._interventions:
            return TrustMetrics()
        now = time.time()
        recent = [i for i in self._interventions if now - i.timestamp < window_hours * 3600]
        total = len(self._interventions)
        recent_total = len(recent)

        if total == 0:
            return TrustMetrics()

        corrections = sum(1 for i in self._interventions if i.intervention_type == InterventionType.CORRECTION)
        rollbacks = sum(1 for i in self._interventions if i.intervention_type == InterventionType.ROLLBACK)
        effective = sum(1 for i in self._interventions if i.was_effective)
        avg_time = sum(i.time_to_intervention_ms for i in self._interventions) / total

        intervention_rate = recent_total / max(window_hours, 1)
        correction_rate = corrections / max(total, 1)
        rollback_rate = rollbacks / max(total, 1)
        effectiveness_rate = effective / max(total, 1)

        trust_score = max(0.0, min(1.0, (
            0.3 * (1 - intervention_rate / 10) +
            0.2 * (1 - correction_rate) +
            0.2 * (1 - rollback_rate) +
            0.15 * effectiveness_rate +
            0.15 * max(0, 1 - avg_time / 300000)
        )))

        if trust_score >= 0.7:
            overall = TrustLevel.HIGH
        elif trust_score >= 0.5:
            overall = TrustLevel.MEDIUM
        elif trust_score >= 0.3:
            overall = TrustLevel.LOW
        else:
            overall = TrustLevel.ERODED

        subsystem_trust: Dict[str, List[Intervention]] = defaultdict(list)
        for i in self._interventions:
            if i.subsystem:
                subsystem_trust[i.subsystem].append(i)
        subsystem_scores = {}
        for sub, interventions in subsystem_trust.items():
            sub_corrections = sum(1 for i in interventions if i.intervention_type == InterventionType.CORRECTION)
            subsystem_scores[sub] = max(0.0, 1.0 - sub_corrections / max(len(interventions), 1))

        failure_dist: Dict[str, int] = defaultdict(int)
        for i in self._interventions:
            failure_dist[i.failure_category.value] += 1

        return TrustMetrics(
            overall_trust=overall,
            trust_score=trust_score,
            intervention_rate=intervention_rate,
            correction_rate=correction_rate,
            rollback_rate=rollback_rate,
            avg_time_to_intervention_ms=avg_time,
            total_interventions=total,
            recent_trend=self._compute_trend(window_hours),
            subsystem_trust=subsystem_scores,
            failure_type_distribution=dict(failure_dist),
        )

    def summarize(self) -> InterventionSummary:
        summary = InterventionSummary(
            total_interventions=len(self._interventions),
        )
        for i in self._interventions:
            summary.by_type[i.intervention_type.value] = summary.by_type.get(i.intervention_type.value, 0) + 1
            summary.by_failure_category[i.failure_category.value] = summary.by_failure_category.get(i.failure_category.value, 0) + 1
            if i.subsystem:
                summary.by_subsystem[i.subsystem] = summary.by_subsystem.get(i.subsystem, 0) + 1
            if i.was_effective:
                summary.effectiveness_rate += 1
        summary.effectiveness_rate /= max(len(self._interventions), 1)

        sorted_failures = sorted(
            summary.by_failure_category.items(),
            key=lambda x: -x[1]
        )[:5]
        summary.most_common_failures = [
            {"category": cat, "count": count}
            for cat, count in sorted_failures
        ]

        summary.learning_recommendations = self._generate_recommendations(summary)

        trust_history = []
        interval = max(len(self._interventions) // 10, 1)
        for i in range(0, len(self._interventions), interval):
            batch = self._interventions[i:i + interval]
            corrections = sum(1 for b in batch if b.intervention_type == InterventionType.CORRECTION)
            trust = 1.0 - corrections / max(len(batch), 1)
            trust_history.append((batch[0].timestamp, trust))
        summary.trust_timeline = trust_history

        return summary

    def get_intervention_rate_by_subsystem(self) -> Dict[str, float]:
        subsystems: Dict[str, int] = defaultdict(int)
        for i in self._interventions:
            if i.subsystem:
                subsystems[i.subsystem] += 1
        total = sum(subsystems.values())
        if total == 0:
            return {}
        return {sub: count / total for sub, count in subsystems.items()}

    def _compute_trend(self, window_hours: float) -> str:
        half = window_hours / 2
        now = time.time()
        recent_half = [i for i in self._interventions if now - i.timestamp < half * 3600]
        older_half = [i for i in self._interventions if half * 3600 <= now - i.timestamp < window_hours * 3600]
        recent_rate = len(recent_half) / max(half, 1)
        older_rate = len(older_half) / max(half, 1)
        if recent_rate < older_rate * 0.7:
            return "improving"
        elif recent_rate > older_rate * 1.3:
            return "degrading"
        return "stable"

    def _generate_recommendations(self, summary: InterventionSummary) -> List[str]:
        recs = []
        if summary.by_type.get(InterventionType.CORRECTION.value, 0) > summary.total_interventions * 0.3:
            recs.append("High correction rate - consider providing more context before tasks")
        if summary.by_type.get(InterventionType.ROLLBACK.value, 0) > 5:
            recs.append("Frequent rollbacks - implement pre-edit verification")
        if summary.by_failure_category.get(FailureCategory.MISSING_CONTEXT.value, 0) > 3:
            recs.append("Agent frequently lacks context - increase context window or improve retrieval")
        if summary.by_failure_category.get(FailureCategory.HALLUCINATION.value, 0) > 3:
            recs.append("Hallucination detected - ground responses in verified sources")
        if summary.by_failure_category.get(FailureCategory.STYLE_MISMATCH.value, 0) > 3:
            recs.append("Style mismatches - provide code style guidelines upfront")
        if not recs:
            recs.append("No systemic issues detected - continue monitoring")
        return recs


class InterventionLearningPipeline:
    def __init__(self, tracker: InterventionTracker):
        self.tracker = tracker
        self._failure_patterns: Dict[str, List[Intervention]] = defaultdict(list)

    def learn_patterns(self) -> Dict[str, Any]:
        for intervention in self.tracker._interventions:
            key = f"{intervention.subsystem}:{intervention.failure_category.value}"
            self._failure_patterns[key].append(intervention)

        patterns = {}
        for key, interventions in self._failure_patterns.items():
            if len(interventions) >= 3:
                subsystem, failure = key.split(":", 1)
                patterns[key] = {
                    "subsystem": subsystem,
                    "failure_category": failure,
                    "frequency": len(interventions),
                    "avg_time_to_catch": sum(
                        i.time_to_intervention_ms for i in interventions
                    ) / len(interventions),
                    "suggestion": self._pattern_suggestion(failure, subsystem),
                }
        return {
            "total_patterns": len(patterns),
            "patterns": patterns,
            "high_frequency": [
                {k: v for k, v in p.items() if k != "suggestion"}
                for p in sorted(patterns.values(), key=lambda x: -x["frequency"])[:5]
            ],
        }

    def predict_intervention_need(self, action_description: str,
                                   subsystem: str = "") -> Dict[str, Any]:
        matching = []
        for key, interventions in self._failure_patterns.items():
            if subsystem and subsystem in key:
                for i in interventions:
                    score = self._similarity_score(action_description, i.agent_action_description)
                    if score > 0.3:
                        matching.append({
                            "pattern_key": key,
                            "similarity": score,
                            "failure_category": i.failure_category.value,
                            "previous_interventions": len(interventions),
                        })
        matching.sort(key=lambda x: -x["similarity"])
        return {
            "needs_monitoring": len(matching) > 0,
            "likely_failures": matching[:3],
            "intervention_probability": min(1.0, len(matching) * 0.2),
        }

    def _pattern_suggestion(self, failure: str, subsystem: str) -> str:
        suggestions = {
            FailureCategory.MISSING_CONTEXT.value: f"Provide subsystem documentation for {subsystem}",
            FailureCategory.HALLUCINATION.value: f"Restrict {subsystem} to known APIs only",
            FailureCategory.INCORRECT_LOGIC.value: f"Add test cases for {subsystem} edge cases",
            FailureCategory.STYLE_MISMATCH.value: f"Provide code style guide for {subsystem}",
        }
        return suggestions.get(failure, f"Monitor {subsystem} for recurring {failure}")

    def _similarity_score(self, a: str, b: str) -> float:
        words_a = set(a.lower().split()[:20])
        words_b = set(b.lower().split()[:20])
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        return len(intersection) / math.sqrt(len(words_a) * len(words_b))
