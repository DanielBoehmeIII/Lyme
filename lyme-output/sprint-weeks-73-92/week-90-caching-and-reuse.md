# Week 90 — Caching and Reuse

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/cache/store.py`

**Cache types with TTL:**

| Cache Type | TTL | Purpose |
|------------|-----|---------|
| embeddings | 1 hour | Pre-computed embeddings (long-lived) |
| file_summary | 5 minutes | File summaries during session |
| ast_extract | 1 minute | AST parses are cheap but reusable |
| repo_graph | 5 minutes | Dependency graph during session |
| test_discovery | 1 minute | Test commands for current state |
| prompt | 1 hour | Exact-match prompt cache (long-lived) |
| verification | 10 seconds | Verification results (short-lived) |
| tool_output | 5 seconds | Idempotent tool outputs (very short) |

## 2. Components

| Component | Purpose |
|-----------|---------|
| `CacheEntry` | Single cache entry with TTL, file dependencies, hit tracking |
| `CacheStore` | Main cache with set/get, TTL expiry, file-based invalidation |
| `CachePolicy` | Configurable TTLs per cache type, max entries cap |
| `WarmCache` | Pre-warming layer for frequently accessed keys |

## 3. Invalidation Rules

| Trigger | Invalidation | Method |
|---------|-------------|--------|
| TTL expiry | Automatic | `is_expired()` on get |
| File change | File hash mismatch | `is_valid(checksums)` |
| Type invalidation | All entries of type | `invalidate_by_type()` |
| File path | Entries depending on file | `invalidate_by_file()` |
| Full flush | All entries | `invalidate_all()` |
| LRU eviction | Oldest entry when full | Auto at `max_entries` |

## 4. Key Design Decisions

- **File-based invalidation**: Entries track which files they depend on and their hashes
- **TTL defaults per type**: Different data has different staleness tolerance
- **Hit counting**: Tracks cache effectiveness per entry
- **LRU eviction**: When at capacity, oldest entries are evicted first
- **Warm cache layer**: Pre-load commonly accessed keys at session start

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/cache/__init__.py` | Module exports |
| `src/lyme_model/cache/store.py` | CacheEntry, CacheStore, CachePolicy, WarmCache |
| `tests/test_week90_caching.py` | 31 tests |

## 6. Tests

**Tests:** `tests/test_week90_caching.py`
**Coverage:** 31 tests — CacheEntry lifecycle, CachePolicy, CacheStore set/get/eviction/invalidation, WarmCache prewarm

## 7. Next Week

Week 91 — Hardware-Aware Scheduling: decide which model to load, when to unload, CPU vs GPU, quantization level, based on hardware profile and task.
