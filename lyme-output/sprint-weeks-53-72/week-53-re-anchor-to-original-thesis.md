# Week 53 — Re-anchor Lyme to the Original Thesis

**Date:** Start of Year Two
**Action:** Corrected system split: Lyme Audit (lab) + Lyme Model (experiment)

---

## 1. Corrected Thesis

### Original Thesis (Year One)
> Lyme is a research platform for coding agent measurement.
> It provides compression, memory, governance, and tracing infrastructure.
> Local models on consumer hardware, with the right architecture, can become useful coding agents.

### Problem with Original
The thesis was stated but never tested. Infrastructure was built for both measurement AND
intelligence in the same codebase, blurring the boundary. The project built 66 modules of
instrumentation but never ran the experiment the instrumentation was designed for.

### Corrected Thesis (Year Two)
> **A small local model (3-8B parameters, quantized to 4-6 bits, running on consumer
> GPU/CPU) can approach the coding-agent quality of frontier cloud models (Claude, Codex,
> OpenCode) when amplified by a purpose-built local runtime that applies compression,
> multi-level retrieval, speculative decoding, hardware-aware scheduling, and tool-use
> optimization — and this proposition can be proven or disproven using Lyme Audit as the
> measurement instrument.**

### What Changed
| Dimension | Year One | Year Two |
|-----------|----------|----------|
| Scope | Build everything | Build the minimum to test the thesis |
| System boundary | One codebase, ~66 modules | Two systems: Audit (measurement) + Model (intelligence) |
| Claim status | All claims unvalidated | Every claim has an experiment |
| Evidence model | Simulated data presented as findings | Real measurements, published honestly |
| Success criterion | Infrastructure completeness | Empirical validation, even if negative |

---

## 2. System Boundary

### Lyme Audit — The Lab Instrument (untouched, `src/lyme/`)

| Property | Value |
|----------|-------|
| Identity | Measurement platform |
| Core question | "How good is this agent?" |
| Primary user | Researcher |
| Output | Reports, traces, benchmarks, metrics |
| Scope | Generic — any agent, any model |
| Model role | Observes and measures models |
| Evaluation | Runs benchmarks, produces scores |
| Data | Traces, comparisons, research corpora |
| Persistence | Memory store, audit logs, research corpus |

### Lyme Model — The Experiment (`src/lyme_model/`, new)

| Property | Value |
|----------|-------|
| Identity | Local intelligence system |
| Core question | "How do we make local models better?" |
| Primary user | Developer / end-user |
| Output | Code edits, completions, analysis, actions |
| Scope | Specific — Lyme's own model/runtime |
| Model role | IS the model/runtime |
| Evaluation | IS what gets benchmarked |
| Data | Inference state, context, generations |
| Persistence | KV cache, quantization state, adapter weights |

### Communication Protocol

```
+-----------------------+       +-----------------------+
|     LYME AUDIT        |       |     LYME MODEL        |
|  (src/lyme/)          |       |  (src/lyme_model/)    |
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

Lyme Model generates traces, metrics, and state.
Lyme Audit reads them: evaluates, compares, stores, analyzes.
Lyme Model imports Audit utilities (compression, memory) as libraries.
Audit never imports Model — it remains model-agnostic.
Audit has veto power over Model releases.

---

## 3. Module Map

### File System Layout

```
src/
  lyme/                         <-- LYME AUDIT (untouched, 66 modules)
    cli.py
    audit.py
    benchmark/
    memory/
    compression/
    cognition/
    replay/
    telemetry/
    governance/
    verification/
    graph/
    discovery/
    ...
    (ALL PRESERVED)

  lyme_model/                   <-- LYME MODEL (new, to be built)
    __init__.py
    cli.py                      # lyme model ... subcommands
    config.py                   # Model-specific configuration
    runtime/                    # Core inference engine + agent loop
    amplify/                    # Small-model force multipliers
    quant/                      # Quantization selection + management
    decode/                     # Speculative decoding
    tools/                      # Tool-use optimization for small models
    hardware/                   # Hardware-aware scheduling
    context/                    # Context management for local models
    distill/                    # Fine-tuning / distillation pipeline
    serve/                      # Local model serving
    eval/                       # Model-specific evaluation harness
