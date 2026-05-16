# Week 85 — Toolformer-Style Data Generation

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/data_generation.py`

**Data types:**
- `ToolExample` — single trace-to-example conversion
- `DatasetSchema` — complete dataset with train/val split
- `DataGenerator` — converts audit traces + synthetic generation

**Action types covered (7):**
- search, read, run_test, inspect_git, stop, ask_user, reject_claim

**Quality filters (6):**
- Minimum 3 tool calls in trace
- Action must be clearly identifiable
- No ambiguous or mixed intents
- Trace duration < 120 seconds
- Not an infinite loop
- Outcome must be known (success/failure)

## 2. Data Sources

| Source | Method | Coverage |
|--------|--------|----------|
| Audit traces | `from_audit_trace()` | Real tool calls, real outcomes |
| Synthetic | `generate_synthetic()` | 21 examples (3 per action type) |

## 3. Dataset Schema

```python
DatasetSchema(
    version="1.0",
    total_examples=N,
    train_count=int(N * 0.8),
    val_count=N - int(N * 0.8),
    by_action={"search": X, "read": Y, ...},
    by_difficulty={"easy": A, "hard": B},
    quality_filters=[...],
)
```

## 4. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/__init__.py` | Module exports |
| `src/lyme_model/learning/data_generation.py` | Toolformer-style data generation |
| `tests/test_weeks85_87_learning.py` | 53 tests (weeks 85-87) |

## 5. Tests

**Tests:** `tests/test_weeks85_87_learning.py`
**Week 85 coverage:** 19 tests — ToolExample, DatasetSchema, DataGenerator, from_audit_trace, generate_synthetic, build_dataset, baseline_comparison

## 6. Next Week

Week 86 — Tool-Use Policy Model: train/simulate a small policy that decides next action from context.
