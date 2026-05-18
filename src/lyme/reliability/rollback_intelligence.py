"""RollbackIntelligence — learns which rollback strategies work and when to use them."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import json


class RollbackStrategy(str, Enum):
    GIT_REVERT = "git_revert"
    GIT_RESET = "git_reset"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    PATCH_REVERT = "patch_revert"
    FILE_COPY_RESTORE = "file_copy_restore"
    MANUAL_FIX = "manual_fix"


class RollbackOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    CONFLICT = "conflict"


@dataclass
class RollbackEvent:
    timestamp: float
    task_id: str
    strategy: RollbackStrategy
    reason: str
    files_affected: int
    success: bool
    duration_sec: float
    outcome: RollbackOutcome
    error: str = ""

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "strategy": self.strategy.value,
            "reason": self.reason[:80],
            "files_affected": self.files_affected,
            "success": self.success,
            "duration_sec": round(self.duration_sec, 2),
            "outcome": self.outcome.value,
            "has_error": bool(self.error),
        }


@dataclass
class StrategyScore:
    strategy: RollbackStrategy
    total_attempts: int
    successes: int
    failures: int
    avg_duration_sec: float
    success_rate: float
    contexts: List[str]
    recommended_for: List[str]

    def to_dict(self) -> Dict:
        return {
            "strategy": self.strategy.value,
            "total_attempts": self.total_attempts,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_sec": round(self.avg_duration_sec, 2),
            "contexts": self.contexts[:5],
            "recommended_for": self.recommended_for[:3],
        }


@dataclass
class RollbackIntelligenceReport:
    total_rollbacks: int
    strategies: List[StrategyScore]
    best_strategy: Optional[StrategyScore]
    recommendations: List[str]
    pattern_insights: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_rollbacks": self.total_rollbacks,
            "strategies": [s.to_dict() for s in self.strategies],
            "best_strategy": self.best_strategy.to_dict() if self.best_strategy else None,
            "recommendations": self.recommendations,
            "pattern_insights": self.pattern_insights,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  ROLLBACK INTELLIGENCE REPORT")
        lines.append("=" * 70)
        lines.append(f"  Total Rollbacks: {self.total_rollbacks}")
        lines.append(f"")
        lines.append(f"  Strategy Performance:")
        for s in sorted(self.strategies, key=lambda x: -x.success_rate):
            bar = "█" * int(s.success_rate * 20)
            lines.append(f"    {s.strategy.value}: {s.success_rate:.0%} {bar} "
                         f"({s.successes}/{s.total_attempts}, avg {s.avg_duration_sec:.1f}s)")
        if self.best_strategy:
            lines.append(f"")
            lines.append(f"  Best Strategy: {self.best_strategy.strategy.value} "
                         f"({self.best_strategy.success_rate:.0%})")
        if self.pattern_insights:
            lines.append("-" * 70)
            lines.append("  PATTERN INSIGHTS:")
            for p in self.pattern_insights:
                lines.append(f"    • {p}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class RollbackIntelligence:
    def __init__(self, storage_path: Optional[str] = None):
        self._events: List[RollbackEvent] = []
        self._storage_path = storage_path
        self._load()

    def record(self, task_id: str, strategy: RollbackStrategy, reason: str,
               files_affected: int, success: bool, duration_sec: float,
               outcome: RollbackOutcome, error: str = "") -> None:
        event = RollbackEvent(
            timestamp=time.time(),
            task_id=task_id,
            strategy=strategy,
            reason=reason,
            files_affected=files_affected,
            success=success,
            duration_sec=duration_sec,
            outcome=outcome,
            error=error,
        )
        self._events.append(event)
        self._save()

    def recommend(self, context: Dict) -> RollbackStrategy:
        reasons = [e for e in self._events]
        if not reasons:
            return RollbackStrategy.GIT_REVERT

        strategies = list(RollbackStrategy)
        best_strategy = strategies[0]
        best_score = -1.0

        for strategy in strategies:
            strategy_events = [e for e in self._events if e.strategy == strategy]
            if not strategy_events:
                continue

            recent = [e for e in strategy_events if e.timestamp > time.time() - 86400 * 7]
            window = recent if len(recent) >= 3 else strategy_events[-10:]

            success_rate = sum(1 for e in window if e.success) / max(len(window), 1)
            avg_duration = sum(e.duration_sec for e in window) / max(len(window), 1)

            file_count_match = 0
            if context.get("files_affected", 0) > 0:
                similar = [e for e in window
                           if abs(e.files_affected - context.get("files_affected", 0)) <= 2]
                file_count_match = len(similar) / max(len(window), 1)

            score = success_rate * 0.5 + (1.0 - avg_duration / 300.0) * 0.2 + file_count_match * 0.3

            if score > best_score:
                best_score = score
                best_strategy = strategy

        return best_strategy

    def analyze(self) -> RollbackIntelligenceReport:
        if not self._events:
            strategies = [
                StrategyScore(
                    strategy=s, total_attempts=0, successes=0, failures=0,
                    avg_duration_sec=0.0, success_rate=0.0,
                    contexts=[], recommended_for=[],
                ) for s in RollbackStrategy
            ]
            return RollbackIntelligenceReport(
                total_rollbacks=0, strategies=strategies, best_strategy=None,
                recommendations=["No rollback data yet — default to git revert"],
                pattern_insights=[],
            )

        strategy_map: Dict[RollbackStrategy, List[RollbackEvent]] = {}
        for e in self._events:
            if e.strategy not in strategy_map:
                strategy_map[e.strategy] = []
            strategy_map[e.strategy].append(e)

        scores: List[StrategyScore] = []
        for strategy, events in strategy_map.items():
            successes = sum(1 for e in events if e.success)
            failures = sum(1 for e in events if not e.success)
            durations = [e.duration_sec for e in events]
            avg_dur = sum(durations) / max(len(durations), 1) if durations else 0.0
            contexts = list(set(e.reason[:40] for e in events))
            rec_for = []
            if successes / max(len(events), 1) > 0.7:
                rec_for.append(f"general use ({len(events)} attempts)")

            scores.append(StrategyScore(
                strategy=strategy,
                total_attempts=len(events),
                successes=successes,
                failures=failures,
                avg_duration_sec=avg_dur,
                success_rate=successes / max(len(events), 1),
                contexts=contexts,
                recommended_for=rec_for,
            ))

        scores.sort(key=lambda s: -s.success_rate)
        best = scores[0] if scores else None

        pattern_insights = self._extract_pattern_insights()
        recommendations = self._generate_recommendations(scores)

        return RollbackIntelligenceReport(
            total_rollbacks=len(self._events),
            strategies=scores,
            best_strategy=best,
            recommendations=recommendations,
            pattern_insights=pattern_insights,
        )

    def _extract_pattern_insights(self) -> List[str]:
        insights: List[str] = []
        if not self._events:
            return insights

        file_counts = [e.files_affected for e in self._events]
        avg_files = sum(file_counts) / max(len(file_counts), 1) if file_counts else 0
        insights.append(f"Average {avg_files:.1f} files affected per rollback")

        success_rate = sum(1 for e in self._events if e.success) / max(len(self._events), 1)
        insights.append(f"Overall rollback success rate: {success_rate:.0%}")

        by_strategy: Dict[str, float] = {}
        for e in self._events:
            if e.strategy.value not in by_strategy:
                by_strategy[e.strategy.value] = 0
            by_strategy[e.strategy.value] += 1
        most_used = max(by_strategy, key=by_strategy.get) if by_strategy else "unknown"
        insights.append(f"Most used strategy: {most_used}")

        recent = [e for e in self._events if e.timestamp > time.time() - 86400 * 7]
        if recent:
            recent_rate = sum(1 for e in recent if e.success) / max(len(recent), 1)
            insights.append(f"Recent (7d) success rate: {recent_rate:.0%}")

        return insights

    def _generate_recommendations(self, scores: List[StrategyScore]) -> List[str]:
        recs: List[str] = []
        if not scores:
            recs.append("Collect more rollback data to generate recommendations")
            return recs

        best = max(scores, key=lambda s: s.success_rate) if scores else None
        if best and best.success_rate > 0.8:
            recs.append(f"Preferred strategy: {best.strategy.value} ({best.success_rate:.0%} success)")
        elif best:
            recs.append(f"Best available: {best.strategy.value} ({best.success_rate:.0%} success)")
            recs.append("Consider manual verification after rollback")

        low_perf = [s for s in scores if s.total_attempts > 2 and s.success_rate < 0.5]
        for s in low_perf:
            recs.append(f"Avoid {s.strategy.value} ({s.success_rate:.0%} success in {s.total_attempts} attempts)")

        if not recs:
            recs.append("All strategies performing nominally")
        return recs

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._events]
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
                self._events.append(RollbackEvent(
                    timestamp=d["timestamp"],
                    task_id=d["task_id"],
                    strategy=RollbackStrategy(d["strategy"]),
                    reason=d.get("reason", ""),
                    files_affected=d.get("files_affected", 0),
                    success=d.get("success", False),
                    duration_sec=d.get("duration_sec", 0.0),
                    outcome=RollbackOutcome(d.get("outcome", "failure")),
                    error=d.get("error", ""),
                ))
        except (json.JSONDecodeError, KeyError):
            pass
