from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import time
import math


@dataclass
class TrendPoint:
    timestamp: float
    value: float
    label: str = ""

    def to_dict(self) -> Dict:
        return {"timestamp": self.timestamp, "value": self.value, "label": self.label}


@dataclass
class TrendLine:
    dimension: str
    points: List[TrendPoint]
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0
    improving: Optional[bool] = None
    significant: bool = False

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension,
            "points": [p.to_dict() for p in self.points],
            "slope": self.slope,
            "intercept": self.intercept,
            "r_squared": self.r_squared,
            "improving": self.improving,
            "significant": self.significant,
        }

    def to_markdown(self) -> str:
        icon = "📈" if self.improving else "📉" if self.improving is False else "➡️"
        sig = "✅" if self.significant else "⚠️"
        lines = []
        lines.append(f"### {icon} {self.dimension}")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Slope | {self.slope:.4f} |")
        lines.append(f"| R² | {self.r_squared:.4f} |")
        lines.append(f"| Improving | {self.improving} |")
        lines.append(f"| Significant | {sig} |")
        if self.points:
            first = self.points[0].value
            last = self.points[-1].value
            change = last - first
            pct = (change / max(first, 0.001)) * 100
            lines.append(f"| Change | {change:+.3f} ({pct:+.1f}%) |")
        return "\n".join(lines)


@dataclass
class RegressionPoint:
    timestamp: float
    dimension: str
    before_value: float
    after_value: float
    delta: float
    severity: str = "minor"
    suspected_cause: str = ""

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "dimension": self.dimension,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "delta": self.delta,
            "severity": self.severity,
            "suspected_cause": self.suspected_cause,
        }


@dataclass
class EvaluationWindow:
    start_time: float
    end_time: float
    scores: Dict[str, float] = field(default_factory=dict)
    num_actions: int = 0
    intervention_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "scores": self.scores,
            "num_actions": self.num_actions,
            "intervention_count": self.intervention_count,
        }


