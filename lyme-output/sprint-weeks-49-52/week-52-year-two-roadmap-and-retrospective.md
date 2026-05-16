# Week 52 — Year Two Roadmap

## Prompt 52.1 — Year Two Research Roadmap

### Guing Principle

Year One built infrastructure. Year Two must produce knowledge. Every research initiative must produce a falsifiable claim supported by empirical evidence by the end of the year.

---

### Area 1: Deeper Causal Reasoning

**Thesis:** Current causal graph construction (import analysis + co-change patterns) is dependency analysis, not causal inference. Year Two must move from "file A imports file B" to "changing file A causes failure in file B with probability P."

**Experiments:**
1. **Interventional causal analysis.** Use git history as natural experiments: when file X changed, what broke? Build causal effect estimates from observational data using do-calculus-inspired methods.
2. **Counterfactual simulation.** Given a change to file A, what would break? Use the dependency graph + invariant catalog to enumerate likely failure modes. Evaluate against real post-deployment incidents.
3. **Causal discovery benchmarking.** Compare Lyme's heuristic graphs against established causal discovery algorithms (PC, FCI, NOTEARS) on synthetic software repositories with known ground-truth causal structures.

**Infrastructure needed:**
- Real incident database (production failures linked to code changes)
- Synthetic repos with known causal structures
- Causal discovery algorithm implementations (can use external libraries)
- Counterfactual query language

**Risks:**
- Causal inference from observational data is fundamentally limited without randomization
- Software causality may be too context-dependent for current methods
- Ground truth is expensive to obtain (requires labeled incident data)

**Expected payoff:** The ability to answer "if we change this, what will break?" with measurable accuracy. This is the single most valuable capability for safe autonomous agents.

---

### Area 2: Stronger Local Agents

**Thesis:** The combination of Lyme's compression pipeline + governance layer + memory system can make 7B-14B local models effective for a defined class of maintenance tasks, even if they cannot match frontier models on complex reasoning.

**Experiments:**
1. **The core experiment (finally).** Compare Qwen 2.5 Coder 7B with and without Lyme's full stack on 8 benchmark scenarios. Primary metric: task success rate. Secondary: token efficiency, error rate, repair attempts.
2. **Compression contribution analysis.** Ablate each compression layer. How much does subsystem clustering help vs. file tree alone? Is invariant discovery worth the compute cost?
3. **Memory decay study.** Run 50+ sequential sessions on the same repo. Measure task success rate over time with and without persistent memory. At what session count does improvement plateau?
4. **Cross-model capability mapping.** Run all 8 scenarios across 5 models (Qwen 7B, CodeLlama 7B, DeepSeek 7B, GPT-4o mini, Claude 3 Haiku). Produce Lyme's first real capability matrix.

**Infrastructure needed:**
- Ollama or llama.cpp integration for model execution
- Automated benchmark runner that drives model API/completion endpoint
- Session persistence across benchmark runs
- Result database for cross-model comparison

**Risks:**
- Local models may perform too poorly to measure meaningful improvement
- Compression may not help (or may hurt) for well-scoped tasks
- Memory may show no measurable effect within 50 sessions

**Expected payoff:** The first empirical answer to Lyme's founding question. Even "local models are not good enough for any task" is a publishable result.

---

### Area 3: Better Software Simulation

**Thesis:** High-quality synthetic repositories with realistic bugs, tests, and architecture can reduce the cost of agent evaluation by 10x while maintaining validity.

**Experiments:**
1. **Synthetic repo fidelity validation.** Generate repos of varying quality (naive random to structured generation) and compare agent performance on synthetic vs. real repos. Find the minimum fidelity needed for valid results.
2. **Bug seeding taxonomy.** Create a taxonomy of realistic bugs (off-by-one, race condition, API misuse, missing null check, etc.) and validate against real-world bug distributions from public datasets (Defects4J, BugsJS).
3. **Difficulty calibration.** Generate repos at 5 difficulty levels. Calibrate against human developer performance and frontier model performance.

**Infrastructure needed:**
- Improved SyntheticRepoGenerator with realistic code generation
- Bug seeding library with configurable difficulty
- Validation framework comparing synthetic vs. real performance
- Integration with Defects4J/SWE-bench datasets

**Risks:**
- Synthetic repos may never match real repo complexity
- Validation requires real agent runs, which this work is supposed to reduce
- Overfitting to synthetic benchmarks

