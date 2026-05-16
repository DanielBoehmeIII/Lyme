# Lyme Model — Local Coding Agent Error Taxonomy
# 12 failure types for small local models
# Measured by Lyme Audit

from .taxonomy import (
    LocalCodingFailureCategory,
    LOCAL_CODING_TAXONOMY,
    LocalCodingFailureRecord,
    LocalCodingFailureAnalysis,
)
from .detector import (
    LocalCodingFailureDetector,
    DetectorRule,
    DETECTOR_RULES,
)
from .metrics import FailureMetrics, compute_failure_metrics
from .report import generate_cli_report

__all__ = [
    "LocalCodingFailureCategory",
    "LOCAL_CODING_TAXONOMY",
    "LocalCodingFailureRecord",
    "LocalCodingFailureAnalysis",
    "LocalCodingFailureDetector",
    "DetectorRule",
    "DETECTOR_RULES",
    "FailureMetrics",
    "compute_failure_metrics",
    "generate_cli_report",
]
