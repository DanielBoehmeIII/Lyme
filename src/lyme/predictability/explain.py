from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConfidenceFactor:
    name: str
    score: float
    weight: float = 1.0
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "weight": self.weight,
            "detail": self.detail,
        }


@dataclass
class ConfidenceExplanation:
    overall: float
    factors: List[ConfidenceFactor] = field(default_factory=list)
    verdict: str = "unknown"
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 3),
            "factors": [f.to_dict() for f in self.factors],
            "verdict": self.verdict,
            "recommendation": self.recommendation,
        }

    def to_markdown(self) -> str:
        lines = [f"## Confidence Explanation\n"]
        bar_len = 20
        filled = int(self.overall * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"**Overall**: {bar} {self.overall:.0%}\n")
        lines.append(f"**Verdict**: {self.verdict}\n")
        for f in self.factors:
            f_bar = "█" * int(f.score * 10) + "░" * (10 - int(f.score * 10))
            lines.append(f"- **{f.name}**: {f_bar} {f.score:.0%} (weight: {f.weight})")
            if f.detail:
                lines.append(f"  - {f.detail}")
        if self.recommendation:
            lines.append(f"\n**Recommendation**: {self.recommendation}")
        return "\n".join(lines)


class ConfidenceExplainer:
    def explain(self, plan: Dict[str, Any]) -> ConfidenceExplanation:
        factors = []
        total_weight = 0
        weighted_sum = 0

        # Plan completeness
        steps = plan.get("steps", [])
        if steps:
            completeness = len([s for s in steps if s.get("status") != "pending"]) / len(steps)
            factors.append(ConfidenceFactor(
                name="Plan completeness",
                score=completeness,
                weight=2.0,
                detail=f"{int(completeness * 100)}% of steps complete",
            ))
            weighted_sum += completeness * 2.0
            total_weight += 2.0

        # Plan size (smaller is more predictable)
        n_steps = len(steps)
        size_score = 1.0 / (1 + n_steps * 0.1)
        factors.append(ConfidenceFactor(
            name="Plan size",
            score=size_score,
            weight=1.0,
            detail=f"{n_steps} steps",
        ))
        weighted_sum += size_score * 1.0
        total_weight += 1.0

        # Reproducibility
        if plan.get("reproducibility_hash"):
            factors.append(ConfidenceFactor(
                name="Reproducibility",
                score=0.9,
                weight=1.5,
                detail="Plan has reproducibility hash",
            ))
            weighted_sum += 0.9 * 1.5
            total_weight += 1.5

        # Environment capture
        if plan.get("environment"):
            env_keys = len(plan["environment"])
            env_score = min(1.0, env_keys * 0.3)
            factors.append(ConfidenceFactor(
                name="Environment capture",
                score=env_score,
                weight=1.0,
                detail=f"{env_keys} environment variables captured",
            ))
            weighted_sum += env_score * 1.0
            total_weight += 1.0

        overall = weighted_sum / max(total_weight, 1)
        overall = max(0.0, min(1.0, overall))

        if overall >= 0.8:
            verdict = "high_confidence"
            recommendation = "Plan is well-structured and reproducible. Proceed with execution."
        elif overall >= 0.5:
            verdict = "moderate_confidence"
            recommendation = "Plan has reasonable structure. Review steps before executing."
        else:
            verdict = "low_confidence"
            recommendation = "Plan lacks detail. Consider adding more explicit steps and expected outcomes."

        return ConfidenceExplanation(
            overall=overall,
            factors=factors,
            verdict=verdict,
            recommendation=recommendation,
        )
