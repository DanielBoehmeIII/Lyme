"""ConflictResolver — handles contradictory agent outputs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionStrategy(str, Enum):
    MAJORITY_VOTE = "majority_vote"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_RECENT = "most_recent"
    MANUAL = "manual"
    MERGE = "merge"


@dataclass
class Conflict:
    id: str
    topic: str
    descriptions: List[str]
    sources: List[str]
    confidences: List[float]
    severity: ConflictSeverity
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "topic": self.topic[:60],
            "source_count": len(self.sources),
            "severity": self.severity.value,
            "resolved": self.resolution is not None,
        }


@dataclass
class ConflictResolutionResult:
    conflict: Conflict
    resolution: str
    confidence: float
    strategy_used: ResolutionStrategy
    explanation: str

    def to_dict(self) -> Dict:
        return {
            "topic": self.conflict.topic[:60],
            "resolution": self.resolution[:80],
            "confidence": round(self.confidence, 3),
            "strategy": self.strategy_used.value,
            "explanation": self.explanation[:100],
        }


@dataclass
class ConflictResolverReport:
    total_conflicts: int
    resolved: int
    unresolved: int
    by_severity: Dict[str, int]
    by_strategy: Dict[str, int]
    insights: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  CONFLICT RESOLVER REPORT")
        lines.append("=" * 70)
        lines.append(f"  Conflicts: {self.total_conflicts} | "
                     f"Resolved: {self.resolved} | "
                     f"Unresolved: {self.unresolved}")
        lines.append("")
        lines.append("  By Severity:")
        for sev, count in sorted(self.by_severity.items(), key=lambda x: -x[1]):
            lines.append(f"    {sev}: {count}")
        lines.append("")
        lines.append("  By Strategy:")
        for strat, count in sorted(self.by_strategy.items(), key=lambda x: -x[1]):
            lines.append(f"    {strat}: {count}")
        if self.insights:
            lines.append("-" * 70)
            for ins in self.insights:
                lines.append(f"  • {ins}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ConflictResolver:
    def __init__(self):
        self._conflicts: List[Conflict] = []
        self._resolutions: List[ConflictResolutionResult] = []
        self._custom_resolvers: Dict[str, Callable] = {}

    def register_resolver(self, topic: str, resolver_fn: Callable) -> None:
        self._custom_resolvers[topic] = resolver_fn

    def detect(self, topic: str, statements: List[Dict]) -> Optional[Conflict]:
        if len(statements) < 2:
            return None

        descriptions = [s.get("statement", "") for s in statements]
        sources = [s.get("source", "unknown") for s in statements]
        confidences = [s.get("confidence", 0.5) for s in statements]

        unique_opinions = set(d.lower().strip() for d in descriptions if d)
        if len(unique_opinions) <= 1:
            return None

        max_conf = max(confidences) if confidences else 0
        min_conf = min(confidences) if confidences else 0
        spread = max_conf - min_conf

        if spread > 0.5:
            severity = ConflictSeverity.HIGH
        elif max_conf > 0.8 and any(c < 0.3 for c in confidences):
            severity = ConflictSeverity.MEDIUM
        else:
            severity = ConflictSeverity.LOW

        conflict = Conflict(
            id=f"conflict-{len(self._conflicts)}",
            topic=topic,
            descriptions=descriptions,
            sources=sources,
            confidences=confidences,
            severity=severity,
        )
        self._conflicts.append(conflict)
        return conflict

    def resolve(self, conflict: Conflict,
                preferred_strategy: Optional[ResolutionStrategy] = None) -> ConflictResolutionResult:
        if conflict.topic in self._custom_resolvers:
            result = self._custom_resolvers[conflict.topic](conflict)
            if result:
                return result

        strategy = preferred_strategy or self._choose_strategy(conflict)

        if strategy == ResolutionStrategy.MAJORITY_VOTE:
            opinion_counts: Dict[str, int] = {}
            for desc in conflict.descriptions:
                key = desc.lower().strip()
                opinion_counts[key] = opinion_counts.get(key, 0) + 1
            max_count = max(opinion_counts.values()) if opinion_counts else 0
            winners = [k for k, v in opinion_counts.items() if v == max_count]
            resolution = winners[0] if winners else conflict.descriptions[0]
            confidence = max_count / max(len(conflict.descriptions), 1)
            explanation = f"Majority vote: {max_count}/{len(conflict.descriptions)} agreed"

        elif strategy == ResolutionStrategy.HIGHEST_CONFIDENCE:
            max_idx = max(range(len(conflict.confidences)),
                          key=lambda i: conflict.confidences[i])
            resolution = conflict.descriptions[max_idx]
            confidence = conflict.confidences[max_idx]
            explanation = f"Highest confidence ({confidence:.0%}): {conflict.sources[max_idx]}"

        elif strategy == ResolutionStrategy.MOST_RECENT:
            resolution = conflict.descriptions[-1]
            confidence = conflict.confidences[-1] if conflict.confidences else 0.5
            explanation = "Most recent statement accepted"

        elif strategy == ResolutionStrategy.MERGE:
            parts = []
            for desc, src in zip(conflict.descriptions, conflict.sources):
                parts.append(f"[{src}] {desc}")
            resolution = " | ".join(parts)
            confidence = max(conflict.confidences) if conflict.confidences else 0.5
            explanation = "Merged statements from all sources"

        else:
            resolution = conflict.descriptions[0]
            confidence = 0.5
            explanation = "Default: first statement accepted"

        conflict.resolution = resolution
        conflict.resolved_by = strategy.value

        result = ConflictResolutionResult(
            conflict=conflict,
            resolution=resolution,
            confidence=confidence,
            strategy_used=strategy,
            explanation=explanation,
        )
        self._resolutions.append(result)
        return result

    def _choose_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        high_conf = sum(1 for c in conflict.confidences if c > 0.7)
        if high_conf >= 2:
            return ResolutionStrategy.HIGHEST_CONFIDENCE
        if len(conflict.descriptions) >= 3:
            return ResolutionStrategy.MAJORITY_VOTE
        return ResolutionStrategy.MERGE

    def resolve_all(self) -> List[ConflictResolutionResult]:
        results = []
        for conflict in self._conflicts:
            if conflict.resolution is None:
                results.append(self.resolve(conflict))
        return results

    def report(self) -> ConflictResolverReport:
        resolved = sum(1 for c in self._conflicts if c.resolution is not None)
        by_severity: Dict[str, int] = {}
        by_strategy: Dict[str, int] = {}
        for c in self._conflicts:
            by_severity[c.severity.value] = by_severity.get(c.severity.value, 0) + 1
        for r in self._resolutions:
            by_strategy[r.strategy_used.value] = by_strategy.get(r.strategy_used.value, 0) + 1

        insights: List[str] = []
        if resolved > 0:
            insights.append(f"Resolved {resolved}/{len(self._conflicts)} conflicts")
        if by_severity.get("critical", 0) > 0:
            insights.append(f"{by_severity['critical']} critical conflicts required resolution")
        if by_strategy.get("majority_vote", 0) > by_strategy.get("manual", 0):
            insights.append("Majority vote is the most effective automated strategy")

        return ConflictResolverReport(
            total_conflicts=len(self._conflicts),
            resolved=resolved,
            unresolved=len(self._conflicts) - resolved,
            by_severity=by_severity,
            by_strategy=by_strategy,
            insights=insights,
        )
