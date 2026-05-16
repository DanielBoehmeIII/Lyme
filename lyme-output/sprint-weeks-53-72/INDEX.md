# Year Two: Sprint Weeks 53–72 — LYME MODEL

**Theme:** Lyme Model — local LLM/coding-agent efficiency on consumer hardware.
**Lyme Audit is preserved intact.** Lyme Model is added alongside.

---

## Complete

| Week | Deliverable | Key Result |
|------|-------------|------------|
| **53** | `week-53-re-anchor-to-original-thesis.md` | Corrected thesis, system boundary, module map, AGENTS.md updated |
| **54** | `week-54-define-lyme-model.md` | Architecture design, initial `src/lyme_model/` package |
| **55** | `week-55-hardware-reality-baseline.md` | RTX 4060 8GB profile, 10.4 tok/s baseline, VRAM model feasibility |
| **56** | `week-56-capability-benchmark.md` | 3 models × 6 tasks: llama3 100%, deepseek 83%, gpt-oss 50% |
| **57** | `week-57-raw-vs-Lyme-enhanced.md` | Compression experiment: no benefit on small repos (317 tok) |
| **58** | `week-58-compression-for-small-models.md` | Compression comparison (RAW→LYME→Packet): 82% best, 86% reduction |
| **59** | `week-59-tool-amplification.md` | Tools built but hurt single-turn (-50pp). Need multi-turn loop |
| **60** | `week-60-agent-runtime-mvp.md` | Runtime engine, CLI, eval harness all built and verified |
| **61** | `week-61-quantization-study.md` | Q4 only on 8GB, Q5 borderline, Q8 impossible |
| **62** | `week-62-speculative-decoding.md` | Design: 7B Q4 + 1.5B Q4 feasible, expected 1.6-2.0x speedup |
| **63** | `week-63-local-model-routing.md` | Design: router would save 1.6x, deferred to post-v0.1 |
| **64** | `week-64-fine-tuning-feasibility.md` | QLoRA borderline on 8GB, defer to Year Three |
| **65** | `week-65-distillation-pipeline.md` | Pipeline design, 200-example target, quality filters |
| **66** | `week-66-first-model-variant.md` | Prompt-tuned runtime (no training alternative) |
| **67** | `week-67-skill-dataset.md` | 9 skill categories, 115-example schema |
| **68** | `week-68-frontier-comparison.md` | Lyme Model achieves 80-90% of cloud quality on focused tasks |
| **69** | `week-69-hardware-optimization.md` | Optimized config: 5-6s latency, 12 tok/s, warm model |
| **70** | `week-70-reverse-engineering-feasibility.md` | Source-code RE feasible, binary RE not |
| **71** | `week-71-lyme-model-v0.1.md` | v0.1 release definition, demo flow, known limitations |
| **72** | `week-72-year-two-first-report.md` | Final report: compression helps (+4pp), agent loop needed |

---

## Core Finding

**Lyme architecture improves local models on medium-to-large codebases:**
- +3.6 pp task completion (78.5% → 82.1%)
- 1.6x speedup (27.5s → 17.5s)
- 86% context reduction (2236 → 323 tokens)
- +28.6 pp on bug finding (57.1% → 85.7%)

The improvement is real but modest. The next phase (agent loop, speculative decoding,
distillation) must make it dramatic.

---

## What Was Preserved

All of Lyme Audit `src/lyme/` — zero modules removed, zero modifications.
All 66 modules, all 20+ CLI commands, all release plans v0.1-v0.7 remain intact.

## What Was Built

`src/lyme_model/` — 11 modules:
- `runtime/` — Inference engine, model loader
- `amplify/` — Context assembly, amplification layer
- `tools/` — Registry, dispatcher, fallback
- `hardware/` — Detector, monitor, budget
- `context/` — Window management (stub)
- `decode/` — Speculative decoding (stub)
- `quant/` — Quantization management (stub)
- `distill/` — Distillation pipeline (stub)
- `serve/` — Model serving (stub)
- `eval/` — Evaluation harness
- `cli.py` — CLI entry point
