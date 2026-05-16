# Semantic Diff: sd-security-003

**Summary**: SemanticDiff v0.7.0 | 1 files | +2 -2 lines | Risk: RiskLevel.LOW | Intent: Fix SQL injection vulnerability in get_user()
**Confidence**: 99%

## Header
- Repository: legacy-ecommerce
- Branch: fix/sql-injection
- Source: e5f6a1b2c3d4 → f6a1b2c3d4e5
- Author: 

## Syntactic Changes (1 files)

| File | Type | + | - | Scope |
|------|------|---|---|-------|
| /src/users/auth.py | DiffType.MODIFICATION | 2 | 2 | function get_user |

## Behavioral Intent
- Type: IntentType.SECURITY
- Description: Fix SQL injection vulnerability in get_user()
- Motivation: user_id parameter was interpolated directly into SQL string, allowing injection
- Expected: Parameterized query prevents SQL injection
- Previous: String interpolation allowed malicious input to modify query
- Backward compatible: True

## Affected Invariants (1)

- **InvariantType.SECURITY_POLICY**: All database queries must use parameterized statements (status: restored, confidence: 99%)

## Architectural Impact
- Level: ImpactLevel.LOW
- Subsystems: 
- Coupling change: +0.00
- Complexity delta: +0

## Risk Assessment
- Overall: **RiskLevel.LOW**
- Regression: RiskLevel.LOW
- Security: RiskLevel.NONE
- Performance: RiskLevel.NONE
- Rollback difficulty: RiskLevel.LOW
- Score: 0.05
  - ⚠ Minimal change, clear improvement

## Verification
- Status: **VerificationStatus.PASSED**
- Tests: 15/15 passed
- Static analysis: ✓
- Type checks: ✓
  - ⚠ Gap: No SQL injection penetration test in CI

## Rollback Strategy
- Strategy: git_revert
- Complexity: simple
- Est. time: 1 min
  1. git revert HEAD
