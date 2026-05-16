# Week 79 — Local Self-Correction Loop

**Theme:** Given failures, model should summarize, locate, patch, rerun, stop.
**Bounded:** Max 3 attempts by default, loop detection after 3 identical failures.

---

## 1. Correction Loop Flow

```
Failure detected
    │
    ▼
1. Summarize failure (test results, errors, verification)
    │
    ▼
2. Locate likely cause (pattern match against 12 error types)
    │
    ▼
3. Choose next action (import fix, syntax fix, logic fix, etc.)
    │
    ▼
4. Apply minimal patch
    │
    ▼
5. Rerun verification
    │
    ▼
6. Stop? (passed, max attempts, infinite loop)
    │
    ▼
Repeat if needed
```

## 2. Cause Detection Patterns

| Pattern | Cause |
|---------|-------|
| AssertionError | Test assertion failed — likely bug in implementation |
| ImportError | Missing or incorrect import |
| NameError | Undefined variable or function name |
| TypeError | Wrong argument types or count |
| SyntaxError | Invalid syntax in generated code |
| AttributeError | Accessed attribute does not exist |
| KeyError | Missing dictionary key |
| IndexError | List index out of range |
| ModuleNotFoundError | Module not installed or import path wrong |
| timeout | Operation exceeded time limit |
| memory | Out of memory error |

## 3. Stop Conditions

| Condition | Reason | 
|-----------|--------|
| Verification passed | Success — resolved |
| Max attempts reached | 3 attempts exhausted |
| No patch applied | Cannot make progress |
| Same failure 3x repeated | Infinite loop detected |

## 4. Metrics

| Metric | Definition |
|--------|------------|
| total_attempts | How many correction cycles ran |
| resolved | Whether final verification passed |
| total_latency_ms | Total time for all attempts |
| regressions | Times test failure count increased |
| stopped_reason | Why the loop ended |

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/correction/__init__.py` | Module exports |
| `src/lyme_model/correction/loop.py` | CorrectionLoop + SelfCorrectingAgent |

## 6. Next Week

Week 80 — Lyme Model v0.2: assemble everything from weeks 73-79 into a hardened release.
