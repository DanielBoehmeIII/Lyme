from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class MemoryType(str, Enum):
    REFACTOR_MOTIF = "refactor_motif"
    BUG_PATTERN = "bug_pattern"
    REPAIR_STRATEGY = "repair_strategy"
    MIGRATION_PATTERN = "migration_pattern"
    FAILED_EXPERIMENT = "failed_experiment"
    ORGANIZATIONAL_HABIT = "organizational_habit"
    SUCCESSFUL_REFACTOR = "successful_refactor"
    REPEATED_MISTAKE = "repeated_mistake"


@dataclass
class MemoryItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    memory_type: MemoryType = MemoryType.REFACTOR_MOTIF
    description: str = ""
    pattern: str = ""
    context: str = ""
    triggers: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    outcome: str = ""
    success_score: float = 0.0
    confidence: float = 0.0
    recurrence_count: int = 0
    timestamp: float = field(default_factory=time.time)
    source_repo: str = ""
    tags: List[str] = field(default_factory=list)
    similar_ids: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "description": self.description[:200],
            "pattern": self.pattern[:200],
            "context": self.context[:200],
            "triggers": self.triggers[:5],
            "steps": self.steps[:5],
            "outcome": self.outcome[:200],
            "success_score": self.success_score,
            "confidence": self.confidence,
            "recurrence_count": self.recurrence_count,
            "timestamp": self.timestamp,
            "source_repo": self.source_repo,
            "tags": self.tags,
            "similar_ids": self.similar_ids[:5],
        }


@dataclass
class RefactorMotif:
    name: str = ""
    pattern: str = ""
    description: str = ""
    before_pattern: str = ""
    after_pattern: str = ""
    success_rate: float = 0.0
    use_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "description": self.description[:200],
            "success_rate": self.success_rate,
            "use_count": self.use_count,
        }


@dataclass
class BugPattern:
    name: str = ""
    signature: str = ""
    frequency: int = 0
    severity: str = "medium"
    fix_strategy: str = ""
    detection_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signature": self.signature,
            "frequency": self.frequency,
            "severity": self.severity,
            "fix_strategy": self.fix_strategy[:100],
            "detection_patterns": self.detection_patterns[:3],
        }


@dataclass
class RepairStrategy:
    name: str = ""
    problem_symptom: str = ""
    steps: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    common_pitfalls: List[str] = field(default_factory=list)
    applicability: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "problem_symptom": self.problem_symptom[:100],
            "steps": self.steps[:5],
            "success_indicators": self.success_indicators[:3],
            "common_pitfalls": self.common_pitfalls[:3],
            "applicability": self.applicability,
        }


@dataclass
class MigrationPattern:
    name: str = ""
    from_technology: str = ""
    to_technology: str = ""
    steps: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    estimated_effort: str = "medium"
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "from": self.from_technology,
            "to": self.to_technology,
            "step_count": len(self.steps),
            "risk_factors": self.risk_factors[:3],
            "estimated_effort": self.estimated_effort,
            "success_rate": self.success_rate,
        }


@dataclass
class MemoryRetrievalResult:
    items: List[MemoryItem] = field(default_factory=list)
    similarity_scores: Dict[str, float] = field(default_factory=dict)
    total_found: int = 0
    query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_found": self.total_found,
            "query": self.query,
            "items": [i.to_dict() for i in self.items[:5]],
            "top_scores": {
                i.id: self.similarity_scores.get(i.id, 0)
                for i in self.items[:5]
            },
        }


class HistoricalMemory:
    def __init__(self):
        self._items: Dict[str, MemoryItem] = {}
        self._index_by_type: Dict[MemoryType, List[str]] = defaultdict(list)
        self._index_by_tag: Dict[str, List[str]] = defaultdict(list)

    def add(self, item: MemoryItem):
        self._items[item.id] = item
        self._index_by_type[item.memory_type].append(item.id)
        for tag in item.tags:
            self._index_by_tag[tag].append(item.id)

    def get(self, item_id: str) -> Optional[MemoryItem]:
        return self._items.get(item_id)

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        return [self._items[iid] for iid in self._index_by_type.get(memory_type, []) if iid in self._items]

    def get_by_tag(self, tag: str) -> List[MemoryItem]:
        return [self._items[iid] for iid in self._index_by_tag.get(tag, []) if iid in self._items]

    def get_high_confidence(self, threshold: float = 0.7) -> List[MemoryItem]:
        return [i for i in self._items.values() if i.confidence >= threshold]

    def count(self) -> int:
        return len(self._items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.count(),
            "by_type": {t.value: len(ids) for t, ids in self._index_by_type.items()},
            "high_confidence_count": len(self.get_high_confidence()),
        }
