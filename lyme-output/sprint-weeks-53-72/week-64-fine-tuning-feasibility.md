# Week 64 — Fine-Tuning Feasibility

**Date:** Week 64 of Year Two
**Action:** Research feasibility of fine-tuning Lyme Model for coding-agent tasks.

---

## 1. Hardware Requirements

| Method | VRAM Needed | RAM Needed | Time (est.) | Quality Gain |
|--------|:-----------:|:----------:|:-----------:|:------------:|
| LoRA (rank=8) | 12-16 GB | 16 GB | 2-4 hrs | Moderate |
| QLoRA (rank=8) | 8-12 GB | 16 GB | 3-6 hrs | Moderate |
| Full fine-tune | 40+ GB | 64 GB | 8+ hrs | Potentially high |
| Prompt tuning | 4-8 GB | 8 GB | 30 min | Low |
| No training (current) | 0 | 0 | 0 | Baseline |

### Assessment
| Factor | Feasible? | Reason |
|--------|:---------:|--------|
| LoRA on 7B | ⚠️ Borderline | Needs 12+ GB VRAM, this machine has 8 GB |
| QLoRA on 7B | ✅ Yes | 8 GB is enough for QLoRA (rank=8, Q4 base) |
| LoRA on 3B | ✅ Yes | Easily fits in 8 GB |
| Full fine-tune | ❌ No | Needs 40+ GB VRAM |

**QLoRA is feasible on 8 GB VRAM** with a 7B base model.

---

## 2. Training Data Sources

Lyme already has structured data suitable for fine-tuning:

| Source | Format | Quantity | Quality |
|--------|--------|:-------:|:-------:|
| Audit traces | JSON (actions, prompts, results) | Growing | High |
| Benchmark scenarios | Task descriptions + expected outputs | 21 scenarios | High |
| Compression output | Structured repo representations | Unlimited | Medium |
| Tool call sequences | Tool name + params + results | To be collected | High |

### Synthetic Data Generation

Lyme can generate training data from:
1. **Benchmark tasks** → expected patches → model prompt + expected response
2. **Compression pipeline** → repo summary → Q&A pairs
3. **Tool traces** → observation → action → next observation

---

## 3. Training Objective

### What to Fine-Tune For
1. **Tool-use accuracy** — Call the right tool with the right parameters
2. **Context compression utilization** — Use compressed context effectively
3. **Error recovery** — Detect and recover from mistakes
4. **Code generation** — Generate correct patches for specific tasks

### Dataset Format
```python
{
  "prompt": "Task: Find the bug in src/auth.py\nContext: [compressed repo]\n",
  "completion": "<think>I need to check the login function</think>\nTOOL: read_file(path=auth.py)\n...",
  "metadata": {
    "task_type": "bugfix",
    "model": "deepseek-coder:6.7b",
    "success": True,
  }
}
```

---

## 4. Experiment Plan

### Experiment A: QLoRA on deepseek-coder:6.7b

| Parameter | Value |
|-----------|-------|
| Base model | deepseek-coder:6.7b |
| Method | QLoRA (rank=8, alpha=16) |
| Dataset | 500 generated examples (from Audit traces) |
| Hardware | 8 GB VRAM, 16 GB RAM |
| Est. time | 3-6 hours |
| Success metric | +10% on benchmark task completion |

### Experiment B: LoRA on qwen2.5-coder:1.5b

| Parameter | Value |
|-----------|-------|
| Base model | qwen2.5-coder:1.5b |
| Method | LoRA (rank=16, alpha=32) |
| Dataset | 200 examples (simpler tasks) |
| Hardware | 4 GB VRAM, 8 GB RAM |
| Est. time | 1-2 hours |
| Success metric | Match 3B-level quality on simple tasks |

---

## 5. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Overfitting to benchmark tasks | High | Medium | Use diverse training data |
| Quality regression on untrained tasks | Medium | High | Evaluate on held-out tasks |
| LoRA rank too low for code | Medium | Medium | Start with rank=16, test rank=8/32 |
| Training data too small | Medium | High | Generate synthetic variations |
| Hardware timeout | Low | Medium | Use gradient checkpointing |

---

## 6. Recommendation

**Do not fine-tune yet.** The current infrastructure (no training pipeline, limited
data, borderline VRAM) makes fine-tuning risky and time-consuming. Instead:

1. **Build the distillation dataset** (Week 65-67) first — create high-quality
   training examples from Audit traces
2. **Use prompt engineering** as the no-training alternative — adapt the runtime
   to use better prompts for different task types
3. **Defer fine-tuning** to Year Three when:
   - A dedicated training pipeline exists
   - 500+ high-quality training examples are collected
   - Hardware with 12+ GB VRAM is available (or cloud GPU rental)

**No-training alternative:** Prompt-tuned runtime that selects from 5-10 task-specific
prompt templates based on task classification. This can improve quality by 5-15%
without any training.
