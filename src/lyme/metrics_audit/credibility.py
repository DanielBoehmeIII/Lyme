from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class CredibilityFactor:
    name: str
    score: float
    weight: float
    details: str

    def to_dict(self) -> dict:
        return {"name": self.name, "score": self.score, "weight": self.weight, "details": self.details}


@dataclass
class CredibilityReport:
    overall_score: float
    factors: List[CredibilityFactor]
    verdict: str
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 3),
            "factors": [f.to_dict() for f in self.factors],
            "verdict": self.verdict,
            "recommendations": self.recommendations,
        }


class BenchmarkCredibilityScorer:
    FACTORS = {
        "provenance": {
            "weight": 0.30,
            "label": "Metric Provenance",
            "description": "Each metric has a clear, verifiable source",
        },
        "reproducibility": {
            "weight": 0.20,
            "label": "Reproducibility",
            "description": "Results can be reproduced with pinned versions",
        },
        "evidence": {
            "weight": 0.20,
            "label": "Evidence Attached",
            "description": "Each result has associated evidence files",
        },
        "real_execution": {
            "weight": 0.15,
            "label": "Real Execution",
            "description": "Metrics come from real command execution, not simulation",
        },
        "human_verification": {
            "weight": 0.15,
            "label": "Human Verification",
            "description": "A human has verified at least a sample of results",
        },
    }

    def score(
        self,
        provenance_score: float = 0.0,
        reproducibility_score: float = 0.0,
        evidence_score: float = 0.0,
        real_execution_score: float = 0.0,
        human_verification_score: float = 0.0,
    ) -> CredibilityReport:
        factors = [
            CredibilityFactor(
                name=self.FACTORS["provenance"]["label"],
                score=provenance_score,
                weight=self.FACTORS["provenance"]["weight"],
                details=f"{provenance_score:.0%} of metrics have clear provenance",
            ),
            CredibilityFactor(
                name=self.FACTORS["reproducibility"]["label"],
                score=reproducibility_score,
                weight=self.FACTORS["reproducibility"]["weight"],
                details=f"{reproducibility_score:.0%} of results are reproducible",
            ),
            CredibilityFactor(
                name=self.FACTORS["evidence"]["label"],
                score=evidence_score,
                weight=self.FACTORS["evidence"]["weight"],
                details=f"{evidence_score:.0%} of results have evidence attached",
            ),
            CredibilityFactor(
                name=self.FACTORS["real_execution"]["label"],
                score=real_execution_score,
                weight=self.FACTORS["real_execution"]["weight"],
                details=f"{real_execution_score:.0%} from real execution",
            ),
            CredibilityFactor(
                name=self.FACTORS["human_verification"]["label"],
                score=human_verification_score,
                weight=self.FACTORS["human_verification"]["weight"],
                details=f"{human_verification_score:.0%} verified by human",
            ),
        ]
        overall = sum(f.score * f.weight for f in factors)

        if overall >= 0.85:
            verdict = "Highly credible — can be used for decision-making"
        elif overall >= 0.7:
            verdict = "Moderately credible — acceptable with caveats"
        elif overall >= 0.5:
            verdict = "Partially credible — needs more verification"
        elif overall >= 0.3:
            verdict = "Low credibility — do not rely on these metrics"
        else:
            verdict = "Not credible — replace with real measurements"

        recommendations = []
        if provenance_score < 0.7:
            recommendations.append("Add provenance metadata to all metrics")
        if reproducibility_score < 0.7:
            recommendations.append("Pin tool/runner versions and document reproduction steps")
        if evidence_score < 0.7:
            recommendations.append("Attach evidence files (logs, screenshots, diffs) to results")
        if real_execution_score < 0.5:
            recommendations.append("Replace simulated metrics with real command execution")
        if human_verification_score < 0.5:
            recommendations.append("Have a human verify at least 20% of results")

        return CredibilityReport(
            overall_score=overall,
            factors=factors,
            verdict=verdict,
            recommendations=recommendations,
        )

    def print_report(self, report: CredibilityReport):
        print(f"{'='*60}")
        print(f"  BENCHMARK CREDIBILITY SCORE")
        print(f"{'='*60}")
        print(f"  Overall: {report.overall_score:.0%}")
        print(f"  Verdict: {report.verdict}")
        print(f"\n  Factors:")
        for f in report.factors:
            bar = "█" * int(f.score * 20) + "░" * (20 - int(f.score * 20))
            print(f"    {f.name:25s} {bar} {f.score:.0%} (w={f.weight:.0%})")
        if report.recommendations:
            print(f"\n  Recommendations:")
            for r in report.recommendations:
                print(f"    → {r}")
        print(f"{'='*60}")


credibility_scorer = BenchmarkCredibilityScorer()
