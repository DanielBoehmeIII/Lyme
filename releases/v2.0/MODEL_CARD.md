# Lyme Model v2.0

> Release Date: 2026-05-16
> Phase 14, Week 92

## Overview

Lyme Model v2.0 is a local coding model adaptation system built on Qwen2.5-Coder-7B-Instruct.
It is trained on Dataset v2 (3,325 curated examples across 9 modalities) with 5 specialized
training stages.

## Components

| Component | Base | Description |
|-----------|------|-------------|
| SFT v2 | Qwen2.5-Coder-7B | Supervised fine-tuning on all dataset modalities |
| Diff Discipline v2 | SFT v2 | Strict unified diff output training |
| Test Repair v2 | Diff Discipline | Test-driven repair specialization |
| Bug Localization v2 | SFT v2 | Bug location identification |
| Multi-File Edit v2 | SFT v2 | Cross-file coordinated changes |

## Dataset

- **Dataset v2**: 3,325 examples (train 2,829 / val 228 / test 268)
- **9 modalities**: unified_diff, patch_planning, repo_qa, bug_localization, tool_use, refusal, verification, multi_file_edit, preference
- **Sources**: v1 pre-existing, public repo mining, synthetic failures, teacher traces

## Training Hardware

- GPU: NVIDIA RTX 4060 Laptop (8GB VRAM)
- Base: Qwen2.5-Coder-7B-Instruct (Q4_K_M)
- Method: QLoRA (r=16, alpha=32, nf4)
- Epochs: 3 (SFT), 2 (specializations)

## Known Limitations

- 7B parameter ceiling: complex multi-step reasoning still limited
- Dataset v2 is smaller than v1 (3,325 vs 16,328) but higher quality
- Real repo mining pipeline not yet populated (Week 82)
- Best-of-N and critic integration planned for v2.1

## Usage

```python
from lyme_model.runtime import LocalInferenceEngine

engine = LocalInferenceEngine(model_name="Qwen/Qwen2.5-Coder-7B-Instruct",
                               adapter_path="adapters/v2.0/sft_v2")
response = engine.generate("Fix this bug: ...")
```
