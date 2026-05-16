from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict


class ConfidenceLevel(str, Enum):
    CERTAIN = "certain"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


@dataclass
class EvidenceSignal:
    source: str = ""
    relation_type: str = ""
    strength: float = 0.0
    recency: float = 0.0
    consistency: float = 0.0
    directness: float = 0.0
    frequency: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def composite_score(self) -> float:
        return (
            self.strength * 0.3 +
            self.recency * 0.15 +
            self.consistency * 0.2 +
            self.directness * 0.2 +
            min(1.0, self.frequency / 10) * 0.15
        )


class ConfidenceScorer:
    SOURCE_WEIGHTS = {
        "static import analysis": 0.95,
        "co-change": 0.7,
        "function call analysis": 0.6,
        "shared variable reference": 0.4,
        "API contract: consumer-provider": 0.7,
        "test imports source module": 0.5,
        "shared global state": 0.4,
        "temporal proximity": 0.3,
        "runtime trace": 0.8,
        "event propagation": 0.65,
        "config dependency": 0.5,
        "inheritance hierarchy": 0.85,
        "interface implementation": 0.8,
        "documentation reference": 0.2,
    }

    def __init__(self, fallback_confidence: float = 0.5):
        self.fallback_confidence = fallback_confidence

    def score(self, signals: List[EvidenceSignal]) -> float:
        if not signals:
            return self.fallback_confidence

        composite_scores = [s.composite_score for s in signals]
        n = len(signals)

        mean_score = sum(composite_scores) / n
        max_score = max(composite_scores)

        diversity_bonus = min(0.2, n * 0.05)
        confidence_gap = max_score - mean_score

        if confidence_gap > 0.3:
            max_score *= 1.1

        final = min(1.0, (mean_score * 0.6 + max_score * 0.4) + diversity_bonus)
        return final

    def classify(self, confidence: float) -> ConfidenceLevel:
        if confidence >= 0.9:
            return ConfidenceLevel.CERTAIN
        elif confidence >= 0.7:
            return ConfidenceLevel.STRONG
        elif confidence >= 0.5:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.3:
            return ConfidenceLevel.WEAK
        else:
            return ConfidenceLevel.SPECULATIVE

    def aggregate_multiple_edges(self, confidences: List[float]) -> float:
        if not confidences:
            return 0.0
        bayesian_numerator = sum(c / (1 - c + 0.001) for c in confidences)
        bayesian_denominator = bayesian_numerator + 1
        return bayesian_numerator / bayesian_denominator if bayesian_denominator > 0 else 0.5

    def weighted_combination(
        self,
        evidence_signals: Dict[str, List[EvidenceSignal]]
    ) -> Dict[str, float]:
        results = {}
        for source, signals in evidence_signals.items():
            base_weight = self.SOURCE_WEIGHTS.get(source, self.fallback_confidence)
            if not signals:
                results[source] = base_weight
                continue
            signal_score = self.score(signals)
            results[source] = min(1.0, base_weight * 0.4 + signal_score * 0.6)
        return results

    def estimate_uncertainty(self, confidence: float, evidence_count: int) -> Dict[str, float]:
        base_uncertainty = 1.0 - confidence
        evidence_reduction = min(0.5, evidence_count * 0.05)
        uncertainty = max(0.05, base_uncertainty - evidence_reduction)

        return {
            "uncertainty": uncertainty,
            "confidence": confidence,
            "evidence_count": evidence_count,
            "information_gap": max(0, 1.0 - confidence - evidence_reduction),
            "needs_more_evidence": uncertainty > 0.3,
        }
