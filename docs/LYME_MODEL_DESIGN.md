# Lyme Model Design

**Splitting Lyme into Measurement + Intelligence**

---

## Table of Contents

1. [Boundary: Lyme Audit vs Lyme Model](#1-boundary-lyme-audit-vs-lyme-model)
2. [The Lyme Model Thesis](#2-the-lyme-model-thesis)
3. [Model/Runtime Architecture](#3-modelruntime-architecture)
4. [Reused Lyme Audit Systems](#4-reused-lyme-audit-systems)
5. [New Lyme Model Modules](#5-new-lyme-model-modules)
6. [First Empirical Experiment](#6-first-empirical-experiment)
7. [MVP Definition](#7-mvp-definition)
8. [Year Two Roadmap (Lyme Model Only)](#8-year-two-roadmap-lyme-model-only)
9. [Lyme Audit as Lab Instrument](#9-lyme-audit-as-lab-instrument)

---

## 1. Boundary: Lyme Audit vs Lyme Model

### Ownership Split

| Domain | Lyme Audit | Lyme Model |
|---|---|---|
| **Identity** | Measurement platform | Local intelligence system |
| **Core question** | "How good is this agent?" | "How do we make the agent better?" |
| **Primary user** | Researcher | Developer / end-user |
| **Output** | Reports, traces, benchmarks, metrics | Code edits, completions, analysis, actions |
| **Scope** | Generic - any agent, any model | Specific - Lyme's own model/runtime |
| **Model role** | Observes and measures models | IS the model/runtime |
| **Evaluation** | Runs benchmarks, produces scores | IS what gets benchmarked |
| **Data** | Traces, comparisons, research corpora | Inference state, context, generations |
| **Persistence** | Memory store, audit logs, research corpus | KV cache, quantization state, adapter weights |

### What Lyme Audit Keeps (untouched)

Everything in `src/lyme/` stays. Lyme Audit retains:

- `compression/` - Multi-layer codebase compression (L1-L5)
- `memory/` - Persistent procedural/episodic/semantic store
- `benchmark/` - Scenario registry, engine, runner
- `cognition/` - Tracing, thought analysis, anomaly detection
- `replay/` - Deterministic and diff replay
- `telemetry/` - Tracing, events, metrics, spans
- `graph/` - Causal software graph analysis
- `discovery/` - Invariant mining and violation detection
- `models/` - Capability matrix and model evaluation
- `experiments/` - Anti-hallucination, tool-use benchmarks
- `evaluation/` - Self-benchmark, longitudinal eval
- `epistemology/` - Evidence theory, confidence calibration
- `governance/` - Autonomy policy, review boards
- `verification/` - Verification graphs, gap detection
- `evolution/` - Evolution analysis and mutation
- `research/` - Intelligence dimensions, scaling laws
- `standards/` - OATS, SDS, Cognition Benchmark Spec
- All CLI commands, all tests, all configs, all release plans

Zero deletion. Zero removal. Zero deprecation.

### What Lyme Model Introduces (new)

New modules under `src/lyme_model/`:

```
src/lyme_model/
  __init__.py
  cli.py                  # lyme model subcommands
  config.py               # Model-specific configuration
  runtime/                # Core inference engine + agent loop
  amplify/                # Small-model force multipliers
  quant/                  # Quantization selection + management
  decode/                 # Speculative decoding
  tools/                  # Tool-use optimization for small models
  hardware/               # Hardware-aware scheduling
  context/                # Context management for local models
  distill/                # Fine-tuning / distillation pipeline
  serve/                  # Local model serving
  eval/                   # Model-specific evaluation harness
```

These live alongside (not inside) the existing `src/lyme/` modules.
They are a peer namespace, not a fork.

### Communication Protocol

```
+-----------------------+       +-----------------------+
|     LYME AUDIT        |       |     LYME MODEL        |
|                       |       |                       |
|  benchmark/engine ----+-------+---> eval/ harness     |
|  compression/ --------+-------+---> amplify/ (reuses) |
|  memory/ -------------+-------+---> context/ (reuses) |
|  telemetry/ ----------+-------+---> runtime/ (instr.) |
|  cognition/ ----------+-------+---> runtime/ (traces) |
|  replay/ -------------+-------+---> runtime/ (replay) |
|  models/ -------------+-------+---> quant/ (profiles) |
|                       |       |                       |
|  <--- traces ---------+-------+--- Generation ------> |
|  <--- metrics --------+-------+--- Actions ---------> |
|  <--- eval results ---+-------+--- State -----------> |
+-----------------------+       +-----------------------+
```

- Lyme Model generates traces, metrics, and state
- Lyme Audit reads them: evaluates, compares, stores, analyzes
- Lyme Model imports Audit utilities (compression, memory) as libraries
- Audit never imports Model - it remains model-agnostic
- The shared telemetry substrate carries all cross-system data

### File System Layout

```
src/
  lyme/                         <-- LYME AUDIT (untouched)
    cli.py
    benchmark/
    memory/
    compression/
    cognition/
    replay/
    telemetry/
    ... (66 modules, all preserved)

  lyme_model/                   <-- LYME MODEL (new)
    __init__.py
    cli.py                      # lyme model ... subcommands
    config.py                   # Model-specific config
    runtime/
    amplify/
    quant/
    decode/
    tools/
    hardware/
    context/
    distill/
    serve/
    eval/

docs/
  LYME_MODEL_DESIGN.md          <-- This document
  LYME_MODEL_EXPERIMENTS.md     # Experiment log

pyproject.toml                  # Updated to include lyme_model
```

---

## 2. The Lyme Model Thesis

### Core Statement

**A small local model (3-8B parameters, quantized to 4-6 bits, running on consumer GPU/CPU) can approach the coding-agent quality of frontier cloud models (Claude, Codex, OpenCode) when amplified by a purpose-built local runtime that applies: compression, multi-level retrieval, speculative decoding, hardware-aware scheduling, and tool-use optimization - and this proposition can be proven or disproven using Lyme Audit as the measurement instrument.**

### Sub-Hypotheses

**H1 - Compression Parity.** A 7B model with Lyme's compression pipeline (L1-L5) matches a stateless 70B model on multi-file editing tasks. Byte-for-byte context is not comprehension; compressed context is.

**H2 - Amplification Over Scale.** A 3B model with full amplification stack (compression + memory + speculative decoding + tool optimization) matches an 8B model with none of those. Architecture beats parameters.

**H3 - Quantization Efficiency.** 4-bit quantization loses <=5% task accuracy while enabling 3x larger effective context on the same VRAM. The optimal quantization point is lower than the field assumes.

**H4 - Speculative Decoding for Coding.** Coding tokens are more predictable (structured syntax, API patterns) than natural language, making speculative decoding 2-3x more effective on code. A small draft model + target model pair can nearly double throughput.

**H5 - Hardware Awareness > Raw Throughput.** A scheduler that understands GPU/CPU/VRAM topology and can dynamically shift computation (prompt processing on GPU, generation hybrid GPU/CPU, retrieval on CPU) outperforms fixed-config deployments by 40%+ on latency P99.

**H6 - Fewer Tools, Better Used.** Small models degrade sharply with large tool surfaces. Optimizing tool selection (fewer tools, better descriptions, cached schemas) recovers 15-25% task accuracy vs. naive tool-use for sub-8B models.

**H7 - Local Parity Is Measurable.** On a defined set of 40 real-codebench tasks (multi-file editing, bug fixing, refactoring, test generation, repo-wide analysis), a 7B model with the full Lyme Model stack achieves >=80% of Claude Sonnet task-completion rate at <5% of the per-task cost.

### What We Are Not Building In Lyme Model

- **Not a foundation model.** We select, quantize, and amplify existing open models.
- **Not a cloud service.** This runs on consumer hardware (RTX 3060+ or M-series Mac).
- **Not a general-purpose LLM.** Coding-agent-specific (tool use, file editing, repo understanding).
- **Not a replacement for Lyme Audit.** Audit measures Model; Model uses Audit as library.

---

## 3. Model/Runtime Architecture

### Layered Architecture

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
|  +------v------+    +------v------+    +------v------+    |
|  | GPU         |    | CPU         |    | Hybrid      |    |
|  | Sched.      |    | Sched.      |    | Sched.      |    |
|  +------+------+    +------+------+    +------+------+    |
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

### Layer Details

#### Layer 1 - Model Store

Purpose: Manage quantized model files, adapters, and metadata.

```
ModelStore
  register(path, metadata)         # Add a GGUF/safetensors model
  select(constraints)              # Pick best model for hardware
    budget VRAM
    min quality threshold
    task type (code, chat, tool-use)
  quantize(model_id, bits)         # On-device quantization
  adapter_load(model_id, task)     # LoRA/QLoRA adapter
  profile(model_id)                # Benchmark: t/s, VRAM, perplexity
  cache(model_id)                  # Keep hot models in memory
```

Metadata tracked per model:
- Base model name + version
- Quantization format (GGUF type, AWQ, GPTQ)
- Bits per weight
- Effective context length
- Per-task quality scores (from Audit evaluation)
- VRAM footprint at various context lengths
- Tokens/second on target hardware
- Optimal batch size

#### Layer 2 - Hardware Abstraction

Purpose: Detect available hardware and make optimal allocation decisions.

```
HardwareAbstraction
  detect()                         # GPU model, VRAM, CPU cores, RAM
  topology()                       # PCIe layout, NUMA nodes
  vram_budget(context_len)         # Available VRAM after OS
  device_select(model_size)        # GPU only, CPU only, hybrid
  memory_map()                     # What is where right now
  thermal_throttle()               # Check if cooling limited
```

Key outputs:
- `optimal_device_map` - Which layers go where for hybrid inference
- `max_context_length` - Based on VRAM - model size - KV cache per token
- `batch_strategy` - Single vs. dynamic batching for throughput
- `offload_plan` - Which layers stay on GPU under VRAM pressure

#### Layer 3 - Inference Engine

Purpose: Generate tokens efficiently. This is the core tight loop.

```
InferenceEngine
  load(model_id, quant, device_map)
  generate(prompt, params)         # Main generation call
    prompt_process()               # Prefill (amortized)
    speculative_decode()           # Draft to target verification
    stream_tokens()                # Token-by-token streaming
    stop_condition()               # EOS, tool call, max tokens
  kv_cache_manage()                # PagedAttention, eviction
  batch_generate(requests)         # Dynamic batching
  profile()                        # Real-time token speed
```

Speculative decoding sub-layer:

```
SpeculativeDecode
  draft_model                      # Small model (0.5-1.5B)
  target_model                     # Main model (3-8B)
  draft(prefix)                    # Fast forward K tokens
  verify(draft, target)            # Parallel verification
  acceptance_rate()                # Track per-session
  adapt_k()                        # Dynamic K selection
  rollback()                       # On rejection
```

Key optimizations for code:
- Code tokens have higher acceptance rates (predictable syntax)
- Structural tokens (braces, parens, newlines) are nearly deterministic
- Comments and strings have lower acceptance - fall back to target
- Dynamic K: start K=5, increase on consecutive accepts, decrease on rejects

#### Layer 4 - Model Amplification

Purpose: Make the small model perform as if it were larger. The force multipliers.

```
AmplificationLayer
  context_assembly(task, repo_state)
    compression_load(L1-L5)        # From Lyme Audit compression/
    retrieval_fuse()               # Multi-source retrieval
    priority_sort()                # Most important content first
    budget_fit()                   # Truncate to fit context

  prompt_optimization()
    template_select(task)
    instruction_compress()         # Shorter instructions, same meaning
    example_prune()                # Fewer examples, better ones
    tool_describe()                # Minimized tool descriptions

  tool_minimization(tool_set)
    filter_relevant()              # Only tools for this task
    schema_cache()                 # Pre-compiled tool schemas
    alias_common()                 # Short names for frequent tools
    fallback_chain()              # If tool fails, simpler alternative

  retrieval_fusion()
    bm25_retrieve(query)
    embedding_retrieve(query)
    structure_retrieve(query)      # From compression L3 subsystem map
    fuse_results()                 # Reciprocal rank fusion
    context_window_fit()          # Truncate to fit remaining budget

  memory_integration()
    episodic_recall(session)       # Past session patterns
    procedural_recall(task)        # How to do this task type
    semantic_recall(domain)        # Codebase knowledge
```

Key insight: amplification is not stacking features - it is a coordinated system where each component adjusts to the others. If retrieval quality is high, compression can be more aggressive. If speculative decoding yields high throughput, more budget can go to retrieval depth. The components co-optimize.

#### Layer 5 - Agent Loop

Purpose: The outer loop that turns generation into action.

```
AgentLoop
  run(task, context)
    plan()                         # Task decomposition
    think()                        # Reasoning step (if model supports)
    act()                          # Tool call or generation
      tool_dispatch()
      tool_result_process()
      error_recover()
    observe()                      # Incorporate tool result
    loop_condition()              # Continue? Done? Failed?

  stream_output()
    token_stream()                 # Real-time token display
    progress_indicator()           # "Planning..." / "Editing..."
    cancel_handler()               # User interrupt

  error_recovery()
    detect_failure()               # No progress, loops, empty output
    fallback_strategy()            # Simpler tool, different approach
    retry_limit()                  # Configurable max retries

  state_management()
    session_state()                # Current turn state
    context_append()               # New observations
    checkpoint()                   # For recovery
```

The agent loop is optimized for small models:
- Fewer reasoning steps (small models degrade with long chains)
- More structured outputs (JSON mode, constrained decoding)
- Shorter tool descriptions, fewer choices per turn
- Aggressive error recovery (small models make more errors)
- Predictable failure modes (learned from Audit anomaly detection)

### Data Flow Through the Stack

```
User Task
    |
    v
Agent Loop (L5)
    |
    +--> Plan: decompose task
    |       |
    |       v
    |   Amplification Layer (L4)
    |       +--> Load compression (Audit L1-L5)
    |       +--> Retrieve (BM25 + embedding + structure)
    |       +--> Fuse results
    |       +--> Fit to context budget
    |       +--> Build prompt (optimized for small model)
    |               |
    |               v
    |       Inference Engine (L3)
    |           +--> Prompt process (GPU prefill)
    |           +--> Speculative decode (draft to verify)
    |           +--> Stream tokens
    |           +--> Emit structured output or tool call
    |                   |
    |                   v
    |           Model does tool call
    |                   |
    |                   v
    |           Execute tool -> observe result
    |                   |
    +-------------------+
    Continue loop or return result
```

### CLI Interface

```bash
# Run a coding task
lyme model run "Add error handling to auth module"
lyme model run --task-type bugfix --file src/auth.py

# Interactive session
lyme model session          # Like Claude Code / OpenCode

# Model management
lyme model list             # Available models
lyme model pull qwen2.5-coder:7b
lyme model quantize qwen2.5-coder:7b --bits 4
lyme model profile qwen2.5-coder:7b:Q4_K_M

# Evaluation (runs through Audit benchmark engine)
lyme model eval             # Full benchmark suite
lyme model eval --scenario multi-file-edit
lyme model eval --compare claude-sonnet  # Reference run

# Hardware info
lyme model hardware         # Detection + recommendations
```

---

## 4. Reused Lyme Audit Systems

Lyme Model stands on Lyme Audit's shoulders. Nothing below is duplicated - these are direct imports, used as libraries, not forks.

### 4.1 Compression Pipeline (`src/lyme/compression/`)

**What:** L1 (tree) -> L2 (APIs) -> L3 (subsystems) -> L4 (invariants) -> L5 (rehydration)

**How Lyme Model uses it:**
- L1-L3 loaded at session start to build structural understanding of the repo
- L4 (invariants) injected into tool-use context - "this repo expects X"
- L5 (rehydration) called on demand when a specific file's detail is needed
- The compressor sits inside the Amplification Layer (L4 of Model stack)

**Why reuse:** This is the single most important force multiplier. A 7B model with compressed context beats a 70B model raw. Building it again would be wasteful; the existing pipeline was designed for exactly this.

### 4.2 Memory Store (`src/lyme/memory/`)

**What:** Three-type persistent memory (procedural, episodic, semantic) with search and distillation.

**How Lyme Model uses it:**
- **Episodic:** Past session traces -> model learns from mistakes across sessions
- **Procedural:** Task recipes -> "here is how we fixed this type of bug before"
- **Semantic:** Codebase knowledge -> "this module's invariants are X"

**Why reuse:** Memory IS the persistent-cognition argument of the Manifesto. Lyme Model running without memory is just another stateless model. The existing MemoryStore is mature and already handles search and distillation.

### 4.3 Benchmark Engine (`src/lyme/benchmark/`)

**What:** ScenarioRegistry, BenchmarkEngine, BenchmarkScenario, runner.

**How Lyme Model uses it:**
- Primary evaluation harness for all experiments
- `lyme model eval` wraps Audit's benchmark engine
- Scenario registry provides the task suite for measuring progress
- Every model release gets a benchmark score (tracked longitudinally)

**Why reuse:** The benchmark engine IS the measurement instrument. Building another would create an unforced inconsistency between "what Audit measures" and "what Model reports."

### 4.4 Telemetry Substrate (`src/lyme/telemetry/`)

**What:** Tracer, EventLog, MetricsStore, Span, Timeline.

**How Lyme Model uses it:**
- Every generation emits a trace (prompt -> tokens -> tool calls -> results)
- Every agent-loop step emits spans with timing and token counts
- Metrics counters: tokens/sec, cache hit rate, speculative acceptance rate
- All Model telemetry shares the same format as Audit telemetry

**Why reuse:** A single trace format means Model performance data can be compared against any other agent Audit has ever measured. Cross-system comparability is the whole point.

### 4.5 Cognitive Tracing (`src/lyme/cognition/`)

**What:** TraceCompressor, ThoughtAnalyzer, AnomalyDetector, CognitiveRecorder.

**How Lyme Model uses it:**
- Runtime anomaly detection -> "model is looping, triggering recovery"
- Thought analysis on generation traces -> "where did this model go wrong?"
- Trace compression -> storing session traces efficiently

**Why reuse:** The anomaly detector was trained on general agent failures. Lyme Model inherits that classifier. Over time, Model-specific failure patterns will be added, but the infrastructure is shared.

### 4.6 Replay System (`src/lyme/replay/`)

**What:** DeterministicReplayer, DiffReplayer.

**How Lyme Model uses it:**
- Session replay for debugging model behavior
- Regression testing: "did this model change break anything?"
- Deterministic replay with same seed -> compare model versions

**Why reuse:** Replay is essential for debugging small-model failures (which will be frequent). The existing system handles this correctly.

### 4.7 Capability Matrix (`src/lyme/models/`)

**What:** CapabilityMatrix, ModelEvaluator.

**How Lyme Model uses it:**
- Profile new quantizations against standard tasks
- Track capability curves as models shrink (3B -> 1.5B -> 0.5B quantized)
- Identify capability cliffs - tasks that collapse below a certain size

**Why reuse:** This is the living map of what different model sizes can do. Lyme Model's quantization and model-selection decisions are driven by this matrix.

### 4.8 Evaluation Framework (`src/lyme/evaluation/`)

**What:** SelfBenchmark, LongitudinalEvaluation, CognitionRegression.

**How Lyme Model uses it:**
- Track Model performance week over week
- Detect regression when changing quantization or amplification strategy
- Generate leaderboard

**Why reuse:** The longitudinal evaluator already tracks performance over time. Lyme Model is the subject.

---

## 5. New Lyme Model Modules

These are built from scratch. Not copied from Audit. Not adapted.

### 5.1 `src/lyme_model/runtime/` - Inference Engine

The core token-generation loop. This is the tightest code in the project.

```
runtime/
  engine.py              # InferenceEngine: load, generate, stream
  loader.py              # ModelLoader: GGUF, safetensors, adapter
  kv_cache.py            # PagedAttention-style KV cache manager
  stream.py              # Token stream handler + stop conditions
  config.py              # Generation parameters (temp, top_p, etc.)
  errors.py              # Inference-specific errors
```

**Backend strategy:** Wrap llama.cpp (via ctypes or llama-cpp-python) as the primary backend. Support MLX on Apple Silicon. Add an OpenAI-compatible adapter for cloud model comparison runs.

**Not building:** A new inference framework. We use llama.cpp, MLX, and OpenAI-compatible APIs. The engine is a thin orchestrator on top.

### 5.2 `src/lyme_model/amplify/` - Amplification Layer

The force-multiplier layer. This is where Lyme Model wins or loses.

```
amplify/
  assembler.py           # ContextAssembler: compression + retrieval + memory
  optimizer.py           # PromptOptimizer: instruction compression
  tool_min.py            # ToolMinimizer: tool selection + schema cache
  retrieval.py           # RetrievalFusion: BM25 + embedding + structure
  budget.py              # ContextBudget: fit content to window
  integration.py         # L0: coordinates all amplification strategies
```

This is the **most important new module.** It holds the thesis. The amplification layer's job: make every token that reaches the model count. No filler. No redundancy. No wasted context.

### 5.3 `src/lyme_model/decode/` - Speculative Decoding

```
decode/
  speculative.py         # SpeculativeDecode: draft -> verify
  draft.py               # Draft model manager (small companion models)
  verify.py              # Parallel verification logic
  schedule.py            # Dynamic K selection
  code_accel.py          # Code-specific optimizations
  metrics.py             # Acceptance rate, speedup tracking
```

### 5.4 `src/lyme_model/quant/` - Quantization Management

```
quant/
  manager.py             # QuantManager: quantization lifecycle
  selector.py            # QuantSelector: pick best quant for hardware
  profile.py             # Benchmark each quant: quality + speed + VRAM
  convert.py             # On-device quantization (via llama.cpp, AutoGPTQ)
  registry.py            # Known working quantizations per model
```

### 5.5 `src/lyme_model/tools/` - Tool-Use Optimization

```
tools/
  optimizer.py           # ToolOptimizer: reduce, deduplicate, describe
  schemas.py             # Schema caching + compression
  dispatch.py            # Tool execution + result formatting
  fallback.py            # Fallback chain when tool fails
  registry.py            # Available tools with metadata + success rates
```

### 5.6 `src/lyme_model/hardware/` - Hardware-Aware Scheduling

```
hardware/
  detector.py            # GPU/CPU/VRAM/RAM detection
  scheduler.py           # Dynamic device allocation
  topology.py            # PCIe, NUMA, shared memory topology
  budget.py              # VRAM budgeting for model + KV cache
  monitor.py             # Runtime hardware monitoring
```

### 5.7 `src/lyme_model/context/` - Context Management

Manages the model's context window for local inference.

```
context/
  window.py              # ContextWindow: sliding window management
  eviction.py            # Smart eviction (not FIFO)
  compression.py         # On-the-fly context compression
  summary.py             # Rolling summary for long sessions
  budget.py              # Token budget allocation per turn
```

### 5.8 `src/lyme_model/distill/` - Distillation & Fine-Tuning Pipeline

```
distill/
  distill.py             # Distillation pipeline (teacher -> student)
  finetune.py            # Fine-tuning orchestration (LoRA/QLoRA)
  data.py                # Training data curation (from Audit traces)
  eval.py                # Post-training evaluation (via Audit)
  curriculum.py          # Curriculum learning schedule
```

### 5.9 `src/lyme_model/serve/` - Local Model Serving

```
serve/
  server.py              # Local API server (OpenAI-compatible)
  batcher.py             # Dynamic batching for throughput
  cache.py               # Response cache (exact + semantic)
  health.py              # Health checks + metrics
```

### 5.10 `src/lyme_model/eval/` - Model-Specific Evaluation

```
eval/
  harness.py             # Evaluation harness (wraps Audit benchmark engine)
  suite.py               # Model-specific task suite (40 tasks)
  compare.py             # Comparison: Model vs. Claude/Codex/OpenCode
  regression.py          # Detect regression across model versions
  leaderboard.py         # Local leaderboard
```

### 5.11 `src/lyme_model/cli.py` - Model CLI

```
lyme model run          # Execute a task
lyme model session      # Interactive session
lyme model list         # Available models
lyme model pull         # Download a model
lyme model quantize     # Quantize a model
lyme model profile      # Profile model performance
lyme model eval         # Evaluate model on benchmark
lyme model hardware     # Hardware detection
lyme model serve        # Start local API server
```

### Module Size Estimates

| Module | Est. LOC | Complexity | Priority |
|--------|----------|------------|----------|
| runtime/ | 1500 | High | P0 - MVP |
| amplify/ | 2000 | High | P0 - MVP |
| decode/ | 800 | Medium | P1 |
| quant/ | 600 | Medium | P0 - MVP |
| tools/ | 500 | Medium | P0 - MVP |
| hardware/ | 400 | Medium | P1 |
| context/ | 600 | Medium | P0 - MVP |
| distill/ | 1200 | High | P2 |
| serve/ | 300 | Low | P2 |
| eval/ | 400 | Low | P0 - MVP |
| cli.py | 300 | Low | P0 - MVP |

**Total estimated: ~8600 LOC** for full implementation.

---

## 6. First Empirical Experiment

### Experiment 1: Compression Parity

**What is the smallest model that, when given compressed context (L1-L4), can match a 7B model with raw file context on a multi-file editing task?**

#### Design

| Aspect | Detail |
|--------|--------|
| **Hypothesis** | H1: 3B + compression = 7B raw |
| **Independent variable** | Model size (3B, 7B) x context type (raw, compressed) |
| **Conditions** | 4 cells: 3B-raw, 3B-compressed, 7B-raw, 7B-compressed |
| **Task** | Multi-file edit: add error handling across 3 files in an unfamiliar codebase |
| **Scenario** | From Audit's scenario registry -- a 3000-file real-world repo |
| **n per cell** | 10 runs (total 40 runs) |
| **Metrics** | Task completion (pass/fail), edit accuracy, hallucinated references, context tokens consumed, wall-clock time |
| **Models** | Qwen2.5-Coder-3B Q4_K_M, Qwen2.5-Coder-7B Q4_K_M |
| **Backend** | llama.cpp via runtime/engine.py |
| **Hardware** | RTX 3090 (24GB VRAM) |
| **Measurement** | Through Audit benchmark/engine + telemetry/tracer |

#### Expected Result

If the thesis is correct: 3B-compressed ~= 7B-raw (within 5% task completion), while consuming 60% fewer total tokens (less context + smaller model).

#### What We Learn

- If true -> compression IS a viable path to local parity. Validate the full amplification stack approach.
- If false -> compression alone is insufficient. Need retrieval or memory or better models. Shift research direction.

### Preparation Required

1. Implement `runtime/engine.py` (llama.cpp backend)
2. Implement `amplify/assembler.py` (compression integration with Audit)
3. Implement `eval/harness.py` (wrap Audit benchmark engine)
4. Write the multi-file-edit scenario if none exists in Audit

---

## 7. MVP Definition

### Lyme Model MVP - Capable of Running a Real Coding Task Locally

The MVP is the smallest vertical slice that proves the concept works end to end. It must be able to accept a task, understand a repo, generate code, and pass Audit's evaluation - all on consumer hardware.

### MVP Scope

| Component | MVP | Post-MVP |
|-----------|-----|----------|
| **runtime/** | llama.cpp backend, single model, basic generation | Speculative decoding, dynamic batching |
| **amplify/** | Compression integration (L1-L4), basic retrieval (BM25) | Multi-source fusion, memory integration |
| **quant/** | Manual model selection, one quantization tier | Auto-selection, on-device quantization |
| **tools/** | 3 core tools (read file, edit file, run command) | Full tool registry, optimization |
| **context/** | Fixed-size context, FIFO eviction | Smart eviction, rolling summary |
| **decode/** | None - single model generation | Speculative decoding |
| **hardware/** | Static detection, GPU-only | Hybrid scheduling |
| **distill/** | None | Full pipeline |
| **serve/** | None | API server |
| **eval/** | Single-task harness, manual compare | Full suite, automated leaderboard |
| **cli/** | `lyme model run`, `lyme model eval` | Full subcommand set |

### MVP Deliverables

1. **Working inference.** Load a Q4 7B model via llama.cpp, generate code tokens on a consumer GPU, stream output to terminal.

2. **Compressed context.** Integrate Audit's compression pipeline. Before every task, build L1-L4, inject into model context. No raw file reads.

3. **Three tools.** `read_file`, `edit_file`, `run_command` - the minimum set for any coding task. Optimized schema descriptions for small models.

4. **Single-task harness.** `lyme model eval --scenario <name>` runs one benchmark scenario through Audit, captures trace, reports score.

5. **Compression Parity experiment.** Run Experiment 1 (Section 6) to validate or invalidate the core thesis. Result documented in `docs/LYME_MODEL_EXPERIMENTS.md`.

6. **CLI entry point.** `lyme model run <task>` works end to end.

### MVP Not Included

- Speculative decoding
- Fine-tuning or distillation
- Hardware-aware hybrid scheduling
- Multi-session memory (procedural/episodic reuse)
- Interactive session mode
- Multi-model routing
- API server

### MVP Success Criteria

- Task completion rate >= 60% of Claude Sonnet on the chosen scenario
- End-to-end latency <= 30s for a multi-file edit task
- All runs produce valid Audit traces (captured, stored, replayable)
- Compression pipeline reduces context tokens >= 60% vs. raw file content
- Runs on RTX 3060 12GB or Apple M2 Pro
- No cloud API calls - every token generated locally

### Estimated MVP Timeline: 6-8 weeks

| Week | Focus |
|------|-------|
| 1-2 | `runtime/engine.py` + llama.cpp integration + model loading |
| 3-4 | `amplify/assembler.py` + compression integration + BM25 retrieval |
| 5 | `tools/` core set + `context/` basic management |
| 6 | `eval/harness.py` + `cli.py` -- end-to-end flow |
| 7-8 | Experiment 1 execution + analysis + documentation |

---

## 8. Year Two Roadmap (Lyme Model Only)

This roadmap is exclusive to Lyme Model. Lyme Audit continues on its own trajectory (v0.3, v0.4, etc. release plans) independently.

### Q1 - Amplification Fundamentals

**Theme:** Make the baseline work well. Validate the core thesis.

- **Experiment 1** (Compression Parity) - Gate decision on full investment. If compression parity fails, pivot to retrieval-heavy approach.
- **Multi-turn context management** - Sliding window + smart eviction for sessions >5 turns. Without this, small models lose track.
- **Tool-use optimization** - Systematically find the minimum viable tool set. Measure accuracy improvement per tool added -> find diminishing returns.
- **5-scenario benchmark suite** - Multi-file edit, bug fix, refactor, test generation, repo analysis. All via Audit benchmark engine.

**Gate check at end of Q1:** Does 3B + compression approach 7B raw? If yes -> full speed ahead. If no -> shift budget to retrieval and fine-tuning.

### Q2 - Speculative Decoding & Throughput

**Theme:** Speed without quality loss.

- **Speculative decoding** - Implement draft->target pair. Measure acceptance rates for code tokens. Characterize where speculative decoding helps vs. hurts (code vs. comments vs. planning tokens).
- **Dynamic K** - Let acceptance rate drive draft length. Track per session.
- **KV cache optimization** - PagedAttention-style management. Measure VRAM savings at various context lengths.
- **Batch inference** - Dynamic batching for parallel tool calls or eval workloads.
- **Experiment 2:** Speculative decoding throughput. Measure: tokens/second, latency P50/P95/P99, VRAM overhead, quality impact.

### Q3 - Multi-Model & Hardware Awareness

**Theme:** Optimal allocation across heterogeneous hardware.

- **Hardware detection + topology mapping** - GPU model, VRAM, CPU cores, shared memory, PCIe topology.
- **Hybrid inference** - Prompt processing on GPU, generation split across GPU/CPU when VRAM is constrained.
- **Model routing** - Route simple tasks (lint fix, import sort) to a tiny model (0.5-1.5B), complex tasks (architecture change) to the large model (7-8B). Measure: average latency, quality, cost.
- **VRAM budgeting** - Dynamic model + KV cache allocation. If context grows, shrink quantization or offload layers.
- **Experiment 3:** Multi-model routing. Show 2x throughput at 90% of large-model-only quality.

### Q4 - Distillation & Memory Integration

**Theme:** Make small models better through training and persistence.

- **Distillation pipeline** - Use Audit traces as training data. Teacher: Claude/Codex/OpenCode. Student: 1.5-3B model. Distill task-specific capabilities (tool calling, file editing, bug detection).
- **Persistent memory integration** - Procedural (how to do tasks), episodic (past sessions), semantic (codebase knowledge). Close the loop: each session feeds the next.
- **Fine-tuning experiments** - QLoRA on distilled data. Measure: do 500 distilled examples match 10K raw examples?
- **Experiment 4:** Distillation efficiency. Measure: teacher-comparable quality at 10x fewer parameters. Target: 3B distilled = 7B raw on benchmark suite.

### Year Two Success Criteria

- 3B distilled model achieves >=80% Claude Sonnet quality on 40-task suite
- End-to-end latency <15s for 90% of tasks
- Runs on RTX 3060 (12GB) and M2 Pro (16GB unified)
- 100% local, zero cloud API calls
- All evaluation data published through Audit's research portal
- Published experiment results in `docs/LYME_MODEL_EXPERIMENTS.md`

### Year Two Resource Estimate

| Activity | Person-weeks |
|----------|-------------|
| Speculative decoding | 4 |
| Context management | 3 |
| Tool optimization | 2 |
| Hardware scheduling | 3 |
| Multi-model routing | 4 |
| Distillation pipeline | 6 |
| Memory integration | 3 |
| Experiments + analysis | 4 |
| Evaluation suite | 2 |
| **Total** | **~31 weeks** |

---

## 9. Lyme Audit as Lab Instrument

### The Core Relationship

Lyme Audit is the microscope. Lyme Model is the specimen.

Without Audit, Model has no evidence. Without Model, Audit has no purpose beyond observing third-party agents. Together they form a closed loop:

```
Audit measures  --->  Model improves  --->  Audit verifies
      ^                                       |
      +---------------------------------------+
```

### What Audit Measures For Model

#### Per-Turn Metrics

- **Task completion rate** - Did the generated code pass tests?
- **Token efficiency** - How many tokens to complete the task?
- **Context utilization** - What percentage of context was actually attended to?
- **Hallucination rate** - Functions, files, or APIs that don't exist
- **Tool accuracy** - Correct tool selection, correct parameters
- **Recovery success** - After error, did model recover or compound?
- **Latency** - Time to first token, total task time, streaming latency
- **Speculative acceptance** - For speculative decoding: acceptance rate by token type (code, comment, whitespace, natural language)

#### Longitudinal Metrics

- **Quality trend** - Is Model getting better over successive releases?
- **Regression detection** - Did a quantization change break something?
- **Capability curves** - How does quality change with model size? (Which tasks collapse first as models shrink?)
- **Quantization cliffs** - At what bit-width does each task fail?
- **Memory utilization** - Is persistent memory actually improving performance over time?

#### Comparative Metrics

- **Model vs. Claude** - Same scenario, same benchmark, same trace format
- **Model vs. Codex** - Cost comparison: tokens x hardware depreciation
- **Model vs. OpenCode** - Latency comparison: local vs. API
- **Model vs. itself (last version)** - Every release is benchmarked against prior releases to detect regression

### Audit as Gatekeeper

Before any Lyme Model release, Audit must validate:

1. **No regression** - All previously passing scenarios still pass
2. **No hallucination increase** - Hallucination rate within noise
3. **Latency bound** - P99 latency under threshold
4. **Reproducible** - Same model + seed = same result (within temperature)
5. **Comparable** - Against cloud baseline for the same scenario

If any check fails, the release is blocked. Audit has veto power over Model releases. This prevents the classic trap: "it feels better" without evidence.

### The Research Loop

```
+-------------------------------------------------------------+
|                    THE LYME RESEARCH LOOP                     |
|                                                             |
|  +--------------+    +--------------+    +--------------+  |
|  | LYME AUDIT   |    | LYME MODEL   |    | LYME AUDIT   |  |
|  | identifies a |--->| implements a |--->| evaluates    |  |
|  | weakness     |    | fix          |    | the fix      |  |
|  +--------------+    +--------------+    +------+-------+  |
|                                                  |          |
|                     +----------------------------+          |
|                     v                                      |
|              +--------------+                              |
|              | Result added |                              |
|              | to corpus,   |                              |
|              | leaderboard, |                              |
|              | experiment   |                              |
|              | log          |                              |
|              +--------------+                              |
+-------------------------------------------------------------+
```

Examples of this loop in practice:

1. **Audit detects** that Model hallucinates imports from non-existent packages -> Model adds retrieval for `requirements.txt` / `pyproject.toml` -> Audit verifies hallucination rate drops.

2. **Audit measures** that Model's tool-call accuracy drops after turn 8 -> Model's context management adds smart eviction -> Audit verifies tool accuracy is stable across 20-turn sessions.

3. **Audit profiles** Model on a Mac M2 and finds prompt processing is the bottleneck -> Model implements speculative decoding -> Audit measures 1.8x throughput improvement.

4. **Audit compares** Model's 3B-distilled variant against 7B-raw and finds parity on 8/10 scenarios -> Model publishes distilled version -> Audit adds the result to the research corpus and leaderboard.

### Published Outputs from the Audit-Model Loop

| Output | Produced By | Description |
|--------|-------------|-------------|
| Leaderboard | Audit evaluation/ | Every Model version scored against every scenario |
| Experiment log | Audit research/ | Documented experiments with methodology + results |
| Traces | Audit telemetry/ | Every Model session stored in standardized format |
| Research corpus | Audit research_corpus/ | Anonymized traces for community analysis |
| Regression report | Audit evaluation/ | Automatic detection of quality drops across Model versions |
| Capability matrix | Audit models/ | Updated per-model-quality scores across all task types |
| Benchmark comparison | Audit benchmark/ | Model vs. Claude/Codex/OpenCode on identical scenarios |

### The Veto

Audit can block a Model release. The criteria:

1. Any previously passing scenario drops >10% task completion
2. Hallucination rate increases >50% relative to previous version
3. P99 latency increases >30% without corresponding quality improvement
4. Deterministic replay produces different results for same seed + prompt (indicates instability)

This veto is enforced by the evaluation harness running as a CI gate.

---

## Summary

| Concern | Lyme Audit | Lyme Model |
|---------|------------|------------|
| **Status** | Existing (v0.7.0) | New (design phase) |
| **Location** | `src/lyme/` (untouched) | `src/lyme_model/` |
| **Purpose** | Measure agents | Run agents locally |
| **Key reuse** | N/A (provides it) | Compression, memory, benchmark, telemetry |
| **New code** | Zero | ~8600 LOC total |
| **First action** | Continue existing roadmap | Build MVP: inference + compression + 3 tools + eval |
| **Decision gate** | N/A | End of Q1: Compression Parity experiment |
| **Year 2 target** | v0.3-v0.7 roadmaps | 3B distilled = 80% of Claude Sonnet |
| **Relationship** | Measures Model | Is measured by Audit |
