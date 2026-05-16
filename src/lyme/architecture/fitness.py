from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import math


class FitnessDimension(str, Enum):
    MAINTAINABILITY = "maintainability"
    EVOLVABILITY = "evolvability"
    REPAIRABILITY = "repairability"
    COORDINATION_COST = "coordination_cost"
    RUNTIME_STABILITY = "runtime_stability"
    TESTING_EFFICIENCY = "testing_efficiency"
    DEPLOYMENT_RISK = "deployment_risk"
    SCALING_PRESSURE = "scaling_pressure"


@dataclass
class FitnessScore:
    dimension: FitnessDimension
    score: float
    confidence: float
    signals: List[Dict]
    causal_assumptions: List[str]

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "confidence": self.confidence,
            "signals": self.signals[:10],
            "causal_assumptions": self.causal_assumptions,
        }


@dataclass
class ArchitectureFitnessReport:
    overall_score: float
    dimension_scores: Dict[str, FitnessScore]
    maintainability: FitnessScore
    evolvability: FitnessScore
    repairability: FitnessScore
    coordination_cost: FitnessScore
    runtime_stability: FitnessScore
    testing_efficiency: FitnessScore
    deployment_risk: FitnessScore
    scaling_pressure: FitnessScore
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "dimensions": {k: v.to_dict() for k, v in self.dimension_scores.items()},
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Architecture Fitness Report",
            f"",
            f"**Overall Score:** {self.overall_score:.0%}",
            f"",
            f"## Dimension Scores",
        ]
        for dim in FitnessDimension:
            score = getattr(self, dim.value.replace("_", ""), None) or self.dimension_scores.get(dim.value)
            if score:
                bar = "█" * int(score.score * 20) + "░" * (20 - int(score.score * 20))
                lines.append(f"- **{dim.value.replace('_', ' ').title()}**: [{bar}] {score.score:.0%}")
        lines.extend([
            f"",
            f"## Recommendations",
        ])
        for r in self.recommendations:
            lines.append(f"- {r}")
        return "\n".join(lines)