**Expected payoff:** Fast, cheap, reproducible evaluation infrastructure. The ability to run 100 benchmark variants in an hour instead of a week.

---

### Area 4: Safe Autonomy

**Thesis:** Lyme's governance framework, combined with the verification graph, can prevent a measurable class of harmful agent actions while allowing beneficial ones, with acceptable overhead.

**Experiments:**
1. **Governance effectiveness study.** Run 100 agent tasks with and without governance. Measure: prevented harmful actions (true positives), blocked beneficial actions (false positives), overhead (time added), bypass attempts.
2. **Constitution generation quality.** Can a repo constitution be auto-generated from the compression pipeline (subsystem graph + invariants + risk zones) with sufficient accuracy? Compare auto-generated vs. expert-written constitutions.
3. **Adversarial robustness.** Can a user prompt bypass the governance engine? Red-team the system with 50 adversarial prompts targeting each default policy.

**Infrastructure needed:**
- Real agent integration (adversarial prompts, agent execution)
- Ground truth dataset of harmful vs. beneficial actions
- Adversarial prompt library
- Overhead measurement instrumentation

**Risks:**
- Governance may be trivially bypassable by adversarial prompts
- False positive rate may be unacceptable (>5% blocks beneficial actions)
- Governance overhead may be too high for practical use

**Expected payoff:** The first empirical validation of governance-as-code for coding agents. A publishable safety result and a product differentiator.

---

### Area 5: Ecosystem Intelligence

**Thesis:** Cross-repository pattern mining can discover software engineering best practices, common failure modes, and architecture evolution patterns that generalize beyond individual projects.

**Experiments:**
1. **Large-scale invariant mining.** Mine invariants from 100+ public repositories. How many invariants are project-specific vs. universal? What are the most common violated invariants?
2. **Failure pattern transfer.** Do failure patterns learned from one project predict failures in another? Build cross-project failure classifiers.
3. **Evolution archetypes.** Cluster repositories by evolution trajectory (steady growth, punctuated refactoring, architectural rewrite, etc.). Can evolution archetype predict maintenance burden?

**Infrastructure needed:**
- Repository acquisition pipeline (clone 100+ repos from GitHub)
- Distributed invariant mining (each repo analyzed independently)
- Cross-repo pattern clustering
- Evolution trajectory time-series analysis

**Risks:**
- Pattern mining may produce trivial findings (most repos have tests, large files change more)
- Cross-project generalization may be weak
- Compute cost of mining 100+ repos

**Expected payoff:** Empirical evidence for universal software engineering patterns. Lyme transforms from "tool for one repo" to "source of knowledge about all repos."

---

### Area 6: Benchmark Leadership

**Thesis:** Lyme's cognition benchmark (8 dimensions × 16 tasks) can become a standard evaluation for coding agent cognition, complementing SWE-bench's task-completion focus with cognitive process measurement.

**Experiments:**
1. **Cognition benchmark implementation.** Implement all 16 cognition benchmark tasks. Run across 3+ models. Publish first leaderboard.
2. **Benchmark validity study.** Do cognition benchmark scores correlate with human developer task performance? With SWE-bench scores? With production incident rates?
3. **Anti-gaming evaluation.** Test whether models can "game" the cognition benchmark by producing plausible traces without actual reasoning. Iterate anti-gaming rules.

**Infrastructure needed:**
- 16 task implementations (major implementation effort)
- Model execution integration
- Leaderboard database and visualization
- Anti-gaming validation suite

**Risks:**
- 16 tasks is a massive implementation effort
- Cognition measurement may not correlate with any meaningful outcome
- Models may game the benchmark regardless of anti-gaming rules

**Expected payoff:** A recognized evaluation standard. Lyme becomes a name in agent evaluation, opening doors for academic collaboration and adoption.

---

### Area 7: Standardization

**Thesis:** Open standards for agent traces (OATS) and semantic diffs (SDS) can achieve adoption if they solve a real interoperability problem.

**Experiments:**
1. **Cross-framework trace conversion.** Build importers/exporters for LangSmith traces, OpenAI trace format, and Claude Code sessions. Can OATS represent all of these faithfully?
2. **Standard usefulness study.** Do OATS traces enable failure analysis that raw logs do not? Survey/task 5 developers comparing OATS traces vs. plain text logs for debugging.
3. **Standard evolution.** Based on conversion and usefulness studies, revise OATS v0.7.0 → OATS v1.0.

