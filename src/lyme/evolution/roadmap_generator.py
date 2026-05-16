from __future__ import annotations

import json
import math
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .fitness_refactoring import FitnessAssessor, FitnessAssessment
from .maintenance_detector import MaintenanceDetector, MaintenanceOpportunity


class RoadmapHorizon(str, Enum):
    TWO_WEEK = "2_weeks"
    SIX_WEEK = "6_weeks"
    THREE_MONTH = "3_months"


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RoadmapRecommendation:
    title: str = ""
    description: str = ""
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    horizon: RoadmapHorizon = RoadmapHorizon.TWO_WEEK
    evidence: str = ""
    uncertainty: float = 0.0
    expected_payoff: float = 0.0
    likely_tradeoff: str = ""
    category: str = ""
    target_files: List[str] = field(default_factory=list)
    effort_estimate: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "horizon": self.horizon.value,
            "evidence": self.evidence,
            "uncertainty": round(self.uncertainty, 4),
            "expected_payoff": round(self.expected_payoff, 4),
            "likely_tradeoff": self.likely_tradeoff,
            "category": self.category,
            "target_files": self.target_files,
            "effort_estimate": self.effort_estimate,
        }


@dataclass
class TechnicalRoadmap:
    roadmap_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    repo_path: str = ""
    generated_at: float = field(default_factory=time.time)
    recommendations: Dict[str, List[RoadmapRecommendation]] = field(default_factory=dict)
    risk_reduction_plan: List[RoadmapRecommendation] = field(default_factory=list)
    refactor_priorities: List[RoadmapRecommendation] = field(default_factory=list)
    testing_priorities: List[RoadmapRecommendation] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roadmap_id": self.roadmap_id,
            "repo_path": self.repo_path,
            "generated_at": self.generated_at,
            "recommendations": {
                k: [r.to_dict() for r in v]
                for k, v in self.recommendations.items()
            },
            "risk_reduction": [r.to_dict() for r in self.risk_reduction_plan],
            "refactor_priorities": [r.to_dict() for r in self.refactor_priorities],
            "testing_priorities": [r.to_dict() for r in self.testing_priorities],
            "summary": self.summary[:500],
        }


