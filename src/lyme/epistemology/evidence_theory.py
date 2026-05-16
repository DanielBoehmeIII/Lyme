from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import math
import uuid


class EvidenceType(str, Enum):
    CODE = "code"
    TEST = "test"
    RUNTIME_TRACE = "runtime_trace"
    DOCUMENTATION = "documentation"
    GIT_HISTORY = "git_history"
    USER_STATEMENT = "user_statement"
    PACKAGE_METADATA = "package_metadata"
    ECOSYSTEM_KNOWLEDGE = "ecosystem_knowledge"
    BENCHMARK_RESULT = "benchmark_result"
    SKILL_TRANSFER = "skill_transfer"
    CROSS_REPO_PATTERN = "cross_repo_pattern"
    INVARIANT = "invariant"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"


class EvidenceSource(str, Enum):
    STATIC_ANALYSIS = "static_analysis"
    DYNAMIC_ANALYSIS = "dynamic_analysis"
    ECOSYSTEM_DB = "ecosystem_db"
    GIT_LOG = "git_log"
    USER_INPUT = "user_input"
    TEST_RUNNER = "test_runner"
    PACKAGE_REGISTRY = "package_registry"
    CROSS_REPO_MINING = "cross_repo_mining"
    BENCHMARK = "benchmark"
    OBSERVATION = "observation"


class ClaimStrength(str, Enum):
    CERTAIN = "certain"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


class InferenceDepth(str, Enum):
    DIRECT = "direct"
    FIRST_HOP = "first_hop"
    SECOND_HOP = "second_hop"
    DEEP = "deep"


class HallucinationRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class Evidence:
    id: str
    evidence_type: EvidenceType
    source: EvidenceSource
    content: str
    source_location: str
    reliability: float
    timestamp: float = 0.0
    confidence: float = 1.0
    contradictions: List[str] = field(default_factory=list)
    corroborating: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "evidence_type": self.evidence_type.value,
            "source": self.source.value,
            "content": self.content[:200],
            "source_location": self.source_location,
            "reliability": self.reliability,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "contradictions": self.contradictions,
            "corroborating": self.corroborating,
        }


@dataclass
class Claim:
    id: str
    statement: str
    evidence: List[Evidence] = field(default_factory=list)
    strength: ClaimStrength = ClaimStrength.WEAK
    inference_depth: InferenceDepth = InferenceDepth.DIRECT
    hallucination_risk: HallucinationRisk = HallucinationRisk.HIGH
    confidence: float = 0.0
    uncertainty: float = 1.0
    contradicted_by: List[str] = field(default_factory=list)
    supported_by: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    domain: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "evidence": [e.to_dict() for e in self.evidence],
            "strength": self.strength.value,
            "inference_depth": self.inference_depth.value,
            "hallucination_risk": self.hallucination_risk.value,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "contradicted_by": self.contradicted_by,
            "supported_by": self.supported_by,
            "missing_evidence": self.missing_evidence,
            "domain": self.domain,
        }


@dataclass
class ClaimAssessment:
    claim: Claim
    overall_confidence: float
    evidence_count: int
    source_reliability_avg: float
    contradiction_count: int
    inference_penalty: float
    hallucination_score: float
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "claim": self.claim.to_dict(),
            "overall_confidence": self.overall_confidence,
            "evidence_count": self.evidence_count,
            "source_reliability_avg": self.source_reliability_avg,
            "contradiction_count": self.contradiction_count,
            "inference_penalty": self.inference_penalty,
            "hallucination_score": self.hallucination_score,
            "recommendation": self.recommendation,
        }


