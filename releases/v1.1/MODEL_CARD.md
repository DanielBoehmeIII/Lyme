# Lyme Model v1.1 — Model Card

> Generated: 2026-05-16T23:00:32.096743+00:00

## Model Overview
- **Base Model**: Qwen/Qwen2.5-Coder-0.5B-Instruct
- **Fine-tuning Method**: QLoRA (4-bit NF4, LoRA r=16, alpha=32)
- **Training Data**: Lyme Dataset v1 (16,328 examples across 10 modalities)
- **Specializations**: tool-use, diff-only, test repair, multi-file edit, critic

## Training Summary
| Component | Status | Epochs | Train Examples |
|-----------|--------|--------|----------------|
| SFT v1 | 🔄 In progress | 2 | 10,610 |
| Tool-Use | ✅ Dataset ready | - | 168 |
| Diff Discipline | ✅ Dataset ready | - | 189 |
| Test Repair | ✅ Dataset ready | - | 210 |
| Multi-File Edit | ✅ Dataset ready | - | 125 |
| Critic v1 | ✅ Dataset ready | - | 244 |

## Performance Metrics
| Metric | Base Model | SFT v1 |
|--------|-----------|--------|
| Valid diff rate | TBD% | TBD% |
| Test repair success | TBD% | TBD% |
| Evidence use | TBD% | TBD% |

## Hardware Requirements
- **Training**: 8GB VRAM GPU (RTX 4060 laptop) with QLoRA
- **Inference**: 4GB VRAM or CPU with 16GB RAM
- **Quantization**: 4-bit NF4 (2.5GB model size)

## Included Components
1. SFT v1 LoRA adapter
2. Dataset v1 (16,328 examples)
3. Specialized datasets (tool-use, diff, test repair, multi-file, critic)
4. Training configurations for each specialization
5. Evaluation suite

## Known Limitations
- 0.5B parameter model — limited reasoning capacity vs 7B+ models
- Training on single GPU with small batch size
- Datasets are synthetic/mined — limited real-world diversity
- No RLHF/DPO training yet
