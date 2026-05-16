# Week 138 — Critic Specialist

**Theme**: Review everything. Plan, patch, claims, imports, verification. Then decide.

## Design

The Critic Specialist performs 5 structured reviews:

### 1. Plan Review
- Missing affected files → error
- No verification command → error
- No rollback path → warning
- No diff shape → info
- Non-existent files → error

### 2. Patch Review
- Empty/small patch → error
- Missing diff headers (---/+++) → warning
- Large additions (>100 lines) → split suggestion
- High deletion ratio (+/- > 3:1) → verification warning
- Modified test with no assertions → info

### 3. Claims Review  
- Claims without citations → warning
- Citations to non-existent files → error

### 4. Imports Review
- Unknown imports that may not resolve → warning

### 5. Verification Review
- Missing syntax_check → warning
- Missing file_existence → warning
- Missing test_run → warning
- Only 1 verifier planned → info

## Decision Mapping

| Conditions | Decision | Action |
|------------|----------|--------|
| 0 critical errors | approve | Proceed |
| < 3 errors | revise | Fix issues and retry |
| ≥ 3 errors | reject | Block entirely |
| ≥ 5 warnings | ask_more_context | Gather more evidence |
| ≥ 3 warnings | require_stronger_model | Upgrade model |
| ≥ 1 critical error | require_human | Escalate to human |

## Metrics Tracked
- `total_critiques`, `approved`, `rejected`, `approval_rate`
- `avg_issues_per_critique`
- `avg_confidence`

## Files Created
- `src/lyme_model/specialists/critic.py` — CriticSpecialist with 5 review dimensions

## Lyme Audit Status
**Untouched.**
