from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import time
import uuid


class MemoryCategory(str, Enum):
    REPAIR_PATTERN = "repair_pattern"
    MIGRATION_STRATEGY = "migration_strategy"
    INVARIANT_FAMILY = "invariant_family"
    ARCHITECTURAL_MOTIF = "architectural_motif"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    ECOSYSTEM_KNOWLEDGE = "ecosystem_knowledge"
    BUG_PATTERN = "bug_pattern"
    PERFORMANCE_PATTERN = "performance_pattern"
    TESTING_PATTERN = "testing_pattern"
    DEPLOYMENT_PATTERN = "deployment_pattern"


@dataclass
class ProvenanceEntry:
    source_repo: str
    source_path: str
    timestamp: float
    confidence: float
    extraction_method: str
    context: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_repo": self.source_repo,
            "source_path": self.source_path,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "context": self.context,
        }


@dataclass
class PrivacyBoundary:
    allowed_repos: List[str]
    blocked_categories: List[str]
    anonymize: bool = True
    max_share_depth: int = 3

    def allows(self, repo: str, category: MemoryCategory) -> bool:
        if category.value in self.blocked_categories:
            return False
        if self.allowed_repos and repo not in self.allowed_repos:
            return False
        return True


@dataclass
class ContradictionRecord:
    memory_a_id: str
    memory_b_id: str
    category: MemoryCategory
    description: str
    detected_at: float
    resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> Dict:
        return {
            "memory_a_id": self.memory_a_id,
            "memory_b_id": self.memory_b_id,
            "category": self.category.value,
            "description": self.description,
            "detected_at": self.detected_at,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class FabricMemory:
    id: str
    category: MemoryCategory
    content: str
    abstraction_level: float
    confidence: float
    provenance: List[ProvenanceEntry]
    created_at: float
    last_accessed: float
    access_count: int
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "content": self.content,
            "abstraction_level": self.abstraction_level,
            "confidence": self.confidence,
            "provenance": [p.to_dict() for p in self.provenance],
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "related_memories": self.related_memories,
        }


@dataclass
class FabricNode:
    id: str
    repo: str
    name: str
    memory_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "name": self.name,
            "memory_ids": self.memory_ids,
            "metadata": self.metadata,
        }


@dataclass
class FabricEdge:
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "weight": self.weight,
            "confidence": self.confidence,
        }


@dataclass
class MemoryQuery:
    query: str
    category: Optional[MemoryCategory] = None
    min_confidence: float = 0.3
    max_results: int = 10
    repo_filter: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class MemoryResult:
    memory: FabricMemory
    relevance_score: float
    match_reason: str

    def to_dict(self) -> Dict:
        return {
            "memory": self.memory.to_dict(),
            "relevance_score": self.relevance_score,
            "match_reason": self.match_reason,
        }


