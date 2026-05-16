"""Lyme Product Positioning — What we are, what we are not, and why it matters.

Not another coding agent.
Not another API wrapper.
Not another benchmark toy.
"""


HOMEPAGE_HEADLINE = (
    "Lyme: The observatory for software intelligence."
)

ONE_SENTENCE_PITCH = (
    "Lyme is a local-first research platform for measuring, understanding, "
    "and improving how coding agents reason about software."
)

TECHNICAL_PITCH = """
Lyme is a dual-architecture system: a usable local coding agent AND a research platform for software cognition.

**Product side**: `lyme doctor`, `lyme ask`, `lyme diff`, `lyme trace`, `lyme fix`, `lyme history`.

**Research side**: cognitive traces, causal graphs, invariant discovery, scaling laws, agent coordination, context degradation studies.

The architecture is designed so every product action generates research data, and every research insight improves product behavior. The telemetry substrate is shared. The privacy boundary is explicit. The data format is versioned, portable, and human-inspectable.

Lyme runs entirely on your machine. No cloud dependency. No telemetry leaves your network unless you choose to publish research data.
"""

README_INTRO = """
# Lyme

**Local-first infrastructure for coding agent measurement and improvement.**

Lyme is a research platform disguised as a developer tool. It helps you understand your codebase, diagnose problems, and interact with coding agents — while simultaneously collecting the structured data needed to study how agents actually think, fail, and improve.

Unlike other coding agent tools, Lyme is built for observability. Every action is traced, every claim is evidence-grounded, every decision is recorded, and every outcome is measured. The result is a system that gets better over time — not through better prompts, but through better understanding.

## What Lyme is NOT

- **Not a coding agent.** Lyme studies coding agents. It can run them, trace them, benchmark them, and improve them, but it is not itself an agent wrapper.
- **Not a cloud platform.** Everything runs locally. Your code never leaves your machine.
- **Not another benchmark.** Lyme provides a benchmark framework, but the value is in the infrastructure around the benchmark — the tracing, the memory, the compression, the analysis tools.
- **Not a replacement for developers.** Lyme measures and improves the interaction between humans and coding agents.
"""

INVESTOR_PITCH = """
**Lyme** is the first research platform purpose-built for the coding agent era.

The market for coding agents is exploding — every major tech company and thousands of startups are building or buying agent infrastructure. But the entire industry is flying blind. There are no standardized measurements, no shared benchmarks that matter, no observability stack for agent cognition, and no way to systematically improve agent behavior across versions.

Lyme solves this by building the measurement infrastructure first.

We are what New Relic is to web services, what Prometheus is to infrastructure, what MLFlow is to machine learning — but for coding agents.

**The insight**: Every product action Lyme performs (diagnosing a repo, answering a question, applying a fix) generates research-quality data about agent cognition. Every experiment Lyme runs (scaling laws, invariant discovery, failure analysis) improves the product layer.

**The business model**: Open-source research platform with optional enterprise features for team-wide agent observability, compliance auditing, and custom experiment design.

**The moat**: The data. As Lyme accumulates traces, benchmarks, and failure analyses across thousands of repositories, it builds the largest corpus of structured agent cognition data in existence — all gathered with explicit consent and privacy boundaries.

**Why now**: Coding agents are being deployed into production faster than we can measure their safety, reliability, or actual effectiveness. The industry needs a measurement layer before it can have a trust layer. Lyme is that measurement layer.
"""

WHY_NOW = """
Coding agents are being deployed into production at an unprecedented rate. Every week a new model claims superhuman performance on SWE-bench. Every month a new startup promises to replace development teams. Every quarter a new agent framework becomes standard.

But we cannot answer the most basic questions:

- Are coding agents actually getting better, or just bigger?
- What is the hallucination rate of a production agent on an actual codebase?
- How does context degradation affect performance over a 100-session engagement?
- What are the reproducible failure modes of current agent architectures?
- How do different models compare on real codebase tasks, not synthetic benchmarks?

These are not philosophical questions. They are engineering questions that require measurement infrastructure to answer. That infrastructure does not exist — so we are building it.

The window for establishing the measurement standard is open. The first platform to provide rigorous, reproducible, privacy-preserving agent observability will define how the industry evaluates and trusts coding agents for the next decade.
"""

