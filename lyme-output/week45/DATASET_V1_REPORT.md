# Week 45 — Dataset v1 Build Report
> Generated: 2026-05-16T22:24:07.803904+00:00

## Summary
- Total examples: 16,328
- Splits: 4
- Source datasets: 4

## Per-Split Breakdown
| Split | Total | Train | Val | Test | Top Modalities |
|-------|-------|-------|-----|------|----------------|
| sft | 13,263 | 10,610 | 1,326 | 1,327 | unified_diff:7328, patch_planning:1772, test_repair:1628 |
| tool_policy | 496 | 396 | 50 | 50 | tool_use:496 |
| critic | 304 | 243 | 30 | 31 | verification:304 |
| eval_only | 2,265 | 1,812 | 226 | 227 | unified_diff:1353, patch_planning:274, test_repair:247 |

## All Modalities (Combined)
- unified_diff: 8,681
- patch_planning: 2,046
- test_repair: 1,875
- repo_qa: 1,738
- tool_use: 548
- verification: 338
- long_horizon_planning: 280
- self_repair: 280
- multi_file_edit: 280
- bug_localization: 140
- refusal: 122

## Dataset Structure
```
datasets/v1/
  sft/
    train/
      combined.jsonl  (10610 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
    val/
      combined.jsonl  (1326 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
    test/
      combined.jsonl  (1327 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
  tool_policy/
    train/
      combined.jsonl  (396 examples)
      tool_use.jsonl
    val/
      combined.jsonl  (50 examples)
      tool_use.jsonl
    test/
      combined.jsonl  (50 examples)
      tool_use.jsonl
  critic/
    train/
      combined.jsonl  (243 examples)
      verification.jsonl
    val/
      combined.jsonl  (30 examples)
      verification.jsonl
    test/
      combined.jsonl  (31 examples)
      verification.jsonl
  eval_only/
    train/
      combined.jsonl  (1812 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
    val/
      combined.jsonl  (226 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
    test/
      combined.jsonl  (227 examples)
      bug_localization.jsonl
      long_horizon_planning.jsonl
      multi_file_edit.jsonl
```

## Notes
- cpython is used as held-out real-repo split (does not appear in any training)
- All examples normalized to canonical LymeExample format
- Deduplicated by ID across all sources
- Each split has its own train/val/test (80/10/10)