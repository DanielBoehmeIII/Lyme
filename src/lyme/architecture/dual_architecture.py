"""Lyme Dual Architecture: Product + Research fused at the telemetry layer.

Every product action generates research data.
Every research insight improves product behavior.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path


class LayerType(Enum):
    PRODUCT = "product"
    RESEARCH = "research"
    SHARED = "shared"


class ProductDomain(Enum):
    CLI = "cli"
    REPO_Q_A = "repo_qa"
    LOCAL_FIX = "local_fix"
    SEMANTIC_DIFF = "semantic_diff"
    TRACE_VIEWER = "trace_viewer"
    MEMORY_INSPECTION = "memory_inspection"
    MODEL_BENCHMARKING = "model_benchmarking"
    REPO_DOCTOR = "repo_doctor"
    ASK_WITH_EVIDENCE = "ask_with_evidence"
    HISTORY = "history"
    REPLAY = "replay"
    UNDO = "undo"
    AUDIT = "audit"


class ResearchDomain(Enum):
    COGNITION_TRACES = "cognition_traces"
    CAUSAL_GRAPHS = "causal_graphs"
    INVARIANT_DISCOVERY = "invariant_discovery"
    TEMPORAL_MODELING = "temporal_modeling"
    SCALING_LAWS = "scaling_laws"
    AGENT_COORDINATION = "agent_coordination"
    MEMORY_COMPRESSION = "memory_compression"
    FAILURE_ANALYSIS = "failure_analysis"
    HALLUCINATION_STUDY = "hallucination_study"
    CONTEXT_DEGRADATION = "context_degradation"


@dataclass
class ProductModule:
    domain: ProductDomain
    name: str
    description: str
    cli_command: Optional[str]
    telemetry_collected: List[str]
    experiments_enabled: List[str]
    privacy_level: str
    human_facing: bool = True

    def to_dict(self) -> dict:
        return {
            "domain": self.domain.value,
            "name": self.name,
            "description": self.description,
            "cli_command": self.cli_command,
            "telemetry_collected": self.telemetry_collected,
            "experiments_enabled": self.experiments_enabled,
            "privacy_level": self.privacy_level,
            "human_facing": self.human_facing,
        }


@dataclass
class ResearchModule:
    domain: ResearchDomain
    name: str
    description: str
    input_sources: List[str]
    output_artifacts: List[str]
    improves_product: List[str]
    privacy_sensitive: bool
    human_facing: bool = False

    def to_dict(self) -> dict:
        return {
            "domain": self.domain.value,
            "name": self.name,
            "description": self.description,
            "input_sources": self.input_sources,
            "output_artifacts": self.output_artifacts,
            "improves_product": self.improves_product,
            "privacy_sensitive": self.privacy_sensitive,
            "human_facing": self.human_facing,
        }


@dataclass
class SharedSubstrate:
    telemetry: bool = True
    storage: bool = True
    experiment_hooks: bool = True
    plugin_system: bool = True
    privacy_layer: bool = True
    replay_system: bool = True

    def to_dict(self) -> dict:
        return {
            "telemetry": self.telemetry,
            "storage": self.storage,
            "experiment_hooks": self.experiment_hooks,
            "plugin_system": self.plugin_system,
            "privacy_layer": self.privacy_layer,
            "replay_system": self.replay_system,
        }


PRODUCT_MODULES = [
    ProductModule(
        domain=ProductDomain.CLI,
        name="Command-Line Interface",
        description="Primary user interface for all Lyme operations",
        cli_command="lyme",
        telemetry_collected=["command_invoked", "duration_ms", "exit_code", "arg_pattern"],
        experiments_enabled=["usage_pattern_analysis", "command_frequency_study"],
        privacy_level="low",
    ),
    ProductModule(
        domain=ProductDomain.REPO_Q_A,
        name="Repository Q&A",
        description="Answer questions about a repository with evidence",
        cli_command="lyme ask",
        telemetry_collected=["question_topic", "context_files_used", "confidence_score",
                             "evidence_count", "contradictions_found", "refused_count"],
        experiments_enabled=["context_selection_effectiveness", "hallucination_rate",
                             "evidence_quality_scoring"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.LOCAL_FIX,
        name="Local Fix",
        description="Analyze and propose fixes for repository issues",
        cli_command="lyme fix",
        telemetry_collected=["issue_type", "files_affected", "fix_attempted",
                             "fix_success", "rollback_needed"],
        experiments_enabled=["fix_success_rate", "repair_strategy_effectiveness",
                             "safe_edit_protocol_evaluation"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.SEMANTIC_DIFF,
        name="Semantic Diff",
        description="Classify and explain diffs by semantic category",
        cli_command="lyme diff",
        telemetry_collected=["diff_size", "semantic_categories", "files_changed",
                             "classification_confidence"],
        experiments_enabled=["diff_classification_accuracy", "semantic_category_taxonomy"],
        privacy_level="low",
    ),
    ProductModule(
        domain=ProductDomain.TRACE_VIEWER,
        name="Trace Viewer",
        description="Visualize agent execution traces",
        cli_command="lyme trace",
        telemetry_collected=["trace_viewed", "filter_used", "export_format"],
        experiments_enabled=["trace_comprehension_study"],
        privacy_level="low",
    ),
    ProductModule(
        domain=ProductDomain.MEMORY_INSPECTION,
        name="Memory Inspection",
        description="Inspect and query persistent agent memory",
        cli_command="lyme memory",
        telemetry_collected=["memory_query", "results_count", "memory_type_accessed"],
        experiments_enabled=["memory_utilization_study", "forgetting_curve_measurement"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.MODEL_BENCHMARKING,
        name="Model Benchmarking",
        description="Compare model performance on coding tasks",
        cli_command="lyme bench",
        telemetry_collected=["model_name", "task_category", "score", "latency"],
        experiments_enabled=["model_ranking", "capability_matrix_evolution",
                             "scaling_law_discovery"],
        privacy_level="low",
    ),
    ProductModule(
        domain=ProductDomain.REPO_DOCTOR,
        name="Repo Doctor",
        description="Diagnose repository health and structure",
        cli_command="lyme doctor",
        telemetry_collected=["diagnosis_categories", "confidence_scores",
                             "risky_files_found", "invariants_inferred"],
        experiments_enabled=["diagnosis_accuracy", "invariant_discovery_effectiveness",
                             "repo_health_metrics"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.ASK_WITH_EVIDENCE,
        name="Ask With Evidence",
        description="Evidence-grounded repository Q&A with confidence scoring",
        cli_command="lyme ask",
        telemetry_collected=["claim_count", "verified_claims", "refused_claims",
                             "uncertainty_marked", "citation_types"],
        experiments_enabled=["claim_verification_accuracy", "uncertainty_calibration",
                             "evidence_trail_quality"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.HISTORY,
        name="History",
        description="View session history with traces and artifacts",
        cli_command="lyme history",
        telemetry_collected=["history_query", "filter_type", "export_requested"],
        experiments_enabled=["session_pattern_analysis"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.REPLAY,
        name="Replay",
        description="Replay previous sessions deterministically",
        cli_command="lyme replay",
        telemetry_collected=["replay_id", "replay_speed", "abandoned"],
        experiments_enabled=["replay_fidelity_analysis", "divergence_detection"],
        privacy_level="low",
    ),
    ProductModule(
        domain=ProductDomain.UNDO,
        name="Undo",
        description="Reverse previous agent actions",
        cli_command="lyme undo",
        telemetry_collected=["undo_target", "files_restored", "success"],
        experiments_enabled=["undo_reliability", "action_reversibility_study"],
        privacy_level="medium",
    ),
    ProductModule(
        domain=ProductDomain.AUDIT,
        name="Audit",
        description="Full action audit trail with replay and patch inspection",
        cli_command="lyme audit",
        telemetry_collected=["audit_run", "artifacts_inspected", "patch_verified"],
        experiments_enabled=["audit_trail_completeness", "action_attribution_accuracy"],
        privacy_level="high",
    ),
]

RESEARCH_MODULES = [
    ResearchModule(
        domain=ResearchDomain.COGNITION_TRACES,
        name="Cognitive Tracing",
        description="Record and analyze agent decision processes",
        input_sources=["all_product_actions", "model_responses", "tool_calls"],
        output_artifacts=["thought_graphs", "decision_trees", "branch_analyses"],
        improves_product=["confidence_scoring",
                          "hallucination_detection", "context_optimization"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.CAUSAL_GRAPHS,
        name="Causal Graph Analysis",
        description="Model cause-effect relationships in software systems",
        input_sources=["git_history", "file_dependencies", "agent_traces"],
        output_artifacts=["causal_graphs", "risk_models", "impact_zones"],
        improves_product=["risk_aware_fix", "impact_estimation",
                          "safe_edit_zones"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.INVARIANT_DISCOVERY,
        name="Invariant Discovery",
        description="Discover architectural invariants and detect violations",
        input_sources=["code_analysis", "git_history", "build_output"],
        output_artifacts=["invariant_sets", "violation_reports",
                          "repair_suggestions"],
        improves_product=["edit_safety_checks",
                          "architectural_guardrails", "refactor_safety"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.TEMPORAL_MODELING,
        name="Temporal Modeling",
        description="Model software evolution over time",
        input_sources=["git_history", "benchmark_history",
                       "memory_evolution"],
        output_artifacts=["evolution_models", "decay_curves",
                          "trend_predictions"],
        improves_product=["staleness_detection",
                          "maintenance_forecasting", "memory_pruning"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.SCALING_LAWS,
        name="Scaling Law Experiments",
        description="Discover how agent performance scales with model size, context, etc.",
        input_sources=["benchmark_runs", "model_evaluations"],
        output_artifacts=["scaling_coefficients",
                          "emergence_thresholds", "diminishing_returns_points"],
        improves_product=["model_selection",
                          "context_budget_optimization",
                          "cost_performance_tradeoffs"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.AGENT_COORDINATION,
        name="Agent Coordination",
        description="Study multi-agent collaboration patterns",
        input_sources=["debate_sessions", "specialization_experiments",
                       "topology_simulations"],
        output_artifacts=["coordination_graphs",
                          "overhead_measurements", "specialization_metrics"],
        improves_product=["debate_quality", "task_routing",
                          "collaboration_efficiency"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.MEMORY_COMPRESSION,
        name="Memory Compression",
        description="Study compression strategies for codebase understanding",
        input_sources=["compression_pipeline", "memory_store",
                       "retrieval_patterns"],
        output_artifacts=["compression_ratios",
                          "retrieval_accuracy_curves",
                          "representation_quality_metrics"],
        improves_product=["context_budget", "retrieval_quality",
                          "compression_strategy"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.FAILURE_ANALYSIS,
        name="Failure Analysis",
        description="Classify and analyze agent failure modes",
        input_sources=["failed_runs", "low_confidence_actions",
                       "hallucination_events"],
        output_artifacts=["failure_taxonomy", "failure_signatures",
                          "recovery_strategies"],
        improves_product=["failure_detection", "graceful_degradation",
                          "retry_strategies"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.HALLUCINATION_STUDY,
        name="Hallucination Study",
        description="Detect and measure hallucination patterns in agent responses",
        input_sources=["claim_verification", "tool_call_accuracy",
                       "code_validation"],
        output_artifacts=["hallucination_rates",
                          "hallucination_type_taxonomy",
                          "context_correlation_models"],
        improves_product=["claim_filtering",
                          "uncertainty_labeling", "verification_gating"],
        privacy_sensitive=False,
    ),
    ResearchModule(
        domain=ResearchDomain.CONTEXT_DEGRADATION,
        name="Context Degradation",
        description="Measure how agent performance degrades with context size",
        input_sources=["stress_experiments", "context_budget_tracking",
                       "attention_distribution"],
        output_artifacts=["degradation_curves", "collapse_points",
                          "context_efficiency_metrics"],
        improves_product=["context_windowing",
                          "retrieval_prioritization", "compression_tuning"],
        privacy_sensitive=False,
    ),
]


@dataclass
class ArchitectureConfig:
    product_enabled: Dict[ProductDomain, bool] = field(default_factory=dict)
    research_enabled: Dict[ResearchDomain, bool] = field(default_factory=dict)
    shared: SharedSubstrate = field(default_factory=SharedSubstrate)
    privacy_policy_path: Optional[str] = None
    storage_root: str = "./lyme-output"

    def __post_init__(self):
        for domain in ProductDomain:
            if domain not in self.product_enabled:
                self.product_enabled[domain] = True
        for domain in ResearchDomain:
            if domain not in self.research_enabled:
                self.research_enabled[domain] = True


class ArchitectureRegistry:
    _instance: Optional["ArchitectureRegistry"] = None

    def __init__(self, config: Optional[ArchitectureConfig] = None):
        self.config = config or ArchitectureConfig()
        self._product_modules: Dict[ProductDomain, ProductModule] = {
            m.domain: m for m in PRODUCT_MODULES
        }
        self._research_modules: Dict[ResearchDomain, ResearchModule] = {
            m.domain: m for m in RESEARCH_MODULES
        }

    @classmethod
    def get_instance(cls, config: Optional[ArchitectureConfig] = None) -> "ArchitectureRegistry":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def get_product(self, domain: ProductDomain) -> Optional[ProductModule]:
        return self._product_modules.get(domain)

    def get_research(self, domain: ResearchDomain) -> Optional[ResearchModule]:
        return self._research_modules.get(domain)

    def list_product_modules(self) -> List[ProductModule]:
        return [m for d, m in self._product_modules.items()
                if self.config.product_enabled.get(d, True)]

    def list_research_modules(self) -> List[ResearchModule]:
        return [m for d, m in self._research_modules.items()
                if self.config.research_enabled.get(d, True)]

    def product_telemetry_schema(self) -> Dict[str, List[str]]:
        return {m.domain.value: m.telemetry_collected for m in self.list_product_modules()}

    def research_feeds_into_product(self) -> Dict[str, List[str]]:
        result = {}
        for m in self.list_research_modules():
            for improvement in m.improves_product:
                if improvement not in result:
                    result[improvement] = []
                result[improvement].append(m.domain.value)
        return result

    def product_feeds_into_research(self) -> Dict[str, List[str]]:
        result = {}
        for m in self.list_product_modules():
            for experiment in m.experiments_enabled:
                if experiment not in result:
                    result[experiment] = []
                result[experiment].append(m.domain.value)
        return result

    def to_dict(self) -> dict:
        return {
            "architecture": "dual_layer",
            "product_modules": [m.to_dict() for m in self.list_product_modules()],
            "research_modules": [m.to_dict() for m in self.list_research_modules()],
            "shared_substrate": self.config.shared.to_dict(),
            "product_research_feed": self.product_feeds_into_research(),
            "research_product_feed": self.research_feeds_into_product(),
        }


def get_architecture() -> ArchitectureRegistry:
    return ArchitectureRegistry.get_instance()