**Infrastructure needed:**
- LangSmith API client
- OpenAI trace format parser
- Claude Code session parser
- Conversion validation test suite

**Risks:**
- Standards may not achieve adoption regardless of quality
- Cross-framework representation may be lossy
- Incumbent formats (OpenTelemetry) may subsume agent tracing

**Expected payoff:** Portable agent behavior. The foundation for an ecosystem of interoperable agent tools.

---

### Area 8: Human-Agent Collaboration

**Thesis:** The most effective deployment of coding agents is not autonomous operation but structured human-agent collaboration, where Lyme provides the governance and measurement layer.

**Experiments:**
1. **Collaboration workflow study.** Compare three conditions: agent-only, human-only, human+agent with Lyme governance. Measure: task completion, quality, time, user satisfaction.
2. **Trust calibration study.** Do Lyme's confidence scores and evidence citations improve user trust calibration? Measure: user overtrust/overtrust with and without Lyme's transparency features.
3. **Intervention effectiveness.** When Lyme flags a governance policy violation and presents evidence, do users make better decisions? Measure: decision quality with vs. without governance flag.

**Infrastructure needed:**
- User study platform (web-based task interface)
- Governance intervention UI
- Trust measurement instruments
- Decision quality scoring rubric

**Risks:**
- User studies require IRB approval and significant time
- Effect sizes may be small with small sample sizes
- Lab studies may not generalize to production settings

**Expected payoff:** Evidence-based design principles for human-agent collaboration. Lyme provides not just measurement infrastructure but empirically validated collaboration patterns.

---

### Year Two Research Milestones

| Quarter | Deliverable | Experiment |
|---|---|---|
| Q1 (v0.8) | First real local model benchmark results | Core hypothesis experiment (8 scenarios × 3 local models) |
| Q1 | Governance effectiveness study | 100-task governance evaluation |
| Q2 (v0.9) | Compression contribution analysis | Layer-by-layer ablation on 3 scenarios |
| Q2 | Cross-model capability matrix | 5 models × 8 scenarios × 5 runs |
| Q2 | Cognition benchmark v1 (8 tasks) | First 8 of 16 tasks implemented |
| Q3 (v1.0) | Memory decay curves | 50-session longitudinal study |
| Q3 | OATS adoption validation | Cross-framework conversion + user study |
| Q3 | Causal graph accuracy evaluation | Counterfactual prediction vs. real incidents |
| Q4 | Full cognition benchmark results | 16 tasks × 5 models |
| Q4 | Cross-repo invariant study | 100+ repos mined, patterns published |
| Q4 | Human-agent collaboration study | Multi-condition user study |
| Q4 | Published research paper | Systems venue (OSDI, ATC, EuroSys) |

---

## Prompt 52.2 — Year Two Product Roadmap

### Product Vision

Lyme becomes the governance and measurement layer for the AI-assisted software development lifecycle. Developers use it to maintain codebases safely; teams use it to enforce policies across agent interactions; organizations use it to measure and improve agent effectiveness.

### v1.0 Core (Target: Month 12 of Year Two)

**Target:** A stable, well-documented CLI tool that provides real value to developers.

**Features:**
- 12 core commands (pruned from 30+): doctor, ask, diff, fix, history, audit, undo, memory, govern, verify, bench, analyze
- Real agent integration (Ollama, with OpenAI-compatible API fallback)
- Governance engine with real policy evaluation
- Verification graph with real test results
- Memory system with real session persistence
- Compression pipeline cached and incremental

**Success criteria:**
- Installs via pip without compilation
- `lyme doctor` works on any Python project in <5 seconds
- `lyme govern evaluate` produces correct decisions on a validation set of 100 scenarios
- All simulated data replaced with real measurements
- Zero crashes on 1000+ repository runs

**Non-goals:**
- Multi-agent support
- Dashboard UI (static HTML is sufficient)
- Enterprise features
- Full research platform

---

### GitHub/CI Integration (Target: Month 3-4)

**Target:** Lyme governance runs in CI pipelines.

**Features:**
- GitHub Action: `lyme ci` runs governance checks on PRs
- GitLab CI template equivalent
- Policy violation comments on PRs
- Governance badge for README
- Check run status: pass/fail/warn based on policy violations

