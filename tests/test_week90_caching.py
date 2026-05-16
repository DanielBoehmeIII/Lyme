"""Tests for Week 90 — Caching and Reuse."""

import pytest
import time
from src.lyme_model.cache import (
    CacheEntry, CacheStore, CachePolicy, timestamp_ms,
)
from src.lyme_model.cache.store import make_key, content_hash, WarmCache


class TestCachePrimitives:
    def test_timestamp_ms(self):
        ts = timestamp_ms()
        assert ts > 0

    def test_make_key(self):
        k = make_key("embeddings", "file.py")
        assert k == "embeddings:file.py"

    def test_content_hash(self):
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        h3 = content_hash("different")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 12


class TestCacheEntry:
    def test_entry_defaults(self):
        e = CacheEntry(key="k1", value="v1")
        assert e.key == "k1"
        assert e.ttl_ms == 300000
        assert e.hit_count == 0

    def test_entry_not_expired_initially(self):
        e = CacheEntry(key="k1", value="v1", created_ms=timestamp_ms())
        assert not e.is_expired()

    def test_entry_expired(self):
        e = CacheEntry(key="k1", value="v1", created_ms=1)
        assert e.is_expired()

    def test_entry_never_expires(self):
        e = CacheEntry(key="k1", value="v1", ttl_ms=0)
        assert not e.is_expired()

    def test_entry_valid_with_no_files(self):
        e = CacheEntry(key="k1", value="v1", created_ms=timestamp_ms())
        assert e.is_valid() is True

    def test_entry_invalid_with_changed_file(self):
        e = CacheEntry(
            key="k1", value="v1",
            created_ms=timestamp_ms(),
            file_hashes={"file.py": "abc123"},
        )
        assert e.is_valid({"file.py": "abc123"}) is True
        assert e.is_valid({"file.py": "def456"}) is False

    def test_entry_to_dict(self):
        e = CacheEntry(key="k1", value="v1", cache_type="test", created_ms=100)
        d = e.to_dict()
        assert d["key"] == "k1"
        assert d["cache_type"] == "test"


class TestCachePolicy:
    def test_policy_defaults(self):
        p = CachePolicy()
        assert p.embeddings_ttl_ms == 3600000
        assert p.max_entries == 1000

    def test_ttl_for_known_type(self):
        p = CachePolicy()
        assert p.ttl_for("embeddings") == 3600000
        assert p.ttl_for("verification") == 10000

    def test_ttl_for_unknown_type(self):
        p = CachePolicy()
        assert p.ttl_for("unknown") == 300000


class TestCacheStore:
    def test_store_initializes(self):
        s = CacheStore()
        assert s.stats()["entries"] == 0

    def test_set_and_get(self):
        s = CacheStore()
        s.set("k1", "value1")
        assert s.get("k1") == "value1"

    def test_get_missing(self):
        s = CacheStore()
        assert s.get("missing") is None

    def test_get_expired(self):
        s = CacheStore()
        s.set("k1", "v1", ttl_ms=0)
        time.sleep(0.001)
        # ttl_ms=0 means never expires, let's manually expire
        assert s.get("k1") == "v1"

    def test_get_expired_after_ttl(self):
        s = CacheStore()
        s.set("k1", "v1", ttl_ms=1)
        time.sleep(0.005)
        assert s.get("k1") is None

    def test_invalidate_by_type(self):
        s = CacheStore()
        s.set("k1", "v1", cache_type="file_summary")
        s.set("k2", "v2", cache_type="embeddings")
        assert s.invalidate_by_type("file_summary") == 1
        assert s.get("k1") is None
        assert s.get("k2") == "v2"

    def test_invalidate_by_file(self):
        s = CacheStore()
        s.set("k1", "v1", depends_on_files=["file.py"])
        s.set("k2", "v2", depends_on_files=["other.py"])
        assert s.invalidate_by_file("file.py") == 1
        assert s.get("k1") is None
        assert s.get("k2") == "v2"

    def test_invalidate_all(self):
        s = CacheStore()
        s.set("k1", "v1")
        s.set("k2", "v2")
        s.set("k3", "v3")
        assert s.invalidate_all() == 3
        assert s.stats()["entries"] == 0

    def test_stats_tracking(self):
        s = CacheStore()
        s.set("k1", "v1")
        s.get("k1")
        s.get("k1")
        s.get("missing")
        stats = s.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_eviction_at_max(self):
        s = CacheStore(policy=CachePolicy(max_entries=3))
        s.set("k1", "v1")
        s.set("k2", "v2")
        s.set("k3", "v3")
        s.set("k4", "v4")
        assert s.stats()["entries"] <= 3

    def test_entry_info(self):
        s = CacheStore()
        s.set("k1", "v1", cache_type="test")
        info = s.entry_info("k1")
        assert info is not None
        assert info["cache_type"] == "test"

    def test_entry_info_missing(self):
        s = CacheStore()
        assert s.entry_info("missing") is None

    def test_multiple_cache_types(self):
        s = CacheStore()
        s.set("emb:1", "data", cache_type="embeddings")
        s.set("sum:1", "data", cache_type="file_summary")
        s.set("ast:1", "data", cache_type="ast_extract")
        s.set("ver:1", "data", cache_type="verification")
        assert s.stats()["entries"] == 4

    def test_custom_ttl_overrides_policy(self):
        s = CacheStore()
        s.set("k1", "v1", cache_type="embeddings", ttl_ms=500)
        entry = s._entries["k1"]
        assert entry.ttl_ms == 500


class TestWarmCache:
    def test_warm_cache_wraps_store(self):
        store = CacheStore()
        wc = WarmCache(store)
        wc.set("k1", "v1")
        assert wc.get("k1") == "v1"

    def test_mark_warm(self):
        store = CacheStore()
        wc = WarmCache(store)
        wc.mark_warm("k1")
        assert "k1" in wc.warm_keys

    def test_prewarm_loads_missing(self):
        store = CacheStore()
        wc = WarmCache(store)
        loaded = 0
        def loader(key):
            nonlocal loaded
            loaded += 1
            return f"value_{key}"
        count = wc.prewarm(loader, ["a", "b"])
        assert count == 2
        assert wc.get("a") == "value_a"

    def test_prewarm_skips_existing(self):
        store = CacheStore()
        store.set("a", "existing")
        wc = WarmCache(store)
        called = False
        def loader(key):
            nonlocal called
            called = True
            return "new"
        count = wc.prewarm(loader, ["a"])
        assert count == 0
        assert wc.get("a") == "existing"
        assert not called
