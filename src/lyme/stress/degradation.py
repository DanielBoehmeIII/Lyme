from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics


@dataclass
class DegradationPoint:
    level: int = 0
    metric_name: str = ""
    value: float = 0.0
    delta_from_baseline: float = 0.0
    delta_pct: float = 0.0

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "metric_name": self.metric_name,
            "value": self.value,
            "delta_from_baseline": self.delta_from_baseline,
            "delta_pct": self.delta_pct,
        }


@dataclass
class DegradationCurve:
    metric_name: str = ""
    baseline_value: float = 0.0
    points: List[DegradationPoint] = field(default_factory=list)
    collapse_point: Optional[int] = None
    collapse_threshold: float = 0.5
    nonlinearity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "points": [p.to_dict() for p in self.points],
            "collapse_point": self.collapse_point,
            "collapse_threshold": self.collapse_threshold,
            "nonlinearity_score": self.nonlinearity_score,
        }


class ContextDegradationAnalyzer:
    def __init__(self):
        self._curves: Dict[str, DegradationCurve] = {}

    def add_measurement(self, metric_name: str, level: int, value: float,
                        baseline: float = 0):
        if metric_name not in self._curves:
            self._curves[metric_name] = DegradationCurve(
                metric_name=metric_name,
                baseline_value=baseline if baseline > 0 else value,
            )

        curve = self._curves[metric_name]
        baseline_val = baseline if baseline > 0 else curve.baseline_value

        point = DegradationPoint(
            level=level,
            metric_name=metric_name,
            value=value,
            delta_from_baseline=value - baseline_val,
            delta_pct=(
                (value - baseline_val) / baseline_val * 100
                if baseline_val > 0 else 0
            ),
        )
        curve.points.append(point)
        curve.points.sort(key=lambda p: p.level)

    def compute_collapse_point(self, metric_name: str,
                               threshold: float = 0.5) -> Optional[int]:
        curve = self._curves.get(metric_name)
        if not curve or len(curve.points) < 2:
            return None

        baseline = curve.baseline_value
        if baseline == 0:
            return None

        for point in sorted(curve.points, key=lambda p: p.level):
            ratio = abs(point.value / baseline - 1) if baseline > 0 else abs(point.value)
            if ratio > threshold:
                curve.collapse_point = point.level
                curve.collapse_threshold = threshold
                return point.level

        return None

    def compute_nonlinearity(self, metric_name: str) -> float:
        curve = self._curves.get(metric_name)
        if not curve or len(curve.points) < 3:
            return 0.0

        sorted_points = sorted(curve.points, key=lambda p: p.level)
        deltas = [abs(p.delta_pct) for p in sorted_points]
        if not deltas:
            return 0.0

        mean_delta = statistics.mean(deltas)
        if mean_delta == 0:
            return 0.0

        variance = statistics.variance(deltas) if len(deltas) > 1 else 0
        # High variance = nonlinear degradation
        curve.nonlinearity_score = min(1.0, variance / (mean_delta * 10 + 1))
        return curve.nonlinearity_score

    def get_curve(self, metric_name: str) -> Optional[DegradationCurve]:
        return self._curves.get(metric_name)

    def all_curves(self) -> Dict[str, DegradationCurve]:
        return self._curves

    def degradation_summary(self) -> dict:
        summary = {}
        for name, curve in self._curves.items():
            summary[name] = {
                "baseline": curve.baseline_value,
                "measurement_count": len(curve.points),
                "max_level": max(p.level for p in curve.points) if curve.points else 0,
                "max_delta_pct": max(abs(p.delta_pct) for p in curve.points) if curve.points else 0,
                "collapse_point": curve.collapse_point,
                "nonlinearity": curve.nonlinearity_score,
                "collapsed": curve.collapse_point is not None,
            }
        return summary

    def identify_bottlenecks(self) -> List[dict]:
        bottlenecks = []
        for name, curve in self._curves.items():
            if curve.collapse_point is not None and curve.collapse_point <= 5:
                bottlenecks.append({
                    "metric": name,
                    "collapse_level": curve.collapse_point,
                    "nonlinearity": curve.nonlinearity_score,
                    "type": "memory" if "memory" in name.lower() or "context" in name.lower()
                            else "planning" if "plan" in name.lower()
                            else "tool" if "tool" in name.lower()
                            else "reasoning",
                })

        bottlenecks.sort(key=lambda b: (b["collapse_level"], -b["nonlinearity"]))
        return bottlenecks

    def scaling_law_estimate(self, metric_name: str) -> dict:
        curve = self._curves.get(metric_name)
        if not curve or len(curve.points) < 3:
            return {"reliable": False}

        sorted_pts = sorted(curve.points, key=lambda p: p.level)
        x = [p.level for p in sorted_pts]
        y = [p.value for p in sorted_pts]

        try:
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_xx = sum(xi * xi for xi in x)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
            intercept = (sum_y - slope * sum_x) / n if n > 0 else 0

            collapse = self.compute_collapse_point(metric_name)
            return {
                "reliable": True,
                "slope": slope,
                "intercept": intercept,
                "trend": "degrading" if slope < 0 else "improving" if slope > 0 else "stable",
                "collapse_point": collapse,
                "nonlinearity": self.compute_nonlinearity(metric_name),
            }
        except Exception:
            return {"reliable": False}
