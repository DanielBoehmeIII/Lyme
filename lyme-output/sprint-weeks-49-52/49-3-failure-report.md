# Failure Report

**Date:** End of Year One
**Project:** Lyme
**Purpose:** Intellectual honesty. This is not a marketing document.

---

## What Did Not Work

### 1. Lyme Did Not Connect to Real Agents

The single most important failure. Lyme has model adapters, a benchmark engine, cognitive tracing, memory stores, a compression pipeline, a tool router, governance, verification, and open standards — and has never connected any of it to a real running agent. No Claude Code session was traced. No CodeLlama benchmark was run. No GPT-4 comparison was made. The entire measurement infrastructure exists in a vacuum.

This is not a technical failure. The infrastructure is ready. It is a priority failure — the work of integration was deferred, and the deferral became permanent.

### 2. The Central Hypothesis Was Not Tested

"Can local models on consumer hardware become useful coding agents through better memory, compression, tool use, telemetry, and governance?"

**One year later, the answer is: we don't know.**

The hypothesis was stated in the README, the manifesto, the positioning, and every release plan. The infrastructure to test it was built. The experiment was never run. This is not a failure of engineering. It is a failure of scientific execution.

### 3. Benchmarks Run on Synthetic Data Only

All 8 benchmark scenarios produce results. All results are from simulated execution. The cognition benchmark specifies 16 tasks; zero are implemented. The leaderboard has simulated scores. The ablation studies report simulated deltas. The scaling laws are theoretical.

This gives the appearance of measurement without the substance. A reader of the output would reasonably conclude that Lyme runs benchmarks and produces results. Both statements are technically true and scientifically meaningless.

### 4. The Research Platform Has No Research

Despite having a research framework, experiment generator, ablation engine, and report generator, Lyme has produced zero research outputs:
- Zero papers
- Zero preprints
- Zero conference submissions
- Zero blog posts with empirical results
- Zero public datasets
- Zero reproduced results from other systems

The infrastructure for research is complete. The research itself is absent.

### 5. No External Users

Lyme was designed for developers, researchers, and organizations studying coding agents. It has been used by exactly one person (the developer). All assumptions about user needs, pain points, workflows, and failure modes are untested guesses. The failure taxonomy, CLI design, command set, and output formats were designed for an audience that never materialized.

---

## What Was Overbuilt

### 1. Software Civilization Maps

`lyme civ-map generate` produces a "software civilization map" — a knowledge-base-driven ecosystem visualization of the software landscape. This is built on hardcoded knowledge about frameworks, languages, and ecosystems. It generates an HTML visualization. It serves no clearly identified user need and contributes nothing to the core hypothesis. Estimated effort: multiple weeks.

**Recommendation:** Kill or demote to tutorial-only.

### 2. Repository Genome

The genome extraction system creates a "DNA profile" of a repository — compact genome strings, locus-level comparison, genome clustering, maintainability prediction, fragility prediction, scaling prediction, evolution path prediction. This is a clever metaphor applied to a problem (compare repositories) that has simpler solutions. The predictions are uncalibrated. Estimated effort: several weeks.

**Recommendation:** Simplify to basic clustering. Remove prediction features.

### 3. Software Evolution Metrics Engine

A 14-metric observation engine measuring repository evolution across coupling, cohesion, stability, entropy, and complexity. Each metric has definitions, normalized values, trend detection, and anomaly flags. This is genuinely impressive engineering — and it has never been validated against any real measure of software quality or team productivity.

**Recommendation:** Keep the metrics, validate against real outcomes, or reduce to 3-5 most predictive metrics.

### 4. Architecture Advisor

`lyme arch suggest` takes scale, team size, latency sensitivity, and reliability requirements and suggests an architecture pattern (microservices, modular monolith, etc.). This is expert-system-style advice from one developer's opinions encoded as rules. It is not evidence-based.

**Recommendation:** Remove or label explicitly as "unvalidated opinion."

### 5. Ecosystem Dependency Modeling

The ecosystem module models Python, JavaScript, and Rust dependency graphs with compatibility analysis, security advisory tracking, migration planning, and vulnerability propagation. It queries hardcoded knowledge about ecosystems. This duplicates the functionality of `pip-audit`, `npm audit`, `cargo audit`, `dependabot`, and `snyk` — all of which are better maintained and more accurate.

**Recommendation:** Replace with adapter wrappers around existing tools.

### 6. Multi-Agent Society Simulation

Debate engine, specialization emergence, coordination topology experiments, collective memory, market coordination — all simulated with random outcomes. The specialization engine runs 20 agents through 200 tasks and reports "specialization levels" that are entirely determined by random number generator seed. The numbers look scientific. They are not.

