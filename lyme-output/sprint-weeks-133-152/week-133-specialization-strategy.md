# Week 133 — Lyme Model Specialization Strategy

**Theme**: Do not try to make one local model good at everything.

## Principle

Specialization trades generality for reliability within a bounded domain. A 7B model cannot match a 70B model at general coding. But a specialized 3B planner can match or exceed a 7B generalist at planning if its architecture is purpose-built.

## All Specializations Assessed

| # | Specialization | Min Model | Min Context | Min HW | Quality (std) | Exists | Score |
|---|---------------|-----------|-------------|--------|:-------------:|:------:|:-----:|
| 1 | Repo Q&A | 1.5B | 4K | CPU | 0.94 | ✓ | 95 |
| 2 | Patch Planning | 3B | 8K | Budget GPU | 0.85 | ✓ | 90 |
| 3 | Safe Small Edits | 3B | 8K | Budget GPU | 0.80 | ✗ | 85 |
| 4 | Test Failure Explanation | 3B | 8K | Budget GPU | 0.92 | ✗ | 80 |
| 5 | Patch Criticism | 7B | 16K | Std GPU | 0.75 | ✓ | 75 |
| 6 | Bug Localization | 7B | 16K | Std GPU | 0.70 | ✗ | 70 |
| 7 | Verification Planning | 3B | 4K | Budget GPU | 0.82 | ✓ | 70 |
| 8 | Tool-Use Routing | 7B | 4K | Std GPU | 0.78 | ✗ | 65 |
| 9 | Semantic Diff Explanation | 1.5B | 4K | CPU | 0.88 | ✗ | 60 |

## Top 3 Specializations

### 1. Patch Planning (score: 90)
- **Why**: Planning before acting prevents hallucinated edits, wrong files, cascading errors. Every coding task benefits. Existing `PatchPlanner` provides foundation.
- **Required**: 3B model, 8K context, budget GPU
- **Benchmark**: plan acceptance rate, completeness, missed dependencies
- **Will become**: Planner Specialist (Week 135)

### 2. Repo Q&A (score: 95)
- **Why**: Already hardened at 94% parity. Foundation all other specialists depend on for context gathering.
- **Required**: 1.5B model, 4K context, CPU-only
- **Benchmark**: answer correctness, hallucination rate
- **Will become**: Retriever Specialist (Week 136)

### 3. Safe Small Edits (score: 85)
- **Why**: The most concrete deliverable — bounded single-file edits with verification and rollback. Directly useful, low risk, high value.
- **Required**: 3B model, 8K context, budget GPU
- **Benchmark**: edit correctness, test pass rate
- **Will become**: Patch Generator Specialist (Week 137)

## Implementation Order (Weeks 134-139)

| Week | Specialist | Builds On |
|:----:|------------|-----------|
| 134 | Interfaces | All |
| 135 | Planner | PatchPlanner (planning/patch_planner.py) |
| 136 | Retriever | Retrieval policies (retrieval/policies.py) |
| 137 | Patch Generator | PatchPlanner (planning/patch_planner.py) |
| 138 | Critic | PatchPlanner.planning.PlanCritic |
| 139 | Verifier | Verification verifiers (verification/verifier.py) |

## Lyme Audit Status

**Untouched.** Lyme Audit remains the measurement, governance, tracing, replay, benchmark, and research system.

## Files Created

- `src/lyme_model/specialists/__init__.py` — Module init
- `src/lyme_model/specialists/strategy.py` — Specialization strategy with specs, rationale, top-3 selection
- `lyme-output/sprint-weeks-133-152/week-133-specialization-strategy.md` — This report
