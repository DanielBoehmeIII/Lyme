# Week 43 — Synthetic Bug Factory Report
> Generated: 2026-05-16T21:22:00.574932+00:00

## Summary
- Total examples: 700
- Bug types: 7

## Per-Bug-Type Breakdown
| Bug Type | Count | Sample Instruction |
|----------|-------|-------------------|
| api_rename_mismatch | 100 | Update the API call from process_item to process_item_v2 to  |
| bad_path_handling | 100 | Fix the file path handling to be safe and cross-platform. |
| broken_test_expectation | 100 | Fix the failing test assertion. |
| missing_null_check | 100 | Fix the ZeroDivisionError when average() receives an empty l |
| off_by_one | 100 | Fix the off-by-one error causing an IndexError in get_last() |
| wrong_config_key | 100 | Fix the KeyError when DATABASE_URL is not set in environment |
| wrong_import | 100 | Fix the import error in the data handler module. |

## Per-Modality Breakdown
| Modality | Count |
|----------|-------|
| test_repair | 400 |
| unified_diff | 300 |

## Splits
- train: 489
- val: 106
- test: 105

## Sample Metadata Fields
- bug_type: identifies the synthetic bug category
- severity: low/medium/high
- buggy_code: the code with the injected bug
- fixed_code: the corrected code
- test_code: pytest-style test
- test_output: simulated failure output
- target_output: unified diff repair patch