class ArchitectureFitnessEngine:
    def __init__(self):
        self._observations: Dict[str, List[float]] = defaultdict(list)

    def evaluate(self, module_names: List[str], file_paths: List[str],
                 import_structure: Dict[str, List[str]],
                 test_files: Optional[List[str]] = None,
                 complexity_metrics: Optional[Dict] = None,
                 commit_history: Optional[List[Dict]] = None) -> ArchitectureFitnessReport:
        complexity_metrics = complexity_metrics or {}
        test_files = test_files or []
        commit_history = commit_history or []

        maintainability = self._score_maintainability(module_names, import_structure, complexity_metrics)
        evolvability = self._score_evolvability(module_names, import_structure, test_files)
        repairability = self._score_repairability(commit_history, test_files)
        coordination_cost = self._score_coordination(import_structure, module_names)
        runtime_stability = self._score_stability(commit_history, complexity_metrics)
        testing_efficiency = self._score_testing(test_files, module_names)
        deployment_risk = self._score_deployment(file_paths)
        scaling_pressure = self._score_scaling(module_names, import_structure)

        scores = {
            FitnessDimension.MAINTAINABILITY: maintainability,
            FitnessDimension.EVOLVABILITY: evolvability,
            FitnessDimension.REPAIRABILITY: repairability,
            FitnessDimension.COORDINATION_COST: coordination_cost,
            FitnessDimension.RUNTIME_STABILITY: runtime_stability,
            FitnessDimension.TESTING_EFFICIENCY: testing_efficiency,
            FitnessDimension.DEPLOYMENT_RISK: deployment_risk,
            FitnessDimension.SCALING_PRESSURE: scaling_pressure,
        }

        overall = sum(s.score * s.confidence for s in scores.values()) / max(1, sum(s.confidence for s in scores.values()))

        recommendations = self._generate_recommendations(scores)

        return ArchitectureFitnessReport(
            overall_score=round(overall, 3),
            dimension_scores={k.value: v for k, v in scores.items()},
            maintainability=maintainability,
            evolvability=evolvability,
            repairability=repairability,
            coordination_cost=coordination_cost,
            runtime_stability=runtime_stability,
            testing_efficiency=testing_efficiency,
            deployment_risk=deployment_risk,
            scaling_pressure=scaling_pressure,
            recommendations=recommendations,
        )

    def _score_maintainability(self, modules: List[str], imports: Dict,
                                complexity: Dict) -> FitnessScore:
        module_count = len(modules)
        import_density = sum(len(v) for v in imports.values()) / max(1, module_count)

        signals = [
            {"metric": "module_count", "value": module_count, "favorable": module_count < 50},
            {"metric": "import_density", "value": round(import_density, 2), "favorable": import_density < 5},
        ]

        score = 1.0 - min(1.0, (import_density / 10) * 0.6 + (module_count / 200) * 0.4)
        if complexity.get("cyclomatic_complexity"):
            avg_complexity = complexity["cyclomatic_complexity"]
            score *= max(0.5, 1.0 - avg_complexity / 20)
            signals.append({"metric": "avg_complexity", "value": avg_complexity})

        return FitnessScore(
            dimension=FitnessDimension.MAINTAINABILITY,
            score=round(max(0, score), 3), confidence=0.7,
            signals=signals,
            causal_assumptions=["Lower module count improves maintainability",
                                "Lower import density improves maintainability"],
        )

    def _score_evolvability(self, modules: List[str], imports: Dict,
                             test_files: List[str]) -> FitnessScore:
        has_tests = len(test_files) > 0
        module_count = len(modules)
        avg_deps = sum(len(v) for v in imports.values()) / max(1, module_count)

        signals = [
            {"metric": "has_tests", "value": has_tests, "favorable": has_tests},
            {"metric": "avg_dependencies", "value": round(avg_deps, 1), "favorable": avg_deps < 3},
        ]

        score = (0.3 if has_tests else 0.1) + max(0, 1.0 - avg_deps / 8) * 0.7

        return FitnessScore(
            dimension=FitnessDimension.EVOLVABILITY,
            score=round(max(0, score), 3), confidence=0.6,
            signals=signals,
            causal_assumptions=["Test coverage improves evolvability",
                                "Low coupling enables easier evolution"],
        )

    def _score_repairability(self, commits: List[Dict], test_files: List[str]) -> FitnessScore:
        bug_fix_ratio = 0
        if commits:
            bug_fixes = sum(1 for c in commits if "fix" in c.get("message", "").lower())
            bug_fix_ratio = bug_fixes / max(1, len(commits))

        signals = [
            {"metric": "bug_fix_ratio", "value": round(bug_fix_ratio, 3)},
            {"metric": "test_files", "value": len(test_files)},
        ]

        score = 0.5 + (len(test_files) / max(1, len(test_files) + 10)) * 0.3 + max(0, 0.3 - bug_fix_ratio) * 0.2

        return FitnessScore(
            dimension=FitnessDimension.REPAIRABILITY,
            score=round(min(1.0, score), 3), confidence=0.5,
            signals=signals,
            causal_assumptions=["Test presence improves repairability",
                                "Lower bug fix ratio indicates healthier codebase"],
        )

    def _score_coordination(self, imports: Dict, modules: List[str]) -> FitnessScore:
        total_modules = len(modules)
        shared_deps = 0
        all_targets = []
        for targets in imports.values():
            all_targets.extend(targets)
        if all_targets:
            from collections import Counter
            dep_counts = Counter(all_targets)
            shared_deps = sum(1 for c in dep_counts.values() if c > 3)

        signals = [
            {"metric": "shared_dependency_hotspots", "value": shared_deps},
            {"metric": "total_modules", "value": total_modules},
        ]

        coordination_overhead = shared_deps / max(1, total_modules)
        score = 1.0 - min(1.0, coordination_overhead)

        return FitnessScore(
            dimension=FitnessDimension.COORDINATION_COST,
            score=round(score, 3), confidence=0.6,
            signals=signals,
            causal_assumptions=["Shared dependency hotspots increase coordination cost",
                                "More modules increase coordination overhead"],
        )

    def _score_stability(self, commits: List[Dict], complexity: Dict) -> FitnessScore:
        commit_frequency = len(commits) / max(1, 30)
        signals = [
            {"metric": "commit_frequency_per_month", "value": round(commit_frequency, 1)},
        ]

        score = min(1.0, 1.0 / (1.0 + commit_frequency * 0.1))

        return FitnessScore(
            dimension=FitnessDimension.RUNTIME_STABILITY,
            score=round(score, 3), confidence=0.4,
            signals=signals,
            causal_assumptions=["High commit frequency may indicate instability",
                                "But could also indicate active development"],
        )

    def _score_testing(self, test_files: List[str], modules: List[str]) -> FitnessScore:
        test_ratio = len(test_files) / max(1, len(modules))
        signals = [
            {"metric": "test_files", "value": len(test_files)},
            {"metric": "test_to_module_ratio", "value": round(test_ratio, 2)},
        ]

        score = min(1.0, test_ratio * 2)

        return FitnessScore(
            dimension=FitnessDimension.TESTING_EFFICIENCY,
            score=round(score, 3), confidence=0.6,
            signals=signals,
            causal_assumptions=["Higher test ratio improves testing efficiency"],
        )

    def _score_deployment(self, file_paths: List[str]) -> FitnessScore:
        has_docker = any("docker" in p.lower() for p in file_paths)
        has_ci = any("github" in p.lower() or "ci" in p.lower() for p in file_paths)
        has_config = any(".yaml" in p or ".yml" in p or ".toml" in p for p in file_paths)

        signals = [
            {"metric": "has_docker", "value": has_docker},
            {"metric": "has_ci", "value": has_ci},
            {"metric": "has_config", "value": has_config},
        ]

        score = (0.3 if has_docker else 0) + (0.3 if has_ci else 0) + (0.2 if has_config else 0) + 0.2

        return FitnessScore(
            dimension=FitnessDimension.DEPLOYMENT_RISK,
            score=round(score, 3), confidence=0.5,
            signals=signals,
            causal_assumptions=["Docker presence reduces deployment risk",
                                "CI presence improves deployment reliability"],
        )

    def _score_scaling(self, modules: List[str], imports: Dict) -> FitnessScore:
        total_imports = sum(len(v) for v in imports.values())
        module_count = len(modules)
        avg_deps = total_imports / max(1, module_count)

        signals = [
            {"metric": "total_imports", "value": total_imports},
            {"metric": "avg_dependencies", "value": round(avg_deps, 1)},
        ]

        score = 1.0 - min(1.0, avg_deps / 12)

        return FitnessScore(
            dimension=FitnessDimension.SCALING_PRESSURE,
            score=round(score, 3), confidence=0.5,
            signals=signals,
            causal_assumptions=["High dependency density increases scaling pressure",
                                "Modular design reduces scaling pressure"],
        )

    def _generate_recommendations(self, scores: Dict[FitnessDimension, FitnessScore]) -> List[str]:
        recs = []
        for dim, score in scores.items():
            if score.score < 0.3:
                recs.append(f"Critical: {dim.value.replace('_', ' ').title()} score is very low ({score.score:.0%})")
            elif score.score < 0.5:
                recs.append(f"Improve: {dim.value.replace('_', ' ').title()} ({score.score:.0%})")
        if not recs:
            recs.append("All dimensions are healthy. Continue monitoring.")
        return recs

    def record_observation(self, dimension: str, value: float):
        self._observations[dimension].append(value)

    def get_longitudinal_measurements(self, dimension: str) -> List[float]:
        return list(self._observations.get(dimension, []))

    def compare_reports(self, report_a: ArchitectureFitnessReport,
                         report_b: ArchitectureFitnessReport) -> Dict:
        deltas = {}
        for dim in FitnessDimension:
            a_score = report_a.dimension_scores.get(dim.value)
            b_score = report_b.dimension_scores.get(dim.value)
            if a_score and b_score:
                deltas[dim.value] = round(b_score.score - a_score.score, 3)
        return {
            "overall_delta": round(report_b.overall_score - report_a.overall_score, 3),
            "dimension_deltas": deltas,
            "improving": [k for k, v in deltas.items() if v > 0],
            "declining": [k for k, v in deltas.items() if v < 0],
        }
