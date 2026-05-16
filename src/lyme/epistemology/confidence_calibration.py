from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import uuid
import time
import math


@dataclass
class CalibrationPoint:
    predicted_confidence: float
    actual_correctness: bool
    domain: str = ""
    timestamp: float = 0.0
    verification_method: str = ""
    user_corrected: bool = False

    def to_dict(self) -> Dict:
        return {
            "predicted_confidence": self.predicted_confidence,
            "actual_correctness": self.actual_correctness,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "verification_method": self.verification_method,
            "user_corrected": self.user_corrected,
        }


@dataclass
class CalibrationBin:
    bin_min: float
    bin_max: float
    points: List[CalibrationPoint]
    avg_predicted: float = 0.0
    actual_accuracy: float = 0.0
    count: int = 0
    error: float = 0.0

    def compute(self):
        if not self.points:
            return
        self.count = len(self.points)
        self.avg_predicted = sum(p.predicted_confidence for p in self.points) / self.count
        self.actual_accuracy = sum(1 for p in self.points if p.actual_correctness) / self.count
        self.error = abs(self.avg_predicted - self.actual_accuracy)

    def to_dict(self) -> Dict:
        return {
            "bin_min": self.bin_min,
            "bin_max": self.bin_max,
            "avg_predicted": round(self.avg_predicted, 3),
            "actual_accuracy": round(self.actual_accuracy, 3),
            "count": self.count,
            "error": round(self.error, 3),
        }


@dataclass
class CalibrationCurve:
    bins: List[CalibrationBin]
    n_bins: int = 10
    total_points: int = 0
    ece: float = 0.0
    mce: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "bins": [b.to_dict() for b in self.bins],
            "n_bins": self.n_bins,
            "total_points": self.total_points,
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
        }


