# Week 87 — SFT Monster v2 Eval Report
> Generated: 2026-05-16T23:40:04.461653+00:00

## Training Configuration
- ✅ Base model: Qwen/Qwen2.5-Coder-7B-Instruct (Qwen2.5-Coder-7B, correct)
- ✅   train_file: datasets/v2/sft/train/combined.jsonl (1824 lines)
- ✅   val_file: datasets/v2/sft/val/combined.jsonl (228 lines)
- ✅   test_file: datasets/v2/sft/test/combined.jsonl (228 lines)
- ✅   epochs: 3
- ✅   lr: 0.0002
- ✅   LoRA r=16

## Dataset v2 Eval Splits
- **v2_action_test**: 3 examples, 1 modalities
- **v2_critic_test**: 4 examples, 1 modalities
- **v2_heldout_hard**: 41 examples, 2 modalities
- **v2_sft_test**: 228 examples, 5 modalities

## Benchmark Delta Targets (v1 → v2)
| Metric | v1 | v2 Target | Delta |
|--------|-----|-----------|-------|
| bug_localization_top3 | 0.6 | 0.8 | +20% |
| multi_file_edit_success | 0.4 | 0.65 | +25% |
| patch_validity | 0.67 | 0.8 | +13% |
| refusal_accuracy | 0.8 | 0.92 | +12% |
| test_repair_pass@1 | 0.5 | 0.7 | +20% |
| tool_action_parse_rate | 0.75 | 0.9 | +15% |

## Training Status
Training has not been run yet.

### To run:
```bash
python training/scripts/sft_train.py --config training/configs/sft_v2.yaml
```

## V1 Failure Analysis (addressed by v2)
| v1 Failure | Root Cause | v2 Fix |
|------------|------------|--------|
| Patch invalid diffs | Not enough real diff examples | More mined real diffs; strict parser feedback |
| Test repair overfits to synthetic data | Synthetic tests too simple | Real repo test failure pairs |
| Bug localization too vague | Examples lack file:line specificity | Force specific location identification |
| Tool-use sequences unrealistic | 2-3 call traces | Teacher traces with 5-15 steps |
| Multi-file edit inconsistency | Independent generation | Coordinated cross-file verification |
| Refusal examples too few | Only 122 examples | Expand to 2,000+ nuanced categories |