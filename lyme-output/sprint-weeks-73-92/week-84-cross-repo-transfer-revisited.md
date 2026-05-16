# Week 84 — Cross-Repo Transfer Revisited

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/memory/transfer.py`
**5 Transfer Policies Compared:**
| Policy | Description |
|--------|-------------|
| no_memory | No cross-repo transfer |
| repo_only | Only repo-specific memory |
| global_memory | All memory shared across repos |
| global_memory_with_critic | Global memory + critic review |
| global_memory_with_verification_gate | Global memory + verification gate |

**Metrics:** success_rate, negative_transfer_rate.

## 2. Tests

**Tests:** `tests/test_weeks81_84_memory.py`
**Coverage:** 25 tests across all 4 weeks, all passing.

## 3. Files Created

| Week | File |
|------|------|
| 81 | `src/lyme_model/memory/coding_memory.py` |
| 82 | `src/lyme_model/memory/corruption.py` |
| 83 | `src/lyme_model/memory/repo_adaptation.py` |
| 84 | `src/lyme_model/memory/transfer.py` |

## 4. Next Week

Week 85 — Toolformer-Style Data Generation
