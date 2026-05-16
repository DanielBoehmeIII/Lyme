from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class IntentType(str, Enum):
    SUBSYSTEM_PURPOSE = "subsystem_purpose"
    BUSINESS_GOAL = "business_goal"
    DESIGN_PHILOSOPHY = "design_philosophy"
    PERFORMANCE_PRIORITY = "performance_priority"
    SAFETY_CONSTRAINT = "safety_constraint"
    ARCHITECTURAL_DECISION = "architectural_decision"
    TRADEOFF = "tradeoff"
    CONSTRAINT = "constraint"
    EVOLUTION_DIRECTION = "evolution_direction"
    TECHNICAL_DEBT = "technical_debt"


class DesignPhilosophy(str, Enum):
    LAYERED_ARCHITECTURE = "layered_architecture"
    HEXAGONAL = "hexagonal"
    MICROSERVICES = "microservices"
    MONOLITHIC = "monolithic"
    EVENT_DRIVEN = "event_driven"
    DOMAIN_DRIVEN = "domain_driven"
    DATA_CENTRIC = "data_centric"
    API_FIRST = "api_first"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class EvolutionDirection(str, Enum):
    TOWARD_SERVICE = "toward_service"
    TOWARD_MODULARITY = "toward_modularity"
    TOWARD_MONOLITH = "toward_monolith"
    TOWARD_ABSTRACTION = "toward_abstraction"
    TOWARD_PERFORMANCE = "toward_performance"
    TOWARD_SIMPLICITY = "toward_simplicity"
    TOWARD_COMPLEXITY = "toward_complexity"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class IntentEvidence:
    source: str = ""
    evidence_type: str = ""
    content: str = ""
    confidence: float = 0.0
    file_path: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "evidence_type": self.evidence_type,
            "content": self.content[:200],
            "confidence": self.confidence,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
        }


@dataclass
class IntentUncertainty:
    overall: float = 0.0
    evidence_gap: float = 0.0
    contradiction_level: float = 0.0
    staleness: float = 0.0
    missing_domains: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "evidence_gap": self.evidence_gap,
            "contradiction_level": self.contradiction_level,
            "staleness": self.staleness,
            "missing_domains": self.missing_domains,
        }


@dataclass
class Tradeoff:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    chosen_path: str = ""
    rejected_path: str = ""
    rationale: str = ""
    cost: str = ""
    benefit: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "chosen_path": self.chosen_path,
            "rejected_path": self.rejected_path,
            "rationale": self.rationale,
            "cost": self.cost,
            "benefit": self.benefit,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class SubsystemIntent:
    subsystem: str = ""
    purpose: str = ""
    design_philosophy: DesignPhilosophy = DesignPhilosophy.UNKNOWN
    performance_priority: str = ""
    safety_constraints: List[str] = field(default_factory=list)
    tradeoffs: List[Tradeoff] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    evolution: List[str] = field(default_factory=list)
    evidence: List[IntentEvidence] = field(default_factory=list)
    uncertainty: IntentUncertainty = field(default_factory=IntentUncertainty)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "purpose": self.purpose,
            "design_philosophy": self.design_philosophy.value,
            "performance_priority": self.performance_priority,
            "safety_constraints": self.safety_constraints,
            "tradeoffs": [t.to_dict() for t in self.tradeoffs],
            "constraints": self.constraints[:10],
            "evolution": self.evolution[:5],
            "evidence_count": len(self.evidence),
            "uncertainty": self.uncertainty.to_dict(),
            "confidence": self.confidence,
        }


@dataclass
class IntentModel:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    repo_path: str = ""
    intents: List[SubsystemIntent] = field(default_factory=list)
    overall_philosophy: DesignPhilosophy = DesignPhilosophy.UNKNOWN
    evolution_direction: EvolutionDirection = EvolutionDirection.UNKNOWN
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "repo_path": self.repo_path,
            "subsystems": [s.to_dict() for s in self.intents],
            "overall_philosophy": self.overall_philosophy.value,
            "evolution_direction": self.evolution_direction.value,
            "created_at": self.created_at,
        }

    def add_subsystem_intent(self, intent: SubsystemIntent):
        self.intents.append(intent)

    def get_subsystem(self, name: str) -> Optional[SubsystemIntent]:
        for si in self.intents:
            if si.subsystem == name:
                return si
        return None


class IntentGraph:
    def __init__(self):
        self._models: List[IntentModel] = []
        self._model_by_repo: Dict[str, IntentModel] = {}

    def add_model(self, model: IntentModel):
        self._models.append(model)
        self._model_by_repo[model.repo_path] = model

    def get_model(self, repo_path: str) -> Optional[IntentModel]:
        return self._model_by_repo.get(repo_path)

    def compare_models(self, repo_a: str, repo_b: str) -> Dict[str, Any]:
        a = self._model_by_repo.get(repo_a)
        b = self._model_by_repo.get(repo_b)
        if not a or not b:
            return {"error": "one or both models not found"}

        a_subsystems = {s.subsystem for s in a.intents}
        b_subsystems = {s.subsystem for s in b.intents}

        return {
            "common_subsystems": list(a_subsystems & b_subsystems),
            "unique_to_a": list(a_subsystems - b_subsystems),
            "unique_to_b": list(b_subsystems - a_subsystems),
            "philosophy_a": a.overall_philosophy.value,
            "philosophy_b": b.overall_philosophy.value,
            "evolution_a": a.evolution_direction.value,
            "evolution_b": b.evolution_direction.value,
        }
