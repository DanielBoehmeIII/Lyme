# Weeks 88-91 — Specialization Eval Report
> Generated: 2026-05-16T23:41:05.925741+00:00

## Infrastructure Readiness
⚠️ Some specializations need setup

### bug_localization ✅
- Config: training/configs/bug_localization_v2.yaml ✅
- Data: datasets/v2/sft/train/bug_localization.jsonl (27 examples) ✅
- Checkpoint: checkpoints/bug_localization_v2 ❌ NOT FOUND

### diff_discipline ✅
- Config: training/configs/diff_discipline_v2.yaml ✅
- Data: datasets/v2/sft/train/unified_diff.jsonl (1219 examples) ✅
- Checkpoint: checkpoints/diff_discipline_v2 ❌ NOT FOUND

### multi_file_edit ✅
- Config: training/configs/multi_file_edit_v2.yaml ✅
- Data: datasets/v2/sft/train/multi_file_edit.jsonl (2 examples) ✅
- Checkpoint: checkpoints/multi_file_edit_v2 ❌ NOT FOUND

### test_repair ⚠️
- Config: training/configs/test_repair_v2.yaml ✅
- Data: datasets/v2/sft/train/test_repair.jsonl ❌ NOT FOUND
- Checkpoint: checkpoints/test_repair_v2 ❌ NOT FOUND

## Target Metrics Matrix
| Specialization | Metric | Target | Description |
|---------------|--------|--------|-------------|
| diff_discipline | valid_diff_rate | 0.9 | Diff parses as valid unified diff |
| diff_discipline | apply_success_rate | 0.85 | Patch applies cleanly |
| diff_discipline | patch_minimality | 0.8 | Patch only changes necessary lines |
| test_repair | first_attempt_pass | 0.7 | First patch passes tests |
| test_repair | second_attempt_pass | 0.85 | Second patch passes after repair |
| test_repair | regression_rate | 0.05 | Fix breaks unrelated tests |
| test_repair | patch_size | 0.75 | Patch is minimal (<= 5 lines) |
| bug_localization | top1_accuracy | 0.6 | Correct file:line as top guess |
| bug_localization | top3_accuracy | 0.8 | Correct location in top 3 |
| bug_localization | wrong_file_rate | 0.15 | Wrong file identified |
| multi_file_edit | cross_file_consistency | 0.75 | Changes across files are consistent |
| multi_file_edit | patch_validity | 0.85 | All patches apply cleanly |
| multi_file_edit | over_edit_rate | 0.1 | Unnecessary changes made |

## Training Order
1. **SFT v2** → base adapter
2. **Diff Discipline v2** → strict patch output (Week 88)
3. **Test Repair v2** → test-driven repair (Week 89)
4. **Bug Localization v2** → find bug location (Week 90)
5. **Multi-File Edit v2** → cross-file changes (Week 91)

## Run Commands
```bash
# Step 1: SFT v2
python training/scripts/sft_train.py --config training/configs/sft_v2.yaml

# Step 2: Diff Discipline (uses SFT v2 as base)
python training/scripts/sft_train.py --config training/configs/diff_discipline_v2.yaml

# Step 3: Test Repair (uses Diff Discipline as base)
python training/scripts/sft_train.py --config training/configs/test_repair_v2.yaml

# Step 4: Bug Localization (uses SFT v2 as base)
python training/scripts/sft_train.py --config training/configs/bug_localization_v2.yaml

# Step 5: Multi-File Edit (uses SFT v2 as base)
python training/scripts/sft_train.py --config training/configs/multi_file_edit_v2.yaml
```