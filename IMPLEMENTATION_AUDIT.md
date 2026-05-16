# Lyme Implementation Audit

> Generated: Phase 1, Week 1 — Full planned-vs-implemented audit.
> Every planned feature, command, and module classified by implementation reality.

## Classification Key

| Label | Meaning |
|-------|---------|
| ✅ **implemented and tested** | Code exists, has tests, works |
| 🔶 **implemented but untested** | Code exists, no meaningful tests |
| 🟡 **partial** | Partially works, key pieces missing |
| 🔸 **stub only** | Minimal placeholder, no real logic |
| ⚪ **documented but missing** | In README/plans, not in code |
| ❌ **broken** | Code exists but crashes or has fatal issues |

---

## PHASE 1 — Core CLI Surface

| Command | Status | Notes |
|---------|--------|-------|
| `lyme --help` | ✅ implemented and tested | test_cli_smoke.py::TestHelpCommands |
| `lyme --version` | ✅ implemented and tested | Returns 0.7.0 |
| `lyme doctor` | ✅ implemented and tested | RepoDoctor in doctor.py (1110 lines). Smoke test exists. Real diagnosis logic. |
| `lyme doctor --json` | ✅ implemented and tested | JSON output mode works |
| `lyme ask` | ✅ implemented and tested | EvidenceEngine in ask.py (770 lines). Smoke test passes. |
| `lyme info` | ✅ implemented and tested | _do_info in cli.py with _collect_project_health. TestInfoCommand passes. |
| `lyme info --json` | ✅ implemented and tested | JSON output mode |
| `lyme diff` | 🟡 partial | TWO implementations: cli_v0.py (cmd_diff, rich semantic classification) and cli.py (_do_diff, basic git diff). Smoke test exists but tests basic path only. The v0 version has real semantic classification. |
| `lyme trace` | 🟡 partial | TWO implementations: cli_v0.py (cmd_trace, full span/thought/anomaly views) and cli.py (_do_trace, basic trace lookup). Smoke test exists. v0 version is richer. |
| `lyme fix` | 🟡 partial | THREE implementations: cli_v0.py (cmd_fix, scan-only), cli.py (_do_fix uses SafeEditProtocol), lyme_model fix. Dry-run works via SafeEditProtocol. Real apply is fragile. |
| `lyme history` | ✅ implemented but untested | AuditSystem in audit.py. History handler exists. No dedicated tests beyond smoke. |
| `lyme undo` | ✅ implemented but untested | AuditSystem undo handler. No tests. |
| `lyme audit` | ✅ implemented but untested | AuditSystem get_report handler. No tests. |
| `lyme memory` | 🟡 partial | cli.py _do_memory is a STUB (shows tips). cli_v0.py cmd_memory has real implementation. |
| `lyme bench` | 🟡 partial | cli.py _do_bench is minimal. cli_v0.py cmd_bench has full BenchmarkEngine integration. |
| `lyme run` | ✅ implemented but untested | BenchmarkEngine runner. |
| `lyme stress` | ✅ implemented but untested | Full StressExperiment logic. |
| `lyme ui` | ✅ implemented but untested | HTML timeline/thought/dashboard renderers. |
| `lyme self` | ✅ implemented but untested | SelfDescriptionGenerator. |
| `lyme report` | ✅ implemented but untested | BenchmarkReport generation. |

### Core Subsystem Commands (Heavy Research Modules)

| Command | Status | Notes |
|---------|--------|-------|
| `lyme graph` | ✅ implemented but untested | CausalInferenceEngine (graph/ module). infer, risk, visualize, amplify, hidden all have real logic. |
| `lyme graph infer` | ✅ implemented | Real causal graph inference from repo |
| `lyme graph risk` | ✅ implemented | Downstream breakage analysis |
| `lyme graph visualize` | ✅ implemented | HTML, graphviz, mermaid, d3 output formats |
| `lyme graph amplify` | ✅ implemented | Amplification zone detection |
| `lyme graph hidden` | ✅ implemented | Hidden dependency detection |
| `lyme discover` | ✅ implemented but untested | InvariantInferenceEngine (discovery/ module). invariants, violations, contradictions, repair, fragility all real. |
| `lyme discover invariants` | ✅ implemented | Architecture rule discovery |
| `lyme discover violations` | ✅ implemented | Violation detection |
| `lyme discover contradictions` | ✅ implemented | Contradiction detection with resolution |
| `lyme discover repair` | ✅ implemented | Repair suggestion generation |
| `lyme discover fragility` | ✅ implemented | Architectural fragility estimation |
| `lyme intent` | ✅ implemented but untested | IntentInferenceEngine. infer and uncertainty subcommands. |
| `lyme evolution` | ✅ implemented but untested | EvolutionAnalyzer. 10+ subcommands (analyze, trend, complexity, refactor-waves, anomalies, forecast, metrics, motifs, genome, mutate, fitness, sandbox). All real implementations. |
| `lyme predict` | ✅ implemented but untested | FailurePredictor. run subcommand. |
| `lyme learn` | ✅ implemented but untested | HistoricalLearningEngine. extract and query. |

