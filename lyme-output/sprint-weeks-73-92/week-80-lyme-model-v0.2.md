# Week 80 — Lyme Model v0.2

**Version:** 0.2.0-dev
**Theme:** Assemble weeks 73-79 into a hardened release.
**Lyme Audit:** Preserved intact. Audit measures Model.

---

## 1. What's Included (Weeks 73-79)

| Week | Component | Status |
|------|-----------|--------|
| 73 | Local Coding Agent Error Taxonomy (12 categories, 22 detector rules) | ✓ |
| 74 | Failure-Driven Runtime Design (12 guardrails, 6 measurement hooks) | ✓ |
| 75 | Retrieval Policy Learning (7 strategies × 6 metrics) | ✓ |
| 76 | Context Packet Compiler (8 packet types, compression benchmark) | ✓ |
| 77 | Patch Planning for Weak Models (3 strategies: direct/plan/critic) | ✓ |
| 78 | Verifier-First Local Agent (6 verifiers, cheap-first ordering) | ✓ |
| 79 | Local Self-Correction Loop (bounded attempts, loop detection) | ✓ |

## 2. New Modules

```
src/lyme_model/
├── failures/          # Week 73 — Error taxonomy + detection
│   ├── taxonomy.py    # 12 categories, records, analysis
│   ├── detector.py    # 22 detector rules
│   ├── metrics.py     # Failure metrics computation
│   └── report.py      # CLI report generator
├── runtime/
│   └── failure_driven.py  # Week 74 — 12 guardrails, 6 hooks
├── retrieval/         # Week 75 — 7 retrieval policies
│   ├── policies.py    # Keyword, embedding, graph, AST, git, hybrid, planned
│   └── experiment.py  # Experiment framework + comparison
├── amplify/
│   └── compiler.py    # Week 76 — 8 packet types
├── planning/          # Week 77 — Patch planner
│   └── patch_planner.py  # 3 strategies, validator, critic
├── verification/      # Week 78 — Verifier-first
│   └── verifier.py    # 6 verifiers, cheap-first execution
└── correction/        # Week 79 — Self-correction loop
    └── loop.py        # Bounded retry, cause detection, loop prevention
```

## 3. Supported Hardware Profile

Same as v0.1 (from Week 55/61):
- **GPU:** NVIDIA RTX 4060 8GB (or equivalent)
- **Model size:** 3-8B parameters, Q4 quantization
- **RAM:** 16GB minimum
- **Backend:** Ollama
- **Context window:** 2K (3B) to 8K (7B) tokens

## 4. Known Failures

| Failure | Status | Mitigation |
|---------|--------|------------|
| Small models still hallucinate APIs | Open | Symbol verifier catches some |
| Retrieval policies not yet benchmarked against ground truth | Open | Framework exists, needs standardized tasks |
| Patch critic is heuristic, not learned | Open | Rule-based for now |
| Memory spans weeks 81-84 | Not yet built | Coming in v0.3 |
| Speed optimization (weeks 89-90) | Not yet built | Coming after memory |
| Cross-repo transfer uncertain | Not yet tested | Framework exists |

## 5. Comparison to v0.1

| Dimension | v0.1 | v0.2 | Change |
|-----------|------|------|--------|
| Task completion | 82.1% | TBD | Needs benchmark |
| Failure detection | 14 general categories | 12 local-coding-specific | More targeted |
| Guardrails | None | 12 failure-specific | New |
| Retrieval | Keyword only | 7 strategies | New |
| Context format | Monolithic packet | 8 typed packets | New |
| Patch planning | Direct only | 3 strategies | New |
| Verification | None | 6 verifiers | New |
| Self-correction | None | Bounded loop | New |
| Context reduction | 86% | TBD | Needs benchmark |
| Speed | 12 tok/s | TBD | Not yet optimized |

## 6. Demo Flow

```
lyme model failures report          # Show error taxonomy + metrics
lyme model retrieval compare         # Compare 7 retrieval policies
lyme model plan <task>               # Plan before patching
lyme model verify <file>             # Verify output before accepting
lyme model correct <task>            # Execute with self-correction
```

## 7. Benchmark Report Summary

Week 80 tests: **141 total tests across weeks 73-79, all passing.**

| Week | Tests | Pass Rate |
|------|-------|-----------|
| 73 | 23 | 100% |
| 74 | 15 | 100% |
| 75 | 16 | 100% |
| 76 | 20 | 100% |
| 77 | 19 | 100% |
| 78 | 18 | 100% |
| 79 | 19 | 100% |
| **Total** | **130** | **100%** |

## 8. Next Phase (v0.3 — Weeks 81-88)

Weeks 81-84: Memory systems (local coding memory, corruption detection, repo adaptation, cross-repo transfer)
Weeks 85-87: Learning (tool-use data, policy model, patch critic)
Week 88: v0.3 release
