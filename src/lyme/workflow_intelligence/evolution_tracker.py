"""ArchitectureEvolutionTracker — learns how architectures evolve over time."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class ArchitectureSnapshot:
    timestamp: float
    module_count: int
    abstraction_ratio: float
    coupling_score: float
    test_ratio: float
    major_layers: List[str]
    framework_versions: Dict[str, str]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "module_count": self.module_count,
            "abstraction_ratio": round(self.abstraction_ratio, 3),
            "coupling_score": round(self.coupling_score, 3),
            "test_ratio": round(self.test_ratio, 3),
            "major_layers": self.major_layers[:5],
            "framework_versions": dict(list(self.framework_versions.items())[:5]),
        }


@dataclass
class EvolutionTrend:
    metric: str
    slope: float
    direction: str
    description: str
    significance: float

    def to_dict(self) -> Dict:
        return {
            "metric": self.metric,
            "slope": round(self.slope, 4),
            "direction": self.direction,
            "description": self.description[:80],
            "significance": round(self.significance, 3),
        }


@dataclass
class EvolutionTrackerReport:
    total_snapshots: int
    trends: List[EvolutionTrend]
    current_profile: Optional[Dict]
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_snapshots": self.total_snapshots,
            "trends": [t.to_dict() for t in self.trends],
            "current_profile": self.current_profile,
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  ARCHITECTURE EVOLUTION TRACKER")
        lines.append("=" * 70)
        lines.append(f"  Snapshots: {self.total_snapshots}")
        lines.append("")
        lines.append("  Trends:")
        for t in self.trends:
            arrow = {"increasing": "↑", "decreasing": "↓", "stable": "→"}
            lines.append(f"    {arrow.get(t.direction, '•')} {t.metric}: {t.description[:60]}")
        if self.current_profile:
            lines.append("")
            lines.append("  Current Profile:")
            for k, v in self.current_profile.items():
                if isinstance(v, float):
                    lines.append(f"    {k}: {v:.3f}")
                else:
                    lines.append(f"    {k}: {v}")
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


class ArchitectureEvolutionTracker:
    def __init__(self, storage_path: Optional[str] = None):
        self._snapshots: List[ArchitectureSnapshot] = []
        self._storage_path = storage_path
        self._load()

    def record(self, module_count: int, abstraction_ratio: float,
               coupling_score: float, test_ratio: float,
               major_layers: List[str],
               framework_versions: Optional[Dict[str, str]] = None) -> None:
        self._snapshots.append(ArchitectureSnapshot(
            timestamp=time.time(),
            module_count=module_count,
            abstraction_ratio=abstraction_ratio,
            coupling_score=coupling_score,
            test_ratio=test_ratio,
            major_layers=major_layers,
            framework_versions=framework_versions or {},
        ))
        self._save()

    def analyze(self) -> EvolutionTrackerReport:
        if not self._snapshots:
            return EvolutionTrackerReport(
                total_snapshots=0, trends=[], current_profile=None,
                insights=["No architecture snapshots yet"],
                recommendations=["Start recording snapshots to track evolution"],
            )

        trends = self._compute_trends()
        current = self._snapshots[-1]

        insights: List[str] = []
        for t in trends:
            if t.direction == "increasing" and t.significance > 0.5:
                insights.append(f"{t.metric} is {t.direction}: {t.description}")
            elif t.direction == "decreasing" and t.significance > 0.5:
                insights.append(f"{t.metric} is {t.direction}: {t.description}")

        if current.test_ratio < 0.3:
            insights.append("Low test coverage — high regression risk")
        if current.abstraction_ratio > 0.5:
            insights.append("High abstraction level — consider if all abstractions pull their weight")
        if current.coupling_score > 0.5:
            insights.append("High coupling — consider dependency inversion")

        recommendations: List[str] = []
        decreasing_tests = [t for t in trends if t.metric == "test_ratio" and t.direction == "decreasing"]
        if decreasing_tests:
            recommendations.append("Test coverage is declining — reverse trend")
        increasing_coupling = [t for t in trends if t.metric == "coupling_score" and t.direction == "increasing"]
        if increasing_coupling:
            recommendations.append("Coupling is increasing — apply dependency inversion")
        if not recommendations:
            recommendations.append("Architecture evolution is healthy")

        return EvolutionTrackerReport(
            total_snapshots=len(self._snapshots),
            trends=trends,
            current_profile={
                "module_count": current.module_count,
                "abstraction_ratio": round(current.abstraction_ratio, 3),
                "coupling_score": round(current.coupling_score, 3),
                "test_ratio": round(current.test_ratio, 3),
                "layers": current.major_layers,
            },
            insights=insights,
            recommendations=recommendations,
        )

    def _compute_trends(self) -> List[EvolutionTrend]:
        if len(self._snapshots) < 2:
            return []

        metrics = ["module_count", "abstraction_ratio", "coupling_score", "test_ratio"]
        trends: List[EvolutionTrend] = []
        ts = [s.timestamp for s in self._snapshots]

        for metric in metrics:
            values = [getattr(s, metric) for s in self._snapshots]
            slope = self._linear_regression_slope(ts, values)
            norm_slope = slope / max(abs(max(values) - min(values)), 0.01) if values else 0
            direction = "increasing" if norm_slope > 0.05 else ("decreasing" if norm_slope < -0.05 else "stable")
            trends.append(EvolutionTrend(
                metric=metric,
                slope=slope,
                direction=direction,
                description=f"{metric} trending {direction}",
                significance=min(1.0, abs(norm_slope)),
            ))
        return trends

    def _linear_regression_slope(self, x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [s.to_dict() for s in self._snapshots]
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
                self._snapshots.append(ArchitectureSnapshot(**d))
        except (json.JSONDecodeError, KeyError):
            pass
