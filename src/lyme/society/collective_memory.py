from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MemoryType(str, Enum):
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    STRATEGIC = "strategic"
    COORDINATION = "coordination"
    UNCERTAINTY = "uncertainty"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    DECAYED = "decayed"
    CONFLICTED = "conflicted"
    SUPERSEDED = "superseded"


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    memory_type: MemoryType = MemoryType.SEMANTIC
    content: str = ""
    agent_id: str = ""
    provenance: List[str] = field(default_factory=list)
    confidence: float = 0.5
    trust_weight: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    status: MemoryStatus = MemoryStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    ttl_days: float = 90.0
    subsystem: str = ""
    contradiction_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content[:200],
            "agent_id": self.agent_id,
            "provenance": self.provenance[:3],
            "confidence": self.confidence,
            "trust_weight": self.trust_weight,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "status": self.status.value,
            "tags": self.tags[:5],
        }

    @property
    def effective_weight(self) -> float:
        age_days = (time.time() - self.created_at) / 86400
        decay = max(0.0, 1.0 - age_days / self.ttl_days)
        return self.confidence * self.trust_weight * decay

    def is_stale(self) -> bool:
        age_days = (time.time() - self.created_at) / 86400
        return age_days > self.ttl_days * 0.8

    def touch(self):
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class MemoryQuery:
    query: str = ""
    memory_types: Optional[List[MemoryType]] = None
    min_confidence: float = 0.0
    tags: Optional[List[str]] = None
    agent_id: Optional[str] = None
    subsystem: Optional[str] = None
    limit: int = 20

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "memory_types": [t.value for t in self.memory_types] if self.memory_types else None,
            "min_confidence": self.min_confidence,
            "tags": self.tags,
            "agent_id": self.agent_id,
            "subsystem": self.subsystem,
            "limit": self.limit,
        }


@dataclass
class MemorySearchResult:
    entries: List[MemoryEntry] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    total_found: int = 0

    def top(self, n: int = 5) -> List[MemoryEntry]:
        scored = [(e, self.scores.get(e.id, 0)) for e in self.entries]
        scored.sort(key=lambda x: -x[1])
        return [s[0] for s in scored[:n]]


@dataclass
class ConflictRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    memory_a_id: str = ""
    memory_b_id: str = ""
    description: str = ""
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""
    resolved_by: str = ""
    confidence_loser: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "memory_a": self.memory_a_id,
            "memory_b": self.memory_b_id,
            "description": self.description[:200],
            "detected_at": self.detected_at,
            "resolved": self.resolved,
            "resolution": self.resolution[:100] if self.resolution else "",
        }