class RoadmapGenerator:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.detector = MaintenanceDetector(repo_path)
        self.fitness = FitnessAssessor(repo_path)

    def generate_roadmap(self, product_goals: Optional[List[str]] = None, historical_velocity: Optional[float] = None) -> TechnicalRoadmap:
        roadmap = TechnicalRoadmap(repo_path=str(self.repo_path))

        fitness = self.fitness.assess()
        opportunities = self.detector.detect_all()
        drift = self._measure_architecture_drift()
        failures = self._analyze_runtime_failures()
        deps = self._analyze_dependency_risks()

        two_week = self._generate_horizon_recommendations(
            RoadmapHorizon.TWO_WEEK, fitness, opportunities, drift, failures, deps
        )
        six_week = self._generate_horizon_recommendations(
            RoadmapHorizon.SIX_WEEK, fitness, opportunities, drift, failures, deps
        )
        three_month = self._generate_horizon_recommendations(
            RoadmapHorizon.THREE_MONTH, fitness, opportunities, drift, failures, deps
        )

        roadmap.recommendations = {
            "2_weeks": two_week,
            "6_weeks": six_week,
            "3_months": three_month,
        }

        roadmap.risk_reduction_plan = self._build_risk_reduction_plan(fitness, opportunities, failures)
        roadmap.refactor_priorities = self._build_refactor_priorities(fitness, opportunities)
        roadmap.testing_priorities = self._build_testing_priorities(fitness, opportunities)

        roadmap.summary = self._generate_summary(fitness, two_week, six_week, three_month)
        self._persist(roadmap)
        return roadmap

    def _measure_architecture_drift(self) -> Dict[str, Any]:
        drift = {"score": 0.0, "indicators": []}
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--format=%s", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                msgs = result.stdout.splitlines()
                arch_mentions = sum(1 for m in msgs if any(kw in m.lower() for kw in ("refactor", "restructure", "redesign", "migrate")))
                drift["indicators"].append(f"{arch_mentions} architecture-related commits in last 200")
                if arch_mentions > 20:
                    drift["score"] += 0.3
                elif arch_mentions > 10:
                    drift["score"] += 0.15
        except Exception:
            pass

        large_files = 0
        for f in self.repo_path.rglob("*.py"):
            if f.is_file() and not any(p.startswith(".") for p in f.parts):
                try:
                    if len(f.read_text(encoding="utf-8", errors="replace").splitlines()) > 500:
                        large_files += 1
                except Exception:
                    pass
        if large_files > 3:
            drift["score"] += 0.2
            drift["indicators"].append(f"{large_files} files over 500 lines")

        return drift

    def _analyze_runtime_failures(self) -> List[Dict[str, Any]]:
        failures = []
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--format=%s", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for msg in result.stdout.splitlines():
                    if any(kw in msg.lower() for kw in ("fix", "bug", "hotfix", "crash", "error")):
                        failures.append({"message": msg[:100]})
        except Exception:
            pass
        return failures[:10]

    def _analyze_dependency_risks(self) -> List[Dict[str, Any]]:
        risks = []
        dep_files = ["pyproject.toml", "requirements.txt", "Cargo.toml", "package.json"]
        for df in dep_files:
            path = self.repo_path / df
            if path.exists():
                risks.append({"file": df, "risk": "manual_review", "details": f"Review {df} for outdated deps"})
        return risks

    def _generate_horizon_recommendations(self, horizon: RoadmapHorizon, fitness: FitnessAssessment, opportunities: List[MaintenanceOpportunity], drift: Dict[str, Any], failures: List[Dict[str, Any]], deps: List[Dict[str, Any]]) -> List[RoadmapRecommendation]:
        recommendations = []
        max_recs = {"2_weeks": 5, "6_weeks": 8, "3_months": 12}
        limit = max_recs.get(horizon.value, 5)

        if horizon == RoadmapHorizon.TWO_WEEK:
            for dim_name, score in fitness.scores.items():
                if score.score < 0.4:
                    recommendations.append(RoadmapRecommendation(
                        title=f"Address critical {dim_name} gap",
                        description=f"Current {dim_name} fitness: {score.score:.2f}. {score.explanation[:100]}",
                        priority=RecommendationPriority.HIGH,
                        horizon=horizon,
                        evidence=f"Fitness assessment shows {dim_name} at {score.score:.2f}",
                        uncertainty=0.3,
                        expected_payoff=0.4,
                        likely_tradeoff="Short-term effort for long-term maintainability",
                        category="fitness",
                    ))

            for opp in opportunities[:3]:
                if opp.score() > 0.3:
                    recommendations.append(RoadmapRecommendation(
                        title=opp.title[:80],
                        description=opp.description[:120],
                        priority=RecommendationPriority.MEDIUM,
                        horizon=horizon,
                        evidence=opp.evidence[:100],
                        uncertainty=opp.risk,
                        expected_payoff=opp.value,
                        likely_tradeoff=f"Estimated effort: {opp.effort:.2f}",
                        category=opp.category.value,
                        target_files=opp.target_files,
                    ))

        elif horizon == RoadmapHorizon.SIX_WEEK:
            if drift.get("score", 0) > 0.2:
                recommendations.append(RoadmapRecommendation(
                    title="Plan architectural remediation",
                    description=f"Architecture drift score: {drift['score']:.2f}. Indicators: {'; '.join(drift.get('indicators', []))}",
                    priority=RecommendationPriority.HIGH,
                    horizon=horizon,
                    evidence=f"Drift indicators: {drift.get('indicators', [])}",
                    uncertainty=0.4,
                    expected_payoff=0.6,
                    likely_tradeoff="May slow feature velocity during cleanup",
                    category="architecture",
                ))

            recommendations.append(RoadmapRecommendation(
                title="Reduce technical debt in lowest-fitness areas",
                description=f"Overall fitness: {fitness.overall_fitness:.2f}. Worst: {fitness.weakest_dimension}",
                priority=RecommendationPriority.MEDIUM,
                horizon=horizon,
                evidence=f"Weakest dimension: {fitness.weakest_dimension} ({fitness.scores.get(fitness.weakest_dimension, '?')})",
                uncertainty=0.35,
                expected_payoff=0.5,
                likely_tradeoff="Debt reduction vs new feature development",
                category="technical_debt",
            ))

        elif horizon == RoadmapHorizon.THREE_MONTH:
            if failures:
                recommendations.append(RoadmapRecommendation(
                    title="Invest in failure prevention infrastructure",
                    description=f"{len(failures)} bug/fix commits in recent history",
                    priority=RecommendationPriority.MEDIUM,
                    horizon=horizon,
                    evidence=f"{len(failures)} bug-related commits detected",
                    uncertainty=0.4,
                    expected_payoff=0.55,
                    likely_tradeoff="Infrastructure investment vs feature work",
                    category="reliability",
                ))

            if deps:
                recommendations.append(RoadmapRecommendation(
                    title="Dependency hygiene audit",
                    description=f"Review and update dependencies across {len(deps)} manifest files",
                    priority=RecommendationPriority.LOW,
                    horizon=horizon,
                    evidence=f"{len(deps)} dependency files to review",
                    uncertainty=0.3,
                    expected_payoff=0.3,
                    likely_tradeoff="Minor effort for reduced supply-chain risk",
                    category="dependencies",
                ))

        return recommendations[:limit]

    def _build_risk_reduction_plan(self, fitness: FitnessAssessment, opportunities: List[MaintenanceOpportunity], failures: List[Dict[str, Any]]) -> List[RoadmapRecommendation]:
        plan = []
        for dim_name, score in fitness.scores.items():
            if score.score < 0.35:
                plan.append(RoadmapRecommendation(
                    title=f"Urgent: improve {dim_name}",
                    description=f"Fitness score {score.score:.2f} is critically low",
                    priority=RecommendationPriority.CRITICAL,
                    horizon=RoadmapHorizon.TWO_WEEK,
                    evidence=score.explanation,
                    uncertainty=0.3,
                    expected_payoff=0.5,
                    likely_tradeoff="Must allocate time despite other priorities",
                    category="risk",
                ))

        for opp in opportunities:
            if opp.risk > 0.3 and opp.value > 0.5:
                plan.append(RoadmapRecommendation(
                    title=f"Risk-reduction: {opp.title[:60]}",
                    description=opp.description[:100],
                    priority=RecommendationPriority.HIGH,
                    horizon=RoadmapHorizon.TWO_WEEK,
                    evidence=opp.evidence[:100],
                    uncertainty=opp.risk,
                    expected_payoff=opp.value,
                    likely_tradeoff=f"Effort: {opp.effort:.2f} vs risk: {opp.risk:.2f}",
                    category="risk_reduction",
                    target_files=opp.target_files,
                ))

        return plan[:5]

    def _build_refactor_priorities(self, fitness: FitnessAssessment, opportunities: List[MaintenanceOpportunity]) -> List[RoadmapRecommendation]:
        priorities = []
        structural = [o for o in opportunities if o.category in ("architectural_erosion", "repeated_code", "cleanup")]
        for opp in sorted(structural, key=lambda o: o.score(), reverse=True)[:5]:
            priorities.append(RoadmapRecommendation(
                title=opp.title[:60],
                description=opp.description[:100],
                priority=RecommendationPriority.MEDIUM if opp.score() > 0.3 else RecommendationPriority.LOW,
                horizon=RoadmapHorizon.SIX_WEEK,
                evidence=opp.evidence[:100],
                uncertainty=opp.risk,
                expected_payoff=opp.value,
                likely_tradeoff=f"Effort: {opp.effort:.2f}",
                category="refactor",
                target_files=opp.target_files,
            ))
        return priorities

    def _build_testing_priorities(self, fitness: FitnessAssessment, opportunities: List[MaintenanceOpportunity]) -> List[RoadmapRecommendation]:
        priorities = []
        test_opps = [o for o in opportunities if o.category == "weak_test"]
        for opp in sorted(test_opps, key=lambda o: o.score(), reverse=True)[:5]:
            priorities.append(RoadmapRecommendation(
                title=opp.title[:60],
                description=opp.description[:100],
                priority=RecommendationPriority.HIGH if opp.value > 0.4 else RecommendationPriority.MEDIUM,
                horizon=RoadmapHorizon.TWO_WEEK,
                evidence=opp.evidence[:100],
                uncertainty=opp.risk,
                expected_payoff=opp.value,
                likely_tradeoff="Testing effort vs coverage gap",
                category="testing",
                target_files=opp.target_files,
            ))

        if fitness.scores.get("testability", FitnessScore("testability", 0, 0, "")).score < 0.3:
            priorities.append(RoadmapRecommendation(
                title="Systematic test coverage improvement",
                description="Testability is the weakest fitness dimension",
                priority=RecommendationPriority.HIGH,
                horizon=RoadmapHorizon.THREE_MONTH,
                evidence="Fitness assessment: testability critical",
                uncertainty=0.3,
                expected_payoff=0.6,
                likely_tradeoff="Significant time investment for safety net",
                category="testing",
            ))

        return priorities

    def _generate_summary(self, fitness: FitnessAssessment, two_week: List[RoadmapRecommendation], six_week: List[RoadmapRecommendation], three_month: List[RoadmapRecommendation]) -> str:
        parts = [
            f"Technical Roadmap for {self.repo_path.name}",
            f"Overall fitness: {fitness.overall_fitness:.2f} (weakest: {fitness.weakest_dimension})",
            "",
            f"Next 2 weeks: {len(two_week)} recommendations",
            f"Next 6 weeks: {len(six_week)} recommendations",
            f"Next 3 months: {len(three_month)} recommendations",
            "",
        ]

        for recs, label in [(two_week, "Immediate"), (six_week, "Short-term"), (three_month, "Medium-term")]:
            if recs:
                parts.append(f"{label} priorities:")
                for r in recs[:3]:
                    parts.append(f"  [{r.priority.value}] {r.title[:70]}")
                parts.append("")

        return "\n".join(parts)

    def _persist(self, roadmap: TechnicalRoadmap):
        out_dir = self.repo_path / ".lyme" / "roadmaps"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{roadmap.roadmap_id}.json"
        path.write_text(json.dumps(roadmap.to_dict(), indent=2, default=str))


from .fitness_refactoring import FitnessScore
