"""Week 119 — Confidence Calibration for Lyme Model.

Calibrates Lyme Model confidence using:
- predicted success vs actual success
- verification outcome
- user correction
- hallucination occurrence
- patch acceptance
- test pass/fail

Produces calibration curves, overconfidence/underconfidence reports, per-task model.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import time
import math
import uuid


@dataclass
class CalibrationPoint:
    domain: str
    task_type: str
    predicted_confidence: float
    actual_success: bool
    verification_passed: Optional[bool] = None
    user_corrected: bool = False
    hallucination_detected: bool = False
    patch_accepted: Optional[bool] = None
    test_pass_rate: Optional[float] = None
    mode_used: str = "local_fast"
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "task_type": self.task_type,
            "predicted_confidence": self.predicted_confidence,
            "actual_success": self.actual_success,
            "verification_passed": self.verification_passed,
            "user_corrected": self.user_corrected,
            "hallucination_detected": self.hallucination_detected,
            "patch_accepted": self.patch_accepted,
            "test_pass_rate": self.test_pass_rate,
            "mode_used": self.mode_used,
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
        self.actual_accuracy = sum(1 for p in self.points if p.actual_success) / self.count
        self.error = abs(self.avg_predicted - self.actual_accuracy)

    def to_dict(self) -> dict:
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

    def to_dict(self) -> dict:
        return {
            "bins": [b.to_dict() for b in self.bins],
            "n_bins": self.n_bins,
            "total_points": self.total_points,
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
        }


@dataclass
class PerTaskConfidenceModel:
    task_type: str
    observations: int
    avg_predicted: float
    avg_actual: float
    calibration_error: float
    overconfidence_rate: float
    underconfidence_rate: float

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "observations": self.observations,
            "avg_predicted": round(self.avg_predicted, 3),
            "avg_actual": round(self.avg_actual, 3),
            "calibration_error": round(self.calibration_error, 3),
            "overconfidence_rate": round(self.overconfidence_rate, 3),
            "underconfidence_rate": round(self.underconfidence_rate, 3),
        }

    def adjusted_confidence(self, raw_confidence: float) -> float:
        if self.calibration_error < 0.05:
            return raw_confidence
        if self.overconfidence_rate > 0.3 and self.avg_predicted > self.avg_actual:
            gap = self.avg_predicted - self.avg_actual
            return max(0.05, raw_confidence - gap * 0.5)
        if self.underconfidence_rate > 0.3 and self.avg_predicted < self.avg_actual:
            gap = self.avg_actual - self.avg_predicted
            return min(0.99, raw_confidence + gap * 0.3)
        return raw_confidence


class LymeConfidenceCalibrator:
    """Confidence calibration for Lyme Model outputs."""

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self._points: List[CalibrationPoint] = []
        self._history: List[dict] = []

    def record(self, domain: str, task_type: str, predicted: float, actual: bool,
               verification: Optional[bool] = None, user_corrected: bool = False,
               hallucination: bool = False, patch_accepted: Optional[bool] = None,
               test_rate: Optional[float] = None, mode: str = "local_fast"):
        self._points.append(CalibrationPoint(
            domain=domain, task_type=task_type,
            predicted_confidence=predicted, actual_success=actual,
            verification_passed=verification, user_corrected=user_corrected,
            hallucination_detected=hallucination, patch_accepted=patch_accepted,
            test_pass_rate=test_rate, mode_used=mode, timestamp=time.time(),
        ))

    def compute_curve(self, points: Optional[List[CalibrationPoint]] = None) -> CalibrationCurve:
        pts = points if points is not None else self._points
        if not pts:
            return CalibrationCurve(bins=[], total_points=0, ece=0.0, mce=0.0)

        bin_edges = [i / self.n_bins for i in range(self.n_bins + 1)]
        bins = []
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

    def detect_overconfidence(self, threshold: float = 0.8) -> List[dict]:
        overconfident = []
        for p in self._points:
            if p.predicted_confidence >= threshold and not p.actual_success:
                overconfident.append({
                    "predicted": p.predicted_confidence,
                    "actual": p.actual_success,
                    "domain": p.domain,
                    "task_type": p.task_type,
                    "gap": p.predicted_confidence - 0.0,
                    "severity": "critical" if p.predicted_confidence > 0.95 else "high",
                })
            elif p.predicted_confidence <= 0.3 and p.actual_success:
                overconfident.append({
                    "predicted": p.predicted_confidence,
                    "actual": p.actual_success,
                    "domain": p.domain,
                    "task_type": p.task_type,
                    "gap": 0.0 - p.predicted_confidence,
                    "severity": "medium",
                    "type": "underconfidence",
                })
        return overconfident

    def compute_overconfidence_rate(self) -> float:
        high_conf = [p for p in self._points if p.predicted_confidence >= 0.8]
        if not high_conf:
            return 0.0
        wrong = sum(1 for p in high_conf if not p.actual_success)
        return wrong / len(high_conf)

    def compute_underconfidence_rate(self) -> float:
        low_conf = [p for p in self._points if p.predicted_confidence <= 0.3]
        if not low_conf:
            return 0.0
        correct = sum(1 for p in low_conf if p.actual_success)
        return correct / len(low_conf)

    def per_task_model(self, task_type: str) -> PerTaskConfidenceModel:
        pts = [p for p in self._points if p.task_type == task_type]
        if not pts:
            return PerTaskConfidenceModel(task_type=task_type, observations=0,
                                          avg_predicted=0.0, avg_actual=0.0,
                                          calibration_error=0.0,
                                          overconfidence_rate=0.0,
                                          underconfidence_rate=0.0)
        avg_pred = sum(p.predicted_confidence for p in pts) / len(pts)
        avg_act = sum(1 for p in pts if p.actual_success) / len(pts)
        overconf = sum(1 for p in pts if p.predicted_confidence >= 0.8 and not p.actual_success) / max(sum(1 for p in pts if p.predicted_confidence >= 0.8), 1)
        underconf = sum(1 for p in pts if p.predicted_confidence <= 0.3 and p.actual_success) / max(sum(1 for p in pts if p.predicted_confidence <= 0.3), 1)
        return PerTaskConfidenceModel(
            task_type=task_type, observations=len(pts),
            avg_predicted=avg_pred, avg_actual=avg_act,
            calibration_error=abs(avg_pred - avg_act),
            overconfidence_rate=overconf,
            underconfidence_rate=underconf,
        )

    def adjusted_confidence(self, raw: float, task_type: str) -> float:
        model = self.per_task_model(task_type)
        if model.observations < 3:
            return raw
        return model.adjusted_confidence(raw)

    def generate_report(self) -> dict:
        curve = self.compute_curve()
        overconfident = self.detect_overconfidence()
        task_models = {}
        seen_types = set(p.task_type for p in self._points)
        for tt in seen_types:
            task_models[tt] = self.per_task_model(tt).to_dict()

        report = {
            "report_id": f"cc_{uuid.uuid4().hex[:12]}",
            "timestamp": time.time(),
            "total_points": len(self._points),
            "curve": curve.to_dict(),
            "calibration_summary": {
                "ece": curve.ece,
                "mce": curve.mce,
                "overconfidence_rate": self.compute_overconfidence_rate(),
                "underconfidence_rate": self.compute_underconfidence_rate(),
            },
            "overconfidence_cases": overconfident[:20],
            "underconfidence_cases": [c for c in overconfident if c.get("type") == "underconfidence"][:20],
            "per_task_models": task_models,
            "hallucination_rate": self._hallucination_rate(),
            "user_correction_rate": self._user_correction_rate(),
        }

        recommendations = []
        if curve.ece > 0.15:
            recommendations.append(f"CRITICAL: ECE={curve.ece:.3f}. Apply strong calibration adjustment.")
        elif curve.ece > 0.08:
            recommendations.append(f"WARNING: ECE={curve.ece:.3f}. Apply moderate calibration adjustment.")
        for tt, tm in task_models.items():
            if tm["calibration_error"] > 0.15:
                recommendations.append(f"Task '{tt}' has calibration error {tm['calibration_error']:.3f} — adjust confidence for this task type.")
        if self.compute_overconfidence_rate() > 0.3:
            recommendations.append(f"Overconfidence rate is {self.compute_overconfidence_rate():.0%} — apply stronger penalty for high-confidence predictions.")
        if not recommendations:
            recommendations.append("Calibration is within acceptable range. Continue monitoring.")

        report["recommendations"] = recommendations
        self._history.append(report)
        return report

    def _hallucination_rate(self) -> float:
        if not self._points:
            return 0.0
        detected = sum(1 for p in self._points if p.hallucination_detected)
        return detected / len(self._points)

    def _user_correction_rate(self) -> float:
        if not self._points:
            return 0.0
        corrected = sum(1 for p in self._points if p.user_corrected)
        return corrected / len(self._points)


calibrator = LymeConfidenceCalibrator()