**Success criteria:**
- Action published on GitHub Marketplace
- 5 external repositories using it
- 95%+ uptime for the CI integration

---

### IDE Integration (Target: Month 5-6)

**Target:** Lyme diagnostics appear in the editor.

**Features:**
- LSP server implementation
- VSCode extension:
  - Inline diagnostics from `lyme doctor`
  - Governance policy warnings during editing
  - One-click `lyme fix` application
  - Hover for evidence citations from `lyme ask`
- JetBrains plugin (if VSCode extension shows traction)

**Success criteria:**
- 100+ VSCode extension installations
- 4.0+ star rating
- Positive user feedback on utility

---

### Observatory UI (Target: Month 6-8)

**Target:** A real dashboard, not static HTML generation.

**Features:**
- Web application (FastAPI + React/Svelte)
- Real-time trace viewing
- Governance policy dashboard
- Benchmark result browser
- Memory browser
- Cross-repository view (for multi-repo users)

**Success criteria:**
- Can open in browser and interact
- Loads in <2 seconds
- Supports multiple concurrent users
- All CLI data visible in UI

---

### Enterprise Governance (Target: Month 8-10)

**Target:** Features needed for organizational adoption.

**Features:**
- Centralized governance policy management (policy CRUD, versioning)
- Team-based policy assignment
- Compliance reports (PDF/CSV export)
- Audit log aggregation across repositories
- Role-based access control (admin, reviewer, developer, auditor)
- SSO/SAML integration
- Self-hosted deployment option

**Success criteria:**
- 3 organizations using enterprise features
- Audit log completeness validated by external auditor
- Policy deployment success rate >99%

---

### Research Portal (Target: Month 8-10)

**Target:** Public access to Lyme's empirical results.

**Features:**
- Live benchmark leaderboard
- Cognition benchmark results (when available)
- Published research papers
- Public dataset downloads (anonymized traces, benchmarks)
- Experiment replication service

**Success criteria:**
- 100+ unique visitors/month
- 3+ external researchers using datasets
- 2+ reproductions of Lyme experiments by external groups

---

### Community Ecosystem (Target: Month 10-12)

**Target:** Lyme has an active contributorbase.

**Features:**
- Community scenario contributions (10+ from external)
- Community model adapter contributions (3+ from external)
- Community governance policy library
- Community compression strategies
- RFC process for significant changes
- Regular contribution recognition

**Success criteria:**
- 10+ external contributors
- 3+ community members on maintainer track
- 100+ GitHub stars
- 50+ closed issues (25 from community)

---

### Quarterly Milestones

```
Q1 (v0.8): Governance Beta
├── Real local model benchmark results published
├── GitHub Action for CI governance
├── CLI pruned to 12 core commands
├── All simulated data removed from default output
└── First community contribution (scenario)

Q2 (v0.9): IDE + Benchmarks
├── VSCode extension published
├── Cross-model capability matrix (5 models)
├── 8 cognition benchmark tasks implemented
├── Compression cached and incremental
└── 5 community scenarios

Q3 (v1.0-RC): Observatory + Standards
├── Web application (interactive dashboard)
├── OATS v1.0 (revised from adoption feedback)
├── Memory decay results from longitudinal study
├── Governance effectiveness study published
└── 10+ community contributors

Q4 (v1.0): Production + Research
├── Enterprise governance features
├── Research portal with leaderboards
├── Human-agent collaboration study published
├── Conference paper submission
└── 100+ GitHub stars, active contributorbase
```

---

## Prompt 52.3 — The Final One-Year Retrospective

---

# Lyme: One-Year Retrospective

**Date:** End of Year One
**Author:** Internal project review

---

### What Was Lyme Supposed to Be?

Lyme was supposed to be a research platform for studying coding agents scientifically. It would provide:

- **For researchers:** Reproducible benchmarks, structured cognitive traces, causal analysis, invariant discovery, scaling laws — the infrastructure to understand how coding agents think, fail, and improve.
- **For developers:** Useful tools (diagnosis, Q&A, safe editing, audit) that double as data generators for the research layer.
- **For the field:** Open standards for agent behavior, shared vocabularies for failure, and the first longitudinal studies of agent improvement.

The founding hypothesis was bold: *Local models on consumer hardware, augmented by the right architecture (compression, memory, tool routing, governance), can become useful coding agents.*

