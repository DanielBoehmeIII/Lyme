# Week 139 — Verifier Specialist

**Theme**: Select and run the cheapest verification that gives meaningful confidence.

## Verifier Cost-Confidence Table

| Verifier | Cost | Confidence | Description |
|----------|:----:|:----------:|-------------|
| file_existence | 0.05 | 0.1 | Verify referenced files exist |
| syntax | 0.1 | 0.3 | Check Python syntax via AST |
| type_check | 0.3 | 0.5 | Run mypy/pyright |
| semantic_diff | 0.3 | 0.5 | Analyze diff for semantic changes |
| static_analysis | 0.4 | 0.4 | Run flake8/pylint |
| unit_tests | 0.5 | 0.7 | Run pytest on specific files |
| targeted_tests | 0.6 | 0.8 | Run tests related to changed files |
| manual_approval | 0.8 | 0.9 | Request human review |
| full_tests | 1.0 | 0.95 | Run full test suite |

## Selection Algorithm

1. Always include **mandatory cheap verifiers** (syntax, file_existence)
2. Sort remaining by **confidence/cost ratio** (descending)
3. Add verifiers until cost budget exhausted OR required confidence met
4. Verify in **ascending cost order** (fail fast on cheap checks)

## Verification Paths

| Cost Tier | Budget | Typical Path | Max Confidence |
|-----------|:------:|--------------|:--------------:|
| cheap | 0.3 | syntax → file_existence | 0.3 |
| medium | 0.6 | + type_check + semantic_diff | 0.6 |
| full | 1.0 | + unit_tests + targeted_tests | 0.95 |

## Benchmark: Quality vs Cost

| Cost Tier | Required Conf | Verifiers Selected | Passed | Conf After | Cheapest Meaningful |
|-----------|:-------------:|--------------------|:------:|:----------:|:-------------------:|
| cheap | 0.3 | syntax, file_existence | ✓ | 0.30 | syntax |
| cheap | 0.6 | syntax, file_existence | ✓ | 0.30 | syntax* |
| medium | 0.3 | syntax, file_existence, type_check, semantic_diff | ✓ | 0.60 | type_check |
| medium | 0.6 | syntax, file_existence, type_check, semantic_diff | ✓ | 0.60 | type_check |
| full | 0.8 | syntax, file_existence, type_check, semantic_diff, targeted_tests | ✓ | 0.80 | targeted_tests |

*\*cheap tier cannot reach 0.6 confidence — fundamental limitation*

## Files Created
- `src/lyme_model/specialists/verifier.py` — VerifierSpecialist with cost-optimized selection

## Lyme Audit Status
**Untouched.**
