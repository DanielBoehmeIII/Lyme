"""Recovery — failure detection, repair loops, rollback, and confidence scoring."""
from .orchestrator import RecoveryOrchestrator, RecoveryConfig, RecoveryResult, RecoveryAction
from .detector import FailureDetector as FailureDetect, DetectionResult, FailureType
from .confidence import ConfidenceScorer, EditConfidence, ConfidenceLevel
from .snapshot import SnapshotManager, FileSnapshot

__all__ = [
    "RecoveryOrchestrator", "RecoveryConfig", "RecoveryResult", "RecoveryAction",
    "FailureDetect", "DetectionResult", "FailureType",
    "ConfidenceScorer", "EditConfidence", "ConfidenceLevel",
    "SnapshotManager", "FileSnapshot",
]
