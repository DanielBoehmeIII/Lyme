# Lyme Technical Thesis

## What Lyme Proved

### 1. A Dual Architecture (Product + Research) Is Viable

Lyme demonstrated that the same infrastructure can simultaneously serve as a useful developer tool and a research platform. Every `lyme doctor` diagnosis, `lyme ask` response, and `lyme diff` classification generates structured research data — cognitive traces, causal graphs, invariant catalogs — without additional effort from the user. This dual-use architecture is not a marketing distinction; it is a concrete design decision reflected in the privacy boundary, the telemetry substrate, and the storage format. It works.

### 2. Compression Pipelines for Codebase Understanding Are Buildable at Consumer Hardware

The 5-layer compression pipeline — file tree, API surface, subsystem clustering, invariant discovery, task-aware rehydration — was fully implemented and runs on any Python environment. It processes repositories of moderate size (hundreds to low thousands of files) within seconds. The layers compose: each layer depends on the previous, and the rehydration layer can produce task-specific context packets that are significantly smaller than the raw codebase.

### 3. A Comprehensive Failure Taxonomy Is Implementable

Fourteen failure categories — from INCOMPLETE_FIX to HALLUCINATED_API to RESOURCE_EXHAUSTION — were defined, implemented, and integrated into the CLI. Every command can produce structured failure records. The taxonomy is complete enough to classify any observed agent failure mode.

### 4. Cognitive Tracing at Scale Is Practical

The 15-thought-type cognitive tracing system records decision points, branches, confidence scores, and exploration patterns. It produces replayable traces. The thought analyzer can detect confidence volatility, decision loops, and abandonment patterns. This proves that structured cognition logging does not require model access — it only requires disciplined instrumentation of the agent loop.

### 5. Governance-as-Code Is Buildable

The v0.6 governance system — 5 decision levels, 13 default policies, risk scoring, repo constitutions, autonomous change ledgers, and verification graphs — demonstrates that machine-readable governance for autonomous agents is implementable as pure Python with zero external dependencies. The verification graph connecting claims → changes → tests → traces → approvals is a novel contribution.

### 6. Open Standards for Agent Behavior Are Definable

The Open Agent Trace Standard (OATS), Semantic Diff Standard (SDS), and Software Cognition Benchmark Specification are concrete, usable formats for making agent behavior portable and comparable. They are versioned, validated, and exemplified with real traces.

### 7. The System Is Testable

60+ tests across governance, verification, standards, epistemology, cross-repo analysis, ecosystem modeling, and hardening demonstrate that a research platform can maintain engineering rigor.

---

## What Lyme Failed to Prove

### 1. The Central Hypothesis Is Untested

Lyme's core claim — "A 7B model with Lyme's compression pipeline matches a 70B model using raw context" — was never empirically tested. The compression pipeline exists. The benchmark scenarios exist. The evaluation framework exists. But no controlled experiment was conducted comparing compressed small-model performance against raw large-model performance on any real task. **This is the single most important unfinished work.**

### 2. Persistent Memory Improves Over Time

The memory store (procedural/episodic/semantic, importance scoring, decay, pruning) is fully implemented but never evaluated across 100+ sessions. The longitudinal evaluation framework uses simulated data. No real agent accumulated enough sessions on a real codebase to measure the hypothesized improvement.

### 3. Context Budget Optimization Prevents Degradation

The ContextBudgetOptimizer scores files by relevance and allocates token budgets. But the "context collapse threshold" — the point where naive retrieval fails — was never measured. The stress experiment generates synthetic repos but does not compare optimized vs. naive retrieval across growing repository sizes.

### 4. Cognitive Tracing Enables >80% Failure Classification

The 14-category failure taxonomy and the cognitive tracing system exist independently. They were never integrated to measure whether structured traces enable automated failure classification at any accuracy threshold. The claim of >80% accuracy is aspirational.

### 5. Anomaly Detection Generalizes Across Model Families

No cross-model transfer experiment was conducted. The anomaly detector works on synthetic data. There is zero evidence that failure patterns learned from one model transfer to another.

