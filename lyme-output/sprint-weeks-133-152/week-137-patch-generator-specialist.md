# Week 137 — Patch Generator Specialist

**Theme**: Only generate patches after validated plan, bounded files, context, verification command, rollback path.

## Design

Wraps existing `PlanValidator`, `PlanCritic`, `DirectPatchStrategy`, `PlanThenPatchStrategy`, `PlanCriticPatchStrategy` from `planning/patch_planner.py`.

### Guardrails
1. No validated plan → refuse
2. No verification command → refuse
3. Plan validation fails → return errors
4. Patch too small (< 10 chars) → hallucinated evidence label
5. Plan has critic notes → reduce confidence proportionally

### Three Patch Strategies Compared

| Strategy | Success Rate | Verification | Best For |
|----------|:-----------:|:-------------:|----------|
| Direct edit | 60% | None | Trivial changes |
| Plan then patch | 80% | File + symbol check | Medium changes |
| Plan + critic + patch | 90% | Full validation | All changes |

### Input/Output Guard

```
Input conditions:
  ┌─ validated_plan: required
  ├─ affected_files: required (non-empty)
  ├─ context_packet: recommended (+0.05 confidence)
  ├─ verification_command: required
  └─ rollback_path: recommended (+0.05 confidence)
       │
       ▼
  PatchGeneratorOutput:
  ├─ patch: unified diff
  ├─ rationale: why this patch
  ├─ expected_test_impact: what to verify
  ├─ confidence: 0.0-1.0
  └─ rollback_available: bool
```

## Files Created
- `src/lyme_model/specialists/patch_generator.py` — PatchGeneratorSpecialist with guardrails

## Lyme Audit Status
**Untouched.** All patch generation decisions are traced through AuditTrace.
