# Week 86 — Tool-Use Policy Model

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/tool_policy.py`

**Actions (7) managed by policy:**
- SEARCH, READ, INSPECT_AST, RUN_COMMAND, GENERATE_PATCH, VERIFY, STOP

**Three policy modes:**

| Mode | Mechanism | Use Case |
|------|-----------|----------|
| heuristic | Rule-based router | Baseline comparison |
| weighted | Heuristic + learned weights | Lightweight training |
| (future) | LoRA/imitation | Full training from traces |

## 2. Heuristic Router Rules

The `HeuristicRouter` uses 6 decision rules in priority order:

| Priority | Condition | Action | Confidence |
|----------|-----------|--------|------------|
| 1 | loop_count > 5 | STOP | 0.9 |
| 2 | No files read, task exists | READ | 0.8 |
| 3 | Patch exists, no test failures | VERIFY | 0.9 |
| 4 | Test failed | SEARCH | 0.7 |
| 5 | Task exists | GENERATE_PATCH | 0.6 |
| 6 | Default (no task) | STOP | 0.5 |

## 3. Weighted Policy Training

`ToolPolicyModel` supports a `train_step()` method that:
- Takes (context, correct_action) pairs
- Compares policy decision to correct action
- Increases weights for correct decisions (×1.01)
- Decreases weights for incorrect decisions (×0.99)
- Bounds weights to [0.1, 2.0]

## 4. Benchmark

`benchmark()` evaluates policy accuracy against test examples:
- accuracy, total, correct, action_distribution

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/tool_policy.py` | Action enum, PolicyDecision, HeuristicRouter, ToolPolicyModel |

## 6. Tests

**Tests:** `tests/test_weeks85_87_learning.py::TestWeek86ToolPolicy`
**Coverage:** 17 tests — router rules, policy modes, training step, benchmark
**All passing.**

## 7. Next Week

Week 87 — Patch Critic Model: evaluate patches before application.