### 6. Semantic Diff Classification Achieves >90% Precision

The semantic diff system classifies diffs into categories using AST/language analysis, but the >90% precision claim is untested against a labeled ground-truth dataset. No such dataset was created.

### 7. Multi-Agent Coordination Overhead Has a Measurable Inflection Point

The society simulation system runs multi-agent experiments using simulated (not real) agents. The coordination compressor, topology experiments, and market coordination engine all produce numbers, but these are simulation outputs, not measurements of real agent behavior.

---

## What Local Models Can Realistically Do

Based on the system design and available evidence (not direct measurement):

| Capability | Assessment |
|---|---|
| Repository diagnosis | Achievable. Static analysis + heuristic rules work at 7B scale. |
| Evidence-grounded Q&A | Achievable for well-scoped questions with file-cited evidence. |
| Semantic diff classification | Achievable via AST analysis independent of model size. |
| Safe edits | Achievable. The protocol (explain → patch → rollback) is model-independent. |
| Codebase compression | Achievable. Pure algorithmic (AST, graph, heuristic). |
| Simple multi-file refactoring | Plausibly achievable with good compression and tool support. |
| Complex causal reasoning | Probably not at 7B. Requires reasoning about indirect effects. |
| Invariant discovery from git history | Achievable up to pattern matching (co-change, duplication). |
| Failure detection | Achievable for known patterns. Unknown failures require larger models. |
| Governance/policy evaluation | Achievable as rule-based system independent of model size. |

Local models (7B-14B) can handle **static analysis, well-scoped Q&A, structured editing, and rule-based governance**. They struggle with **causal reasoning, long-horizon planning, novel failure detection, and tasks requiring broad cross-file synthesis**.

---

## What Architecture Mattered Most

### 1. The Dual Architecture (Product + Research)

This is Lyme's most distinctive architectural contribution. It ensures research data is produced as a byproduct of normal use, not as an extra step. The privacy boundary between product and research layers is explicit and enforced.

### 2. The Compression Pipeline (5 Layers)

The layered compression hierarchy — tree → APIs → subsystems → invariants → rehydration — is a novel approach to codebase understanding. It encodes a hypothesis about the structure of software comprehension that is independent of any specific model.

### 3. The Verification Graph

Connecting claims, code changes, tests, traces, static analysis results, type checks, approvals, benchmark outcomes, and rollback evidence into a single directed graph is a genuinely novel approach to agent verification. The 14 gap labels provide a vocabulary for discussing verification completeness.

### 4. Governance-as-Code

The repo constitution format, the 5-level decision framework, and the immutable change ledger provide a practical architecture for safe agent autonomy. This is infrastructure that the agent safety community needs but has not produced in a usable form.

---

## What Memory Improved

**What was improved:**
- Memory storage (3 types, JSON-backed, importance-scored) works for storing and retrieving agent experiences
- Memory distillation compresses memories while preserving key facts
- The collective memory extends single-agent memory to multi-agent settings

**What was NOT improved by memory:**
- No measurable improvement in agent task completion
- No measured reduction in hallucination rate
- No measured reduction in redundant retrieval
- No measured improvement in session continuity

Memory was built. It was not evaluated. The question of whether it improves anything remains open.

---

## What Compression Improved

**What was improved:**
- Compression ratio: The pipeline demonstrably reduces raw codebase size by 10-50x depending on repository structure
- Task relevance: The rehydration layer can produce focused context packets for specific tasks
- Abstraction extraction: The semantic compression engine discovers cross-file patterns

**What was NOT improved:**
- No measured improvement in agent task performance with compressed vs. raw context
- No measured reduction in token costs
- No measured improvement in response accuracy
- No measured improvement in context window utilization

The compression pipeline is an engineering achievement. Its impact on agent performance is unevaluated.

---

## What Tool Routing Improved

The tool router categorizes 10 tools by capability, cost, and reliability. It uses heuristic routing to select tools for tasks.

