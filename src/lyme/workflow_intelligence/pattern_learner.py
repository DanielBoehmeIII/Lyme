"""PatternLearner — discovers common implementation patterns from workflows."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class ImplementationPattern:
    name: str
    description: str
    steps: List[str]
    frequency: int
    success_rate: float
    avg_duration_sec: float
    tags: List[str]
    confidence: float
    last_observed: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description[:80],
            "steps": self.steps[:5],
            "frequency": self.frequency,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_sec": round(self.avg_duration_sec, 1),
            "tags": self.tags[:5],
            "confidence": round(self.confidence, 3),
        }


@dataclass
class PatternLearningReport:
    total_patterns: int
    total_observations: int
    top_patterns: List[ImplementationPattern]
    emerging_patterns: List[ImplementationPattern]
    stable_patterns: List[ImplementationPattern]
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_patterns": self.total_patterns,
            "total_observations": self.total_observations,
            "top_patterns": [p.to_dict() for p in self.top_patterns[:5]],
            "emerging_count": len(self.emerging_patterns),
            "stable_count": len(self.stable_patterns),
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  PATTERN LEARNER REPORT")
        lines.append("=" * 70)
        lines.append(f"  Patterns: {self.total_patterns} | "
                     f"Observations: {self.total_observations}")
        lines.append("")
        lines.append("  Top Patterns:")
        for p in self.top_patterns[:5]:
            bar = "█" * int(p.confidence * 20)
            lines.append(f"    {p.name}: {p.success_rate:.0%} success "
                         f"({p.frequency}x) {bar}")
            lines.append(f"      {' → '.join(p.steps[:4])}")
        if self.emerging_patterns:
            lines.append("")
            lines.append("  Emerging:")
            for p in self.emerging_patterns[:3]:
                lines.append(f"    {p.name} ({p.frequency} observations, "
                             f"{p.success_rate:.0%} success)")
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


class PatternLearner:
    def __init__(self, storage_path: Optional[str] = None):
        self._patterns: List[ImplementationPattern] = []
        self._storage_path = storage_path
        self._load()

    def observe(self, name: str, description: str, steps: List[str],
                success: bool, duration_sec: float, tags: Optional[List[str]] = None) -> None:
        existing = None
        for p in self._patterns:
            if p.name == name:
                existing = p
                break

        if existing:
            existing.frequency += 1
            if success:
                existing.success_rate = (
                    (existing.success_rate * (existing.frequency - 1) + 1) / existing.frequency
                )
            existing.avg_duration_sec = (
                (existing.avg_duration_sec * (existing.frequency - 1) + duration_sec) / existing.frequency
            )
            if tags:
                existing.tags = list(set(existing.tags + tags))
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.last_observed = time.time()
        else:
            self._patterns.append(ImplementationPattern(
                name=name,
                description=description,
                steps=steps,
                frequency=1,
                success_rate=1.0 if success else 0.0,
                avg_duration_sec=duration_sec,
                tags=tags or [],
                confidence=0.3,
                last_observed=time.time(),
            ))
        self._save()

    def analyze(self) -> PatternLearningReport:
        if not self._patterns:
            return PatternLearningReport(
                total_patterns=0, total_observations=0, top_patterns=[],
                emerging_patterns=[], stable_patterns=[],
                insights=["No patterns learned yet"],
                recommendations=["Record more observations to discover patterns"],
            )

        total_obs = sum(p.frequency for p in self._patterns)
        sorted_patterns = sorted(self._patterns, key=lambda p: -p.frequency)

        threshold = time.time() - 86400 * 7
        emerging = [p for p in self._patterns if p.frequency < 5]
        stable = [p for p in self._patterns if p.frequency >= 5 and p.success_rate > 0.7]

        insights: List[str] = []
        if sorted_patterns:
            best = sorted_patterns[0]
            insights.append(f"Most frequent: '{best.name}' ({best.frequency} uses, "
                           f"{best.success_rate:.0%} success)")
        high_sr = [p for p in self._patterns if p.success_rate > 0.9 and p.frequency > 3]
        if high_sr:
            insights.append(f"{len(high_sr)} highly reliable patterns (>90% success)")
        low_sr = [p for p in self._patterns if p.success_rate < 0.5 and p.frequency > 2]
        if low_sr:
            insights.append(f"{len(low_sr)} unreliable patterns — consider revising")
        if emerging:
            insights.append(f"{len(emerging)} emerging patterns being evaluated")

        recommendations: List[str] = []
        if low_sr:
            for p in low_sr[:3]:
                recommendations.append(f"Review '{p.name}' pattern — "
                                      f"{p.success_rate:.0%} success rate needs improvement")
        if not recommendations:
            recommendations.append("All patterns performing well")

        return PatternLearningReport(
            total_patterns=len(self._patterns),
            total_observations=total_obs,
            top_patterns=sorted_patterns[:10],
            emerging_patterns=emerging,
            stable_patterns=stable,
            insights=insights,
            recommendations=recommendations,
        )

    def suggest(self, goal_keywords: List[str]) -> Optional[ImplementationPattern]:
        best = None
        best_score = 0.0
        for p in self._patterns:
            tag_match = sum(1 for kw in goal_keywords if kw in p.tags)
            name_match = sum(1 for kw in goal_keywords if kw in p.name.lower())
            score = tag_match * 0.6 + name_match * 0.4 + p.success_rate * 0.3 + min(p.frequency / 10, 1) * 0.2
            if score > best_score:
                best_score = score
                best = p
        return best if best_score > 0.5 else None

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in self._patterns]
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
                self._patterns.append(ImplementationPattern(**d))
        except (json.JSONDecodeError, KeyError):
            pass