@dataclass
class LongitudinalReport:
    windows: List[EvaluationWindow] = field(default_factory=list)
    trends: List[TrendLine] = field(default_factory=list)
    regressions: List[RegressionPoint] = field(default_factory=list)
    overall_trend: str = "stable"
    recent_score: float = 0.0
    baseline_score: float = 0.0
    improvement_pct: float = 0.0
    regression_count: int = 0
    recommendation: str = ""

    def to_dict(self) -> Dict:
        return {
            "windows": [w.to_dict() for w in self.windows],
            "trends": [t.to_dict() for t in self.trends],
            "regressions": [r.to_dict() for r in self.regressions],
            "overall_trend": self.overall_trend,
            "recent_score": self.recent_score,
            "baseline_score": self.baseline_score,
            "improvement_pct": self.improvement_pct,
            "regression_count": self.regression_count,
            "recommendation": self.recommendation,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append("# Longitudinal Evaluation Report")
        lines.append(f"")
        trend_icons = {"improving": "📈", "stable": "➡️", "declining": "📉", "volatile": "🎢"}
        lines.append(f"**Overall Trend**: {trend_icons.get(self.overall_trend, '❓')} {self.overall_trend.upper()}")
        lines.append(f"**Baseline Score**: {self.baseline_score:.3f}")
        lines.append(f"**Recent Score**: {self.recent_score:.3f}")
        lines.append(f"**Improvement**: {self.improvement_pct:+.1f}%")
        lines.append(f"**Regressions Detected**: {self.regression_count}")
        lines.append(f"")
        lines.append(f"## Dimension Trends")
        for trend in self.trends:
            lines.append("")
            lines.append(trend.to_markdown())
        lines.append(f"")
        if self.regressions:
            lines.append(f"## Regressions")
            for r in self.regressions:
                icon = "🔴" if r.severity == "critical" else "🟠" if r.severity == "major" else "🟡"
                lines.append(f"{icon} **{r.dimension}**: {r.before_value:.3f} → {r.after_value:.3f} ({r.delta:+.3f})")
                if r.suspected_cause:
                    lines.append(f"   Cause: {r.suspected_cause}")
        lines.append(f"")
        lines.append(f"## Recommendation")
        lines.append(self.recommendation)
        return "\n".join(lines)


class LongitudinalEvaluation:
    def __init__(self, storage_path: Optional[Path] = None):
        self._windows: List[EvaluationWindow] = []
        self._benchmark_history: List[Dict] = []
        self._storage_path = storage_path
        self._load()

    def add_benchmark_run(self, run_data: Dict) -> None:
        self._benchmark_history.append({
            "timestamp": run_data.get("timestamp", time.time()),
            "scores": run_data.get("scores", {}),
            "overall": run_data.get("overall_score", 0.0),
        })
        self._save()

    def add_window(self, window: EvaluationWindow) -> None:
        self._windows.append(window)
        self._save()

    def get_report(self) -> LongitudinalReport:
        if not self._benchmark_history:
            return self._empty_report()

        dimensions = set()
        for run in self._benchmark_history:
            if isinstance(run.get("scores"), dict):
                dimensions.update(run["scores"].keys())
            elif isinstance(run.get("scores"), list):
                for s in run["scores"]:
                    if isinstance(s, dict) and "dimension" in s:
                        dimensions.add(s["dimension"])

        trends = []
        regressions: List[RegressionPoint] = []

        for dim in sorted(dimensions):
            points = []
            for run in self._benchmark_history:
                ts = run["timestamp"]
                scores_data = run.get("scores", {})
                if isinstance(scores_data, list):
                    val = None
                    for s in scores_data:
                        if isinstance(s, dict) and s.get("dimension") == dim:
                            val = s.get("score")
                            break
                else:
                    val = scores_data.get(dim)

                if val is not None:
                    points.append(TrendPoint(timestamp=ts, value=val))

            if len(points) >= 2:
                trend = self._compute_trend(dim, points)
                trends.append(trend)

                for i in range(1, len(points)):
                    if points[i].value < points[i - 1].value - 0.1:
                        delta = points[i].value - points[i - 1].value
                        severity = "critical" if abs(delta) > 0.3 else "major" if abs(delta) > 0.2 else "minor"
                        regressions.append(RegressionPoint(
                            timestamp=points[i].timestamp,
                            dimension=dim,
                            before_value=points[i - 1].value,
                            after_value=points[i].value,
                            delta=delta,
                            severity=severity,
                            suspected_cause="Automated detection — investigate dimension",
                        ))

        overall_trend = "stable"
        improving_dims = sum(1 for t in trends if t.improving is True)
        declining_dims = sum(1 for t in trends if t.improving is False)
        if improving_dims > declining_dims * 2:
            overall_trend = "improving"
        elif declining_dims > improving_dims * 2:
            overall_trend = "declining"
        elif len(regressions) > len(self._benchmark_history) * 0.3:
            overall_trend = "volatile"

        scores_list = [run.get("overall", 0.0) for run in self._benchmark_history]
        baseline = scores_list[0] if scores_list else 0.0
        recent = scores_list[-1] if scores_list else 0.0
        improvement = ((recent - baseline) / max(baseline, 0.001)) * 100

        if overall_trend == "declining":
            rec = "Investigate declining dimensions. Consider rolling back recent changes that correlate with drops."
        elif overall_trend == "volatile":
            rec = "High variance detected. Stabilize verification pipeline and reduce concurrent changes."
        elif regressions:
            rec = f"Address {len(regressions)} regression(s). Focus on declining dimensions."
        elif overall_trend == "improving":
            rec = "Lyme is improving. Continue current trajectory and monitor for plateaus."
        else:
            rec = "Performance is stable. Consider running stress tests to find improvement opportunities."

        return LongitudinalReport(
            windows=self._windows,
            trends=trends,
            regressions=regressions,
            overall_trend=overall_trend,
            recent_score=recent,
            baseline_score=baseline,
            improvement_pct=round(improvement, 1),
            regression_count=len(regressions),
            recommendation=rec,
        )

    def _compute_trend(self, dimension: str, points: List[TrendPoint]) -> TrendLine:
        n = len(points)
        if n < 2:
            return TrendLine(dimension=dimension, points=points)

        xs = [(p.timestamp - points[0].timestamp) / 86400.0 for p in points]
        ys = [p.value for p in points]

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)

        slope = num / den if den != 0 else 0.0
        intercept = mean_y - slope * mean_x

        if den != 0 and n > 2:
            y_pred = [slope * x + intercept for x in xs]
            ss_res = sum((y - yp) ** 2 for y, yp in zip(ys, y_pred))
            ss_tot = sum((y - mean_y) ** 2 for y in ys)
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        else:
            r_squared = 0.0

        improving = None
        if abs(slope) > 0.001:
            improving = slope > 0

        significant = r_squared > 0.5 and abs(slope) > 0.005

        return TrendLine(
            dimension=dimension,
            points=points,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            improving=improving,
            significant=significant,
        )

    def _empty_report(self) -> LongitudinalReport:
        return LongitudinalReport(
            recommendation="No benchmark data available. Run 'lyme self-benchmark' first.",
        )

    def _save(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "windows": [w.to_dict() for w in self._windows],
            "benchmark_history": self._benchmark_history,
        }
        self._storage_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text())
            self._windows = [EvaluationWindow(**w) for w in data.get("windows", [])]
            self._benchmark_history = data.get("benchmark_history", [])
        except (json.JSONDecodeError, KeyError):
            pass
