# Week 71 — Lyme Model v0.1

**Date:** Week 71 of Year Two
**Action:** Define the Lyme Model v0.1 release.

---

## 1. Release Checklist

### Infrastructure
| Component | Status | Notes |
|-----------|:------:|-------|
| `src/lyme_model/` package | ✅ | 11 modules, all stubs |
| `__init__.py` with version | ✅ | v0.1.0-dev |
| Hardware profiler | ✅ | `hardware/detector.py`, `monitor.py`, `budget.py` |
| Local model runner | ✅ | `runtime/engine.py` (Ollama backend) |
| CLI (`lyme model`) | ✅ | run, list, profile, hardware, eval |
| Compression for small models | ✅ | `amplify/assembler.py`, `integration.py` |
| Tool controller | ✅ | `tools/registry.py`, `dispatch.py`, `fallback.py` |
| Eval harness | ✅ | `eval/harness.py` |

### Experiments
| Experiment | Status | Reference |
|-----------|:------:|-----------|
| Hardware baseline | ✅ | Week 55 |
| Raw capability benchmark | ✅ | Week 56 |
| Compression comparison | ✅ | Week 58 |
| Quantization analysis | ✅ | Week 61 |

### Documentation
| Document | Status | Notes |
|----------|:------:|-------|
| LYME_MODEL_DESIGN.md | ✅ | 1020 lines, complete architecture |
| LYME_MODEL_EXPERIMENTS.md | ✅ | Living experiment log |
| Year Two Roadmap | ✅ | Weeks 53-72 |

---

## 2. Demo Flow

```bash
# 1. Show hardware detection
lyme model hardware

# 2. List available models
lyme model list

# 3. Profile the model
lyme model profile --model deepseek-coder:6.7b

# 4. Run a task
lyme model run "Add error handling to the divide function"

# 5. Run evaluation
lyme model eval --model deepseek-coder:6.7b
```

---

## 3. Known Limitations

| Limitation | Impact | Planned Fix |
|-----------|--------|-------------|
| Single-turn only | No interactive sessions | Multi-turn agent loop |
| Ollama-only backend | No direct llama.cpp support | Direct GGUF loading |
| No speculative decoding | 10 tok/s ceiling | Speculative decode |
| Q4 only (Ollama default) | No quality comparison | Multi-quant testing |
| JSON file output | Not streamed to Audit | Audit telemetry integration |
| No interactive session | No `lyme model session` | Post-v0.1 |

---

## 4. Supported Hardware

| Tier | Hardware | Status |
|:----:|----------|:------:|
| ✅ | RTX 4060 8GB (tested) | Verified working |
| ✅ | RTX 3060 12GB | Expected to work |
| ✅ | M2 Pro 16GB | Expected via MLX |
| ⚠️ | CPU-only 16GB RAM | Slow but functional |
| ❌ | Integrated GPU (Intel/AMD) | Not supported |

---

## 5. Supported Models

| Model | Status | Notes |
|-------|:------:|-------|
| deepseek-coder:6.7b | ✅ Primary | Best speed/quality tradeoff |
| llama3:8b | ✅ Tested | Better hallucination resistance, slower |
| qwen2.5-coder:7b | ⚠️ Recommended | Not tested, same class |
| qwen2.5-coder:3b | ⚠️ Lightweight | Not tested |
| gpt-oss:20b | ❌ Not practical | Too slow on 8GB |

---

## 6. Evidence Summary

### What We Know Works

| Claim | Evidence | Confidence |
|-------|----------|:----------:|
| Local 7B models can complete basic coding tasks | 83-100% pass rate on 6-task benchmark | High |
| Compression improves quality on medium+ repos | 82% vs 78% (compressed vs raw) | Medium |
| Compression reduces tokens 86% | 2236 → 323 tokens | High |
| Compression speeds inference 1.6x | 27.5s → 17.5s | High |
| Q4 quantization is acceptable on 8GB VRAM | Fits with room for KV cache | High |
| Consumer hardware (8GB VRAM) can run 7B models | Measured 10 tok/s | High |

### What We Know Does NOT Work

| Claim | Evidence | Confidence |
|-------|----------|:----------:|
| Tools help in single-turn prompts | -50pp vs model-only | High |
| 20B models on 8GB VRAM | 36s avg, 50% timeout rate | High |
| Raw context for large repos | Degrades without compression | Medium |

### What We Don't Know Yet

| Question | Priority | Next Step |
|----------|:--------:|-----------|
| Does multi-turn help? | High | Build agent loop |
| Does speculative decoding help? | Medium | Direct llama.cpp integration |
| Does fine-tuning help? | Low | Wait for dataset + hardware |
| Does model routing help? | Medium | Multi-model loading test |
