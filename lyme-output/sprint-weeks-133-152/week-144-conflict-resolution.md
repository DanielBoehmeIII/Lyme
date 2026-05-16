# Week 144 — Conflict Resolution

**Theme**: Evidence beats confidence. Tests beat claims. Governance beats generation. Uncertainty triggers fallback.

## Conflict Types & Resolution Rules

| Conflict | Detection | Resolution | Action |
|----------|-----------|:----------:|--------|
| Plan says safe, Critic says risky | plan_risk < 0.3 AND critic = reject | **Critic wins** (evidence beats confidence) | Revise plan |
| Retriever says enough, Verifier says missing | missing_context_rate > 0.3 | **Verifier wins** (tests beat claims) | Gather more context |
| Patch too broad, Governance says too risky | patch_size > 50 lines AND stop conditions | **Governance wins** | Reduce scope |
| Local model confident, Audit contradicts | confidence > 0.8 AND errors exist | **Audit wins** | Reduce confidence |

## Hierarchy

```
Strength of Signal (high to low):
  1. Tests / Verification Results (empirical)
  2. Governance / Stop Conditions (policy)
  3. Audit Evidence / Error History (historical)
  4. Critic Evaluation (structured review)
  5. Planner / Retriever Recommendations (analysis)
  6. Raw Model Confidence (unreliable signal)
```

## Fallback Chain

When resolution produces a clear loser:
1. Loser revises output based on winner's feedback
2. If revision still conflicts → router re-runs specialist with adjusted inputs
3. If conflict persists → escalate to human
