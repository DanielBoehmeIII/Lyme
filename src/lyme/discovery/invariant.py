from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class InvariantType(str, Enum):
    LAYER_VIOLATION = "layer_violation"
    STATELESS_REQUIREMENT = "stateless_requirement"
    AUTH_REQUIRED = "auth_required"
    CO_EVOLUTION = "co_evolution"
    IDEMPOTENCY_EXPECTED = "idempotency_expected"
    VERSION_COUPLING = "version_coupling"
    DATA_FLOW_CONSTRAINT = "data_flow_constraint"
    API_CONTRACT = "api_contract"
    CONFIG_SCHEMA = "config_schema"
    DEPENDENCY_RULE = "dependency_rule"
    NAMING_CONVENTION = "naming_convention"
    LIFECYCLE_ORDER = "lifecycle_order"
    RESOURCE_CLEANUP = "resource_cleanup"
    THREAD_SAFETY = "thread_safety"
    TRANSACTION_BOUNDARY = "transaction_boundary"
    ERROR_HANDLING = "error_handling"
    TEST_COVERAGE = "test_coverage"
    PERFORMANCE_BUDGET = "performance_budget"
    SECURITY_REQUIREMENT = "security_requirement"
    MIGRATION_ORDER = "migration_order"


class InvariantSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Invariant:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    invariant_type: InvariantType = InvariantType.LAYER_VIOLATION
    description: str = ""
    rule: str = ""
    severity: InvariantSeverity = InvariantSeverity.MEDIUM
    scope: str = ""  # which files/subsystems this applies to
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    source: str = ""  # "explicit", "implicit", "historical", "social", "fragile", "hidden"
    created_at: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    observation_count: int = 1
    violations: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "invariant_type": self.invariant_type.value,
            "description": self.description,
            "rule": self.rule,
            "severity": self.severity.value,
            "scope": self.scope,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source": self.source,
            "created_at": self.created_at,
            "last_observed": self.last_observed,
            "observation_count": self.observation_count,
            "violations": self.violations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Invariant:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class InvariantRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    invariant_id: str = ""
    condition: str = ""
    action: str = ""  # "enforce", "warn", "inform"
    priority: int = 0
    pattern: str = ""
    exceptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "invariant_id": self.invariant_id,
            "condition": self.condition,
            "action": self.action,
            "priority": self.priority,
            "pattern": self.pattern,
            "exceptions": self.exceptions,
        }


@dataclass
class Violation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    invariant_id: str = ""
    invariant_name: str = ""
    file_path: str = ""
    line_number: int = 0
    description: str = ""
    severity: InvariantSeverity = InvariantSeverity.MEDIUM
    confidence: float = 0.0
    detected_at: float = field(default_factory=time.time)
    context: str = ""
    suggested_fix: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
            "metadata": self.metadata,
        }


@dataclass
class Contradiction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    invariant_a_id: str = ""
    invariant_a_name: str = ""
    invariant_b_id: str = ""
    invariant_b_name: str = ""
    description: str = ""
    conflict_type: str = ""
    severity: InvariantSeverity = InvariantSeverity.MEDIUM
    resolution: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "invariant_a_id": self.invariant_a_id,
            "invariant_a_name": self.invariant_a_name,
            "invariant_b_id": self.invariant_b_id,
            "invariant_b_name": self.invariant_b_name,
            "description": self.description,
            "conflict_type": self.conflict_type,
            "severity": self.severity.value,
            "resolution": self.resolution,
            "detected_at": self.detected_at,
        }


class InvariantSet:
    def __init__(self, repo_path: str = ""):
        self.repo_path = repo_path
        self._invariants: Dict[str, Invariant] = {}
        self._violations: Dict[str, Violation] = {}
        self._contradictions: Dict[str, Contradiction] = {}
        self._type_index: Dict[InvariantType, List[str]] = defaultdict(list)
        self._scope_index: Dict[str, List[str]] = defaultdict(list)
        self.created_at: float = time.time()

    def add_invariant(self, invariant: Invariant) -> str:
        self._invariants[invariant.id] = invariant
        self._type_index[invariant.invariant_type].append(invariant.id)
        if invariant.scope:
            self._scope_index[invariant.scope].append(invariant.id)
        return invariant.id

    def add_violation(self, violation: Violation) -> str:
        self._violations[violation.id] = violation
        inv = self._invariants.get(violation.invariant_id)
        if inv:
            inv.violations += 1
        return violation.id

    def add_contradiction(self, contradiction: Contradiction) -> str:
        self._contradictions[contradiction.id] = contradiction
        return contradiction.id

    def get_invariant(self, invariant_id: str) -> Optional[Invariant]:
        return self._invariants.get(invariant_id)

    def get_by_type(self, invariant_type: InvariantType) -> List[Invariant]:
        return [self._invariants[iid] for iid in self._type_index.get(invariant_type, []) if iid in self._invariants]

    def get_by_scope(self, scope: str) -> List[Invariant]:
        return [self._invariants[iid] for iid in self._scope_index.get(scope, []) if iid in self._invariants]

    def get_by_severity(self, severity: InvariantSeverity) -> List[Invariant]:
        return [i for i in self._invariants.values() if i.severity == severity]

    def get_violations(self, invariant_id: Optional[str] = None) -> List[Violation]:
        if invariant_id:
            return [v for v in self._violations.values() if v.invariant_id == invariant_id]
        return list(self._violations.values())

    def summary(self) -> Dict[str, Any]:
        return {
            "total_invariants": len(self._invariants),
            "total_violations": len(self._violations),
            "total_contradictions": len(self._contradictions),
            "invariants_by_type": {
                t.value: len(ids) for t, ids in self._type_index.items()
            },
            "invariants_by_severity": {
                s.value: len(self.get_by_severity(s))
                for s in InvariantSeverity
            },
            "invariants_by_source": self._count_by_source(),
            "high_severity_violations": sum(
                1 for v in self._violations.values()
                if v.severity in (InvariantSeverity.CRITICAL, InvariantSeverity.HIGH)
            ),
        }

    def _count_by_source(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for inv in self._invariants.values():
            counts[inv.source] += 1
        return dict(counts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "summary": self.summary(),
            "invariants": [i.to_dict() for i in self._invariants.values()],
            "violations": [v.to_dict() for v in self._violations.values()],
            "contradictions": [c.to_dict() for c in self._contradictions.values()],
            "created_at": self.created_at,
        }
