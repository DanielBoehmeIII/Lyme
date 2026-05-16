from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .risk_model import FailurePrediction, FileRiskProfile


class PredictionEvaluator:
    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def evaluate(self, prediction: FailurePrediction, actual_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not prediction.file_profiles:
            return {"error": "no predictions to evaluate"}

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for profile in prediction.file_profiles:
            predicted_risky = profile.risk_score.overall >= 0.5
            actual_failure = any(
                o.get("file") == profile.file_path and o.get("failed", False)
                for o in actual_outcomes
            )

            if predicted_risky and actual_failure:
                true_positives += 1
            elif predicted_risky and not actual_failure:
                false_positives += 1
            elif not predicted_risky and not actual_failure:
                true_negatives += 1
            elif not predicted_risky and actual_failure:
                false_negatives += 1

        total = true_positives + false_positives + true_negatives + false_negatives
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(true_positives + false_negatives, 1)
        f1 = 2 * (precision * recall) / max(precision + recall, 0.001)

        result = {
            "timestamp": time.time(),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives,
            "total_predictions": total,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

        self._history.append(result)
        return result

    def get_performance_trend(self) -> Dict[str, Any]:
        if not self._history:
            return {"error": "no evaluation history"}

        f1_scores = [h["f1_score"] for h in self._history]
        return {
            "evaluation_count": len(self._history),
            "avg_f1": sum(f1_scores) / len(f1_scores),
            "f1_trend": f1_scores[-1] - f1_scores[0] if len(f1_scores) > 1 else 0,
            "best_f1": max(f1_scores),
            "latest_f1": f1_scores[-1],
        }


class FeedbackLoop:
    def __init__(self):
        self._feedback: List[Dict[str, Any]] = []

    def record_outcome(self, file_path: str, predicted_risk: float, actually_failed: bool):
        self._feedback.append({
            "file": file_path,
            "predicted_risk": predicted_risk,
            "actually_failed": actually_failed,
            "timestamp": time.time(),
        })

    def calibrate_threshold(self, target_f1: float = 0.8) -> float:
        if len(self._feedback) < 10:
            return 0.5

        thresholds = [i * 0.05 for i in range(5, 19)]
        best_threshold = 0.5
        best_f1 = 0.0

        for threshold in thresholds:
            tp = sum(
                1 for f in self._feedback
                if f["predicted_risk"] >= threshold and f["actually_failed"]
            )
            fp = sum(
                1 for f in self._feedback
                if f["predicted_risk"] >= threshold and not f["actually_failed"]
            )
            fn = sum(
                1 for f in self._feedback
                if f["predicted_risk"] < threshold and f["actually_failed"]
            )

            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * (precision * recall) / max(precision + recall, 0.001)

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold

        return best_threshold
