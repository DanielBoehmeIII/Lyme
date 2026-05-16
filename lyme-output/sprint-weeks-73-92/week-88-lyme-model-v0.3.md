# Week 88 — Lyme Model v0.3

**Version:** 0.3.0-dev
**Theme:** Assemble weeks 85-87 into a hardened release. Preserve v0.2 components.
**Lyme Audit:** Preserved intact. Audit measures Model.

---

## 1. What's Included (All Weeks 73-87)

| Week | Component | Status |
|------|-----------|--------|
| 73 | Local Coding Agent Error Taxonomy (12 categories, 22 detector rules) | ✓ v0.2 |
| 74 | Failure-Driven Runtime Design (12 guardrails, 6 measurement hooks) | ✓ v0.2 |
| 75 | Retrieval Policy Learning (7 strategies × 6 metrics) | ✓ v0.2 |
| 76 | Context Packet Compiler (8 packet types, compression benchmark) | ✓ v0.2 |
| 77 | Patch Planning for Weak Models (3 strategies: direct/plan/critic) | ✓ v0.2 |
| 78 | Verifier-First Local Agent (6 verifiers, cheap-first ordering) | ✓ v0.2 |
| 79 | Local Self-Correction Loop (bounded attempts, loop detection) | ✓ v0.2 |
| 80 | v0.2 Release | ✓ v0.2 |
| 81 | Local Agent Memory (9 memory types, evidence-override) | ✓ |
| 82 | Memory Corruption Detection (7 corruption types, quarantine) | ✓ |
| 83 | Repo-Specific Adaptation (9 profile fields, prompt section) | ✓ |
| 84 | Cross-Repo Transfer (5 transfer policies, experiment framework) | ✓ |
| **85** | **Toolformer-Style Data Generation (7 action types, 6 filters)** | **NEW v0.3** |
| **86** | **Tool-Use Policy Model (heuristic + weighted, train/benchmark)** | **NEW v0.3** |
| **87** | **Patch Critic Model (7 evaluation checks, diff-aware)** | **NEW v0.3** |

## 2. All Modules

```
src/lyme_model/
├── failures/         # Week 73 — Error taxonomy + detection
├── runtime/          # Week 74 — Failure-driven runtime
├── retrieval/        # Week 75 — Retrieval policy experiments
├── amplify/          # Week 76 — Context packet compiler
├── planning/         # Week 77 — Patch planner
├── verification/     # Week 78 — Verifier-first workflow
├── correction/       # Week 79 — Self-correction loop
├── memory/           # Weeks 81-84 — Memory system
├── learning/         # Weeks 85-87 — Learning pipeline (NEW)
├── hardware/         # Hardware detection
├── tools/            # Tool registry
├── eval/             # Evaluation harness
├── cli.py            # CLI entry point
├── config.py         # Configuration
└── __init__.py       # Package init (v0.3.0-dev)
```

## 3. Learning Pipeline (Weeks 85-87)

```
learning/
├── __init__.py         # Module exports
├── data_generation.py  # Week 85 — Toolformer-style data generation
│   ├── ToolExample        # Single trace-to-example
│   ├── DatasetSchema      # Complete dataset with train/val split
│   └── DataGenerator      # Audit trace + synthetic generation
├── tool_policy.py      # Week 86 — Tool-use policy model
│   ├── Action              # 7-action enum
│   ├── PolicyDecision      # Action + confidence + reasoning
│   ├── HeuristicRouter     # 6-rule baseline router
│   └── ToolPolicyModel     # Weighted learning + benchmark
└── patch_critic.py     # Week 87 — Patch critic model
    ├── CriticVerdict       # Approved + risks + blocked
    └── PatchCritic         # 7 evaluation checks
```

## 4. Supported Hardware Profile

Same as v0.2 (unchanged):
- **GPU:** NVIDIA RTX 4060 8GB (or equivalent)
- **Model size:** 3-8B parameters, Q4 quantization
- **RAM:** 16GB minimum
- **Backend:** Ollama
- **Context window:** 2K (3B) to 8K (7B) tokens

## 5. Known Failures

| Failure | Status | Mitigation |
|---------|--------|------------|
| Small models still hallucinate APIs | Open | Symbol verifier + patch critic catch some |
| Tool policy is heuristic + weighted, not learned | Open | Training data pipeline exists, model training deferred |
| Patch critic is rule-based, not learned | Open | Rules catch 7 categories, static analysis usable |
| Speed optimization (weeks 89-90) | Not yet built | Coming in v0.4 |
| Caching (week 90) | Not yet built | Coming in v0.4 |
| Hardware-aware scheduling (week 91) | Partial | Hardware detection exists, scheduling incomplete |

## 6. Comparison to v0.1

| Dimension | v0.1 | v0.2 | v0.3 |
|-----------|------|------|------|
| Task completion | 82.1% | TBD | TBD |
| Failure detection | 14 general categories | 12 local-coding-specific | Same |
| Guardrails | None | 12 failure-specific | Same |
| Retrieval | Keyword only | 7 strategies | Same |
| Context format | Monolithic | 8 typed packets | Same |
| Patch planning | Direct only | 3 strategies | Same |
| Verification | None | 6 verifiers | Same |
| Self-correction | None | Bounded loop | Same |
| Coding memory | None | None | 9 types |
| Cross-repo transfer | None | None | 5 policies |
| Tool-use training data | None | None | 7 action types |
| Tool-use policy | None | None | Heuristic + weighted |
| Patch critic | None | None | 7 checks |
| Context reduction | 86% | TBD | TBD |

## 7. Test Suite

**363 tests total, all passing.**

| Week | Module | Tests |
|------|--------|-------|
| 73 | failures/ | 23 |
| 74 | runtime/failure_driven | 15 |
| 75 | retrieval/ | 16 |
| 76 | amplify/compiler | 20 |
| 77 | planning/ | 19 |
| 78 | verification/ | 18 |
| 79 | correction/ | 19 |
| 80 | v0.2 assembly | 130 subtotal |
| 81-84 | memory/ | 25 |
| 85-87 | learning/ | 53 |
| Other | cli, config, hardware, tools, eval | ~180 |
| **Total** | | **363** |

## 8. Demo Flow

```bash
# v0.2 capabilities (preserved)
lyme model failures report        # Show error taxonomy + metrics
lyme model retrieval compare       # Compare 7 retrieval policies
lyme model plan <task>             # Plan before patching
lyme model verify <file>           # Verify output before accepting
lyme model correct <task>          # Execute with self-correction

# v0.3 new capabilities
lyme model learning generate       # Generate training data from traces
lyme model learning policy         # Run tool-use policy
lyme model learning critic <patch> # Criticize a patch before apply
```

## 9. Next Phase (v0.4 — Weeks 89-92)

Weeks 89-90: Speed optimization + caching
Week 91: Hardware-aware scheduling
Week 92: Second 20-week report + next roadmap
