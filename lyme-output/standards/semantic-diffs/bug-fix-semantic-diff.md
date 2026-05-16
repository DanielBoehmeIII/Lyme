# Semantic Diff: sd-bugfix-001

**Summary**: SemanticDiff v0.7.0 | 2 files | +13 -1 lines | Risk: RiskLevel.LOW | Intent: Fix off-by-one error in pagination where last page returns empty
**Confidence**: 97%

## Header
- Repository: sample-project
- Branch: fix/pagination-off-by-one
- Source: a1b2c3d4e5f6 → b2c3d4e5f6a1
- Author: fixer-agent
- PR: https://github.com/example/sample-project/pull/42

## Syntactic Changes (2 files)

| File | Type | + | - | Scope |
|------|------|---|---|-------|
| /src/pagination.py | DiffType.MODIFICATION | 1 | 1 | function paginate |
| /tests/test_pagination.py | DiffType.ADDITION | 12 | 0 | test test_paginate_last_page |

## Behavioral Intent
- Type: IntentType.BUG_FIX
- Description: Fix off-by-one error in pagination where last page returns empty
- Motivation: When page number is large enough that start + per_page exceeds list length, slicing returns empty list instead of remaining items
- Expected: pagination returns correct remaining items on any valid page
- Previous: last page returns empty list for large page numbers
- Backward compatible: True

## Affected Invariants (1)

- **InvariantType.DATA_INVARIANT**: paginate() always returns a subset of input items (status: preserved, confidence: 99%)

## Architectural Impact
- Level: ImpactLevel.LOW
- Subsystems: pagination module
- Coupling change: +0.00
- Complexity delta: +1

## Risk Assessment
- Overall: **RiskLevel.LOW**
- Regression: RiskLevel.LOW
- Security: RiskLevel.NONE
- Performance: RiskLevel.NONE
- Rollback difficulty: RiskLevel.LOW
- Score: 0.15
  - ⚠ Small change, 1 line modified

## Verification
- Status: **VerificationStatus.PASSED**
- Tests: 12/12 passed
- Coverage: 95.0%
- Static analysis: ✓
- Type checks: ✓

## Rollback Strategy
- Strategy: git_revert
- Complexity: simple
- Est. time: 2 min
  1. git revert <commit>
  1. Verify pagination tests pass
