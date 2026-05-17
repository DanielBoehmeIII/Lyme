# Lyme Model — Dataset v1 Audit Report
> Generated: 2026-05-16T22:09:06.458757+00:00
> Source: `datasets/generated/` (105 files, 15287 lines)

## 1. Overview
| Metric | Value |
|--------|-------|
| Total JSONL files | 105 |
| Total lines (including empty) | 15287 |
| Valid examples | 15287 |
| Parse errors | 0 |
| Estimated total tokens | 3,069,522 |
| Canonical format (LymeExample) | 15287 |
| Flat format (legacy) | 200 |

## 2. Counts by Modality
| Modality | Count |
|----------|-------|
| bug_localization | 272 |
| long_horizon_planning | 280 |
| multi_file_edit | 280 |
| patch_planning | 1304 |
| refusal | 242 |
| repo_qa | 3441 |
| self_repair | 280 |
| test_repair | 1480 |
| tool_use | 1444 |
| unified_diff | 5252 |
| verification | 1012 |

## 3. Week 41 Target Categories
| Category | Count |
|----------|-------|
| repo_qa | 3441 |
| bug_localization | 272 |
| patch_planning | 1304 |
| diff_generation | 5252 |
| test_repair | 1480 |
| tool_use | 1444 |
| critique | 1012 |
| multi_file_edit | 280 |
| self_repair | 280 |
| long_horizon_planning | 280 |

## 4. Token Lengths (character-based estimate ÷ 4)
| Metric | Value |
|--------|-------|
| Total estimated tokens | 3,069,522 |

## 5. Languages Detected
| Language | Count |
|----------|-------|
| Go | 418 |
| JavaScript | 416 |
| Python | 13619 |
| Rust | 420 |
| TypeScript | 414 |

## 6. Quality Issues
| Issue | Count |
|-------|-------|
| Missing instruction | 0 |
| Missing output/target | 0 |
| Missing modality | 0 |
| Missing difficulty | 0 |
| Missing source | 0 |
| Missing repo context | 0 |
| Parse errors | 0 |

## 7. Duplicate Rate
| Metric | Value |
|--------|-------|
| IDs with duplicates | 0 |
| Duplicate rate | 0/15287 (0.0%) |

## 8. Train/Val/Test Split Analysis
| Split | Files | Lines |
|-------|-------|-------|
| train | 14 | 6230 |
| val | 14 | 824 |
| test | 14 | 823 |

**Leakage analysis:**
- Training examples: 6230
- Validation examples: 824
- Test examples: 823
- Leaked examples (same ID/instr across splits): 0

## 9. Missing Categories Assessment

- **repo_qa**: ✅ 3441 examples
- **bug_localization**: ✅ 272 examples
- **patch_planning**: ✅ 1304 examples
- **diff_generation**: ✅ 5252 examples
- **test_repair**: ✅ 1480 examples
- **tool_use**: ✅ 1444 examples
- **critique**: ✅ 1012 examples
- **multi_file_edit**: ✅ 280 examples
- **self_repair**: ✅ 280 examples
- **long_horizon_planning**: ✅ 280 examples

