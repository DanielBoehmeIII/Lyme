# Week 76 — Context Packet Compiler

**Theme:** Compile repo information into small, model-readable packets.
**Target:** Small models (3-8B), low context windows (2K-8K).

---

## 1. Packet Types (8)

| Packet | Content | Typical Size | Purpose |
|--------|---------|-------------|---------|
| task | Type, description, target files, constraints | 20-50 tokens | What to do |
| file | Path, purpose, classes, functions, deps, LOC | 30-80 tokens | File summary |
| api | Module path, function signatures, class methods | 50-200 tokens | Public surface |
| dependency | Imports, imported-by, external deps, circular | 20-60 tokens | Dependency graph |
| test | Test files, functions, run command, gaps | 30-80 tokens | Test coverage |
| error | Type, message, file, line, stack summary | 40-100 tokens | Failure context |
| invariant | Must-not-break rules | 20-50 tokens | Safety constraints |
| patch | File, type, summary, +/- lines, verify/rollback | 30-60 tokens | Patch plan |

## 2. Design Principles

- **Natural language** (not JSON) — models tokenize NL more efficiently
- **Task-specific** — only relevant packets for the task
- **Prioritized** — most important content first within each packet
- **Bounded** — budget_per_packet = max_tokens / 8
- **Stable formatting** — same structure every time, models learn the pattern
- **High evidence density** — no filler, every token carries signal

## 3. Compression Benchmark

The compiler includes a `benchmark_compression()` method that compares packet format vs raw text size:
- `raw_tokens`: tokens in the raw file
- `packet_tokens`: tokens in the compiled packet
- `compression_ratio`: packet_tokens / raw_tokens

## 4. Integration with Existing Assembler

The compiler builds on the existing `SmallModelContextAssembler` in `amplify/assembler.py`. Where the assembler creates a monolithic `ContextPacket`, the compiler creates individual typed packets that can be independently compiled and composed.

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/amplify/compiler.py` | Context Packet Compiler with 8 packet types |

## 6. Next Week

Week 77 will build the Patch Planner — requiring plan validation before allowing weak models to patch.
