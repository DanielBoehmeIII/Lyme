# Week 69 — Consumer Hardware Optimization

**Date:** Week 69 of Year Two
**Action:** Optimize Lyme Model for consumer hardware (the RTX 4060 laptop).

---

## 1. Baseline Performance

| Metric | Value | Source |
|--------|:-----:|--------|
| Model load time (Ollama) | 1-3s | Week 55 |
| Time to first token | ~1s | Estimated |
| Generation speed | 10.4 tok/s | Week 56 |
| Task completion (avg) | 6.5s | Week 60 |
| VRAM usage (Q4 6.7B) | ~5900 MB | Week 55 |
| GPU utilization | 97% peak | Week 56 |

---

## 2. Optimization Targets

| Area | Current | Target | Improvement | Effort |
|------|:-------:|:------:|:-----------:|:------:|
| Cold start | 3-8s | <2s | 3x | Low |
| Token throughput | 10.4 t/s | 15 t/s | 1.4x | Medium |
| Task latency | 6.5s | 4s | 1.6x | Medium |
| VRAM usage | 5900 MB | 5000 MB | 18% | High |
| Context utilization | ~60% | >80% | 33% | Low |

---

## 3. Optimization Techniques

### A. Model Loading (Cold Start)

| Technique | Improvement | Complexity |
|-----------|:-----------:|:----------:|
| Keep model warm (Ollama keepalive) | 3-8s → 0s | Low |
| Pre-warm during idle | 3-8s → 0s | Medium |
| Shared model across sessions | 3-8s → 0s | Low |

**Recommendation:** Set Ollama `keepalive` to 5 minutes. This keeps the model
loaded between tasks, eliminating cold start.

### B. Inference Speed

| Technique | Improvement | Complexity |
|-----------|:-----------:|:----------:|
| Use smaller model for simple tasks | 2x | Medium (routing) |
| Reduce prompt length | 1.2x | Low (compression) |
| Batch prompt processing | 1.1x | Low |
| Increase GPU clock speed | 1.05x | Low (nvidia-smi) |

**Recommendation:** The largest gain comes from task routing (Week 63) —
using a 3B model for simple tasks and 6.7B only for complex ones.

### C. Memory Footprint

| Technique | VRAM Saved | Complexity |
|-----------|:----------:|:----------:|
| Reduce KV cache size | ~500 MB | Low |
| Use Q4 instead of Q5 | ~1000 MB | Low |
| Unload unused layers | ~200 MB | High |
| Process in CPU-only mode | ~5000 MB | Low |

**Recommendation:** Q4_K_M quantization is the best tradeoff for 8GB VRAM.
Don't try to squeeze more - accept the 8GB constraint.

### D. Context Packing

| Technique | Improvement | Complexity |
|-----------|:-----------:|:----------:|
| Prioritize important context first | 1.3x better attention | Medium |
| Remove redundant instructions | 1.1x | Low |
| Compress tool descriptions | 1.05x | Low |
| Use cheaper embeddings | 1.1x | Low |

**Recommendation:** Order context as: task > relevant files > repo structure >
tool descriptions. The model attends better to content at the start of context.

---

## 4. Hardware Tiers

| Tier | Hardware | VRAM | Models | Expected Performance |
|:----:|----------|:----:|--------|:-------------------:|
| **Minimum** | RTX 3060 12GB / M2 Pro 16GB | 12-16 GB | 7B Q5 + 1.5B draft | 15 tok/s, full agent loop |
| **Target** | RTX 4060 8GB / M2 16GB | 8-16 GB | 7B Q4 | 10 tok/s, basic agent |
| **Budget** | CPU only (16GB RAM) | 0 GB | 3B Q4 (CPU) | 3 tok/s, limited tasks |
| **Premium** | RTX 4090 24GB / M4 Max | 24-48 GB | 14B Q4 + 7B Q4 | 25 tok/s, full stack |

---

## 5. Final Optimized Configuration

```
Model: deepseek-coder:6.7b (Q4_K_M)
Backend: Ollama (keepalive=5m)
VRAM: ~5900 MB (model) + ~1400 MB (KV cache) = ~7300 MB

Optimizations applied:
  ✅ Compression (86% context reduction)
  ✅ Task-specific prompt templates
  ✅ Prioritized context ordering
  ✅ Warm model (no cold start)
  
Not applied (future):
  ❌ Speculative decoding
  ❌ Model routing
  ❌ Fine-tuning

Expected performance after optimizations:
  Task latency: 5-6s (vs 6.5s baseline, ~20% improvement)
  Throughput: ~12 tok/s (vs 10.4 baseline, ~15% improvement)
  Context budget: fits tasks up to ~4000 tokens in context
```
