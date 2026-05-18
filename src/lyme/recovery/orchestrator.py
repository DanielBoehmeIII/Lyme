"""RecoveryOrchestrator — unified failure detection + repair + rollback."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .detector import FailureDetector, DetectionResult, FailureType
from .confidence import ConfidenceScorer, EditConfidence, ConfidenceLevel
from .snapshot import SnapshotManager


class RecoveryAction(Enum):
    RETRY = "retry"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"
    IGNORE = "ignore"
    REGENERATE = "regenerate"


@dataclass
class RecoveryConfig:
    max_retries: int = 3
    auto_rollback: bool = True
    min_confidence: float = 0.3
    snapshot_before_edit: bool = True
    escalate_on_pattern: List[str] = field(default_factory=lambda: ["repeated_crash", "infinite_loop"])


@dataclass
class RecoveryResult:
    success: bool = False
    actions_taken: List[RecoveryAction] = field(default_factory=list)
    rollback_performed: bool = False
    retries_used: int = 0
    final_confidence: float = 0.0
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "actions": [a.value for a in self.actions_taken],
            "rollback": self.rollback_performed,
            "retries": self.retries_used,
            "confidence": round(self.final_confidence, 4),
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }


class RecoveryOrchestrator:
    def __init__(self, config: RecoveryConfig = None):
        self.config = config or RecoveryConfig()
        self.detector = FailureDetector()
        self.snapshot_mgr = SnapshotManager()
        self.confidence = ConfidenceScorer()
        self._repair_fn: Optional[Callable] = None

    def set_repair_fn(self, fn: Callable) -> None:
        self._repair_fn = fn

    def execute(self, task: str, context: Dict[str, Any]) -> RecoveryResult:
        start = time.time()
        result = RecoveryResult()

        for attempt in range(self.config.max_retries + 1):
            # Check for errors
            detection = self.detector.detect(context)

            if not detection.has_failures:
                result.success = True
                result.final_confidence = self.confidence.score_edit(context).overall
                break

            # Handle detected failures
            for failure in detection.failures:
                if failure.failure_type in (FailureType.SYNTAX_ERROR, FailureType.IMPORT_ERROR):
                    result.actions_taken.append(RecoveryAction.RETRY)
                    if self._repair_fn:
                        try:
                            self._repair_fn(task, context, failure)
                        except Exception:
                            pass

                elif failure.failure_type in (FailureType.TEST_FAILURE, FailureType.HALLUCINATION):
                    if self.config.auto_rollback:
                        self.snapshot_mgr.restore()
                        result.rollback_performed = True
                        result.actions_taken.append(RecoveryAction.ROLLBACK)
                    result.actions_taken.append(RecoveryAction.RETRY)
                    if self._repair_fn:
                        try:
                            self._repair_fn(task, context, failure)
                        except Exception:
                            pass

                elif failure.failure_type == FailureType.DEAD_EDIT:
                    self.snapshot_mgr.restore()
                    result.rollback_performed = True
                    result.actions_taken.append(RecoveryAction.ROLLBACK)
                    result.actions_taken.append(RecoveryAction.REGENERATE)
                    context["regenerate"] = True

                elif failure.failure_type == FailureType.TIMEOUT:
                    result.actions_taken.append(RecoveryAction.RETRY)
                    context["timeout_multiplier"] = context.get("timeout_multiplier", 1) * 2

            result.retries_used = attempt + 1

        result.duration_ms = (time.time() - start) * 1000
        result.final_confidence = self.confidence.score_edit(context).overall

        return result
