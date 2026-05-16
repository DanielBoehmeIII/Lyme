# Lyme Research Manifesto

**Local-first, observable, measurable infrastructure for coding agent science.**

---

## Preamble

Coding agents are the most important tools we do not understand.

Every week a new model is released, every month a new benchmark claims superhuman performance, and every quarter a new startup promises to replace every developer on the planet. The discourse oscillates between breathless hype and cynical dismissal, with almost no rigorous measurement in between.

This is not normal science. It is not even normal engineering.

We are flying coding agents by the seat of our pants — running them on proprietary cloud APIs, evaluating them on vibes-based benchmarks, and deploying them into production with less observability than the average web service. We cannot reproduce each other's results. We cannot profile a model's cognition. We cannot point to a single graph that shows whether coding agents are getting better or just bigger.

Lyme exists to fix this. Not by building a better coding agent, but by building the infrastructure to study them scientifically.

---

## The Problem

### 1. Coding Agents Are Stateless Improvisers

Every conversation with a coding agent is groundhog day. The agent has no memory of the previous session, no persistent understanding of the codebase, no accumulated skill. It begins each interaction as a blank slate — fluent but amnesiac.

This is not a limitation of the model. It is a limitation of the architecture. We have built agents as stateless request-response systems and called it "chat." We have wrapped them in orchestration loops and called it "agency." But an agent without memory is not an agent. It is a particularly elaborate autocomplete.

### 2. No Measurement, No Improvement

The software engineering industry runs on observability. We instrument our databases, profile our CPUs, trace our requests, and track our error budgets. We would never deploy a microservice without dashboards, alerts, and structured logging.

Coding agents run in an observability desert. We do not measure their cognition. We do not trace their decision paths. We do not profile their context utilization. We do not track their hallucination rates over time. We treat them as black boxes and then wonder why they behave unpredictably.

### 3. Benchmarks Measure Everything Except What Matters

Current benchmarks fall into two categories:

- **Task-specific benchmarks** (HumanEval, SWE-bench, etc.) that measure narrow capabilities in artificial settings. They are useful for model comparison but tell us almost nothing about how an agent performs on an actual codebase with actual technical debt, actual tests, actual team conventions, and actual ambiguity.

- **Vibes-based evaluation** where a human runs a few queries, decides it "feels" better, and declares victory. This is astrology with a CLI.

Neither approach measures cognition, failure modes, recovery behavior, context degradation, or the subtle collapse of agent performance as task complexity increases. We are benchmarking a 747 by measuring how fast its engines spin on the tarmac.

### 4. Context Is the Central Bottleneck, and We Are Pretending It Is Not

Context windows are growing — 32K, 128K, 1M tokens, and beyond. The assumption is that bigger is better: give the agent more code, more history, more documentation, and it will make better decisions.

This assumption is false on at least three levels:

- **Context windows are not memory.** Attention scales poorly with sequence length, and models exhibit a documented tendency to lose information in the middle of long contexts (the "lost in the middle" problem). A 1M token context is not a 1M token understanding.

- **Attention is not understanding.** A model can attend to every line of your codebase and still not understand its architecture, its invariants, or its intent. Raw context is not comprehension.

- **Prompt engineering is not architecture.** We have been solving every problem by adding tokens — more instructions, more examples, more RAG results, more tool descriptions. This is duct tape, not design. We need compression, not expansion.

### 5. Compression May Be Intelligence

Understanding a codebase is knowing what to ignore. A senior engineer reading a repository does not read every file. They form a mental model — a compressed representation — and rehydrate details only as needed.

This is not a metaphor. This is the fundamental operation of intelligence. The ability to discard irrelevant information is as important as the ability to retain relevant information. Perhaps more important.

The Lyme compression pipeline — from file tree to API surface to subsystem map to invariant catalog — is a hypothesis about the structure of code understanding. If a small model armed with a good compressed representation can outperform a large model drowning in raw context, we will have learned something important about both intelligence and architecture.

### 6. Software Development Needs Observability

We cannot improve what we cannot measure. This is the first law of engineering, and we are violating it at scale.

Coding agents need the equivalent of distributed tracing — not just of tool calls, but of decisions. They need metrics — not just pass/fail, but confidence, latency, context utilization, recovery time. They need profiling — not just of the model, but of the entire agent loop.

Without observability, every claim about agent performance is an anecdote.

### 7. Memory Is the Difference Between a Tool and a Colleague

Without memory, every session is the first day on the job. The agent learns nothing from its mistakes, accumulates no knowledge of the codebase, and cannot improve over time.

Persistent cognition — the ability to store, retrieve, and synthesize experiences across sessions — is not a nice-to-have. It is the defining characteristic of an intelligent system that operates in a persistent environment. A codebase is such an environment.

We do not know what happens when an agent accumulates 100 hours of experience on a single codebase. Nobody has run that experiment. The infrastructure to do so barely exists. Lyme aims to build it.

### 8. Diffs Are Too Low-Level

`git diff` shows what changed. It does not show why. It does not classify the semantic nature of the change — whether a line was refactored, a behavior altered, a dependency added, or an invariant violated.

Semantic understanding of change requires architectural awareness. It requires knowing that changing line 47 of `auth.py` affects the permissions of every endpoint. It requires knowing that renaming a function is different from changing its return type.