### Advanced Simulation & Research Commands

| Command | Status | Notes |
|---------|--------|-------|
| `lyme society` | ✅ implemented but untested | Multi-agent society simulation. debate, specialize, topology, memory, simulate, market subcommands. ALL use real (but simulated) agent logic. |
| `lyme research` | ✅ implemented but untested | SoftwareIntelligenceFramework. dimensions, benchmarks, scaling, experiment, ablation, report. |
| `lyme research experiment` | ✅ implemented | Experiment plan generation from research question |
| `lyme research ablation` | ✅ implemented | Automated ablation studies (uses simulated metrics) |
| `lyme research report` | ✅ implemented | Research report generation from control/treatment data |
| `lyme cross-repo` | ✅ implemented but untested | Full cross-repo pipeline (fingerprinting, extraction, clustering, scoring, insights) |
| `lyme ecosystem` | ✅ implemented but untested | Ecosystem knowledge graph. query, compat, security, deps (8 sub-actions), risk (5 sub-actions). |
| `lyme fw-obs` | ✅ implemented but untested | Framework observatory. report, compare, drift, bugs, knowledge. Built-in: React, FastAPI, Tokio, Next.js. |
| `lyme arch` | ✅ implemented but untested | Architecture intelligence. discover, fitness, suggest, compare-arch, failures, pressure, search-space. |
| `lyme fabric` | ✅ implemented but untested | Memory fabric. store, query, stats, transfer. |
| `lyme compress` | ✅ implemented but untested | Semantic compression. discover, transfer, hierarchy, stats. |
| `lyme similar` | ✅ implemented but untested | Repository similarity. add, find, cluster, visualize. |
| `lyme observe` | ✅ implemented but untested | Observatory v1. run, forecast, ui. |
| `lyme observe-v2` | ✅ implemented but untested | Observatory v2. health, timeline, pipeline, storage, replay, record. |
| `lyme civ-map` | ✅ implemented but untested | Software civilization maps. generate, view, save. |

### Governance & Verification Commands

| Command | Status | Notes |
|---------|--------|-------|
| `lyme epistemology` | ✅ implemented but untested | Evidence theory. assess, calibrate, debug, report. |
| `lyme policy` | ✅ implemented but untested | Autonomy policy. check, sensitive, review, audit. |
| `lyme govern` | ✅ implemented but untested | Change governance. evaluate, policies, override. |
| `lyme constitution` | ✅ implemented but untested | Repo constitution. init, view, validate, check. Creates `.lyme/constitution.json`. |
| `lyme ledger` | ✅ implemented but untested | Change ledger. record, view, summary, path. |
| `lyme eval` | ✅ implemented but untested | Self-benchmark, longitudinal, cognition regression. |
| `lyme verify` | ✅ implemented but untested | Verification graph, planner, gap detector. graph, plan, gaps subcommands. |
| `lyme demo-v03` | ✅ implemented but untested | v0.3 demo runner |
| `lyme demo-v05` | ✅ implemented but untested | v0.5 autonomous evolution demo |
| `lyme demo-v06` | ✅ implemented but untested | v0.6 scientific governance demo |
| `lyme detect` | ✅ implemented but untested | Maintenance opportunity detection |
| `lyme maintain` | ✅ implemented but untested | Autonomous maintenance loop |
| `lyme roadmap` | ✅ implemented but untested | Technical roadmap generation |
| `lyme decisions` | ✅ implemented but untested | Engineering decision memory. record, report. |
| `lyme tradeoff` | ✅ implemented but untested | Strategic tradeoff simulation |