class EvidenceAggregator:
    def __init__(self):
        self._source_reliability = {
            EvidenceSource.STATIC_ANALYSIS: 0.90,
            EvidenceSource.DYNAMIC_ANALYSIS: 0.85,
            EvidenceSource.TEST_RUNNER: 0.95,
            EvidenceSource.ECOSYSTEM_DB: 0.75,
            EvidenceSource.GIT_LOG: 0.80,
            EvidenceSource.USER_INPUT: 0.40,
            EvidenceSource.PACKAGE_REGISTRY: 0.70,
            EvidenceSource.CROSS_REPO_MINING: 0.65,
            EvidenceSource.BENCHMARK: 0.85,
            EvidenceSource.OBSERVATION: 0.50,
        }

        self._evidence_type_weights = {
            EvidenceType.CODE: 0.90,
            EvidenceType.TEST: 0.85,
            EvidenceType.RUNTIME_TRACE: 0.80,
            EvidenceType.DOCUMENTATION: 0.50,
            EvidenceType.GIT_HISTORY: 0.70,
            EvidenceType.USER_STATEMENT: 0.30,
            EvidenceType.PACKAGE_METADATA: 0.75,
            EvidenceType.ECOSYSTEM_KNOWLEDGE: 0.60,
            EvidenceType.BENCHMARK_RESULT: 0.85,
            EvidenceType.SKILL_TRANSFER: 0.65,
            EvidenceType.CROSS_REPO_PATTERN: 0.60,
            EvidenceType.INVARIANT: 0.80,
            EvidenceType.ARCHITECTURE_ANALYSIS: 0.75,
        }

    def aggregate(self, evidence_list: List[Evidence]) -> Dict:
        if not evidence_list:
            return {
                "total_weight": 0.0,
                "weighted_confidence": 0.5,
                "effective_reliability": 0.0,
                "evidence_count": 0,
                "source_diversity": 0.0,
            }

        total_weight = 0.0
        weighted_confidence = 0.0
        total_reliability = 0.0
        sources_seen = set()

        for ev in evidence_list:
            type_weight = self._evidence_type_weights.get(ev.evidence_type, 0.5)
            source_weight = self._source_reliability.get(ev.source, 0.5)
            effective_weight = type_weight * source_weight * ev.reliability

            source_certainty = ev.confidence
            total_weight += effective_weight
            weighted_confidence += effective_weight * source_certainty
            total_reliability += source_weight
            sources_seen.add(ev.source.value)

        base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5
        source_diversity = len(sources_seen) / len(EvidenceSource)

        return {
            "total_weight": round(total_weight, 3),
            "weighted_confidence": round(base_confidence, 3),
            "effective_reliability": round(total_reliability / len(evidence_list), 3) if evidence_list else 0.0,
            "evidence_count": len(evidence_list),
            "source_diversity": round(source_diversity, 3),
        }


