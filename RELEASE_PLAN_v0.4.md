# Lyme v0.4 — Computational Software Ecology

Theme: Repositories as living ecosystems within a computational software ecology.

> "Repositories are not isolated objects. They are ecosystems that evolve like living systems — libraries compete, abstractions mutate, architectures spread, conventions emerge, technical debt propagates, and repair strategies evolve socially."

---

## 1. Dependency Ecosystem Modeling

**Research Value:** Establishes the foundation for treating software ecosystems as living systems — with epidemiology modeling (vulnerability propagation), ecological modeling (competition/dominance/fragmentation), and network science (transitive dependency chains, centrality analysis).

**Product Value:** Engineers can visualize dependency risk, identify fragile chains, detect ecosystem lock-in, and forecast migration waves before they become critical.

**Demo Potential:**
- `lyme ecosystem deps build` — Build dependency graph from ecosystem knowledge
- `lyme ecosystem deps analyze` — Run full ecosystem analysis (stability, fragmentation, dominance)
- `lyme ecosystem deps chains` — Find brittle transitive dependency chains
- `lyme ecosystem deps visualize` — Interactive dependency graph HTML
- Benchmark datasets for Python web, JS frontend, and Rust ecosystems

**Scalability Concerns:** Graph algorithms (transitive closures, cycle detection) scale quadratically with library count. For >10K nodes, indexing and sampling strategies needed.

**Known Weaknesses:** Dependency data is knowledge-base-driven rather than live-scraped. Temporal propagation uses estimated delays rather than real-world measured data.

**Future Directions:** Live registry scraping (PyPI, npm, crates.io), real-time vulnerability feed integration, ML-based migration wave prediction.

---

## 2. Framework Evolution Observatory

**Research Value:** Enables longitudinal studies of how frameworks evolve — API surface changes, convention drift, architectural trends, and ecosystem migration patterns over time.

**Product Value:** Provides intelligence for migration planning (understanding breaking changes), framework selection (comparing health/trends), and upgrade risk assessment.

**Demo Potential:**
- `lyme fw-obs report <framework>` — Complete evolution report for any tracked framework
- `lyme fw-obs compare <a> <b>` — Compare two frameworks' evolution trajectories
- `lyme fw-obs drift <framework>` — Detect convention drift over versions
- `lyme fw-obs bugs <framework>` — Common bug pattern trends
- Built-in knowledge bases: React, FastAPI, Next.js, Tokio/Rust async ecosystem

**Scalability Concerns:** Snapshot storage grows linearly with tracked versions × frameworks. Current knowledge-base approach is hand-curated.

**Known Weaknesses:** Knowledge bases are static snapshots, not auto-updated. API surface changes are approximated rather than precisely extracted from source.

**Future Directions:** Automatic API diffing between framework versions, real-time ecosystem trend tracking from GitHub/registry APIs, community health metrics from contributor activity.

---

## 3. Ecosystem Risk Forecasting

**Research Value:** Combines epidemiology (vulnerability propagation), network science (dependency chain risk), and ecological modeling (abandonment/decay) into a unified risk framework.

**Product Value:** Proactive risk management — identify fragile libraries, predict breaking change impact, estimate migration effort, and get actionable recommendations before failures occur.

**Demo Potential:**
- `lyme risk assess <library>` — Full risk profile for any library
- `lyme risk report` — Complete ecosystem risk report
- `lyme risk migration <from> <to>` — Migration risk assessment
- `lyme risk vulnerabilities <file>` — Scan dependency file for vulnerabilities
- `lyme risk propagate <library>` — Vulnerability propagation analysis

**Scalability Concerns:** Propagation analysis traverses dependency graph breadth-first. For large ecosystems, algorithmic optimization and memoization are needed.

**Known Weaknesses:** Vulnerability database is hand-curated. Breaking change probabilities are heuristic. Abandonment detection relies on proxy signals rather than direct maintainer activity.

**Future Directions:** Integration with OSV/GHSA vulnerability databases, ML-based breaking change prediction from git history, real-time ecosystem health monitoring.

---

## 4. Architecture Pattern Discovery

**Research Value:** Enables automatic architecture classification and comparison — detecting layered monoliths, event-driven systems, CQRS variants, microservice clusters, hexagonal architectures, and plugin systems from codebase structure.

**Product Value:** Teams can understand their architecture objectively, detect pattern erosion, compare architectural variants, and identify hidden complexity before it becomes problematic.

**Demo Potential:**
- `lyme arch discover <repo>` — Discover architecture patterns in a repository
- `lyme arch compare <repo-a> <repo-b>` — Compare architectures
- `lyme arch failures <repo>` — Estimate failure tendencies
- `lyme arch pressure <repo>` — Track evolutionary pressure

