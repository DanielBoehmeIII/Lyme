"""
Week 12 Prompt 1 — Define Software Intelligence
================================================
A formal research document investigating the actual dimensions of
software intelligence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IntelligenceDimension(str, Enum):
    ABSTRACTION_FORMATION = "abstraction_formation"
    CAUSAL_REASONING = "causal_reasoning"
    TEMPORAL_REASONING = "temporal_reasoning"
    INVARIANT_PRESERVATION = "invariant_preservation"
    REPAIR_ABILITY = "repair_ability"
    ARCHITECTURAL_PREDICTION = "architectural_prediction"
    UNCERTAINTY_ESTIMATION = "uncertainty_estimation"
    COORDINATION_EFFICIENCY = "coordination_efficiency"
    MEMORY_COMPRESSION = "memory_compression"
    INTENT_MODELING = "intent_modeling"


@dataclass
class DimensionDefinition:
    dimension: IntelligenceDimension = IntelligenceDimension.ABSTRACTION_FORMATION
    rigorous_definition: str = ""
    human_manifestation: str = ""
    agent_manifestation: str = ""
    measurable_proxies: List[str] = field(default_factory=list)
    failure_cases: List[str] = field(default_factory=list)
    experiment_designs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "definition": self.rigorous_definition[:200],
            "human": self.human_manifestation[:200],
            "agent": self.agent_manifestation[:200],
            "proxies": self.measurable_proxies[:5],
            "failure_cases": self.failure_cases[:3],
            "experiments": self.experiment_designs[:3],
        }


@dataclass
class DimensionProxies:
    dimension: IntelligenceDimension = IntelligenceDimension.ABSTRACTION_FORMATION
    proxy_measurements: Dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "proxy_measurements": self.proxy_measurements,
            "score": self.score,
            "confidence": self.confidence,
        }


@dataclass
class ExperimentDesign:
    dimension: IntelligenceDimension = IntelligenceDimension.ABSTRACTION_FORMATION
    name: str = ""
    hypothesis: str = ""
    methodology: str = ""
    independent_variables: List[str] = field(default_factory=list)
    dependent_metrics: List[str] = field(default_factory=list)
    controls: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "name": self.name,
            "hypothesis": self.hypothesis[:200],
            "methodology": self.methodology[:200],
            "variables": self.independent_variables[:5],
            "metrics": self.dependent_metrics[:5],
        }


class SoftwareIntelligenceFramework:
    """Research document defining software intelligence dimensions."""

    def __init__(self):
        self.dimensions: Dict[IntelligenceDimension, DimensionDefinition] = {}
        self._build_definitions()

    def _build_definitions(self):
        self.dimensions[IntelligenceDimension.ABSTRACTION_FORMATION] = DimensionDefinition(
            dimension=IntelligenceDimension.ABSTRACTION_FORMATION,
            rigorous_definition=(
                "The ability to identify, extract, and represent recurring patterns "
                "in code as generalized abstractions. This includes recognizing when "
                "code duplicates structure, when interfaces can be unified, and when "
                "patterns of computation can be parameterized."
            ),
            human_manifestation=(
                "Senior engineers naturally form abstractions after seeing similar "
                "patterns 3-5 times. They create generic solutions, extract shared "
                "libraries, and design API surfaces that encapsulate complexity."
            ),
            agent_manifestation=(
                "An agent exhibits abstraction formation when it can take scattered "
                "implementations, identify their common structure, and propose a unified "
                "abstraction. This requires more than pattern matching—it requires "
                "understanding which differences are essential and which are incidental."
            ),
            measurable_proxies=[
                "Detects duplicated code patterns across files",
                "Proposes unified interfaces for similar operations",
                "Correctly identifies variability points vs. fixed structure",
                "Able to name/describe the abstraction",
                "Abstraction survives test permutations",
            ],
            failure_cases=[
                "Creates overly generic abstractions (leaky abstractions)",
                "Fails to recognize abstractions when names differ",
                "Overfits to training examples", "Creates abstraction hierarchies too deep",
            ],
            experiment_designs=[
                "Present agent with 5 scattered implementations of the same pattern with different names; measure if it proposes unification",
                "Vary surface-level details while keeping abstract structure identical; measure if agent sees through surface variation",
            ],
        )

        self.dimensions[IntelligenceDimension.CAUSAL_REASONING] = DimensionDefinition(
            dimension=IntelligenceDimension.CAUSAL_REASONING,
            rigorous_definition=(
                "The capacity to model cause-effect relationships in software systems. "
                "This includes understanding that changing component X will affect "
                "component Y, even when no direct dependency exists. Causal reasoning "
                "requires distinguishing correlation from causation in code changes."
            ),
            human_manifestation=(
                "Experienced developers can predict downstream breakage from a change. "
                "They reason: 'if we change this API contract, these 5 services will "
                "break, and these 2 have fallback mechanisms.'"
            ),
            agent_manifestation=(
                "Agent can construct and traverse causal graphs of software components, "
                "estimate propagation likelihoods, distinguish direct vs. transitive "
                "effects, and identify non-obvious failure cascades."
            ),
            measurable_proxies=[
                "Downstream breakage prediction accuracy",
                "Identifies non-import dependencies",
                "Constructs causal graph from change history",
                "Estimates propagation probabilities",
                "Detects hidden causal chains",
            ],
            failure_cases=[
                "Confuses correlation with causation (co-change != causal link)",
                "Misses transitive effects beyond depth 2",
                "Doesn't account for compensating mechanisms",
            ],
            experiment_designs=[
                "Introduce hidden causal link between two apparently unrelated modules; measure if agent detects it",
                "Compare agent's breakage predictions against actual CI failures over N changes",
            ],
        )

        self.dimensions[IntelligenceDimension.TEMPORAL_REASONING] = DimensionDefinition(
            dimension=IntelligenceDimension.TEMPORAL_REASONING,
            rigorous_definition=(
                "Understanding software systems as temporal entities that evolve. "
                "This includes reasoning about past states, predicting future evolution, "
                "understanding decay patterns, and recognizing that code has a lifecycle."
            ),
            human_manifestation=(
                "Engineers understand that today's design decisions create future "
                "constraints. They anticipate technical debt, plan migrations, and "
                "recognize when a subsystem is in decline."
            ),
            agent_manifestation=(
                "Agent can model repository evolution, detect accelerated complexity "
                "growth, predict future bottlenecks, and recommend interventions at "
                "the right time."
            ),
            measurable_proxies=[
                "Predicts future complexity hotspots",
                "Detects accelerating technical debt",
                "Recommends interventions at appropriate times",
                "Models architectural drift over time",
            ],
            failure_cases=[
                "Treats codebase as static snapshot",
                "Cannot distinguish temporary vs. permanent patterns",
                "Misses slow-moving decay signals",
            ],
            experiment_designs=[
                "Feed agent a sequence of snapshots; measure if it identifies the trajectory and can predict the next snapshot properties",
            ],
        )

        self.dimensions[IntelligenceDimension.INVARIANT_PRESERVATION] = DimensionDefinition(
            dimension=IntelligenceDimension.INVARIANT_PRESERVATION,
            rigorous_definition=(
                "The ability to discover, maintain, and restore invariants—properties "
                "that must remain true across code changes. This includes architectural "
                "constraints, behavioral contracts, data invariants, and implicit rules."
            ),
            human_manifestation=(
                "Developers maintain invariants through testing, code review, and "
                "institutional knowledge: 'we never call the database from views', "
                "'this function must always return a non-null value.'"
            ),
            agent_manifestation=(
                "Agent can discover invariants from code analysis, detect violations, "
                "propose repairs, and track invariant evolution over time."
            ),
            measurable_proxies=[
                "Invariant discovery recall",
                "Violation detection accuracy",
                "Repair suggestion relevance",
                "Tracks invariant evolution accurately",
            ],
            failure_cases=[
                "Discovers overly specific invariants (overfitting)",
                "Misses implicit/convention-based invariants",
                "Cannot prioritize which invariants matter",
            ],
            experiment_designs=[
                "Plant subtle invariant violations; measure detection rate across invariant types",
            ],
        )

        self.dimensions[IntelligenceDimension.REPAIR_ABILITY] = DimensionDefinition(
            dimension=IntelligenceDimension.REPAIR_ABILITY,
            rigorous_definition=(
                "The capacity to diagnose and fix defects in software. This is not "
                "just generating patches, but understanding root causes, evaluating "
                "fix correctness, and avoiding regressions."
            ),
            human_manifestation=(
                "Engineers debug by forming hypotheses, gathering evidence, isolating "
                "root causes, and crafting minimal repairs."
            ),
            agent_manifestation=(
                "Agent can diagnose defects from symptoms, trace through execution "
                "paths, generate candidate fixes, verify correctness, and learn from "
                "repair outcomes."
            ),
            measurable_proxies=[
                "First-attempt fix success rate",
                "Root cause identification accuracy",
                "Fix minimality (lines changed)",
                "Regression rate of fixes",
            ],
            failure_cases=[
                "Treats symptoms not causes",
                "Generates patches that pass tests but miss the real issue",
                "Creates cascading failures from overly broad fixes",
            ],
            experiment_designs=[
                "Inject defects with known root causes; measure diagnostic accuracy and fix quality",
            ],
        )

        self.dimensions[IntelligenceDimension.ARCHITECTURAL_PREDICTION] = DimensionDefinition(
            dimension=IntelligenceDimension.ARCHITECTURAL_PREDICTION,
            rigorous_definition=(
                "The ability to forecast likely architectural evolution paths. "
                "This includes predicting where abstractions will emerge, where "
                "coupling will increase, and what architectural style the system "
                "is converging toward."
            ),
            human_manifestation=(
                "Architects anticipate that overly coupled modules will be extracted "
                "into services, that certain patterns will become standard, and that "
                "technology choices will constrain future options."
            ),
            agent_manifestation=(
                "Agent can analyze growth patterns, detect architectural drift, "
                "predict likely extraction points, and forecast technology migration "
                "trajectories."
            ),
            measurable_proxies=[
                "Predicts actual future architecture changes",
                "Identifies likely extraction points before they're extracted",
                "Forecasts technology migration paths",
            ],
            failure_cases=[
                "Projects current trends linearly without accounting for phase changes",
                "Underestimates social/organizational factors",
            ],
            experiment_designs=[
                "Train on first 80% of repo history; predict next 20% of architectural changes",
            ],
        )

        self.dimensions[IntelligenceDimension.UNCERTAINTY_ESTIMATION] = DimensionDefinition(
            dimension=IntelligenceDimension.UNCERTAINTY_ESTIMATION,
            rigorous_definition=(
                "The capacity to accurately estimate one's own uncertainty about "
                "software artifacts and decisions. This means knowing what you don't "
                "know, and calibrating confidence to actual correctness."
            ),
            human_manifestation=(
                "Skilled developers say 'I'm not sure about this edge case' rather "
                "than confidently asserting incorrect solutions. They seek verification "
                "when uncertainty is high."
            ),
            agent_manifestation=(
                "Agent produces calibrated confidence scores, expresses uncertainty "
                "about ambiguous specifications, and seeks additional information when "
                "confidence is low."
            ),
            measurable_proxies=[
                "Confidence calibration (does 70% confident = 70% correct?)",
                "Appropriate deferral to human judgment",
                "Identifies knowledge boundaries",
            ],
            failure_cases=[
                "Overconfidence on out-of-distribution inputs",
                "Underconfidence leading to excessive verification overhead",
                "Cannot distinguish known unknowns from unknown unknowns",
            ],
            experiment_designs=[
                "Measure confidence calibration curve across varied tasks and difficulty levels",
            ],
        )

        self.dimensions[IntelligenceDimension.COORDINATION_EFFICIENCY] = DimensionDefinition(
            dimension=IntelligenceDimension.COORDINATION_EFFICIENCY,
            rigorous_definition=(
                "In multi-agent settings, the ratio of productive work to coordination "
                "overhead. High coordination efficiency means agents spend minimal "
                "bandwidth on synchronization and maximal bandwidth on actual problem-solving."
            ),
            human_manifestation=(
                "Well-organized teams have minimal meeting overhead relative to output. "
                "They use async communication, clear interfaces, and shared mental models."
            ),
            agent_manifestation=(
                "Agents communicate via compressed intent packets, maintain shared "
                "context efficiently, and avoid redundant synchronization."
            ),
            measurable_proxies=[
                "Productive work / total communication ratio",
                "Time spent in coordination vs. execution",
                "Communication compression ratio",
            ],
            failure_cases=[
                "Oversynchronization (every agent waits for every other)",
                "Undersynchronization (conflicting edits, duplicated work)",
                "Communication protocol overhead exceeds benefit",
            ],
            experiment_designs=[
                "Vary communication topology and measure task completion efficiency",
            ],
        )

        self.dimensions[IntelligenceDimension.MEMORY_COMPRESSION] = DimensionDefinition(
            dimension=IntelligenceDimension.MEMORY_COMPRESSION,
            rigorous_definition=(
                "The ability to compress software knowledge into efficient representations "
                "that preserve essential information while discarding noise. This determines "
                "how much of a codebase can be 'understood' within a fixed context window."
            ),
            human_manifestation=(
                "Engineers build mental models that summarize thousands of lines of "
                "code into key abstractions and relationships. They don't memorize code; "
                "they understand structure."
            ),
            agent_manifestation=(
                "Agent can compress codebases into essential representations, retrieve "
                "relevant context efficiently, and maintain working memory without "
                "exceeding context limits."
            ),
            measurable_proxies=[
                "Compression ratio without information loss",
                "Retrieval precision from compressed representation",
                "Context window utilization efficiency",
            ],
            failure_cases=[
                "Lossy compression that drops critical details",
                "Compression that loses causal relationships",
                "Retrieval fails for unanticipated queries",
            ],
            experiment_designs=[
                "Fix context window size; measure how much of a repo the agent can effectively reason about",
            ],
        )

        self.dimensions[IntelligenceDimension.INTENT_MODELING] = DimensionDefinition(
            dimension=IntelligenceDimension.INTENT_MODELING,
            rigorous_definition=(
                "The capacity to infer the purpose, design rationale, and future "
                "trajectory of code. This goes beyond what code does to why it exists, "
                "what tradeoffs were made, and what constraints shaped it."
            ),
            human_manifestation=(
                "Engineers reading unfamiliar code reconstruct the original developer's "
                "intent: 'they chose this pattern because performance mattered more than "
                "clarity here.'"
            ),
            agent_manifestation=(
                "Agent can infer subsystem purpose, detect design philosophy, identify "
                "tradeoffs, and predict likely evolution paths from code structure and history."
            ),
            measurable_proxies=[
                "Purpose inference accuracy",
                "Tradeoff identification precision",
                "Evolution prediction accuracy",
            ],
            failure_cases=[
                "Confuses implementation detail with intent",
                "Cannot distinguish accidental from essential complexity",
                "Projects current constraints onto past decisions",
            ],
            experiment_designs=[
                "Present agent with unfamiliar codebase; measure accuracy of inferred purpose against documentation",
            ],
        )

    def get_definition(self, dimension: IntelligenceDimension) -> Optional[DimensionDefinition]:
        return self.dimensions.get(dimension)

    def get_all_definitions(self) -> Dict[str, Dict[str, Any]]:
        return {
            d.value: defn.to_dict()
            for d, defn in self.dimensions.items()
        }

    def generate_report(self) -> str:
        lines = []
        lines.append("# Software Intelligence: A Formal Framework")
        lines.append("")
        lines.append("## Abstract")
        lines.append("")
        lines.append(
            "This document defines the dimensions of software intelligence as a "
            "research apparatus. Rather than measuring benchmark scores or token "
            "throughput, we identify the cognitive capacities that underpin genuine "
            "software understanding and autonomous modification."
        )
        lines.append("")
        lines.append(f"*Generated: {time.ctime()}*")
        lines.append("")
        lines.append("## Dimensions")
        lines.append("")

        for dim in IntelligenceDimension:
            defn = self.dimensions.get(dim)
            if not defn:
                continue
            lines.append(f"### {dim.value.replace('_', ' ').title()}")
            lines.append("")
            lines.append(f"**Rigorous Definition:** {defn.rigorous_definition}")
            lines.append("")
            lines.append(f"**Human Manifestation:** {defn.human_manifestation}")
            lines.append("")
            lines.append(f"**Agent Manifestation:** {defn.agent_manifestation}")
            lines.append("")
            lines.append("**Measurable Proxies:**")
            for proxy in defn.measurable_proxies:
                lines.append(f"- {proxy}")
            lines.append("")
            lines.append("**Failure Cases:**")
            for case in defn.failure_cases:
                lines.append(f"- {case}")
            lines.append("")
            lines.append("**Experiment Designs:**")
            for exp in defn.experiment_designs:
                lines.append(f"- {exp}")
            lines.append("")

        lines.append("## Research Implications")
        lines.append("")
        lines.append(
            "These ten dimensions form a framework for evaluating and improving "
            "software intelligence. No current system excels across all dimensions. "
            "The framework suggests that genuine software intelligence requires:"
        )
        lines.append("")
        lines.append("1. **Causal understanding** - not pattern matching")
        lines.append("2. **Temporal awareness** - not static analysis")
        lines.append("3. **Intent inference** - not syntax manipulation")
        lines.append("4. **Uncertainty calibration** - not false confidence")
        lines.append("5. **Efficient compression** - not brute-force context")
        lines.append("")

        return "\n".join(lines)
