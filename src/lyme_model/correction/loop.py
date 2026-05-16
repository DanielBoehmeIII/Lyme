"""Week 79 — Local Self-Correction Loop.

Given failed tests or verification errors, Lyme Model should:
1. Summarize failure
2. Locate likely cause
3. Choose next action
4. Patch minimally
5. Rerun verification
6. Stop after bounded attempts
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import time
import re


@dataclass
class CorrectionAttempt:
    attempt_number: int = 0
    failure_summary: str = ""
    likely_cause: str = ""
    action_taken: str = ""
    patch_applied: bool = False
    verification_passed: bool = False
    latency_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "attempt_number": self.attempt_number,
            "failure_summary": self.failure_summary[:100],
            "likely_cause": self.likely_cause[:100],
            "action_taken": self.action_taken[:100],
            "patch_applied": self.patch_applied,
            "verification_passed": self.verification_passed,
            "latency_ms": round(self.latency_ms, 1),
            "errors": self.errors,
        }


@dataclass
class CorrectionSummary:
    total_attempts: int = 0
    resolved: bool = False
    total_latency_ms: float = 0.0
    attempts: List[CorrectionAttempt] = field(default_factory=list)
    regressions: int = 0
    stopped_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "total_attempts": self.total_attempts,
            "resolved": self.resolved,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "regressions": self.regressions,
            "stopped_reason": self.stopped_reason,
            "attempts": [a.to_dict() for a in self.attempts],
        }

    def to_markdown(self) -> str:
        lines = ["# Self-Correction Summary", ""]
        lines.append(f"**Resolved**: {'Yes' if self.resolved else 'No'}")
        lines.append(f"**Attempts**: {self.total_attempts}")
        lines.append(f"**Total time**: {self.total_latency_ms:.0f}ms")
        lines.append(f"**Regressions**: {self.regressions}")
        lines.append(f"**Stopped**: {self.stopped_reason}")
        lines.append("")
        for a in self.attempts:
            lines.append(f"### Attempt {a.attempt_number}")
            lines.append(f"- Failure: {a.failure_summary[:80]}")
            lines.append(f"- Cause: {a.likely_cause[:80]}")
            lines.append(f"- Action: {a.action_taken[:80]}")
            lines.append(f"- Patch: {'Yes' if a.patch_applied else 'No'}")
            lines.append(f"- Verified: {'Yes' if a.verification_passed else 'No'}")
            lines.append("")
        return "\n".join(lines)


class CorrectionLoop:
    """Self-correction loop with bounded attempts.

    max_attempts: stop after this many tries (default 3)
    stop_on_success: if True, stop as soon as verification passes
    """

    def __init__(self, max_attempts: int = 3, stop_on_success: bool = True):
        self.max_attempts = max_attempts
        self.stop_on_success = stop_on_success
        self.attempts: List[CorrectionAttempt] = []

    def summarize_failure(self, context: dict) -> str:
        """Extract a concise failure summary from context."""
        parts = []

        test_results = context.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0)
            if failed > 0:
                errors = test_results.get("errors", [])
                if errors:
                    parts.append(f"{failed} test(s) failed")
                    for e in errors[:2]:
                        parts.append(str(e)[:80])
                else:
                    parts.append(f"{failed} test(s) failed (no details)")

        error = context.get("error", "")
        if error:
            parts.append(str(error)[:120])

        verification = context.get("verification_results", [])
        for v in verification:
            if isinstance(v, dict) and not v.get("passed", True):
                parts.append(v.get("details", "Verification failed"))

        return "; ".join(parts) if parts else "Unknown failure"

    def locate_cause(self, failure_summary: str, context: dict) -> str:
        """Identify the likely cause of the failure."""
        summary_lower = failure_summary.lower()
        causes = []

        # Pattern matching against known failure types
        cause_patterns = [
            ("AssertionError", "Test assertion failed — likely bug in implementation"),
            ("ImportError", "Missing or incorrect import"),
            ("NameError", "Undefined variable or function name"),
            ("TypeError", "Wrong argument types or count"),
            ("SyntaxError", "Invalid syntax in generated code"),
            ("AttributeError", "Accessed attribute does not exist on object"),
            ("KeyError", "Missing dictionary key"),
            ("IndexError", "List index out of range"),
            ("ValueError", "Invalid value provided"),
            ("ModuleNotFoundError", "Module not installed or import path wrong"),
            ("FileNotFoundError", "Referenced file does not exist"),
            ("timeout", "Operation exceeded time limit"),
            ("permission", "File permission issue"),
            ("memory", "Out of memory error"),
        ]

        for keyword, cause in cause_patterns:
            if keyword.lower() in summary_lower:
                causes.append(cause)

        # Check for test-specific patterns
        test_results = context.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0)
            total = test_results.get("total", 0)
            if total > 0 and failed == total:
                causes.append("All tests failed — likely fundamental issue with patch or setup")

        return causes[0] if causes else "Could not determine cause from available information"

    def choose_action(self, failure_summary: str, cause: str, context: dict) -> str:
        """Determine the next action to take."""
        summary_lower = failure_summary.lower()
        cause_lower = cause.lower()

        if "import" in cause_lower or "import" in summary_lower:
            return "Fix imports — add missing import or correct module path"
        if "syntax" in cause_lower or "syntax" in summary_lower:
            return "Fix syntax — check brackets, indentation, and punctuation"
        if "assertion" in cause_lower or "assert" in summary_lower:
            return "Fix logic — review assertion requirements and update implementation"
        if "name" in cause_lower or "undefined" in summary_lower:
            return "Fix naming — define missing variables or correct references"
        if "type" in cause_lower:
            return "Fix types — ensure correct argument types and return values"
        if "timeout" in cause_lower:
            return "Optimize — reduce scope or split into smaller steps"

        # Generic actions
        if context.get("patch_applied", False):
            return "Re-examine and revise the patch"
        return "Gather more context and retry"

    def apply_patch(self, action: str, context: dict,
                    patch_fn: Callable) -> tuple[bool, str]:
        """Apply a minimal patch based on the chosen action."""
        try:
            result = patch_fn(action, context)
            return True, result
        except Exception as e:
            return False, str(e)

    def run_verification(self, context: dict,
                         verify_fn: Callable) -> bool:
        """Run verification and return pass/fail."""
        try:
            return verify_fn(context)
        except Exception:
            return False

    def should_stop(self, attempt: CorrectionAttempt) -> tuple[bool, str]:
        """Check if we should stop the correction loop."""
        if attempt.verification_passed and self.stop_on_success:
            return True, "Verification passed"
        if len(self.attempts) >= self.max_attempts:
            return True, f"Max attempts ({self.max_attempts}) reached"
        if attempt.attempt_number > 0 and not attempt.patch_applied:
            return True, "No patch applied — cannot make progress"
        # Check for loop detection: same failure-action repeated 3+ times
        if len(self.attempts) >= 3:
            last_three = self.attempts[-3:]
            all_same = all(
                a.failure_summary == last_three[0].failure_summary
                and a.action_taken == last_three[0].action_taken
                for a in last_three
            )
            if all_same:
                return True, "Same failure and action repeated 3 times — likely infinite loop"
        return False, ""

    def run(self, context: dict, patch_fn: Callable,
            verify_fn: Callable) -> CorrectionSummary:
        """Execute the self-correction loop."""
        start_time = time.time()
        self.attempts = []
        regressions = 0
        previous_failures = 0

        for attempt_num in range(1, self.max_attempts + 1):
            attempt_start = time.time()
            ca = CorrectionAttempt(attempt_number=attempt_num)

            # 1. Summarize failure
            ca.failure_summary = self.summarize_failure(context)

            # 2. Locate cause
            ca.likely_cause = self.locate_cause(ca.failure_summary, context)

            # 3. Choose action
            ca.action_taken = self.choose_action(ca.failure_summary, ca.likely_cause, context)

            # 4. Apply patch
            patch_applied, patch_result = self.apply_patch(ca.action_taken, context, patch_fn)
            ca.patch_applied = patch_applied
            if not patch_applied:
                ca.errors.append(patch_result)

            # 5. Rerun verification
            if patch_applied:
                ca.verification_passed = self.run_verification(context, verify_fn)

            # Track regressions
            current_failures = context.get("test_results", {}).get("failed", 0) if isinstance(
                context.get("test_results"), dict) else 0
            if current_failures > previous_failures:
                regressions += 1
            previous_failures = current_failures

            ca.latency_ms = int((time.time() - attempt_start) * 1000)
            self.attempts.append(ca)

            # 6. Check stop condition
            should_stop, reason = self.should_stop(ca)
            if should_stop:
                total_time = int((time.time() - start_time) * 1000)
                return CorrectionSummary(
                    total_attempts=attempt_num,
                    resolved=ca.verification_passed,
                    total_latency_ms=total_time,
                    attempts=list(self.attempts),
                    regressions=regressions,
                    stopped_reason=reason,
                )

        total_time = int((time.time() - start_time) * 1000)
        last = self.attempts[-1] if self.attempts else None
        return CorrectionSummary(
            total_attempts=self.max_attempts,
            resolved=last.verification_passed if last else False,
            total_latency_ms=total_time,
            attempts=list(self.attempts),
            regressions=regressions,
            stopped_reason=f"Completed {self.max_attempts} attempts",
        )


class SelfCorrectingAgent:
    """Agent wrapper with built-in self-correction."""

    def __init__(self, max_attempts: int = 3):
        self.loop = CorrectionLoop(max_attempts=max_attempts)

    def execute(self, task: str, context: dict,
                patch_fn: Callable, verify_fn: Callable) -> CorrectionSummary:
        """Execute a task with self-correction."""
        return self.loop.run(context, patch_fn, verify_fn)