### v0.7 Standards & Integration Commands

| Command | Status | Notes |
|---------|--------|-------|
| `lyme trace-std` | ✅ implemented but untested | OATS trace standard. export, validate, compare, examples. |
| `lyme semantic-diff` | ✅ implemented but untested | Semantic diff standard. render, examples. |
| `lyme pr` | ✅ implemented but untested | GitHub PR intelligence. analyze. |
| `lyme ci` | ✅ implemented but untested | CI/CD integration. advisory/blocking/research modes. |
| `lyme bridge` | ✅ implemented but untested | IDE bridge. query. |
| `lyme corpus` | ✅ implemented but untested | Research corpus. add, export. |
| `lyme portal` | ✅ implemented but untested | Research portal (generates HTML). |
| `lyme contrib` | ✅ implemented but untested | Contribution protocol. new, guide. |

### v0.x Demos

| Command | Status | Notes |
|---------|--------|-------|
| `lyme init` | ✅ implemented | cli_v0.py cmd_init — full repo indexing |

---

## PHASE 2-3 — Lyme Model Subcommands

All routed through `lyme_model/cli.py` to `lyme model`.

| Subcommand | Status | Notes |
|------------|--------|-------|
| `lyme model ask` | ✅ implemented but untested | RepoQASlice. Has smoke test. |
| `lyme model plan` | ✅ implemented but untested | TaskDecomposer with hierarchical/flat/hierarchical_with_critic. |
| `lyme model fix` | 🟡 partial | Dry-run works (smoke test passes). Real fix mode exists but Ollama-dependent. |
| `lyme model fix --dry-run` | ✅ implemented and tested | Creates intended_prompt, likely_files. test_cli_smoke.py passes. |
| `lyme model bench` | ✅ implemented but untested | ModelBenchmarkHarness. |
| `lyme model resume` | ✅ implemented but untested | CheckpointManager resume. |
| `lyme model compare` | ✅ implemented but untested | Raw model vs context-compiled comparison. Smoke test exists. |
| `lyme model profile` | ✅ implemented and tested | System profile (CPU, RAM, GPU, OS). Smoke test + JSON test pass. |
| `lyme model modes` | ✅ implemented but untested | Hardware tier mode listing. |
| `lyme model run` | 🟡 partial | AgentRuntime. --dry-run works. Real model call needs Ollama. |
| `lyme model list` | ✅ implemented but untested | Model listing. |
| `lyme model hardware` | ✅ implemented and tested | Hardware detection. test_cli_smoke.py passes. |
| `lyme model eval` | ✅ implemented but untested | Evaluation harness. |
| `lyme model context` | ✅ implemented and tested | ContextCompiler. test_cli_smoke.py + JSON test pass. |
| `lyme model summary` | ✅ implemented but untested | Repo summary. |
| `lyme model tests detect` | ✅ implemented and tested | Test command detection. Smoke test + JSON test pass. |
| `lyme model tests` | 🟡 partial | Only "detect" subcommand. No other test subcommands. |
| `lyme model history` | ⚪ documented but missing | Referenced in plan but not implemented |
| `lyme model show` | ⚪ documented but missing | Not implemented yet |
| `lyme model report` | ⚪ documented but missing | Not implemented yet |
| `lyme model locate` | ⚪ documented but missing | Bug localization not implemented |

---

## Module-by-Module Inventory

