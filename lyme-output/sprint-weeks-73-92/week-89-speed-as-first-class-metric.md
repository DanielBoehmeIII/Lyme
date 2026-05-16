# Week 89 — Speed as a First-Class Metric

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/speed/profiler.py`

## 2. Speed Metrics Tracked

| Metric | Measured By | Optimization Target |
|--------|-------------|-------------------|
| Model load time (cold) | `profile_cold()` | < 5s |
| Model load time (warm) | `profile_warm()` | 0s (already loaded) |
| First token latency | `first_token_latency_s` | < 2s |
| Tokens per second | `tokens_per_second` | > 15 tok/s |
| Retrieval latency | `measure_retrieval_latency()` | < 200ms per policy |
| Tool overhead | `measure_tool_overhead()` | < 50ms per tool |
| Verification latency | `measure_verification_latency()` | < 100ms |
| Patch critic latency | `patch_critic_latency_ms` | < 50ms |
| Total task time | `total_task_time_s` | < 15s |

## 3. Components

| Component | Purpose |
|-----------|---------|
| `SpeedProfile` | Single profile measurement (cold or warm) |
| `SpeedProfiler` | Orchestrates benchmarking across all paths |
| `LatencyReport` | Cold vs warm comparison + bottlenecks + recommendations |
| `benchmark_all()` | Quick CLI-friendly summary |

## 4. Speedup Detection

The profiler automatically:
- Compares cold vs warm start
- Calculates speedup factor
- Identifies bottlenecks (load >5s, tok/s <5, retrieval >500ms, tools >200ms, verification >300ms)
- Generates actionable recommendations

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/speed/__init__.py` | Module exports |
| `src/lyme_model/speed/profiler.py` | Speed profiling + benchmarking |
| `tests/test_week89_speed.py` | 21 tests |

## 6. Tests

**Tests:** `tests/test_week89_speed.py`
**Coverage:** 21 tests — profile dataclass, cold/warm profiling, benchmark, retrieval/tool/verification measurement, bottleneck detection, recommendations

## 7. Next Week

Week 90 — Caching and Reuse: build caching for embeddings, file summaries, AST extracts, model prompts, verification results with invalidation rules.