class CollectiveMemory:
    def __init__(self):
        self._entries: Dict[str, MemoryEntry] = {}
        self._conflicts: List[ConflictRecord] = []
        self._by_type: Dict[MemoryType, List[str]] = defaultdict(list)
        self._by_agent: Dict[str, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)
        self._by_subsystem: Dict[str, List[str]] = defaultdict(list)

    def store(self, entry: MemoryEntry) -> str:
        self._entries[entry.id] = entry
        self._by_type[entry.memory_type].append(entry.id)
        self._by_agent[entry.agent_id].append(entry.id)
        for tag in entry.tags:
            self._by_tag[tag].append(entry.id)
        if entry.subsystem:
            self._by_subsystem[entry.subsystem].append(entry.id)

        self._detect_conflicts(entry)
        return entry.id

    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(memory_id)
        if entry:
            entry.touch()
            if entry.is_stale():
                entry.status = MemoryStatus.STALE
        return entry

    def search(self, query: MemoryQuery) -> MemorySearchResult:
        candidates = list(self._entries.values())

        if query.memory_types:
            candidates = [e for e in candidates if e.memory_type in query.memory_types]
        if query.min_confidence > 0:
            candidates = [e for e in candidates if e.confidence >= query.min_confidence]
        if query.tags:
            candidates = [e for e in candidates if any(t in e.tags for t in query.tags)]
        if query.agent_id:
            candidates = [e for e in candidates if e.agent_id == query.agent_id]
        if query.subsystem:
            candidates = [e for e in candidates if e.subsystem == query.subsystem]

        candidates = [e for e in candidates if e.status in (MemoryStatus.ACTIVE, MemoryStatus.STALE)]

        query_words = set(query.query.lower().split())
        scores = {}
        for entry in candidates:
            score = 0.0

            content_words = set(entry.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                score += overlap / max(len(query_words), 1) * 2.0

            tag_overlap = len(query_words & set(t.lower() for t in entry.tags))
            if tag_overlap > 0:
                score += tag_overlap * 1.5

            score *= entry.effective_weight
            recency = 1.0 / (1.0 + (time.time() - entry.last_accessed) / 86400)
            score += recency * 0.5

            scores[entry.id] = score

        ranked = sorted(
            [(e, scores.get(e.id, 0)) for e in candidates],
            key=lambda x: -x[1],
        )
        entries = [r[0] for r in ranked[:query.limit]]

        result = MemorySearchResult(
            entries=entries,
            scores={e.id: scores.get(e.id, 0) for e in entries},
            total_found=len(candidates),
        )

        for e in entries:
            e.touch()

        return result

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        return [self._entries[eid] for eid in self._by_type.get(memory_type, [])
                if eid in self._entries]

    def get_by_agent(self, agent_id: str) -> List[MemoryEntry]:
        return [self._entries[eid] for eid in self._by_agent.get(agent_id, [])
                if eid in self._entries]

    def decay_stale(self):
        now = time.time()
        for entry in list(self._entries.values()):
            age_days = (now - entry.created_at) / 86400
            if age_days > entry.ttl_days:
                entry.status = MemoryStatus.DECAYED
            elif entry.is_stale() and entry.access_count == 0:
                entry.status = MemoryStatus.STALE

    def get_active_memories(self) -> List[MemoryEntry]:
        return [e for e in self._entries.values()
                if e.status == MemoryStatus.ACTIVE]

    def _detect_conflicts(self, new_entry: MemoryEntry):
        for existing in self._entries.values():
            if existing.id == new_entry.id:
                continue
            if existing.status in (MemoryStatus.DECAYED, MemoryStatus.SUPERSEDED):
                continue

            if existing.memory_type == new_entry.memory_type:
                existing_words = set(existing.content.lower().split())
                new_words = set(new_entry.content.lower().split())
                overlap = len(existing_words & new_words)
                union = len(existing_words | new_words)

                if union > 0 and overlap / union > 0.6:
                    if new_entry.confidence > existing.confidence * 1.5:
                        conflict = ConflictRecord(
                            memory_a_id=existing.id,
                            memory_b_id=new_entry.id,
                            description=f"New entry has higher confidence for similar content",
                            detected_at=time.time(),
                        )
                        self._conflicts.append(conflict)
                        new_entry.contradiction_ids.append(existing.id)
                        existing.contradiction_ids.append(new_entry.id)
                        existing.status = MemoryStatus.CONFLICTED

    def resolve_conflicts(self, resolution_strategy: str = "highest_confidence"):
        resolved = []
        for conflict in self._conflicts:
            if conflict.resolved:
                continue
            a = self._entries.get(conflict.memory_a_id)
            b = self._entries.get(conflict.memory_b_id)
            if not a or not b:
                continue

            if resolution_strategy == "highest_confidence":
                if a.confidence >= b.confidence:
                    b.status = MemoryStatus.SUPERSEDED
                    b.superseded_by = a.id
                    conflict.resolution = "Kept A (higher confidence)"
                else:
                    a.status = MemoryStatus.SUPERSEDED
                    a.superseded_by = b.id
                    conflict.resolution = "Kept B (higher confidence)"
            elif resolution_strategy == "most_recent":
                if a.created_at >= b.created_at:
                    b.status = MemoryStatus.SUPERSEDED
                    b.superseded_by = a.id
                    conflict.resolution = "Kept A (more recent)"
                else:
                    a.status = MemoryStatus.SUPERSEDED
                    a.superseded_by = b.id
                    conflict.resolution = "Kept B (more recent)"

            conflict.resolved = True
            resolved.append(conflict)

        return len(resolved)

    def update_trust(self, agent_id: str, delta: float):
        for entry in self._entries.values():
            if entry.agent_id == agent_id:
                entry.trust_weight = max(0.0, min(2.0, entry.trust_weight + delta))
                entry.confidence = max(0.0, min(1.0, entry.confidence + delta * 0.1))

    def get_high_value_abstractions(self, min_weight: float = 0.5) -> List[MemoryEntry]:
        return sorted(
            [e for e in self._entries.values() if e.effective_weight >= min_weight],
            key=lambda e: -e.effective_weight,
        )[:20]

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self._entries)
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        for e in self._entries.values():
            by_status[e.status.value] += 1
            by_type[e.memory_type.value] += 1

        active = sum(1 for e in self._entries.values() if e.status == MemoryStatus.ACTIVE)
        avg_confidence = (
            sum(e.confidence for e in self._entries.values()) / max(total, 1)
        )

        return {
            "total_entries": total,
            "active_entries": active,
            "decayed_entries": by_status.get("decayed", 0),
            "conflicted_entries": by_status.get("conflicted", 0),
            "superseded_entries": by_status.get("superseded", 0),
            "by_type": dict(by_type),
            "avg_confidence": avg_confidence,
            "unique_agents": len(self._by_agent),
            "total_conflicts": len(self._conflicts),
            "resolved_conflicts": sum(1 for c in self._conflicts if c.resolved),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics": self.get_statistics(),
            "recent_entries": [
                e.to_dict() for e in sorted(
                    self._entries.values(), key=lambda x: -x.created_at
                )[:20]
            ],
            "recent_conflicts": [c.to_dict() for c in self._conflicts[-10:]],
        }