**Improved:**
- Tool selection is deterministic and auditable
- Tool failure can be traced to specific routing decisions
- Tool capability discovery is explicit (capability matrix per model)

**Not improved:**
- No measured reduction in tool call failures
- No measured improvement in task completion via routing
- Routing is heuristic, not learned
- No experimental comparison of routing strategies

---

## What Governance Prevented

**Preventable risks addressed:**
- The 5 decision levels (AUTO_APPLY → BLOCK) provide a gradient of autonomy that can prevent unauthorized changes
- The 13 default policies cover security files, architecture changes, dependency updates, testing requirements
- Sensitive code detection identifies 13 categories of sensitive files (auth, config, secrets, crypto, etc.)
- The review board with 5 critic roles provides multi-perspective change evaluation
- The immutable change ledger ensures auditability

**What governance DID NOT prevent (untested):**
- No real-world evaluation of governance preventing a harmful agent action
- No false positive/negative measurement for policy violations
- No evaluation of governance overhead (how much does it slow down legitimate work?)
- No adversarial testing (can a malicious prompt bypass the governance engine?)

The governance system is well-designed but unevaluated in production-like conditions.

---

## What Remains Unsolved

### 1. The Central Hypothesis Is Untested

One year in, Lyme cannot answer its founding question: "Does compression + memory + tool routing make local models useful coding agents?" The infrastructure to answer this question exists. The experiment has not been run.

### 2. No Real Agent Integration

Lyme has never been connected to a running agent (Claude Code, OpenCode, CodeLlama, Qwen, GPT) in a controlled experiment. All benchmark scenarios exist as specifications. All cognitive traces are either simulated or generated from the demo system. The gap between the research platform and real agent measurement is unfilled.

### 3. No Longitudinal Data

A one-year project that studies agent improvement over time has zero longitudinal datasets. The evaluation framework uses simulated data for trend detection. There is no evidence of agent behavior changing over sessions because no agent was observed over multiple sessions.

### 4. No Cross-Model Comparison

Despite having a model adapter system, a capability matrix, and benchmark scenarios, Lyme has never compared two models on the same task using the same measurement infrastructure. The benchmark leaderboard contains simulated data, not real model runs.

### 5. The Scaling Laws Are Theoretically Specified, Not Empirically Derived

The scaling law framework defines variables, experiment designs, and reporting formats. It has produced zero empirical scaling laws. The numbers in the system are placeholders.

### 6. No External Validation

Lyme has not been used by anyone outside its development team. All assumptions about user needs, failure modes, and utility are untested with real users.

### 7. The Web UI Does Not Work

The UI system generates static HTML. The dashboard, timeline viewer, and thought viewer produce standalone HTML files. There is no interactive backend, no real-time updates, no server.

### 8. The Research Portal Is Static

The research portal generates JSON files. The leaderboard has simulated data. The research questions are listed as "OPEN" with no progress. The ablation studies produce reports from simulated components.

### 9. No ML Models Exist in the System

Lyme is entirely heuristic/rule-based. The invariant discovery engine uses pattern matching, not learned models. The anomaly detector uses threshold-based detection. The failure predictor uses heuristic scoring. There are zero trained ML models in the entire codebase.

### 10. The Project Lacks a Clear Audience

Lyme is too complex for a casual developer (30+ CLI commands, 66+ modules), too research-oriented for a production tool (no real agent integration), and too unevaluated for a research platform (no experiments run). It falls between audiences without serving any well.

---

## Summary

| Dimension | Status |
|---|---|
| Architecture designed | Complete |
| Architecture validated | Minimal |
| Central hypothesis | Untested |
| Compression pipeline | Built, unevaluated |
| Memory system | Built, unevaluated |
| Cognitive tracing | Built, partially evaluated (synthetic only) |
| Governance system | Built, unevaluated |
| Benchmark framework | Built, unevaluated (synthetic data) |
| Open standards | Defined, exemplified |
| Real agent measurement | Not accomplished |
| Longitudinal data | None |
| Cross-model comparison | None |
| User testing | None |
| Published research | None |
| ML models in system | Zero |
