import sys
import json
import random
import argparse
from pathlib import Path
from typing import List, Optional

from . import __version__
from .config import Settings, load_config, AgentConfig
from .ecosystem.dependency_engine import (
    DependencyGraphEngine, LibraryNode, DependencyEdge, DependencyType, EcosystemPhase,
)
from .ecosystem.propagation import TemporalPropagationAnalyzer
from .ecosystem.stability import EcosystemStabilityAnalyzer
from .ecosystem.visualization import EcosystemVisualization
from .ecosystem.benchmark_datasets import EcosystemBenchmarkDatasets
from .ecosystem_risk.forecasting import EcosystemRiskForecaster
from .ecosystem_risk.scoring import RiskScoringEngine, VulnerabilityPropagationScorer
from .framework_observatory import (
    FrameworkObservatory, FrameworkEvolutionReport,
    FrameworkKnowledgeBase,
    ReactEcosystemKnowledge, FastAPIEcosystemKnowledge,
    RustAsyncEcosystemKnowledge, NextJSEcosystemKnowledge,
)
from .architecture.discovery import ArchitecturePatternDiscovery, ArchitecturePatternType
from .architecture.fitness import ArchitectureFitnessEngine
from .architecture.advisor import ArchitectureAdvisor, ArchitectureConstraint, ArchitectureType
from .memory_fabric import MemoryFabric, FabricMemory, MemoryQuery, MemoryCategory, ProvenanceEntry
from .compression.semantic_compression import SemanticCompressionEngine, AbstractionType
from .similarity import RepositorySimilarityEngine, RepoProfile
from .observatory.observatory_v2 import ObservatoryV2, ObservatoryV2Config, IntegratedObservation
from .civilization_maps import SoftwareCivilizationMapper
from .benchmark import BenchmarkEngine, ScenarioRegistry
from .benchmark import __scenarios__  # register all scenarios
from .cognition import (
    TraceCompressor, ThoughtAnalyzer, AnomalyDetector,
)
from .graph import (
    CausalInferenceEngine, CausalGraphRenderer, FailurePropagator,
    ImpactEstimator, DownstreamAnalyzer,
)
from .discovery import (
    InvariantInferenceEngine, ViolationDetector, ContradictionDetector,
    RepairSuggester, EvolutionTracker,
)
from .intent import IntentInferenceEngine, UncertaintyEstimator, IntentEvolutionTracker
from .evolution import (
    EvolutionAnalyzer, TrendDetector, StabilityAnalyzer, ComplexityTracker,
    RefactorWaveDetector, AnomalyDetector as EvolutionAnomalyDetector,
    EvolutionForecaster, BottleneckPredictor,
    SoftwareEvolutionMetricsEngine, MotifDiscoveryEngine,
    GenomeExtractor, GenomeComparator, GenomePredictor, GenomeClusterer,
)
from .prediction import FailurePredictor, PredictionEvaluator, FeedbackLoop
from .learning import HistoricalLearningEngine
from .skills import (
    SkillLibrary, SkillExtractor, SkillRetriever, SkillExecutor, Skill, SkillType,
    SkillTransferEngine, TransferExperiment, SkillCritic,
)
from .society import (
    DebateEngine, DebateConfig, SpecializationEngine, DomainExpertise,
    CoordinationCompressor, TopologyExperiment, TopologyType,
    CollectiveMemory, MemoryEntry, MemoryType, MemoryQuery,
    SynchronizationProtocol, TrustWeightingSystem,
    SocietySimulator, SimulationConfig,
    MarketCoordinationEngine, MarketAgent, MarketRole,
)
from .research import (
    SoftwareIntelligenceFramework, BenchmarkGenerator, AntiGamingProtection,
    ScalingLawExperiment, VariableType, AutomatedExperimenter,
    ExperimentGenerator, AutomatedAblation, AblationComponent,
    ResearchReportGenerator,
)
from .replay import DeterministicReplayer, DiffReplayer
from .stress import StressExperiment, SyntheticRepoGenerator, ContextDegradationAnalyzer
from .store import EventStore
from .ui.timeline_viewer import render_timeline
from .ui.thought_viewer import render_cognitive_trace
from .ui.metrics_dashboard import render_dashboard
from .self_modeling import SelfDescriptionGenerator, SelfDescriptionUpdateTrigger
from .self_improving import (
    WorkflowEvolutionEngine, WorkflowStep, StepType,
    PromptEvolutionEngine, PromptGenome,
    CognitiveArchitectureSearch,
)
from .archfile import (
    ArchitectureFileGenerator, ArchitectureFileUpdater,
    ArchitectureFileValidator, ArchitectureViolationDetector,
    ArchitectureFileRenderer,
)
from .planning import ArchitectureAwarePlanner, PlannerConfig, BaselinePlanner


