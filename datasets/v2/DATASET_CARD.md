# Lyme Model Dataset v2 — Dataset Card

> Generated: 2026-05-16T23:23:56.498207+00:00
> Assembly: Week 85

## Summary
- **Total examples**: 3613
- **Total unique**: 2385
- **Splits**: 7
- **Sources**: 6
- **Modalities**: 9

## Sources
- **mined**: 0 raw → 0 after filter
- **synthetic_failures**: 750 raw → 422 after filter
- **teacher_traces**: 100 raw → 90 after filter
- **v1_critic**: 243 raw → 243 after filter
- **v1_existing**: 10610 raw → 5674 after filter
- **v1_tool_policy**: 396 raw → 335 after filter

## Split Breakdown
- **action**: {'train': 19, 'val': 2, 'test': 3}
- **critic**: {'train': 32, 'val': 4, 'test': 4}
- **eval_only**: {'train': 0, 'val': 0, 'test': 0}
- **heldout_hard**: {'train': 0, 'val': 0, 'test': 41}
- **preference**: {'train': 1000, 'val': 0, 'test': 0}
- **reward**: {'train': 182, 'val': 23, 'test': 23}
- **sft**: {'train': 1824, 'val': 228, 'test': 228}

## Per-Modality Totals
- bug_localization: 43
- multi_file_edit: 5
- patch_planning: 690
- preference: 1000
- refusal: 17
- repo_qa: 55
- tool_use: 24
- unified_diff: 1739
- verification: 40

## Split Purposes
- **sft**: Main supervised fine-tuning on all task types
- **action**: Tool-use action sequences for training tool behavior
- **critic**: Patch critique/verification examples
- **reward**: Preference/reward model training data
- **heldout_hard**: Expert-difficulty examples, never used in training
- **eval_only**: Held-out evaluation (from test splits)
- **preference**: Generated preference pairs for DPO/RLHF

## Usage
```python
from datasets.schema import LymeExample
import json

with open('datasets/v2/sft/train/combined.jsonl') as f:
    for line in f:
        ex = LymeExample.from_dict(json.loads(line))
```