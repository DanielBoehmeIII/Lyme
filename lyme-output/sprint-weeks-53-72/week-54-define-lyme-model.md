# Week 54 — Define Lyme Model

**Goal:** Design Lyme Model as a focused local coding-agent system that makes small/local models perform better through architecture.

---

## 1. Design Principle

Lyme Model is NOT a new LLM. It is NOT a cloud service. It is NOT a general-purpose chatbot.

**It is a purpose-built local runtime that amplifies small models through architecture.**

The thesis: architecture can compensate for parameter count. A 7B model with compression,
retrieval, tool routing, and speculative decoding can approach Claude/Codex/OpenCode quality
on coding-agent tasks.

## 2. Architecture Overview (from LYME_MODEL_DESIGN.md)

```
+-------------------------------------------------------------+
|                   LYME MODEL RUNTIME                         |
+-------------------------------------------------------------+
|                                                             |
|  +-------------------------------------------------------+  |
|  |  LAYER 5: AGENT LOOP                                   |  |
|  |  Orchestrator . Turn Management . Tool Dispatch        |  |
|  |  Stream Handler . Error Recovery . Planning            |  |
|  +---------------------------+---------------------------+  |
|                              |                              |
|  +---------------------------v---------------------------+  |
|  |  LAYER 4: MODEL AMPLIFICATION                         |  |
|  |  Context Assembly . Retrieval Fusion . Prompt Opt.    |  |
|  |  Tool Minimization . Instruction Compression          |  |
|  +---------------------------+---------------------------+  |
|                              |                              |
|  +---------------------------v---------------------------+  |
|  |  LAYER 3: INFERENCE ENGINE                            |  |
|  |  Model Loader . KV Cache . Speculative Decode         |  |
|  |  Token Generation . Stream Processing                 |  |
|  +------+------------------+------------------+----------+  |
|         |                  |                  |             |
|  +------v------+    +------v------+    +------v------+     |
|  | GPU         |    | CPU         |    | Hybrid      |     |
|  | Sched.      |    | Sched.      |    | Sched.      |     |
|  +------+------+    +------+------+    +------+------+     |
|         |                  |                  |             |
|  +------v------------------v------------------v----------+  |
|  |  LAYER 2: HARDWARE ABSTRACTION                        |  |
|  |  GPU/CPU/VRAM Detection . Topology Map                |  |
|  |  Memory Budget . Device Selection                     |  |
|  +---------------------------+---------------------------+  |
|                              |                              |
|  +---------------------------v---------------------------+  |
|  |  LAYER 1: MODEL STORE                                 |  |
|  |  Quantized Models . Adapter Registry                  |  |
|  |  Version Control . Metadata Cache                     |  |
|  +-------------------------------------------------------+  |
|                                                             |
+-------------------------------------------------------------+
|  INTEGRATION WITH LYME AUDIT                                |
|  +------------+ +----------+ +--------+ +--------------+  |
|  | Telemetry  | | Memory   | | Comp.  | | Benchmark    |  |
|  | (traces)   | | (store)  | | (L1-5) | | (evaluation) |  |
|  +------------+ +----------+ +--------+ +--------------+  |
+-------------------------------------------------------------+
```

## 3. Audit Measurement Requirement (MANDATORY)

Every Lyme Model run MUST be measured by Lyme Audit. This is enforced by design:

| Requirement | Mechanism |
|-------------|-----------|
| Every model run emits a trace | `telemetry/` import in `runtime/` |
| Every benchmark uses Audit engine | `eval/` wraps `benchmark/engine` |
| No unmeasured runs | CLI enforces trace capture before execution |
| Regression detection | `evaluation/` compares against prior runs |
| Hallucination tracking | `cognition/anomaly_detection` on all outputs |

**The CLI enforces this:**
```bash
lyme model run "add auth"        # Auto-captures trace via Audit telemetry
lyme model eval --scenario fix   # Runs through Audit benchmark engine
```

There is no `--no-audit` flag. Every run is measured.

## 4. Component Architecture

### Layer 1 — Model Store (`src/lyme_model/runtime/`)
- Model registry (GGUF, safetensors)
- Quantization management
- Metadata: VRAM, tokens/sec, quality scores
- Backend: llama.cpp (primary), MLX (Apple Silicon), OpenAI-compatible (comparison)

### Layer 2 — Hardware Abstraction (`src/lyme_model/hardware/`)
- GPU/CPU/VRAM detection
- Device map: optimal layer placement
- Memory budget: model + KV cache allocation
- Thermal monitoring (if detectable)

### Layer 3 — Inference Engine (`src/lyme_model/runtime/`)
- Model loading, prompt processing, token generation
- KV cache management (PagedAttention-style)
- Speculative decoding: draft model (0.5-1.5B) + target (3-8B)
- Streaming, stop conditions, error recovery

### Layer 4 — Model Amplification (`src/lyme_model/amplify/`)
- **Context assembly:** compression (Audit L1-L5) + retrieval (BM25 + embedding) + memory
- **Prompt optimization:** instruction compression, example pruning, template selection
- **Tool minimization:** filter relevant tools, cache schemas, shorten descriptions
- **Context budgeting:** fit highest-value content into window

