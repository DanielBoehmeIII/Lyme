# Lyme — Agent Instructions

**Two-system architecture:** Lyme Audit (measurement) + Lyme Model (intelligence)

## Test Commands

```bash
cd /home/dboehmeiii/Desktop/repos/Lyme
python3 -m pytest tests/ -v
```

## System Split (Year Two)

| System | Location | Purpose | Status |
|--------|----------|---------|--------|
| **Lyme Audit** | `src/lyme/` (66 modules) | Measurement, governance, research | Existing v0.7.0, untouched |
| **Lyme Model** | `src/lyme_model/` (new) | Local model runtime, small-model amplification | Building (Year Two) |

### Invariant
Do NOT remove, delete, replace, or shrink Lyme Audit.
Preserve all existing modules: traces, benchmarks, governance, memory, semantic diffs, replay, telemetry, research reports, audit systems.

Lyme Audit measures. Lyme Model competes. Audit has veto power over Model releases.

## Key Architecture (Lyme Audit)

- **src/lyme/compression/** — Multi-layer codebase compression (L1-L5)
- **src/lyme/memory/** — Persistent procedural/episodic/semantic store
- **src/lyme/benchmark/** — Scenario registry, benchmark engine
- **src/lyme/cognition/** — Cognitive tracing, anomaly detection
- **src/lyme/replay/** — Deterministic and diff replay
- **src/lyme/telemetry/** — Tracing, events, metrics
- **src/lyme/graph/** — Causal software graph analysis
- **src/lyme/discovery/** — Invariant mining and violation detection
- **src/lyme/governance/** — Autonomy policy, review boards
- **src/lyme/verification/** — Verification graphs, gap detection
- **src/lyme/evolution/** — Evolution analysis and mutation
- **src/lyme/cross_repo/** — Cross-repository intelligence
- **src/lyme/ecosystem/** — Ecosystem knowledge graph
- **src/lyme/epistemology/** — Evidence theory, confidence calibration

## Year Two Roadmap

Running in `lyme-output/sprint-weeks-53-72/`. Each week is one unit of work.
Current week tracked in the INDEX.md of that directory.

### Weeks 53-72 Summary

| Week | Focus |
|------|-------|
| 53 | Re-anchor to original thesis (Audit + Model split) |
| 54 | Define Lyme Model architecture |
| 55 | Hardware reality baseline |
| 56 | Local model capability benchmark |
| 57 | Raw 7B vs Lyme-enhanced 7B |
| 58 | Context compression for small models |
| 59 | Tool use as model amplification |
| 60 | Local agent runtime MVP |
| 61 | Quantization study |
| 62 | Speculative decoding / draft model research |
| 63 | Local model routing |
| 64 | Fine-tuning feasibility |
| 65 | Distillation from strong models |
| 66 | Train/adapt first Lyme Model variant |
| 67 | Coding-agent skill dataset |
| 68 | Frontier comparison |
| 69 | Consumer hardware optimization |
| 70 | Reverse engineering / open source feasibility |
| 71 | Lyme Model v0.1 |
| 72 | Year Two first report |

## CLI Commands (Lyme Audit, v0.3+)

| Command | Purpose |
|---------|---------|
| `lyme doctor` | Diagnose repository health |
| `lyme ask` | Evidence-grounded Q&A |
| `lyme diff` | Semantic diff classification |
| `lyme trace` | Execution trace viewer |
| `lyme fix` | Safe, auditable edits |
| `lyme history` | Action audit trail |
| `lyme audit` | Full action inspection |
| `lyme undo` | Reverse actions |
| `lyme memory` | Persistent memory |
| `lyme bench` | Model benchmarking |
| `lyme graph` | Causal graph analysis |
| `lyme discover` | Invariant discovery |
| `lyme run` | Run benchmarks |
| `lyme stress` | Stress experiments |
| `lyme research` | Research framework |
| `lyme self` | Repository self-description |
| `lyme archfile` | Machine-readable architecture |
| `lyme plan` | Architecture-aware planning |
| `lyme skill` | Skill library |
| `lyme cross-repo --dirs repo1 repo2` | Cross-repo pattern mining |
| `lyme ecosystem query --library fastapi` | Ecosystem knowledge query |
| `lyme epistemology assess --claim "..."` | Evidence-grounded claim assessment |
| `lyme epistemology calibrate` | Confidence calibration report |
| `lyme epistemology debug` | Epistemic debugging |
| `lyme policy check` | Autonomy policy evaluation |
| `lyme policy sensitive --path /repo` | Sensitive code detection |
| `lyme policy review --request '{}'` | Action review board |
| `lyme demo-v03` | Full v0.3 demo |

## Lyme Model CLI (building)

| Command | Purpose |
|---------|---------|
| `lyme model run <task>` | Execute a coding task |
| `lyme model session` | Interactive session |
| `lyme model list` | Available models |
| `lyme model pull` | Download a model |
| `lyme model quantize` | Quantize a model |
| `lyme model profile` | Profile model performance |
| `lyme model eval` | Evaluate on benchmark |
| `lyme model hardware` | Hardware detection/recommendation |
| `lyme model serve` | Start local API server |

## Module Conventions

- Dataclasses with `to_dict()` for serialization
- JSON file storage under `.lyme/` and `lyme-output/`
- `__init__.py` exports only public API
- Tests in `tests/` directory with pytest
- Lyme Model modules under `src/lyme_model/` follow same conventions