class EvidenceTheoryEngine:
    def __init__(self):
        self._aggregator = EvidenceAggregator()
        self._claims: Dict[str, Claim] = {}

    def make_claim(self, statement: str, domain: str = "") -> Claim:
        claim = Claim(
            id=f"claim_{uuid.uuid4().hex[:12]}",
            statement=statement,
            domain=domain,
        )
        self._claims[claim.id] = claim
        return claim

    def add_evidence(self, claim_id: str, evidence: Evidence):
        claim = self._claims.get(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        claim.evidence.append(evidence)

    def assess_claim(self, claim_id: str) -> ClaimAssessment:
        claim = self._claims.get(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        agg = self._aggregator.aggregate(claim.evidence)

        base_confidence = agg["weighted_confidence"]
        evidence_count = agg["evidence_count"]
        source_reliability_avg = agg["effective_reliability"]

        contradiction_count = sum(1 for e in claim.evidence if e.contradictions)
        contradiction_penalty = 1.0 - (contradiction_count / max(evidence_count, 1)) * 0.5

        inference_penalty = {
            InferenceDepth.DIRECT: 1.0,
            InferenceDepth.FIRST_HOP: 0.85,
            InferenceDepth.SECOND_HOP: 0.70,
            InferenceDepth.DEEP: 0.50,
        }.get(claim.inference_depth, 0.5)

        hallucination_score = self._compute_hallucination_risk(base_confidence, evidence_count, contradiction_count, claim.inference_depth)
        hallucination_risk = self._score_to_hallucination_risk(hallucination_score)

        final_confidence = base_confidence * contradiction_penalty * inference_penalty
        final_confidence = max(0.0, min(1.0, final_confidence))

        claim.confidence = round(final_confidence, 3)
        claim.uncertainty = round(1.0 - final_confidence, 3)
        claim.strength = self._confidence_to_strength(final_confidence)
        claim.hallucination_risk = hallucination_risk

        recommendation = self._generate_recommendation(claim, final_confidence, evidence_count)

        return ClaimAssessment(
            claim=claim,
            overall_confidence=round(final_confidence, 3),
            evidence_count=evidence_count,
            source_reliability_avg=round(source_reliability_avg, 3),
            contradiction_count=contradiction_count,
            inference_penalty=round(1.0 - inference_penalty, 3),
            hallucination_score=round(hallucination_score, 3),
            recommendation=recommendation,
        )

    def _compute_hallucination_risk(self, confidence: float, evidence_count: int, contradictions: int, depth: InferenceDepth) -> float:
        base_risk = 1.0 - confidence
        if evidence_count == 0:
            base_risk = 0.9
        elif evidence_count == 1:
            base_risk = max(base_risk, 0.4)
        elif evidence_count >= 5:
            base_risk *= 0.5

        contradiction_risk = contradictions * 0.15

        depth_risk = {
            InferenceDepth.DIRECT: 0.0,
            InferenceDepth.FIRST_HOP: 0.1,
            InferenceDepth.SECOND_HOP: 0.2,
            InferenceDepth.DEEP: 0.35,
        }.get(depth, 0.3)

        return min(1.0, base_risk + contradiction_risk + depth_risk)

    def _score_to_hallucination_risk(self, score: float) -> HallucinationRisk:
        if score >= 0.8:
            return HallucinationRisk.VERY_HIGH
        if score >= 0.6:
            return HallucinationRisk.HIGH
        if score >= 0.4:
            return HallucinationRisk.MEDIUM
        if score >= 0.2:
            return HallucinationRisk.LOW
        return HallucinationRisk.NONE

    def _confidence_to_strength(self, confidence: float) -> ClaimStrength:
        if confidence >= 0.95:
            return ClaimStrength.CERTAIN
        if confidence >= 0.80:
            return ClaimStrength.STRONG
        if confidence >= 0.60:
            return ClaimStrength.MODERATE
        if confidence >= 0.30:
            return ClaimStrength.WEAK
        return ClaimStrength.SPECULATIVE

    def _generate_recommendation(self, claim: Claim, confidence: float, evidence_count: int) -> str:
        if evidence_count == 0:
            return "NO_EVIDENCE: Gather at least one source of evidence before acting"
        if confidence < 0.3:
            return "INSUFFICIENT: Evidence too weak. Seek corroborating sources or reduce claim scope"
        if confidence < 0.6:
            missing = claim.missing_evidence
            if missing:
                return f"CAUTION: Low confidence. Missing evidence: {', '.join(missing[:3])}. Seek additional sources"
            return "CAUTION: Low confidence. Consider gathering more evidence"
        if claim.contradicted_by:
            return f"CONTRADICTION: {len(claim.contradicted_by)} contradictory sources. Resolve before acting"
        if claim.hallucination_risk in (HallucinationRisk.HIGH, HallucinationRisk.VERY_HIGH):
            return f"HALLUCINATION RISK: {claim.hallucination_risk.value}. Verify with direct evidence"
        return "RELIABLE: Evidence sufficient for confident action"

    def detect_contradictions(self, claim_id: str) -> List[Dict]:
        claim = self._claims.get(claim_id)
        if not claim:
            return []

        contradictions = []
        ev_by_type: Dict[str, List[Evidence]] = {}
        for ev in claim.evidence:
            if ev.evidence_type.value not in ev_by_type:
                ev_by_type[ev.evidence_type.value] = []
            ev_by_type[ev.evidence_type.value].append(ev)

        for etype, ev_list in ev_by_type.items():
            if len(ev_list) >= 2:
                for i in range(len(ev_list)):
                    for j in range(i + 1, len(ev_list)):
                        if ev_list[i].confidence > 0.7 and ev_list[j].confidence > 0.3 and abs(ev_list[i].confidence - ev_list[j].confidence) > 0.5:
                            contradictions.append({
                                "type": "confidence_gap",
                                "evidence_a": ev_list[i].id,
                                "evidence_b": ev_list[j].id,
                                "gap": round(abs(ev_list[i].confidence - ev_list[j].confidence), 2),
                                "severity": "high" if abs(ev_list[i].confidence - ev_list[j].confidence) > 0.6 else "medium",
                            })

        return contradictions

    def find_missing_evidence(self, claim: Claim, available_types: Optional[List[EvidenceType]] = None) -> List[str]:
        types_present = {e.evidence_type for e in claim.evidence}
        all_types = set(EvidenceType)

        if available_types:
            all_types = set(available_types)

        missing = []
        priority_types = [EvidenceType.CODE, EvidenceType.TEST, EvidenceType.ARCHITECTURE_ANALYSIS]

        for pt in priority_types:
            if pt not in types_present:
                missing.append(f"Missing {pt.value} evidence")

        if claim.inference_depth != InferenceDepth.DIRECT and EvidenceType.RUNTIME_TRACE not in types_present:
            missing.append("Inference deeper than direct without runtime trace verification")

        return missing

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self._claims.get(claim_id)

    @property
    def claims(self) -> List[Claim]:
        return list(self._claims.values())