**Scalability Concerns:** Pattern matching scales with module/file counts. Directory scanning is O(n) in file count. Import structure analysis needs efficient parsing.

**Known Weaknesses:** Pattern detection is heuristic (signal/indicator matching) rather than deep structural analysis. May misclassify hybrid architectures.

**Future Directions:** Dynamic analysis of runtime behavior for pattern confirmation, ML-based architecture classification from AST patterns, cross-repo architecture family learning.

---

## 5. Architecture Fitness Metrics

**Research Value:** Defines and operationalizes eight dimensions of architecture fitness — maintainability, evolvability, repairability, coordination cost, runtime stability, testing efficiency, deployment risk, and scaling pressure — with causal assumptions and observable signals.

**Product Value:** Quantifiable architecture quality assessment. Teams can track fitness over time, compare architectural alternatives, and identify specific improvement areas.

**Demo Potential:**
- `lyme arch fitness <repo>` — Full architecture fitness report
- `lyme arch fitness compare <a> <b>` — Compare fitness over time/snapshots
- Markdown report with dimension scores, signals, and recommendations

**Scalability Concerns:** Each dimension requires different data sources (git history, file structure, test coverage). Missing data reduces confidence.

**Known Weaknesses:** Metrics are proxy-based rather than ground truth. Some dimensions (runtime stability, scaling pressure) need runtime/operational data not available from static analysis.

**Future Directions:** Integration with CI/CD pipelines for operational metrics, longitudinal tracking across versions, calibrated benchmarks against known high-quality architectures.

---

## 6. Architecture Advisor

**Research Value:** Formalizes the architecture selection problem as a constrained optimization — given scale, team size, latency requirements, reliability goals, and deployment environment, which architecture maximizes fitness?

**Product Value:** Evidence-based architecture recommendations for new projects or migration decisions. Tradeoff analysis with predicted failure modes and hidden complexity estimates.

**Demo Potential:**
- `lyme arch suggest --scale=50 --team=8 --latency=low` — Architecture suggestions
- `lyme arch compare-arch "modular-monolith" "microservices"` — Architecture comparison
- `lyme arch predict-failures modular-monolith --scale=50 --team=8` — Failure mode prediction
- `lyme arch search-space` — Explore the full architecture decision space

**Scalability Concerns:** Decision space is small (12 architecture types × constraint combinations). Not a scalability problem.

**Known Weaknesses:** Recommendations are based on expert knowledge encoded in profiles, not empirical validation. Tradeoff weights are subjective.

**Future Directions:** Empirical validation against real project outcomes, ML-based architecture fitness prediction from project characteristics, integration with cost estimation models.

---

## 7. Multi-Repo Memory Fabric

**Research Value:** Enables cross-repository learning — repair patterns, migration strategies, invariant families, architectural motifs, and workflow optimizations shared across repositories with provenance tracking, privacy boundaries, contradiction handling, and confidence decay.

**Product Value:** Organizations learn continuously across projects. Patterns discovered in one repo transfer to others. Memory persists and improves over time with automatic contradiction detection and confidence decay.

**Demo Potential:**
- `lyme fabric store --content="..." --category=repair_pattern --tags="fastapi,async"` — Store a memory
- `lyme fabric query "how to handle pydantic v2 migration"` — Query across repos
- `lyme fabric stats` — Memory fabric statistics
- `lyme fabric transfer <source-repo> <target-repo>` — Cross-repo transfer score

**Scalability Concerns:** Memory retrieval is O(n) in memory count without indexing. With 100K+ memories, vector embeddings and approximate nearest neighbor search needed.

**Known Weaknesses:** Simple keyword-based relevance scoring rather than semantic similarity. No embedding/indexing support yet. Privacy boundary implementation is basic.

**Future Directions:** Vector embedding support for semantic search, automatic pattern extraction from git history, federated memory across organizational boundaries, active contradiction resolution.

---

## 8. Semantic Compression

**Research Value:** Investigates whether software understanding can be compressed into reusable abstractions — authentication patterns, API structures, deployment workflows, testing strategies, caching architectures — with template-based compression, invariant extraction, and cross-context adaptation.

**Product Value:** Automatically discover and transfer best-practice patterns across repositories. Detect mismatches between compressed abstractions and local context. Build abstraction hierarchies.

**Demo Potential:**
- `lyme compress discover <files>` — Discover abstractions from code samples
- `lyme compress transfer --abstraction=auth --target-context=...` — Transfer abstraction
- `lyme compress hierarchy` — Build abstraction hierarchies
- `lyme compress stats` — Compression statistics

**Scalability Concerns:** Pattern matching at scale requires efficient code sample comparison. Current approach is template-based.

**Known Weaknesses:** Templates cover only 6 pattern types. Code matching is keyword-based. No real compression metrics (information-theoretic).

