from .dual_architecture import (
    ArchitectureRegistry,
    ArchitectureConfig,
    ProductModule,
    ResearchModule,
    SharedSubstrate,
    ProductDomain,
    ResearchDomain,
    LayerType,
    get_architecture,
)
from .telemetry_substrate import (
    TelemetrySubstrate,
    TelemetrySink,
    TelemetrySource,
    TelemetryConsent,
    TelemetryRecord,
    DataCategory,
)
from .experiment_api import (
    ExperimentAPI,
    ExperimentDefinition,
    ExperimentResult,
    ExperimentHook,
    ExperimentContext,
    ExperimentHookType,
    ExperimentStatus,
)
from .plugin_system import (
    PluginRegistry,
    PluginSpec,
    PluginHook,
    PluginContext,
    PluginManifest,
)
from .privacy_boundary import (
    PrivacyBoundary,
    DataClassification,
    SanitizationRule,
    PrivacyPolicy,
    BoundaryViolationError,
)
from .storage_strategy import (
    StorageStrategy,
    StorageBackend,
    StorageManifest,
    SchemaVersion,
)
from .boundary import (
    BoundaryRegistry,
    FeatureBoundary,
    get_boundary,
)
from .schema import (
    LymeProject,
    LymeSchemaMeta,
    ProjectSchema,
    RepoGraph,
    AgentTrace,
    SemanticDiff,
    MemoryEntry,
    BenchmarkResult,
    InvariantHypothesis,
    CausalRelationship,
    TemporalSnapshot,
    UserIntervention,
    WorkflowEntry,
    ModelRun,
    ActionType,
    ActionOutcome,
    SCHEMA_VERSION,
)
from .discovery import (
    ArchitecturePatternDiscovery, ArchitecturePattern, ArchitectureFingerprint,
    ArchitecturePatternType, PatternMaturity,
)
from .fitness import (
    ArchitectureFitnessEngine, ArchitectureFitnessReport, FitnessScore,
    FitnessDimension,
)
from .advisor import (
    ArchitectureAdvisor, ArchitectureSuggestion, ArchitectureConstraint,
    ArchitectureType,
)

__all__ = [
    "ArchitectureRegistry", "ArchitectureConfig",
    "ProductModule", "ResearchModule",
    "SharedSubstrate", "ProductDomain", "ResearchDomain", "LayerType",
    "get_architecture",
    "TelemetrySubstrate", "TelemetrySink", "TelemetrySource",
    "TelemetryConsent", "TelemetryRecord", "DataCategory",
    "ExperimentAPI", "ExperimentDefinition", "ExperimentResult",
    "ExperimentHook", "ExperimentContext", "ExperimentHookType", "ExperimentStatus",
    "PluginRegistry", "PluginSpec", "PluginHook",
    "PluginContext", "PluginManifest",
    "PrivacyBoundary", "DataClassification", "SanitizationRule",
    "PrivacyPolicy", "BoundaryViolationError",
    "StorageStrategy", "StorageBackend", "StorageManifest", "SchemaVersion",
    "BoundaryRegistry", "FeatureBoundary", "get_boundary",
    "LymeProject", "LymeSchemaMeta", "ProjectSchema",
    "RepoGraph", "AgentTrace", "SemanticDiff", "MemoryEntry",
    "BenchmarkResult", "InvariantHypothesis", "CausalRelationship",
    "TemporalSnapshot", "UserIntervention", "WorkflowEntry", "ModelRun",
    "ActionType", "ActionOutcome", "SCHEMA_VERSION",
    "ArchitecturePatternDiscovery", "ArchitecturePattern", "ArchitectureFingerprint",
    "ArchitecturePatternType", "PatternMaturity",
    "ArchitectureFitnessEngine", "ArchitectureFitnessReport", "FitnessScore",
    "FitnessDimension",
    "ArchitectureAdvisor", "ArchitectureSuggestion", "ArchitectureConstraint",
    "ArchitectureType",
]
