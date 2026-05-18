"""Positioning — Lyme's market position and manifesto."""
from __future__ import annotations

MANIFESTO = """Lyme Manifesto
==============

Lyme is the operating system for autonomous local software engineering.

We believe:

1. LOCAL IS THE FUTURE
   The best coding agent runs on your hardware, under your control,
   with zero data leaving your machine. Local is not a compromise —
   it's the architectural advantage.

2. RELIABILITY OVER NOVELTY
   A coding agent that works 95% of the time is worth more than
   one that's 10% more creative but fails unpredictably.
   We optimize for dependability, determinism, and trust.

3. ORCHESTRATION IS THE MOAT
   Models get better every month. The moat isn't a single model —
   it's the system that orchestrates models, plans edits,
   runs tests, repairs failures, and learns from every session.

4. DEVELOPERS DESERVE AUTONOMY
   Lyme doesn't replace developers. It amplifies them.
   By handling the mechanical parts of software engineering,
   it frees developers to focus on architecture, design, and judgment.

5. MEASURE EVERYTHING
   Every edit is scored. Every failure is categorized.
   Every session improves the system. If you can't measure it,
   you can't improve it.

6. OPEN ECOSYSTEM
   Lyme's plugin SDK, agent configs, and evaluation harness
   are designed for extensibility. The platform wins when
   the ecosystem wins.

7. LOCAL CODING AGENTS ARE A PLATFORM PLAY
   This is not a feature. It's a new category.
   The company that makes local agents dependable
   will define the category.

Lyme: The operating system for autonomous local software engineering.
"""

TAGLINE = "The operating system for autonomous local software engineering."
MISSION = "Make local coding agents dependable at scale."

TARGET_MARKETS = {
    "dev_shops": "Agencies doing client work — reduce costs, increase throughput",
    "startups": "Small teams that need to move fast without a large engineering team",
    "freelancers": "Independent developers competing with teams 10x their size",
    "enterprise": "Organizations that need airgapped, auditable coding assistance",
}

VALUE_PROPOSITIONS = {
    "cost": "10x cheaper than cloud coding agents (no API costs)",
    "privacy": "Zero data leaves your machine",
    "reliability": "Measured, scored, and improved over time",
    "speed": "Low-latency local inference with speculative decoding",
    "control": "Full control over models, tools, and workflows",
}


def print_manifesto() -> str:
    return MANIFESTO


def market_positioning() -> dict:
    return {
        "tagline": TAGLINE,
        "mission": MISSION,
        "category": "Autonomous Local Software Engineering",
        "target_markets": TARGET_MARKETS,
        "value_propositions": VALUE_PROPOSITIONS,
        "competitors": ["Claude Code", "GitHub Copilot (Codex)", "OpenCode", "Aider", "Cursor"],
        "differentiators": [
            "Fully local — no data leaves your machine",
            "Multi-agent orchestration with trust-weighted collective verdicts",
            "Measured reliability with failure taxonomy and confidence scoring",
            "Plugin ecosystem for custom agents, tools, and model packs",
            "Enterprise-grade audit trails and airgapped operation",
        ],
    }
