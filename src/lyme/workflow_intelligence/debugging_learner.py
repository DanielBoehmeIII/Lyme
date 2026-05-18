"""DebuggingSequenceLearner — learns effective debugging sequences from outcomes."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class DebuggingAttempt:
    failure_type: str
    symptoms: List[str]
    actions_taken: List[str]
    successful: bool
    duration_sec: float
    root_cause: str = ""
    fix_description: str = ""

    def to_dict(self) -> Dict:
        return {
            "failure_type": self.failure_type,
            "symptoms": self.symptoms[:5],
            "actions_taken": self.actions_taken[:10],
            "successful": self.successful,
            "duration_sec": round(self.duration_sec, 1),
            "root_cause": self.root_cause[:80] if self.root_cause else "",
        }


@dataclass
class DebuggingStrategy:
    failure_type: str
    recommended_actions: List[str]
    success_rate: float
    total_attempts: int
    avg_duration_sec: float
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "failure_type": self.failure_type,
            "recommended_actions": self.recommended_actions[:5],
            "success_rate": round(self.success_rate, 3),
            "total_attempts": self.total_attempts,
            "avg_duration_sec": round(self.avg_duration_sec, 1),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class DebuggingLearnerReport:
    total_attempts: int
    strategies: List[DebuggingStrategy]
    overall_success_rate: float
    most_common_failures: List[str]
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_attempts": self.total_attempts,
            "strategies": [s.to_dict() for s in self.strategies[:5]],
            "overall_success_rate": round(self.overall_success_rate, 3),
            "most_common_failures": self.most_common_failures[:5],
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  DEBUGGING SEQUENCE LEARNER")
        lines.append("=" * 70)
        lines.append(f"  Total Attempts: {self.total_attempts}")
        lines.append(f"  Overall Success Rate: {self.overall_success_rate:.0%}")
        lines.append("")
        lines.append("  Strategies:")
        for s in self.strategies[:5]:
            bar = "█" * int(s.success_rate * 20)
            lines.append(f"    {s.failure_type}: {s.success_rate:.0%} {bar} "
                         f"({s.total_attempts} attempts, {s.avg_duration_sec:.0f}s avg)")
            lines.append(f"      → {' → '.join(s.recommended_actions[:3])}")
        if self.most_common_failures:
            lines.append("")
            lines.append("  Most Common Failures:")
            for f in self.most_common_failures[:5]:
                lines.append(f"    • {f}")
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


class DebuggingSequenceLearner:
    def __init__(self, storage_path: Optional[str] = None):
        self._attempts: List[DebuggingAttempt] = []
        self._storage_path = storage_path
        self._load()

    def record(self, failure_type: str, symptoms: List[str], actions_taken: List[str],
               successful: bool, duration_sec: float, root_cause: str = "",
               fix_description: str = "") -> None:
        self._attempts.append(DebuggingAttempt(
            failure_type=failure_type,
            symptoms=symptoms,
            actions_taken=actions_taken,
            successful=successful,
            duration_sec=duration_sec,
            root_cause=root_cause,
            fix_description=fix_description,
        ))
        self._save()

    def analyze(self) -> DebuggingLearnerReport:
        if not self._attempts:
            return DebuggingLearnerReport(
                total_attempts=0, strategies=[], overall_success_rate=0.0,
                most_common_failures=[],
                insights=["No debugging data yet"],
                recommendations=["Record debugging attempts to generate strategies"],
            )

        by_type: Dict[str, List[DebuggingAttempt]] = {}
        for a in self._attempts:
            if a.failure_type not in by_type:
                by_type[a.failure_type] = []
            by_type[a.failure_type].append(a)

        strategies: List[DebuggingStrategy] = []
        for ftype, attempts in by_type.items():
            successes = sum(1 for a in attempts if a.successful)
            durations = [a.duration_sec for a in attempts if a.successful]

            action_success: Dict[str, int] = {}
            for a in attempts:
                if a.successful:
                    for act in a.actions_taken:
                        action_success[act] = action_success.get(act, 0) + 1

            top_actions = sorted(action_success, key=action_success.get, reverse=True)[:5]

            strategies.append(DebuggingStrategy(
                failure_type=ftype,
                recommended_actions=top_actions,
                success_rate=successes / max(len(attempts), 1),
                total_attempts=len(attempts),
                avg_duration_sec=sum(durations) / max(len(durations), 1) if durations else 0.0,
                confidence=min(1.0, len(attempts) / 10),
            ))

        strategies.sort(key=lambda s: -s.success_rate)
        overall_sr = sum(1 for a in self._attempts if a.successful) / max(len(self._attempts), 1)

        failure_counts: Dict[str, int] = {}
        for a in self._attempts:
            failure_counts[a.failure_type] = failure_counts.get(a.failure_type, 0) + 1
        most_common = sorted(failure_counts, key=failure_counts.get, reverse=True)

        insights: List[str] = []
        if strategies:
            best = strategies[0]
            insights.append(f"Best debug strategy: '{best.failure_type}' "
                           f"({best.success_rate:.0%} success in {best.total_attempts} attempts)")
        worst = [s for s in strategies if s.total_attempts > 2 and s.success_rate < 0.4]
        if worst:
            insights.append(f"{len(worst)} failure types need better strategies")
        insights.append(f"Most common issue: {most_common[0]} ({failure_counts[most_common[0]]} occurrences)")

        recommendations: List[str] = []
        if worst:
            for w in worst[:3]:
                recommendations.append(f"Improve strategy for '{w.failure_type}' "
                                      f"(currently {w.success_rate:.0%})")
        if overall_sr < 0.6:
            recommendations.append("Add more verification steps between debugging actions")
        if not recommendations:
            recommendations.append("Debugging strategies are effective")

        return DebuggingLearnerReport(
            total_attempts=len(self._attempts),
            strategies=strategies,
            overall_success_rate=overall_sr,
            most_common_failures=most_common,
            insights=insights,
            recommendations=recommendations,
        )

    def suggest_actions(self, failure_type: str) -> Optional[List[str]]:
        matching = [a for a in self._attempts
                    if a.failure_type == failure_type and a.successful]
        if not matching:
            return None
        action_scores: Dict[str, float] = {}
        for a in matching:
            for i, act in enumerate(a.actions_taken):
                action_scores[act] = action_scores.get(act, 0) + 1.0 / (i + 1)
        sorted_actions = sorted(action_scores, key=action_scores.get, reverse=True)
        return sorted_actions[:5] if sorted_actions else None

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
                self._attempts.append(DebuggingAttempt(**d))
        except (json.JSONDecodeError, KeyError):
            pass