**Recommendation:** Either connect to real models or document clearly as prototype simulations with no empirical basis.

---

## What Was Scientifically Weak

### 1. Claimed Accuracy Without Measurement

Multiple places in the codebase and documentation claim specific accuracy numbers:
- ">80% accuracy" for failure classification
- ">90% precision" for semantic diff classification
- "<20% accuracy drop" for cross-model transfer

None of these numbers come from experiments. They are targets, not results. Presenting them in the present tense is misleading.

### 2. Failure Propagation as Causal Inference

The causal graph engine builds graphs where an edge means "file A affects file B" based on import relationships and co-change patterns. This is not causal inference. It is dependency analysis relabeled as causation. The failure propagator assumes cascade effects propagate linearly through the graph, ignoring feedback, buffering, dampening, and context dependence.

### 3. Simulated Results Masquerading as Measurements

The v0.7 demo produces a benchmark leaderboard with scores like "lyme-agent-v0.7: 0.812 overall, 14/16 tasks." These are simulated numbers. The demo script generates them. They are indistinguishable from real results unless you read the source code. This is the most dangerous pattern in the project — the appearance of empirical validation where none exists.

### 4. Scaling Laws Without Data

The scaling law framework defines experiment designs, variable types, and reporting formats. It has produced zero data points. The research question "Do semantic diffs correlate with post-merge bug rates?" is listed as "OPEN." It was never investigated.

---

## What Was Too Speculative

### 1. "Software Cognition" Framework

Ten intelligence dimensions (abstraction formation, causal reasoning, temporal reasoning, invariant preservation, repair ability, architectural prediction, uncertainty estimation, coordination efficiency, memory compression, intent modeling) are defined with rigorous-sounding language. They are not operationalized. There are no measurement instruments for any dimension. The framework is a taxonomy, not a science.

### 2. Self-Improving Agents

The workflow evolution engine, prompt evolution engine, and cognitive architecture search modules generate evolutionary variations of agent workflows and prompts. They work on the level of JSON manipulation — they generate new workflow step sequences and prompt genomes. There is no evaluation of whether the evolved variants improve anything. "Self-improving" in the module name implies a capability that was never demonstrated.

### 3. Autonomous Maintenance Loop

`lyme maintain` runs an autonomous maintenance loop that detects issues, generates tasks, executes them, and reports statistics. The detection is heuristic. The execution is simulated. The loop runs autonomously on no real validation. The concept is compelling. The implementation is a demo.

### 4. Software Intent Modeling

`lyme intent infer` produces a "software intent model" that purports to understand a repository's philosophy, subsystem purposes, constraints, tradeoffs, and evolution. This is a template-based text generation system fed by AST analysis. It does not model intent in any meaningful sense. The output reads as plausible but is not falsifiable.

---

## What Users Did Not Need

**This section is speculative because there are no users. The following is inferred from the gap between the feature set and any plausible user workflow.**

### 1. 30+ CLI Commands

No single user needs 30 commands. The CLI surface is too large. Commands like `civ-map`, `fw-obs`, `tradeoff`, and `genome` serve no clear user need that isn't already met by simpler tools.

### 2. The Plugin System

Plugins are registered via a registry pattern. No third-party plugin was ever written. The system adds complexity (lifetime hooks, experiment plugins, telemetry sinks) that no user has encountered.

### 3. The Research Portal

Static JSON files pretending to be a web portal. Users who want a research portal want an interactive web application with search, filtering, and visualization. This is a placeholder.

### 4. Contribution Protocol

11 contribution types, a review workflow, and a submission format — all defined before a single external contribution was received. Process without community.

---

## What Agents Still Cannot Do

### 1. Reliably Refactor Across Multiple Files

The `multi-file-edit-consistency` benchmark scenario exists precisely because agents fail at this. They update some callers but miss others, change function signatures without updating all references, or break invariants across file boundaries. No architecture has solved this reliably, and Lyme has not measured the failure rate.

### 2. Maintain Context Across Long Sessions

Context degradation is documented. The "lost in the middle" problem is known. Agents still cannot maintain coherent understanding over 100+ turn sessions on large codebases. Lyme's context budget optimizer is a proposed solution that was never evaluated.

### 3. Learn From Mistakes

Without persistent memory that works, agents repeat the same errors. The memory system exists but was never proven to reduce error repetition. The fundamental problem — an agent that makes a mistake in session 1 and repeats it in session 10 — remains unsolved.

### 4. Self-Correct Without Human Intervention

