from .specification import (
    CognitionBenchmarkSpec,
    BenchmarkTask,
    ScoringMethod,
    TelemetryRequirements,
    AntiGamingRules,
    BaselineSystem,
    FailureInterpretation,
    BenchmarkDimension,
    TaskFormat,
    ScoreMetric,
    TaskCategory,
)
from .registry import BenchmarkRegistry

SCHEMA_VERSION = "0.7.0"
SCHEMA_NAME = "software-cognition-benchmark-spec"
SCHEMA_URN = "urn:lyme:standard:cognition-benchmark:v1"

__all__ = [
    "CognitionBenchmarkSpec", "BenchmarkTask",
    "ScoringMethod", "TelemetryRequirements",
    "AntiGamingRules", "BaselineSystem", "FailureInterpretation",
    "BenchmarkDimension", "TaskFormat", "ScoreMetric", "TaskCategory",
    "BenchmarkRegistry",
    "SCHEMA_VERSION", "SCHEMA_NAME", "SCHEMA_URN",
]