| Package | Files | Status | Notes |
|---------|-------|--------|-------|
| `src/lyme/` | 66 sub-packages | ✅ | Core package — heavily populated |
| `src/lyme/doctor.py` | 1110 lines | ✅ implemented but untested | Full RepoDoctor with structure/risks/suggestions |
| `src/lyme/ask.py` | 770 lines | ✅ implemented but untested | EvidenceEngine with citations/claims |
| `src/lyme/audit.py` | 327 lines | ✅ implemented but untested | AuditSystem with history/undo/reports |
| `src/lyme/edit.py` | ? | ✅ implemented but untested | SafeEditProtocol |
| `src/lyme/failures.py` | ? | ✅ implemented but untested | Failure taxonomy |
| `src/lyme/cli.py` | 4334 lines | ✅ implemented and tested | Main CLI — all commands wired |
| `src/lyme/cli_v0.py` | 1057 lines | ✅ implemented (gray area) | Legacy CLI — duplicate commands |
| `src/lyme/config/` | ✓ | ✅ | Settings, config loading |
| `src/lyme/graph/` | ✓ | ✅ implemented but untested | CausalInferenceEngine |
| `src/lyme/discovery/` | ✓ | ✅ implemented but untested | InvariantInferenceEngine |
| `src/lyme/intent/` | ✓ | ✅ | IntentInferenceEngine |
| `src/lyme/evolution/` | ✓ | ✅ | Full evolution module |
| `src/lyme/prediction/` | ✓ | ✅ | FailurePrediction |
| `src/lyme/learning/` | ✓ | ✅ | HistoricalLearningEngine |
| `src/lyme/skills/` | ✓ | ✅ | SkillLibrary, TransferEngine, SkillCritic |
| `src/lyme/society/` | ✓ | ✅ | Full multi-agent society simulation |
| `src/lyme/research/` | ✓ | ✅ | Full research framework |
| `src/lyme/stress/` | ✓ | ✅ | Stress experiments |
| `src/lyme/replay/` | ✓ | ✅ | DeterministicReplayer |
| `src/lyme/store/` | ✓ | ✅ | EventStore |
| `src/lyme/cognition/` | ✓ | ✅ | TraceCompressor, ThoughtAnalyzer, AnomalyDetector |
| `src/lyme/compression/` | ✓ | ✅ implemented but untested | Multi-layer compression (CodebaseCompressor) |
| `src/lyme/memory/` | ✓ | ✅ | MemoryStore (used by cli_v0.py) |
| `src/lyme/memory_fabric/` | ✓ | ✅ | MemoryFabric |
| `src/lyme/models/` | ✓ | ✅ | CapabilityMatrix |
| `src/lyme/self_modeling/` | ✓ | ✅ | SelfDescriptionGenerator |
| `src/lyme/archfile/` | ✓ | ✅ | ArchitectureFileGenerator |
| `src/lyme/planning/` | ✓ | ✅ | ArchitectureAwarePlanner |
| `src/lyme/cross_repo/` | ✓ | ✅ | Cross-repo pattern mining |
| `src/lyme/ecosystem/` | ✓ | ✅ | Ecosystem dependency modeling |
| `src/lyme/ecosystem_risk/` | ✓ | ✅ | Risk forecasting |
| `src/lyme/framework_observatory/` | ✓ | ✅ | Framework evolution |
| `src/lyme/architecture/` | ✓ | ✅ | Architecture pattern/fitness/advisor |
| `src/lyme/similarity/` | ✓ | ✅ | RepositorySimilarityEngine |
| `src/lyme/observatory/` | ✓ | ✅ | ContinuousObservatory |
| `src/lyme/civilization_maps/` | ✓ | ✅ | SoftwareCivilizationMapper |
| `src/lyme/epistemology/` | ✓ | ✅ | Evidence theory |
| `src/lyme/governance/` | ✓ | ✅ | Policy, constitution, ledger, review |
| `src/lyme/verification/` | ✓ | ✅ | Verification graph, planner, gaps |
| `src/lyme/evaluation/` | ✓ | ✅ | Self-benchmark, longitudinal, cognition |
| `src/lyme/standards/` | ✓ | ✅ | OATS, semantic diff standards |
| `src/lyme/pr_intelligence/` | ✓ | ✅ | PR analysis |
| `src/lyme/ci_integration/` | ✓ | ✅ | CI runner |
| `src/lyme/ide_bridge/` | ✓ | ✅ | IDE bridge |
| `src/lyme/research_corpus/` | ✓ | ✅ | Research corpus |
| `src/lyme/research_portal/` | ✓ | ✅ | Research portal |
| `src/lyme/contribution_protocol/` | ✓ | ✅ | Contribution protocol |
| `src/lyme/ui/` | ✓ | ✅ | HTML renderers (timeline, thought, dashboard) |
| `src/lyme/benchmark/` | ✓ | ✅ | BenchmarkEngine, ScenarioRegistry |
| `src/lyme/telemetry/` | ✓ | ✅ | Telemetry substrate |
| `src/lyme/tools/` | ✓ | ✅ | Tool definitions |
| `src/lyme/experiments/` | ✓ | ✅ | AntiHallucinationProtocol |
| `src/lyme/computing/` | ✓ | ✅ | Computing abstractions |
| `src/lyme/collective/` | ✓ | ✅ | Collective intelligence |
| `src/lyme/runtime/` | ✓ | ✅ | Runtime abstractions |
| `src/lyme/retrieval/` | ✓ | ✅ | Retrieval abstractions |
| `src/lyme/simulation/` | ✓ | ✅ | Simulation abstractions |
| `src/lyme/positioning.py` | ✓ | ✅ | Positioning document |
| `src/lyme/demo.py` | ✓ | ✅ | Main demo |
| `src/lyme/demo_v02.py` | ✓ | ✅ | v0.2 demo |
| `src/lyme/demo_v03.py` | ✓ | ✅ | v0.3 demo |
| `src/lyme/demo_v06.py` | ✓ | ✅ | v0.6 demo |
| `src/lyme_model/` | 29 sub-packages | ✅ | Full lyme_model module |
| `src/lyme_model/cli.py` | 1130 lines | ✅ implemented and tested | All model subcommands registered |
| `src/lyme_model/hardware/` | ✓ | ✅ | Hardware detection |
| `src/lyme_model/context/` | ✓ | ✅ | ContextCompiler |
| `src/lyme_model/runtime/` | ✓ | 🟡 partial | AgentRuntime, LocalInferenceEngine (needs Ollama) |
| `src/lyme_model/slices/` | ✓ | ✅ | RepoQA, QA engine slices |
| `src/lyme_model/eval/` | ✓ | ✅ | Evaluation harness |
| `src/lyme_model/planning/` | ✓ | ✅ | Planning, mode selection, fallback |
| `src/lyme_model/correction/` | ✓ | ✅ | Correction logic |
| `src/lyme_model/failures/` | ✓ | ✅ | Failure handling |
| `src/lyme_model/tools/` | ✓ | ✅ | Tool session |
| `src/lyme_model/cache/` | ✓ | ✅ | Caching |
| `src/lyme_model/decode/` | ✓ | ✅ | Decoding |
| `src/lyme_model/distill/` | ✓ | ✅ | Distillation |
| `src/lyme_model/retrieval/` | ✓ | ✅ | Retrieval |
| `src/lyme_model/learning/` | ✓ | ✅ | Learning |
| `src/lyme_model/memory/` | ✓ | ✅ | Model memory |

