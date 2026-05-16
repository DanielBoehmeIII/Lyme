# Week 146 — Specialist Training Data

**Theme**: Every dataset item traces back to Lyme Audit.

## Dataset Overview

| Specialist | Examples | Avg Difficulty | Top Failure Trap |
|------------|:--------:|:--------------:|------------------|
| Planner | 3 | 0.33 | Edit multiple files without verification |
| Retriever | 2 | 0.25 | Return too many files |
| Patch Generator | 2 | 0.25 | Return entire file instead of minimal diff |
| Critic | 2 | 0.40 | Miss patch format issues |
| Verifier | 2 | 0.25 | Run full test suite for every change |
| Router | 2 | 0.30 | Escalate immediately on first error |
| **Total** | **13** | **0.30** | |

## Example Format

```json
{
  "example_id": "abc123",
  "specialist": "planner",
  "input_data": {"task": "Fix auth bug", ...},
  "ideal_output": {"task_decomposition": [...], ...},
  "evidence": ["Auth bug pattern: missing null check"],
  "failure_traps": ["Fix all auth bugs at once"],
  "verification_result": {"passed": true},
  "audit_trace_id": "audit-trace-planner-1234567890",
  "difficulty": 0.5
}
```

## Data Source Traceability
- Every example has an `audit_trace_id` linking back to Lyme Audit
- Evidence fields cite specific file content and patterns
- Failure traps are extracted from real error histories
- Verification results are empirical pass/fail

## Files Created
- `src/lyme_model/specialists/training_data.py` — TrainingDataGenerator with 6 specialist datasets