@dataclass
class CalibrationReport:
    report_id: str
    timestamp: float
    curve: CalibrationCurve
    metrics: Dict
    recommendations: List[str]
    trend: str = "stable"

    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "curve": self.curve.to_dict(),
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "trend": self.trend,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Confidence Calibration Report")
        lines.append(f"")
        lines.append(f"**ECE (Expected Calibration Error)**: {self.curve.ece:.4f}")
        lines.append(f"**MCE (Max Calibration Error)**: {self.curve.mce:.4f}")
        lines.append(f"**Total Points**: {self.curve.total_points}")
        lines.append(f"**Trend**: {self.trend}")
        lines.append(f"")
        lines.append(f"## Calibration Curve")
        lines.append(f"")
        lines.append(f"| Bin | Range | Count | Avg Predicted | Actual Accuracy | Error |")
        lines.append(f"|-----|-------|-------|---------------|-----------------|-------|")
        for b in self.curve.bins:
            marker = " ✓" if b.error < 0.1 else " ⚠" if b.error < 0.2 else " ✗"
            lines.append(f"| {b.bin_min:.1f}-{b.bin_max:.1f} | [{b.bin_min:.1f}, {b.bin_max:.1f}] | {b.count} | {b.avg_predicted:.3f} | {b.actual_accuracy:.3f} | {b.error:.3f}{marker} |")
        lines.append(f"")
        lines.append(f"## Metrics")
        for k, v in self.metrics.items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
        lines.append(f"")
        if self.recommendations:
            lines.append(f"## Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)


class OverconfidenceDetector:
    def __init__(self, high_threshold: float = 0.8, low_threshold: float = 0.3):
        self.high = high_threshold
        self.low = low_threshold

    def check(self, points: List[CalibrationPoint]) -> List[Dict]:
        overconfident = []
        for p in points:
            if p.predicted_confidence >= self.high and not p.actual_correctness:
                overconfident.append({
                    "point": p,
                    "gap": p.predicted_confidence - 0.0,
                    "severity": "critical" if p.predicted_confidence > 0.95 else "high",
                })
            elif p.predicted_confidence <= self.low and p.actual_correctness:
                overconfident.append({
                    "point": p,
                    "gap": 0.0 - p.predicted_confidence,
                    "severity": "medium",
                    "type": "underconfidence",
                })
        return overconfident

    def compute_overconfidence_rate(self, points: List[CalibrationPoint]) -> float:
        high_conf_points = [p for p in points if p.predicted_confidence >= self.high]
        if not high_conf_points:
            return 0.0
        wrong = sum(1 for p in high_conf_points if not p.actual_correctness)
        return wrong / len(high_conf_points)


class ConfidenceCalibrator:
    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self._points: List[CalibrationPoint] = []
        self._overconfidence = OverconfidenceDetector()
        self._history: List[CalibrationReport] = []

    def record(self, predicted: float, actual: bool, domain: str = "", method: str = "", user_corrected: bool = False):
        self._points.append(CalibrationPoint(
            predicted_confidence=predicted,
            actual_correctness=actual,
            domain=domain,
            timestamp=time.time(),
            verification_method=method,
            user_corrected=user_corrected,
        ))

    def compute_curve(self, points: Optional[List[CalibrationPoint]] = None) -> CalibrationCurve:
        pts = points if points is not None else self._points
        if not pts:
            return CalibrationCurve(bins=[], total_points=0, ece=0.0, mce=0.0)

        bin_edges = [i / self.n_bins for i in range(self.n_bins + 1)]
        bins: List[CalibrationBin] = []

        for i in range(self.n_bins):
            bmin = bin_edges[i]
            bmax = bin_edges[i + 1]
            if i == self.n_bins - 1:
                bmax = 1.01
            bin_points = [p for p in pts if bmin <= p.predicted_confidence < bmax]
            cb = CalibrationBin(bin_min=bmin, bin_max=bin_edges[i + 1], points=bin_points)
            cb.compute()
            bins.append(cb)

        total = len(pts)
        ece = sum(b.error * (b.count / total) for b in bins if b.count > 0)
        mce = max((b.error for b in bins if b.count > 0), default=0.0)

        return CalibrationCurve(bins=bins, n_bins=self.n_bins, total_points=total, ece=ece, mce=mce)

    def calibrate_confidence(self, raw_confidence: float, domain: str = "") -> float:
        domain_points = [p for p in self._points if p.domain == domain] if domain else self._points
        if not domain_points:
            return raw_confidence

        curve = self.compute_curve(domain_points)
        bin_idx = min(int(raw_confidence * self.n_bins), self.n_bins - 1)
        if bin_idx >= len(curve.bins):
            return raw_confidence

        bin_data = curve.bins[bin_idx]
        if bin_data.count < 3:
            return raw_confidence

        if bin_data.actual_accuracy < raw_confidence:
            adjustment = raw_confidence - bin_data.actual_accuracy
            return max(0.0, raw_confidence - adjustment * 0.5)
        elif bin_data.actual_accuracy > raw_confidence:
            adjustment = bin_data.actual_accuracy - raw_confidence
            return min(1.0, raw_confidence + adjustment * 0.3)

        return raw_confidence

    def detect_overconfidence(self, min_points: int = 10) -> List[Dict]:
        if len(self._points) < min_points:
            return []
        return self._overconfidence.check(self._points)

    def generate_report(self) -> CalibrationReport:
        curve = self.compute_curve()
        overconfident = self.detect_overconfidence()
        domain_breakdown = self._domain_breakdown()

        metrics = {
            "ece": round(curve.ece, 4),
            "mce": round(curve.mce, 4),
            "total_points": curve.total_points,
            "overconfidence_cases": len([d for d in overconfident if d.get("type") != "underconfidence"]),
            "underconfidence_cases": len([d for d in overconfident if d.get("type") == "underconfidence"]),
            "overconfidence_rate": round(self._overconfidence.compute_overconfidence_rate(self._points), 3),
            "accuracy": self._compute_accuracy(),
            "avg_confidence": self._avg_confidence(),
            "domain_count": len(domain_breakdown),
        }

        recommendations = self._generate_recommendations(curve, metrics, overconfident)

        if len(self._history) >= 2:
            prev_ece = self._history[-1].curve.ece
            trend = "improving" if curve.ece < prev_ece else "declining" if curve.ece > prev_ece else "stable"
        else:
            trend = "stable"

        report = CalibrationReport(
            report_id=f"cr_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            curve=curve,
            metrics=metrics,
            recommendations=recommendations,
            trend=trend,
        )
        self._history.append(report)
        return report

    def _domain_breakdown(self) -> Dict[str, Dict]:
        domains: Dict[str, List[CalibrationPoint]] = {}
        for p in self._points:
            if p.domain not in domains:
                domains[p.domain] = []
            domains[p.domain].append(p)

        breakdown = {}
        for domain, points in domains.items():
            accuracy = sum(1 for p in points if p.actual_correctness) / len(points)
            avg_conf = sum(p.predicted_confidence for p in points) / len(points)
            breakdown[domain] = {
                "count": len(points),
                "accuracy": round(accuracy, 3),
                "avg_confidence": round(avg_conf, 3),
                "calibration_error": round(abs(avg_conf - accuracy), 3),
            }
        return breakdown

    def _compute_accuracy(self) -> float:
        if not self._points:
            return 0.0
        return sum(1 for p in self._points if p.actual_correctness) / len(self._points)

    def _avg_confidence(self) -> float:
        if not self._points:
            return 0.0
        return sum(p.predicted_confidence for p in self._points) / len(self._points)

    def _generate_recommendations(self, curve: CalibrationCurve, metrics: Dict, overconfident: List[Dict]) -> List[str]:
        recs = []
        if curve.ece > 0.2:
            recs.append("CRITICAL: Expected Calibration Error is very high ({:.2f}). Implement systematic confidence correction.".format(curve.ece))
        elif curve.ece > 0.1:
            recs.append("WARNING: ECE is {:.2f}. Apply calibration adjustments to improve reliability.".format(curve.ece))

        if metrics.get("overconfidence_rate", 0) > 0.3:
            recs.append("Overconfidence rate is {:.0%}. Apply stronger penalties for high-confidence predictions.".format(metrics["overconfidence_rate"]))

        low_bins = [b for b in curve.bins if b.count >= 3 and b.error > 0.15]
        for b in low_bins[:3]:
            direction = "overconfident" if b.avg_predicted > b.actual_accuracy else "underconfident"
            recs.append(f"Bin [{b.bin_min:.1f}-{b.bin_max:.1f}]: {direction} by {b.error:.0%}. Adjust confidence in this range.")

        if metrics.get("total_points", 0) < 30:
            recs.append(f"Only {metrics['total_points']} calibration points. Gather more data for reliable calibration.")

        if not recs:
            recs.append("Calibration is within acceptable range. Continue monitoring.")

        return recs

    def recent_trend(self, window: int = 50) -> Dict:
        if len(self._points) < window * 2:
            return {"error": "insufficient data for trend analysis"}

        recent = self._points[-window:]
        older = self._points[:-window]

        recent_curve = self.compute_curve(recent)
        older_curve = self.compute_curve(older)

        return {
            "recent_ece": recent_curve.ece,
            "older_ece": older_curve.ece,
            "change": older_curve.ece - recent_curve.ece,
            "improving": recent_curve.ece < older_curve.ece,
        }

    @property
    def points(self) -> List[CalibrationPoint]:
        return self._points

    @property
    def history(self) -> List[CalibrationReport]:
        return self._history
