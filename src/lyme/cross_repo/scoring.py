from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import math


class EvidenceSource(str, Enum):
    CODE_ANALYSIS = "code_analysis"
    GIT_HISTORY = "git_history"
    TEST_RESULTS = "test_results"
    DEPENDENCY_AUDIT = "dependency_audit"
    USER_FEEDBACK = "user_feedback"
    BENCHMARK = "benchmark"
    CROSS_REPO_VALIDATION = "cross_repo_validation"
    ECOSYSTEM_KNOWLEDGE = "ecosystem_knowledge"


@dataclass
class EvidenceSourceInfo:
    source: EvidenceSource
    weight: float
    confidence: float
    count: int


@dataclass
class ConfidenceBreakdown:
    overall: float
    by_source: Dict[str, float]
    uncertainty: float
    contradictory_evidence: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall": self.overall,
            "by_source": self.by_source,
            "uncertainty": self.uncertainty,
            "contradictory_evidence": self.contradictory_evidence,
            "missing_evidence": self.missing_evidence,
        }


class PatternScorer:
    def __init__(self):
        self._source_weights = {
            EvidenceSource.CODE_ANALYSIS: 0.85,
            EvidenceSource.GIT_HISTORY: 0.75,
            EvidenceSource.TEST_RESULTS: 0.90,
            EvidenceSource.DEPENDENCY_AUDIT: 0.70,
            EvidenceSource.USER_FEEDBACK: 0.50,
            EvidenceSource.BENCHMARK: 0.80,
            EvidenceSource.CROSS_REPO_VALIDATION: 0.85,
            EvidenceSource.ECOSYSTEM_KNOWLEDGE: 0.65,
        }

    def score_pattern(self, pattern) -> ConfidenceBreakdown:
        by_source: Dict[str, float] = {}
        source_info = self._gather_evidence(pattern)
        total_weight = 0.0
        weighted_sum = 0.0

        for info in source_info:
            effective = info.weight * (1.0 - (1.0 / (info.count + 1)))
            by_source[info.source.value] = round(effective, 3)
            weighted_sum += effective * info.confidence
            total_weight += effective

        overall = weighted_sum / total_weight if total_weight > 0 else 0.5
        uncertainty = 1.0 - min(len(source_info) / 5.0, 1.0)

        contradictory = self._find_contradictions(pattern)
        missing = self._find_missing_evidence(pattern)

        return ConfidenceBreakdown(
            overall=round(overall, 3),
            by_source=by_source,
            uncertainty=round(uncertainty, 3),
            contradictory_evidence=contradictory,
            missing_evidence=missing,
        )

    def _gather_evidence(self, pattern) -> List[EvidenceSourceInfo]:
        infos: List[EvidenceSourceInfo] = []

        if pattern.occurrences >= 2:
            infos.append(EvidenceSourceInfo(
                source=EvidenceSource.CROSS_REPO_VALIDATION,
                weight=self._source_weights[EvidenceSource.CROSS_REPO_VALIDATION],
                confidence=min(pattern.occurrences / 10.0, 1.0),
                count=pattern.occurrences,
            ))

        if pattern.sources:
            avg_conf = sum(s.confidence for s in pattern.sources) / len(pattern.sources)
            infos.append(EvidenceSourceInfo(
                source=EvidenceSource.CODE_ANALYSIS,
                weight=self._source_weights[EvidenceSource.CODE_ANALYSIS],
                confidence=avg_conf,
                count=len(pattern.sources),
            ))

        if pattern.transfer_success_rate > 0:
            infos.append(EvidenceSourceInfo(
                source=EvidenceSource.BENCHMARK,
                weight=self._source_weights[EvidenceSource.BENCHMARK],
                confidence=pattern.transfer_success_rate,
                count=max(int(pattern.transfer_success_rate * 10), 1),
            ))

        if pattern.variants:
            infos.append(EvidenceSourceInfo(
                source=EvidenceSource.ECOSYSTEM_KNOWLEDGE,
                weight=self._source_weights[EvidenceSource.ECOSYSTEM_KNOWLEDGE],
                confidence=0.6,
                count=len(pattern.variants),
            ))

        return infos

    def _find_contradictions(self, pattern) -> List[str]:
        contradictions = []
        if pattern.transfer_success_rate < 0.3 and pattern.occurrences > 5:
            contradictions.append("High occurrence but low transfer success rate")
        if pattern.severity.value == "info" and any(s.confidence > 0.9 for s in pattern.sources):
            pass
        return contradictions

    def _find_missing_evidence(self, pattern) -> List[str]:
        missing = []
        if pattern.transfer_success_rate == 0.0 and pattern.occurrences >= 3:
            missing.append("No transfer benchmark data")
        if not pattern.variants:
            missing.append("No variant analysis")
        if not any(s.source == EvidenceSource.GIT_HISTORY for s in self._gather_evidence(pattern)):
            missing.append("No git history analysis")
        return missing

    def cross_validate(self, pattern, fingerprints: List) -> float:
        matching = 0
        total = 0
        for fp in fingerprints:
            for dep in fp.dependency_signature:
                if dep.category in str(pattern.signature):
                    matching += 1
                    total += 1
                    break
            total += 1
        return matching / max(total, 1)

    def calibrate(self, predictions: List[Tuple[float, bool]]) -> Dict:
        if not predictions:
            return {"bias": 0.0, "mae": 0.0, "calibration_slope": 1.0}

        errors = [(pred - (1.0 if actual else 0.0)) for pred, actual in predictions]
        mae = sum(abs(e) for e in errors) / len(errors)
        bias = sum(errors) / len(errors)

        correct = sum(1 for p, a in predictions if (p > 0.5) == a)
        accuracy = correct / len(predictions)

        return {
            "bias": round(bias, 3),
            "mae": round(mae, 3),
            "accuracy": round(accuracy, 3),
            "calibration_slope": round(1.0 - bias, 3),
            "n_samples": len(predictions),
        }