class MemoryFabric:
    def __init__(self, name: str = "default"):
        self.name = name
        self._memories: Dict[str, FabricMemory] = {}
        self._nodes: Dict[str, FabricNode] = {}
        self._edges: Dict[str, FabricEdge] = {}
        self._contradictions: List[ContradictionRecord] = []
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)
        self._repo_index: Dict[str, List[str]] = defaultdict(list)
        self._privacy_boundary: Optional[PrivacyBoundary] = None

    def set_privacy_boundary(self, boundary: PrivacyBoundary):
        self._privacy_boundary = boundary

    def store(self, content: str, category: MemoryCategory,
              provenance: List[ProvenanceEntry],
              tags: Optional[List[str]] = None,
              abstraction_level: float = 0.5,
              confidence: float = 0.7) -> FabricMemory:
        if self._privacy_boundary:
            for p in provenance:
                if not self._privacy_boundary.allows(p.source_repo, category):
                    raise PermissionError(f"Privacy boundary blocks storage from {p.source_repo} for {category.value}")

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = time.time()

        memory = FabricMemory(
            id=memory_id, category=category, content=content,
            abstraction_level=abstraction_level, confidence=confidence,
            provenance=provenance, created_at=now, last_accessed=now,
            access_count=0, tags=tags or [],
        )

        self._memories[memory_id] = memory
        self._category_index[category.value].append(memory_id)
        for tag in (tags or []):
            self._tag_index[tag].append(memory_id)
        for p in provenance:
            self._repo_index[p.source_repo].append(memory_id)

        self._detect_contradictions(memory)
        return memory

    def query(self, query: MemoryQuery) -> List[MemoryResult]:
        results = []
        candidates = list(self._memories.values())

        if query.category:
            candidate_ids = self._category_index.get(query.category.value, [])
            candidates = [m for m in candidates if m.id in candidate_ids]

        if query.repo_filter:
            repo_ids = self._repo_index.get(query.repo_filter, [])
            candidates = [m for m in candidates if m.id in repo_ids]

        if query.tags:
            tag_ids = set()
            for tag in query.tags:
                tag_ids.update(self._tag_index.get(tag, []))
            candidates = [m for m in candidates if m.id in tag_ids]

        for mem in candidates:
            if mem.confidence < query.min_confidence:
                continue
            relevance = self._compute_relevance(mem, query.query)
            if relevance > 0.1:
                results.append(MemoryResult(
                    memory=mem, relevance_score=round(relevance, 3),
                    match_reason=f"relevance_{relevance:.2f}",
                ))

        results.sort(key=lambda r: -r.relevance_score)

        for r in results[:query.max_results]:
            self._memories[r.memory.id].access_count += 1
            self._memories[r.memory.id].last_accessed = time.time()

        return results[:query.max_results]

    def _compute_relevance(self, memory: FabricMemory, query: str) -> float:
        query_lower = query.lower()
        content_lower = memory.content.lower()

        keyword_matches = sum(1 for word in query_lower.split() if word in content_lower)
        text_score = keyword_matches / max(1, len(query_lower.split()))

        tag_matches = sum(1 for tag in memory.tags if tag.lower() in query_lower)
        tag_score = tag_matches / max(1, len(memory.tags)) if memory.tags else 0

        recency = 1.0 / (1.0 + (time.time() - memory.last_accessed) / 86400)
        frequency = min(1.0, memory.access_count / 10)

        return (text_score * 0.4 + tag_score * 0.3 + recency * 0.15 + frequency * 0.15) * memory.confidence

    def get(self, memory_id: str) -> Optional[FabricMemory]:
        mem = self._memories.get(memory_id)
        if mem:
            mem.access_count += 1
            mem.last_accessed = time.time()
        return mem

    def link_memories(self, memory_a_id: str, memory_b_id: str, relationship: str = "related"):
        if memory_a_id in self._memories and memory_b_id in self._memories:
            if memory_b_id not in self._memories[memory_a_id].related_memories:
                self._memories[memory_a_id].related_memories.append(memory_b_id)
            if memory_a_id not in self._memories[memory_b_id].related_memories:
                self._memories[memory_b_id].related_memories.append(memory_a_id)

    def add_node(self, node: FabricNode):
        self._nodes[node.id] = node

    def add_edge(self, edge: FabricEdge):
        self._edges[edge.id] = edge

    def _detect_contradictions(self, new_memory: FabricMemory):
        for existing in self._memories.values():
            if existing.id == new_memory.id:
                continue
            if existing.category == new_memory.category:
                contradiction = self._check_contradiction(existing, new_memory)
                if contradiction:
                    self._contradictions.append(contradiction)

    def _check_contradiction(self, a: FabricMemory, b: FabricMemory) -> Optional[ContradictionRecord]:
        if a.confidence > 0.7 and b.confidence > 0.7:
            a_words = set(a.content.lower().split())
            b_words = set(b.content.lower().split())
            overlap = len(a_words & b_words) / max(1, len(a_words | b_words))
            if 0.3 < overlap < 0.7:
                return ContradictionRecord(
                    memory_a_id=a.id, memory_b_id=b.id,
                    category=a.category,
                    description=f"Contradicting patterns in category {a.category.value}",
                    detected_at=time.time(),
                )
        return None

    def resolve_contradiction(self, contradiction_id: str, resolution: str):
        for c in self._contradictions:
            if c.memory_a_id == contradiction_id or c.memory_b_id == contradiction_id:
                c.resolved = True
                c.resolution = resolution

    def confidence_decay(self, half_life_days: float = 30.0):
        now = time.time()
        half_life_seconds = half_life_days * 86400
        for mem in self._memories.values():
            age = now - mem.last_accessed
            decay = math.exp(-math.log(2) * age / half_life_seconds)
            mem.confidence = round(mem.confidence * decay, 3)

    def get_memories_by_category(self, category: MemoryCategory) -> List[FabricMemory]:
        ids = self._category_index.get(category.value, [])
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def get_memories_by_repo(self, repo: str) -> List[FabricMemory]:
        ids = self._repo_index.get(repo, [])
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def compute_cross_repo_transfer_score(self, source_repo: str, target_repo: str) -> Dict:
        source_mems = self.get_memories_by_repo(source_repo)
        target_mems = self.get_memories_by_repo(target_repo)
        if not source_mems or not target_mems:
            return {"transfer_score": 0, "shared_patterns": []}

        shared_categories = set(m.category.value for m in source_mems) & set(m.category.value for m in target_mems)
        confidence_scores = []
        for cat in shared_categories:
            s_mems = [m for m in source_mems if m.category.value == cat]
            t_mems = [m for m in target_mems if m.category.value == cat]
            if s_mems and t_mems:
                avg_confidence = (sum(m.confidence for m in s_mems) / len(s_mems) +
                                  sum(m.confidence for m in t_mems) / len(t_mems)) / 2
                confidence_scores.append(avg_confidence)

        transfer_score = sum(confidence_scores) / max(1, len(confidence_scores)) if confidence_scores else 0

        return {
            "source_repo": source_repo,
            "target_repo": target_repo,
            "transfer_score": round(transfer_score, 3),
            "shared_categories": list(shared_categories),
            "source_memory_count": len(source_mems),
            "target_memory_count": len(target_mems),
        }

    def statistics(self) -> Dict:
        return {
            "name": self.name,
            "total_memories": len(self._memories),
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "contradictions": len(self._contradictions),
            "unresolved_contradictions": sum(1 for c in self._contradictions if not c.resolved),
            "categories": {k: len(v) for k, v in self._category_index.items()},
            "repos": {k: len(v) for k, v in self._repo_index.items()},
            "avg_confidence": round(sum(m.confidence for m in self._memories.values()) / max(1, len(self._memories)), 3) if self._memories else 0,
        }

    def save(self, path: str):
        data = {
            "name": self.name,
            "memories": [m.to_dict() for m in self._memories.values()],
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
            "contradictions": [c.to_dict() for c in self._contradictions],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> MemoryFabric:
        with open(path) as f:
            data = json.load(f)
        fabric = cls(data.get("name", "loaded"))
        for md in data.get("memories", []):
            mem = FabricMemory(
                id=md["id"], category=MemoryCategory(md["category"]),
                content=md["content"], abstraction_level=md.get("abstraction_level", 0.5),
                confidence=md.get("confidence", 0.7),
                provenance=[ProvenanceEntry(**p) for p in md.get("provenance", [])],
                created_at=md.get("created_at", 0), last_accessed=md.get("last_accessed", 0),
                access_count=md.get("access_count", 0),
                tags=md.get("tags", []), related_memories=md.get("related_memories", []),
            )
            fabric._memories[mem.id] = mem
            fabric._category_index[mem.category.value].append(mem.id)
            for tag in mem.tags:
                fabric._tag_index[tag].append(mem.id)
            for p in mem.provenance:
                fabric._repo_index[p.source_repo].append(mem.id)
        for nd in data.get("nodes", []):
            fabric._nodes[nd["id"]] = FabricNode(**nd)
        for ed in data.get("edges", []):
            fabric._edges[ed["id"]] = FabricEdge(**ed)
        for cd in data.get("contradictions", []):
            fabric._contradictions.append(ContradictionRecord(**cd))
        return fabric

    @property
    def memory_count(self) -> int:
        return len(self._memories)
