"""FailureDetector — detects failure types from execution context."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureType(Enum):
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    TEST_FAILURE = "test_failure"
    HALLUCINATION = "hallucination"
    DEAD_EDIT = "dead_edit"
    TIMEOUT = "timeout"
    LOW_CONFIDENCE = "low_confidence"
    UNKNOWN = "unknown"


@dataclass
class Failure:
    failure_type: FailureType
    description: str = ""
    severity: str = "medium"
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.failure_type.value,
            "description": self.description[:200],
            "severity": self.severity,
        }


@dataclass
class DetectionResult:
    failures: List[Failure] = field(default_factory=list)
    has_failures: bool = False

    def add(self, failure: Failure) -> None:
        self.failures.append(failure)
        self.has_failures = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_count": len(self.failures),
            "failures": [f.to_dict() for f in self.failures],
        }


class FailureDetector:
    def detect(self, context: Dict[str, Any]) -> DetectionResult:
        result = DetectionResult()

        # Syntax error detection
        error_text = context.get("error", "") or context.get("stderr", "") or ""
        if any(kw in error_text for kw in ("SyntaxError", "syntax error", "invalid syntax")):
            result.add(Failure(
                failure_type=FailureType.SYNTAX_ERROR,
                description="Syntax error detected in generated code",
                severity="high",
                context={"error_snippet": error_text[:200]},
            ))

        # Import error detection
        if any(kw in error_text for kw in ("ImportError", "ModuleNotFoundError", "No module named")):
            result.add(Failure(
                failure_type=FailureType.IMPORT_ERROR,
                description="Import error — missing module or circular dependency",
                severity="high",
            ))

        # Test failure detection
        test_results = context.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0) or test_results.get("summary", {}).get("failed", 0)
            if failed and failed > 0:
                result.add(Failure(
                    failure_type=FailureType.TEST_FAILURE,
                    description=f"{failed} test(s) failed",
                    severity="medium",
                ))

        # Hallucination detection
        if context.get("hallucination_detected") or "hallucinated" in error_text.lower():
            result.add(Failure(
                failure_type=FailureType.HALLUCINATION,
                description="Potential hallucination detected in model output",
                severity="high",
            ))

        # Dead edit detection
        patches = context.get("patches", [])
        if isinstance(patches, list):
            for p in patches:
                diff = p.get("diff", "") if isinstance(p, dict) else getattr(p, "diff", "")
                if not diff:
                    result.add(Failure(
                        failure_type=FailureType.DEAD_EDIT,
                        description="Edit produced no actual changes (empty diff)",
                        severity="low",
                    ))
                    break

        # Timeout detection
        if context.get("timeout") or "timed out" in error_text.lower():
            result.add(Failure(
                failure_type=FailureType.TIMEOUT,
                description="Operation timed out",
                severity="medium",
            ))

        # Low confidence detection
        confidence = context.get("confidence", 1.0)
        if isinstance(confidence, (int, float)) and confidence < 0.3:
            result.add(Failure(
                failure_type=FailureType.LOW_CONFIDENCE,
                description=f"Low confidence score: {confidence:.2f}",
                severity="low",
            ))

        return result