class LymeCLI:
    def __init__(self):
        self.settings: Optional[Settings] = None

    def run(self, argv: List[str] = None):
        if argv is None:
            argv = sys.argv[1:]

        parser = argparse.ArgumentParser(
            description="Lyme — Research infrastructure for local coding agent evaluation",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  lyme run --scenario latency-baseline
  lyme list-scenarios
  lyme replay <trace-id>
  lyme compare --scenario multi-file-edit-consistency
  lyme stress repo-size
  lyme ui timeline <run-id>
  lyme ui thought <run-id>
  lyme ui dashboard
""",
        )
        parser.add_argument("--config", "-c", help="Path to config file")
        parser.add_argument("--verbose", "-v", action="store_true")
        parser.add_argument("--version", action="version", version=f"lyme v{__version__}")

        subparsers = parser.add_subparsers(dest="command", help="Commands")

        run_parser = subparsers.add_parser("run", help="Run benchmarks")
        run_parser.add_argument("--scenario", "-s", nargs="+", help="Scenario names to run")
        run_parser.add_argument("--agent", "-a", nargs="+", help="Agent names to use")
        run_parser.add_argument("--all", action="store_true", help="Run all scenarios")
        run_parser.add_argument("--parallel", action="store_true", help="Run in parallel")
        run_parser.add_argument("--output", "-o", help="Output directory")

        list_parser = subparsers.add_parser("list-scenarios", help="List available scenarios")

        replay_parser = subparsers.add_parser("replay", help="Replay a trace")
        replay_parser.add_argument("trace_id", help="Trace ID to replay")
        replay_parser.add_argument("--speed", type=float, default=1.0, help="Playback speed")

        compare_parser = subparsers.add_parser("compare", help="Compare agents on a scenario")
        compare_parser.add_argument("--scenario", required=True, help="Scenario to compare on")
        compare_parser.add_argument("--agents", nargs="+", default=[], help="Agents to compare")

        ask_parser = subparsers.add_parser("ask", help="Ask evidence-grounded questions about a repo")
        ask_parser.add_argument("question", nargs="+", help="Question to ask")
        ask_parser.add_argument("--repo", "-r", default=".", help="Path to repository")
        ask_parser.add_argument("--output", "-o", help="Output file for answer")

        doctor_parser = subparsers.add_parser("doctor", help="Diagnose repository health")
        doctor_parser.add_argument("repo_path", nargs="?", default=".",
                                   help="Path to repository (default: current dir)")
        doctor_parser.add_argument("--output", "-o", help="Output file for diagnosis JSON")
        doctor_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")

        stress_parser = subparsers.add_parser("stress", help="Run stress experiments")
        stress_parser.add_argument("experiment", choices=["repo-size", "hidden-coupling"])
        stress_parser.add_argument("--agent", help="Agent to use")
        stress_parser.add_argument("--output", "-o", help="Output directory")
        stress_parser.add_argument("--generate", action="store_true",
                                   help="Generate synthetic repos without running agents")

        ui_parser = subparsers.add_parser("ui", help="Generate UI visualizations")
        ui_parser.add_argument("type", choices=["timeline", "thought", "dashboard", "branch"])
        ui_parser.add_argument("run_id", nargs="?", help="Run ID")
        ui_parser.add_argument("--output", "-o", help="Output HTML file")

        history_parser = subparsers.add_parser("history", help="Show action history")
        history_parser.add_argument("--limit", type=int, default=20, help="Number of entries")
        history_parser.add_argument("--kind", help="Filter by action kind")

        undo_parser = subparsers.add_parser("undo", help="Undo a previous action")
        undo_parser.add_argument("audit_id", help="Audit ID to undo")
        undo_parser.add_argument("--force", action="store_true", help="Force undo even if risky")

        audit_parser = subparsers.add_parser("audit", help="Full audit report for an action")
        audit_parser.add_argument("audit_id", help="Audit ID to inspect")
        audit_parser.add_argument("--output", "-o", help="Output file")

        info_parser = subparsers.add_parser("info", help="Show info about a trace")

        self_parser = subparsers.add_parser("self", help="Repository self-description")
        self_parser.add_argument("--repo", "-r", default=".", help="Path to repository")
        self_parser.add_argument("--update", action="store_true", help="Force update")
        self_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
        self_parser.add_argument("--output", "-o", help="Output file")

        archfile_parser = subparsers.add_parser("archfile", help="Machine-readable architecture file")
        archfile_sub = archfile_parser.add_subparsers(dest="archfile_command", help="Architecture file commands")
        archfile_gen = archfile_sub.add_parser("generate", help="Generate architecture file")
        archfile_gen.add_argument("--repo", "-r", default=".", help="Path to repository")
        archfile_gen.add_argument("--output", "-o", help="Output file")
        archfile_validate = archfile_sub.add_parser("validate", help="Validate architecture file")
        archfile_validate.add_argument("--repo", "-r", default=".", help="Path to repository")
        archfile_violations = archfile_sub.add_parser("violations", help="Detect architecture violations")
        archfile_violations.add_argument("--repo", "-r", default=".", help="Path to repository")
        archfile_view = archfile_sub.add_parser("view", help="View architecture as markdown")
        archfile_view.add_argument("--repo", "-r", default=".", help="Path to repository")
        archfile_mermaid = archfile_sub.add_parser("mermaid", help="Render architecture as Mermaid diagram")
        archfile_mermaid.add_argument("--repo", "-r", default=".", help="Path to repository")

        plan_parser = subparsers.add_parser("plan", help="Architecture-aware planning")
        plan_parser.add_argument("task", nargs="+", help="Task description")
        plan_parser.add_argument("--repo", "-r", default=".", help="Path to repository")
        plan_parser.add_argument("--baseline", action="store_true", help="Use baseline planner for comparison")
        plan_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
        plan_parser.add_argument("--output", "-o", help="Output file")

        report_parser = subparsers.add_parser("report", help="Generate benchmark reports")
        report_parser.add_argument("run_id", nargs="*", help="Run IDs")
        report_parser.add_argument("--all", action="store_true", help="Report on all runs")
        report_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")

        graph_parser = subparsers.add_parser("graph", help="Causal software graph analysis")
        graph_sub = graph_parser.add_subparsers(dest="graph_command", help="Graph commands")
        graph_infer = graph_sub.add_parser("infer", help="Build causal graph from repo")
        graph_infer.add_argument("repo_path", help="Path to repository")
        graph_infer.add_argument("--output", "-o", help="Output JSON file")
        graph_risk = graph_sub.add_parser("risk", help="Analyze breakage risk")
        graph_risk.add_argument("repo_path", help="Path to repository")
        graph_risk.add_argument("file", help="File path to analyze")
        graph_risk.add_argument("--output", "-o", help="Output JSON file")
        graph_viz = graph_sub.add_parser("visualize", help="Generate graph visualization")
        graph_viz.add_argument("repo_path", help="Path to repository")
        graph_viz.add_argument("--format", choices=["html", "graphviz", "mermaid", "d3"], default="html")
        graph_viz.add_argument("--output", "-o", help="Output file")
        graph_amplify = graph_sub.add_parser("amplify", help="Find amplification zones")
        graph_amplify.add_argument("repo_path", help="Path to repository")
        graph_hidden = graph_sub.add_parser("hidden", help="Find hidden dependencies")
        graph_hidden.add_argument("repo_path", help="Path to repository")

        discover_parser = subparsers.add_parser("discover", help="Discover architectural invariants")
        discover_sub = discover_parser.add_subparsers(dest="discover_command", help="Discovery commands")
        discover_infer = discover_sub.add_parser("invariants", help="Discover architectural invariants")
        discover_infer.add_argument("repo_path", help="Path to repository")
        discover_infer.add_argument("--min-confidence", type=float, default=0.3, help="Minimum confidence threshold")
        discover_infer.add_argument("--output", "-o", help="Output JSON file")
        discover_violate = discover_sub.add_parser("violations", help="Detect invariant violations")
        discover_violate.add_argument("repo_path", help="Path to repository")
        discover_violate.add_argument("--output", "-o", help="Output JSON file")
        discover_contradict = discover_sub.add_parser("contradictions", help="Find contradictory invariants")
        discover_contradict.add_argument("repo_path", help="Path to repository")
        discover_repair = discover_sub.add_parser("repair", help="Generate repair suggestions")
        discover_repair.add_argument("repo_path", help="Path to repository")
        discover_trend = discover_sub.add_parser("fragility", help="Estimate architectural fragility")
        discover_trend.add_argument("repo_path", help="Path to repository")

        intent_parser = subparsers.add_parser("intent", help="Software intent modeling")
        intent_sub = intent_parser.add_subparsers(dest="intent_command", help="Intent commands")
        intent_infer = intent_sub.add_parser("infer", help="Infer software intent")
        intent_infer.add_argument("repo_path", help="Path to repository")
        intent_infer.add_argument("--output", "-o", help="Output JSON file")
        intent_uncertainty = intent_sub.add_parser("uncertainty", help="Estimate intent uncertainty")
        intent_uncertainty.add_argument("repo_path", help="Path to repository")

        evolution_parser = subparsers.add_parser("evolution", help="Repository evolution analysis")
        evolution_sub = evolution_parser.add_subparsers(dest="evolution_command", help="Evolution commands")
        evolution_analyze = evolution_sub.add_parser("analyze", help="Analyze repository evolution")
        evolution_analyze.add_argument("repo_path", help="Path to repository")
        evolution_trend = evolution_sub.add_parser("trend", help="Detect evolution trends")
        evolution_trend.add_argument("repo_path", help="Path to repository")
        evolution_complexity = evolution_sub.add_parser("complexity", help="Track complexity accumulation")
        evolution_complexity.add_argument("repo_path", help="Path to repository")
        evolution_refactor = evolution_sub.add_parser("refactor-waves", help="Detect refactor waves")
        evolution_refactor.add_argument("repo_path", help="Path to repository")
        evolution_anomaly = evolution_sub.add_parser("anomalies", help="Detect evolution anomalies")
        evolution_anomaly.add_argument("repo_path", help="Path to repository")
        evolution_forecast = evolution_sub.add_parser("forecast", help="Forecast evolution trends")
        evolution_forecast.add_argument("repo_path", help="Path to repository")
        evolution_metrics = evolution_sub.add_parser("metrics", help="Run software evolution metrics engine")
        evolution_metrics.add_argument("repo_path", help="Path to repository")
        evolution_metrics.add_argument("--output", "-o", help="Output JSON file")
        evolution_metrics.add_argument("--report", action="store_true", help="Generate full report")
        evolution_motifs = evolution_sub.add_parser("motifs", help="Discover evolutionary motifs")
        evolution_motifs.add_argument("repo_path", help="Path to repository")
        evolution_motifs.add_argument("--output", "-o", help="Output JSON file")
        evolution_genome = evolution_sub.add_parser("genome", help="Extract repository genome")
        evolution_genome.add_argument("repo_path", help="Path to repository")
        evolution_genome.add_argument("--output", "-o", help="Output JSON file")
        evolution_genome.add_argument("--compare", help="Compare with another repo genome")
        evolution_genome.add_argument("--predict", action="store_true", help="Run genome predictions")
        evolution_genome.add_argument("--cluster", nargs="+", help="Cluster multiple repos (paths)")

        predict_parser = subparsers.add_parser("predict", help="Failure prediction")
        predict_sub = predict_parser.add_subparsers(dest="predict_command", help="Prediction commands")
        predict_run = predict_sub.add_parser("run", help="Run failure prediction")
        predict_run.add_argument("repo_path", help="Path to repository")
        predict_run.add_argument("--output", "-o", help="Output JSON file")

        learn_parser = subparsers.add_parser("learn", help="Learn from repository history")
        learn_sub = learn_parser.add_subparsers(dest="learn_command", help="Learning commands")
        learn_extract = learn_sub.add_parser("extract", help="Extract historical patterns")
        learn_extract.add_argument("repo_path", help="Path to repository")
        learn_query = learn_sub.add_parser("query", help="Query historical memory")
        learn_query.add_argument("repo_path", help="Path to repository")
        learn_query.add_argument("query", help="Query string")

        skill_parser = subparsers.add_parser("skill", help="Skill library management")
        skill_sub = skill_parser.add_subparsers(dest="skill_command", help="Skill commands")
        skill_list = skill_sub.add_parser("list", help="List all skills")
        skill_list.add_argument("--type", help="Filter by skill type")
        skill_search = skill_sub.add_parser("search", help="Search skills")
        skill_search.add_argument("query", help="Search query")
        skill_extract = skill_sub.add_parser("extract", help="Extract skill from run data")
        skill_extract.add_argument("run_id", help="Run ID to extract from")
        skill_transfer = skill_sub.add_parser("transfer", help="Transfer skills to another repo")
        skill_transfer.add_argument("target_repo", help="Target repository path")
        skill_critique = skill_sub.add_parser("critique", help="Critique a skill for applicability")
        skill_critique.add_argument("skill_id", help="Skill ID to critique")

        improve_parser = subparsers.add_parser("improve", help="Self-improving agent infrastructure")
        improve_sub = improve_parser.add_subparsers(dest="improve_command", help="Improve commands")
        improve_workflow = improve_sub.add_parser("workflow", help="Workflow evolution engine")
        improve_workflow.add_argument("action", choices=["observe", "compress", "mutate", "evolve", "stats"])
        improve_workflow.add_argument("--steps", type=int, default=5, help="Number of workflow steps to generate")
        improve_workflow.add_argument("--generations", type=int, default=5, help="Number of evolution generations")
        improve_workflow.add_argument("--output", "-o", help="Output JSON file")
        improve_prompt = improve_sub.add_parser("prompt", help="Autonomous prompt evolution")
        improve_prompt.add_argument("action", choices=["seed", "evolve", "best", "stats"])
        improve_prompt.add_argument("--generations", type=int, default=10, help="Number of evolution generations")
        improve_prompt.add_argument("--output", "-o", help="Output JSON file")
        improve_arch = improve_sub.add_parser("arch", help="Cognitive architecture search")
        improve_arch.add_argument("method", choices=["random", "evolutionary", "exhaustive"], default="evolutionary", nargs="?")
        improve_arch.add_argument("--samples", type=int, default=20, help="Random search samples")
        improve_arch.add_argument("--population", type=int, default=10, help="Evolutionary population size")
        improve_arch.add_argument("--generations", type=int, default=5, help="Evolutionary generations")
        improve_arch.add_argument("--output", "-o", help="Output JSON file")

        society_parser = subparsers.add_parser("society", help="Multi-agent society")
        society_sub = society_parser.add_subparsers(dest="society_command", help="Society commands")
        society_debate = society_sub.add_parser("debate", help="Run agent debate")
        society_debate.add_argument("problem", help="Problem to debate")
        society_specialize = society_sub.add_parser("specialize", help="Run specialization experiment")
        society_specialize.add_argument("--agents", type=int, default=5, help="Number of agents")
        society_specialize.add_argument("--tasks", type=int, default=20, help="Number of tasks")
        society_topology = society_sub.add_parser("topology", help="Run topology experiment")
        society_topology.add_argument("--topology", choices=["star", "ring", "mesh", "tree", "line", "fully_connected"], default="mesh")
        society_topology.add_argument("--agents", type=int, default=5)
        society_topology.add_argument("--tasks", type=int, default=10)
        society_memory = society_sub.add_parser("memory", help="Persistent multi-agent collective memory")
        society_memory.add_argument("action", choices=["store", "search", "stats", "resolve", "trust"])
        society_memory.add_argument("--content", help="Memory content to store")
        society_memory.add_argument("--type", choices=["procedural", "episodic", "semantic", "strategic", "coordination", "uncertainty"], default="semantic")
        society_memory.add_argument("--agent", default="agent_0", help="Agent ID")
        society_memory.add_argument("--query", help="Search query")
        society_memory.add_argument("--output", "-o", help="Output JSON file")
        society_simulate = society_sub.add_parser("simulate", help="Run agent society simulation")
        society_simulate.add_argument("--agents", type=int, default=20, help="Number of agents")
        society_simulate.add_argument("--tasks", type=int, default=200, help="Number of tasks")
        society_simulate.add_argument("--ticks", type=int, default=100, help="Simulation ticks")
        society_simulate.add_argument("--seed", type=int, default=42, help="Random seed")
        society_simulate.add_argument("--output", "-o", help="Output JSON file")
        society_market = society_sub.add_parser("market", help="Market-based coordination simulation")
        society_market.add_argument("--agents", type=int, default=10, help="Number of agents")
        society_market.add_argument("--tasks", type=int, default=30, help="Number of tasks")
        society_market.add_argument("--epochs", type=int, default=50, help="Number of epochs")
        society_market.add_argument("--output", "-o", help="Output JSON file")
        society_market.add_argument("--compare", action="store_true", help="Compare with centralized orchestration")

        observe_parser = subparsers.add_parser("observe", help="Lyme Observatory v1 — continuous repository intelligence")
        observe_sub = observe_parser.add_subparsers(dest="observe_command", help="Observe commands")
        observe_run = observe_sub.add_parser("run", help="Run continuous observatory")
        observe_run.add_argument("--repo", "-r", default=".", help="Repository path")
        observe_run.add_argument("--interval", type=int, default=3600, help="Poll interval in seconds")
        observe_run.add_argument("--iterations", type=int, default=3, help="Number of observation iterations")
        observe_run.add_argument("--output", "-o", help="Output directory")
        observe_forecast = observe_sub.add_parser("forecast", help="Run health forecasting")
        observe_forecast.add_argument("--repo", "-r", default=".", help="Repository path")
        observe_forecast.add_argument("--horizon", type=int, default=30, help="Forecast horizon in days")
        observe_forecast.add_argument("--output", "-o", help="Output JSON file")
        observe_ui = observe_sub.add_parser("ui", help="Generate observatory dashboard HTML")
        observe_ui.add_argument("--output", "-o", default="lyme-observatory.html", help="Output HTML file")

        research_parser = subparsers.add_parser("research", help="Software intelligence research")
        research_sub = research_parser.add_subparsers(dest="research_command", help="Research commands")
        research_dimensions = research_sub.add_parser("dimensions", help="Define software intelligence dimensions")
        research_dimensions.add_argument("--report", action="store_true", help="Generate research report")
        research_benchmarks = research_sub.add_parser("benchmarks", help="Generate research benchmarks")
        research_benchmarks.add_argument("--count", type=int, default=10, help="Number of benchmarks")
        research_scaling = research_sub.add_parser("scaling", help="Run scaling law experiments")
        research_scaling.add_argument("--auto", action="store_true", help="Run automated experiments")

        research_experiment = research_sub.add_parser("experiment", help="Generate experiment plan from research question")
        research_experiment.add_argument("question", nargs="+", help="Research question")
        research_experiment.add_argument("--output", "-o", help="Output file")

        research_ablation = research_sub.add_parser("ablation", help="Run automated ablation study")
        research_ablation.add_argument("--components", nargs="+", default=[], help="Components to ablate")
        research_ablation.add_argument("--output", "-o", help="Output file")

        research_report = research_sub.add_parser("report", help="Generate research report from experiment data")
        research_report.add_argument("--title", default="Experiment Results", help="Report title")
        research_report.add_argument("--control", help="JSON file with control metrics")
        research_report.add_argument("--treatment", help="JSON file with treatment metrics")
        research_report.add_argument("--output", "-o", help="Output file")

        # v0.3 commands
        cross_repo_parser = subparsers.add_parser("cross-repo", help="Cross-repository pattern mining")
        cross_repo_parser.add_argument("--dirs", nargs="+", required=True, help="Repository directories to mine")
        cross_repo_parser.add_argument("--output", "-o", default="lyme-output/cross-repo", help="Output directory")
        cross_repo_parser.add_argument("--anonymize", action="store_true", default=True, help="Anonymize repo fingerprints")
        cross_repo_parser.add_argument("--clusters", type=int, default=5, help="Number of clusters")

        ecosystem_parser = subparsers.add_parser("ecosystem", help="Ecosystem knowledge graph and dependency modeling")
        eco_sub = ecosystem_parser.add_subparsers(dest="eco_command", help="Ecosystem commands")
        eco_query = eco_sub.add_parser("query", help="Query ecosystem knowledge graph")
        eco_query.add_argument("--library", "-l", help="Library name to query")
        eco_compat = eco_sub.add_parser("compat", help="Check dependency compatibility")
        eco_compat.add_argument("--dep-file", "-d", help="Dependency file to check")
        eco_security = eco_sub.add_parser("security", help="List security advisories")
        eco_info = eco_sub.add_parser("info", help="Ecosystem graph info")

        eco_deps = eco_sub.add_parser("deps", help="Dependency ecosystem modeling")
        eco_deps.add_argument("action", choices=["build", "analyze", "chains", "visualize", "snapshot", "compare", "propagate", "migrations", "vulnerability"])
        eco_deps.add_argument("--ecosystem", default="python", choices=["python", "javascript", "rust"], help="Ecosystem to analyze")
        eco_deps.add_argument("--library", help="Library name for analysis")
        eco_deps.add_argument("--output", "-o", help="Output file")

        eco_risk = eco_sub.add_parser("risk", help="Ecosystem risk assessment")
        eco_risk.add_argument("action", choices=["assess", "report", "migration", "vulnerabilities", "propagate"])
        eco_risk.add_argument("--library", help="Library name to assess")
        eco_risk.add_argument("--source", help="Source framework for migration")
        eco_risk.add_argument("--target", help="Target framework for migration")
        eco_risk.add_argument("--dep-file", help="Dependency file to scan")
        eco_risk.add_argument("--output", "-o", help="Output file")

        fw_obs_parser = subparsers.add_parser("fw-obs", help="Framework evolution observatory")
        fw_obs_sub = fw_obs_parser.add_subparsers(dest="fw_obs_command", help="Framework observatory commands")
        fw_report = fw_obs_sub.add_parser("report", help="Framework evolution report")
        fw_report.add_argument("framework", choices=["react", "fastapi", "nextjs", "tokio"], help="Framework to analyze")
        fw_report.add_argument("--output", "-o", help="Output file")
        fw_compare = fw_obs_sub.add_parser("compare", help="Compare framework evolution")
        fw_compare.add_argument("a", help="First framework")
        fw_compare.add_argument("b", help="Second framework")
        fw_drift = fw_obs_sub.add_parser("drift", help="Detect convention drift")
        fw_drift.add_argument("framework", help="Framework to analyze")
        fw_bugs = fw_obs_sub.add_parser("bugs", help="Common bug pattern trends")
        fw_bugs.add_argument("framework", help="Framework to analyze")
        fw_kb = fw_obs_sub.add_parser("knowledge", help="List framework knowledge base")
        fw_kb.add_argument("--framework", help="Specific framework")

        arch_parser = subparsers.add_parser("arch", help="Architecture intelligence")
        arch_sub = arch_parser.add_subparsers(dest="arch_command", help="Architecture commands")
        arch_discover = arch_sub.add_parser("discover", help="Discover architecture patterns")
        arch_discover.add_argument("repo_path", help="Path to repository")
        arch_fitness = arch_sub.add_parser("fitness", help="Architecture fitness metrics")
        arch_fitness.add_argument("repo_path", help="Path to repository")
        arch_fitness.add_argument("--output", "-o", help="Output file")
        arch_suggest = arch_sub.add_parser("suggest", help="Architecture advisor suggestions")
        arch_suggest.add_argument("--scale", type=int, default=10, help="Expected scale (users/services)")
        arch_suggest.add_argument("--team", type=int, default=5, help="Team size")
        arch_suggest.add_argument("--latency", choices=["low", "medium", "high"], default="medium", help="Latency sensitivity")
        arch_suggest.add_argument("--reliability", type=float, default=0.8, help="Required reliability (0-1)")
        arch_compare_arch = arch_sub.add_parser("compare-arch", help="Compare two architectures")
        arch_compare_arch.add_argument("a", choices=[a.value for a in ArchitectureType], help="First architecture")
        arch_compare_arch.add_argument("b", choices=[a.value for a in ArchitectureType], help="Second architecture")
        arch_failures = arch_sub.add_parser("failures", help="Predict failure modes")
        arch_failures.add_argument("architecture", choices=[a.value for a in ArchitectureType], help="Architecture type")
        arch_failures.add_argument("--scale", type=int, default=10)
        arch_failures.add_argument("--team", type=int, default=5)
        arch_pressure = arch_sub.add_parser("pressure", help="Evolutionary pressure on patterns")
        arch_pressure.add_argument("repo_path", help="Path to repository")
        arch_search_space = arch_sub.add_parser("search-space", help="Explore architecture search space")

        fabric_parser = subparsers.add_parser("fabric", help="Multi-repo memory fabric")
        fabric_sub = fabric_parser.add_subparsers(dest="fabric_command", help="Fabric commands")
        fabric_store = fabric_sub.add_parser("store", help="Store memory in fabric")
        fabric_store.add_argument("--content", required=True, help="Memory content")
        fabric_store.add_argument("--category", choices=[c.value for c in MemoryCategory], default="ecosystem_knowledge", help="Memory category")
        fabric_store.add_argument("--repo", default="unknown", help="Source repository")
        fabric_store.add_argument("--tags", nargs="+", default=[], help="Tags")
        fabric_store.add_argument("--confidence", type=float, default=0.7, help="Confidence (0-1)")
        fabric_query = fabric_sub.add_parser("query", help="Query memory fabric")
        fabric_query.add_argument("query", help="Search query")
        fabric_query.add_argument("--category", choices=[c.value for c in MemoryCategory], help="Filter by category")
        fabric_query.add_argument("--repo", help="Filter by repo")
        fabric_query.add_argument("--max", type=int, default=10, help="Max results")
        fabric_stats = fabric_sub.add_parser("stats", help="Memory fabric statistics")
        fabric_transfer = fabric_sub.add_parser("transfer", help="Cross-repo transfer score")
        fabric_transfer.add_argument("source_repo", help="Source repository")
        fabric_transfer.add_argument("target_repo", help="Target repository")

        compress_parser = subparsers.add_parser("compress", help="Semantic compression")
        compress_sub = compress_parser.add_subparsers(dest="compress_command", help="Compression commands")
        compress_discover = compress_sub.add_parser("discover", help="Discover abstractions from code")
        compress_discover.add_argument("files", nargs="+", help="Code files to analyze")
        compress_discover.add_argument("--output", "-o", help="Output file")
        compress_transfer = compress_sub.add_parser("transfer", help="Transfer abstraction to context")
        compress_transfer.add_argument("--abstraction", required=True, help="Abstraction name")
        compress_transfer.add_argument("--params", help="JSON parameter mapping")
        compress_hierarchy = compress_sub.add_parser("hierarchy", help="Build abstraction hierarchies")
        compress_stats = compress_sub.add_parser("stats", help="Compression statistics")

        similar_parser = subparsers.add_parser("similar", help="Repository similarity engine")
        similar_sub = similar_parser.add_subparsers(dest="similar_command", help="Similarity commands")
        similar_add = similar_sub.add_parser("add", help="Add repository profile")
        similar_add.add_argument("repo_id", help="Repository ID")
        similar_add.add_argument("--name", required=True, help="Repository name")
        similar_add.add_argument("--language", default="python", help="Primary language")
        similar_add.add_argument("--patterns", nargs="+", default=[], help="Architecture patterns")
        similar_add.add_argument("--deps", nargs="+", default=[], help="Dependencies (name=version)")
        similar_find = similar_sub.add_parser("find", help="Find similar repositories")
        similar_find.add_argument("repo_id", help="Repository ID to find similar to")
        similar_find.add_argument("--top", type=int, default=5, help="Number of results")
        similar_cluster = similar_sub.add_parser("cluster", help="Cluster repositories")
        similar_cluster.add_argument("--n", type=int, default=3, help="Number of clusters")
        similar_viz = similar_sub.add_parser("visualize", help="Generate similarity visualization")
        similar_viz.add_argument("--output", "-o", default="similarity-matrix.html", help="Output HTML file")

        observe_v2_parser = subparsers.add_parser("observe-v2", help="Lyme Observatory v2")
        observe_v2_sub = observe_v2_parser.add_subparsers(dest="observe_v2_command", help="Observe v2 commands")
        observe_v2_health = observe_v2_sub.add_parser("health", help="Integrated health dashboard")
        observe_v2_timeline = observe_v2_sub.add_parser("timeline", help="Build observation timeline")
        observe_v2_timeline.add_argument("--dimension", choices=["health", "architecture", "confidence"], default="health")
        observe_v2_pipeline = observe_v2_sub.add_parser("pipeline", help="Data pipeline report")
        observe_v2_storage = observe_v2_sub.add_parser("storage", help="Storage report")
        observe_v2_replay = observe_v2_sub.add_parser("replay", help="Replay observations")
        observe_v2_replay.add_argument("--start", type=int, default=0)
        observe_v2_replay.add_argument("--end", type=int, help="End index")
        observe_v2_record = observe_v2_sub.add_parser("record", help="Record an observation")
        observe_v2_record.add_argument("--output", "-o", help="Output file")

        civ_map_parser = subparsers.add_parser("civ-map", help="Software civilization maps")
        civ_map_sub = civ_map_parser.add_subparsers(dest="civ_map_command", help="Civilization map commands")
        civ_map_gen = civ_map_sub.add_parser("generate", help="Generate civilization map")
        civ_map_gen.add_argument("--output", "-o", help="Output JSON file")
        civ_map_view = civ_map_sub.add_parser("view", help="View civilization map as HTML")
        civ_map_view.add_argument("--output", "-o", default="civilization-map.html", help="Output HTML file")
        civ_map_save = civ_map_sub.add_parser("save", help="Save civilization map")
        civ_map_save.add_argument("output", help="Output path")

        epi_parser = subparsers.add_parser("epistemology", help="Evidence theory and epistemic debugging")
        epi_parser.add_argument("epi_command", choices=["assess", "debug", "calibrate", "report"])
        epi_parser.add_argument("--claim", "-C", help="Claim statement to assess")
        epi_parser.add_argument("--trace", "-t", help="Trace ID to debug")
        epi_parser.add_argument("--domain", "-d", default="code_analysis", help="Knowledge domain")

        policy_parser = subparsers.add_parser("policy", help="Autonomy policy and governance")
        policy_parser.add_argument("policy_command", choices=["check", "sensitive", "review", "audit"])
        policy_parser.add_argument("--action", "-a", help="Action type to check")
        policy_parser.add_argument("--context", "-k", help="JSON context for policy evaluation")
        policy_parser.add_argument("--path", "-p", help="Path to scan for sensitive code")
        policy_parser.add_argument("--request", "-r", help="JSON review request")

        gov_parser = subparsers.add_parser("govern", help="Change governance engine")
        gov_sub = gov_parser.add_subparsers(dest="govern_command", help="Govern commands")
        gov_eval = gov_sub.add_parser("evaluate", help="Evaluate a proposed change")
        gov_eval.add_argument("--context", help="JSON context for change evaluation")
        gov_eval.add_argument("--risk", type=float, default=0.3, help="Risk score (0-1)")
        gov_eval.add_argument("--scope", choices=["local", "module", "broad", "cross_repo"], default="local")
        gov_eval.add_argument("--sensitivity", choices=["none", "security", "critical"], default="none")
        gov_eval.add_argument("--description", default="Change", help="Change description")
        gov_eval.add_argument("--output", "-o", help="Output file")
        gov_list = gov_sub.add_parser("policies", help="List governance policies")
        gov_override = gov_sub.add_parser("override", help="Override a governance decision")
        gov_override.add_argument("--reason", required=True, help="Override reason")

        constit_parser = subparsers.add_parser("constitution", help="Repo constitution management")
        constit_sub = constit_parser.add_subparsers(dest="constitution_command", help="Constitution commands")
        constit_init = constit_sub.add_parser("init", help="Initialize a repo constitution")
        constit_init.add_argument("--repo", default=".", help="Repository path")
        constit_init.add_argument("--name", default="", help="Repository name")
        constit_init.add_argument("--output", "-o", help="Output file path")
        constit_view = constit_sub.add_parser("view", help="View constitution")
        constit_view.add_argument("--path", default=".lyme/constitution.json", help="Constitution file")
        constit_validate = constit_sub.add_parser("validate", help="Validate constitution")
        constit_validate.add_argument("--path", default=".lyme/constitution.json", help="Constitution file")
        constit_check = constit_sub.add_parser("check", help="Check if action is allowed by constitution")
        constit_check.add_argument("--file", required=True, help="File path to check")
        constit_check.add_argument("--action", choices=["read", "suggest", "create_patch", "run_tests", "modify_files", "deploy"], default="modify_files")
        constit_check.add_argument("--constitution", default=".lyme/constitution.json", help="Constitution file")

        ledger_parser = subparsers.add_parser("ledger", help="Autonomous change ledger")
        ledger_sub = ledger_parser.add_subparsers(dest="ledger_command", help="Ledger commands")
        ledger_record = ledger_sub.add_parser("record", help="Record a ledger entry")
        ledger_record.add_argument("--description", required=True, help="Entry description")
        ledger_record.add_argument("--type", choices=["code_change", "verification", "governance", "approval", "rollback", "memory"], default="code_change")
        ledger_record.add_argument("--agent", default="lyme", help="Agent name")
        ledger_record.add_argument("--intent", default="modify", help="Intent")
        ledger_record.add_argument("--risk", type=float, default=0.0, help="Risk score")
        ledger_record.add_argument("--outcome", choices=["success", "failure", "blocked", "rolled_back", "partial", "pending"], default="success")
        ledger_view = ledger_sub.add_parser("view", help="View ledger entries")
        ledger_view.add_argument("--type", help="Filter by entry type")
        ledger_view.add_argument("--limit", type=int, default=20, help="Number of entries")
        ledger_summary = ledger_sub.add_parser("summary", help="Ledger summary statistics")
        ledger_path = ledger_sub.add_parser("path", help="Show rollback path for an entry")
        ledger_path.add_argument("entry_id", help="Entry ID")

        eval_parser = subparsers.add_parser("eval", help="Evaluation and regression detection")
        eval_sub = eval_parser.add_subparsers(dest="eval_command", help="Evaluation commands")
        eval_bench = eval_sub.add_parser("benchmark", help="Run self-benchmark")
        eval_bench.add_argument("--type", choices=["demo", "real"], default="demo", help="Repository type")
        eval_bench.add_argument("--name", default="", help="Repository name")
        eval_bench.add_argument("--output", "-o", help="Output JSON file")
        eval_long = eval_sub.add_parser("longitudinal", help="Run longitudinal evaluation")
        eval_long.add_argument("--output", "-o", help="Output JSON file")
        eval_cog = eval_sub.add_parser("cognition", help="Run cognition regression detection")
        eval_cog.add_argument("--baseline", type=float, default=0.8, help="Baseline score for all dimensions")
        eval_cog.add_argument("--output", "-o", help="Output JSON file")

        verify_parser = subparsers.add_parser("verify", help="Verification graph, planner, and gap detection")
        verify_sub = verify_parser.add_subparsers(dest="verify_command", help="Verification commands")
        vg = verify_sub.add_parser("graph", help="Build and render verification graph")
        vg.add_argument("--action-id", default="default", help="Action identifier")
        vg.add_argument("--description", default="Lyme action", help="Action description")
        vg.add_argument("--context", help="JSON context for verification")
        vg.add_argument("--report", action="store_true", help="Show full verification report")
        vg.add_argument("--output", "-o", help="Output JSON file")
        vp = verify_sub.add_parser("plan", help="Plan verification strategy for an edit")
        vp.add_argument("--edit", default="Unnamed edit", help="Edit description")
        vp.add_argument("--risk", type=float, default=0.3, help="Edit risk score (0-1)")
        vp.add_argument("--scope", choices=["local", "module", "broad", "cross_repo"], default="local", help="Edit scope")
        vp.add_argument("--sensitive", action="store_true", help="Edit touches sensitive code")
        vp.add_argument("--lang", default="python", help="Project language")
        vp.add_argument("--output", "-o", help="Output JSON file")
        vd = verify_sub.add_parser("gaps", help="Detect verification gaps")
        vd.add_argument("--context", help="JSON context for gap detection")
        vd.add_argument("--output", "-o", help="Output JSON file")
        vd.add_argument("--format", choices=["markdown", "cli", "json"], default="cli", help="Output format")

        demo_parser = subparsers.add_parser("demo-v03", help="Run v0.3 demo")
        demo_parser.add_argument("--full", action="store_true", help="Run full demo")

        demo_v06_parser = subparsers.add_parser("demo-v06", help="Run v0.6 scientific governance demo")
        demo_v06_parser.add_argument("--full", action="store_true", help="Run full demo")

        # v0.5 commands
        demo_v05_parser = subparsers.add_parser("demo-v05", help="Run v0.5 autonomous evolution demo")
        demo_v05_parser.add_argument("--repo", "-r", default=".", help="Repository path")
        demo_v05_parser.add_argument("--full", action="store_true", help="Run full demo")

        detect_parser = subparsers.add_parser("detect", help="Detect maintenance opportunities")
        detect_parser.add_argument("--repo", "-r", default=".", help="Repository path")
        detect_parser.add_argument("--output", "-o", help="Output JSON file")
        detect_parser.add_argument("--top", type=int, default=10, help="Show top N opportunities")

        maintain_parser = subparsers.add_parser("maintain", help="Run autonomous maintenance loop")
        maintain_parser.add_argument("--repo", "-r", default=".", help="Repository path")
        maintain_parser.add_argument("--tasks", type=int, default=1, help="Number of tasks per loop")
        maintain_parser.add_argument("--stats", action="store_true", help="Show maintenance statistics")

        roadmap_parser = subparsers.add_parser("roadmap", help="Generate technical roadmap")
        roadmap_parser.add_argument("--repo", "-r", default=".", help="Repository path")
        roadmap_parser.add_argument("--output", "-o", help="Output JSON file")

        decisions_parser = subparsers.add_parser("decisions", help="Engineering decision memory")
        decisions_sub = decisions_parser.add_subparsers(dest="decisions_command", help="Decision commands")
        decisions_record = decisions_sub.add_parser("record", help="Record an architectural decision")
        decisions_record.add_argument("--title", required=True, help="Decision title")
        decisions_record.add_argument("--context", required=True, help="Decision context")
        decisions_record.add_argument("--decision", required=True, help="The decision made")
        decisions_record.add_argument("--rationale", required=True, help="Why this decision")
        decisions_record.add_argument("--constraints", nargs="+", default=[], help="Constraints")
        decisions_record.add_argument("--alternatives", nargs="+", default=[], help="Alternatives considered")
        decisions_report = decisions_sub.add_parser("report", help="Produce decision memory report")

        tradeoff_parser = subparsers.add_parser("tradeoff", help="Strategic tradeoff simulation")
        tradeoff_parser.add_argument("--repo", "-r", default=".", help="Repository path")
        tradeoff_parser.add_argument("--domain", choices=["refactor_timing", "framework_strategy", "module_strategy", "test_strategy", "model_strategy", "automation_strategy", "all"], default="all", help="Tradeoff domain to analyze")
        tradeoff_parser.add_argument("--output", "-o", help="Output JSON file")

        # v0.7 commands
        trace_std_parser = subparsers.add_parser("trace-std", help="Open Agent Trace Standard operations")
        trace_std_sub = trace_std_parser.add_subparsers(dest="trace_std_command")
        trace_std_export = trace_std_sub.add_parser("export", help="Export trace in OATS format")
        trace_std_export.add_argument("--input", help="Input trace file (Lyme format)")
        trace_std_export.add_argument("--output", "-o", default="trace-export.json", help="Output file")
        trace_std_validate = trace_std_sub.add_parser("validate", help="Validate OATS trace")
        trace_std_validate.add_argument("file", help="Trace file to validate")
        trace_std_compare = trace_std_sub.add_parser("compare", help="Compare two OATS traces")
        trace_std_compare.add_argument("trace_a", help="First trace file")
        trace_std_compare.add_argument("trace_b", help="Second trace file")
        trace_std_examples = trace_std_sub.add_parser("examples", help="Generate example traces")
        trace_std_examples.add_argument("--output", "-o", default="lyme-output/standards/traces", help="Output directory")

        sd_parser = subparsers.add_parser("semantic-diff", help="Semantic Diff Standard operations")
        sd_sub = sd_parser.add_subparsers(dest="semantic_diff_command")
        sd_render = sd_sub.add_parser("render", help="Render semantic diff")
        sd_render.add_argument("--input", "-i", help="Input semantic diff JSON")
        sd_render.add_argument("--format", choices=["markdown", "json", "html", "console"], default="markdown")
        sd_render.add_argument("--output", "-o", help="Output file")
        sd_examples = sd_sub.add_parser("examples", help="Generate example semantic diffs")
        sd_examples.add_argument("--output", "-o", default="lyme-output/standards/semantic-diffs", help="Output dir")

        pr_parser = subparsers.add_parser("pr", help="GitHub PR Intelligence")
        pr_sub = pr_parser.add_subparsers(dest="pr_command")
        pr_analyze = pr_sub.add_parser("analyze", help="Analyze a pull request")
        pr_analyze.add_argument("repo", help="Repository (owner/name)")
        pr_analyze.add_argument("pr_number", type=int, help="PR number")
        pr_analyze.add_argument("--output", "-o", help="Output file")

        ci_parser = subparsers.add_parser("ci", help="CI/CD Integration")
        ci_parser.add_argument("--mode", choices=["advisory", "blocking", "research"], default="advisory")
        ci_parser.add_argument("--repo", default="local", help="Repository name")
        ci_parser.add_argument("--commit", default="HEAD", help="Commit hash")
        ci_parser.add_argument("--branch", default="main", help="Branch name")
        ci_parser.add_argument("--output", "-o", default="lyme-output/ci", help="Output directory")

        bridge_parser = subparsers.add_parser("bridge", help="IDE Bridge")
        bridge_sub = bridge_parser.add_subparsers(dest="bridge_command")
        bridge_query = bridge_sub.add_parser("query", help="Query the IDE bridge")
        bridge_query.add_argument("type", choices=["evidence", "diff-preview", "arch-warning", "verify-gap", "confidence", "edit-suggestion"])
        bridge_query.add_argument("query", nargs="?", default="", help="Query text")
        bridge_query.add_argument("--file", "-f", help="File path")

        corpus_parser = subparsers.add_parser("corpus", help="Research Corpus operations")
        corpus_sub = corpus_parser.add_subparsers(dest="corpus_command")
        corpus_add = corpus_sub.add_parser("add", help="Add entry to corpus")
        corpus_add.add_argument("--trace", help="Trace file to add")
        corpus_add.add_argument("--type", default="agent_trace", help="Entry type")
        corpus_add.add_argument("--title", default="", help="Entry title")
        corpus_add.add_argument("--output", "-o", default="lyme-output/research-corpus", help="Output directory")
        corpus_export = corpus_sub.add_parser("export", help="Export corpus")
        corpus_export.add_argument("--format", choices=["json", "jsonl", "citations"], default="json")
        corpus_export.add_argument("--output", "-o", help="Output file")

        portal_parser = subparsers.add_parser("portal", help="Research Portal")
        portal_parser.add_argument("--output", "-o", default="lyme-output/research-portal", help="Output directory")

        contrib_parser = subparsers.add_parser("contrib", help="Contribution Protocol")
        contrib_sub = contrib_parser.add_subparsers(dest="contrib_command")
        contrib_new = contrib_sub.add_parser("new", help="Create new contribution")
        contrib_new.add_argument("--type", choices=["benchmark_task", "model_adapter", "tool_router", "memory_system", "compression_strategy", "governance_policy", "visualization_module"], default="benchmark_task")
        contrib_new.add_argument("--title", required=True, help="Contribution title")
        contrib_submit = contrib_sub.add_parser("submit", help="Submit contribution for review")
        contrib_guide = contrib_sub.add_parser("guide", help="Get contribution guide")
        contrib_guide.add_argument("type", help="Contribution type")

        # Extend evolution sub-parser with v0.5 commands
        evolution_mutate = evolution_sub.add_parser("mutate", help="Generate and analyze software mutations")
        evolution_mutate.add_argument("--repo", "-r", default=".", help="Repository path")
        evolution_mutate.add_argument("--apply", action="store_true", help="Apply the best mutation")
        evolution_mutate.add_argument("--benchmark", action="store_true", help="Benchmark mutation impact")
        evolution_mutate.add_argument("--output", "-o", help="Output JSON file")

        evolution_fitness = evolution_sub.add_parser("fitness", help="Assess architecture fitness")
        evolution_fitness.add_argument("--repo", "-r", default=".", help="Repository path")
        evolution_fitness.add_argument("--output", "-o", help="Output JSON file")

        evolution_sandbox = evolution_sub.add_parser("sandbox", help="Run evolution in isolated sandbox")
        evolution_sandbox.add_argument("--repo", "-r", default=".", help="Repository path")
        evolution_sandbox.add_argument("--name", default="sandbox-experiment", help="Experiment name")
        evolution_sandbox.add_argument("--apply", action="store_true", help="Apply and run experiment")
        evolution_sandbox.add_argument("--list", action="store_true", help="List experiments")

        config_path = None
        for i, arg in enumerate(argv):
            if arg in ("-c", "--config") and i + 1 < len(argv):
                config_path = argv[i + 1]
                break
        self.settings = load_config(config_path)
        args = parser.parse_args(argv)

        if not args.command:
            parser.print_help()
            return

        command_map = {
            "observe": self._do_observe,
            "improve": self._do_improve,
            "self": self._do_self,
            "archfile": self._do_archfile,
            "plan": self._do_plan,
            "skill": self._do_skill,
            "run": self._do_run,
            "list-scenarios": self._do_list_scenarios,
            "replay": self._do_replay,
            "compare": self._do_compare,
            "doctor": self._do_doctor,
            "ask": self._do_ask,
            "history": self._do_history,
            "undo": self._do_undo,
            "audit": self._do_audit,
            "stress": self._do_stress,
            "ui": self._do_ui,
            "info": self._do_info,
            "report": self._do_report,
            "graph": self._do_graph,
            "discover": self._do_discover,
            "intent": self._do_intent,
            "evolution": self._do_evolution,
            "predict": self._do_predict,
            "learn": self._do_learn,
            "society": self._do_society,
            "research": self._do_research,
            "cross-repo": self._do_cross_repo,
            "ecosystem": self._do_ecosystem,
            "fw-obs": self._do_fw_obs,
            "arch": self._do_arch,
            "fabric": self._do_fabric,
            "compress": self._do_compress,
            "similar": self._do_similar,
            "observe-v2": self._do_observe_v2,
            "civ-map": self._do_civ_map,
            "epistemology": self._do_epistemology,
            "policy": self._do_policy,
            "govern": self._do_govern,
            "constitution": self._do_constitution,
            "ledger": self._do_ledger,
            "eval": self._do_eval,
            "verify": self._do_verify,
            "demo-v03": self._do_demo_v03,
            "demo-v05": self._do_demo_v05,
            "demo-v06": self._do_demo_v06,
            "detect": self._do_detect,
            "maintain": self._do_maintain,
            "roadmap": self._do_roadmap,
            "decisions": self._do_decisions,
            "tradeoff": self._do_tradeoff,
            "trace-std": self._do_trace_std,
            "semantic-diff": self._do_semantic_diff,
            "pr": self._do_pr,
            "ci": self._do_ci,
            "bridge": self._do_bridge,
            "corpus": self._do_corpus,
            "portal": self._do_portal,
            "contrib": self._do_contrib,
        }

        handler = command_map.get(args.command)
        if handler:
            handler(args)
        else:
            parser.print_help()

    def _do_run(self, args):
        engine = BenchmarkEngine(self.settings)

        agents = self.settings.agents
        if args.agent:
            agents = [a for a in agents if a.name in args.agent]
            if not agents:
                print(f"No agents found matching: {args.agent}")
                return

        if args.all:
            runs = engine.run_all(agents, parallel=args.parallel)
        elif args.scenario:
            runs = engine.run_scenarios(args.scenario, agents, parallel=args.parallel)
        else:
            print("Specify --scenario, --all, or use: lyme run --all")
            return

        self._print_run_summary(runs)

    def _do_list_scenarios(self, args):
        scenarios = ScenarioRegistry.list_scenarios()
        if not scenarios:
            print("No scenarios registered.")
            return

        print(f"{'Name':40s} {'Category':25s} {'Difficulty':10s}")
        print("-" * 75)
        for s in scenarios:
            print(f"{s['name']:40s} {s['category']:25s} {s['difficulty']:<10.1f}")

    def _do_replay(self, args):
        replayer = DeterministicReplayer()
        store = EventStore(self.settings.benchmark.output_dir)

        trace = store.load_trace(args.trace_id)
        if not trace:
            print(f"Trace '{args.trace_id}' not found in {store.base_dir / 'traces'}")
            return

        session = replayer.load_from_trace(trace)
        summary = replayer.session_summary(session)

        print(f"Replaying: {session.agent_name} / {session.scenario_name}")
        print(f"Events: {summary['event_count']}, Spans: {summary['span_count']}")
        print(f"Duration: {summary['real_duration_s']:.1f}s")
        print(f"Speed: {args.speed}x")
        print()

        def on_event(event, index, total):
            ts = event.get("timestamp", 0)
            etype = event.get("type", "?")
            desc = event.get("payload", {}).get("description", "")
            bar = "█" * int((index + 1) / total * 30) + "░" * (30 - int((index + 1) / total * 30))
            sys.stdout.write(f"\r[{bar}] {index+1}/{total} {etype}: {desc[:50]}  ")
            sys.stdout.flush()

        replayer.play(session, speed=args.speed, on_event=on_event)
        print("\nReplay complete.")

    def _do_compare(self, args):
        engine = BenchmarkEngine(self.settings)
        agents = self.settings.agents

        if args.agents:
            agents = [a for a in agents if a.name in args.agents]

        comparison = engine.compare_agents(args.scenario, agents)

        print(f"\nComparison: {comparison['scenario']}")
        print("=" * 60)
        for agent_name, result in comparison.get("agents", {}).items():
            status = "✓" if result.get("success") else "✗"
            print(f"\n{status} {agent_name}")
            print(f"  Duration: {result.get('duration_ms', 0):.1f}ms")
            for k, v in result.get("metrics", {}).items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.3f}")
                else:
                    print(f"  {k}: {v}")
            for err in result.get("errors", []):
                print(f"  ! {err}")

    def _do_ask(self, args):
        from .ask import EvidenceEngine
        question = " ".join(args.question)
        repo_path = Path(args.repo).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        engine = EvidenceEngine()
        answer = engine.ask(question, repo_path)

        output = answer.to_markdown()
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Answer written to {args.output}")
        else:
            print(output)

    def _do_doctor(self, args):
        from .doctor import RepoDoctor
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        doctor = RepoDoctor()
        diagnosis = doctor.diagnose(repo_path)

        if args.format == "json":
            output = json.dumps(diagnosis.to_dict(), indent=2, default=str)
        else:
            output = diagnosis.to_markdown()

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Diagnosis written to {args.output}")
        else:
            print(output)

    def _do_history(self, args):
        repo_path = Path.cwd()
        from .audit import AuditSystem
        audit = AuditSystem(repo_path)
        trail = audit.get_history(limit=args.limit, kind_filter=args.kind)
        print(trail.to_markdown(limit=args.limit))

    def _do_undo(self, args):
        repo_path = Path.cwd()
        from .audit import AuditSystem
        audit = AuditSystem(repo_path)
        if audit.undo(args.audit_id):
            print(f"Undo of '{args.audit_id}' completed.")
        else:
            print(f"Cannot undo '{args.audit_id}'. "
                  f"Check that it exists and is reversible with: lyme audit {args.audit_id}")

    def _do_audit(self, args):
        repo_path = Path.cwd()
        from .audit import AuditSystem
        audit = AuditSystem(repo_path)
        report = audit.get_report(args.audit_id)
        if not report:
            print(f"Audit ID '{args.audit_id}' not found")
            return
        output = report.to_markdown()
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Audit report written to {args.output}")
        else:
            print(output)

    def _do_stress(self, args):
        agent = None
        if args.agent:
            agent = next(
                (a for a in self.settings.agents if a.name == args.agent),
                None
            )
            if not agent:
                print(f"Agent '{args.agent}' not found")
                return
        else:
            agent = self.settings.agents[0]

        experiment = StressExperiment(
            name=args.experiment,
            agent_cfg=agent,
            work_base_dir=self.settings.benchmark.experiments_dir,
        )

        if args.generate:
            gen = SyntheticRepoGenerator()
            work_dir = Path(self.settings.benchmark.experiments_dir) / "synthetic"
            spec = gen.generate(work_dir, num_files=50, depth=3)
            print(f"Generated {spec['file_count']} files in {work_dir}")
            print(f"Complexity: {spec['complexity']:.2f}")
            return

        if args.experiment == "repo-size":
            result = experiment.run_repo_size_experiment(
                sizes=[5, 10, 20, 50]
            )
        elif args.experiment == "hidden-coupling":
            result = experiment.run_hidden_coupling_experiment(
                coupling_levels=[0, 1, 3, 5]
            )
        else:
            print(f"Unknown experiment: {args.experiment}")
            return

        print()
        print(experiment.generate_report(result))

        if result.bottlenecks:
            print("\nBottlenecks:")
            for b in result.bottlenecks:
                print(f"  - {b['metric']}: collapsed at level {b['collapse_level']} ({b['type']})")

    def _do_ui(self, args):
        store = EventStore(self.settings.benchmark.output_dir)

        if args.type == "dashboard":
            runs = []
            for rid in store.list_runs():
                data = store.load_run(rid)
                if data:
                    trace = store.load_trace(rid)
                    if trace:
                        data["metrics"] = trace.get("scenario_result", {}).get("metrics", {})
                    runs.append(data)

            output = args.output or "lyme-dashboard.html"
            render_dashboard(runs, output_path=output)
            print(f"Dashboard written to {output}")

        elif args.type in ("timeline", "thought", "branch"):
            if not args.run_id:
                print("Run ID required")
                return

            trace = store.load_trace(args.run_id)
            if not trace:
                print(f"Trace '{args.run_id}' not found")
                return

            output = args.output or f"lyme-{args.type}-{args.run_id}.html"

            if args.type == "timeline":
                from ..telemetry import Timeline
                timeline = Timeline()
                for event in trace.get("events", []):
                    from ..telemetry.timeline import TimelineEvent
                    te = TimelineEvent(
                        timestamp=event.get("timestamp", 0),
                        type=event.get("type", "event"),
                        label=event.get("type", "").replace("_", " ").title(),
                        detail=event.get("payload", {}).get("description", ""),
                        status=event.get("severity", "info"),
                        event_id=event.get("id", ""),
                    )
                    timeline.add(te)
                render_timeline(timeline, title=f"{trace.get('agent', '')} / {trace.get('scenario', '')}",
                                output_path=output)
            elif args.type == "thought":
                cog_trace = store.load_cognitive_trace(args.run_id) or {}
                render_cognitive_trace(cog_trace, output_path=output)
            elif args.type == "branch":
                from ..ui.thought_viewer import render_branch_view
                cog_trace = store.load_cognitive_trace(args.run_id) or {}
                render_branch_view(cog_trace, output_path=output)

            print(f"{args.type.title()} view written to {output}")

    def _do_info(self, args):
        store = EventStore(self.settings.benchmark.output_dir)

        if args.run_id:
            run_ids = [args.run_id]
        else:
            run_ids = store.list_runs()[-5:]

        for rid in run_ids:
            data = store.load_run(rid)
            if data:
                print(f"\nRun: {rid}")
                print(f"  Agent: {data.get('agent_name', '?')}")
                print(f"  Scenario: {data.get('scenario_name', '?')}")
                print(f"  Success: {data.get('success', '?')}")
                print(f"  Duration: {data.get('total_duration_ms', 0):.1f}ms")
                print(f"  Spans: {data.get('spans_count', 0)}")
                print(f"  Events: {data.get('events_count', 0)}")
                print(f"  Tool Calls: {data.get('tool_calls_count', 0)}")
                print(f"  Errors: {data.get('errors_count', 0)}")
                print(f"  Hallucinations: {data.get('hallucinations_detected', 0)}")

                cog = store.load_cognitive_trace(rid)
                if cog:
                    summary = cog.get("summary", {})
                    print(f"  Cognition:")
                    print(f"    Steps: {summary.get('total_steps', 0)}")
                    print(f"    Decisions: {summary.get('total_decisions', 0)}")
                    print(f"    Branches: {summary.get('branches_explored', 0)}")
                    print(f"    Avg Confidence: {summary.get('avg_confidence', 0):.2f}")

    def _do_report(self, args):
        store = EventStore(self.settings.benchmark.output_dir)

        if args.all:
            run_ids = store.list_runs()
        elif args.run_id:
            run_ids = args.run_id
        else:
            print("Specify run IDs or --all")
            return

        for rid in run_ids:
            data = store.load_run(rid)
            if not data:
                print(f"Run {rid} not found")
                continue

            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:
                from .store import BenchmarkReport
                report = BenchmarkReport(**data)
                from .store import StructuredOutput
                print(StructuredOutput.report_to_markdown(report))
            print()

    def _do_graph(self, args):
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        engine = CausalInferenceEngine()
        graph = engine.infer(repo_path)
        renderer = CausalGraphRenderer(graph)

        if args.graph_command == "infer":
            result = graph.to_dict()
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"Causal graph written to {args.output}")
            else:
                print(json.dumps(result, indent=2, default=str))

        elif args.graph_command == "risk":
            target_file = args.file
            node = graph.find_node_by_name(target_file)
            if not node:
                print(f"File '{target_file}' not found in graph")
                return
            estimator = DownstreamAnalyzer(graph)
            breakage = estimator.find_downstream_breakage(node.id)
            propagator = FailurePropagator(graph)
            cascade = propagator.cascade_analysis(node.id)
            result = {
                "target_file": target_file,
                "node": node.to_dict(),
                "breakage_estimate": breakage[:20],
                "cascade_analysis": cascade,
            }
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"Risk analysis written to {args.output}")
            else:
                print(json.dumps(result, indent=2, default=str))

        elif args.graph_command == "visualize":
            if args.format == "html":
                output = renderer.to_html(title=f"Causal Graph: {repo_path.name}")
            elif args.format == "graphviz":
                output = renderer.to_graphviz()
            elif args.format == "mermaid":
                output = renderer.to_mermaid()
            elif args.format == "d3":
                output = json.dumps(renderer.to_d3_json(), indent=2)
            else:
                output = renderer.to_html()

            out_path = args.output or f"lyme-causal-graph-{repo_path.name}.{args.format}"
            if args.format == "html":
                out_path = args.output or f"lyme-causal-graph-{repo_path.name}.html"
            elif args.format == "graphviz":
                out_path = args.output or f"lyme-causal-graph-{repo_path.name}.gv"
            elif args.format == "mermaid":
                out_path = args.output or f"lyme-causal-graph-{repo_path.name}.mmd"
            elif args.format == "d3":
                out_path = args.output or f"lyme-causal-graph-{repo_path.name}.json"

            with open(out_path, "w") as f:
                f.write(output)
            print(f"Visualization written to {out_path}")

        elif args.graph_command == "amplify":
            zones = graph.find_amplification_zones()
            pressure = graph.find_architectural_pressure_points()
            result = {
                "amplification_zones": zones[:20],
                "architectural_pressure_points": pressure[:20],
            }
            print(json.dumps(result, indent=2, default=str))

        elif args.graph_command == "hidden":
            hiddens = graph.find_hidden_dependencies()
            syncs = graph.find_synchronization_surfaces()
            result = {
                "hidden_dependencies": hiddens[:30],
                "synchronization_surfaces": syncs[:20],
            }
            print(json.dumps(result, indent=2, default=str))

    def _do_discover(self, args):
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        engine = InvariantInferenceEngine()

        if args.discover_command == "invariants":
            inv_set = engine.discover_with_confidence(repo_path, min_confidence=args.min_confidence)
            result = inv_set.to_dict()
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"Invariants written to {args.output}")
            else:
                print(f"\n=== Architectural Invariants ===")
                print(f"Total: {result['summary']['total_invariants']}")
                print(f"By source: {result['summary']['invariants_by_source']}")
                print(f"By severity: {result['summary']['invariants_by_severity']}")
                print()
                for inv in result["invariants"]:
                    print(f"  [{inv['severity']}] {inv['name']}")
                    print(f"        {inv['description'][:100]}")
                    print(f"        confidence={inv['confidence']:.2f} source={inv['source']}")
                    print()

        elif args.discover_command == "violations":
            inv_set = engine.discover(repo_path)
            detector = ViolationDetector()
            violations = detector.detect(repo_path, inv_set)
            for v in violations:
                inv_set.add_violation(v)
            result = {
                "total_violations": len(violations),
                "violations": [v.to_dict() for v in violations],
            }
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"Violations written to {args.output}")
            else:
                print(f"\n=== Violations Detected: {len(violations)} ===")
                for v in violations:
                    print(f"  [{v.severity}] {v.description[:100]}")
                    print(f"        in {v.file_path}:{v.line_number}")

        elif args.discover_command == "contradictions":
            inv_set = engine.discover(repo_path)
            detector = ContradictionDetector()
            contradictions = detector.detect(inv_set)
            for c in contradictions:
                inv_set.add_contradiction(c)
            result = {
                "total_contradictions": len(contradictions),
                "contradictions": [c.to_dict() for c in contradictions],
            }
            print(f"\n=== Contradictions: {len(contradictions)} ===")
            for c in contradictions:
                print(f"  [{c.severity}] {c.description[:100]}")
                print(f"        resolution: {c.resolution}")

        elif args.discover_command == "repair":
            inv_set = engine.discover(repo_path)
            detector = ViolationDetector()
            violations = detector.detect(repo_path, inv_set)
            for v in violations:
                inv_set.add_violation(v)
            suggester = RepairSuggester()
            plan = suggester.generate_repair_plan(inv_set)
            print(f"\n=== Repair Plan ===")
            print(f"Total violations: {plan['total_violations']}")
            print(f"Critical: {plan['critical_count']}, High: {plan['high_count']}")
            for p in plan["repair_plans"][:10]:
                print(f"\n  [{p['severity']}] {p['violation_description'][:80]}")
                for s in p["suggestions"]:
                    print(f"    -> {s['action']} (effort: {s['effort']})")

        elif args.discover_command == "fragility":
            inv_set = engine.discover(repo_path)
            detector = ViolationDetector()
            violations = detector.detect(repo_path, inv_set)
            for v in violations:
                inv_set.add_violation(v)
            contradiction_detector = ContradictionDetector()
            contradictions = contradiction_detector.detect(inv_set)
            for c in contradictions:
                inv_set.add_contradiction(c)
            tracker = EvolutionTracker()
            fragility = tracker.estimate_fragility(inv_set)
            print(f"\n=== Architectural Fragility ===")
            print(f"Fragility Score: {fragility['fragility_score']:.2f}")
            print(f"High Severity Ratio: {fragility['high_severity_ratio']:.2f}")
            print(f"Contradiction Ratio: {fragility['contradiction_ratio']:.2f}")
            print(f"Violation Ratio: {fragility['violation_ratio']:.2f}")

    def _do_intent(self, args):
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        if args.intent_command == "infer":
            engine = IntentInferenceEngine()
            model = engine.infer(repo_path)
            result = model.to_dict()
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"Intent model written to {args.output}")
            else:
                print(f"\n=== Software Intent Model ===")
                print(f"Repo: {model.repo_path}")
                print(f"Philosophy: {model.overall_philosophy.value}")
                print(f"Subsystems: {len(model.intents)}")
                print()
                for si in model.intents:
                    print(f"  [{si.subsystem}]")
                    print(f"    Purpose: {si.purpose[:80] if si.purpose else '(unknown)'}")
                    print(f"    Confidence: {si.confidence:.2f}")
                    print(f"    Uncertainty: {si.uncertainty.overall:.2f}")
                    if si.tradeoffs:
                        print(f"    Tradeoffs ({len(si.tradeoffs)}):")
                        for t in si.tradeoffs[:3]:
                            print(f"      - {t.description[:80]}")
                    if si.constraints:
                        print(f"    Constraints ({len(si.constraints)}):")
                        for c in si.constraints[:3]:
                            print(f"      - {c[:80]}")
                    if si.evolution:
                        print(f"    Evolution:")
                        for e in si.evolution[:3]:
                            print(f"      - {e[:80]}")
                    print()
                if model.metadata.get("refactor_predictions"):
                    print("  Predictions:")
                    for p in model.metadata["refactor_predictions"][:5]:
                        print(f"    - [{p['timeframe']}] {p['prediction'][:100]} (conf={p['confidence']:.2f})")

        elif args.intent_command == "uncertainty":
            engine = IntentInferenceEngine()
            model = engine.infer(repo_path)
            estimator = UncertaintyEstimator()
            uncertainty = estimator.estimate(model)
            print(f"\n=== Intent Uncertainty ===")
            print(f"Overall: {uncertainty.overall:.2f}")
            print(f"Evidence Gap: {uncertainty.evidence_gap:.2f}")
            print(f"Contradiction Level: {uncertainty.contradiction_level:.2f}")
            print(f"Staleness: {uncertainty.staleness:.2f}")
            if uncertainty.missing_domains:
                print(f"Missing Domains: {', '.join(uncertainty.missing_domains)}")

    def _do_evolution(self, args):
        if hasattr(args, 'evolution_command') and args.evolution_command in ('mutate', 'fitness', 'sandbox'):
            repo_path = Path(getattr(args, 'repo', '.')).resolve()
        else:
            repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        if hasattr(args, 'evolution_command') and args.evolution_command in ('mutate', 'fitness', 'sandbox'):
            engine = EvolutionAnalyzer()
            model = None
        else:
            engine = EvolutionAnalyzer()
            model = engine.analyze(repo_path)

        if args.evolution_command == "analyze":
            print(f"\n=== Repository Evolution: {repo_path.name} ===")
            print(f"Total events: {len(model.events)}")
            print(f"Timeline snapshots: {len(model.timeline.snapshots)}")
            print(f"Trend metrics: {list(model.timeline.trends.keys())}")
            if model.timeline.snapshots:
                latest = model.timeline.snapshots[-1].metrics
                print(f"\nCurrent State:")
                print(f"  Files: {latest.total_files}")
                print(f"  Lines: {latest.total_lines}")
                print(f"  Dependencies: {latest.dependency_count}")
                print(f"  Subsystems: {latest.subsystem_count}")

        elif args.evolution_command == "trend":
            detector = TrendDetector()
            trends = detector.detect(model)
            print(f"\n=== Evolution Trends ===")
            if trends:
                for t in trends:
                    print(f"  [{t['severity']}] {t['signal'][:100]}")
            else:
                print("  No significant trends detected.")

        elif args.evolution_command == "complexity":
            tracker = ComplexityTracker()
            result = tracker.track(repo_path)
            print(f"\n=== Complexity Analysis ===")
            print(f"Total files: {result['total_files_analyzed']}")
            print(f"Total complexity: {result['total_complexity']:.1f}")
            print(f"Average complexity: {result['avg_complexity']:.1f}")
            print("\nMost complex files:")
            for fc in result['most_complex_files'][:10]:
                print(f"  {fc['complexity_score']:6.1f} {fc['file']}")

        elif args.evolution_command == "refactor-waves":
            detector = RefactorWaveDetector()
            waves = detector.detect(model.events)
            print(f"\n=== Refactor Waves ({len(waves)}) ===")
            for w in waves[:5]:
                print(f"  Refactors: {w['refactor_count']}, intensity: {w['intensity']:.1f}/day")
                print(f"  Authors: {', '.join(w['authors'][:3])}")

        elif args.evolution_command == "anomalies":
            detector = EvolutionAnomalyDetector()
            anomalies = detector.detect(model)
            print(f"\n=== Evolution Anomalies ({len(anomalies)}) ===")
            for a in anomalies:
                print(f"  [{a['severity']}] {a['description']}")

        elif args.evolution_command == "forecast":
            forecaster = EvolutionForecaster()
            forecast = forecaster.forecast(model)
            print(f"\n=== Evolution Forecast ===")
            print(f"Confidence: {forecast['confidence']:.2f}")
            for metric, values in forecast['forecasts'].items():
                print(f"  {metric}: {[f'{v:.1f}' for v in values]}")

        elif args.evolution_command == "metrics":
            metrics_engine = SoftwareEvolutionMetricsEngine()
            observations = metrics_engine.measure(repo_path)
            output = metrics_engine.generate_report() if args.report else {"observations": {k: v.to_dict() for k, v in observations.items()}}
            output_str = json.dumps(output, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Metrics written to {args.output}")
            else:
                print(f"\n=== Software Evolution Metrics ===")
                print(f"Metrics calculated: {len(observations)}")
                for name, obs in observations.items():
                    defn = metrics_engine.get_definitions().get(name)
                    cat = defn.category.value if defn else "?"
                    arrow = "↑" if obs.normalized_value > 0.6 else "↓" if obs.normalized_value < 0.4 else "→"
                    print(f"  {arrow} [{cat}] {name}: {obs.value:.4f} (norm: {obs.normalized_value:.3f})")
                if args.report:
                    report = metrics_engine.generate_report()
                    print(f"\n--- Full Report ---")
                    print(f"Metric count: {len(report['metrics'])}")

        elif args.evolution_command == "motifs":
            engine = MotifDiscoveryEngine()
            motifs = engine.analyze(model)
            output = {"motifs": [m.to_dict() for m in motifs]}
            output_str = json.dumps(output, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Motifs written to {args.output}")
            else:
                print(f"\n=== Evolutionary Motifs ({len(motifs)}) ===")
                for m in motifs:
                    health_tag = {"healthy": "✓", "neutral": "~", "unhealthy": "!", "critical": "✗"}.get(m.health.value, "?")
                    print(f"  {health_tag} [{m.motif_type.value}] (conf={m.confidence:.2f}, health={m.health.value})")
                    print(f"     {m.description[:120]}")
                    for ind in m.indicators[:3]:
                        print(f"     - {ind}")
                    if m.recommended_action:
                        print(f"     -> {m.recommended_action[:120]}")

        elif args.evolution_command == "genome":
            extractor = GenomeExtractor()
            genome = extractor.extract(repo_path)

            if args.compare:
                other_path = Path(args.compare).resolve()
                if not other_path.is_dir():
                    print(f"Not a directory: {other_path}")
                    return
                other_genome = extractor.extract(other_path)
                comparator = GenomeComparator()
                comparison = comparator.compare(genome, other_genome)
                output = {"genome_a": genome.to_dict(), "genome_b": other_genome.to_dict(), "comparison": comparison.to_dict()}
            elif args.predict:
                predictor = GenomePredictor(genome)
                output = {
                    "genome": genome.to_dict(),
                    "maintainability": predictor.predict_maintainability(),
                    "fragility": predictor.predict_fragility(),
                    "scaling": predictor.predict_scaling_behavior(),
                    "evolution_path": predictor.predict_evolution_path(),
                }
            elif args.cluster:
                all_genomes = [genome]
                for p in args.cluster:
                    p_path = Path(p).resolve()
                    if p_path.is_dir():
                        all_genomes.append(extractor.extract(p_path))
                clusterer = GenomeClusterer()
                output = {
                    "genomes": [g.to_dict() for g in all_genomes],
                    "clusters": clusterer.cluster(all_genomes),
                }
            else:
                output = genome.to_dict()

            output_str = json.dumps(output, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Genome data written to {args.output}")
            else:
                print(f"\n=== Repository Genome: {repo_path.name} ===")
                print(f"Genome ID: {genome.genome_id}")
                print(f"Loci: {len(genome.loci)}")
                print(f"Compact: {genome.to_compact()[:200]}")
                for segment in [s for s in GenomeSegment]:
                    loci = genome.get_segment(segment)
                    if loci:
                        print(f"\n  [{segment.value}]")
                        for l in loci[:5]:
                            print(f"    {l.name}: {str(l.value)[:60]}")
                if args.compare:
                    print(f"\n  === Comparison ===")
                    print(f"  Overall similarity: {comparison.overall_similarity:.3f}")
                    for seg, sim in comparison.segment_similarities.items():
                        print(f"  {seg}: {sim:.3f}")
                if args.predict:
                    for pred_name in ["maintainability", "fragility", "scaling"]:
                        p = output[pred_name]
                        print(f"\n  {pred_name}: score={p['score']:.3f}")

        elif args.evolution_command == "mutate":
            repo_path = Path(getattr(args, 'repo', '.')).resolve()
            from lyme.evolution.mutation_engine import MutationEngine
            engine = MutationEngine(repo_path)
            if args.apply:
                mutations = engine.generate_mutations()
                if mutations:
                    m = mutations[0]
                    engine.simulate_impact(m)
                    engine.produce_patches(m)
                    result = m.to_dict()
                    print(f"\n=== Applied Mutation: {m.description} ===")
                    print(f"  Type: {m.mutation_type.value}")
                    print(f"  Benefit: {m.predicted_benefit.overall_score():.3f}")
                    print(f"  Risk: {m.predicted_risk.overall_risk():.3f}")
                    print(f"  Patches: {len(m.patches)}")
            else:
                mutations = engine.generate_mutations()
                print(f"\n=== Generated {len(mutations)} mutations ===")
                for m in mutations[:10]:
                    engine.simulate_impact(m)
                    impact = m.simulated_impact
                    print(f"  [{m.mutation_type.value}] {m.description[:70]}")
                    print(f"       benefit={m.predicted_benefit.overall_score():.3f} risk={m.predicted_risk.overall_risk():.3f} net={impact.get('net_impact', 0):.3f}")
            if args.benchmark and mutations:
                m = mutations[0]
                benchmark = engine.benchmark_mutation(m)
                print(f"\n  Benchmark: {benchmark.duration_ms:.1f}ms, mem_delta={benchmark.memory_delta_kb:.1f}KB")
            if args.output:
                import json
                data = [m.to_dict() for m in engine.get_mutation_history()]
                with open(args.output, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"Mutation data written to {args.output}")

        elif args.evolution_command == "fitness":
            repo_path = Path(getattr(args, 'repo', '.')).resolve()
            from lyme.evolution.fitness_refactoring import FitnessAssessor, FitnessGuidedRefactorer
            assessor = FitnessAssessor(repo_path)
            assessment = assessor.assess()
            print(f"\n=== Architecture Fitness Assessment: {repo_path.name} ===")
            print(f"Overall: {assessment.overall_fitness:.4f}")
            print(f"Weakest: {assessment.weakest_dimension}")
            print(f"Strongest: {assessment.strongest_dimension}\n")
            for dim_name, score in sorted(assessment.scores.items()):
                bar = "█" * int(score.score * 20) + "░" * (20 - int(score.score * 20))
                print(f"  [{bar}] {dim_name:25s} {score.score:.4f} (conf={score.confidence:.2f})")
            if args.output:
                import json
                with open(args.output, "w") as f:
                    json.dump(assessment.to_dict(), f, indent=2, default=str)
                print(f"\nFitness data written to {args.output}")

        elif args.evolution_command == "sandbox":
            repo_path = Path(getattr(args, 'repo', '.')).resolve()
            from lyme.evolution.sandbox import EvolutionSandbox
            sandbox = EvolutionSandbox(repo_path)
            if args.list:
                experiments = sandbox.list_experiments()
                print(f"\n=== Sandbox Experiments ({len(experiments)}) ===")
                for e in experiments:
                    print(f"  [{e.status.value}] {e.name} ({e.branch_name})")
            elif args.apply:
                from lyme.evolution.mutation_engine import MutationEngine
                engine = MutationEngine(repo_path)
                mutations = engine.generate_mutations()
                if mutations:
                    m = mutations[0]
                    experiment = sandbox.run_full_experiment(args.name, m)
                    print(f"\n=== Experiment: {experiment.name} ===")
                    print(f"Status: {experiment.status.value}")
                    print(f"Branch: {experiment.branch_name}")
                    comparison = experiment.comparison
                    if comparison:
                        print(f"Fitness delta: {comparison.get('overall_delta', 'N/A')}")
                    tests = experiment.test_results
                    if tests:
                        print(f"Tests: {'passed' if tests.get('passed') else 'failed'}")
                    print(f"Trace: {len(experiment.trace_log)} events")

    def _do_predict(self, args):
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        if args.predict_command == "run":
            predictor = FailurePredictor()
            prediction = predictor.predict(repo_path)
            result = prediction.to_dict()
            print(f"\n=== Failure Prediction ===")
            print(f"Files analyzed: {result['file_profiles_count']}")
            print(f"Pipeline confidence: {result['pipeline_confidence']:.2f}")
            print(f"\nTop Risks:")
            for risk in result['top_risks'][:10]:
                print(f"  [{risk['category']}] {risk['name'][:60]} (score={risk['score']:.2f})")
            print(f"\nEvidence:")
            for ev in result['evidence_trail']:
                print(f"  - {ev}")
            if result['alternative_strategies']:
                print(f"\nStrategies:")
                for s in result['alternative_strategies']:
                    print(f"  - {s}")
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"\nPrediction written to {args.output}")

    def _do_learn(self, args):
        repo_path = Path(args.repo_path).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        if args.learn_command == "extract":
            engine = HistoricalLearningEngine()
            engine.learn_from_git_history(repo_path)
            result = engine.memory.to_dict()
            print(f"\n=== Historical Learning ===")
            print(f"Total memories: {result['total_items']}")
            print(f"By type: {result['by_type']}")
            print(f"High confidence: {result['high_confidence_count']}")

        elif args.learn_command == "query":
            engine = HistoricalLearningEngine()
            engine.learn_from_git_history(repo_path)
            results = engine.query(args.query)
            recommendations = engine.recommend(repo_path, args.query)
            print(f"\n=== Query: '{args.query}' ===")
            print(f"Found {results.total_found} matching memories")
            if results.items:
                print(f"\nTop matches:")
                for item in results.items[:5]:
                    score = results.similarity_scores.get(item.id, 0)
                    print(f"  [{item.memory_type.value}] (sim={score:.2f}) {item.description[:80]}")
            if recommendations:
                print(f"\nRecommendations ({len(recommendations)}):")
                for r in recommendations[:5]:
                    if 'steps' in r and r['steps']:
                        print(f"  [{r.get('type', 'strategy')}] Steps: {' -> '.join(r['steps'][:3])}")
                    else:
                        print(f"  [{r.get('type', 'pattern')}] {r.get('pattern', r.get('description', ''))[:100]}")

    def _do_society(self, args):
        if args.society_command == "debate":
            engine = DebateEngine()
            verdict = engine.debate(args.problem)
            print(f"\n=== Debate Result ===")
            print(f"Approved: {verdict.approved}")
            print(f"Score: {verdict.score:.2f}")
            print(f"Consensus: {verdict.consensus}")
            print(f"Final confidence: {verdict.final_confidence:.2f}")
            if verdict.remaining_concerns:
                print(f"Remaining concerns:")
                for c in verdict.remaining_concerns[:5]:
                    print(f"  - {c}")

        elif args.society_command == "specialize":
            engine = SpecializationEngine()
            domains = list(DomainExpertise)
            agents = []
            for i in range(args.agents):
                preferred = [domains[i % len(domains)]]
                profile = engine.create_agent(f"Agent_{i}", domains=preferred)
                agents.append(profile)

            import random
            for task_id in range(args.tasks):
                domain = random.choice(domains)
                assigned = engine.assign_task(domain.value, f"task_{task_id}")
                if assigned:
                    success = random.random() < 0.7
                    quality = random.uniform(0.5, 1.0)
                    engine.record_outcome(assigned.agent_id, domain.value, success, quality)

                if len(agents) >= 2:
                    a = random.choice(agents)
                    b = random.choice([x for x in agents if x.agent_id != a.agent_id])
                    if a and b:
                        engine.record_collaboration(a.agent_id, b.agent_id)

            result = engine.measure_specialization_emergence()
            print(f"\n=== Specialization Experiment ===")
            print(f"Agents: {result.get('agent_count', 0)}")
            print(f"Specialization level: {result.get('specialization_level', 0):.2f}")
            print(f"Collaboration clusters: {result.get('collaboration_clusters', 0)}")
            print(f"Total collaborations: {result.get('total_collaborations', 0)}")
            print(f"\nTop specializations:")
            for domain, score in result.get('top_specializations', []):
                print(f"  {domain}: {score:.2f}")

            print(f"\nAgent profiles:")
            for agent_id, profile in engine.profiles.items():
                top = profile.get_top_competency()
                print(f"  {profile.name}: top={top}, success={profile.reputation.success_rate:.0%}")

        elif args.society_command == "topology":
            topo_map = {
                "star": TopologyType.STAR,
                "ring": TopologyType.RING,
                "mesh": TopologyType.MESH,
                "tree": TopologyType.TREE,
                "line": TopologyType.LINE,
                "fully_connected": TopologyType.FULLY_CONNECTED,
            }
            experiment = TopologyExperiment()
            topology = topo_map.get(args.topology, TopologyType.MESH)
            result = experiment.simulate(topology, args.agents, args.tasks)
            print(f"\n=== Topology Experiment: {args.topology} ===")
            print(f"Messages: {result.total_messages}")
            print(f"Total bytes: {result.total_bytes}")
            print(f"Compression savings: {result.compression_savings:.1%}")
            print(f"Information loss: {result.information_loss:.1%}")
            print(f"Coordination overhead: {result.coordination_overhead_ms:.0f}ms")
            print(f"Tasks completed: {result.tasks_completed}")
            print(f"Efficiency: {result.tasks_completed / max(result.total_messages, 1):.3f} tasks/message")

        elif args.society_command == "memory":
            memory = CollectiveMemory()
            trust = TrustWeightingSystem()

            if args.action == "store":
                mem_type = MemoryType(args.type)
                entry = MemoryEntry(
                    memory_type=mem_type,
                    content=args.content or "test memory",
                    agent_id=args.agent,
                )
                mem_id = memory.store(entry)
                print(f"Stored memory: {mem_id}")

            elif args.action == "search":
                query = MemoryQuery(query=args.query or "", limit=10)
                results = memory.search(query)
                print(f"\n=== Memory Search: '{args.query}' ===")
                print(f"Found: {results.total_found}")
                for e in results.top(10):
                    print(f"  [{e.memory_type.value}] {e.content[:80]}... (conf={e.confidence:.2f}, weight={e.effective_weight:.2f})")

            elif args.action == "stats":
                stats = memory.get_statistics()
                print(f"\n=== Collective Memory Statistics ===")
                for k, v in stats.items():
                    print(f"  {k}: {v}")

            elif args.action == "resolve":
                resolved = memory.resolve_conflicts()
                print(f"Resolved {resolved} memory conflicts")

            elif args.action == "trust":
                tstats = trust.get_statistics()
                print(f"\n=== Trust Weighting System ===")
                for k, v in tstats.items():
                    print(f"  {k}: {v}")

        elif args.society_command == "simulate":
            config = SimulationConfig(
                num_agents=args.agents,
                num_tasks=args.tasks,
                num_ticks=args.ticks,
                seed=args.seed,
            )
            simulator = SocietySimulator(config)
            snapshots = simulator.run()
            summary = simulator.get_summary()
            agent_analysis = simulator.get_agent_analysis()

            output_data = {
                "config": config.to_dict(),
                "summary": summary,
                "agent_analysis": agent_analysis,
                "snapshots": [s.to_dict() for s in snapshots],
            }

            output_str = json.dumps(output_data, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Simulation results written to {args.output}")
            else:
                print(f"\n=== Agent Society Simulation ===")
                print(f"Ticks: {summary['ticks']}, Agents: {summary['agents']}")
                print(f"Tasks: {summary['tasks_completed']} completed / {summary['tasks_failed']} failed")
                print(f"Completion rate: {summary['completion_rate']:.1%}")
                print(f"\nSpecialization: {summary['specialization_emergence']['initial']:.2f} -> {summary['specialization_emergence']['final']:.2f}")
                print(f"Hierarchy depth: {summary['hierarchy_emergence']['initial']} -> {summary['hierarchy_emergence']['final']}")
                print(f"Trust avg: {summary['trust_evolution']['initial']:.2f} -> {summary['trust_evolution']['final']:.2f}")
                print(f"Collaborations: {summary['collaboration_emergence']['initial']} -> {summary['collaboration_emergence']['final']}")
                print(f"Gini coefficient: {summary['gini_evolution']['initial']:.3f} -> {summary['gini_evolution']['final']:.3f}")
                print(f"\nRoles: {summary['roles_distribution']}")
                print(f"\nTop agents:")
                for a in agent_analysis.get("top_agents", [])[:3]:
                    print(f"  {a['name']}: role={a['role']}, rep={a['reputation']:.2f}, success={a['success_rate']:.0%}, level={a['hierarchy_level']}")

        elif args.society_command == "market":
            engine = MarketCoordinationEngine()

            domains = ["architecture", "testing", "performance", "security", "debugging"]
            for i in range(args.agents):
                role = MarketRole.PRODUCER if i < args.agents - 2 else MarketRole.VERIFIER
                agent_domains = [random.choice(domains) for _ in range(random.randint(1, 3))]
                engine.create_agent(f"Agent_{i}", role=role, domains=agent_domains)

            for i in range(args.tasks):
                engine.create_task(
                    domain=random.choice(domains),
                    complexity=random.uniform(0.2, 0.9),
                    budget=random.uniform(5, 20),
                    required_quality=random.uniform(0.4, 0.8),
                )

            states = engine.run_simulation(num_epochs=args.epochs)
            comparison = engine.compare_with_orchestration()

            output_data = {
                "agents": [a.to_dict() for a in engine.agents.values()],
                "tasks": [t.to_dict() for t in engine.tasks],
                "market_analysis": comparison,
                "state_history": [s.to_dict() for s in states],
            }

            output_str = json.dumps(output_data, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Market simulation written to {args.output}")
            else:
                last = states[-1] if states else None
                print(f"\n=== Market-Based Coordination ===")
                print(f"Epochs: {args.epochs}")
                print(f"Agents: {args.agents}")
                if last:
                    print(f"Tasks completed: {last.completed_tasks}")
                    print(f"Tasks failed: {last.failed_tasks}")
                    print(f"Avg quality: {last.avg_quality:.3f}")
                    print(f"Avg reputation: {last.avg_reputation:.3f}")
                    print(f"Total earnings: {last.total_earnings:.1f}")
                    print(f"Efficiency: {last.efficiency:.2f}")
                print(f"\nSpecialization quality: {comparison.get('specialization_quality', {}).get('avg_specialization', 0):.3f}")
                print(f"Top agents:")
                for a in comparison.get("specialization_quality", {}).get("top_agents", [])[:3]:
                    print(f"  {a['name']}: spec={a['specialization']:.2f}, rep={a['reputation']:.2f}, earned={a['earnings']:.1f}")

    def _do_research(self, args):
        if args.research_command == "dimensions":
            framework = SoftwareIntelligenceFramework()
            if args.report:
                report = framework.generate_report()
                print(report)
            else:
                print(f"\n=== Software Intelligence Dimensions ===")
                for dim_name, defn in framework.get_all_definitions().items():
                    print(f"\n  [{dim_name.replace('_', ' ').title()}]")
                    print(f"  Definition: {defn['definition'][:120]}...")
                    print(f"  Proxies: {', '.join(defn['proxies'][:3])}")
                    print(f"  Experiments: {', '.join(defn['experiments'][:2])}")

        elif args.research_command == "benchmarks":
            generator = BenchmarkGenerator()
            suite = generator.generate_suite(count=args.count)
            print(f"\n=== Research Benchmarks ({len(suite)}) ===")
            for bm in suite:
                print(f"  [{bm.category.value}] {bm.name}")
                print(f"    Difficulty: {bm.difficulty:.1f}, Steps: {bm.steps}")
                print(f"    Hidden coupling: {bm.hidden_coupling}, Temporal drift: {bm.temporal_drift}")

        elif args.research_command == "scaling":
            if args.auto:
                experiment = ScalingLawExperiment()
                matrix = experiment.define_experiment(
                    VariableType.MODEL_SIZE,
                    levels=[0.1, 0.3, 0.5, 0.7, 0.9],
                )
                results = experiment.run_all()
                print(f"\n=== Scaling Law Experiments ===")
                for var_name, result_list in results.items():
                    for result in result_list:
                        print(f"\n  Variable: {var_name}")
                        print(f"  Coefficient: {result.get('scaling_coefficient', 'N/A')}")
                        print(f"  Emergence threshold: {result.get('emergence_threshold', 'N/A')}")
                        print(f"  Diminishing returns: {result.get('diminishing_returns_point', 'N/A')}")
                        print(f"  Conclusion: {result.get('conclusion', 'N/A')[:120]}")
            else:
                experiment = ScalingLawExperiment()
                plan = experiment.generate_experiment_plan()
                print(plan)

        elif args.research_command == "experiment":
            question = " ".join(args.question)
            generator = ExperimentGenerator()
            plan = generator.generate(question)
            output = plan.to_markdown()
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"Experiment plan written to {args.output}")
            else:
                print(output)

        elif args.research_command == "ablation":
            components = []
            if args.components:
                for c in args.components:
                    try:
                        components.append(AblationComponent(c))
                    except ValueError:
                        print(f"Unknown component: {c}. Options: {[e.value for e in AblationComponent]}")
                        return
            else:
                components = [c for c in AblationComponent if c not in (AblationComponent.ALL, AblationComponent.NONE)]

            ablation = AutomatedAblation()
            baseline = {
                "task_completion": 0.75,
                "code_accuracy": 0.80,
                "hallucination_rate": 0.10,
                "context_utilization": 0.65,
                "edit_success": 0.70,
            }
            report = ablation.run_all_ablations(
                tasks=["bug_fix", "refactor"],
                baseline_metrics=baseline,
                components=components,
            )
            output = report.to_markdown()
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"Ablation report written to {args.output}")
            else:
                print(output)

        elif args.research_command == "report":
            import json as _json
            control_metrics = {}
            treatment_metrics = {}

            if args.control:
                try:
                    with open(args.control) as f:
                        data = _json.load(f)
                        for k, v in data.items():
                            control_metrics[k] = v if isinstance(v, list) else [v]
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error loading control file: {e}")
                    return

            if args.treatment:
                try:
                    with open(args.treatment) as f:
                        data = _json.load(f)
                        for k, v in data.items():
                            treatment_metrics[k] = v if isinstance(v, list) else [v]
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error loading treatment file: {e}")
                    return

            if not control_metrics:
                control_metrics = {
                    "task_completion": [0.70, 0.72, 0.68, 0.75, 0.71],
                    "code_accuracy": [0.78, 0.82, 0.76, 0.80, 0.79],
                    "hallucination_rate": [0.12, 0.10, 0.15, 0.08, 0.11],
                }
                print("Using example control data")

            if not treatment_metrics:
                treatment_metrics = {
                    "task_completion": [0.82, 0.85, 0.79, 0.88, 0.81],
                    "code_accuracy": [0.85, 0.89, 0.83, 0.87, 0.86],
                    "hallucination_rate": [0.06, 0.04, 0.08, 0.05, 0.07],
                }
                print("Using example treatment data")

            generator = ResearchReportGenerator()
            report = generator.generate_from_metrics(
                title=args.title,
                control_metrics=control_metrics,
                treatment_metrics=treatment_metrics,
                metadata={"repetitions": 5, "temperature": 0.0},
            )
            output = report.to_markdown()
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"Research report written to {args.output}")
            else:
                print(output)

    def _do_observe(self, args):
        from .observatory import ContinuousObservatory, ObservatoryConfig, HealthForecastingEngine, ObservatoryUIRenderer

        if args.observe_command == "run":
            config = ObservatoryConfig(
                repository=args.repo,
                poll_interval_seconds=args.interval,
            )
            observatory = ContinuousObservatory(config)
            observatory.start()

            repo_path = Path(args.repo).resolve()
            print(f"\n=== Continuous Observatory: {repo_path.name} ===")

            for i in range(args.iterations):
                snapshot = observatory.observe(
                    file_structure={},
                    commit="HEAD",
                    branch="main",
                )
                summary = observatory.generate_daily_summary()
                state = observatory.get_state()

                print(f"\n  Observation {i+1}/{args.iterations}")
                print(f"  Health: {state.get('overall_health', 0):.3f}")
                print(f"  Subsystems: {len(snapshot.subsystem_health)}")
                print(f"  Anomalies: {len(snapshot.anomalies)}")
                print(f"  Alerts: {summary.risk_alerts_active}")
                print(f"  Degrading trends: {summary.trends_degrading}")
                for rec in summary.recommendations[:2]:
                    print(f"  → {rec}")

                import time as _time
                if i < args.iterations - 1:
                    _time.sleep(0.1)

            observatory.stop()
            print(f"\n  Observations complete. Total: {state.get('observations', 0)}")

            if args.output:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                import json as _json
                with open(output_dir / "observatory_state.json", "w") as f:
                    _json.dump(observatory.get_state(), f, indent=2, default=str)
                print(f"  State saved to {output_dir / 'observatory_state.json'}")

                renderer = ObservatoryUIRenderer()
                html_path = renderer.render(observatory, output_path=str(output_dir / "observatory.html"))
                print(f"  Dashboard saved to {html_path}")

        elif args.observe_command == "forecast":
            engine = HealthForecastingEngine()

            subsystems = ["core", "api", "data", "ui", "infra"]
            for sub in subsystems:
                import random as _random
                for _ in range(10):
                    health = max(0.1, min(1.0, 0.7 + _random.uniform(-0.3, 0.2)))
                    engine.record_health(sub, health)

            results = engine.forecast_all(subsystems, horizon_days=args.horizon)
            summary = engine.get_forecast_summary()

            output_data = {
                "forecasts": [r.to_dict() for r in results],
                "summary": summary,
            }

            output_str = json.dumps(output_data, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Forecasts written to {args.output}")
            else:
                print(f"\n=== Repository Health Forecast ===")
                print(f"Horizon: {args.horizon} days")
                print(f"Subsystems analyzed: {len(results)}")
                for r in results:
                    arrow = "↑" if r.trend == "improving" else "↓" if r.trend == "degrading" else "→"
                    print(f"  {arrow} {r.subsystem}: {r.current_health:.2f} → {r.projected_health:.2f} "
                          f"(ci: [{r.confidence_interval[0]:.2f}, {r.confidence_interval[1]:.2f}], "
                          f"conf={r.confidence:.2f})")
                    for f in r.causal_factors[:2]:
                        print(f"     causal: {f.name} ({f.impact_direction}, mag={f.impact_magnitude:.2f})")
                if summary.get("needs_refactor"):
                    print(f"\n  Needs refactoring: {', '.join(summary['needs_refactor'])}")

        elif args.observe_command == "ui":
            config = ObservatoryConfig()
            observatory = ContinuousObservatory(config)
            observatory.start()

            repo_path = Path(".").resolve()
            for i in range(3):
                observatory.observe(file_structure={}, commit="HEAD", branch="main")
                observatory.generate_daily_summary()

            observatory.stop()

            renderer = ObservatoryUIRenderer()
            html_path = renderer.render(observatory, output_path=args.output)
            print(f"Observatory dashboard written to {html_path}")

    def _do_improve(self, args):
        if args.improve_command == "workflow":
            engine = WorkflowEvolutionEngine()

            if args.action == "observe":
                step_types = list(StepType)
                steps = []
                for i in range(args.steps):
                    steps.append({
                        "type": random.choice(step_types).value,
                        "target": f"file_{i}.py",
                        "context_size": random.randint(100, 5000),
                        "duration_ms": random.uniform(100, 5000),
                        "success": random.random() < 0.85,
                        "depth": random.randint(0, 3),
                        "is_verification": random.random() < 0.2,
                    })
                sequence = engine.observe_workflow(steps)
                print(f"\n=== Workflow Observed ===")
                print(f"Sequence: {sequence.id}")
                print(f"Steps: {len(sequence.steps)}")
                print(f"Fitness: {sequence.fitness:.3f}")
                print(f"Pattern: {' -> '.join(s.step_type.value for s in sequence.steps[:10])}")

            elif args.action == "compress":
                step_types = list(StepType)
                steps = []
                for i in range(10):
                    steps.append({
                        "type": random.choice([StepType.READ, StepType.SEARCH, StepType.VERIFY, StepType.EDIT]).value,
                        "target": f"target_{i}.py",
                        "context_size": random.randint(200, 3000),
                        "duration_ms": random.uniform(200, 4000),
                        "success": True,
                        "depth": 0,
                        "is_verification": random.random() < 0.3,
                    })
                sequence = engine.observe_workflow(steps)
                result = engine.compress_workflow(sequence.id)
                if result:
                    print(f"\n=== Workflow Compression ===")
                    print(f"Original: {result.original_step_count} steps")
                    print(f"Compressed: {result.compressed_step_count} steps")
                    print(f"Ratio: {result.compression_ratio:.2f}")
                    print(f"Redundancies removed: {result.removed_redundancies}")
                    print(f"Fitness impact: {result.fitness_impact:+.3f}")

            elif args.action == "mutate":
                step_types = list(StepType)
                steps = []
                for i in range(6):
                    steps.append({
                        "type": random.choice(step_types).value,
                        "target": f"mutate_{i}.py",
                        "context_size": random.randint(100, 2000),
                        "duration_ms": random.uniform(100, 3000),
                        "success": True,
                        "depth": 0,
                        "is_verification": False,
                    })
                sequence = engine.observe_workflow(steps)
                mutated = engine.mutate(sequence.id)
                if mutated:
                    print(f"\n=== Workflow Mutation ===")
                    print(f"Parent fitness: {sequence.fitness:.3f}")
                    print(f"Mutated fitness: {mutated.fitness:.3f}")
                    print(f"Parent steps: {len(sequence.steps)}, Mutated steps: {len(mutated.steps)}")

            elif args.action == "evolve":
                step_types = list(StepType)
                steps = []
                for i in range(6):
                    steps.append({
                        "type": random.choice(step_types).value,
                        "target": f"evolve_{i}.py",
                        "context_size": random.randint(100, 2000),
                        "duration_ms": random.uniform(100, 3000),
                        "success": True,
                        "depth": 0,
                        "is_verification": random.random() < 0.3,
                    })
                sequence = engine.observe_workflow(steps)
                history = engine.evolve(sequence.id, generations=args.generations)
                print(f"\n=== Workflow Evolution ===")
                print(f"Generations: {len(history)}")
                print(f"Initial fitness: {sequence.fitness:.3f}")
                print(f"Best fitness: {max((h.fitness for h in history), default=0):.3f}")
                print(f"Fitness history: {[f'{h.fitness:.3f}' for h in history[:10]]}")

            elif args.action == "stats":
                stats = engine.get_statistics()
                print(f"\n=== Workflow Evolution Engine ===")
                for k, v in stats.items():
                    if isinstance(v, float):
                        print(f"  {k}: {v:.3f}")
                    else:
                        print(f"  {k}: {v}")

        elif args.improve_command == "prompt":
            engine = PromptEvolutionEngine()

            if args.action == "seed":
                engine.seed()
                print(f"\n=== Prompt Genome Seeded ===")
                print(f"Variants: {len(engine.genome.variants)}")
                print(f"Best fitness: {engine.genome.best_fitness:.3f}")
                best = engine.evaluate_variant(engine.genome.best_variant_id) if engine.genome.best_variant_id else None
                if best:
                    print(f"Best text: {best['full_text'][:200]}...")

            elif args.action == "evolve":
                engine.seed()
                genome = engine.evolve(generations=args.generations)
                print(f"\n=== Prompt Evolution Complete ===")
                print(f"Generations: {genome.generation}")
                print(f"Variants tested: {len(genome.variants)}")
                print(f"Best fitness: {genome.best_fitness:.3f}")
                print(f"Diversity: {genome.diversity:.3f}")
                print(f"Convergence: {genome.convergence_score:.3f}")
                if genome.best_variant_id:
                    best = engine.evaluate_variant(genome.best_variant_id)
                    if best:
                        print(f"\nBest prompt:")
                        for seg, text in best.get("segments", {}).items():
                            print(f"  [{seg}]: {text[:100]}...")

            elif args.action == "best":
                if engine.genome.best_variant_id:
                    best = engine.evaluate_variant(engine.genome.best_variant_id)
                    if best:
                        print(f"\n=== Best Prompt ===")
                        print(f"Fitness: {best['fitness']:.3f}")
                        print(f"Safety: {best['safety']:.3f}")
                        print(f"Text:\n{best['full_text']}")

            elif args.action == "stats":
                stats = engine.get_statistics()
                print(f"\n=== Prompt Evolution Engine ===")
                for k, v in stats.items():
                    if isinstance(v, float):
                        print(f"  {k}: {v:.3f}")
                    else:
                        print(f"  {k}: {v}")

        elif args.improve_command == "arch":
            searcher = CognitiveArchitectureSearch()
            result = searcher.search(
                method=args.method,
                num_samples=args.samples,
                population_size=args.population,
                generations=args.generations,
            )

            output_data = result.to_dict()
            output_str = json.dumps(output_data, indent=2, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output_str)
                print(f"Architecture search results written to {args.output}")
            else:
                print(f"\n=== Cognitive Architecture Search ===")
                print(f"Method: {args.method}")
                print(f"Search space: {result.search_space_size} architectures")
                print(f"Explored: {result.explored_count} architectures")
                if result.best_benchmark:
                    bb = result.best_benchmark
                    print(f"\nBest architecture fitness: {bb.composite_score:.4f}")
                    print(f"  Task completion: {bb.task_completion:.3f}")
                    print(f"  Code accuracy: {bb.code_accuracy:.3f}")
                    print(f"  Hallucination rate: {bb.hallucination_rate:.3f}")
                    print(f"  Context efficiency: {bb.context_efficiency:.3f}")
                if result.best_variant:
                    print(f"\nBest architecture dimensions:")
                    for dim, val in result.best_variant.dimensions.items():
                        print(f"  {dim.value}: {val}")
                if result.dimension_importance:
                    print(f"\nDimension importance:")
                    for dim, imp in sorted(result.dimension_importance.items(), key=lambda x: -x[1])[:5]:
                        print(f"  {dim}: {imp:.3f}")

    def _do_self(self, args):
        repo_path = Path(getattr(args, "repo", ".")).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        trigger = SelfDescriptionUpdateTrigger(repo_path)
        if args.update:
            desc = trigger.update()
            if desc is None:
                desc = SelfDescriptionGenerator(repo_path).generate()
        else:
            desc = trigger.load()
            if desc is None:
                print("No cached self-description. Generating...")
                desc = SelfDescriptionGenerator(repo_path).generate()
                lyme_dir = repo_path / ".lyme"
                lyme_dir.mkdir(parents=True, exist_ok=True)
                (lyme_dir / "self-description.json").write_text(
                    json.dumps(desc.to_dict(), indent=2, default=str)
                )

        if args.format == "json":
            output = json.dumps(desc.to_dict(), indent=2, default=str)
        else:
            output = desc.to_markdown()

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Self-description written to {args.output}")
        else:
            print(output)

    def _do_archfile(self, args):
        repo_path = Path(getattr(args, "repo", ".")).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        if args.archfile_command == "generate":
            generator = ArchitectureFileGenerator(repo_path)
            arch = generator.generate()
            updater = ArchitectureFileUpdater(repo_path)
            updater._arch_path.parent.mkdir(parents=True, exist_ok=True)
            updater._arch_path.write_text(arch.to_json())

            output = args.output or str(updater._arch_path)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(arch.to_json())
            print(f"Architecture file written to {output}")
            print(f"Subsystems: {len(arch.subsystems)}")
            print(f"Boundary rules: {len(arch.boundary_rules)}")
            print(f"Dependency rules: {len(arch.dependency_rules)}")

        elif args.archfile_command == "validate":
            updater = ArchitectureFileUpdater(repo_path)
            arch = updater.load()
            if not arch:
                print("No architecture file found. Run `lyme archfile generate` first.")
                return
            validator = ArchitectureFileValidator()
            result = validator.validate(arch)
            print(f"Valid: {result['valid']}")
            if result['errors']:
                print(f"\nErrors ({len(result['errors'])}):")
                for e in result['errors']:
                    print(f"  - {e}")
            if result['warnings']:
                print(f"\nWarnings ({len(result['warnings'])}):")
                for w in result['warnings']:
                    print(f"  - {w}")

        elif args.archfile_command == "violations":
            updater = ArchitectureFileUpdater(repo_path)
            arch = updater.load()
            if not arch:
                print("No architecture file found. Run `lyme archfile generate` first.")
                return
            detector = ArchitectureViolationDetector(repo_path)
            violations = detector.detect(arch)
            print(f"Violations detected: {len(violations)}")
            for v in violations:
                print(f"  [{v['severity']}] {v['description']}")

        elif args.archfile_command == "view":
            updater = ArchitectureFileUpdater(repo_path)
            arch = updater.load()
            if not arch:
                print("No architecture file found. Run `lyme archfile generate` first.")
                return
            print(arch.to_markdown())

        elif args.archfile_command == "mermaid":
            updater = ArchitectureFileUpdater(repo_path)
            arch = updater.load()
            if not arch:
                print("No architecture file found. Run `lyme archfile generate` first.")
                return
            print(ArchitectureFileRenderer.to_mermaid(arch))

        else:
            print("Unknown archfile command. Use: generate, validate, violations, view, mermaid")

    def _do_plan(self, args):
        repo_path = Path(getattr(args, "repo", ".")).resolve()
        if not repo_path.is_dir():
            print(f"Not a directory: {repo_path}")
            return

        task = " ".join(args.task)
        print(f"Planning for: {task}")

        if args.baseline:
            planner = BaselinePlanner(repo_path)
        else:
            planner = ArchitectureAwarePlanner(repo_path)

        result = planner.plan(task)

        if args.output:
            with open(args.output, "w") as f:
                if args.format == "json":
                    json.dump(result.to_dict(), f, indent=2, default=str)
                else:
                    f.write(result.to_markdown())
            print(f"Plan written to {args.output}")
        else:
            if args.format == "json":
                print(json.dumps(result.to_dict(), indent=2, default=str))
            else:
                print(result.to_markdown())

        if args.baseline:
            print("\n[BASELINE PLANNER - no architecture awareness]")
        else:
            print(f"\n[ARCHITECTURE-AWARE PLANNER - planning time: {result.planning_time_ms:.0f}ms]")

    def _do_skill(self, args):
        lib = SkillLibrary()

        if args.skill_command == "list":
            skill_type = None
            if args.type:
                try:
                    skill_type = SkillType(args.type)
                except ValueError:
                    print(f"Unknown type: {args.type}. Options: {[t.value for t in SkillType]}")
                    return
            skills = lib.list_by_type(skill_type)
            if not skills:
                print("No skills found.")
                return
            print(f"{'ID':20s} {'Name':30s} {'Type':20s} {'Confidence':12s} {'Status':12s}")
            print("-" * 94)
            for s in skills:
                conf = f"{s.current_confidence:.0%}"
                print(f"{s.id:20s} {s.name[:28]:30s} {s.skill_type.value:20s} {conf:12s} {s.status.value:12s}")
            print(f"\nTotal: {len(skills)} skills")

        elif args.skill_command == "search":
            results = lib.search(args.query)
            if not results:
                print(f"No skills matching '{args.query}'")
                return
            print(f"Skills matching '{args.query}':")
            for s in results:
                print(f"  {s.id}: {s.name} ({s.skill_type.value}, conf={s.current_confidence:.0%})")

        elif args.skill_command == "extract":
            store = EventStore(self.settings.benchmark.output_dir)
            run_data = store.load_run(args.run_id)
            if run_data:
                extractor = SkillExtractor()
                skill = extractor.extract_from_successful_run(run_data)
                if skill:
                    lib.add(skill)
                    print(f"Extracted skill: {skill.name} (id: {skill.id})")
                else:
                    print("Could not extract skill from run data")
            else:
                print(f"Run {args.run_id} not found")

        elif args.skill_command == "transfer":
            target = Path(args.target_repo).resolve()
            if not target.is_dir():
                print(f"Not a directory: {target}")
                return
            engine = SkillTransferEngine()
            experiment = TransferExperiment(engine)
            report = experiment.run_cross_repo_experiment(Path.cwd(), target)
            print(report.to_markdown())

        elif args.skill_command == "critique":
            skill = lib.get(args.skill_id)
            if not skill:
                print(f"Skill {args.skill_id} not found")
                return
            critic = SkillCritic()
            critique = critic.critique(skill)
            print(critique.to_markdown())

        else:
            print("Unknown skill command. Use: list, search, extract, transfer, critique")

    def _do_cross_repo(self, args):
        try:
            from lyme.cross_repo.fingerprint import RepoFingerprinter
            from lyme.cross_repo.pattern_extractor import PatternExtractor
            from lyme.cross_repo.clustering import PatternClusterer
            from lyme.cross_repo.scoring import PatternScorer
            from lyme.cross_repo.insight_generator import InsightGenerator
        except ImportError:
            print("Cross-repo module not available. Install with: pip install lyme[cross-repo]")
            return

        root = Path(args.output)
        root.mkdir(parents=True, exist_ok=True)

        fingerprints = []
        for d in args.dirs:
            repo_path = Path(d).resolve()
            if repo_path.is_dir():
                fp = RepoFingerprinter(repo_path, anonymize=args.anonymize).fingerprint()
                fingerprints.append(fp)
                print(f"  Fingerprinted: {fp.repo_id} ({len(fp.components)} components)")

        extractor = PatternExtractor()
        patterns = extractor.extract_from_fingerprints(fingerprints)
        print(f"\n  Extracted {len(patterns)} cross-repo patterns:")

        scorer = PatternScorer()
        for p in patterns[:10]:
            score = scorer.score_pattern(p)
            print(f"    - {p.name} ({p.occurrences} repos, conf={score.overall:.2f})")

        clusterer = PatternClusterer(n_clusters=args.clusters)
        clusters = clusterer.cluster_fingerprints(fingerprints)
        clusterer.label_clusters(clusters)
        print(f"\n  Found {len(clusters)} repo clusters:")
        for c in clusters:
            print(f"    - {c.label}: {c.size} repos, similarity={c.intra_cluster_similarity:.0%}")

        insight_gen = InsightGenerator()
        insights = insight_gen.generate(patterns, clusters)
        print(f"\n  Generated {len(insights)} transferable insights:")
        for i in insights[:5]:
            print(f"    - {i.title} ({i.confidence.value})")

        extractor.save(root / "patterns.json")
        clusterer.save(root / "clusters.json")
        insight_gen.save(root / "insights.json")
        print(f"\n  Results saved to {root}/")

    def _do_ecosystem(self, args):
        try:
            from lyme.ecosystem.fastapi_knowledge import FastAPIEcosystemKnowledge
            from lyme.ecosystem.compatibility import CompatibilityChecker
            from lyme.ecosystem.security_zones import SecurityZoneDetector
        except ImportError:
            print("Ecosystem module not available.")
            return

        knowledge = FastAPIEcosystemKnowledge()
        g = knowledge.graph

        if args.eco_command == "info":
            print(f"Ecosystem Graph: {g.node_count} nodes, {g.edge_count} edges")
            nodes = knowledge.get_library_recommendations("")
            print(f"  Known libraries: {len(nodes)}")
            if nodes:
                print(f"  Top: {nodes[0]['name']} v{nodes[0]['version']}")

        elif args.eco_command == "query":
            if args.library:
                deps = g.get_dependencies(args.library.lower())
                dependents = g.get_dependents(args.library.lower())
                upgrade = g.get_upgrade_path(args.library)
                print(f"Library: {args.library}")
                print(f"  Dependencies ({len(deps)}): {', '.join(d.name for d in deps[:5])}")
                print(f"  Used by ({len(dependents)}): {', '.join(d.name for d in dependents[:5])}")
                if upgrade:
                    print(f"  Upgrade paths:")
                    for src, tgt, desc in upgrade:
                        print(f"    {src} -> {tgt}: {desc}")
                bugs = knowledge.get_known_bugs()
                relevant = [b for b in bugs if any(
                    kw in b['name'].lower() for kw in [args.library.lower()]
                )]
                if relevant:
                    print(f"  Known bugs: {len(relevant)}")
                    for b in relevant[:3]:
                        print(f"    - {b['name']} ({b['severity']})")

        elif args.eco_command == "compat":
            checker = CompatibilityChecker()
            if args.dep_file:
                path = Path(args.dep_file)
                if path.exists():
                    text = path.read_text()
                    if path.suffix == ".toml":
                        deps = checker.parse_pyproject(text)
                    else:
                        deps = checker.parse_requirements(text)
                    report = checker.check_compatibility(deps)
                    print(f"Compatibility Report:")
                    print(f"  Score: {report.overall_score:.0%}")
                    print(f"  Issues: {report.total_issues} ({report.critical_count} critical, {report.warning_count} warnings)")
                    for issue in report.issues[:5]:
                        print(f"    [{issue.severity.value}] {issue.library} {issue.version}: {issue.description}")

        elif args.eco_command == "security":
            advisories = knowledge.get_security_advisories()
            print(f"Ecosystem Security Advisories ({len(advisories)}):")
            for adv in advisories[:10]:
                print(f"  [{adv['severity']}] {adv['name']}: {adv['description'][:80]}")

        elif args.eco_command == "deps":
            self._do_ecosystem_deps(args)

        elif args.eco_command == "risk":
            self._do_ecosystem_risk(args)

    def _do_ecosystem_deps(self, args):
        if args.ecosystem == "python":
            engine = EcosystemBenchmarkDatasets.build_python_web_ecosystem()
        elif args.ecosystem == "javascript":
            engine = EcosystemBenchmarkDatasets.build_js_frontend_ecosystem()
        else:
            engine = EcosystemBenchmarkDatasets.build_rust_ecosystem()

        analyzer = TemporalPropagationAnalyzer(engine)
        stability = EcosystemStabilityAnalyzer(engine)
        viz = EcosystemVisualization(engine, stability)

        if args.action == "build":
            metrics = engine.compute_ecosystem_metrics()
            print(json.dumps(metrics, indent=2))

        elif args.action == "analyze":
            print(f"\n=== Ecosystem Analysis: {args.ecosystem} ===")
            metrics = engine.compute_ecosystem_metrics()
            print(f"\nEcosystem Metrics:")
            print(f"  Libraries: {metrics['total_libraries']}")
            print(f"  Edges: {metrics['total_edges']}")
            print(f"  Density: {metrics['density']}")
            print(f"  Central nodes: {metrics['central_nodes']}")
            print(f"  Category diversity: {metrics['category_diversity']}")
            print(f"  Circular deps: {metrics['circular_dependency_count']}")
            frags = engine.detect_ecosystem_fragmentation()
            print(f"\nFragmentation: {len(frags)} communities")
            for f in frags[:5]:
                print(f"  - {f['size']} members: {', '.join(f['members'][:3])}")
            dec = engine.detect_ecosystem_decay()
            print(f"\nDecaying Libraries: {len(dec)}")
            for d in dec[:5]:
                print(f"  - {d['library']} (risk: {d.get('abandonment_risk', 0):.0%})")
            lockin = engine.compute_lock_in_risk()
            print(f"\nLock-in Risks: {len(lockin)}")
            for l in lockin[:5]:
                print(f"  - {l['library']} (score: {l['lock_in_score']:.0%})")
            metrics_report = stability.compute_stability()
            print(f"\nStability: {metrics_report.level.value} ({metrics_report.overall_score:.0%})")

        elif args.action == "chains":
            chains = engine.compute_brittle_chains()
            print(f"Brittle dependency chains: {len(chains)}")
            for c in chains[:10]:
                names = [engine.get_library(n) for n in c.chain[:5]]
                chain_str = " → ".join(n.name if n else n[:8] for n in names)
                print(f"  Risk {c.risk_score:.0%}: {chain_str}")

        elif args.action == "visualize":
            html = viz.to_dependency_graph_html(f"{args.ecosystem.title()} Ecosystem")
            out = args.output or f"ecosystem-{args.ecosystem}-graph.html"
            Path(out).write_text(html)
            print(f"Visualization written to {out}")

        elif args.action == "snapshot":
            import time
            snap = engine.take_snapshot(time.time())
            print(f"Snapshot taken: stability={snap.stability_score:.0%}, fragility={snap.fragility_score:.0%}")
            print(f"  Dominant: {', '.join(snap.dominant_frameworks[:3])}")
            print(f"  Emerging: {', '.join(snap.emerging_trends[:3])}")
            print(f"  Risks: {', '.join(snap.risk_hotspots[:3])}")

        elif args.action == "propagate":
            if not args.library:
                print("--library is required")
                return
            lib = engine.get_library(args.library)
            if lib:
                forecast = analyzer.analyze_update_propagation(args.library, "major")
                print(f"Propagation forecast for {lib.name}:")
                print(f"  Total affected: {forecast.total_affected}")
                print(f"  Impact score: {forecast.total_impact_score}")
                print(f"  Mean delay: {forecast.mean_propagation_time}")
                print(f"  Max depth: {forecast.max_depth}")
                for a in forecast.affected_libraries[:10]:
                    print(f"  → {a['library']} (depth {a['depth']}, impact {a['impact']})")

        elif args.action == "vulnerability":
            if not args.library:
                print("--library is required")
                return
            affected = engine.propagate_vulnerability(args.library)
            print(f"Vulnerability propagation from {args.library}: {len(affected)} affected")
            for a in affected[:15]:
                print(f"  depth {a['depth']}: {a['library']}")

        elif args.action == "migrations":
            waves = stability.forecast_migration_waves()
            print(f"Forecasted migration waves: {len(waves)}")
            for w in waves[:10]:
                print(f"  {w.source} → {w.target} (likelihood: {w.likelihood:.0%}, timeframe: {w.timeframe})")

    def _do_ecosystem_risk(self, args):
        engine = EcosystemBenchmarkDatasets.build_python_web_ecosystem()
        forecaster = EcosystemRiskForecaster(engine)
        scoring = RiskScoringEngine(engine)

        if args.action == "report":
            report = forecaster.generate_ecosystem_report()
            print(report.to_markdown())

        elif args.action == "assess":
            if not args.library:
                print("--library is required")
                return
            profile = forecaster.assess_library_risk(args.library)
            print(f"\nRisk Profile: {profile.library_name}")
            print(f"  Overall Risk: {profile.overall_risk.value} ({profile.risk_score:.0%})")
            print(f"  Abandonment Probability: {profile.abandonment_probability:.0%}")
            print(f"  Breaking Change Probability: {profile.breaking_change_probability:.0%}")
            print(f"  Dependency Chain Risk: {profile.dependency_chain_risk:.0%}")
            print(f"  Recommended Action: {profile.recommended_action}")
            if profile.alternative_libraries:
                print(f"  Alternatives: {', '.join(profile.alternative_libraries)}")

        elif args.action == "migration":
            if not args.source or not args.target:
                print("--source and --target are required")
                return
            risk = forecaster.assess_migration_risk(args.source, args.target)
            print(f"\nMigration Risk: {args.source} → {args.target}")
            print(f"  Risk: {risk.overall_risk.value} ({risk.risk_score:.0%})")
            print(f"  Breaking Changes: {risk.breaking_change_count}")
            print(f"  Estimated Effort: {risk.estimated_effort_person_weeks} person-weeks")
            print(f"  High Risk Components: {', '.join(risk.high_risk_components)}")
            print(f"  Recommended Approach: {risk.recommended_approach}")

        elif args.action == "vulnerabilities":
            if args.dep_file:
                path = Path(args.dep_file)
                if path.exists():
                    from lyme.ecosystem.compatibility import CompatibilityChecker
                    checker = CompatibilityChecker()
                    text = path.read_text()
                    deps = checker.parse_requirements(text) if path.suffix != ".toml" else checker.parse_pyproject(text)
                    result = scoring.compute_combined_risk(deps)
                    print(f"Vulnerability Scan: {result['libraries_scanned']} libraries")
                    print(f"  Overall Risk: {result['overall_risk']}")
                    print(f"  Critical: {result['critical_count']}, High: {result['high_count']}, Medium: {result['medium_count']}")
                    for v in result['vulnerability_details'][:10]:
                        if v['vulnerabilities']:
                            print(f"  - {v['library']} v{v['version']}: {len(v['vulnerabilities'])} vulns")

        elif args.action == "propagate":
            if not args.library:
                print("--library is required")
                return
            propagator = VulnerabilityPropagationScorer(engine)
            result = propagator.compute_propagation_score(args.library)
            print(f"Vulnerability Propagation: {args.library}")
            print(f"  Propagation Score: {result.get('propagation_score', 0):.0%}")
            print(f"  Total Affected: {result.get('total_affected', 0)}")
            print(f"  Max Depth: {result.get('max_depth', 0)}")
            print(f"  Risk Level: {result.get('risk_level', 'unknown')}")

    def _do_fw_obs(self, args):
        obs_react = ReactEcosystemKnowledge.build_observatory()
        obs_fastapi = FastAPIEcosystemKnowledge.build_observatory()
        obs_tokio = RustAsyncEcosystemKnowledge.build_observatory()
        obs_next = NextJSEcosystemKnowledge.build_observatory()

        if args.fw_obs_command == "report":
            fw_map = {"react": obs_react, "fastapi": obs_fastapi, "tokio": obs_tokio, "nextjs": obs_next}
            obs = fw_map.get(args.framework)
            if not obs:
                print(f"Unknown framework: {args.framework}")
                return
            report = obs.compute_evolution_report(args.framework.title())
            if report:
                output = report.to_markdown()
                if args.output:
                    Path(args.output).write_text(output)
                    print(f"Report written to {args.output}")
                else:
                    print(output)
            else:
                print(f"No data for {args.framework}")

        elif args.fw_obs_command == "compare":
            obs_a = obs_react if args.a == "react" else obs_fastapi if args.a == "fastapi" else obs_tokio
            obs_b = obs_react if args.b == "react" else obs_fastapi if args.b == "fastapi" else obs_tokio
            result = obs_a.compare_frameworks(args.a.title(), args.b.title())
            print(f"\nComparison: {result.get('comparison', 'N/A')}")
            print(f"  Health Delta: {result.get('health_delta', 0)}")
            print(f"  Breaking Change Delta: {result.get('breaking_change_delta', 0)}")

        elif args.fw_obs_command == "drift":
            fw_map = {"react": obs_react, "fastapi": obs_fastapi, "tokio": obs_tokio, "nextjs": obs_next}
            obs = fw_map.get(args.framework)
            if not obs:
                print(f"Unknown framework: {args.framework}")
                return
            drifts = obs.detect_convention_drift(args.framework.title())
            print(f"\nConvention Drift: {args.framework.title()}")
            for d in drifts:
                print(f"  [{d['type']}] {d['convention']} (version: {d['version']})")

        elif args.fw_obs_command == "bugs":
            fw_map = {"react": obs_react, "fastapi": obs_fastapi, "tokio": obs_tokio, "nextjs": obs_next}
            obs = fw_map.get(args.framework)
            if not obs:
                print(f"Unknown framework: {args.framework}")
                return
            bugs = obs.get_common_bug_trends(args.framework.title())
            print(f"\nCommon Bug Trends: {args.framework.title()}")
            for b in bugs[:10]:
                print(f"  {b['pattern']} ({b['occurrences']} occurrences)")

        elif args.fw_obs_command == "knowledge":
            kb = FrameworkKnowledgeBase()
            if args.framework:
                fw = kb.get(args.framework)
                if fw:
                    print(f"\n{fw.name}")
                    print(f"  Ecosystem: {fw.ecosystem}")
                    print(f"  Current Version: {fw.current_version}")
                    print(f"  Key Abstractions: {', '.join(fw.key_abstractions)}")
                    print(f"  Strengths: {', '.join(fw.strengths)}")
                    print(f"  Weaknesses: {', '.join(fw.weaknesses)}")
                    print(f"  Common Mistakes: {', '.join(fw.common_mistakes)}")
                else:
                    print(f"Framework '{args.framework}' not found")
            else:
                print(f"Known frameworks: {', '.join(kb.list_frameworks())}")

    def _do_arch(self, args):
        if args.arch_command == "discover":
            repo_path = Path(args.repo_path).resolve()
            if not repo_path.is_dir():
                print(f"Not a directory: {repo_path}")
                return
            modules = [p.name for p in repo_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
            files = [str(p.relative_to(repo_path)) for p in repo_path.rglob("*") if p.is_file() and p.suffix in (".py", ".ts", ".js", ".rs")]
            imports = {}
            for py in repo_path.rglob("*.py"):
                if py.is_file():
                    try:
                        content = py.read_text()
                        for line in content.splitlines():
                            if line.startswith("import ") or line.startswith("from "):
                                parts = line.split()
                                if len(parts) >= 2:
                                    src = py.stem
                                    tgt = parts[1].split(".")[0]
                                    if src not in imports:
                                        imports[src] = []
                                    imports[src].append(tgt)
                    except Exception:
                        pass

            discoverer = ArchitecturePatternDiscovery()
            fp = discoverer.discover_patterns(modules, files, imports)
            print(f"\nArchitecture Pattern Discovery: {repo_path.name}")
            print(f"  Complexity: {fp.complexity_score:.0%}")
            print(f"  Coupling: {fp.coupling_score:.0%}")
            print(f"  Cohesion: {fp.cohesion_score:.0%}")
            print(f"  Primary Pattern: {fp.primary_pattern.value if fp.primary_pattern else 'None'}")
            print(f"  Patterns found: {len(fp.patterns)}")
            for p in fp.patterns[:5]:
                print(f"    [{p.confidence:.0%}] {p.pattern_type.value} ({p.maturity.value})")

        elif args.arch_command == "fitness":
            repo_path = Path(args.repo_path).resolve()
            if not repo_path.is_dir():
                print(f"Not a directory: {repo_path}")
                return
            modules = [p.name for p in repo_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
            files = [str(p.relative_to(repo_path)) for p in repo_path.rglob("*") if p.is_file()]
            imports = {}
            test_files = [f for f in files if "test" in f.lower()]
            for py in repo_path.rglob("*.py"):
                if py.is_file():
                    try:
                        for line in py.read_text().splitlines():
                            if line.startswith("import ") or line.startswith("from "):
                                parts = line.split()
                                if len(parts) >= 2:
                                    src = py.stem
                                    tgt = parts[1].split(".")[0]
                                    if src not in imports:
                                        imports[src] = []
                                    imports[src].append(tgt)
                    except Exception:
                        pass

            engine = ArchitectureFitnessEngine()
            report = engine.evaluate(modules, files, imports, test_files)
            output = report.to_markdown()
            if args.output:
                Path(args.output).write_text(output)
                print(f"Fitness report written to {args.output}")
            else:
                print(output)

        elif args.arch_command == "suggest":
            advisor = ArchitectureAdvisor()
            constraints = [
                ArchitectureConstraint("scale", args.scale, "users", "Expected scale"),
                ArchitectureConstraint("team_size", args.team, "people", "Team size"),
                ArchitectureConstraint("latency_sensitivity", args.latency, "", "Latency requirements"),
                ArchitectureConstraint("reliability", args.reliability, "", "Required reliability"),
            ]
            suggestions = advisor.suggest(constraints)
            print(f"\nArchitecture Suggestions (scale={args.scale}, team={args.team})")
            for s in suggestions[:5]:
                print(f"\n  [{s.fit_score:.0%}] {s.architecture.value}")
                print(f"    Strengths: {', '.join(s.strengths[:3])}")
                print(f"    Weaknesses: {', '.join(s.weaknesses[:2])}")
                print(f"    Maintenance: {s.maintenance_burden}")
                print(f"    Migration path: {s.migration_path or 'N/A'}")

        elif args.arch_command == "compare-arch":
            advisor = ArchitectureAdvisor()
            result = advisor.compare_architectures(
                ArchitectureType(args.a), ArchitectureType(args.b)
            )
            print(f"\nArchitecture Comparison: {args.a} vs {args.b}")
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"  {k}: {', '.join(v[:3])}")
                else:
                    print(f"  {k}: {v}")

        elif args.arch_command == "failures":
            advisor = ArchitectureAdvisor()
            constraints = [
                ArchitectureConstraint("scale", args.scale, "users", ""),
                ArchitectureConstraint("team_size", args.team, "people", ""),
            ]
            failures = advisor.predict_failure_modes(
                ArchitectureType(args.architecture), constraints
            )
            print(f"\nPredicted Failure Modes: {args.architecture}")
            for f in failures:
                print(f"  [{f['risk_level']}] {f['failure_mode']} (prob: {f['probability']:.0%})")

        elif args.arch_command == "pressure":
            repo_path = Path(args.repo_path).resolve()
            if not repo_path.is_dir():
                print(f"Not a directory: {repo_path}")
                return
            modules = [p.name for p in repo_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
            files = [str(p.relative_to(repo_path)) for p in repo_path.rglob("*") if p.is_file() and p.suffix in (".py", ".ts", ".js", ".rs")]
            discoverer = ArchitecturePatternDiscovery()
            fp = discoverer.discover_patterns(modules, files, {})
            pressure = discoverer.track_evolutionary_pressure(fp)
            print(f"\nEvolutionary Pressure: {repo_path.name}")
            print(f"  Dominant: {', '.join(pressure['dominant_patterns'])}")
            print(f"  Emerging: {', '.join(pressure['emerging_patterns'])}")
            for p in pressure['evolutionary_pressures']:
                print(f"  ! {p['pattern']}: {p['pressure']}")

        elif args.arch_command == "search-space":
            advisor = ArchitectureAdvisor()
            space = advisor.architecture_search_space()
            print(f"\nArchitecture Search Space ({len(space)} architectures)")
            for s in space:
                p = s['profiles']
                print(f"\n  {s['architecture']}")
                print(f"    Scale: {p['scale_range'][0]}-{p['scale_range'][1]}")
                print(f"    Team: {p['team_range'][0]}-{p['team_range'][1]}")
                print(f"    Latency: {p['latency_sensitivity']}, Reliability: {p['reliability']:.0%}")
                print(f"    Maintenance: {p['maintenance_burden']}")

    def _do_fabric(self, args):
        fabric = MemoryFabric("lyme-fabric")

        if args.fabric_command == "store":
            provenance = [ProvenanceEntry(
                source_repo=args.repo, source_path="cli",
                timestamp=__import__("time").time(), confidence=args.confidence,
                extraction_method="cli_store",
            )]
            mem = fabric.store(
                content=args.content,
                category=MemoryCategory(args.category),
                provenance=provenance,
                tags=args.tags,
                confidence=args.confidence,
            )
            print(f"Stored memory: {mem.id}")

        elif args.fabric_command == "query":
            query = MemoryQuery(
                query=args.query,
                category=MemoryCategory(args.category) if args.category else None,
                repo_filter=args.repo,
                max_results=args.max,
            )
            results = fabric.query(query)
            print(f"Memory fabric results ({len(results)}):")
            for r in results:
                print(f"\n  [{r.relevance_score:.0%}] {r.memory.content[:100]}...")
                print(f"    Category: {r.memory.category.value}")
                print(f"    Confidence: {r.memory.confidence:.0%}")
                print(f"    Sources: {', '.join(p.source_repo for p in r.memory.provenance[:2])}")

        elif args.fabric_command == "stats":
            stats = fabric.statistics()
            print(f"\nMemory Fabric: {stats['name']}")
            print(f"  Memories: {stats['total_memories']}")
            print(f"  Contradictions: {stats['contradictions']} ({stats['unresolved_contradictions']} unresolved)")
            print(f"  Categories:")
            for cat, count in stats.get('categories', {}).items():
                print(f"    {cat}: {count}")
            print(f"  Repos served: {len(stats.get('repos', {}))}")
            print(f"  Avg confidence: {stats['avg_confidence']:.0%}")

        elif args.fabric_command == "transfer":
            score = fabric.compute_cross_repo_transfer_score(args.source_repo, args.target_repo)
            print(f"\nCross-Repo Transfer: {args.source_repo} → {args.target_repo}")
            print(f"  Transfer Score: {score['transfer_score']:.0%}")
            print(f"  Shared Categories: {', '.join(score.get('shared_categories', []))}")
            print(f"  Source Memories: {score['source_memory_count']}")
            print(f"  Target Memories: {score['target_memory_count']}")

    def _do_compress(self, args):
        engine = SemanticCompressionEngine()

        if args.compress_command == "discover":
            code_samples = []
            for fp in args.files:
                path = Path(fp)
                if path.exists():
                    code_samples.append({"code": path.read_text(), "repo": path.parent.name})
            abstractions = engine.discover_abstractions(code_samples)
            output_data = [a.to_dict() for a in abstractions]
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(output_data, f, indent=2)
                print(f"Abstractions written to {args.output}")
            else:
                print(f"\nDiscovered {len(abstractions)} abstractions:")
                for a in abstractions:
                    print(f"\n  [{a.confidence:.0%}] {a.name}")
                    print(f"    Type: {a.abstraction_type.value}")
                    print(f"    Compression: {a.compression_ratio:.0%}")
                    print(f"    Generalization: {a.generalization_score:.0%}")
                    print(f"    From {len(a.source_repositories)} repos")

        elif args.compress_command == "transfer":
            params = json.loads(args.params) if args.params else {}
            abstractions = engine._abstractions
            target = abstractions.get(args.abstraction)
            if target:
                adapted = engine.transfer(target, params)
                print(f"Transferred abstraction: {args.abstraction}")
                print(adapted)
            else:
                print(f"Abstraction '{args.abstraction}' not found. Available: {list(abstractions.keys())[:5]}")

        elif args.compress_command == "hierarchy":
            abs_list = list(engine._abstractions.values())
            hierarchies = engine.build_hierarchy(abs_list)
            print(f"Abstraction Hierarchies: {len(hierarchies)}")
            for h in hierarchies:
                print(f"\n  Root: {h.root.name}")
                print(f"  Specializations: {h.specialization_depth}")
                print(f"  Coverage: {h.coverage:.0%}")
                for c in h.children[:3]:
                    print(f"    - {c.name} ({c.confidence:.0%})")

        elif args.compress_command == "stats":
            stats = engine.get_statistics()
            print(f"\nSemantic Compression Stats")
            for k, v in stats.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.0%}")
                else:
                    print(f"  {k}: {v}")

    def _do_similar(self, args):
        engine = RepositorySimilarityEngine()

        if args.similar_command == "add":
            deps = {}
            for d in args.deps:
                if "=" in d:
                    k, v = d.split("=", 1)
                    deps[k] = v
            profile = RepoProfile(
                repo_id=args.repo_id,
                repo_name=args.name,
                primary_language=args.language,
                module_names=[],
                file_paths=[],
                import_structure={},
                dependencies=deps,
                architecture_patterns=args.patterns,
                invariants=[],
                workflow_files=[],
                test_ratio=0.3,
            )
            engine.add_profile(profile)
            print(f"Added repo profile: {args.repo_id} ({args.name})")

        elif args.similar_command == "find":
            similar = engine.find_similar_repos(args.repo_id, top_n=args.top)
            print(f"\nRepos similar to {args.repo_id}:")
            for s in similar:
                print(f"  {s['repo_name']}: {s['similarity']:.0%}")

        elif args.similar_command == "cluster":
            clusters = engine.cluster_repos(n_clusters=args.n)
            print(f"\nRepo clusters ({len(clusters)}):")
            for c in clusters:
                print(f"\n  {c.label}")
                print(f"  Size: {c.size}")
                print(f"  Members: {', '.join(c.members[:5])}")
                if c.common_patterns:
                    print(f"  Common Patterns: {', '.join(c.common_patterns)}")
                print(f"  Avg Similarity: {c.avg_similarity:.0%}")

        elif args.similar_command == "visualize":
            viz = engine.cluster_visualization()
            html = viz.to_html()
            Path(args.output).write_text(html)
            print(f"Similarity visualization written to {args.output}")

        else:
            print(f"Unknown similar command. Use: add, find, cluster, visualize")

    def _do_observe_v2(self, args):
        obs = ObservatoryV2()

        if args.observe_v2_command == "health":
            health = obs.compute_integrated_health()
            print(f"\nObservatory v2 — Integrated Health")
            print(f"  Health Score: {health['health_score']:.0%}")
            print(f"  Trend: {health['trend']}")
            print(f"  Dimensions:")
            for dim, score in health.get('dimension_scores', {}).items():
                print(f"    {dim}: {score:.0%}")
            if health.get('signals'):
                print(f"  Signals: {', '.join(health['signals'])}")

            report = obs.storage_report()
            print(f"  Observations: {report['total_observations']}")

        elif args.observe_v2_command == "timeline":
            timeline = obs.build_timeline(dimension=args.dimension)
            print(f"Observation timeline ({len(timeline)} entries):")
            for t in timeline[-20:]:
                bar = "█" * int(t['value'] * 20) + "░" * (20 - int(t['value'] * 20))
                print(f"  [{t['index']}] [{bar}] {t['value']:.0%}")

        elif args.observe_v2_command == "pipeline":
            report = obs.data_pipeline_report()
            print(f"Data Pipeline Report:")
            print(f"  Total Sources: {report['total_sources']}")
            print(f"  Total Observations: {report['total_observations']}")
            print(f"  Features:")
            for k, v in report.get('config', {}).items():
                print(f"    {k}: {v}")

        elif args.observe_v2_command == "storage":
            report = obs.storage_report()
            print(f"Storage Report:")
            print(f"  Backend: {report['storage_backend']}")
            print(f"  Observations: {report['total_observations']}")
            print(f"  Retention: {report['retention_policy']}")

        elif args.observe_v2_command == "replay":
            observations = obs.replay_observations(args.start, args.end)
            for i, o in enumerate(observations[:10]):
                print(f"\n  Observation {args.start + i}:")
                print(f"    Time: {o.timestamp}")
                print(f"    Evolution stability: {o.repo_evolution.get('stability_score', 'N/A')}")
                print(f"    Architecture fitness: {o.architecture_fitness.get('overall_score', 'N/A')}")
                print(f"    Risk health: {o.risk_forecast.get('health_score', 'N/A')}")

        elif args.observe_v2_command == "record":
            import time
            observation = IntegratedObservation(
                timestamp=time.time(),
                repo_evolution={"stability_score": 0.8, "metrics": {}},
                runtime_trace=None,
                ecosystem_intelligence={"libraries_tracked": 0},
                architecture_fitness={"overall_score": 0.75, "maintainability": 0.7},
                invariant_systems={"invariants_tracked": 0},
                coordination_telemetry=None,
                skill_transfer=None,
                confidence_calibration={"average_confidence": 0.7, "calibration_error": 0.1},
                risk_forecast={"health_score": 0.8, "migration_risks": []},
            )
            obs.record_observation(observation)
            out = args.output or "observatory-v2-snapshot.json"
            obs.save(out)
            print(f"Observation recorded and saved to {out}")

    def _do_civ_map(self, args):
        mapper = SoftwareCivilizationMapper()

        if args.civ_map_command == "generate":
            cm = mapper.build_civilization_map()
            output = json.dumps(cm.to_dict(), indent=2)
            if args.output:
                Path(args.output).write_text(output)
                print(f"Civilization map written to {args.output}")
            else:
                print(output[:2000] + "\n...")

        elif args.civ_map_command == "view":
            cm = mapper.build_civilization_map()
            html = cm.to_html()
            Path(args.output).write_text(html)
            print(f"Civilization map written to {args.output}")

        elif args.civ_map_command == "save":
            mapper.save(args.output)
            print(f"Civilization map saved to {args.output}")

    def _do_epistemology(self, args):
        if args.epi_command == "assess":
            try:
                from lyme.epistemology.evidence_theory import EvidenceTheoryEngine, Evidence, EvidenceType, EvidenceSource
            except ImportError:
                print("Epistemology module not available.")
                return
            engine = EvidenceTheoryEngine()
            claim = engine.make_claim(args.claim or "Undefined claim", domain=args.domain)
            assessment = engine.assess_claim(claim.id)
            print(f"Claim: {claim.statement}")
            print(f"  Confidence: {assessment.overall_confidence:.0%}")
            print(f"  Strength: {claim.strength.value}")
            print(f"  Evidence: {assessment.evidence_count} sources")
            print(f"  Hallucination Risk: {claim.hallucination_risk.value}")
            print(f"  Contradictions: {assessment.contradiction_count}")
            print(f"  Recommendation: {assessment.recommendation}")

        elif args.epi_command == "calibrate":
            try:
                from lyme.epistemology.confidence_calibration import ConfidenceCalibrator
            except ImportError:
                print("Confidence calibration module not available.")
                return
            calibrator = ConfidenceCalibrator()
            for pred, actual in [(0.9, True), (0.8, True), (0.7, False), (0.95, False),
                                  (0.6, True), (0.5, True), (0.4, False), (0.3, True)]:
                calibrator.record(pred, actual, domain="code_analysis")
            report = calibrator.generate_report()
            print(report.to_markdown())

        elif args.epi_command == "debug":
            try:
                from lyme.epistemology.epistemic_debugging import EpistemicDebugger, FailureCategory, FailedInference
            except ImportError:
                print("Epistemic debugging module not available.")
                return
            debugger = EpistemicDebugger()
            debugger.record_failure(
                category=FailureCategory.OVERCONFIDENCE,
                false_claim="Claimed repo uses FastAPI without checking framework files",
                description="Agent asserted FastAPI usage based on directory name alone",
                what_was_believed="Repository uses FastAPI framework",
                what_was_true="Repository uses Flask",
                evidence_missing=["framework config files", "import statements", "dependency list"],
                inference_step_failed=FailedInference(
                    step="framework_detection",
                    expected="Check pyproject.toml for FastAPI dependency",
                    actual="Inferred from directory naming convention only",
                    reason="Used heuristic instead of static analysis",
                ),
                tool_that_should_have_been_used="Static analyzer for dependency detection",
                confidence_at_time=0.85,
                corrected_confidence=0.20,
            )
            report = debugger.generate_report()
            print(report.to_markdown())

        elif args.epi_command == "report":
            try:
                from lyme.epistemology.epistemic_debugging import EpistemicDebugger
            except ImportError:
                print("Epistemic debugging module not available.")
                return
            debugger = EpistemicDebugger()
            report = debugger.generate_report(include_history=True)
            print(report.to_markdown())

    def _do_policy(self, args):
        if args.policy_command == "check":
            try:
                from lyme.governance.autonomy_policy import AutonomyPolicyEngine, ActionType
            except ImportError:
                print("Policy module not available.")
                return
            engine = AutonomyPolicyEngine()
            context = json.loads(args.context) if args.context else {
                "autonomy_level": "suggest_only", "test_coverage": 0.3, "edit_size": 10,
                "confidence": 0.6, "sensitive_zone": False, "repo_risk": 0.2,
            }
            if args.action:
                action = ActionType(args.action)
                eval_result = engine.evaluate(action, context)
                print(f"Action: {action.value}")
                print(f"  Allowed: {eval_result.allowed}")
                print(f"  Reason: {eval_result.reason}")
                print(f"  Risk Score: {eval_result.risk_score:.2f}")
                print(f"  Requires Approval: {eval_result.requires_approval}")
                explanation = engine.explain(eval_result)
                print(f"\nExplanation:\n{explanation.to_markdown()}")

        elif args.policy_command == "sensitive":
            try:
                from lyme.governance.sensitive_code import SensitiveCodeDetector
            except ImportError:
                print("Sensitive code module not available.")
                return
            path = Path(args.path or ".")
            detector = SensitiveCodeDetector()
            result = detector.detect(path)
            print(result.to_markdown())

        elif args.policy_command == "review":
            try:
                from lyme.governance.review_board import ActionReviewBoard, ReviewRequest
            except ImportError:
                print("Review board module not available.")
                return
            data = json.loads(args.request) if args.request else {
                "title": "Demo change", "description": "Test review board",
                "action_type": "modify_files",
                "files_changed": ["src/module.py"],
                "diff_summary": "Minor refactoring",
                "risk_score": 0.5,
            }
            board = ActionReviewBoard()
            request = ReviewRequest(
                id="req_001", title=data["title"], description=data.get("description", ""),
                action_type=data.get("action_type", "modify_files"),
                files_changed=data.get("files_changed", []),
                diff_summary=data.get("diff_summary", ""),
                risk_score=data.get("risk_score", 0.5),
                proposer_notes=data.get("proposer_notes", ""),
            )
            decision = board.submit_request(request)
            print(decision.to_markdown())

        elif args.policy_command == "audit":
            try:
                from lyme.governance.autonomy_policy import AutonomyPolicyEngine, ActionType
            except ImportError:
                print("Policy module not available.")
                return
            engine = AutonomyPolicyEngine()
            context = {"autonomy_level": "verified_auto", "test_coverage": 0.5, "edit_size": 20}
            evaluations = []
            for action in [ActionType.READ_ONLY, ActionType.MODIFY_FILES, ActionType.DELETE_FILES,
                           ActionType.OPEN_PR, ActionType.DEPLOY]:
                ev = engine.evaluate(action, context)
                evaluations.append(ev)
            print(engine.audit_trail(evaluations))

    def _do_verify(self, args):
        if args.verify_command == "graph":
            from lyme.verification.graph import (
                VerificationGraph, Claim, CodeChange, TestResult, RuntimeTrace,
                StaticAnalysisResult, TypeCheckResult, UserApproval,
                BenchmarkResult, RollbackEvidence,
            )
            graph = VerificationGraph()
            import json, time

            context = json.loads(args.context) if args.context else {}

            claims_data = context.get("claims", [
                {"id": "c1", "statement": "Change does not break existing tests",
                 "source": "developer", "confidence": 0.8},
            ])
            claims = [Claim(id=c["id"], statement=c["statement"], source=c.get("source", ""),
                            confidence=c.get("confidence", 0.5)) for c in claims_data]

            changes_data = context.get("changes", [
                {"id": "ch1", "file_path": "src/module.py", "diff": "--- a/src/module.py\n+++ b/src/module.py\n@@ -1,3 +1,4 @@\n",
                 "risk_score": 0.3},
            ])
            changes = [CodeChange(id=c["id"], file_path=c["file_path"], diff=c.get("diff", ""),
                                  risk_score=c.get("risk_score", 0.3)) for c in changes_data]

            tests_data = context.get("tests", [])
            tests = [TestResult(id=t.get("id", f"t{i}"), test_name=t["name"], passed=t["passed"],
                                duration_ms=t.get("duration_ms", 0), coverage_pct=t.get("coverage", 0))
                     for i, t in enumerate(tests_data)]

            traces_data = context.get("traces", [])
            traces = [RuntimeTrace(id=t.get("id", f"r{i}"), operation=t["operation"],
                                   success=t["success"]) for i, t in enumerate(traces_data)]

            static_data = context.get("static_analysis", [])
            static_results = [StaticAnalysisResult(id=s.get("id", f"s{i}"), tool=s["tool"],
                                                   passed=s["passed"], issues_count=s.get("issues", 0),
                                                   warnings_count=s.get("warnings", 0),
                                                   errors_count=s.get("errors", 0))
                              for i, s in enumerate(static_data)]

            type_data = context.get("type_checks", [])
            type_results = [TypeCheckResult(id=tc.get("id", f"tc{i}"), tool=tc["tool"],
                                            passed=tc["passed"], errors_count=tc.get("errors", 0))
                            for i, tc in enumerate(type_data)]

            approvals_data = context.get("approvals", [])
            approvals = [UserApproval(id=a.get("id", f"a{i}"), approver=a["approver"],
                                      approved=a["approved"], reason=a.get("reason", ""))
                         for i, a in enumerate(approvals_data)]

            bench_data = context.get("benchmarks", [])
            benchmarks = [BenchmarkResult(id=b.get("id", f"b{i}"), benchmark_name=b["name"],
                                          score=b["score"], baseline_score=b.get("baseline", 0),
                                          regression=b.get("regression", False))
                          for i, b in enumerate(bench_data)]

            rollback_data = context.get("rollback_evidence", [])
            rollbacks = [RollbackEvidence(id=rb.get("id", f"rb{i}"),
                                          rollback_reason=rb["reason"], success=rb["success"])
                         for i, rb in enumerate(rollback_data)]

            report = graph.build_action_verification(
                action_id=args.action_id,
                action_description=args.description,
                claims=claims, changes=changes, test_results=tests, traces=traces,
                static_results=static_results, type_results=type_results,
                approvals=approvals, benchmark_results=benchmarks,
                rollback_evidence=rollbacks,
            )

            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report.to_dict(), f, indent=2)
                print(f"Verification report written to {args.output}")
            else:
                print(graph.render_cli(report))

        elif args.verify_command == "plan":
            from lyme.verification.planner import VerificationStrategyPlanner
            planner = VerificationStrategyPlanner()
            context = {
                "risk_score": args.risk,
                "scope": args.scope,
                "is_sensitive": args.sensitive,
                "language": args.lang,
            }
            result = planner.plan(args.edit, context)

            if args.output:
                import json
                with open(args.output, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)
                print(f"Plan written to {args.output}")
            else:
                print(result.render_cli())

        elif args.verify_command == "gaps":
            from lyme.verification.gap_detector import VerificationGapDetector
            import json
            detector = VerificationGapDetector()
            context = json.loads(args.context) if args.context else {
                "source_files": ["src/module.py"],
                "test_files": [],
                "changed_files": ["src/module.py"],
                "test_coverage_pct": 45,
                "has_type_check": False,
                "has_static_analysis": False,
                "has_runtime_verification": False,
                "has_rollback_path": False,
                "has_benchmark_baseline": False,
                "confidence": 0.95,
                "claims": [{"statement": "This change is safe", "verified": False}],
                "assumptions": [{"statement": "No side effects on other modules"}],
                "build_available": True,
                "is_sensitive": False,
            }
            result = detector.detect(context)

            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)
                print(f"Gaps written to {args.output}")
            elif args.format == "json":
                print(json.dumps(result.to_dict(), indent=2))
            elif args.format == "markdown":
                print(result.to_markdown())
            else:
                print(result.render_cli())

    def _do_govern(self, args):
        from lyme.governance.change_governance import ChangeGovernanceEngine
        engine = ChangeGovernanceEngine()
        import json

        if args.govern_command == "evaluate":
            if args.context:
                context = json.loads(args.context)
            else:
                context = {
                    "risk_score": args.risk,
                    "scope": args.scope,
                    "sensitivity": args.sensitivity,
                    "description": args.description,
                    "files_changed": [],
                    "verification_coverage": 0.5,
                    "user_intent": "modify",
                    "deployment_impact": "none",
                    "architectural_impact": "none",
                    "reversibility": "easy",
                }
            result = engine.evaluate(context)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)
                print(f"Governance result written to {args.output}")
            else:
                print(result.render_cli())

        elif args.govern_command == "policies":
            lines = []
            lines.append("=" * 70)
            lines.append("  GOVERNANCE POLICIES")
            lines.append("=" * 70)
            for p in engine.policies:
                lines.append(f"  [{p.priority}] {p.name}")
                lines.append(f"       {p.description}")
                lines.append(f"       Decision: {p.decision.value}")
                lines.append(f"       Conditions: {json.dumps(p.conditions)}")
                lines.append("")
            print("\n".join(lines))

        elif args.govern_command == "override":
            print(f"Override not supported in CLI mode. Reason: {args.reason}")

    def _do_constitution(self, args):
        from lyme.governance.repo_constitution import (
            RepoConstitution, ConstitutionValidator, ConstitutionEditor,
            AllowedAction,
        )
        import json
        from pathlib import Path

        if args.constitution_command == "init":
            constit = RepoConstitution.create_default(repo_name=args.name or Path(args.repo).name)
            output_path = Path(args.output) if args.output else Path(args.repo) / ".lyme" / "constitution.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            constit.save(output_path)
            print(f"Constitution written to {output_path}")
            print(constit.to_markdown())

        elif args.constitution_command == "view":
            path = Path(args.path)
            if not path.exists():
                print(f"Constitution not found at {path}")
                return
            constit = RepoConstitution.load(path)
            print(constit.to_markdown())

        elif args.constitution_command == "validate":
            path = Path(args.path)
            if not path.exists():
                print(f"Constitution not found at {path}")
                return
            constit = RepoConstitution.load(path)
            validator = ConstitutionValidator(constit)
            issues = validator.validate()
            if issues:
                print("Constitution validation issues:")
                for issue in issues:
                    print(f"  ⚠ {issue}")
            else:
                print("✅ Constitution is valid")

        elif args.constitution_command == "check":
            path = Path(args.constitution)
            if not path.exists():
                print(f"No constitution at {path}. Run 'lyme constitution init' first.")
                return
            constit = RepoConstitution.load(path)
            validator = ConstitutionValidator(constit)
            action = AllowedAction(args.action)
            allowed, reason = validator.validate_action(args.file, action)
            approval = validator.check_approval_needed(args.file)
            print(f"File:    {args.file}")
            print(f"Action:  {args.action}")
            print(f"Allowed: {'✅ YES' if allowed else '🚫 NO'}")
            print(f"Reason:  {reason}")
            if approval:
                print(f"Approval: {approval.value}")

    def _do_ledger(self, args):
        from lyme.governance.change_ledger import (
            AutonomousChangeLedger, LedgerEntryType, EntryOutcome,
        )
        from pathlib import Path

        ledger_path = Path(".lyme/ledger.json")
        ledger = AutonomousChangeLedger(storage_path=ledger_path)

        if args.ledger_command == "record":
            entry_type = LedgerEntryType(args.type) if hasattr(LedgerEntryType, args.type.replace("-", "_")) else LedgerEntryType.CODE_CHANGE
            outcome = EntryOutcome(args.outcome) if hasattr(EntryOutcome, args.outcome.replace("-", "_")) else EntryOutcome.SUCCESS
            eid = ledger.record_change(
                description=args.description,
                agent=args.agent,
                intent=args.intent,
                risk_score=args.risk,
                verification_result="recorded",
                outcome=outcome,
            )
            print(f"Recorded entry: {eid}")

        elif args.ledger_command == "view":
            entry_type = None
            if args.type:
                entry_type = LedgerEntryType(args.type)
            entries = ledger.get_entries(entry_type=entry_type, limit=args.limit)
            if not entries:
                print("No ledger entries found.")
                return
            for e in entries:
                print(e.to_markdown())
                print("---")

        elif args.ledger_command == "summary":
            summary = ledger.get_summary()
            print(summary.to_markdown())

        elif args.ledger_command == "path":
            path = ledger.get_rollback_path(args.entry_id)
            if path:
                print(f"Rollback path for {args.entry_id}: {path}")
            else:
                print(f"No rollback path found for {args.entry_id}")

    def _do_eval(self, args):
        import json

        if args.eval_command == "benchmark":
            from lyme.evaluation.self_benchmark import SelfBenchmark
            bench = SelfBenchmark()
            run = bench.run(repo_type=args.type, repo_name=args.name or args.type)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(run.to_dict(), f, indent=2)
                print(f"Benchmark run written to {args.output}")
            else:
                print(run.to_markdown())

        elif args.eval_command == "longitudinal":
            from lyme.evaluation.longitudinal import LongitudinalEvaluation
            eval_inst = LongitudinalEvaluation()
            report = eval_inst.get_report()
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report.to_dict(), f, indent=2)
                print(f"Longitudinal report written to {args.output}")
            else:
                print(report.to_markdown())

        elif args.eval_command == "cognition":
            from lyme.evaluation.cognition_regression import (
                CognitionRegressionDetector, CognitionDimension,
            )
            import time
            detector = CognitionRegressionDetector()
            detector.set_all_baselines({d: args.baseline for d in CognitionDimension})
            scores = {}
            for dim in CognitionDimension:
                scores[dim] = args.baseline + (0.1 if dim.value == "verification" else -0.05)
            result = detector.evaluate(scores)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)
                print(f"Cognition report written to {args.output}")
            else:
                print(result.render_cli())

    def _do_demo_v05(self, args):
        repo_path = Path(args.repo).resolve()
        from lyme.evolution.demo_v05 import V05Demo
        demo = V05Demo(repo_path)
        result = demo.run(full=args.full)
        print(result["summary"])

    def _do_demo_v06(self, args):
        from lyme.demo_v06 import V06Demo
        demo = V06Demo()
        result = demo.run(full=args.full)
        print(result["summary"])

    def _do_detect(self, args):
        repo_path = Path(args.repo).resolve()
        from lyme.evolution.maintenance_detector import MaintenanceDetector
        detector = MaintenanceDetector(repo_path)
        opportunities = detector.detect_all()
        opportunities.sort(key=lambda o: o.score(), reverse=True)
        top = opportunities[:args.top]
        if args.output:
            import json
            with open(args.output, "w") as f:
                json.dump([o.to_dict() for o in top], f, indent=2, default=str)
            print(f"Opportunities written to {args.output}")
        else:
            print(f"\n=== Maintenance Opportunities: {len(opportunities)} found ===")
            for o in top:
                score = o.score()
                print(f"  [{score:.3f}] [{o.category.value}] {o.title[:70]}")
                print(f"         value={o.value:.2f} risk={o.risk:.2f} effort={o.effort:.2f} conf={o.confidence:.0%}")
                print(f"         {o.evidence[:80]}")

    def _do_maintain(self, args):
        repo_path = Path(args.repo).resolve()
        from lyme.evolution.maintenance_loops import AutonomousMaintenanceLoop
        loop = AutonomousMaintenanceLoop(repo_path)
        if args.stats:
            stats = loop.get_statistics()
            for k, v in stats.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v}")
        else:
            completed = loop.run_loop(max_tasks=args.tasks)
            print(f"\n=== Maintenance Loop Complete ===")
            print(f"Tasks attempted: {len(completed)}")
            for t in completed:
                print(f"  [{t.outcome.value if t.outcome else 'pending'}] {t.opportunity.title[:70]}")
                if t.patch_diff:
                    print(f"       diff: {len(t.patch_diff)} chars")
                print(f"       verification: {'passed' if t.verification_result.get('passed') else 'failed' if t.verification_result else 'none'}")

    def _do_roadmap(self, args):
        repo_path = Path(args.repo).resolve()
        from lyme.evolution.roadmap_generator import RoadmapGenerator
        generator = RoadmapGenerator(repo_path)
        roadmap = generator.generate_roadmap()
        if args.output:
            import json
            with open(args.output, "w") as f:
                json.dump(roadmap.to_dict(), f, indent=2, default=str)
            print(f"Roadmap written to {args.output}")
        else:
            print(roadmap.summary)
            print(f"\nFull roadmap with {sum(len(v) for v in roadmap.recommendations.values())} recommendations generated.")

    def _do_decisions(self, args):
        repo_path = Path.cwd()
        from lyme.evolution.decision_memory import EngineeringDecisionMemory
        memory = EngineeringDecisionMemory(repo_path)
        if args.decisions_command == "record":
            adr = memory.record_decision(
                title=args.title,
                context=args.context,
                decision=args.decision,
                rationale=args.rationale,
                constraints=args.constraints,
                alternatives=args.alternatives,
            )
            print(f"\n=== ADR Recorded ===")
            print(adr.to_markdown()[:500])
        elif args.decisions_command == "report":
            print(memory.produce_report())

    def _do_tradeoff(self, args):
        repo_path = Path(args.repo).resolve()
        from lyme.evolution.tradeoff_simulator import TradeoffSimulator, TradeoffDomain
        simulator = TradeoffSimulator(repo_path)
        if args.domain == "all":
            results = simulator.batch_analyze()
            print(f"\n=== Tradeoff Analysis: {len(results)} domains ===\n")
            for r in results:
                print(f"  {r.question}")
                print(f"    → {r.recommended}")
                print()
        else:
            domain = TradeoffDomain(args.domain)
            analysis = simulator.compare(domain, f"Tradeoff analysis for {args.domain}")
            if args.output:
                import json
                with open(args.output, "w") as f:
                    json.dump(analysis.to_dict(), f, indent=2, default=str)
                print(f"Analysis written to {args.output}")
            else:
                print(f"\n=== Tradeoff Analysis: {analysis.question} ===")
                print(f"Recommended: {analysis.recommended}")
                print(analysis.explanation)

    # ── v0.7 Handlers ──

    def _do_trace_std(self, args):
        cmd = args.trace_std_command
        if cmd == "export":
            from lyme.standards.trace.converter import LymeTraceConverter
            converter = LymeTraceConverter()
            if args.input:
                import json
                with open(args.input) as f:
                    data = json.load(f)
                if "steps" in data or "decisions" in data:
                    oat = converter.convert_cognitive_trace(data)
                elif "spans" in data or "span_id" in data:
                    oat = converter.convert_spans(data.get("spans", data if isinstance(data, list) else []))
                else:
                    oat = converter.build_from_run()
            else:
                oat = converter.build_from_run()
            with open(args.output, "w") as f:
                f.write(oat.to_json())
            print(f"Trace exported to {args.output}")
            print(f"  Events: {oat.summary.get('event_count', 0)}")
            print(f"  Schema: {oat.summary.get('schema', 'N/A')}")
        elif cmd == "validate":
            from lyme.standards.trace.validator import OpenTraceValidator
            from lyme.standards.trace.schema import OpenAgentTrace
            import json
            with open(args.file) as f:
                trace = OpenAgentTrace.from_dict(json.load(f))
            validator = OpenTraceValidator()
            result = validator.validate(trace)
            print(result.summary())
        elif cmd == "compare":
            from lyme.standards.trace.comparison import TraceComparer
            import json
            from lyme.standards.trace.schema import OpenAgentTrace
            with open(args.trace_a) as f:
                ta = OpenAgentTrace.from_dict(json.load(f))
            with open(args.trace_b) as f:
                tb = OpenAgentTrace.from_dict(json.load(f))
            comparer = TraceComparer()
            report = comparer.compare(ta, tb)
            print(report.summary)
        elif cmd == "examples":
            from lyme.standards.trace.examples import generate_all_examples
            generate_all_examples(args.output)
        else:
            print("trace-std commands: export, validate, compare, examples")

    def _do_semantic_diff(self, args):
        cmd = args.semantic_diff_command
        if cmd == "render":
            from lyme.standards.semantic_diff import SemanticDiff
            from lyme.standards.semantic_diff.renderer import SemanticDiffRenderer
            import json
            if args.input:
                with open(args.input) as f:
                    sd = SemanticDiff.from_dict(json.load(f))
            else:
                from lyme.standards.semantic_diff.examples import generate_bug_fix_diff
                sd = generate_bug_fix_diff()
            renderer = SemanticDiffRenderer(args.format)
            rendered = renderer.render(sd)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(rendered)
                print(f"Rendered to {args.output}")
            else:
                print(rendered)
        elif cmd == "examples":
            from lyme.standards.semantic_diff.examples import generate_all_examples
            generate_all_examples(args.output)
        else:
            print("semantic-diff commands: render, examples")

    def _do_pr(self, args):
        if args.pr_command == "analyze":
            from lyme.pr_intelligence.report import PRReportGenerator
            gen = PRReportGenerator()
            report = gen.analyze_pr(args.repo, args.pr_number)
            if report:
                md = gen.generate_markdown(report)
                if args.output:
                    with open(args.output, "w") as f:
                        f.write(md)
                    print(f"PR report written to {args.output}")
                else:
                    print(md)
            else:
                print(f"Could not analyze PR {args.repo}#{args.pr_number}")

    def _do_ci(self, args):
        from lyme.ci_integration import CIRunner, CIConfig, CIMode
        mode_map = {"advisory": CIMode.ADVISORY, "blocking": CIMode.BLOCKING, "research": CIMode.RESEARCH_TELEMETRY}
        config = CIConfig(mode=mode_map.get(args.mode, CIMode.ADVISORY), output_dir=args.output)
        runner = CIRunner(config)
        audit = runner.run(args.repo, args.commit, args.branch)
        print(audit.summary)

    def _do_bridge(self, args):
        from lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        type_map = {
            "evidence": InsightType.EVIDENCE_ANSWER,
            "diff-preview": InsightType.SEMANTIC_DIFF_PREVIEW,
            "arch-warning": InsightType.ARCHITECTURE_WARNING,
            "verify-gap": InsightType.VERIFICATION_GAP,
            "confidence": InsightType.CONFIDENCE_INDICATOR,
            "edit-suggestion": InsightType.SAFE_EDIT_SUGGESTION,
        }
        bridge = IDEBridge()
        bridge.connect()
        q = IDEQuery(
            query_type=type_map.get(args.type, InsightType.EVIDENCE_ANSWER),
            query=args.query or f"Query about {args.file or 'codebase'}",
            file_path=args.file,
        )
        resp = bridge.query(q)
        print(f"Insight: {resp.insight_type}")
        print(f"Content: {resp.content[:200]}")
        print(f"Confidence: {resp.confidence:.0%}")

    def _do_corpus(self, args):
        from lyme.research_corpus import ResearchCorpus, CorpusEntry, CorpusConfig
        config = CorpusConfig(output_dir=args.output)
        corpus = ResearchCorpus(config)
        if args.corpus_command == "add":
            entry = CorpusEntry(
                title=args.title or f"Corpus entry {int(__import__('time').time())}",
                entry_type=args.type,
            )
            if args.trace:
                import json
                with open(args.trace) as f:
                    entry.data = json.load(f)
            entry.source_hash = entry.compute_hash()
            eid = corpus.add_entry(entry)
            print(f"Entry added: {eid}")
        elif args.corpus_command == "export":
            output = args.output or f"{args.output}/corpus-export.json"
            with open(output, "w") as f:
                f.write(corpus.export_all(args.format))
            print(f"Corpus exported to {output}")

    def _do_portal(self, args):
        from lyme.research_portal import ResearchPortal, PortalConfig
        from lyme.research_portal import BenchmarkLeaderboard, LeaderboardEntry
        config = PortalConfig(output_dir=args.output)
        portal = ResearchPortal(config)
        portal.leaderboard.add_entry(LeaderboardEntry(
            agent_name="local-agent", model="unknown",
            overall_score=0.0, tasks_completed=0, total_tasks=16,
        ))
        portal.save_portal()
        print(f"Research portal generated at {args.output}/index.html")

    def _do_contrib(self, args):
        from lyme.contribution_protocol import ContributionProtocol, Contribution, ContributionType
        protocol = ContributionProtocol()
        if args.contrib_command == "new":
            ct = args.type
            c = Contribution(
                contribution_type=ct,
                title=args.title,
                author="local",
            )
            cid = protocol.submit(c)
            print(f"Contribution created: {cid}")
            print(f"Status: {c.status}")
            checklist = protocol.generate_checklist(ct)
            print("Checklist:")
            for item in checklist:
                print(f"  ☐ {item}")
        elif args.contrib_command == "guide":
            guide = protocol.get_guide(args.type)
            if guide:
                print(f"Guide for {args.type}:")
                for item in guide.review_criteria:
                    print(f"  ☐ {item}")
            else:
                print(f"No guide for {args.type}")

    def _do_demo_v03(self, args):
        from lyme.demo_v03 import run_demo
        run_demo(full=args.full)

    def _print_run_summary(self, runs):
        if not runs:
            print("No runs completed.")
            return

        print(f"\n{'Run ID':15s} {'Agent':20s} {'Scenario':35s} {'Status':10s} {'Duration':10s}")
        print("-" * 90)
        for run in runs:
            status = "✓" if run.status == "success" else "✗" if run.status == "failure" else "!"
            duration = f"{(run.end_time or run.start_time) - run.start_time:.1f}s" if run.end_time else "?"
            print(f"{run.run_id:15s} {run.agent_name:20s} {run.scenario_name:35s} {status:10s} {duration:10s}")


def main():
    cli = LymeCLI()
    cli.run()


if __name__ == "__main__":
    main()