### Layer 5 — Agent Loop (`src/lyme_model/amplify/` or separate orchestrator)
- Task decomposition → reasoning → action → observation → loop
- Turn management, tool dispatch, error recovery
- Structured output parsing, JSON mode
- State management: session context, checkpoints, recovery

## 5. Model Support Strategy

| Model Size | Quantization | Hardware | Role |
|-----------|-------------|----------|------|
| 0.5-1.5B | Q4-Q8 | Any | Draft model for speculative decoding |
| 3B | Q4-Q8 | 6GB+ VRAM | Lightweight agent, classification |
| 7-8B | Q4-Q6 | 12GB+ VRAM | Primary coding agent |
| 14B | Q4 | 24GB+ VRAM | Stronger reasoning (if available) |
| 32B | Q4 | 48GB+ VRAM | Frontier comparison (if available) |

## 6. CLI Design

```bash
lyme model run "task"           # Execute a coding task
lyme model session              # Interactive session (like Claude Code)
lyme model list                 # Available models
lyme model pull <name>          # Download a model
lyme model quantize <name>      # Quantize a model
lyme model profile <name>       # Profile model performance
lyme model eval [--scenario]    # Evaluate on benchmark
lyme model hardware             # Hardware detection + recommendations
lyme model serve                # Start local API server
```

## 7. Initial Package Structure

```
src/lyme_model/
  __init__.py                   # Package init, version
  cli.py                        # lyme model subcommands
  config.py                     # Model-specific configuration
  runtime/
    __init__.py
    engine.py                   # InferenceEngine: load, generate, stream
    loader.py                   # ModelLoader: GGUF, safetensors, adapter
    kv_cache.py                 # KV cache manager
    stream.py                   # Token stream handler
    config.py                   # Generation parameters
    errors.py                   # Inference-specific errors
  amplify/
    __init__.py
    assembler.py                # ContextAssembler
    optimizer.py                # PromptOptimizer
    tool_min.py                 # ToolMinimizer
    retrieval.py                # RetrievalFusion
    budget.py                   # ContextBudget
    integration.py              # L0 coordinator
  quant/
    __init__.py
    manager.py                  # QuantManager
    selector.py                 # QuantSelector
    profile.py                  # Quant benchmark
    convert.py                  # On-device conversion
    registry.py                 # Known working quants
  decode/
    __init__.py
    speculative.py              # SpeculativeDecode
    draft.py                    # Draft model manager
    verify.py                   # Parallel verification
    schedule.py                 # Dynamic K selection
    code_accel.py               # Code-specific optimizations
    metrics.py                  # Acceptance rate tracking
  tools/
    __init__.py
    optimizer.py                # ToolOptimizer
    schemas.py                  # Schema caching
    dispatch.py                 # Tool execution
    fallback.py                 # Fallback chain
    registry.py                 # Available tools
  hardware/
    __init__.py
    detector.py                 # GPU/CPU/VRAM detection
    scheduler.py                # Dynamic device allocation
    topology.py                 # PCIe, NUMA topology
    budget.py                   # VRAM budgeting
    monitor.py                  # Runtime monitoring
  context/
    __init__.py
    window.py                   # ContextWindow
    eviction.py                 # Smart eviction
    compression.py              # On-the-fly compression
    summary.py                  # Rolling summary
    budget.py                   # Token budget allocation
  distill/
    __init__.py
    distill.py                  # Distillation pipeline
    finetune.py                 # Fine-tuning orchestration
    data.py                     # Training data curation
    eval.py                     # Post-training evaluation
    curriculum.py               # Curriculum learning
  serve/
    __init__.py
    server.py                   # Local API server
    batcher.py                  # Dynamic batching
    cache.py                    # Response cache
    health.py                   # Health checks
  eval/
    __init__.py
    harness.py                  # Evaluation harness
    suite.py                    # Model-specific task suite
    compare.py                  # Model comparison
    regression.py               # Regression detection
    leaderboard.py              # Local leaderboard
```

## 8. What This Design Assumes

| Assumption | Risk | Mitigation |
|-----------|------|------------|
| llama.cpp can load and run models on consumer GPU | Backend may not support all hardware | Multiple backends (llama.cpp, MLX, OpenAI) |
| Existing Audit compression is correct | Compression may not help small models | Test in Week 58, redesign if needed |
| Local models can complete coding tasks at all | Models may be too weak | Week 56 baseline, gate decision |
| 7B + compression can approach 70B quality | Compression parity may fail | Week 57 experiment, pivot if needed |
| Quantization Q4 is acceptable | Quality loss may be too high | Week 61 systematic study |

## 9. Verification: Audit Integration Check

Before any Lyme Model release, Audit must confirm:
1. All benchmark scenarios pass at >= previous release rate
2. Hallucination rate within noise of previous version
3. P99 latency under threshold
4. Reproducible: same seed + prompt = same result
5. Comparable: cloud baseline measured for the same scenario
