# Week 143 — Specialist Router

**Theme**: Decide which specialist acts next, when to stop, retry, escalate, ask user, or verify.

## Router Decision Tree

```
                     ┌──────────────────┐
                     │  Current State   │
                     └────────┬─────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Stop conditions?   │
                    └─────────┬──────────┘
                          YES │           NO
                    ┌─────────▼──┐  ┌─────▼──────┐
                    │ STOP_FAIL  │  │  >3 errors? │
                    └────────────┘  └─────┬──────┘
                                     YES │       NO
                               ┌──────────▼──┐ ┌──▼───────────┐
                               │  ESCALATE   │ │ Next pipeline │
                               └─────────────┘ │    phase?     │
                                                └──┬───────────┘
                                              YES  │        NO
                                         ┌──────────▼──┐ ┌───▼────┐
                                         │  CONTINUE   │ │ STOP   │
                                         │  (call spec) │ │ SUCCESS│
                                         └──────────────┘ └────────┘
```

## Pipeline

```
init → plan → retrieve → generate_patch → critique → verify → summarize → STOP_SUCCESS
```

## Retry Policy

| Specialist | Max Retries | Condition |
|------------|:-----------:|-----------|
| Planner | 1 | Ambiguous input |
| Retriever | 2 | Missing context rate > 0.5 |
| Patch Generator | 2 | Validation failure |
| Critic | 1 | Insufficient context |
| Verifier | 2 | Transient failure |

## Escalation Triggers
- >3 errors in 30 seconds
- All specialists return low confidence (< 0.3)
- Conflict resolution fails