---

### What Did It Become?

Lyme became a large, internally consistent codebase of 66+ modules spanning:

- A dual architecture with product and research layers
- A 5-layer compression pipeline for codebase understanding
- A 3-type memory system with persistence and retrieval
- A 15-thought-type cognitive tracing framework
- A causal graph engine with failure propagation
- An invariant discovery engine with violation detection
- A governance engine with 5 decision levels and 13 policies
- A verification graph with 43 evidence types and 14 gap labels
- 8 benchmark scenarios with full evaluation infrastructure
- 3 open standards with examples and validation
- A comprehensive failure taxonomy with 14 categories
- A research framework with intelligence dimensions and experiment generators

And zero validated claims.

Lyme became infrastructure without evidence. A research platform that has conducted no research. A measurement system that has measured nothing.

---

### What Did We Learn?

**1. Building infrastructure is easier than doing science.**

The project allocated approximately 90% of effort to system building and 10% to experimentation. The default trajectory of a technical project is "build more things." Running experiments requires: forming hypotheses, designing protocols, executing measurements, analyzing results, handling negative findings. Each step is harder than writing code. Each step was deferred.

**2. Simulated data is dangerous.**

The demo scripts that generate realistic-looking benchmark results were the project's most consequential design mistake. They gave the appearance of progress without its substance. They made it possible to ship "results" that were actually random numbers. They satisfied the engineering desire for "output" without satisfying the scientific requirement for "evidence."

**3. Scope creep is a symptom of uncertainty avoidance.**

Every new module (civilization maps, genome extraction, self-improving agents, market coordination) was a new thing to build, which meant avoiding the question of whether existing things worked. The expansion from v0.1 through v0.7 added scope faster than validation could catch up. The result is a wide but shallow project.

**4. No user feedback means no reality check.**

Without users, there was no external forcing function for prioritization. Every feature seemed equally important because nobody was asking for any of them. The project optimized for internal consistency (does the code work?) instead of external validation (does anyone need this?).

**5. The central hypothesis is still open.**

After one year, we cannot answer the question that motivated the project. This is the single most important finding: Lyme's infrastructure is complete enough to test its founding hypothesis, but the test was never conducted.

---

### What Surprised Us?

**1. How far you can get with heuristics.**

Lyme contains zero trained ML models. Everything — compression, memory retrieval, invariant discovery, failure detection, governance evaluation — is implemented with pattern matching, keyword search, threshold-based detection, and rule evaluation. The system works (in the sense of producing plausible output) without any learned component. This was not by design, but it is revealing.

**2. How much infrastructure a single developer can build.**

66 modules. ~1200 lines in the CLI entry point alone. 2500+ line CLI implementation. Full governance system. Compression pipeline. 8 benchmarks. 3 standards. A failure taxonomy. A research framework. All by one person. The infrastructure is genuinely impressive. The gap is not in code quantity.

**3. How easy it is to avoid the hard question.**

Every release plan mentioned the core hypothesis. Every demo presented "results." Every README made claims. And yet the experiment was never scheduled, never prioritized, never executed. The question was always "next week." For 52 weeks.

**4. How the manifesto was more honest than the code.**

The MANIFESTO.md says things like "this is a research project" and "we do not know which abstractions will survive contact with real research." The codebase's claim structure (simulated results presented as findings) contradicts the manifesto's intellectual honesty. The manifesto knew what it was talking about. The codebase did not listen.

---

### What Failed?

**1. The experiment never ran.** This is the head failure from which all others follow.

**2. No external engagement.** A research project with no collaborators, no reviewers, no users, no community. This is not research. It is engineering with research aspirations.

**3. Simulated results presented as findings.** The benchmark leaderboard, ablation studies, and capability matrix contain simulated data that is visually indistinguishable from real results. This is misleading and must be corrected.

**4. Scope without focus.** 30+ CLI commands, 66+ modules, 14 failure categories, 8 benchmark scenarios, 3 standards, 10 intelligence dimensions, 5 governance levels, 13 policies, 43 evidence types, 14 gap labels. The system is comprehensive and incomprehensible.

**5. No real agent connection.** The platform designed for agents never talked to one.

**6. No longitudinal data.** A hypothesis about improvement over time was tested at time zero only.

