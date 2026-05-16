# Week 83 — Repo-Specific Adaptation

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/memory/repo_adaptation.py`
**Learns From Repo:**
- Language detection (Python, Rust, Go, TS, JS)
- Test framework (pytest, jest, cargo test, etc.)
- Build system (setuptools, npm, cargo, make, cmake)
- Source/test directory discovery
- Naming conventions (snake_case, camelCase, PascalCase)
- Common imports (frequency analysis)
- Architectural rules (from docs)
- Code conventions (docstrings, __future__, etc.)

**Deliverable:** `to_prompt_section()` — formats profile as model prompt.

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

Week 84 — 
