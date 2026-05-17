# Lyme Model v0.1 — First SFT Adapter Release

**Date**: 2026-05-16  
**Status**: Experimental — Proof of fine-tuning pipeline  
**Local**: Runs entirely on consumer hardware (RTX 4060 8GB VRAM)

---

## What This Is

The first actual Lyme Model adapter — a LoRA adapter fine-tuned on top of deepseek-coder-6.7b-instruct for repository Q&A.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | 8GB VRAM (RTX 4060) | 12GB+ VRAM |
| RAM | 16GB | 32GB |
| Storage | 10GB free | 20GB free |
| Software | Ollama, Python 3.10+ | + CUDA 12.x |

## Installation

```bash
# 1. Base model
ollama pull deepseek-coder:6.7b

# 2. Load adapter
# The adapter is at adapters/deepseek-coder-6.7b-first-sft/
# Use with: python -c "
# from peft import PeftModel
# from transformers import AutoModelForCausalLM
# base = AutoModelForCausalLM.from_pretrained('deepseek-ai/deepseek-coder-6.7b-instruct')
# model = PeftModel.from_pretrained(base, 'adapters/deepseek-coder-6.7b-first-sft')
# "

# 3. Run inference via Ollama (base model for now)
ollama run deepseek-coder:6.7b "What framework is FastAPI?"
```

## Dataset

Generated synthetic dataset with 7,037 unique examples across 8 modalities:

| Modality | Count | Status |
|----------|-------|--------|
| combined (Repo Q&A) | 2,912 | Trained |
| repo_qa | 1,669 | Generated |
| all_modalities | 1,243 | Generated |
| tool_use | 455 | Generated |
| verification | 337 | Generated |
| unified_diff | 126 | Generated |
| patch_planning | 90 | Generated |
| bug_localization | 72 | Generated |
| test_repair | 32 | Generated |
| refusal | 20 | Generated |

## Training Results

| Metric | Value |
|--------|-------|
| Base model | deepseek-coder-6.7b-instruct |
| Method | QLoRA (4-bit nf4) |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Train examples | 2,332 |
| Validation examples | 290 |
| Test examples | 290 |
| Epochs | 3 |
| Total steps | 876 |
| Training time | 1h 45min |
| Final train loss | 0.174 |
| Final eval loss | 0.073 |
| Adapter size | 155 MB |

## Benchmark Results

| Category | Base Score | Notes |
|----------|------------|-------|
| Repo Understanding | 1.00 | Strong out of box |
| Hallucination Resistance | 1.00 | Good on known APIs |
| Evidence Grounding | 1.00 | Cites files correctly |
| Patch Correctness | 0.67 | Needs improvement |
| Syntax Validity | 0.50 | Sometimes wraps in markdown |
| Test Repair | 0.50 | Partial fix capability |
| **Overall** | **0.89** | Strong foundation |

## Known Limitations

1. **Dataset Diversity**: Synthetic templates limit variety. Need real repo traces.
2. **Adapter Integration**: Not yet mergeable into Ollama. Requires Python peft loading.
3. **Patch Quality**: Score of 0.67 — needs dedicated patch-planning training.
4. **Syntax**: Model sometimes wraps code in ``` markers.
5. **Context Length**: Capped at 1024 tokens during training.
6. **No Distillation**: No teacher model distillation done yet.
7. **No Quantization Research**: Using QLoRA nf4 — other formats untested.

## Repository Structure

```
training/
  configs/        — YAML training configs
  scripts/        — All training/generation scripts
datasets/
  schema.py       — Canonical dataset schema
  generated/      — Generated JSONL datasets (train/val/test)
adapters/          — Trained LoRA/QLoRA adapters
checkpoints/       — Training checkpoints
evals/             — Evaluation results
```

## Next Steps

1. Real-repo Q&A dataset (Lyme traces)
2. Patch planning dedicated training
3. Unified diff generation training
4. Tool-use policy training
5. Critic/verifier training
6. Distillation from stronger models
7. Quantization research (Q4/Q5/Q6/Q8)
8. Inference optimization