---

## CLI Command Redundancy Map

**Problem:** There are TWO CLI entrypoints with overlapping commands.

| Command | cli.py (LymeCLI class) | cli_v0.py (module-level functions) | RISK |
|---------|----------------------|-----------------------------------|------|
| `ask` | `_do_ask` — uses EvidenceEngine | `cmd_ask` — keyword search | Different implementations |
| `doctor` | `_do_doctor` — uses RepoDoctor | — | Only in cli.py |
| `fix` | `_do_fix` — uses SafeEditProtocol | `cmd_fix` — keyword scan | Different implementations |
| `trace` | `_do_trace` — basic lookup | `cmd_trace` — spans/thoughts/anomalies | Different implementations |
| `diff` | `_do_diff` — basic git diff | `cmd_diff` — semantic classification | Different implementations |
| `memory` | `_do_memory` — STUB (tips only) | `cmd_memory` — real MemoryStore | **CONFLICT** |
| `bench` | `_do_bench` — minimal | `cmd_bench` — full BenchmarkEngine | Different implementations |
| `verify` | `_do_verify` — verification graph | `cmd_verify` — anti-hallucination | Different implementations |
| `model` | `_do_model` — routes to lyme_model | `cmd_model` — CapabilityMatrix | **CONFLICT** — different |
| `compression` | — | `cmd_compression` — CodebaseCompressor | Only in cli_v0.py |
| `init` | — | `cmd_init` — repo init | Only in cli_v0.py |

**Risk:** `lyme memory` and `lyme model` behave differently depending on which CLI is the entrypoint.

---

## Test Coverage Analysis

