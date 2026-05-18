"""ExecutionSupervisor — monitors long-running tasks for drift, cascading mistakes, partial completion."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DRIFTED = "drifted"
    PARTIAL = "partial"
    CASCADING = "cascading"
    ROLLED_BACK = "rolled_back"


class DriftType(str, Enum):
    CONTEXT_DRIFT = "context_drift"
    GOAL_DRIFT = "goal_drift"
    SCOPE_CREEP = "scope_creep"
    ARCHITECTURAL_DRIFT = "architectural_drift"
    QUALITY_DEGRADATION = "quality_degradation"


@dataclass
class TaskSnapshot:
    timestamp: float
    status: TaskStatus
    description: str
    files_touched: List[str]
    subtask_index: int
    token_count: int
    confidence: float
    verification_passed: bool
    error_count: int


@dataclass
class DriftEvent:
    drift_type: DriftType
    severity: float
    description: str
    from_state: str
    to_state: str
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity,
            "description": self.description,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "recommendation": self.recommendation,
        }


@dataclass
class SupervisionReport:
    task_id: str
    goal: str
    status: TaskStatus
    duration_sec: float
    subtasks_planned: int
    subtasks_completed: int
    snapshots: List[TaskSnapshot]
    drift_events: List[DriftEvent]
    verification_pass_rate: float
    cascading_detected: bool
    partial_completion: bool
    recommendations: List[str]
    overall_health: str

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal[:80],
            "status": self.status.value,
            "duration_sec": round(self.duration_sec, 1),
            "subtasks_planned": self.subtasks_planned,
            "subtasks_completed": self.subtasks_completed,
            "drift_events": [d.to_dict() for d in self.drift_events],
            "verification_pass_rate": round(self.verification_pass_rate, 3),
            "cascading_detected": self.cascading_detected,
            "partial_completion": self.partial_completion,
            "recommendations": self.recommendations,
            "overall_health": self.overall_health,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  EXECUTION SUPERVISOR REPORT")
        lines.append("=" * 70)
        health_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🚫", "unknown": "❓"}
        lines.append(f"  Health: {health_icon.get(self.overall_health, '•')} {self.overall_health.upper()}")
        lines.append(f"  Task: {self.goal[:60]}")
        lines.append(f"  Status: {self.status.value}")
        lines.append(f"  Duration: {self.duration_sec:.1f}s | "
                     f"Subtasks: {self.subtasks_completed}/{self.subtasks_planned}")
        lines.append(f"  Verification: {self.verification_pass_rate:.0%} | "
                     f"Cascading: {self.cascading_detected} | Partial: {self.partial_completion}")
        if self.drift_events:
            lines.append("-" * 70)
            lines.append("  DRIFT EVENTS:")
            for d in self.drift_events:
                drift_icon = {"context_drift": "🌀", "goal_drift": "🎯", "scope_creep": "📏",
                              "architectural_drift": "🏗️", "quality_degradation": "📉"}
                lines.append(f"  {drift_icon.get(d.drift_type.value, '•')} [{d.drift_type.value}] {d.description}")
                lines.append(f"     → {d.recommendation}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ExecutionSupervisor:
    def __init__(self, drift_threshold: float = 0.3, cascade_threshold: int = 3):
        self.drift_threshold = drift_threshold
        self.cascade_threshold = cascade_threshold
        self._snapshots: Dict[str, List[TaskSnapshot]] = {}
        self._reports: Dict[str, SupervisionReport] = {}

    def start_monitoring(self, task_id: str, goal: str, subtask_count: int) -> None:
        snapshot = TaskSnapshot(
            timestamp=time.time(),
            status=TaskStatus.RUNNING,
            description="Task started",
            files_touched=[],
            subtask_index=0,
            token_count=0,
            confidence=1.0,
            verification_passed=True,
            error_count=0,
        )
        self._snapshots[task_id] = [snapshot]

    def record_snapshot(self, task_id: str, status: TaskStatus, description: str,
                        files_touched: List[str], subtask_index: int,
                        token_count: int, confidence: float,
                        verification_passed: bool, error_count: int) -> None:
        if task_id not in self._snapshots:
            self._snapshots[task_id] = []
        snapshot = TaskSnapshot(
            timestamp=time.time(),
            status=status,
            description=description,
            files_touched=files_touched,
            subtask_index=subtask_index,
            token_count=token_count,
            confidence=confidence,
            verification_passed=verification_passed,
            error_count=error_count,
        )
        self._snapshots[task_id].append(snapshot)

    def analyze(self, task_id: str, goal: str, subtasks_planned: int) -> Optional[SupervisionReport]:
        snapshots = self._snapshots.get(task_id, [])
        if not snapshots:
            return None

        drift_events: List[DriftEvent] = []
        total_verifications = 0
        passed_verifications = 0
        total_errors = 0
        completed_count = 0

        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1]
            curr = snapshots[i]

            if curr.status == TaskStatus.COMPLETED:
                completed_count += 1
            if curr.verification_passed:
                passed_verifications += 1
            total_verifications += 1
            total_errors += curr.error_count

            context_change_ratio = 0.0
            if prev.files_touched and curr.files_touched:
                new_files = set(curr.files_touched) - set(prev.files_touched)
                context_change_ratio = len(new_files) / max(len(curr.files_touched), 1)

            if context_change_ratio > self.drift_threshold:
                drift_events.append(DriftEvent(
                    drift_type=DriftType.CONTEXT_DRIFT,
                    severity=min(1.0, context_change_ratio),
                    description=f"Context shifted significantly: {len(new_files)} new files introduced",
                    from_state=f"{len(prev.files_touched)} files",
                    to_state=f"{len(curr.files_touched)} files ({len(new_files)} new)",
                    recommendation="Consider checkpointing before context switches between unrelated files",
                ))

            confidence_drop = prev.confidence - curr.confidence
            if confidence_drop > 0.2:
                drift_events.append(DriftEvent(
                    drift_type=DriftType.QUALITY_DEGRADATION,
                    severity=min(1.0, confidence_drop),
                    description=f"Confidence dropped from {prev.confidence:.0%} to {curr.confidence:.0%}",
                    from_state=f"confidence={prev.confidence:.2f}",
                    to_state=f"confidence={curr.confidence:.2f}",
                    recommendation="Loss of confidence indicates potential quality issues — consider verification checkpoint",
                ))

            if not curr.verification_passed and prev.verification_passed:
                drift_events.append(DriftEvent(
                    drift_type=DriftType.QUALITY_DEGRADATION,
                    severity=0.5,
                    description="Verification started failing",
                    from_state="verification passing",
                    to_state="verification failing",
                    recommendation="Investigate root cause of verification failure before proceeding",
                ))

        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            if first.token_count > 0 and last.token_count > first.token_count * 3:
                drift_events.append(DriftEvent(
                    drift_type=DriftType.GOAL_DRIFT,
                    severity=min(1.0, last.token_count / (first.token_count * 5)),
                    description=f"Token usage grew {last.token_count / max(first.token_count, 1):.1f}x — possible scope creep",
                    from_state=f"{first.token_count} tokens",
                    to_state=f"{last.token_count} tokens",
                    recommendation="Large token growth suggests goal drift — verify task is still on track",
                ))

        cascading_detected = total_errors >= self.cascade_threshold and any(
            s.error_count > 0 for s in snapshots[-3:]
        )
        partial_completion = completed_count < subtasks_planned and not any(
            s.status == TaskStatus.FAILED for s in snapshots
        )

        if cascading_detected:
            drift_events.append(DriftEvent(
                drift_type=DriftType.CONTEXT_DRIFT,
                severity=0.8,
                description=f"Cascading failure detected: {total_errors} errors across last 3 subtasks",
                from_state="normal execution",
                to_state="cascading failures",
                recommendation="STOP and rollback to last known good checkpoint. Errors are compounding.",
            ))

        recommendations = self._generate_recommendations(drift_events, cascading_detected,
                                                        partial_completion, total_errors)

        verification_pass_rate = passed_verifications / max(total_verifications, 1)

        if cascading_detected:
            overall_health = "critical"
            final_status = TaskStatus.CASCADING
        elif drift_events and any(d.severity > 0.6 for d in drift_events):
            overall_health = "warning"
            final_status = TaskStatus.DRIFTED
        elif partial_completion:
            overall_health = "warning"
            final_status = TaskStatus.PARTIAL
        elif verification_pass_rate < 0.5:
            overall_health = "warning"
            final_status = TaskStatus.DRIFTED
        else:
            overall_health = "healthy"
            final_status = TaskStatus.COMPLETED

        start_time = snapshots[0].timestamp
        end_time = snapshots[-1].timestamp

        report = SupervisionReport(
            task_id=task_id,
            goal=goal,
            status=final_status,
            duration_sec=end_time - start_time,
            subtasks_planned=subtasks_planned,
            subtasks_completed=completed_count,
            snapshots=snapshots,
            drift_events=drift_events,
            verification_pass_rate=verification_pass_rate,
            cascading_detected=cascading_detected,
            partial_completion=partial_completion,
            recommendations=recommendations,
            overall_health=overall_health,
        )
        self._reports[task_id] = report
        return report

    def _generate_recommendations(self, drift_events: List[DriftEvent],
                                  cascading: bool, partial: bool, errors: int) -> List[str]:
        recs = []
        if cascading:
            recs.append("Immediate rollback: cascading errors detected")
            recs.append("Reduce subtask complexity before retrying")
            recs.append("Add intermediate verification checkpoints")
        if partial:
            recs.append("Complete remaining subtasks with reduced scope")
            recs.append("Consider splitting the remaining work into a new task")
        if errors > 0:
            recs.append(f"Investigate root cause of {errors} errors")
        if any(d.drift_type == DriftType.CONTEXT_DRIFT for d in drift_events):
            recs.append("Limit context switches between unrelated files")
            recs.append("Group related file changes into single subtasks")
        if any(d.drift_type == DriftType.GOAL_DRIFT for d in drift_events):
            recs.append("Re-verify original goal before continuing")
            recs.append("Reset to last verified checkpoint if goal has drifted")
        if not recs:
            recs.append("Continue normal execution")
        return recs

    def get_report(self, task_id: str) -> Optional[SupervisionReport]:
        return self._reports.get(task_id)

    def reset(self, task_id: str) -> None:
        self._snapshots.pop(task_id, None)
        self._reports.pop(task_id, None)