WHY_LOCAL = """
Local-first is not a feature. It is a methodological requirement.

- **Privacy**: Your codebase is your intellectual property. It should never leave your machine for the purpose of measuring agent performance. Research data should be collected with explicit consent, not as a cost of using a cloud service.

- **Reproducibility**: Cloud-dependent measurements are not reproducible. API versions change, models are updated, routing changes. Local infrastructure means you can lock versions, replay traces, and verify results.

- **Latency**: Realistic agent measurement requires realistic latencies. Network calls distort timing data. Local models and local execution produce measurements that reflect actual agent cognition, not network conditions.

- **Experimentation**: Research requires the ability to modify every part of the stack — the model, the prompts, the tools, the memory system. Local infrastructure provides this control. Cloud APIs are black boxes.

- **Cost**: Running benchmarks on API-based models is expensive. Local models (via Ollama, llama.cpp, etc.) make large-scale agent research economically viable.

Lyme runs entirely on your machine. Research data stays on your machine. You choose what to publish.
"""

WHY_DIFFERENT = """
**Lyme is not another coding agent. It is the observatory for them.**

| Dimension | Other Tools | Lyme |
|-----------|-------------|------|
| Purpose | Help developers code | Measure and improve agent cognition |
| Architecture | Agent + UI | Product layer + Research layer + Shared telemetry |
| Data model | Chat history, file edits | Versioned schema: traces, graphs, invariants, causals, failures |
| Privacy | Cloud-dependent, API keys required | 100% local, privacy boundary between product/research |
| Measurement | None (vibes-based) | Every action generates research data |
| Improvement | Prompt engineering | Data-driven: scaling laws, failure analysis, memory |
| Reproducibility | None | Deterministic replay, versioned traces, git-state capture |
| Failure handling | Silent failures | Explicit failure taxonomy, labels, retry recommendations |
| Extensibility | Closed | Plugin system, experiment API, research module framework |

**The key insight that makes Lyme different:**

Every other coding agent tool treats research as an afterthought — something you might do later if you have time. Lyme was designed from the ground up as a research platform that also happens to be useful as a developer tool.

This is not a cosmetic difference. It affects every architectural decision:

- The storage format is not a chat log — it is a versioned schema with graphs, invariants, causals, and temporal snapshots
- The CLI is not a REPL — it is an experiment runner with telemetry hooks
- The "memory" is not a summary — it is a structured store with decay curves and retrieval metrics
- The "fix" is not a patch — it is a safe edit protocol with risk estimation, rollback, and audit

This architecture means Lyme can answer questions no other tool can:

- What is the confidence calibration of your agent?
- Where does context degradation first appear in your codebase?
- What invariants does your architecture implicitly depend on?
- What is the reproducibility rate of your agent's fixes?
- How does model size affect fix quality vs. fix safety?

These are the questions that matter for building trustworthy coding agents. Lyme is built to answer them.
"""


def generate_positioning_report() -> str:
    sections = [
        ("Homepage Headline", HOMEPAGE_HEADLINE),
        ("One-Sentence Pitch", ONE_SENTENCE_PITCH),
        ("Technical Pitch", TECHNICAL_PITCH),
        ("README Intro", README_INTRO),
        ("Investor / Research Lab Pitch", INVESTOR_PITCH),
        ("Why Now", WHY_NOW),
        ("Why Local", WHY_LOCAL),
        ("Why This Is Different", WHY_DIFFERENT),
    ]

    lines = []
    lines.append("# Lyme Product Positioning")
    lines.append("")
    for title, content in sections:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines)