class SynchronizationProtocol:
    def __init__(self, local_memory: CollectiveMemory):
        self.local = local_memory
        self._sync_log: List[Dict[str, Any]] = []
        self._peers: Dict[str, CollectiveMemory] = {}

    def register_peer(self, peer_id: str, memory: CollectiveMemory):
        self._peers[peer_id] = memory

    def sync_to_peer(self, peer_id: str, memory_types: Optional[List[MemoryType]] = None) -> int:
        peer = self._peers.get(peer_id)
        if not peer:
            return 0

        entries_to_sync = self.local.get_active_memories()
        if memory_types:
            entries_to_sync = [e for e in entries_to_sync if e.memory_type in memory_types]

        synced_count = 0
        for entry in entries_to_sync:
            query = MemoryQuery(query=entry.content, min_confidence=0.1, limit=1)
            existing = peer.search(query)
            if not existing.entries:
                peer.store(entry)
                synced_count += 1
            elif existing.entries[0].confidence < entry.confidence * 0.8:
                peer.store(entry)
                synced_count += 1

        self._sync_log.append({
            "timestamp": time.time(),
            "peer_id": peer_id,
            "synced_count": synced_count,
            "memory_types": [t.value for t in memory_types] if memory_types else "all",
        })

        return synced_count

    def pull_from_peer(self, peer_id: str, memory_types: Optional[List[MemoryType]] = None) -> int:
        peer = self._peers.get(peer_id)
        if not peer:
            return 0

        entries_to_pull = peer.get_active_memories()
        if memory_types:
            entries_to_pull = [e for e in entries_to_pull if e.memory_type in memory_types]

        pulled_count = 0
        for entry in entries_to_pull:
            query = MemoryQuery(query=entry.content, min_confidence=0.1, limit=1)
            existing = self.local.search(query)
            if not existing.entries:
                self.local.store(entry)
                pulled_count += 1

        return pulled_count

    def get_sync_history(self) -> List[Dict[str, Any]]:
        return self._sync_log[-20:]


class TrustWeightingSystem:
    def __init__(self):
        self._agent_trust: Dict[str, float] = defaultdict(lambda: 1.0)
        self._agent_accuracy: Dict[str, List[float]] = defaultdict(list)
        self._agent_contribution_count: Dict[str, int] = defaultdict(int)
        self._verification_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_contribution(self, agent_id: str, verified: bool):
        self._agent_accuracy[agent_id].append(1.0 if verified else 0.0)
        self._agent_contribution_count[agent_id] += 1

        accuracy = sum(self._agent_accuracy[agent_id]) / len(self._agent_accuracy[agent_id])
        base = 1.0
        if self._agent_contribution_count[agent_id] < 3:
            base = 0.5 + accuracy * 0.5
        else:
            base = accuracy * 1.5

        self._agent_trust[agent_id] = max(0.0, min(2.0, base))

        self._verification_history[agent_id].append({
            "timestamp": time.time(),
            "verified": verified,
            "new_trust": self._agent_trust[agent_id],
        })

    def get_trust(self, agent_id: str) -> float:
        return self._agent_trust.get(agent_id, 1.0)

    def get_weighted_confidence(self, agent_id: str, base_confidence: float) -> float:
        trust = self.get_trust(agent_id)
        return base_confidence * (0.3 + 0.7 * trust)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "agents_tracked": len(self._agent_trust),
            "avg_trust": sum(self._agent_trust.values()) / max(len(self._agent_trust), 1),
            "total_contributions": sum(self._agent_contribution_count.values()),
            "top_agents": sorted(
                self._agent_trust.items(), key=lambda x: -x[1]
            )[:5],
        }