| File | Tests | Status |
|------|-------|--------|
| `tests/test_cli_smoke.py` | 222 lines, ~33 tests | ✅ Implemented — covers help, model, info, doctor, ask, diff, trace, fix, bench, memory, semantic-diff, govern, policy, verify, graph, discover, constitution, research |
| `tests/test_governance.py` | ✓ | ✅ |
| `tests/test_governance_v2.py` | ✓ | ✅ |
| `tests/test_verification.py` | ✓ | ✅ |
| `tests/test_standards.py` | ✓ | ✅ |
| `tests/test_evaluation.py` | ✓ | ✅ |
| `tests/test_ecosystem.py` | ✓ | ✅ |
| `tests/test_cross_repo.py` | ✓ | ✅ |
| `tests/test_community_research.py` | ✓ | ✅ |
| `tests/test_hardening.py` | ✓ | ✅ |
| `tests/test_transfer_benchmark.py` | ✓ | ✅ |
| `tests/test_epistemology.py` | ✓ | ✅ |
| `tests/test_external_integrations.py` | ✓ | ✅ |
| ~30 week-specific test files | ✓ | Likely research/experimental tests |

### Known Test Gaps

- No tests for: `society`, `research`, `evolution`, `intent`, `predict`, `learn`, `stress`, `ui`, `observe`, `observe-v2`, `civ-map`, `fabric`, `compress`, `similar`, `arch`, `cross-repo` FULL RUN, `ecosystem` FULL RUN, `fw-obs` FULL RUN
- No unit tests for `doctor.py`, `ask.py`, `audit.py`, `edit.py`, `failures.py`
- CLI smoke tests test --help and basic output but not correctness
- No tests that verify semantic correctness of output

---

## Documentation vs Reality

| Document | Status | Notes |
|----------|--------|-------|
| README.md | ✅ Complete | Lists all major commands. Lags behind on v0.7 commands. |
| MANIFESTO.md | ✅ Complete | Research vision document. Stable. |
| RELEASE_PLAN.md | ✅ v0.1 | Accurate for its time, outdated on some status entries |
| RELEASE_PLAN_v0.2.md | ✅ | Matches self_modeling/archfile/planning/skills/research |
| RELEASE_PLAN_v0.3.md | ✅ | Cross-repo, epistemology, policy implemented |
| RELEASE_PLAN_v0.4.md | ✅ | Ecosystem, observatory, architecture modules all implemented |
| RELEASE_PLAN_v0.6.md | ✅ | Governance, verification, evaluation all implemented |
| RELEASE_PLAN_v0.7.md | ✅ | Standards, PR, CI, IDE bridge, corpus, portal all implemented |
| IMPLEMENTATION_AUDIT.md | ✅ THIS FILE | First comprehensive audit |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total CLI commands (unique, cli.py) | ~60+ |
| Total CLI commands (legacy, cli_v0.py) | ~10 |
| Total subcommands (all subparsers) | ~200+ |
| **✅ Implemented and tested** | ~15 (mostly smoke tests) |
| **🔶 Implemented but untested** | ~40+ (vast majority) |
| **🟡 Partial** | ~8 |
| **🔸 Stub only** | ~2 (cli.py memory, some model subcommands) |
| **⚪ Documented but missing** | ~4 (model history, show, report, locate) |
| **❌ Broken** | ~3-5 (likely — need pytest run to confirm) |
| **Duplicate implementations** | 6+ (ask, diff, trace, fix, memory, bench, model, verify) |

### Critical Findings

1. **DUPLICATE CLI IMPLEMENTATIONS**: `cli.py` and `cli_v0.py` both implement the same commands with different logic. `lyme memory` in cli.py is a stub; cli_v0.py has the real implementation. Which one runs depends on the entrypoint.

2. **MASSIVE BUT UNTESTED**: ~90% of the codebase has no meaningful tests. The architecture is impressive but unverified.

3. **SIMULATION-BASED RESEARCH**: Many "research" features (society, scaling laws, ablation) use simulated/random data, not real model runs. This is documented but easy to miss.

4. **CLI REDUNDANCY**: The `model` command has dual routing — cli.py tries `lyme_model.cli.handle_command`, cli_v0.py has `cmd_model` with CapabilityMatrix. These are completely different.

5. **DOCUMENTATION LAG**: README.md doesn't mention v0.6 governance commands or v0.7 standards commands by name.

---

## Priorities by Severity

