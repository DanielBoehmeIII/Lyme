from .intelligence_dimensions import (
    IntelligenceDimension, DimensionDefinition, DimensionProxies,
    SoftwareIntelligenceFramework, ExperimentDesign,
)
from .benchmarks import (
    ResearchBenchmark, BenchmarkGenerator, ScoringSystem,
    LongitudinalEvaluation, AntiGamingProtection,
)
from .scaling_laws import (
    ScalingLawExperiment, ExperimentMatrix, VariableDefinition, VariableType,
    ExperimentControls, AutomatedExperimenter, ScalingLawFindings,
)
from .experiment_generator import (
    ExperimentGenerator, ExperimentPlan, Hypothesis, Variable,
    BenchmarkTask, FailureMode, EvaluationCriterion,
)
from .ablation import (
    AutomatedAblation, AblationRunner, AblationReport, AblationResult,
    AblationComponent, MetricResult,
)
from .report_generator import (
    ResearchReportGenerator, ResearchReport, Finding, StatisticalResult,
    ResultStrength,
)

__all__ = [
    "IntelligenceDimension", "DimensionDefinition", "DimensionProxies",
    "SoftwareIntelligenceFramework", "ExperimentDesign",
    "ResearchBenchmark", "BenchmarkGenerator", "ScoringSystem",
    "LongitudinalEvaluation", "AntiGamingProtection",
    "ScalingLawExperiment", "ExperimentMatrix", "VariableDefinition", "VariableType",
    "ExperimentControls", "AutomatedExperimenter", "ScalingLawFindings",
    "ExperimentGenerator", "ExperimentPlan", "Hypothesis", "Variable",
    "BenchmarkTask", "FailureMode", "EvaluationCriterion",
    "AutomatedAblation", "AblationRunner", "AblationReport", "AblationResult",
    "AblationComponent", "MetricResult",
    "ResearchReportGenerator", "ResearchReport", "Finding", "StatisticalResult",
    "ResultStrength",
]