```

### What Exists Already That Supports This Split

| File | Status |
|------|--------|
| `docs/LYME_MODEL_DESIGN.md` | Already written (1020 lines) — covers boundary, thesis, architecture, roadmap |
| `docs/LYME_MODEL_EXPERIMENTS.md` | Already written (35 lines) — living experiment log, first experiment defined |
| `src/lyme/audit.py` | Already exists (327 lines) — AuditEntry, AuditTrail, AuditReport |
| Release plans v0.1-v0.7 | Already exist — Audit's own roadmap continues independently |

---

## 4. Existing Modules Lyme Model Should Reuse

| Audit Module | What Model Uses It For | How |
|-------------|----------------------|-----|
| `compression/` | Pre-build compressed context for small models (L1-L5) | Import as library in amplify/ layer |
| `memory/` | Persistent procedural/episodic/semantic store | Import as library for context/ layer |
| `benchmark/` | Primary evaluation harness, scenario registry | Wrap in eval/ harness |
| `telemetry/` | Trace emission, metric recording, span tracking | Import in runtime/ for instrumentation |
| `cognition/` | Runtime anomaly detection, thought analysis | Import for error recovery |
| `replay/` | Session replay for debugging | Import for debugging tools |
| `models/` | Capability matrix for quantization decisions | Import for quant/ selection |
| `evaluation/` | Longitudinal tracking, regression detection | Import for eval/ suite |

---

## 5. New Modules Needed

| Module | Est. LOC | Priority | Description |
|--------|----------|----------|-------------|
| `runtime/` | 1500 | P0 - MVP | Inference engine: load, generate, stream |
| `amplify/` | 2000 | P0 - MVP | Context assembly, retrieval fusion, prompt optimization |
| `quant/` | 600 | P0 - MVP | Quantization management and selection |
| `tools/` | 500 | P0 - MVP | Tool-use optimization for small models |
| `context/` | 600 | P0 - MVP | Context window management for local inference |
| `eval/` | 400 | P0 - MVP | Model-specific evaluation harness |
| `cli.py` | 300 | P0 - MVP | `lyme model` subcommands |
| `decode/` | 800 | P1 | Speculative decoding |
| `hardware/` | 400 | P1 | Hardware-aware scheduling |
| `distill/` | 1200 | P2 | Distillation and fine-tuning pipeline |
| `serve/` | 300 | P2 | Local API server |
| **Total** | **~8600** | | |

---

## 6. Claims That Must Be Empirically Tested First

### Tier 1 — Gates further investment (must test first)

| Claim | Experiment | Week |
|-------|-----------|------|
| H1 - Compression Parity: 3B + compressed context = 7B raw context | Week 57 | Week 57 |
| Local models can complete coding tasks on consumer hardware at all | Week 56 | Week 56 |
| H3 - Quantization Efficiency: 4-bit loses <=5% accuracy | Week 61 | Week 61 |

### Tier 2 — Important for architecture decisions

| Claim | Experiment | Week |
|-------|-----------|------|
| H2 - Amplification Over Scale: architecture beats parameters | Week 57-58 | Week 57-58 |
| H6 - Fewer Tools, Better Used: optimized tool sets recover accuracy | Week 59 | Week 59 |
| H4 - Speculative Decoding for Code: coding tokens are more predictable | Week 62 | Week 62 |

### Tier 3 — Nice to have, dependent on earlier results

| Claim | Experiment | Week |
|-------|-----------|------|
| H5 - Hardware Awareness > Raw Throughput: dynamic scheduling wins | Week 63, 69 | Week 63, 69 |
| H7 - Local Parity Is Measurable: 7B stack >= 80% of Claude Sonnet | Week 68 | Week 68 |
| Fine-tuning/distillation improves small models measurably | Week 66 | Week 66 |

### Decision Gates

| Gate | Condition | Week | Consequence of Failure |
|------|-----------|------|----------------------|
| G1 | Raw local model can complete ANY benchmark task | Week 56 | Abandon or pivot to cloud-based |
| G2 | Lyme compression improves raw model performance | Week 57 | Redesign compression for small models |
| G3 | Quantized model (Q4) loses <= 15% accuracy | Week 61 | Accept lower quality or require more VRAM |
| G4 | Lyme Model stack beats raw model | Week 66 | Re-evaluate architecture approach |

---

## Summary

| Concern | Lyme Audit | Lyme Model |
|---------|------------|------------|
| Status | Existing (v0.7.0) | New (design phase) |
| Location | `src/lyme/` (untouched) | `src/lyme_model/` |
| Purpose | Measure agents | Run agents locally |
| Key reuse | N/A (provides it) | Compression, memory, benchmark, telemetry |
| New code | Zero | ~8600 LOC total |
| First action | Continue existing roadmap | Build hardware profiler (Week 55) |
| Decision gate | N/A | G1: Can local models run at all? |
| Year 2 target | v0.8+ roadmaps | Tested, measured, honest results |
| Relationship | Measures Model | Is measured by Audit |