**Future Directions:** AST-based pattern extraction, learned compression from large code corpora, formal information-theoretic compression ratios, automated adaptation rule learning.

---

## 9. Repository Similarity Engine

**Research Value:** Enables systematic comparison of repositories across multiple dimensions — architecture, invariants, dependency structure, runtime behavior, workflow patterns, evolution history, and failure motifs.

**Product Value:** Find similar systems for pattern reuse, identify migration candidates, discover hidden risks through comparison with known failure patterns, and cluster repositories into meaningful ecosystem groups.

**Demo Potential:**
- `lyme similar add <repo>` — Add a repository profile
- `lyme similar find <repo-id>` — Find similar repositories
- `lyme similar cluster --n=3` — Cluster repositories
- `lyme similar visualize` — Interactive similarity matrix HTML

**Scalability Concerns:** Similarity computation is O(n²) in profile count. Pairwise comparison doesn't scale beyond ~1000 repos without approximation.

**Known Weaknesses:** Limited to static analysis-derived features. No runtime behavior or evolution history comparison yet. Clustering is heuristic (seed-based) rather than principled (e.g., spectral clustering).

**Future Directions:** Runtime trace similarity comparison, evolution trajectory similarity, ML-based similarity learning from labeled pairs, approximate nearest neighbor for large-scale comparison.

---

## 10. Observatory v2

**Research Value:** Integrates all observatory v1 capabilities with ecosystem intelligence, architecture fitness, invariant systems, coordination telemetry, skill transfer, confidence calibration, and risk forecasting into a unified instrumentation platform.

**Product Value:** Single pane of glass for software ecosystem health — evolution trends, architecture quality, risk forecasts, and confidence calibration in one system with data pipeline, storage strategy, and replay capabilities.

**Demo Potential:**
- `lyme observe-v2 health` — Integrated health dashboard
- `lyme observe-v2 timeline` — Build observation timeline
- `lyme observe-v2 pipeline` — Data pipeline report
- `lyme observe-v2 storage` — Storage report
- `lyme observe-v2 replay --start=0 --end=10` — Replay observations

**Scalability Concerns:** Observation storage grows linearly with snapshot frequency. Pipeline stages need async processing for real-time monitoring.

**Known Weaknesses:** Integration points stubbed — needs real connections to each subsystem. No visualization UI yet. Pipeline is conceptual.

**Future Directions:** Real-time dashboard with WebSocket updates, Grafana/Prometheus integration, automated alerting based on health thresholds, ML-based anomaly detection in observation streams.

---

## 11. Software Civilization Maps

**Research Value:** Represents software development as a living computational civilization — visualizing ecosystem evolution, framework influence networks, migration pathways, dependency empires, abstraction lineages, and repair cultures across Python, JavaScript, and Rust ecosystems.

**Product Value:** Strategic understanding of the software landscape — which frameworks are rising/falling, where migrations are flowing, which dependencies pose empire-level risk, and how repair cultures differ across ecosystems.

**Demo Potential:**
- `lyme civ-map generate` — Generate complete civilization map
- `lyme civ-map view` — View as HTML with ecosystem cards
- `lyme civ-map save` — Save as JSON for further analysis

**Scalability Concerns:** Civilization map data is knowledge-base-derived, not computed from live data. Adding new ecosystems requires manual knowledge encoding.

**Known Weaknesses:** Covers only 3 ecosystems (Python, JS, Rust). Framework influence is estimated rather than measured. Migration pathway volumes are approximate.

**Future Directions:** Live data integration from GitHub Archive/Libraries.io, temporal civilization maps showing evolution over time, ecosystem interaction analysis, automated civilization discovery for new ecosystems.

---

## Overall v0.4 Assessment

**What's New:** 11 major modules across 4 themes — ecosystem dynamics (3), architecture theory (3), repository cognition (3), and observatory v2 (2).

**Integration Points:** All modules expose CLI commands, JSON serialization, and dataclass-based APIs. New modules registered in `lyme/__init__.py` and CLI. Architecture module extended with 3 new submodules. Compression module extended with semantic compression.

**Scalability Concerns:** Graph algorithms in ecosystem analysis are the primary bottleneck. Most other modules are O(n) in their primary operations. Memory fabric and similarity engine need optimization for large-scale use.

**Known Gaps:** No live registry integration (PyPI/npm/crates.io scraping). No ML models yet (all heuristic/rule-based). No real-time monitoring integration. No database backend (all JSON file storage).

**Future Directions (v0.5):** Live ecosystem data integration, ML-powered pattern discovery and risk prediction, real-time observatory dashboards, database backend for production deployments, cross-ecosystem civilization analysis, automated repair pattern extraction from open source.
