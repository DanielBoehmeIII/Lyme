# Week 97 — SFT Feasibility Run

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/sft_experiment.py`
**Tests:** `tests/test_week97_sft_experiment.py` (27 tests, all passing)

**Experiment framework for supervised fine-tuning feasibility.** Compares 4 model variants:
1. Base model (raw, no prompting)
2. Prompted base model (few-shot in prompt)
3. Lyme Runtime base model (amplification + context packets)
4. Fine-tuned model (LoRA/QLoRA)

---

## 2. Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Target model | Qwen/Qwen2.5-Coder-1.5B |
| LoRA rank | 8 |
| Learning rate | 2e-4 |
| Epochs | 3 |
| Task | patch planning (plan_patch) |
| Training data | Lyme Model Dataset v0.1 (filtered) |
| Quantization | fp16 or QLoRA 4-bit |

---

## 3. Comparison Framework

| Variant | What It Measures | Why It Matters |
|---------|-----------------|----------------|
| Base model | Raw model quality on task | Baseline — can the model even understand the task? |
| Prompted base | Few-shot improvement | Is the model capable with better input? |
| Lyme Runtime | Amplification + retrieval | Does context help more than training? |
| Fine-tuned LoRA | Task-specific adaptation | Does training on task data help more than prompting? |

### Metrics

| Metric | What It Captures |
|--------|-----------------|
| Quality score | Task-specific accuracy (exact match + semantic) |
| Latency | End-to-end generation time |
| Memory | Peak VRAM/RAM during inference |
| General coding | Regression probes (5 Python knowledge questions) |
| Overfitting gap | Train accuracy - validation accuracy |

---

## 4. Hardware Requirements

Memory estimates for the 1.5B model:

| Configuration | Estimated VRAM | Feasible On |
|--------------|---------------|-------------|
| fp32 (no LoRA) | ~9 GB | 12GB+ GPUs |
| fp16 + LoRA r=8 | ~6 GB | 8GB+ GPUs |
| QLoRA 4-bit + LoRA r=8 | ~4 GB | 8GB GPUs |
| fp16 + LoRA r=8 + gradient ckpt | ~4.5 GB | 8GB GPUs |

**Conclusion:** QLoRA makes SFT feasible on consumer 8GB GPUs. Full training on 1.5B requires ~6GB with LoRA.

---

## 5. Training Pipeline

The `SFTTrainingHarness` class provides:
- `_train_real()` — Actual training using transformers + peft (when deps available)
- `_train_simulated()` — Simulation mode (current env)
- Memory estimation
- Dependency checking

Real training command (when deps installed):
```python
from src.lyme_model.learning.sft_experiment import SFTExperimentRunner, SFTExperimentConfig
config = SFTExperimentConfig(
    model_name='Qwen/Qwen2.5-Coder-1.5B',
    lora_r=8,
    num_epochs=3,
    use_qlora=True,
    task_filter='plan_patch',
)
runner = SFTExperimentRunner(config)
result = runner.run()
```

---

## 6. Files

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/sft_experiment.py` | Experiment config, training harness, 4 evaluators, runner |
| `tests/test_week97_sft_experiment.py` | 27 tests |

---

## 7. Next Week

Week 98 — Tool-Use Fine-Tuning: train a model specifically for tool-use decisions (search, read, edit, verify, stop).

---

## End of Week 97

**SFT feasibility framework built. 27 tests. 4 model variant comparison. LoRA/QLoRA support. Memory estimation. Real training ready when ML deps installed.**
