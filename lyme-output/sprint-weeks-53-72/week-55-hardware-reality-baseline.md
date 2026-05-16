# Week 55 — Hardware Reality Baseline

**Date:** Week 55 of Year Two
**Action:** Measure the actual hardware Lyme Model will run on.

---

## 1. Hardware Profile

### Machine Specs

| Component | Detail |
|-----------|--------|
| **CPU** | 12th Gen Intel(R) Core(TM) i7-12650H (16 cores) |
| **RAM** | 16.5 GB total (6.0 GB available at baseline) |
| **GPU** | NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM, 8188 MiB) |
| **Driver** | 535.288.01 (CUDA 12.2) |
| **Disk** | 500 GB NVMe (156 GB free) |
| **Platform** | Linux 6.17.0, x86_64 |
| **Ollama** | v0.17.4, available |

### Classification

This is a **mid-range consumer laptop** from 2023. Not a workstation, not a server.
This is exactly the hardware Lyme Model targets: ordinary consumer GPU with 8 GB VRAM.

---

## 2. Measured Model Performance

### Inference Latency

| Model | Size | Tokens/s | Gen Time (s) | Output Chars |
|-------|------|----------|-------------|-------------|
| deepseek-coder:6.7b | 6.7B | **10.4** | 11.6 | 778 |
| llama3:8b | 8.0B | **7.3** | 10.1 | 506 |
| gpt-oss:20b | 20B | **7.2** | 36.8 | 2037 |

### GPU Utilization (deepseek-coder:6.7b)

| Metric | Value |
|--------|-------|
| Idle VRAM | 5895 MiB / 8188 MiB (72%) |
| Peak GPU util | **98%** |
| Avg GPU util | 26% |
| Peak VRAM during inference | 5895 MiB (no delta — model pre-loaded by Ollama) |
| Peak temperature | 70°C |
| Power | 13W idle, burst to 60W limit |

**Key finding:** GPU utilization spikes to 98% during generation. The model is
GPU-bound, not CPU-bound. This means optimizations to generation speed will have
direct impact on throughput.

---

## 3. VRAM Analysis

### Available VRAM for Models

| Usage | MiB |
|-------|-----|
| Total VRAM | 8188 |
| OS/Display | ~300 |
| Ollama baseline (loaded model) | ~5886 |
| **Free for inference** | **~2000** |

When a model is loaded, Ollama retains it in VRAM (~5886 MiB for deepseek-coder 6.7B).
This leaves ~2000 MiB for KV cache and context.

### Model Feasibility Matrix

| Model Size | Q8 | Q6 | Q5 | Q4 |
|-----------|-----|-----|-----|-----|
| **1.5B** (draft) | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE |
| **3B** (light) | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE |
| **7B** (primary) | ⚠️ BORDERLINE | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE |
| **8B** | ❌ NO | ✅ FEASIBLE | ✅ FEASIBLE | ✅ FEASIBLE |
| **14B** | ❌ NO | ❌ NO | ❌ NO | ❌ NO |
| **20B** | ❌ NO | ❌ NO | ❌ NO | ❌ NO |

**7B at Q8 barely fits:** VRAM needed ~7884 MB. With OS overhead, context is ~0.
**7B at Q6** is the sweet spot: ~5918 MB VRAM, leaving ~2000 MB for KV cache (~878K tokens context).

---

## 4. Expected Latency Bands

| Model | Q4 tok/s | Q6 tok/s | Q8 tok/s | TTFT estimate |
|-------|---------|---------|---------|--------------|
| deepseek-coder:6.7b | 10-12 | 8-10 | 5-7 | ~1-2s |
| qwen2.5-coder:3b | 20-30 | 15-20 | 10-15 | ~0.5-1s |
| qwen2.5-coder:1.5b | 40-60 | 30-40 | 20-30 | ~0.3-0.5s |
| llama3:8b | 7-9 | 5-7 | 3-5 | ~1-2s |

