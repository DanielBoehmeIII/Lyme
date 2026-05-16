"""Week 90 — Caching and Reuse for Lyme Model.

Cache:
- embeddings
- file summaries
- AST extracts
- repo graph
- test command discovery
- model prompts
- verification results
- tool outputs when safe

With invalidation rules based on file changes and time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import json
import time
import hashlib


def timestamp_ms() -> int:
    return int(time.time() * 1000)


CacheKey = str


def make_key(*parts: str) -> CacheKey:
    return ":".join(parts)


def content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class CacheEntry:
    key: str
    value: Any
    cache_type: str = "generic"
    created_ms: int = 0
    ttl_ms: int = 300000  # 5 minutes default
    depends_on_files: List[str] = field(default_factory=list)
    file_hashes: Dict[str, str] = field(default_factory=dict)
    hit_count: int = 0

    def is_expired(self) -> bool:
        if self.ttl_ms <= 0:
            return False
        return (timestamp_ms() - self.created_ms) > self.ttl_ms

    def is_valid(self, file_checksums: Optional[Dict[str, str]] = None) -> bool:
        if self.is_expired():
            return False
        if file_checksums and self.file_hashes:
            for fpath, expected_hash in self.file_hashes.items():
                actual = file_checksums.get(fpath)
                if actual is None or actual != expected_hash:
                    return False
        return True

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "cache_type": self.cache_type,
            "created_ms": self.created_ms,
            "ttl_ms": self.ttl_ms,
            "depends_on_files": list(self.depends_on_files),
            "hit_count": self.hit_count,
            "expired": self.is_expired(),
        }


@dataclass
class CachePolicy:
    embeddings_ttl_ms: int = 3600000       # 1 hour
    file_summary_ttl_ms: int = 300000       # 5 minutes
    ast_extract_ttl_ms: int = 60000         # 1 minute
    repo_graph_ttl_ms: int = 300000         # 5 minutes
    test_discovery_ttl_ms: int = 60000      # 1 minute
    prompt_cache_ttl_ms: int = 3600000      # 1 hour (exact-match only)
    verification_ttl_ms: int = 10000        # 10 seconds
    tool_output_ttl_ms: int = 5000          # 5 seconds (idempotent tools only)
    max_entries: int = 1000

    def ttl_for(self, cache_type: str) -> int:
        mapping = {
            "embeddings": self.embeddings_ttl_ms,
            "file_summary": self.file_summary_ttl_ms,
            "ast_extract": self.ast_extract_ttl_ms,
            "repo_graph": self.repo_graph_ttl_ms,
            "test_discovery": self.test_discovery_ttl_ms,
            "prompt": self.prompt_cache_ttl_ms,
            "verification": self.verification_ttl_ms,
            "tool_output": self.tool_output_ttl_ms,
        }
        return mapping.get(cache_type, 300000)


class CacheStore:
    """General-purpose cache store with TTL and file-based invalidation."""

    def __init__(self, policy: Optional[CachePolicy] = None):
        self.policy = policy or CachePolicy()
        self._entries: Dict[str, CacheEntry] = {}
        self._stats: Dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str,
            file_checksums: Optional[Dict[str, str]] = None) -> Optional[Any]:
        entry = self._entries.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        if not entry.is_valid(file_checksums):
            self._evict(key)
            self._stats["misses"] += 1
            return None
        entry.hit_count += 1
        self._stats["hits"] += 1
        return entry.value

    def set(self, key: str, value: Any, cache_type: str = "generic",
            ttl_ms: Optional[int] = None,
            depends_on_files: Optional[List[str]] = None,
            file_checksums: Optional[Dict[str, str]] = None) -> None:
        if len(self._entries) >= self.policy.max_entries:
            self._evict_lru()
        effective_ttl = ttl_ms if ttl_ms is not None else self.policy.ttl_for(cache_type)
        self._entries[key] = CacheEntry(
            key=key,
            value=value,
            cache_type=cache_type,
            created_ms=timestamp_ms(),
            ttl_ms=effective_ttl,
            depends_on_files=depends_on_files or [],
            file_hashes=file_checksums or {},
        )

    def _evict(self, key: str) -> None:
        if key in self._entries:
            del self._entries[key]
            self._stats["evictions"] += 1

    def _evict_lru(self) -> None:
        if not self._entries:
            return
        oldest = min(self._entries.keys(),
                     key=lambda k: self._entries[k].created_ms)
        self._evict(oldest)

    def invalidate_by_type(self, cache_type: str) -> int:
        count = 0
        for key in list(self._entries.keys()):
            if self._entries[key].cache_type == cache_type:
                self._evict(key)
                count += 1
        return count

    def invalidate_by_file(self, filepath: str) -> int:
        count = 0
        for key in list(self._entries.keys()):
            if filepath in self._entries[key].depends_on_files:
                self._evict(key)
                count += 1
        return count

    def invalidate_all(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        self._stats["evictions"] += count
        return count

    def stats(self) -> Dict:
        return {
            **self._stats,
            "entries": len(self._entries),
            "max_entries": self.policy.max_entries,
            "by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in self._entries.values():
            counts[entry.cache_type] = counts.get(entry.cache_type, 0) + 1
        return counts

    def entry_info(self, key: str) -> Optional[Dict]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        return entry.to_dict()


class WarmCache:
    """Warm cache layer — keeps commonly accessed entries hot."""

    def __init__(self, store: CacheStore, warm_keys: Optional[List[str]] = None):
        self.store = store
        self.warm_keys = set(warm_keys or [])

    def mark_warm(self, key: str) -> None:
        self.warm_keys.add(key)

    def get(self, key: str, **kwargs) -> Optional[Any]:
        return self.store.get(key, **kwargs)

    def set(self, key: str, value: Any, **kwargs) -> None:
        self.store.set(key, value, **kwargs)

    def prewarm(self, loader: Callable[[str], Any], keys: List[str]) -> int:
        loaded = 0
        for key in keys:
            if self.store.get(key) is None:
                value = loader(key)
                if value is not None:
                    self.store.set(key, value)
                    self.warm_keys.add(key)
                    loaded += 1
        return loaded
