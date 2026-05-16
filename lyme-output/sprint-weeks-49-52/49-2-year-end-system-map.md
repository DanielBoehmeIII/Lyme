# Year-End System Map

## Module Inventory

### 1. Runtime

**Purpose:** CLI framework, configuration loading, plugin system, event loop, storage layer.

**Maturity:** Stable. 30+ commands with argparse-based parsing, error handling, configuration from YAML, and output formatting. Entry point (`lyme.cli:main`) is production-usable.

**Dependencies:** `pyyaml>=6.0`, Python 3.10+.

**Known Weaknesses:**
- No async support. All commands are synchronous.
- No daemon/server mode. Everything is one-shot CLI.
- Configuration is flat YAML, no schema validation at load time.
- Plugin system is a registry pattern, not a dynamic loader.

**Next Evolution:**
- Add async runtime for concurrent benchmark execution
- Add server mode for IDE bridge and CI integration
- Add JSON Schema validation for config

---

### 2. Model Adapters

**Purpose:** Interface for connecting to local and API-based models (Ollama, llama.cpp, OpenAI-compatible, Claude Code, OpenCode).

**Maturity:** Alpha. Capability matrix defines evaluation tasks. Model adapter exists but is not the primary integration path — Lyme does not drive agents; it observes them.

**Dependencies:** Optional: Ollama, llama.cpp, HTTP client.

**Known Weaknesses:**
- No adapter for VSCode extensions, Copilot, or Cursor
- No streaming response handling
- No model health monitoring (response time, error rate)
- No fallback/retry logic
- Capability matrix is hardcoded, not discovered

**Next Evolution:**
- Add LangChain/LiteLLM integration for broader model access
- Implement model health monitoring
- Add streaming trace recording
- Make capability matrix auto-detectable via eval prompts

---

### 3. Compression Layers

**Purpose:** 5-layer codebase compression pipeline: File Tree → API Surface → Subsystem Clustering → Invariant Discovery → Task-Aware Rehydration.

**Maturity:** Beta. All 5 layers implemented. File tree supports 55 languages, 14 frameworks. API layer does full AST for Python, regex for JS/TS. Subsystem layer builds import graphs and detects circular dependencies. Invariant layer analyzes git history for co-change patterns, shared constants, duplication. Rehydration layer produces task-focused context packets with budget optimization.

**Dependencies:** None beyond Python stdlib.

**Known Weaknesses:**
- Full AST parsing for Python only. JS/TS/MD use regex (fragile).
- Invariant layer requires git history. Shallow clones or new projects produce weak invariants.
- Rehydration budget optimization is heuristic (keyword scoring), not learned.
- No cross-language compression comparison.
- No compression ratio benchmarks across different repo sizes/languages.
- Compression is one-shot, not incremental — recompresses entire repo each time.

**Next Evolution:**
- Add tree-sitter for multi-language AST parsing
- Implement incremental compression (cache layers, update only changed files)
- Add compression ratio telemetry
- Build learned relevance scoring for context budget
- Add language-specific compression strategies

---

### 4. Memory Systems

**Purpose:** Persistent agent memory with 3 types (procedural, episodic, semantic), importance scoring, access tracking, age-based pruning, capacity limits. Cross-repo memory fabric for multi-repo knowledge.

**Maturity:** Beta (single-repo), Alpha (fabric).

**Dependencies:** JSON file storage.

**Known Weaknesses:**
- Keyword-based retrieval only. No vector embeddings.
- No semantic search (no embedding model integration).
- Importance scoring is heuristic (access count, recency, explicit marking).
- Pruning is FIFO + threshold, not learned.
- Memory fabric is a cross-repo extension but uses the same keyword search.
- No memory consolidation/compression across sessions.
- No concept of memory conflicts or contradiction resolution.

**Next Evolution:**
- Add optional embedding model for semantic retrieval
- Implement importance decay curves from real usage data
- Add memory consolidation (summarize multiple episodic memories)
- Build cross-session memory synthesis
- Add memory conflict detection