All governance levels above AUTO_APPLY require human review. The "safe autonomy" that the governance system enables is autonomy within guardrails, not autonomous improvement. Agents cannot identify their own failures, diagnose root causes, and implement corrective measures without human oversight.

### 5. Understand Architecture, Not Just Code

Agents read code line by line. They do not form architectural mental models. The compression pipeline attempts to provide a structured representation, but the agent still processes it as text. No agent has demonstrated the ability to reason about software architecture at the level of invariants, design patterns, or tradeoffs.

---

## What Local Models Still Cannot Handle

### 1. Repos Larger Than ~10K Files

At current context windows (128K-200K tokens for local models), a comprehensive view of a large repository is impossible. The compression pipeline reduces the representation but still produces outputs that exceed context limits. 7B models specifically struggle with instruction following beyond ~8K tokens of context.

### 2. Complex Causal Reasoning

"Why did this change break that unrelated feature?" requires tracing chains of effects through layers of abstraction. Local models (7B-14B) consistently fail at multi-step causal inference tasks. The causal graph system attempts to offload this reasoning to a static analysis layer, but this was never tested.

### 3. Novel Vulnerability Discovery

Agents can find known vulnerability patterns (SQL injection, XSS) but cannot discover novel vulnerability classes. Local models lack the reasoning depth to generalize from "this pattern is dangerous" to "this conceptually similar but syntactically different pattern is also dangerous."

### 4. Long-Horizon Task Planning

Tasks requiring 50+ steps with dependencies, conditionals, and rollback scenarios are beyond the planning capability of current local models. The architecture-aware planner improves this at the prompt level but does not change model capability.

### 5. Reliable Test Generation

Generating tests that actually validate behavior (rather than just execute without failing) requires understanding intent, not just structure. Local models produce high-coverage-but-low-value test suites. This is a known limitation that Lyme does not address.

---

## What Should Be Killed or Simplified

### Kill (Remove Entirely)

| Feature | Reason |
|---|---|
| Software Civilization Maps | Overbuilt, no user, no validation path |
| Autonomous Maintenance Loop | Simulated, unsafe, pretends to work |
| Self-Improving Agents (workflow/prompt evolution) | Simulated evolution, no validation |
| Software Intent Modeling | Not falsifiable, not useful |
| Contribution Protocol | Process without community |
| Ecosystem Risk Forecasting | Duplicates existing tools, unvalidated |
| Architecture Advisor | Opinion engine, not evidence-based |

### Simplify (Reduce Scope)

| Feature | Simplification |
|---|---|
| Repository Genome | Keep basic fingerprinting, remove prediction/evolution |
| Evolution Metrics | Keep 3-5 validated metrics, remove remaining 9 |
| Multi-Agent Society | Remove simulated experiments. Keep only if connected to real models. |
| Research Framework | Keep dimensions taxonomy, remove experiment/ablation/report generators until there's actual data |
| Plugin System | Keep registry, remove plugin lifecycle hooks until there are plugins |
| CLI Surface | Reduce from 30+ to 10-12 core commands. Move advanced to `--advanced` flag or separate script. |

### Keep But Make Honest

| Feature | Honest Positioning |
|---|---|
| Compression Pipeline | "Algorithmic codebase compression. Unvalidated against model performance." |
| Memory Store | "JSON-backed memory storage. Keyword retrieval. Unmeasured impact." |
| Governance System | "Rule-based governance. No production testing. Verified audit trail." |
| Benchmark Engine | "Scenario framework. Runs synthetic tasks. No real agent integration yet." |
| Causal Graph | "Dependency analysis visualized as causal graph. Not validated causal inference." |
| Cognitive Tracing | "Thought recording format and analyzer. No failure classification accuracy data." |

---

## Summary: What We Actually Built vs. What We Claimed

| Claimed | Actually Built |
|---|---|
| Research platform for coding agent science | Infrastructure for coding agent science, awaiting experiments |
| Local-first agent improvement system | Developer tools + research scaffolding, never connected to agents |
| Measurable improvement through compression/memory | Compression and memory exist, impact unmeasured |
| >80% failure classification | Failure taxonomy + cognitive traces, never integrated |
| >90% semantic diff precision | Semantic diff system, never evaluated against ground truth |
| Scaling laws for coding agents | Scaling law experiment framework, zero empirical results |
| Cross-model anomaly transfer | Anomaly detector, no cross-model experiment |
| Longitudinal agent improvement | Evaluation framework, zero longitudinal datasets |
| Safe autonomous agents | Governance system, never tested with real agent actions |

The gap between what was claimed and what was built is the project's defining failure. The infrastructure is impressive. The science is absent.
