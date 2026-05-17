# Lyme Model Dataset v1 — Dataset Card

> Generated: 2026-05-16T22:24:07.803531+00:00

## Summary
- **Total examples**: 16,328
- **Splits**: 5
- **Sources**: Previous v0 data, Real repo mined (Week 42), Synthetic bugs (Week 43), Teacher traces (Week 44)

## Per-Split Breakdown
- **sft**: 13,263 examples
  - Train: 10,610
  - Val: 1,326
  - Test: 1,327
  - Modalities:
    - unified_diff: 7,328
    - patch_planning: 1,772
    - test_repair: 1,628
    - repo_qa: 1,561
    - long_horizon_planning: 240
    - self_repair: 240
    - multi_file_edit: 240
    - bug_localization: 134
    - refusal: 120
- **tool_policy**: 496 examples
  - Train: 396
  - Val: 50
  - Test: 50
  - Modalities:
    - tool_use: 496
- **critic**: 304 examples
  - Train: 243
  - Val: 30
  - Test: 31
  - Modalities:
    - verification: 304
- **eval_only**: 2,265 examples
  - Train: 1,812
  - Val: 226
  - Test: 227
  - Modalities:
    - unified_diff: 1,353
    - patch_planning: 274
    - test_repair: 247
    - repo_qa: 177
    - tool_use: 52
    - self_repair: 40
    - multi_file_edit: 40
    - long_horizon_planning: 40
    - verification: 34
    - bug_localization: 6
    - refusal: 2
- **held_out_real_repo**: 0 examples
  - Train: 0
  - Val: 0
  - Test: 0
  - Modalities:

## Per-Modality Totals
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

## Split Purposes
- **SFT**: Supervised fine-tuning on all task types. The main training split.
- **tool_policy**: Tool-use sequences for training tool call behavior.
- **critic**: Verification/approval examples for training the critic model.
- **eval_only**: Held-out evaluation examples (from test splits of source datasets).
- **held_out_real_repo**: Examples from cpython, not used in any training.

## Sources
- **Previous v0 data**: Synthetic examples covering 8 core modalities
- **Real repo mined (Week 42)**: 8,248 examples from 14 repos across Python, JS, Go, Rust
- **Synthetic bugs (Week 43)**: 3,900 examples across 13 bug types
- **Teacher traces (Week 44)**: 292 traces from curated solutions + qwen2.5-coder:7b, deepseek-coder:6.7b

## Usage
```python
from datasets.schema import LymeExample
import json

# Load SFT training data
with open("datasets/v1/sft/train/combined.jsonl") as f:
    for line in f:
        ex = LymeExample.from_dict(json.loads(line))
```

## License
Same as Lyme project: MIT