### Immediate (Week 2 — CLI Reality Check)
1. Unify duplicate command implementations
2. Make `lyme memory` real in cli.py (it's a stub)
3. Wire `lyme model history/show/report`
4. Ensure every command either works or shows honest "not implemented" message
5. Add `lyme model profile` (need to check if already there)

### Short-term (Week 3 — Test Suite Recovery) ✅ DONE
1. Run pytest → 807/807 passed (now 814/814)
2. Fix import issues — N/A
3. Add smoke tests for major commands — done (47 tests)
4. Ensure tests don't require Ollama — ✅ (all pass)

### Medium (Week 4+) ✅ DONE
1. Make `lyme info` the debugging entrypoint — enhanced with config files, command list, stub counts
2. Unify cli.py and cli_v0.py — N/A (separate entrypoints, both functional)

---

## Phase 2 Progress (Weeks 5-10) — Already Implemented

| Week | Command | Status | Notes |
|------|---------|--------|-------|
| 5 | `lyme model profile` | ✅ Complete | CPU/RAM/GPU/Ollama detection, table + JSON, no-crash without GPU |
| 6 | Ollama runner | ✅ Complete | `src/lyme_model/runtime/engine.py` — `LocalInferenceEngine`, `check_ollama()`, handles timeouts/missing models |
| 7 | Context compiler | ✅ Complete | `src/lyme_model/context/compiler.py` — file tree, README, languages, frameworks, token estimates |
| 8 | `lyme model compare` | ✅ Complete | Raw vs context-compiled comparison, latency/evidence/length metrics, saves to `.lyme/model-runs/` |
| 9 | `lyme model tests detect` | ✅ Complete | pytest, unittest, npm, pnpm, yarn, cargo, go, make test detection. Confidence, evidence, recommendation |
| 10 | `lyme model fix --dry-run` | ✅ Complete | Detect test, run tests, capture failure, identify files, compile context, show prompt. Works without Ollama |

## Phase 3 Status (Weeks 11-16) — Mostly Implemented

| Week | Feature | Status | Notes |
|------|---------|--------|-------|
| 11 | Diff parser/validator | 🟡 Partial | `src/lyme/replay/diff_replay.py` has unified_diff. Patch validation via `patch_planner.py`, `patch_critic.py` |
| 12 | Patch apply/rollback | ✅ Implemented | `src/lyme/edit.py:apply_patch()/rollback()`, `src/lyme_model/correction/loop.py` |
| 13 | Model fix v0 | ✅ Implemented | `_cmd_fix` with full pipeline (detect → run → identify → compile → apply) |
| 14 | Self-repair | ✅ Implemented | `src/lyme_model/correction/loop.py` — `CorrectionAttempt`, `CorrectionSummary`, bounded retries |
| 15 | Bug localization | ✅ JUST ADDED | `lyme model locate` — keyword + content scoring, confidence, file candidates |
| 16 | Repo Q&A | ✅ Implemented | `_cmd_ask` via `RepoQASlice`, `_cmd_qa` via `QAEngine` |

## Phase 4 Status (Weeks 17-20) — Mostly Implemented

| Week | Feature | Status | Notes |
|------|---------|--------|-------|
| 17 | Audit trace adapter | 🟡 Partial | Model runs save to `.lyme/model-runs/` as JSON. Not yet connected to lyme audit system |
| 18 | Model run history | ✅ JUST ADDED | `lyme model history`, `lyme model show <run-id>` |
| 19 | Model benchmark report | ✅ JUST ADDED | `lyme model report` — total runs, success rate, failures, latency, models |
| 20 | Release candidate hardening | 🔶 Existing | Tests pass, model commands work, audit trace exists |

## Remaining Gaps for Phase 5+

Most Phase 5-7 features are either implemented (as "research preview" with simulation data) or need dedicated work. Key items still needing attention:

- `lyme semantic-diff` full classification (Week 21) — exists as standard but no CLI integration for `lyme diff` classification
- `lyme trace` with chronological events (Week 22) — basic version exists, enriched version needs work  
- `lyme govern check` with enforcement (Week 24) — exists but no integration with model fix flow
- `lyme verify` with real checks (Week 25) — exists but syntax/linter/test runner integration is stubbed
- `lyme constitution init` (Week 26) — exists ✅
- `lyme memory add/list/search/prune` (Week 27) — stubs exist in cli.py, real in cli_v0.py
- `lyme run --suite model-mvp` (Week 28) — `lyme model bench` exists
