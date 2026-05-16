# Week 87 — Patch Critic Model

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/patch_critic.py`

**7 evaluation checks before patch application:**

| Check | What It Detects | Blocking? |
|-------|----------------|-----------|
| Syntax risk | Invalid Python syntax in diff | Yes |
| Missing imports | New imports not in file context | Warning |
| Wrong file | Patch targets file not in task scope | Yes |
| Likely test failure | Patch contradicts test patterns | Warning |
| Architectural mismatch | Violates "never" rules | Warning |
| Hallucinated symbols | Unknown function/class names | Warning |
| Over-broad change | >50 lines added or >30 removed | Warning |

## 2. Verdict Types

`CriticVerdict` returns:
- `approved` — patch safe to apply (no blocking issues)
- `risks` — non-blocking warnings
- `blocked_reasons` — blocking issues requiring revision
- `confidence` — verdict confidence (0.9 approved, 0.95 blocked)
- `latency_ms` — evaluation time

## 3. Critical Design Decisions

- **Diff-aware syntax checking**: Strips `+`/`-` prefixes and diff headers before `ast.parse()`
- **File existence fallback**: Import check gracefully skips if target file doesn't exist yet
- **Builtin symbol filter**: 40+ Python builtins excluded from hallucination detection

## 4. Files

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/patch_critic.py` | CriticVerdict, PatchCritic with 7 checks |

## 5. Tests

**Tests:** `tests/test_weeks85_87_learning.py::TestWeek87PatchCritic`
**Coverage:** 17 tests — each check type, stats tracking, latency, edge cases
**All passing.**

## 6. Next Week

Week 88 — Lyme Model v0.3: assemble weeks 85-87 into a hardened release with benchmark report.