## 10. Per-File Breakdown
| File | Valid | Errors | Modalities | Missing Fields |
|------|-------|--------|------------|---------------|
| real_repo/test/combined.jsonl | 378 | 0 | patch_planning, test_repair, unified_diff | 0 |
| real_repo/test/patch_planning.jsonl | 125 | 0 | patch_planning | 0 |
| real_repo/test/test_repair.jsonl | 14 | 0 | test_repair | 0 |
| real_repo/test/unified_diff.jsonl | 239 | 0 | unified_diff | 0 |
| real_repo/train/combined.jsonl | 1760 | 0 | patch_planning, test_repair, unified_diff | 0 |
| real_repo/train/patch_planning.jsonl | 226 | 0 | patch_planning | 0 |
| real_repo/train/test_repair.jsonl | 42 | 0 | test_repair | 0 |
| real_repo/train/unified_diff.jsonl | 1492 | 0 | unified_diff | 0 |
| real_repo/val/combined.jsonl | 377 | 0 | patch_planning, test_repair, unified_diff | 0 |
| real_repo/val/patch_planning.jsonl | 135 | 0 | patch_planning | 0 |
| real_repo/val/test_repair.jsonl | 7 | 0 | test_repair | 0 |
| real_repo/val/unified_diff.jsonl | 235 | 0 | unified_diff | 0 |
| schema_demo.jsonl | 8 | 0 | bug_localization, patch_planning, refusal | 0 |
| synthetic_bugs/test/api_rename_mismatch.jsonl | 15 | 0 | unified_diff | 0 |
| synthetic_bugs/test/bad_path_handling.jsonl | 18 | 0 | unified_diff | 0 |
| synthetic_bugs/test/broken_test_expectation.jsonl | 18 | 0 | test_repair | 0 |
| synthetic_bugs/test/combined.jsonl | 105 | 0 | test_repair, unified_diff | 0 |
| synthetic_bugs/test/missing_null_check.jsonl | 14 | 0 | test_repair | 0 |
| synthetic_bugs/test/modality_test_repair.jsonl | 61 | 0 | test_repair | 0 |
| synthetic_bugs/test/modality_unified_diff.jsonl | 44 | 0 | unified_diff | 0 |
| synthetic_bugs/test/off_by_one.jsonl | 14 | 0 | test_repair | 0 |
| synthetic_bugs/test/wrong_config_key.jsonl | 11 | 0 | unified_diff | 0 |
| synthetic_bugs/test/wrong_import.jsonl | 15 | 0 | test_repair | 0 |
| synthetic_bugs/train/api_rename_mismatch.jsonl | 65 | 0 | unified_diff | 0 |
| synthetic_bugs/train/bad_path_handling.jsonl | 69 | 0 | unified_diff | 0 |
| synthetic_bugs/train/broken_test_expectation.jsonl | 70 | 0 | test_repair | 0 |
| synthetic_bugs/train/combined.jsonl | 489 | 0 | test_repair, unified_diff | 0 |
| synthetic_bugs/train/missing_null_check.jsonl | 72 | 0 | test_repair | 0 |
| synthetic_bugs/train/modality_test_repair.jsonl | 281 | 0 | test_repair | 0 |
| synthetic_bugs/train/modality_unified_diff.jsonl | 208 | 0 | unified_diff | 0 |
| synthetic_bugs/train/off_by_one.jsonl | 68 | 0 | test_repair | 0 |
| synthetic_bugs/train/wrong_config_key.jsonl | 74 | 0 | unified_diff | 0 |
| synthetic_bugs/train/wrong_import.jsonl | 71 | 0 | test_repair | 0 |
| synthetic_bugs/val/api_rename_mismatch.jsonl | 20 | 0 | unified_diff | 0 |
| synthetic_bugs/val/bad_path_handling.jsonl | 13 | 0 | unified_diff | 0 |
| synthetic_bugs/val/broken_test_expectation.jsonl | 12 | 0 | test_repair | 0 |
| synthetic_bugs/val/combined.jsonl | 106 | 0 | test_repair, unified_diff | 0 |
| synthetic_bugs/val/missing_null_check.jsonl | 14 | 0 | test_repair | 0 |
| synthetic_bugs/val/modality_test_repair.jsonl | 58 | 0 | test_repair | 0 |
| synthetic_bugs/val/modality_unified_diff.jsonl | 48 | 0 | unified_diff | 0 |
| synthetic_bugs/val/off_by_one.jsonl | 18 | 0 | test_repair | 0 |
| synthetic_bugs/val/wrong_config_key.jsonl | 15 | 0 | unified_diff | 0 |
| synthetic_bugs/val/wrong_import.jsonl | 14 | 0 | test_repair | 0 |
| teacher_traces/test/bug_localization.jsonl | 2 | 0 | bug_localization | 0 |
| teacher_traces/test/combined.jsonl | 6 | 0 | bug_localization, patch_planning, test_repair | 0 |
| teacher_traces/test/patch_planning.jsonl | 2 | 0 | patch_planning | 0 |
| teacher_traces/test/test_repair.jsonl | 1 | 0 | test_repair | 0 |
| teacher_traces/test/unified_diff.jsonl | 1 | 0 | unified_diff | 0 |
| teacher_traces/train/bug_localization.jsonl | 7 | 0 | bug_localization | 0 |
| teacher_traces/train/combined.jsonl | 25 | 0 | bug_localization, patch_planning, repo_qa | 0 |
| teacher_traces/train/patch_planning.jsonl | 3 | 0 | patch_planning | 0 |
| teacher_traces/train/repo_qa.jsonl | 5 | 0 | repo_qa | 0 |
| teacher_traces/train/test_repair.jsonl | 5 | 0 | test_repair | 0 |
| teacher_traces/train/tool_use.jsonl | 1 | 0 | tool_use | 0 |
| teacher_traces/train/unified_diff.jsonl | 4 | 0 | unified_diff | 0 |
| teacher_traces/val/combined.jsonl | 5 | 0 | patch_planning, repo_qa, tool_use | 0 |
| teacher_traces/val/patch_planning.jsonl | 1 | 0 | patch_planning | 0 |
| teacher_traces/val/repo_qa.jsonl | 1 | 0 | repo_qa | 0 |
| teacher_traces/val/tool_use.jsonl | 2 | 0 | tool_use | 0 |
| teacher_traces/val/unified_diff.jsonl | 1 | 0 | unified_diff | 0 |
| test/bug_localization.jsonl | 4 | 0 | bug_localization | 0 |
| test/combined.jsonl | 290 | 0 | bug_localization, patch_planning, refusal | 0 |
| test/examples.jsonl | 124 | 0 | bug_localization, patch_planning, refusal | 0 |
| test/long_horizon_planning.jsonl | 40 | 0 | long_horizon_planning | 0 |
| test/multi_file_edit.jsonl | 40 | 0 | multi_file_edit | 0 |
| test/patch.jsonl | 8 | 0 | patch_planning, test_repair, unified_diff | 0 |
| test/patch_planning.jsonl | 9 | 0 | patch_planning | 0 |
| test/refusal.jsonl | 2 | 0 | refusal | 0 |
| test/repo_qa.jsonl | 166 | 0 | repo_qa | 0 |
| test/self_repair.jsonl | 40 | 0 | self_repair | 0 |
| test/test_repair.jsonl | 4 | 0 | test_repair | 0 |
| test/tool_use.jsonl | 49 | 0 | tool_use | 0 |
| test/unified_diff.jsonl | 13 | 0 | unified_diff | 0 |
| test/verification.jsonl | 34 | 0 | verification | 0 |
| test.jsonl | 20 | 0 | bug_localization, patch_planning, refusal | 0 |
| train/bug_localization.jsonl | 61 | 0 | bug_localization | 0 |
| train/combined.jsonl | 2332 | 0 | bug_localization, patch_planning, refusal | 0 |
| train/examples.jsonl | 995 | 0 | bug_localization, patch_planning, refusal | 0 |
| train/long_horizon_planning.jsonl | 200 | 0 | long_horizon_planning | 0 |
| train/multi_file_edit.jsonl | 200 | 0 | multi_file_edit | 0 |
| train/patch.jsonl | 65 | 0 | patch_planning, test_repair, unified_diff | 0 |
| train/patch_planning.jsonl | 70 | 0 | patch_planning | 0 |
| train/refusal.jsonl | 16 | 0 | refusal | 0 |
| train/repo_qa.jsonl | 1337 | 0 | refusal, repo_qa | 0 |
| train/self_repair.jsonl | 200 | 0 | self_repair | 0 |
| train/test_repair.jsonl | 25 | 0 | test_repair | 0 |
| train/tool_use.jsonl | 356 | 0 | tool_use | 0 |
| train/unified_diff.jsonl | 103 | 0 | unified_diff | 0 |
| train/verification.jsonl | 270 | 0 | verification | 0 |
| train.jsonl | 160 | 0 | bug_localization, patch_planning, refusal | 0 |
| val/bug_localization.jsonl | 7 | 0 | bug_localization | 0 |
| val/combined.jsonl | 290 | 0 | bug_localization, patch_planning, refusal | 0 |
| val/examples.jsonl | 124 | 0 | bug_localization, patch_planning, refusal | 0 |
| val/long_horizon_planning.jsonl | 40 | 0 | long_horizon_planning | 0 |
| val/multi_file_edit.jsonl | 40 | 0 | multi_file_edit | 0 |
| val/patch.jsonl | 8 | 0 | patch_planning, unified_diff | 0 |
| val/patch_planning.jsonl | 11 | 0 | patch_planning | 0 |
| val/refusal.jsonl | 2 | 0 | refusal | 0 |
| val/repo_qa.jsonl | 166 | 0 | refusal, repo_qa | 0 |
| val/self_repair.jsonl | 40 | 0 | self_repair | 0 |
| val/test_repair.jsonl | 3 | 0 | test_repair | 0 |
| val/tool_use.jsonl | 50 | 0 | tool_use | 0 |
| val/unified_diff.jsonl | 10 | 0 | unified_diff | 0 |
| val/verification.jsonl | 33 | 0 | verification | 0 |
| val.jsonl | 20 | 0 | bug_localization, patch_planning, repo_qa | 0 |

## 11. Recommendations for Dataset v1

Based on this audit, Dataset v1 should address:

2. **Migrate 200 flat-format examples to canonical LymeExample schema**
6. **Expand from 15,287 to ~10K+ examples with real repo data**
7. **Add language metadata to unknown-language examples**
