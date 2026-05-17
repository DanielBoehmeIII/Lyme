# Lyme Model Dataset
## Summary
- **Total examples**: 4000
- **Deduplicated**: yes
- **Splits**: 995 train / 124 val / 124 test
- **Modalities**: repo_qa, bug_localization, patch_planning, unified_diff, test_repair, tool_use, verification, refusal
- **Total tokens (approx)**: 150,022
## Per-Modality Counts

| Modality | Count |
|----------|-------|
| bug_localization | 500 |
| patch_planning | 500 |
| refusal | 500 |
| repo_qa | 500 |
| test_repair | 500 |
| tool_use | 500 |
| unified_diff | 500 |
| verification | 500 |

## Token Statistics (Overall)

- Average instruction tokens: 10.0
- Average target tokens: 10.5
- Average total tokens per example: 120.7

## Per-Modality Token Statistics

| Modality | Count | Avg Instruction | Avg Target | Avg Total |
|----------|-------|-----------------|------------|-----------|
| repo_qa | 111 | 5.2 | 6.6 | 115.5 |
| bug_localization | 72 | 10.3 | 16.9 | 135.1 |
| patch_planning | 90 | 10.3 | 15.4 | 134.6 |
| unified_diff | 126 | 9.7 | 28.5 | 78.2 |
| test_repair | 32 | 12.6 | 8.9 | 70.4 |
| tool_use | 455 | 11.0 | 5.2 | 173.6 |
| verification | 337 | 10.3 | 9.6 | 68.9 |
| refusal | 20 | 5.0 | 11.2 | 52.2 |

## Schema

Each example follows the canonical LymeExample schema defined in `datasets/schema.py`.
Fields: id, modality, created, source, difficulty, instruction, repo_context,
retrieved_files, tool_outputs, target_output, metadata.

## Validation
All examples pass schema validation.