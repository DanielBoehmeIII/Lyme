# Week 102 — Local Reward Model / Critic

**Module:** `learning/reward_model.py`
**Scores across 7 dimensions:** plan_quality (0.20), evidence_grounding (0.15), patch_safety (0.20), verification_completeness (0.15), hallucination_risk (0.10), edit_minimality (0.10), likely_test_success (0.10)
**Hybrid approach:** rules + pattern matching + context-aware scoring
**Tests:** 10 tests

Detects risky patterns (exec, eval, rm -rf), validates safe patterns (raise ValueError, validate), scores patch minimality by line count, and assesses hallucination risk from symbol mismatches.