**7. Overbuilt features.** Civilization maps, genome extraction, market coordination, architecture advisor, self-improving agents — built, not validated, and likely wrong.

---

### What Deserves Another Year?

**1. The governance system.** This is the most novel and differentiated component. Governance-as-code for coding agents does not exist elsewhere. The design is sound. It needs testing, not rebuilding.

**2. The compression pipeline.** The 5-layer architecture encodes a real hypothesis about software comprehension. It needs evaluation: does compression help agents, and by how much?

**3. The benchmark scenarios.** Well-designed, varied, and ready for real execution. They need agent integration, not redesign.

**4. The open standards.** OATS and SDS are well-specified. They need adoption, which requires community engagement, which requires publishing and outreach.

**5. The core hypothesis.** It was the reason for starting. It deserves an answer. Even a negative answer is publishable.

---

### What Should Be Killed?

**1. Software civilization maps.** No clear path to utility.

**2. Self-improving agents (workflow/prompt evolution).** Simulated evolution with no validation mechanism.

**3. Autonomous maintenance loop.** Dangerous pattern (trust the simulation) without governance validation.

**4. Architecture advisor.** Opinion engine labeled as analysis.

**5. Ecosystem risk forecasting.** Duplicates existing tools.

**6. Repository genome (prediction features).** Keep basic fingerprinting; remove maintainability/fragility/scaling predictions.

**7. Multi-agent society (simulated experiments).** Keep only if connected to real models. Remove random-based simulations.

---

### What Would Make Lyme Field-Changing?

**One experiment.** Run the core hypothesis test: compare a 7B model with Lyme's full stack against a raw 70B model on real multi-file editing tasks. If Lyme-enhanced 7B achieves ≥80% of 70B performance, the result is field-changing. If it achieves 50%, that is still a publishable result with clear implications for architecture design. If it achieves 30%, that tells us compression is not a substitute for scale, which is also important knowledge.

**The experiment is the product.** Lyme does not need more features, more modules, more standards, or more documentation. It needs one controlled experiment with real models, real agents, and real tasks. The result, whether positive or negative, is worth more than all the infrastructure built in Year One.

**Second-order effects of running the experiment:**
- Forces agent integration (necessary regardless of outcome)
- Produces the first honest benchmark results
- Creates a reproducibility checkpoint
- Generates the first real trace data
- Enables the first real failure analysis
- Produces the first real longitudinal baseline
- Creates credibility for open standards

**Third-order effects:**
- Research paper (even with null results)
- Community interest from reproducible findings
- Governance testing becomes possible
- Real data drives real improvement

---

### The Clearest Possible Next Move

**Stop building infrastructure. Run the core experiment.**

1. **Week 1:** Set up Ollama with Qwen 2.5 Coder 7B. Write a script that calls its completion API with a benchmark task prompt and evaluates the output.

2. **Week 2:** Run all 8 benchmark scenarios with the raw 7B model. Record task success rate, latency, token usage, error rate. This is the baseline.

3. **Week 3:** Integrate the compression pipeline: for each scenario, compress the repository, build the rehydration packet, feed it to the model instead of raw files. Run all 8 scenarios again.

4. **Week 4:** Add memory: run 5 sequential sessions per scenario, enabling persistent memory. Measure improvement across sessions.

5. **Week 5:** Add governance: enable governance evaluation. Measure overhead and false positive/negative rates.

6. **Week 6:** Compare results against a frontier API model (GPT-4o mini) on the same tasks.

7. **Week 7:** Write up results. Publish. This is the paper, the blog post, the Hacker News post, the repository README update, and the direction for Year Two.

**After the experiment, Lyme either has evidence or it doesn't. Either way, the project is honest for the first time.**

---

### Final Scorecard

| Year One Goal | Status |
|---|---|
| Research infrastructure for coding agent science | Built but unused |
| Local-first, private, reproducible agent measurement | Infrastructure exists, measurement absent |
| Open standards for agent behavior | OATS and SDS defined |
| Governance layer for safe autonomy | Built, unevaluated |
| Compression pipeline demonstration | Built, unevaluated |
| Memory system for persistent improvement | Built, unevaluated |
| Published research | None |
| Community adoption | None |
| Core hypothesis tested | Not tested |
| Empirical validation of ANY claim | None |

The infrastructure is a 9/10. The science is a 0/10. Year Two must invert this ratio.
