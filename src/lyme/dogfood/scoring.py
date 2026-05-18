from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import json


class DailyUsefulnessScore:
    """Score how likely you'd use Lyme daily based on actual dogfood results."""

    CATEGORIES = {
        "speed": {
            "weight": 0.25,
            "label": "Speed (time saved vs manual)",
            "benchmark": 3.0,
        },
        "accuracy": {
            "weight": 0.25,
            "label": "Accuracy (correct answers)",
            "benchmark": 0.8,
        },
        "coverage": {
            "weight": 0.15,
            "label": "Coverage (questions answered)",
            "benchmark": 0.85,
        },
        "reliability": {
            "weight": 0.15,
            "label": "Reliability (no crashes)",
            "benchmark": 0.9,
        },
        "integration": {
            "weight": 0.10,
            "label": "Integration (works with workflow)",
            "benchmark": 0.7,
        },
        "friction": {
            "weight": 0.10,
            "label": "Low Friction (intuitive UX)",
            "benchmark": 0.7,
        },
    }

    @staticmethod
    def compute(
        productivity_ratio: float,
        qa_accuracy: float,
        coverage_rate: float,
        reliability_rate: float,
        integration_score: float = 0.5,
        friction_score: float = 0.5,
    ) -> float:
        scores = {
            "speed": min(1.0, productivity_ratio / DailyUsefulnessScore.CATEGORIES["speed"]["benchmark"]),
            "accuracy": min(1.0, qa_accuracy / DailyUsefulnessScore.CATEGORIES["accuracy"]["benchmark"]),
            "coverage": min(1.0, coverage_rate / DailyUsefulnessScore.CATEGORIES["coverage"]["benchmark"]),
            "reliability": min(1.0, reliability_rate / DailyUsefulnessScore.CATEGORIES["reliability"]["benchmark"]),
            "integration": min(1.0, integration_score / DailyUsefulnessScore.CATEGORIES["integration"]["benchmark"]),
            "friction": min(1.0, friction_score / DailyUsefulnessScore.CATEGORIES["friction"]["benchmark"]),
        }

        total = 0.0
        breakdown = {}
        for key, score in scores.items():
            weight = DailyUsefulnessScore.CATEGORIES[key]["weight"]
            weighted = score * weight
            total += weighted
            breakdown[key] = {
                "score": round(score, 3),
                "weight": weight,
                "weighted": round(weighted, 3),
                "benchmark": DailyUsefulnessScore.CATEGORIES[key]["benchmark"],
                "label": DailyUsefulnessScore.CATEGORIES[key]["label"],
            }

        return round(total, 3)

    @staticmethod
    def interpret(score: float) -> str:
        if score >= 0.85:
            return "I don't want to code without this"
        elif score >= 0.7:
            return "Daily driver — minor friction"
        elif score >= 0.5:
            return "Useful but not daily — too many gaps"
        elif score >= 0.3:
            return "Occasional use — demos only"
        else:
            return "Not ready — significant issues remain"

    @staticmethod
    def print_report(score: float, breakdown: dict):
        print(f"\n{'='*60}")
        print(f"  DAILY USEFULNESS SCORE")
        print(f"{'='*60}")
        print(f"  Overall: {score:.0%}")
        print(f"  Verdict: {DailyUsefulnessScore.interpret(score)}")
        print(f"\n  Breakdown:")
        for key, data in breakdown.items():
            score = data.get("score", 0.5)
            weight = data.get("weight", 0.1)
            label = data.get("label", key)
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            print(f"    {label:35s} {bar} {score:.0%} (w={weight:.0%})")
        print(f"{'='*60}")


usefulness_scorer = DailyUsefulnessScore()
