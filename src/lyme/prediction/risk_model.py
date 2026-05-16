from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RiskCategory(str, Enum):
    BREAKAGE = "breakage"
    REGRESSION = "regression"
    TECHNICAL_DEBT = "technical_debt"
    TEST_FRAGILITY = "test_fragility"
    ARCHITECTURAL_INSTABILITY = "architectural_instability"
    HIDDEN_COUPLING = "hidden_coupling"
    COMPLEXITY = "complexity"


@dataclass
class RiskFactor:
    name: str = ""
    category: RiskCategory = RiskCategory.BREAKAGE
    score: float = 0.0
    weight: float = 1.0
    evidence: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "score": self.score,
            "weight": self.weight,
            "evidence": self.evidence[:200],
            "confidence": self.confidence,
        }

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class RiskScore:
    overall: float = 0.0
    factors: List[RiskFactor] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "factors": [f.to_dict() for f in self.factors],
            "confidence": self.confidence,
        }


@dataclass
class FileRiskProfile:
    file_path: str = ""
    subsystem: str = ""
    risk_score: RiskScore = field(default_factory=RiskScore)
    previous_failures: int = 0
    change_frequency: float = 0.0
    complexity: float = 0.0
    test_coverage: float = 0.0
    author_count: int = 0
    last_modified: float = 0.0
    predicted_breakpoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "subsystem": self.subsystem,
            "risk_score": self.risk_score.to_dict(),
            "previous_failures": self.previous_failures,
            "change_frequency": self.change_frequency,
            "complexity": self.complexity,
            "test_coverage": self.test_coverage,
            "author_count": self.author_count,
            "predicted_breakpoints": self.predicted_breakpoints[:5],
        }


@dataclass
class FailurePrediction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    file_profiles: List[FileRiskProfile] = field(default_factory=list)
    top_risks: List[Dict[str, Any]] = field(default_factory=list)
    evidence_trail: List[str] = field(default_factory=list)
    alternative_strategies: List[str] = field(default_factory=list)
    pipeline_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "file_profiles_count": len(self.file_profiles),
            "top_risks": self.top_risks[:10],
            "evidence_trail": self.evidence_trail[:5],
            "alternative_strategies": self.alternative_strategies[:5],
            "pipeline_confidence": self.pipeline_confidence,
        }


class PredictionPipeline:
    def __init__(self):
        self.predictions: List[FailurePrediction] = []

    def add_prediction(self, pred: FailurePrediction):
        self.predictions.append(pred)

    def get_latest(self) -> Optional[FailurePrediction]:
        return self.predictions[-1] if self.predictions else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_predictions": len(self.predictions),
            "latest": self.get_latest().to_dict() if self.get_latest() else None,
        }


class RiskModel:
    def __init__(self):
        self._profiles: Dict[str, FileRiskProfile] = {}

    def add_profile(self, profile: FileRiskProfile):
        self._profiles[profile.file_path] = profile

    def get_profile(self, file_path: str) -> Optional[FileRiskProfile]:
        return self._profiles.get(file_path)

    def get_high_risk(self, threshold: float = 0.7) -> List[FileRiskProfile]:
        return [
            p for p in self._profiles.values()
            if p.risk_score.overall >= threshold
        ]

    def get_risk_distribution(self) -> Dict[str, int]:
        distribution: Dict[str, int] = defaultdict(int)
        for p in self._profiles.values():
            if p.risk_score.overall >= 0.7:
                distribution["high"] += 1
            elif p.risk_score.overall >= 0.4:
                distribution["medium"] += 1
            elif p.risk_score.overall >= 0.2:
                distribution["low"] += 1
            else:
                distribution["negligible"] += 1
        return dict(distribution)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": len(self._profiles),
            "risk_distribution": self.get_risk_distribution(),
            "high_risk_files": [
                p.to_dict() for p in self.get_high_risk()
            ][:30],
        }