TTFT (time-to-first-token) varies by prompt processing length.

---

## 5. Recommendations

### Primary Model
**deepseek-coder:6.7b at Q6 or Q4_K_M**

- Fits in 8 GB VRAM with room for KV cache
- Measured 10.4 tok/s (sufficient for interactive use)
- Code-specialized (not general-purpose like llama3)
- 6.7B parameters strong enough for meaningful benchmark comparisons

### Draft Model (speculative decoding)
**qwen2.5-coder:1.5b at Q4**

- Fits in ~1 GB VRAM
- Expected 40-60 tok/s
- Can run alongside 7B model in hybrid mode

### Lightweight Agent
**qwen2.5-coder:3b at Q4**

- Fits in ~2 GB VRAM
- Expected 20-30 tok/s
- Good for classification, simple tasks, routing decisions

### What Does NOT Fit
- 14B+ models at any quantization
- Multiple large models simultaneously

---

## 6. Thermal/Slowdown Behavior

| Condition | Temp | Power | Notes |
|-----------|------|-------|-------|
| Idle | 58°C | 13W | GPU in P8 low-power state |
| Active inference | 70°C | ~60W | GPU in P0 high-performance state |
| Sustained load | 70-75°C | 60W | Thermal limit not reached during short runs |

**Laptop GPU thermal behavior:** The RTX 4060 laptop likely throttles after
5-10 minutes of sustained load. Brief benchmark runs (10-30s) do not trigger
throttling. Longer sessions would need thermal monitoring.

---

## 7. Latency Budget for Agent Loop

For a multi-turn coding agent session:

| Step | Est. Time (7B, Q4) |
|------|-------------------|
| Model load (cold start) | 3-8s (can cache) |
| Prompt processing | 1-3s (varies with context) |
| First token | 0.5-2s |
| Per generated token | ~100ms (10 tok/s) |
| Tool execution (read file) | 0.1-0.5s |
| Tool execution (run tests) | 5-60s+ |
| Context management | ~0.1s |

**Estimated time for a 3-turn bug fix:** 30-90 seconds (excluding test runs).
This is usable but slower than cloud API models (which do the same in 5-15s).

---

## 8. Integration with Lyme Audit Telemetry

The hardware profile is now recordable through Audit telemetry:

```python
from lyme_model.hardware.detector import detect_all

profile = detect_all()
# profile.to_dict() can be stored as Audit telemetry metadata
# Every benchmark run stores the hardware profile with results
```

The monitor module allows runtime GPU tracking:

```python
from lyme_model.hardware.monitor import HardwareMonitor

monitor = HardwareMonitor()
gpu = monitor.sample_gpu()  # Real-time GPU metrics
inference = monitor.measure_inference(model_name, prompt, generate_func)
```

---

## 9. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/hardware/detector.py` | Hardware detection: CPU, RAM, GPU, disk, Ollama |
| `src/lyme_model/hardware/monitor.py` | Runtime GPU monitoring during inference |
| `src/lyme_model/hardware/budget.py` | VRAM estimation, model feasibility suggestions |
| `lyme-output/sprint-weeks-53-72/hardware-baseline-results.json` | Raw benchmark data |

---

## 10. Key Takeaways for Lyme Model

1. **8 GB VRAM is the binding constraint.** This caps us at 7B-8B models. No 14B+ without cloud.
2. **10 tok/s is the baseline for a 7B code model.** This is usable for interactive coding (slow but not unusable).
3. **GPU is fully utilized during generation** (98% peak). Optimizations to generation speed matter.
4. **Cold start matters.** Model loading takes 3-8s. Keeping the model loaded in Ollama avoids this.
5. **Thermal throttling is a concern** for sustained sessions. Long agent loops (>5 min) may degrade.
6. **A 1.5B draft model can run alongside the primary** on this hardware for speculative decoding experiments.
7. **This RTX 4060 laptop is representative consumer hardware.** Results generalize to similar GPUs (RTX 3060-4070, 8-12 GB).
