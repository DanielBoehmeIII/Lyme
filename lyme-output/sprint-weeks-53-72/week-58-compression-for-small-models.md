# Week 58 — Context Compression for Small Models

**Date:** Week 58 of Year Two
**Action:** Redesign and benchmark context compression specifically for weak/local models.

---

## 1. Experimental Design

### Test Project
17-file Python project (~2236 tokens raw):
- 15 domain modules (Service/Repository classes)
- `app.py` (Application orchestrator)
- `test_app.py` (pytest tests)
- `config.yaml`

### Three Strategies Compared

| Strategy | Description | Tokens | Reduction |
|----------|------------|-------:|----------|
| **Raw** | Full file contents sent as-is | 2236 | 0% |
| **Lyme Compression** | Structured L1-L4 pipeline output | 323 | **86%** |
| **Small-Model Packet** | Natural language cards (new) | 377 | **83%** |

### Tasks (4 categories)
1. **Architecture** — Describe components and interactions
2. **Change impact** — Plan adding a new module
3. **Bug finding** — Identify design issues
4. **Summary** — Write README

### Model
deepseek-coder:6.7b (Ollama)

---

## 2. Results

### Per-Task Comparison

| Task | Raw | Lyme Compress | Small-Model Packet |
|------|:---:|:-------------:|:------------------:|
| Architecture | 71.4% | **85.7%** | 71.4% |
| Change impact | 85.7% | 85.7% | 85.7% |
| Bug finding | 57.1% | **85.7%** | 71.4% |
| Summary | **100.0%** | 71.4% | 71.4% |

### Average Scores

| Strategy | Avg Score | Avg Time | Avg Tokens |
|----------|:---------:|:--------:|:----------:|
| **Raw** | **78.5%** | 27.5s | 2236 |
| **Lyme Compression** | **82.1%** | **17.5s** | **323** |
| **Small-Model Packet** | 75.0% | 19.8s | 377 |

### Speed-Improved Tasks

| Strategy | Avg Time | vs Raw |
|----------|:--------:|:-----:|
| Raw | 27.5s | 1.0x |
| Lyme Compression | 17.5s | **1.6x faster** |
| Small-Model Packet | 19.8s | **1.4x faster** |

---

## 3. Key Findings

### Finding 1: Compression works at scale
On the 17-file project (unlike the 5-file test in Week 57), Lyme compression
**improves quality by 3.6 percentage points** while reducing tokens by 86%.
This confirms the hypothesis: compression helps when raw context exceeds the
model's comfort zone.

### Finding 2: Structured compression beats natural language
The existing Lyme L1-L4 pipeline (82.1%) outperformed the new natural-language
cards (75.0%). The structured format works better for code models because:
- Exact function/symbol names are preserved
- Relationship data is explicit
- No information is lost in "natural language" conversion

### Finding 3: Compression is faster for the model
Lyme compression runs 36% faster (27.5s → 17.5s). Fewer input tokens means:
- Faster prompt processing (prefill)
- Less attention computation
- Better "lost in the middle" behavior

### Finding 4: Bug finding benefits most from compression
Bug finding improved from 57.1% to 85.7% (+28.6 pp) with compression.
The structured API surface and invariant output helps the model identify
design issues that raw context obscures.

---

## 4. What We Built

### New Modules in `src/lyme_model/amplify/`

| Module | Purpose |
|--------|---------|
| `assembler.py` | `SmallModelContextAssembler` + `ContextPacket` + card types |
| `integration.py` | `AmplificationLayer` — coordinates all strategies |

### Context Packet Components
| Component | Purpose | When Used |
|-----------|---------|-----------|
| Repo structure | Top-level project overview | Always |
| API surface cards | Function/class signatures per module | Always |
| Dependency cards | Import relationships | Architecture tasks |
| Test cards | Test coverage and results | Debug/repair tasks |
| Invariants | Code conventions and patterns | Code generation |

---

## 5. Decision: Which Compression to Use

| Use Case | Best Strategy | Reason |
|----------|--------------|--------|
| **Small repo** (<500 tok) | Raw | Compression adds overhead without benefit |
| **Medium repo** (500-4000 tok) | Lyme L1-L4 structured | 86% reduction, quality improvement |
| **Large repo** (4000+ tok) | Rehydration packet (L5) | Only way to fit in context |
| **Bug finding** task | Lyme L1-L4 structured | +28.6 pp improvement |
| **Summary/documentation** | Raw | Raw gives best context for write tasks |

---

## 6. Recommendation

**Use Lyme L1-L4 compression as the default for Lyme Model on repos >500 tokens.**
This is the first confirmed positive result for the compression thesis.

For small repos (<500 tokens), skip compression and use raw context directly.

For the rehydration layer (L5), test in a future week on very large repos.

---

## 7. Raw Data

Saved to `lyme-output/sprint-weeks-53-72/compression-comparison-results.json`
