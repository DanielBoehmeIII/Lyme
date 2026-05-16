# Week 60 — Local Agent Runtime MVP

**Date:** Week 60 of Year Two
**Action:** Build and verify the Lyme Model Runtime MVP.

---

## 1. MVP Components Built

### Runtime Engine (`src/lyme_model/runtime/engine.py`)

| Component | Status | Description |
|-----------|--------|-------------|
| `LocalInferenceEngine` | ✅ | Core generation via Ollama subprocess |
| `AgentRuntime` | ✅ | Full agent loop with history tracking |
| `InferenceResult` | ✅ | Structured output with metrics |

### Model Management (`src/lyme_model/runtime/loader.py`)

| Component | Status | Description |
|-----------|--------|-------------|
| `ModelLoader` | ✅ | Model discovery and hardware-aware selection |
| `ModelInfo` | ✅ | Model metadata dataclass |

### CLI (`src/lyme_model/cli.py`)

| Command | Status | Description |
|---------|--------|-------------|
| `lyme model run <task>` | ✅ | Execute a coding task |
| `lyme model list` | ✅ | List available models |
| `lyme model profile` | ✅ | Profile model performance |
| `lyme model hardware` | ✅ | Detect and report hardware |
| `lyme model eval` | ✅ | Run benchmark evaluation |

### Eval Harness (`src/lyme_model/eval/harness.py`)

| Component | Status | Description |
|-----------|--------|-------------|
| `ModelEvaluationHarness` | ✅ | Runs benchmark tasks through the runtime |
| Benchmark tasks | ✅ | repo-qa, code-gen, bug-find, latency, test-gen |

### Hardware Detection (reused from Week 55)

| Component | Status | Description |
|-----------|--------|-------------|
| `hardware/detector.py` | ✅ | CPU, RAM, GPU, disk detection |
| `hardware/monitor.py` | ✅ | Real-time GPU utilization tracking |
| `hardware/budget.py` | ✅ | VRAM budgeting and model feasibility |

### Amplification (reused from Week 58)

| Component | Status | Description |
|-----------|--------|-------------|
| `amplify/assembler.py` | ✅ | Context packet builder for small models |
| `amplify/integration.py` | ✅ | Amplification layer coordinator |

### Tool System (reused from Week 59)

| Component | Status | Description |
|-----------|--------|-------------|
| `tools/registry.py` | ✅ | 10-tool registry with size-optimized subsets |
| `tools/dispatch.py` | ✅ | Tool execution and result processing |
| `tools/fallback.py` | ✅ | Error recovery chains |

---

## 2. Verified Runtime Performance

```
Model: deepseek-coder:6.7b
Backend: Ollama (llama.cpp)
GPU: RTX 4060 Laptop (8GB VRAM)

Task: Write hello world function
  Success: True
  Time: 1.21s
  Throughput: 13.2 tok/s
  GPU utilization: 97%

Eval harness (3 tasks):
  repo-qa:    PASS (5.5s)
  code-gen:   PASS (5.9s)
  bug-find:   PASS (7.9s)
  Average:    6.5s per task
```

---

## 3. Data Flow

```
User Task ("add auth middleware")
    |
    v
AgentRuntime.run_task(task, context?)
    |
    +--> If context provided: build compressed prompt
    |       compression_result = CodebaseCompressor().compress(repo)
    |       packet = AmplificationLayer().amplify(task, compression)
    |       prompt = packet.to_text() + task
    |
    +--> Else: use raw prompt
    |
    v
LocalInferenceEngine.generate(prompt)
    |
    +--> [ollama run model_name prompt]
    |       GPU utilization: 97%
    |       Token throughput: 13.2 tok/s
    |
    v
InferenceResult (output, metrics, GPU stats)
    |
    v
Results stored in history, saved to file
```

---

## 4. Integration Points with Lyme Audit

| Point | What | Status |
|-------|------|--------|
| **Traces** | Every `run()` call emits an InferenceResult | ✅ Implemented |
| **Metrics** | Tokens/sec, latency, GPU util, VRAM | ✅ Captured per call |
| **Compression** | Uses Lyme Audit's `CodebaseCompressor` | ✅ Via amplify/ |
| **Telemetry** | Structured output saved to JSON | ✅ Via eval harness |
| **Benchmarks** | Runs through Audit-compatible benchmark suite | ✅ In eval/ |

### Audit Integration Flow

```
Lyme Model Runtime
  |
  +---> InferenceResult (to_dict)
  |       model_name, task, output, success
  |       time_s, tokens_per_second
  |       gpu_utilization, vram_used_mb
  |
  +---> Saved to lyme-output/model-eval-*.json
  |
  +---> Can be ingested by Lyme Audit's telemetry/
          (same JSON format, same metric structure)
```

---

## 5. CLI Verification

```bash
# Run a task
lyme model run "Add error handling to auth module"

# List available models
lyme model list

# Profile performance
lyme model profile --model deepseek-coder:6.7b

# Detect hardware
lyme model hardware

# Run evaluation
lyme model eval --model deepseek-coder:6.7b
```

---

## 6. Known Limitations

| Limitation | Impact | Future Work |
|-----------|--------|-------------|
| Single-turn only | No multi-turn agent loop yet | Week 63+ |
| Ollama-only backend | No direct llama.cpp integration | Post-MVP |
| No speculative decoding | Throughput limited to 13 tok/s | Week 62 |
| No adaptive quantization | Always uses Ollama default Q4 | Week 61 |
| No Audit trace persistence | Results saved but not streamed to Audit | Week 63 |
| No interactive session | No `lyme model session` | Post-MVP |
