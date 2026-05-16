import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List


MEMORY_TYPES = {"procedural", "episodic", "semantic"}


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    type: str = "semantic"
    content: str = ""
    source_task: str = ""
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    importance_score: float = 0.0
    tags: list = field(default_factory=list)
    embedding: list = field(default_factory=list)
    compressed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "source_task": self.source_task,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "importance_score": self.importance_score,
            "tags": self.tags,
            "embedding": self.embedding,
            "compressed": self.compressed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:16]),
            type=data.get("type", "semantic"),
            content=data.get("content", ""),
            source_task=data.get("source_task", ""),
            timestamp=data.get("timestamp", time.time()),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
            importance_score=data.get("importance_score", 0.0),
            tags=data.get("tags", []),
            embedding=data.get("embedding", []),
            compressed=data.get("compressed", False),
        )


def _keyword_overlap(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / math.sqrt(len(tokens_a) * len(tokens_b))


def _embed_text(text: str) -> list:
    words = text.lower().split()
    freq: dict = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    max_count = max(freq.values()) if freq else 1
    return [freq[w] / max_count for w in sorted(freq)]


class MemoryStore:
    def __init__(self, base_dir: str = "./lyme-output/memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = {}
        self._dirty = False
        self._load()

    def _index_path(self) -> Path:
        return self.base_dir / "index.json"

    def _entry_path(self, entry_id: str) -> Path:
        return self.base_dir / f"{entry_id}.json"

    def _load(self):
        index = self._index_path()
        if index.exists():
            with open(index) as f:
                ids = json.load(f)
            for eid in ids:
                path = self._entry_path(eid)
                if path.exists():
                    with open(path) as f:
                        self._entries[eid] = MemoryEntry.from_dict(json.load(f))

    def _save_index(self):
        with open(self._index_path(), "w") as f:
            json.dump(list(self._entries.keys()), f)

    def _persist(self, entry: MemoryEntry):
        with open(self._entry_path(entry.id), "w") as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)

    def save(self, entry: MemoryEntry):
        self._entries[entry.id] = entry
        self._persist(entry)
        self._save_index()

    def load(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._persist(entry)
            return entry
        path = self._entry_path(entry_id)
        if path.exists():
            with open(path) as f:
                entry = MemoryEntry.from_dict(json.load(f))
            self._entries[entry_id] = entry
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._persist(entry)
            return entry
        return None

    def search(self, query: str, limit: int = 10, threshold: float = 0.1) -> List[MemoryEntry]:
        query_emb = _embed_text(query)
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._entries.values():
            if entry.embedding:
                emb = entry.embedding
            else:
                emb = _embed_text(entry.content)
            sim = _cosine_similarity(query_emb, emb)
            if sim >= threshold:
                scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        sorted_entries = sorted(
            self._entries.values(), key=lambda e: e.timestamp, reverse=True
        )
        return sorted_entries[:n]

    def get_important(self, n: int = 10) -> List[MemoryEntry]:
        sorted_entries = sorted(
            self._entries.values(), key=lambda e: e.importance_score, reverse=True
        )
        return sorted_entries[:n]

    def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
        path = self._entry_path(entry_id)
        if path.exists():
            path.unlink()
            self._save_index()
            return True
        return False

    def prune(self, max_entries: int = 1000, max_age_days: int = 30):
        now = time.time()
        cutoff = now - max_age_days * 86400
        to_remove: list[str] = []
        for eid, entry in self._entries.items():
            if entry.timestamp < cutoff:
                to_remove.append(eid)
        for eid in to_remove:
            self.delete(eid)

        if len(self._entries) > max_entries:
            sorted_by_importance = sorted(
                self._entries.values(), key=lambda e: e.importance_score
            )
            excess = len(self._entries) - max_entries
            for entry in sorted_by_importance[:excess]:
                self.delete(entry.id)

    def count(self) -> int:
        return len(self._entries)

    def all_entries(self) -> List[MemoryEntry]:
        return list(self._entries.values())


def _cosine_similarity(a: list, b: list) -> float:
    if not a or not b:
        return 0.0
    max_len = max(len(a), len(b))
    va = a + [0.0] * (max_len - len(a))
    vb = b + [0.0] * (max_len - len(b))
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