---

### 5. Tool Router

**Purpose:** Routes agent actions to appropriate tools (10 defined: grep_search, ast_parse, dep_graph, vector_search, test_runner, shell_command, package_manager, static_analyzer, formatter, type_checker). Heuristic capability → cost → reliability scoring.

**Maturity:** Alpha. Tools are defined with capability metadata. Router uses static scoring, not learned routing.

**Dependencies:** None.

**Known Weaknesses:**
- Tool definitions are hardcoded in the module, not pluggable.
- Routing is a weighted heuristic — no learning from past routing outcomes.
- No tool call caching (repeated identical calls re-execute).
- Tool cost model is developer estimate, not measured.
- No timeout/retry per tool type.
- Router does not observe tool success/failure to update routing.

**Next Evolution:**
- Add learned routing from past tool call outcomes
- Implement tool call caching with invalidation
- Add pluggable tool definitions (community-contributed tools)
- Measure actual tool cost/latency for model updates

---

### 6. Causal Graph

**Purpose:** Build causal graphs from repository analysis. Infer file-level effect relationships. Propagate failure impact through the graph. Estimate breakage risk. Identify hidden dependencies, amplification zones, and architectural pressure points.

**Maturity:** Beta. Full pipeline: inference engine builds graph from AST + import analysis, propagator models failure cascades, impact estimator scores breakage risk, renderer produces HTML/Graphviz/Mermaid/D3 visualizations.

**Dependencies:** graphviz optional.

