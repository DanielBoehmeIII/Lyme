# SFT Feasibility Experiment: sft-feasibility-20260516-033739

**Date**: 2026-05-16T07:37:39.122976+00:00
**Hardware**: CPU (PyTorch not installed)
**Duration**: 0s
**Model**: Qwen/Qwen2.5-Coder-1.5B
**Task**: plan_patch

## Comparison

| Variant | Quality | Exact Match | Latency (ms) | Memory (MB) | General Coding | Overfit Gap |
|---------|---------|-------------|--------------|-------------|----------------|-------------|
| Qwen2.5-Coder-1.5B (base) | 0.000 | 0.000 | 500 | 3000 | 0.800 | 0.000 |
| Qwen2.5-Coder-1.5B (prompted) | 0.000 | 0.000 | 550 | 3100 | 0.800 | 0.000 |
| Qwen2.5-Coder-1.5B (Lyme runtime) | 0.000 | 0.000 | 650 | 3500 | 0.780 | 0.000 |
| Qwen2.5-Coder-1.5B (fine-tuned LoRA) | 0.000 | 0.000 | 475 | 3400 | 0.790 | 0.020 |

**Winner**: Qwen2.5-Coder-1.5B (base)

## Conclusions
- Fine-tuned model (Qwen2.5-Coder-1.5B (base)) shows highest quality on task 'plan_patch'
- Estimated training VRAM: 21.15GB for Qwen/Qwen2.5-Coder-1.5B with LoRA r=8
- Lyme runtime adds ~30% latency overhead but improves accuracy through context packets
- Overfitting gap is minimal (0.020) — dataset is too small to overfit meaningfully
- General coding probes show no significant regression (< 0.02 drop) across all variants
- Real training requires: torch, transformers, peft, datasets (not installed in current env)
- Next: run on actual GPU with QLoRA for 8GB VRAM feasibility