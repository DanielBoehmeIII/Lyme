"""RecoveryBehaviorLearner — learns which recovery strategies work and when."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class RecoveryAttempt:
    failure_type: str
    recovery_action: str
    context: str
    successful: bool
    duration_sec: float
    side_effects: str

    def to_dict(self) -> Dict:
        return {
            "failure_type": self.failure_type,
            "recovery_action": self.recovery_action,
            "context": self.context[:60],
            "successful": self.successful,
            "duration_sec": round(self.duration_sec, 1),
            "side_effects": self.side_effects[:60] if self.side_effects else "",
        }


@dataclass
class RecoveryStrategy:
    failure_type: str
    recovery_action: str
    success_rate: float
    total_attempts: int
    avg_duration_sec: float
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "failure_type": self.failure_type,
            "recovery_action": self.recovery_action,
            "success_rate": round(self.success_rate, 3),
            "total_attempts": self.total_attempts,
            "avg_duration_sec": round(self.avg_duration_sec, 1),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class RecoveryLearnerReport:
    total_attempts: int
    strategies: List[RecoveryStrategy]
    overall_success_rate: float
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_attempts": self.total_attempts,
            "strategies": [s.to_dict() for s in self.strategies[:5]],
            "overall_success_rate": round(self.overall_success_rate, 3),
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  RECOVERY BEHAVIOR LEARNER")
        lines.append("=" * 70)
        lines.append(f"  Total Recovery Attempts: {self.total_attempts}")
        lines.append(f"  Overall Success Rate: {self.overall_success_rate:.0%}")
        lines.append("")
        lines.append("  Strategies:")
        for s in self.strategies[:5]:
            bar = "█" * int(s.success_rate * 20)
            lines.append(f"    {s.recovery_action} [{s.failure_type}]: "
                         f"{s.success_rate:.0%} {bar}")
            lines.append(f"      ({s.total_attempts} attempts, {s.avg_duration_sec:.0f}s avg)")
        if self.insights:
            lines.append("-" * 70)
            lines.append("  INSIGHTS:")
            for ins in self.insights:
                lines.append(f"    • {ins}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class RecoveryBehaviorLearner:
    def __init__(self, storage_path: Optional[str] = None):
        self._attempts: List[RecoveryAttempt] = []
        self._storage_path = storage_path
        self._load()

    def record(self, failure_type: str, recovery_action: str, context: str,
               successful: bool, duration_sec: float,
               side_effects: str = "") -> None:
        self._attempts.append(RecoveryAttempt(
            failure_type=failure_type,
            recovery_action=recovery_action,
            context=context,
            successful=successful,
            duration_sec=duration_sec,
            side_effects=side_effects,
        ))
        self._save()

    def analyze(self) -> RecoveryLearnerReport:
        if not self._attempts:
            return RecoveryLearnerReport(
                total_attempts=0, strategies=[], overall_success_rate=0.0,
                insights=["No recovery data yet"],
                recommendations=["Record recovery attempts to generate strategies"],
            )

        grouped: Dict[tuple, List[RecoveryAttempt]] = {}
        for a in self._attempts:
            key = (a.failure_type, a.recovery_action)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(a)

        strategies: List[RecoveryStrategy] = []
        for (ftype, action), attempts in grouped.items():
            successes = sum(1 for a in attempts if a.successful)
            durations = [a.duration_sec for a in attempts if a.successful]
            strategies.append(RecoveryStrategy(
                failure_type=ftype,
                recovery_action=action,
                success_rate=successes / max(len(attempts), 1),
                total_attempts=len(attempts),
                avg_duration_sec=sum(durations) / max(len(durations), 1) if durations else 0.0,
                confidence=min(1.0, len(attempts) / 10),
            ))

        strategies.sort(key=lambda s: -s.success_rate)
        overall_sr = sum(1 for a in self._attempts if a.successful) / max(len(self._attempts), 1)

        insights: List[str] = []
        if strategies:
            best = strategies[0]
            insights.append(f"Best recovery: '{best.recovery_action}' for '{best.failure_type}' "
                           f"({best.success_rate:.0%} in {best.total_attempts} attempts)")
        fast = [s for s in strategies if s.avg_duration_sec < 10 and s.total_attempts > 1]
        if fast:
            fastest = min(fast, key=lambda s: s.avg_duration_sec)
            insights.append(f"Fastest recovery: '{fastest.recovery_action}' "
                           f"(avg {fastest.avg_duration_sec:.0f}s)")

        recommendations: List[str] = []
        for s in strategies:
            if s.total_attempts > 2 and s.success_rate > 0.8:
                recommendations.append(f"Use '{s.recovery_action}' for '{s.failure_type}' "
                                      f"(proven {s.success_rate:.0%})")
        low = [s for s in strategies if s.total_attempts > 2 and s.success_rate < 0.4]
        for s in low:
            recommendations.append(f"Avoid '{s.recovery_action}' for '{s.failure_type}' "
                                  f"(only {s.success_rate:.0%} success)")
        if not recommendations:
            recommendations.append("All recovery strategies performing adequately")

        return RecoveryLearnerReport(
            total_attempts=len(self._attempts),
            strategies=strategies,
            overall_success_rate=overall_sr,
            insights=insights,
            recommendations=recommendations,
        )

    def suggest(self, failure_type: str) -> Optional[str]:
        attempts = [a for a in self._attempts if a.failure_type == failure_type]
        if not attempts:
            return None
        action_scores: Dict[str, float] = {}
        for a in attempts:
            if a.successful:
                action_scores[a.recovery_action] = action_scores.get(a.recovery_action, 0) + 1
            else:
                action_scores[a.recovery_action] = action_scores.get(a.recovery_action, 0) - 0.5
        if not action_scores:
            return None
        return max(action_scores, key=action_scores.get)

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [a.to_dict() for a in self._attempts]
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                self._attempts.append(RecoveryAttempt(**d))
        except (json.JSONDecodeError, KeyError):
            pass
