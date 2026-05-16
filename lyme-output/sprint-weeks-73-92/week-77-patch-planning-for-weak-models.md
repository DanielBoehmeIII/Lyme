# Week 77 — Patch Planning for Weak Models

**Theme:** Weak models should not freely edit immediately. Require plan validation first.
**Compare:** direct → plan-then-patch → plan-critic-patch

---

## 1. Plan Requirements

| Field | Required | Purpose |
|-------|----------|---------|
| affected_files | Yes | Which files will change |
| intended_change | Yes (>=10 chars) | What the change does |
| dependency_risks | No | What could break |
| verification_command | Yes | How to verify correctness |
| rollback_path | Yes | How to revert |
| expected_diff_shape | Yes | "+N/-M lines, modify X functions" |

## 2. Three Strategies

| Strategy | Steps | Failure Prevention | Latency Cost |
|----------|-------|--------------------|--------------|
| **direct** | Patch immediately | None | 0ms validation |
| **plan_then_patch** | Plan → Validate → Patch | Blocks invalid plans | ~10ms validation |
| **plan_critic_patch** | Plan → Validate → Critique → Patch | Advises on risks | ~15ms validation |

## 3. Validation Rules

- All required fields must be non-empty
- File paths must exist in repo
- `intended_change` must be >= 10 characters
- Status: `draft` → `validated` or `rejected`

## 4. Critic Risk Patterns

| Pattern | Risk |
|---------|------|
| import | Import changes can break downstream modules |
| delete | Deleting code may affect callers |
| rename | Renaming requires updating all references |
| migration | Database migrations need rollback scripts |
| schema | Schema changes affect all consumers |
| config | Config changes affect runtime behavior |
| test | Test modifications reduce coverage confidence |
| public | Public API changes break consumers |

## 5. Comparison Metrics

| Metric | Definition |
|--------|------------|
| success_rate | Patches that succeeded / total attempts |
| avg_validation_time_ms | Time spent in validation |
| avg_patch_time_ms | Time spent generating the patch |
| blocked_bad_patches | Patches rejected by validator |
| false_rejections | Valid patches incorrectly rejected |

## 6. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/planning/__init__.py` | Module exports |
| `src/lyme_model/planning/patch_planner.py` | Planner, validator, critic, 3 strategies |

## 7. Next Week

Week 78 will build the Verifier-First Local Agent — verifying before accepting any model output.
