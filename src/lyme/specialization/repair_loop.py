"""RepairLoop — chains specialized models for self-repair."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class RepairStage(str, Enum):
    DETECT = "detect"
    LOCALIZE = "localize"
    PLAN = "plan"
    PATCH = "patch"
    VERIFY = "verify"
    RETRY = "retry"


class RepairOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    ESCALATED = "escalated"


@dataclass
class RepairAttempt:
    stage: RepairStage
    slice_used: str
    duration_sec: float
    success: bool
    output_summary: str
    error: str = ""

    def to_dict(self) -> Dict:
        return {
            "stage": self.stage.value,
            "slice": self.slice_used,
            "duration_sec": round(self.duration_sec, 2),
            "success": self.success,
            "output": self.output_summary[:60],
        }


@dataclass
class RepairResult:
    task: str
    outcome: RepairOutcome
    attempts: List[RepairAttempt]
    total_duration_sec: float
    retries_used: int
    max_retries: int
    final_error: str

    def to_dict(self) -> Dict:
        return {
            "task": self.task[:80],
            "outcome": self.outcome.value,
            "attempts": [a.to_dict() for a in self.attempts],
            "total_duration_sec": round(self.total_duration_sec, 1),
            "retries": self.retries_used,
        }

    def render_cli(self) -> str:
        icons = {RepairOutcome.SUCCESS: "✅", RepairOutcome.FAILED: "❌",
                 RepairOutcome.PARTIAL: "🟡", RepairOutcome.ESCALATED: "⬆️"}
        lines = []
        lines.append("=" * 70)
        lines.append("  REPAIR LOOP RESULT")
        lines.append("=" * 70)
        lines.append(f"  Outcome: {icons.get(self.outcome, '•')} {self.outcome.value}")
        lines.append(f"  Task: {self.task[:60]}")
        lines.append(f"  Duration: {self.total_duration_sec:.1f}s | "
                     f"Retries: {self.retries_used}/{self.max_retries}")
        lines.append("")
        lines.append("  Stages:")
        for a in self.attempts:
            icon = "✅" if a.success else "❌"
            lines.append(f"    {icon} [{a.stage.value}] {a.slice_used} ({a.duration_sec:.1f}s)")
            lines.append(f"       → {a.output_summary[:60]}")
        if self.final_error:
            lines.append(f"  Error: {self.final_error[:80]}")
        lines.append("=" * 70)
        return "\n".join(lines)


class RepairLoop:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._slices: Dict[RepairStage, Callable] = {}

    def register_slice(self, stage: RepairStage, slice_fn: Callable) -> None:
        self._slices[stage] = slice_fn

    def run(self, task: str, context: Any = None) -> RepairResult:
        attempts: List[RepairAttempt] = []
        start = time.time()

        stages = [
            RepairStage.DETECT, RepairStage.LOCALIZE,
            RepairStage.PLAN, RepairStage.PATCH, RepairStage.VERIFY,
        ]

        retries_used = 0
        final_error = ""

        for retry in range(self.max_retries + 1):
            for stage in stages:
                stage_start = time.time()
                slice_fn = self._slices.get(stage)
                if not slice_fn:
                    attempts.append(RepairAttempt(
                        stage=stage, slice_used="none",
                        duration_sec=time.time() - stage_start,
                        success=True, output_summary="No slice registered — skipped",
                    ))
                    continue

                try:
                    result = slice_fn(task, context, attempts)
                    duration = time.time() - stage_start
                    success = result.get("success", False)
                    output = result.get("output", str(result)[:60])
                    attempts.append(RepairAttempt(
                        stage=stage,
                        slice_used=slice_fn.__name__ if hasattr(slice_fn, "__name__") else "unknown",
                        duration_sec=duration,
                        success=success,
                        output_summary=output,
                    ))

                    if not success:
                        final_error = result.get("error", f"Stage {stage.value} failed")
                        break
                except Exception as e:
                    duration = time.time() - stage_start
                    attempts.append(RepairAttempt(
                        stage=stage, slice_used="error",
                        duration_sec=duration, success=False,
                        output_summary=str(e)[:60], error=str(e),
                    ))
                    final_error = str(e)
                    break

            verify_attempts = [a for a in attempts if a.stage == RepairStage.VERIFY]
            if verify_attempts and verify_attempts[-1].success:
                total_duration = time.time() - start
                return RepairResult(
                    task=task,
                    outcome=RepairOutcome.SUCCESS,
                    attempts=attempts,
                    total_duration_sec=total_duration,
                    retries_used=retries_used,
                    max_retries=self.max_retries,
                    final_error="",
                )

            if retry < self.max_retries:
                retries_used += 1
                retry_fn = self._slices.get(RepairStage.RETRY)
                if retry_fn:
                    try:
                        retry_fn(task, context, attempts)
                    except Exception:
                        pass

        total_duration = time.time() - start
        verify_passed = any(a.success and a.stage == RepairStage.VERIFY for a in attempts)
        outcome = RepairOutcome.SUCCESS if verify_passed else RepairOutcome.FAILED

        return RepairResult(
            task=task,
            outcome=outcome,
            attempts=attempts,
            total_duration_sec=total_duration,
            retries_used=retries_used,
            max_retries=self.max_retries,
            final_error=final_error,
        )
