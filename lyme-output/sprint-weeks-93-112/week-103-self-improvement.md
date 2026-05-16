# Week 103 — Self-Improvement Without Hype

**Module:** `learning/self_improvement.py`
**Bounded loop:** Max 3 plans, max 7 steps, min score threshold 0.3
**Guardrails:** 4 (no core rewrite, no audit overwrite, no recursion claims, no unverified training)
**Benchmark:** 6 tasks tested — 3 safe (completed), 3 unsafe (blocked by guardrails)
**Tests:** 10 tests

Design: generate candidate plans → score with critic → execute safest → verify → store → stop. No recursive improvement claimed. Lyme Audit protected.
