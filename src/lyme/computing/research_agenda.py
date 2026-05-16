from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ResearchProgram:
    title: str = ""
    why_it_matters: str = ""
    what_is_unknown: str = ""
    what_lyme_can_uniquely_test: str = ""
    required_infrastructure: str = ""
    possible_breakthroughs: str = ""
    failure_cases: str = ""
    priority: int = 5
    dependencies: List[str] = field(default_factory=list)


class LymeResearchAgenda:
    def __init__(self):
        self.programs: List[ResearchProgram] = self._define_programs()

    def _define_programs(self) -> List[ResearchProgram]:
        return [
            ResearchProgram(
                title="Scaling Laws of Software Intelligence",
                why_it_matters=(
                    "If software cognition has scaling laws comparable to language modeling, "
                    "we can predict what infrastructure investments yield what cognitive capabilities. "
                    "This transforms Lyme from a research platform into an engineering discipline."
                ),
                what_is_unknown=(
                    "Does software understanding scale with observation volume? "
                    "What is the relationship between trace density and causal inference quality? "
                    "Is there a 'bitter lesson' for software cognition (more data beats better algorithms)?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's telemetry substrate captures all agent actions, decisions, and outcomes. "
                    "By varying observation budgets and measuring cognition quality, "
                    "Lyme can produce the first scaling curves for software understanding."
                ),
                required_infrastructure=(
                    "Variable-density trace ingestion, cognition quality metrics, "
                    "controlled observation budgets, automated measurement pipelines."
                ),
                possible_breakthroughs=(
                    "Discovery of power-law relationships between observation and understanding. "
                    "Identification of diminishing returns thresholds. "
                    "Optimal resource allocation formulas for software cognition systems."
                ),
                failure_cases=(
                    "Diminishing returns hit immediately (cognition is cheap). "
                    "No stable scaling relationship exists (too many confounding variables). "
                    "Quality metrics are too noisy to measure reliably."
                ),
                priority=1,
            ),
            ResearchProgram(
                title="Causal Software Reasoning",
                why_it_matters=(
                    "Current coding agents operate on pattern matching, not causal understanding. "
                    "They can mimic fixes they've seen but cannot reason about why software behaves. "
                    "Causal reasoning is the difference between a lookup table and understanding."
                ),
                what_is_unknown=(
                    "Can causal graphs of sufficient quality be inferred from observational data alone? "
                    "How do we handle hidden confounders in software systems? "
                    "What fraction of software causality is fundamentally opaque?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's causal graph engine, combined with runtime trace correlation and "
                    "failure replay, creates a unique testbed for causal inference in software. "
                    "Controlled intervention experiments can validate causal claims."
                ),
                required_infrastructure=(
                    "Causal graph with confidence and evidence tracking, "
                    "intervention tracking, counterfactual simulation, "
                    "ground-truth validation via controlled experiments."
                ),
                possible_breakthroughs=(
                    "Demonstration that causal software models outperform "
                    "pattern-matching baselines for repair suggestions. "
                    "Quantification of causal opacity in real systems."
                ),
                failure_cases=(
                    "Causal graphs are too noisy to be useful. "
                    "Pattern matching always wins on practical tasks. "
                    "Confounders are too numerous to control."
                ),
                priority=2,
            ),
            ResearchProgram(
                title="Memory Compression Limits",
                why_it_matters=(
                    "Software repositories grow without bound. Cognition systems must compress. "
                    "Understanding the fundamental limits of code compression "
                    "determines whether software cognition is feasible at scale."
                ),
                what_is_unknown=(
                    "What is the minimal representation of a codebase that preserves cognition-relevant information? "
                    "How does compression ratio trade off against inference quality? "
                    "Are there universal compression strategies across languages and domains?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's multi-layer compression system (tree, APIs, subsystems, invariants) "
                    "provides a testbed for measuring compression-cognition tradeoffs. "
                    "Systematic experiments can map the Pareto frontier."
                ),
                required_infrastructure=(
                    "Configurable compression pipeline, cognition quality benchmarks "
                    "at each compression level, information-theoretic measurements."
                ),
                possible_breakthroughs=(
                    "Discovery of universal compression ratios for code cognition. "
                    "Identification of 'critical information' that cannot be compressed. "
                    "Adaptive compression strategies that allocate budget by information density."
                ),
                failure_cases=(
                    "Compression destroys cognition-relevant information at any useful ratio. "
                    "Optimal compression is task-specific and doesn't generalize. "
                    "Information-theoretic approach is too abstract to produce practical results."
                ),
                priority=3,
            ),
            ResearchProgram(
                title="Collective Agent Cognition",
                why_it_matters=(
                    "Single-agent systems have fundamental limits (context windows, knowledge, reliability). "
                    "Collective intelligence may overcome these, but we don't understand how to design effective agent societies."
                ),
                what_is_unknown=(
                    "What coordination patterns maximize collective software understanding? "
                    "How do specialization and debate affect outcome quality? "
                    "What are the scaling laws of agent collectives?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's multi-agent society system supports running controlled experiments "
                    "with different coordination patterns, specializations, and debate protocols. "
                    "Telemetry captures all inter-agent communication."
                ),
                required_infrastructure=(
                    "Multi-agent orchestration, communication protocols, "
                    "coordination metrics, specialization frameworks, debate mechanisms."
                ),
                possible_breakthroughs=(
                    "Demonstration that coordinated agent collectives outperform "
                    "single agents on complex software tasks. "
                    "Discovery of optimal group sizes and specialization patterns."
                ),
                failure_cases=(
                    "Coordination overhead always exceeds intelligence gains. "
                    "Agent societies are too brittle for practical use. "
                    "Single agents with enough context match collective performance."
                ),
                priority=4,
            ),
            ResearchProgram(
                title="Invariant Discovery and Maintenance",
                why_it_matters=(
                    "Software systems are held together by invariants that are almost never written down. "
                    "Making invariants explicit would transform how we understand, test, and evolve software."
                ),
                what_is_unknown=(
                    "What fraction of software invariants can be automatically discovered? "
                    "How do invariants evolve as code changes? "
                    "Which invariant violations predict actual failures?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's invariant discovery engine, combined with runtime trace analysis "
                    "and failure replay, can correlate discovered invariants with actual failures, "
                    "providing the first empirical map of invariant importance."
                ),
                required_infrastructure=(
                    "Invariant inference across multiple dimensions (structural, behavioral, temporal), "
                    "invariant evolution tracking, violation-to-failure correlation."
                ),
                possible_breakthroughs=(
                    "Discovery that a small set of invariants predicts most failures. "
                    "Automatic invariant generation that matches human-written contracts. "
                    "Invariant-aware editing that prevents accidental violations."
                ),
                failure_cases=(
                    "Too many invariants (most are noise). "
                    "Important invariants are too complex to discover automatically. "
                    "Invariants change too fast to track meaningfully."
                ),
                priority=5,
            ),
            ResearchProgram(
                title="Software Simulation and Forecasting",
                why_it_matters=(
                    "The most powerful software understanding would be the ability to simulate "
                    "hypothetical changes and forecast their consequences before making them."
                ),
                what_is_unknown=(
                    "How accurate can software simulation be without full execution? "
                    "What is the tradeoff between simulation depth and prediction accuracy? "
                    "Can simulation substitute for testing?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's edit simulator and digital twin infrastructure enables "
                    "controlled experiments comparing simulated outcomes with actual outcomes. "
                    "This provides the first empirical calibration of simulation accuracy."
                ),
                required_infrastructure=(
                    "Edit simulator with configurable depth, outcome tracking, "
                    "accuracy measurement, and calibration pipelines."
                ),
                possible_breakthroughs=(
                    "Calibration of simulation accuracy against real edit outcomes. "
                    "Identification of which edits are most/least predictable. "
                    "Development of confidence-calibrated simulation that knows its limits."
                ),
                failure_cases=(
                    "Simulation accuracy is too low to be useful. "
                    "Confidence calibration fails (system is overconfident in wrong cases). "
                    "Full execution simulation is needed for acceptable accuracy."
                ),
                priority=6,
            ),
            ResearchProgram(
                title="Human-Agent Cognition Systems",
                why_it_matters=(
                    "The most impactful future is not agents replacing humans "
                    "but effective human-agent collaboration. We need to understand "
                    "how to design systems that amplify both."
                ),
                what_is_unknown=(
                    "What mental models do humans form of agent capabilities? "
                    "How does trust evolve over repeated interactions? "
                    "What feedback mechanisms best calibrate human expectations?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's intervention tracking, trust modeling, and cognition interface "
                    "create a complete testbed for studying human-agent collaboration. "
                    "Every interaction is recorded and analyzable."
                ),
                required_infrastructure=(
                    "Intervention tracking, trust metrics, shared cognition interfaces, "
                    "adaptation learning pipelines, usability measurement tools."
                ),
                possible_breakthroughs=(
                    "Quantification of trust-repair curves. "
                    "Design patterns for effective human-agent handoff. "
                    "Demonstration that adaptive autonomy outperforms fixed autonomy levels."
                ),
                failure_cases=(
                    "Human trust is too complex to model usefully. "
                    "Adaptive systems confuse rather than help. "
                    "Static autonomy levels are good enough."
                ),
                priority=7,
            ),
            ResearchProgram(
                title="Computational Software Theory",
                why_it_matters=(
                    "We need a formal theory of software as a computational object "
                    "that can be observed, modeled, simulated, and understood. "
                    "Without theory, we are engineering without physics."
                ),
                what_is_unknown=(
                    "What are the fundamental abstractions for computational software understanding? "
                    "Can we define formal measures of software complexity, coherence, and fragility? "
                    "What are the limits of software self-modeling?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme provides the empirical testbed for theoretical claims. "
                    "Hypotheses about software cognition can be implemented, measured, and falsified."
                ),
                required_infrastructure=(
                    "Formal framework definitions, measurement instruments, "
                    "hypothesis testing pipelines, theoretical result validation."
                ),
                possible_breakthroughs=(
                    "Development of a formal calculus for software cognition. "
                    "Discovery of conservation laws or invariants in software evolution. "
                    "Proof of fundamental limits on software self-understanding."
                ),
                failure_cases=(
                    "Software is too irregular for useful formalization. "
                    "Theory is too abstract to connect to practice. "
                    "Empirical results don't support theoretical predictions."
                ),
                priority=8,
            ),
            ResearchProgram(
                title="Architecture Forecasting",
                why_it_matters=(
                    "Software architecture decays predictably. If we can forecast decay, "
                    "we can intervene before systems become unmaintanable."
                ),
                what_is_unknown=(
                    "How predictable is architectural evolution? "
                    "What are leading indicators of architectural collapse? "
                    "Can intervention timing be optimized?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme's digital twin and drift detection infrastructure "
                    "enables longitudinal studies of architectural evolution. "
                    "Multiple repositories can be tracked over time."
                ),
                required_infrastructure=(
                    "Multi-repository tracking, drift metrics, "
                    "evolution forecasting, intervention effectiveness measurement."
                ),
                possible_breakthroughs=(
                    "Identification of universal leading indicators of architectural decay. "
                    "Demonstration that forecast-driven intervention extends system lifespan. "
                    "Development of architectural 'credit rating' for software systems."
                ),
                failure_cases=(
                    "Architectural evolution is too erratic to forecast. "
                    "Leading indicators don't generalize across systems. "
                    "Interventions come too late regardless of forecasting."
                ),
                priority=9,
            ),
            ResearchProgram(
                title="Software Cognition as Infrastructure",
                why_it_matters=(
                    "If software cognition becomes reliable infrastructure, "
                    "it changes how all software is built: self-aware systems, "
                    "continuous improvement, automated governance."
                ),
                what_is_unknown=(
                    "What reliability guarantees can software cognition provide? "
                    "How do we verify that cognition systems are correct? "
                    "What is the minimum viable cognition infrastructure?"
                ),
                what_lyme_can_uniquely_test=(
                    "Lyme can operate continuously on real repositories, "
                    "building the empirical track record needed to establish "
                    "reliability baselines and failure modes."
                ),
                required_infrastructure=(
                    "Production-ready runtime, reliability monitoring, "
                    "failure mode catalog, verification framework, "
                    "observatory mode with continuous operation."
                ),
                possible_breakthroughs=(
                    "First continuous software cognition infrastructure. "
                    "Reliability and accuracy benchmarks for production use. "
                    "Architectural patterns for building cognition-aware systems."
                ),
                failure_cases=(
                    "Cognition infrastructure is too expensive to run continuously. "
                    "Reliability is insufficient for production trust. "
                    "Value proposition doesn't justify infrastructure cost."
                ),
                priority=10,
            ),
        ]

    def generate_full_agenda(self) -> str:
        lines = []
        lines.append("# Lyme Long-Term Research Agenda")
        lines.append("")
        lines.append("## Preamble")
        lines.append(
            "This document is not a startup roadmap. It does not project user counts, "
            "funding rounds, or market share. It is a scientific research agenda for "
            "answering the question: Can software understand, model, and predict itself?"
        )
        lines.append("")
        lines.append("## Gupling Principles")
        lines.append("")
        lines.append("1. **Measurement First** — Every claim must be grounded in measurement")
        lines.append("2. **Falsifiability** — Every hypothesis must be testable")
        lines.append("3. **Cumulative Progress** — Results build on prior results")
        lines.append("4. **Open Science** — Methods and measurements are reproducible")
        lines.append("5. **Engineering Reality** — Theory must connect to practice")
        lines.append("")

        for i, program in enumerate(self.programs, 1):
            lines.append(f"## Research Program {i}: {program.title}")
            lines.append(f"**Priority:** {program.priority}")
            if program.dependencies:
                lines.append(f"**Depends on:** {', '.join(program.dependencies)}")
            lines.append("")
            lines.append(f"### Why It Matters")
            lines.append(program.why_it_matters)
            lines.append("")
            lines.append(f"### What Is Unknown")
            lines.append(program.what_is_unknown)
            lines.append("")
            lines.append(f"### What Lyme Can Uniquely Test")
            lines.append(program.what_lyme_can_uniquely_test)
            lines.append("")
            lines.append(f"### Required Infrastructure")
            lines.append(program.required_infrastructure)
            lines.append("")
            lines.append(f"### Possible Breakthroughs")
            lines.append(program.possible_breakthroughs)
            lines.append("")
            lines.append(f"### Failure Cases")
            lines.append(program.failure_cases)
            lines.append("")

        lines.append("## Cross-Cutting Themes")
        lines.append("")
        lines.append("### Uncertainty Quantification")
        lines.append(
            "Almost every program above requires better uncertainty handling. "
            "Knowing what we don't know is as important as knowing what we know."
        )
        lines.append("")
        lines.append("### Longitudinal Studies")
        lines.append(
            "Software evolution happens over months and years. Many of these "
            "questions require longitudinal data that only continuous observation can provide."
        )
        lines.append("")
        lines.append("### Ground Truth")
        lines.append(
            "The hardest problem in software cognition research is establishing ground truth. "
            "Lyme's design — with complete telemetry and replay capability — "
            "is uniquely positioned to address this."
        )
        lines.append("")
        lines.append("## Conclusion")
        lines.append(
            "This is a 3-5 year research agenda. Some programs may fail. "
            "Some may produce breakthroughs. All will produce measurements "
            "that advance our understanding of what it means for software to understand itself."
        )
        return "\n".join(lines)
