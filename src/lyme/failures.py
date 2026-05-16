"""Lyme Failure Honesty — Detect, classify, and report failures transparently.

Failure taxonomy with user-facing explanations and research-facing telemetry.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum


class FailureCategory(Enum):
    INCOMPLETE_FIX = "incomplete_fix"
    UNVERIFIED_ASSUMPTION = "unverified_assumption"
    FAILED_TEST = "failed_test"
    MISSING_DEPENDENCY = "missing_dependency"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    MODEL_UNCERTAINTY = "model_uncertainty"
    CONTEXT_INSUFFICIENCY = "context_insufficiency"
    TOOL_FAILURE = "tool_failure"
    HALLUCINATED_API = "hallucinated_api"
    RISKY_EDIT = "risky_edit"
    TIMEOUT = "timeout"
    PARSING_ERROR = "parsing_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class FailureSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


FAILURE_TAXONOMY = {
    FailureCategory.INCOMPLETE_FIX: {
        "description": "The fix was applied but does not fully resolve the issue",
        "severity": FailureSeverity.HIGH,
        "user_message": "This fix may be incomplete. The root cause was not fully addressed.",
        "retry_strategy": "Re-analyze the issue with additional context about remaining symptoms",
        "detectable_by": ["test_failure_after_fix", "partial_test_coverage",
                          "user_correction"],
    },
    FailureCategory.UNVERIFIED_ASSUMPTION: {
        "description": "The agent made an assumption about the codebase that was not verified",
        "severity": FailureSeverity.MEDIUM,
        "user_message": "I made an assumption that I could not verify. Please confirm it is correct.",
        "retry_strategy": "Verify the assumption explicitly before proceeding",
        "detectable_by": ["missing_file_reference", "inferred_behavior",
                          "confidence_below_threshold"],
    },
    FailureCategory.FAILED_TEST: {
        "description": "Tests failed after the agent's change",
        "severity": FailureSeverity.HIGH,
        "user_message": "The change caused test failures. Review the test output below.",
        "retry_strategy": "Analyze test output, identify regression, adjust fix",
        "detectable_by": ["test_runner_exit_code", "test_output_pattern",
                          "coverage_change"],
    },
    FailureCategory.MISSING_DEPENDENCY: {
        "description": "A required dependency was not found",
        "severity": FailureSeverity.HIGH,
        "user_message": "A required dependency is missing. Check the dependency list below.",
        "retry_strategy": "Install missing dependency or adjust import",
        "detectable_by": ["import_error", "module_not_found", "command_not_found"],
    },
    FailureCategory.UNSUPPORTED_CLAIM: {
        "description": "The agent made a claim that cannot be supported by available evidence",
        "severity": FailureSeverity.MEDIUM,
        "user_message": "I cannot provide evidence for this claim. I should have refused to answer.",
        "retry_strategy": "Reframe the question or provide additional context",
        "detectable_by": ["no_file_citations", "confidence_below_0_3",
                          "contradiction_detected"],
    },
    FailureCategory.MODEL_UNCERTAINTY: {
        "description": "Model confidence is below the threshold for reliable action",
        "severity": FailureSeverity.LOW,
        "user_message": "I am not confident about this response. Please verify before acting.",
        "retry_strategy": "Gather more context or use a different model",
        "detectable_by": ["confidence_score", "response_entropy", "token_probability"],
    },
    FailureCategory.CONTEXT_INSUFFICIENCY: {
        "description": "The agent did not have enough context to make an informed decision",
        "severity": FailureSeverity.MEDIUM,
        "user_message": "I didn't have enough information to fully understand this. Consider providing more context.",
        "retry_strategy": "Provide additional relevant files or context",
        "detectable_by": ["context_window_utilization", "file_coverage",
                          "retrieval_score"],
    },
    FailureCategory.TOOL_FAILURE: {
        "description": "A tool call failed or returned unexpected results",
        "severity": FailureSeverity.HIGH,
        "user_message": "A tool I tried to use failed. The error is below.",
        "retry_strategy": "Retry the tool with adjusted parameters",
        "detectable_by": ["non_zero_exit_code", "exception_in_tool",
                          "timeout_in_tool"],
    },
    FailureCategory.HALLUCINATED_API: {
        "description": "The agent referenced an API or function that does not exist",
        "severity": FailureSeverity.CRITICAL,
        "user_message": "I referenced something that does not exist in this codebase. This is a hallucination.",
        "retry_strategy": "Verify API/function existence before use",
        "detectable_by": ["nonexistent_import", "missing_function_call",
                          "fake_module_reference"],
    },
    FailureCategory.RISKY_EDIT: {
        "description": "The edit involves high-risk files without adequate safeguards",
        "severity": FailureSeverity.HIGH,
        "user_message": "This edit affects critical files. Consider manual review before applying.",
        "retry_strategy": "Review edit plan carefully, add additional tests",
        "detectable_by": ["auth_config_file_targeted", "schema_migration",
                          "security_sensitive_code"],
    },
    FailureCategory.TIMEOUT: {
        "description": "The operation exceeded the allowed time limit",
        "severity": FailureSeverity.MEDIUM,
        "user_message": "The operation took too long and was cancelled.",
        "retry_strategy": "Split the task into smaller parts or increase timeout",
        "detectable_by": ["duration_exceeds_limit", "no_response_in_interval"],
    },
    FailureCategory.PARSING_ERROR: {
        "description": "Could not parse the repository's code or structure",
        "severity": FailureSeverity.LOW,
        "user_message": "I had trouble understanding some parts of the code structure.",
        "retry_strategy": "Check for syntax errors or unsupported language features",
        "detectable_by": ["syntax_error", "ast_parse_failure", "encoding_error"],
    },
    FailureCategory.PERMISSION_ERROR: {
        "description": "Insufficient permissions to access or modify files",
        "severity": FailureSeverity.HIGH,
        "user_message": "I don't have permission to access or modify the required files.",
        "retry_strategy": "Check file permissions and ownership",
        "detectable_by": ["permission_denied", "eacces", "read_only_filesystem"],
    },
    FailureCategory.RESOURCE_EXHAUSTION: {
        "description": "System resources (memory, disk, CPU) were exhausted",
        "severity": FailureSeverity.HIGH,
        "user_message": "The system ran out of resources. Try closing other applications.",
        "retry_strategy": "Reduce scope, free resources, or use a smaller model",
        "detectable_by": ["memory_error", "disk_full", "oom_kill", "swap_exhaustion"],
    },
}


@dataclass
class FailureRecord:
    failure_id: str
    category: FailureCategory
    severity: FailureSeverity
    description: str
    user_message: str
    retry_recommendation: str
    context: dict = field(default_factory=dict)
    trace_ref: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved_by_retry: bool = False
    resolved_by: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "failure_id": self.failure_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "user_message": self.user_message,
            "retry_recommendation": self.retry_recommendation,
            "context": self.context,
            "trace_ref": self.trace_ref,
            "timestamp": self.timestamp,
            "resolved_by_retry": self.resolved_by_retry,
            "resolved_by": self.resolved_by,
        }

    def user_facing(self) -> str:
        severity_icons = {
            FailureSeverity.CRITICAL: "🚨",
            FailureSeverity.HIGH: "⚠",
            FailureSeverity.MEDIUM: "!",
            FailureSeverity.LOW: "?",
            FailureSeverity.INFO: "i",
        }
        icon = severity_icons.get(self.severity, "!")
        lines = [
            f"{icon} [{self.severity.value.upper()}] {self.category.value.replace('_', ' ').title()}",
            f"  {self.user_message}",
            f"  → Try: {self.retry_recommendation}",
        ]
        return "\n".join(lines)


@dataclass 
class FailureAnalysis:
    failures: List[FailureRecord] = field(default_factory=list)
    total_count: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "by_category": self.by_category,
            "by_severity": self.by_severity,
            "failures": [f.to_dict() for f in self.failures],
            "summary": self.summary,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append("# Failure Analysis")
        lines.append(f"**Total failures**: {self.total_count}")
        lines.append("")
        lines.append("## By Category")
        for cat, count in sorted(self.by_category.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {count}")
        lines.append("")
        lines.append("## By Severity")
        for sev, count in sorted(self.by_severity.items(), key=lambda x: -x[1]):
            lines.append(f"- {sev}: {count}")
        lines.append("")
        lines.append("## Failures")
        for f in self.failures:
            lines.append("")
            lines.append(f"### {f.failure_id}")
            lines.append(f"**Category**: {f.category.value}")
            lines.append(f"**Severity**: {f.severity.value}")
            lines.append(f"**Description**: {f.description}")
            lines.append(f"**User message**: {f.user_message}")
            lines.append(f"**Retry**: {f.retry_recommendation}")
        return "\n".join(lines)


class FailureDetector:
    """Detects and classifies failures in agent operations."""

    def __init__(self):
        self._history: List[FailureRecord] = []

    def detect(self, context: dict) -> List[FailureRecord]:
        failures = []

        detectors = [
            self._check_tool_failure,
            self._check_test_failure,
            self._check_hallucination,
            self._check_uncertainty,
            self._check_timeout,
            self._check_resource_exhaustion,
            self._check_permission_error,
        ]

        for detector in detectors:
            try:
                result = detector(context)
                if result:
                    failures.extend(result)
            except Exception:
                pass

        self._history.extend(failures)
        return failures

    def _check_tool_failure(self, ctx: dict) -> List[FailureRecord]:
        records = []
        exit_code = ctx.get("exit_code")
        if exit_code is not None and exit_code != 0:
            records.append(FailureRecord(
                failure_id=self._new_id(),
                category=FailureCategory.TOOL_FAILURE,
                severity=FailureSeverity.HIGH,
                description=f"Tool exited with code {exit_code}",
                user_message=FAILURE_TAXONOMY[FailureCategory.TOOL_FAILURE]["user_message"],
                retry_recommendation=FAILURE_TAXONOMY[FailureCategory.TOOL_FAILURE]["retry_strategy"],
                context={"exit_code": exit_code, "stderr": ctx.get("stderr", "")},
                trace_ref=ctx.get("trace_id"),
            ))
        return records

    def _check_test_failure(self, ctx: dict) -> List[FailureRecord]:
        records = []
        test_results = ctx.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0)
            if failed and failed > 0:
                records.append(FailureRecord(
                    failure_id=self._new_id(),
                    category=FailureCategory.FAILED_TEST,
                    severity=FailureSeverity.HIGH,
                    description=f"{failed} test(s) failed",
                    user_message=FAILURE_TAXONOMY[FailureCategory.FAILED_TEST]["user_message"],
                    retry_recommendation=FAILURE_TAXONOMY[FailureCategory.FAILED_TEST]["retry_strategy"],
                    context={"failed": failed, "total": test_results.get("total", 0)},
                    trace_ref=ctx.get("trace_id"),
                ))
        return records

    def _check_hallucination(self, ctx: dict) -> List[FailureRecord]:
        records = []
        claims = ctx.get("claims", [])
        for claim in claims:
            if isinstance(claim, dict):
                if claim.get("refused") or claim.get("confidence", 1.0) < 0.3:
                    if claim.get("citations") is None or len(claim.get("citations", [])) == 0:
                        records.append(FailureRecord(
                            failure_id=self._new_id(),
                            category=FailureCategory.HALLUCINATED_API,
                            severity=FailureSeverity.CRITICAL,
                            description=f"Unsupported claim: {claim.get('statement', '')[:100]}",
                            user_message=FAILURE_TAXONOMY[FailureCategory.HALLUCINATED_API]["user_message"],
                            retry_recommendation=FAILURE_TAXONOMY[FailureCategory.HALLUCINATED_API]["retry_strategy"],
                            context={"claim": claim},
                            trace_ref=ctx.get("trace_id"),
                        ))
                        break
        return records

    def _check_uncertainty(self, ctx: dict) -> List[FailureRecord]:
        records = []
        confidence = ctx.get("confidence", 1.0)
        if confidence < 0.4:
            records.append(FailureRecord(
                failure_id=self._new_id(),
                category=FailureCategory.MODEL_UNCERTAINTY,
                severity=FailureSeverity.LOW,
                description=f"Confidence {confidence:.2f} below threshold",
                user_message=FAILURE_TAXONOMY[FailureCategory.MODEL_UNCERTAINTY]["user_message"],
                retry_recommendation=FAILURE_TAXONOMY[FailureCategory.MODEL_UNCERTAINTY]["retry_strategy"],
                context={"confidence": confidence},
                trace_ref=ctx.get("trace_id"),
            ))
        return records

    def _check_timeout(self, ctx: dict) -> List[FailureRecord]:
        records = []
        timeout = ctx.get("timeout", False)
        if timeout:
            records.append(FailureRecord(
                failure_id=self._new_id(),
                category=FailureCategory.TIMEOUT,
                severity=FailureSeverity.MEDIUM,
                description="Operation timed out",
                user_message=FAILURE_TAXONOMY[FailureCategory.TIMEOUT]["user_message"],
                retry_recommendation=FAILURE_TAXONOMY[FailureCategory.TIMEOUT]["retry_strategy"],
                context={"duration_ms": ctx.get("duration_ms", 0)},
                trace_ref=ctx.get("trace_id"),
            ))
        return records

    def _check_resource_exhaustion(self, ctx: dict) -> List[FailureRecord]:
        records = []
        error = str(ctx.get("error", ""))
        resource_signals = ["memory", "oom", "disk full", "no space",
                            "cannot allocate", "out of memory"]
        for signal in resource_signals:
            if signal in error.lower():
                records.append(FailureRecord(
                    failure_id=self._new_id(),
                    category=FailureCategory.RESOURCE_EXHAUSTION,
                    severity=FailureSeverity.HIGH,
                    description=f"Resource exhaustion: {error[:100]}",
                    user_message=FAILURE_TAXONOMY[FailureCategory.RESOURCE_EXHAUSTION]["user_message"],
                    retry_recommendation=FAILURE_TAXONOMY[FailureCategory.RESOURCE_EXHAUSTION]["retry_strategy"],
                    context={"error": error},
                    trace_ref=ctx.get("trace_id"),
                ))
                break
        return records

    def _check_permission_error(self, ctx: dict) -> List[FailureRecord]:
        records = []
        error = str(ctx.get("error", ""))
        perm_signals = ["permission denied", "eacces", "not permitted",
                        "access denied", "read-only"]
        for signal in perm_signals:
            if signal in error.lower():
                records.append(FailureRecord(
                    failure_id=self._new_id(),
                    category=FailureCategory.PERMISSION_ERROR,
                    severity=FailureSeverity.HIGH,
                    description=f"Permission error: {error[:100]}",
                    user_message=FAILURE_TAXONOMY[FailureCategory.PERMISSION_ERROR]["user_message"],
                    retry_recommendation=FAILURE_TAXONOMY[FailureCategory.PERMISSION_ERROR]["retry_strategy"],
                    context={"error": error},
                    trace_ref=ctx.get("trace_id"),
                ))
                break
        return records

    def _new_id(self) -> str:
        import uuid
        return f"fail_{uuid.uuid4().hex[:12]}"

    def analyze(self, records: List[FailureRecord]) -> FailureAnalysis:
        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for f in records:
            cat = f.category.value.replace("_", " ").title()
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

        total = len(records)
        if total == 0:
            summary = "No failures detected."
        else:
            top_cat = max(by_category, key=by_category.get)
            top_sev = max(by_severity, key=by_severity.get)
            summary = (
                f"{total} failure(s) detected. "
                f"Most common: {top_cat} ({by_category[top_cat]}). "
                f"Highest severity: {top_sev} ({by_severity[top_sev]})."
            )

        return FailureAnalysis(
            failures=records,
            total_count=total,
            by_category=by_category,
            by_severity=by_severity,
            summary=summary,
        )

    def get_history(self) -> List[FailureRecord]:
        return list(self._history)


def get_failure_taxonomy() -> dict:
    return {
        cat.value: {
            "description": info["description"],
            "severity": info["severity"].value,
            "user_message": info["user_message"],
            "retry_strategy": info["retry_strategy"],
            "detectable_by": info["detectable_by"],
        }
        for cat, info in FAILURE_TAXONOMY.items()
    }