Current tools treat all diffs as equivalent. This is like grading essays by counting words.

### 9. Multi-Agent Systems Currently Fail

The grand vision of multiple agents collaborating on a codebase is compelling. The reality is coordination overhead eating intelligence gains.

We do not understand the scaling laws of collaboration. At what point does adding more agents decrease throughput? When does communication overhead exceed the marginal benefit of specialization? How do we measure the cognitive load of coordination?

These are empirical questions. Nobody is running the experiments. Lyme can.

---

## What Lyme Is Trying to Prove

1. **That local coding agents can be studied scientifically** — with reproducible benchmarks, structured observability, and quantitative metrics that degrade gracefully with model size.

2. **That the right abstractions make small models effective** — that compression, memory, and context optimization are force multipliers that can close the gap between a 7B model and a 70B model on real codebase tasks.

3. **That observability + memory + compression > scale** — that a well-instrumented, persistent, compressed agent running on a local 7B model can outperform a stateless agent on a 70B API model for sustained codebase work.

4. **That failure is measurable and learnable** — that agents can detect their own hallucinations, recover from their own errors, and improve from their own mistakes if given the right infrastructure.

---

## Research Agenda

The following hypotheses are testable within the Lyme framework:

### H1: Compression-First Architecture
A 7B model equipped with Lyme's compression pipeline (tree + APIs + subsystems + invariants) will match or exceed the task completion rate of a 70B model using raw file context on multi-file editing tasks.

### H2: Persistent Memory Improves Over Time
An agent with access to a persistent MemoryStore will show measurable improvement in task completion rate, hallucination reduction, and response latency over 100+ sessions on the same codebase.

### H3: Context Budget Optimization Prevents Degradation
As the number of files in a repository grows, agents using ContextBudgetOptimizer will maintain stable accuracy, while agents using naive top-k retrieval will exhibit measurable accuracy decay (the "context collapse" threshold).

### H4: Cognitive Tracing Enables Failure Analysis
Structured cognitive traces (decision points, branches, confidence scores) enable automated classification of failure modes with >80% accuracy, making agent debugging tractable.

### H5: Anomaly Detection Generalizes
Anomaly patterns learned from one agent family (e.g., CodeLlama) transfer to another (e.g., Qwen) with <20% drop in detection accuracy, suggesting universal failure signatures in coding agent cognition.

### H6: Semantic Diff Classification
Diffs can be automatically classified into semantic categories (structural, behavioral, dependency, cosmetic) with >90% precision using a combination of AST analysis and the repo's subsystem-layer compression.

### H7: Multi-Agent Coordination Overhead
There exists a measurable inflection point (in terms of coupling between files) beyond which adding agents decreases net throughput, and this point can be predicted from the compression layer's subsystem graph.

---

## What We Are Not Building

- **Not a coding agent.** Lyme is infrastructure for studying coding agents. We may build reference agents to validate the infrastructure, but the goal is measurement, not replacement.

- **Not a cloud platform.** Lyme runs locally. No telemetry leaves your machine. No API keys required. No subscription tiers.

- **Not another benchmark.** Lyme provides a benchmark *framework* (ScenarioRegistry, BenchmarkEngine) but the value is in the infrastructure around the benchmark — the tracing, the memory, the compression, the analysis tools.

- **Not a replacement for human developers.** Lyme measures and improves the interaction between humans and coding agents. It is not a tool for removing humans from the loop.

- **Not a product.** Lyme is a research project. The output is measurements, papers, and tools for the research community. If it becomes a product, that will be someone else's job.

---

## The Shape of the System

Lyme is organized into six concerns:

| Module | Purpose |
|---|---|
| **compression/** | Multi-layer codebase compression pipeline (tree, APIs, subsystems, invariants, rehydration) |
| **memory/** | Persistent memory store with procedural/episodic/semantic types, search, and distillation |
| **benchmark/** | Scenario registry, benchmark engine, structured result storage |
| **cognition/** | Cognitive tracing, thought analysis, anomaly detection |
| **replay/** | Deterministic replay, diff replay, semantic change analysis |
| **experiments/** | Anti-hallucination protocols, tool-use benchmarks, coordination experiments |

Each module is independent. You can use the compression pipeline without the benchmark engine. You can use the memory store without the cognitive tracer. This is intentional — we do not know which abstractions will survive contact with real research, so we keep them loosely coupled.

---

## A Call to Contribute Measurement, Not Code

The most valuable contribution to this project is not a pull request. It is a measurement.

Run Lyme on your codebase. Benchmark your workflow. Publish your results. Fail loudly, share the traces, let us all learn from what collapsed and why.

We need:

- **Traces** of coding agent sessions on real codebases with real bugs
- **Benchmark results** comparing models, prompts, and strategies
- **Failure analyses** documenting where agents go wrong
- **Compression ratios** for different codebases and languages
- **Memory decay curves** showing how agents forget over time
- **Coordination graphs** for multi-agent experiments

The code is the means. The measurement is the end.

---

*Lyme is named for the tick-borne pathogen because, like a really bad bug in production, it's small, persistent, hard to detect, and surprisingly hard to get rid of.*

*Also because researching Lyme disease requires understanding a complex system — the vector, the host, the pathogen, the environment — and that is what we do when we study coding agents. We study the interaction of model, codebase, task, and context. Understanding that interaction is the science.*