**Known Weaknesses:**
- Causal inference is heuristic (import graph + file co-change patterns = arrows). No actual causal inference algorithm.
- Graph construction is static (one-shot per repo analysis).
- Failure propagation assumes linear chain — does not model feedback loops or damping.
- No temporal dimension (graph doesn't capture how causality evolves).
- Large repos produce unreadably dense graphs (thousands of nodes).
- Impact estimation is uncalibrated — scores have no known error rate.

**Next Evolution:**
- Add do-calculus-inspired intervention analysis
- Add temporal causal graphs (how causality changes over git history)
- Implement graph sparsification for large repos
- Calibrate impact scores against real incidents
- Add time-to-failure estimation

---

### 7. Invariant Discovery

**Purpose:** Discover architectural invariants from repository analysis. Detect violations, contradictions, and fragility. Generate repair suggestions. Track invariant evolution.

**Maturity:** Beta. Discovers co-change patterns, shared constants, duplicated code, circular imports, large file/import risk zones, naming conventions. Violation detector checks invariants against current state. Repair suggester produces concrete plans.

**Dependencies:** git history.

**Known Weaknesses:**
- Invariants are pattern-based, not semantic. "Files A and B always change together" ≠ "A and B share an architectural invariant."
- No formal specification language for invariants (no AI, TLA+, or similar).
- Violation detection is heuristic threshold-based.
- Repair suggestions are template-based, not context-aware.
- Invariant quality depends entirely on git history depth.
- No invariant confidence calibration.

**Next Evolution:**
- Add formal invariant specification format
- Implement invariant inference from multiple sources (not just git)
- Add learned violation detection (train on past violations)
- Build invariant-driven test generation
- Add cross-project invariant comparison

---

### 8. Observatory

**Purpose:** Continuous repository observation. v1: polling-based with health metrics, forecasts, dashboard. v2: integrated observation pipelines with data storage, timeline building, replay capabilities.

**Maturity:** Alpha. Both versions implemented but produce synthetic/estimated data, not real measurements.

**Dependencies:** None (JSON output).

**Known Weaknesses:**
- No real continuous observation — poll interval is a simulation parameter.
- Health metrics are static analysis scores, not dynamic.
- Forecasting uses simple trend extrapolation, no time-series model.
- Dashboard is static HTML generation.
- Observatory v2 storage strategy produces JSON snapshots, not time-series.
- No real integration with CI/CD pipelines.

**Next Evolution:**
- Add real CRON-based observation scheduler
- Implement time-series database adapter (SQLite/InfluxDB)
- Build health metric baseline detection
- Add real CI/CD pipeline hooks (GitHub Actions, GitLab CI)
- Implement anomaly alerting

---

### 9. Governance

**Purpose:** Change governance engine with 5 decision levels (AUTO_APPLY → BLOCK), 13 default policies, risk scoring, sensitive code detection (13 categories), 5-critic review board, repo constitution format, immutable change ledger.

**Maturity:** Beta. Fully implemented with CLI commands, JSON policy format, constitution initialization and validation, ledger recording and path tracing.

**Dependencies:** None (JSON file storage).

**Known Weaknesses:**
- Policies are evaluated statically (file path + action type), not contextually.
- Risk scoring is a single float, not a multi-dimensional assessment.
- Review board uses simulated critics — no real model integration.
- Constitution format is JSON-only, no DSL or higher-level language.
- Ledger is append-only JSON, not a cryptographically verified log.
- No integration with external policy systems (OPA, Kyverno, etc.).
- Governance decisions are not empirically evaluated for correctness.

**Next Evolution:**
- Add contextual policy evaluation (consider file content, not just path)
- Implement multi-dimensional risk scoring
- Connect review board to real models
- Add constitution DSL for human-readable policies
- Upgrade ledger to Merkle-tree-based verification
- Add OPA/Kyverno integration

---

### 10. Benchmarks

**Purpose:** 8 registered benchmark scenarios across 5 categories (latency, hallucination, multi-file edit, context retention, tool call accuracy, search efficiency, long-horizon, repair ability). Benchmark engine with tracing, evaluation, and storage. Cognition benchmark spec (8 dimensions, 16 tasks) with anti-gaming rules.

**Maturity:** Beta (scenarios), Alpha (cognition spec).

**Dependencies:** pytest (for test-aware scenarios).

**Known Weaknesses:**
- Scenarios are synthetic/test repositories, not real codebases.
- Evaluation is rule-based (check output matches expected), not semantic.
- No model integration — scenarios define tasks but don't actually run agents.
- Benchmark results are simulated for demo purposes.
- Cognition benchmark spec is aspirational — 16 tasks defined but none implemented.
- No automated regression testing against model versions.
- Leaderboard shows simulated data.

**Next Evolution:**
- Connect benchmarks to real agent execution
- Implement SWE-bench-compatible scenario adapter
- Build continuous benchmark pipeline (run on every release)
- Add community-contributed scenarios
- Implement cognition benchmark tasks
- Calibrate scenario difficulty against real model performance

---

### 11. Standards

**Purpose:** Open Agent Trace Standard (OATS) v0.7.0, Semantic Diff Standard (SDS), Software Cognition Benchmark Specification.

**Maturity:** Alpha. Formats defined, validated, exemplified with 3+ examples each. Trace comparison tools exist.

**Dependencies:** None.

**Known Weaknesses:**
- Standards are Lyme-internal. No adoption outside the project.
- No formal specification process (no RFC, no working group).
- Semantic diff standard has no formal validation rules.
- Benchmark spec is aspirational.
- No tooling for converting between Lyme format and other agent formats.
- Standards versioning strategy is ad-hoc.

**Next Evolution:**
- Publish standards as open specs with community review
- Build conversion tools for major agent frameworks (LangChain traces, OpenAI, etc.)
- Establish a standards working group
- Implement formal validation (JSON Schema, ShEx)
- Add version migration tooling

---

### 12. Integrations

**Purpose:** CI/CD integration (governance policies in CI pipeline, artifact export), IDE bridge (LSP-compatible protocol), PR intelligence (GitHub PR analysis), research corpus management, research portal, contribution protocol.

**Maturity:** Pre-Alpha. Interfaces defined, implementations are stubs or mock-mode.

**Dependencies:** Optional: GitHub API (for PR intelligence).

**Known Weaknesses:**
- CI integration produces artifacts but has no real CI pipeline hooks.
- IDE bridge is a protocol specification with a mock endpoint.
- PR intelligence runs in mock mode — no real GitHub API integration in core.
- Research corpus management is JSON file management with basic privacy redaction.
- Research portal generates static JSON.
- Contribution protocol has 11 types defined but no community process.
- No integration with any external agent framework (LangChain, CrewAI, AutoGPT, etc.).

**Next Evolution:**
- Build real CI integration (GitHub Action, GitLab CI template)
- Implement VSCode extension via LSP
- Connect PR intelligence to real GitHub API
- Build interactive research portal (web app)
- Launch community contribution process

---

## Module Summary

| Module | Maturity | Dependencies | Weaknesses | Next Evolution |
|---|---|---|---|---|
| Runtime | Stable | pyyaml | No async, no server mode | Async runtime, server mode |
| Model Adapters | Alpha | Ollama/llama.cpp opt | No streaming, no health | LangChain integration |
| Compression | Beta | None | Python-only AST, no incremental | Tree-sitter, incremental |
| Memory | Beta | JSON files | Keyword-only search, no embeddings | Semantic search, consolidation |
| Tool Router | Alpha | None | Static heuristic, no learning | Learned routing, caching |
| Causal Graph | Beta | graphviz opt | Heuristic inference, no temporal | Do-calculus, temporal |
| Invariant Discovery | Beta | git history | Pattern-based, no formal spec | Formal spec language |
| Observatory | Alpha | None | Simulated data, no scheduler | CRON scheduler, TSDB |
| Governance | Beta | None | Static evaluation, no crypto | Contextual eval, Merkle |
| Benchmarks | Beta | pytest opt | Synthetic, no model integration | Real agent execution |
| Standards | Alpha | None | No adoption outside Lyme | Open publishing, RFC |
| Integrations | Pre-Alpha | GitHub API opt | Stubs, mock mode | Real CI, IDE, PR |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI (30+ commands)                        │
├──────────────────────┬──────────────────────┬───────────────────────┤
│    PRODUCT LAYER     │    RESEARCH LAYER    │   GOVERNANCE LAYER     │
│                      │                      │                        │
│  doctor              │  Cognitive Tracing   │  Change Governance     │
│  ask                 │  Causal Graphs       │  Constitution          │
│  diff                │  Invariant Discovery │  Ledger                │
│  trace               │  Temporal Modeling   │  Sensitive Code        │
│  fix                 │  Scaling Laws        │  Review Board          │
│  history             │  Agent Coordination  │  Policies              │
│  memory              │  Hallucination Study │  Verification Graph    │
│  bench               │  Context Degradation │                        │
│  replay              │  Failure Analysis    │                        │
├──────────┬───────────┴──────────┬───────────┴──────────┬─────────────┤
│          │                      │                      │             │
│  Compression Pipeline          │  Memory Systems       │  Tools      │
│  (5 layers)                    │  (3 types + fabric)   │  (10 tools) │
│          │                      │                      │             │
├──────────┴─────────────────────┴──────────────────────┴─────────────┤
│                      TELEMETRY SUBSTRATE                             │
│  Tracing │ Events │ Metrics │ Privacy Boundary │ Storage │ Replay    │
├─────────────────────────────────────────────────────────────────────┤
│                      BENCHMARK ENGINE                                │
│  8 Scenarios │ Registry │ Cognitive Spec │ Leaderboard │ Reports     │
├─────────────────────────────────────────────────────────────────────┤
│                      STANDARDS                                        │
│  OATS │ SDS │ Cognition Benchmark Spec                               │
├─────────────────────────────────────────────────────────────────────┤
│                      INTEGRATIONS (Pre-Alpha)                        │
│  CI/CD │ IDE Bridge │ PR Intelligence │ Research Portal │ Corpus     │
└─────────────────────────────────────────────────────────────────────┘

Maturity Legend:
███ Production  ██ Beta  █ Alpha  ░ Pre-Alpha
```
