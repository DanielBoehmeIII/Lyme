from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import math
from collections import Counter, defaultdict


class StabilityLevel(str, Enum):
    STABLE = "stable"
    MODERATE = "moderate"
    UNSTABLE = "unstable"
    CRITICAL = "critical"


@dataclass
class StabilityMetrics:
    overall_score: float
    level: StabilityLevel
    package_stability: float
    dependency_stability: float
    community_health: float
    release_consistency: float
    adoption_depth: float
    breaking_change_frequency: float
    confidence: float
    signals: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "level": self.level.value,
            "package_stability": self.package_stability,
            "dependency_stability": self.dependency_stability,
            "community_health": self.community_health,
            "release_consistency": self.release_consistency,
            "adoption_depth": self.adoption_depth,
            "breaking_change_frequency": self.breaking_change_frequency,
            "confidence": self.confidence,
            "signals": self.signals[:20],
        }


@dataclass
class MigrationForecast:
    source: str
    target: str
    likelihood: float
    timeframe: str
    driving_forces: List[str]
    blocking_factors: List[str]
    risk_score: float
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "likelihood": self.likelihood,
            "timeframe": self.timeframe,
            "driving_forces": self.driving_forces,
            "blocking_factors": self.blocking_factors,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
        }


class EcosystemStabilityAnalyzer:
    def __init__(self, dependency_graph):
        self._graph = dependency_graph

    def compute_stability(self) -> StabilityMetrics:
        libs = self._graph.libraries if hasattr(self._graph, 'libraries') else []
        if not libs:
            return StabilityMetrics(0, StabilityLevel.UNSTABLE, 0, 0, 0, 0, 0, 0, 0)

        total = len(libs)

        release_consistencies = []
        adoption_rates = []
        abandonment_risks = []
        centrality_scores = self._graph.compute_centrality() if hasattr(self._graph, 'compute_centrality') else {}

        for lib in libs:
            release_consistencies.append(lib.release_frequency if hasattr(lib, 'release_frequency') else 0.5)
            adoption_rates.append(lib.adoption_rate if hasattr(lib, 'adoption_rate') else 0.5)
            abandonment_risks.append(lib.abandonment_risk if hasattr(lib, 'abandonment_risk') else 0)

        package_stability = 1.0 - (sum(abandonment_risks) / len(abandonment_risks) if abandonment_risks else 0)
        community_health = sum(adoption_rates) / len(adoption_rates) if adoption_rates else 0.5
        release_consistency = sum(release_consistencies) / len(release_consistencies) if release_consistencies else 0.5

        dependents_count = sum(
            len(self._graph.get_dependents(lib.id)) for lib in libs
        ) if hasattr(self._graph, 'get_dependents') else 0
        adoption_depth = min(1.0, dependents_count / max(1, total * 2))

        breaking_changes = sum(1 for e in self._graph._edges.values()
                               if hasattr(e, 'is_conflicting') and e.is_conflicting) if hasattr(self._graph, '_edges') else 0
        breaking_change_frequency = breaking_changes / max(1, total)

        signals = self._compute_stability_signals(libs)

        overall = (package_stability * 0.25 + community_health * 0.2 +
                   release_consistency * 0.15 + adoption_depth * 0.2 +
                   (1.0 - breaking_change_frequency) * 0.2)

        level = self._score_to_level(overall)

        return StabilityMetrics(
            overall_score=round(overall, 3),
            level=level,
            package_stability=round(package_stability, 3),
            dependency_stability=round(1.0 - breaking_change_frequency, 3),
            community_health=round(community_health, 3),
            release_consistency=round(release_consistency, 3),
            adoption_depth=round(adoption_depth, 3),
            breaking_change_frequency=round(breaking_change_frequency, 3),
            confidence=0.7,
            signals=signals,
        )

    def _compute_stability_signals(self, libs) -> List[Dict]:
        signals = []

        high_abandonment = [l for l in libs if getattr(l, 'abandonment_risk', 0) > 0.7]
        if high_abandonment:
            signals.append({
                "type": "abandonment_risk",
                "severity": "high",
                "count": len(high_abandonment),
                "libraries": [l.name for l in high_abandonment[:5]],
                "description": f"{len(high_abandonment)} libraries at high abandonment risk",
            })

        low_release = [l for l in libs if getattr(l, 'release_frequency', 1) < 0.1]
        if low_release:
            signals.append({
                "type": "stale_releases",
                "severity": "medium",
                "count": len(low_release),
                "libraries": [l.name for l in low_release[:5]],
                "description": f"{len(low_release)} libraries with infrequent releases",
            })

        central_deps = self._graph.analyze_dominance() if hasattr(self._graph, 'analyze_dominance') else {}
        high_concentration = {k: v for k, v in central_deps.items() if v > 0.3}
        if high_concentration:
            signals.append({
                "type": "dependency_concentration",
                "severity": "medium",
                "libraries": list(high_concentration.keys())[:5],
                "description": "High dependency concentration: few libraries dominate",
            })

        return signals

    def _score_to_level(self, score: float) -> StabilityLevel:
        if score >= 0.7:
            return StabilityLevel.STABLE
        if score >= 0.5:
            return StabilityLevel.MODERATE
        if score >= 0.3:
            return StabilityLevel.UNSTABLE
        return StabilityLevel.CRITICAL

    def forecast_migration_waves(self) -> List[MigrationForecast]:
        forecasts = []
        libs = self._graph.libraries if hasattr(self._graph, 'libraries') else []

        for lib in libs:
            if getattr(lib, 'phase', None) and lib.phase.value == "declining":
                dependents = self._graph.get_dependents(lib.id) if hasattr(self._graph, 'get_dependents') else []
                if dependents:
                    replacement = lib.metadata.get("replacement", "") if hasattr(lib, 'metadata') else ""
                    if replacement:
                        forecasts.append(MigrationForecast(
                            source=lib.name,
                            target=replacement,
                            likelihood=min(1.0, lib.abandonment_risk * 1.2),
                            timeframe="6-12 months" if lib.abandonment_risk < 0.5 else "1-6 months",
                            driving_forces=["Abandonment risk", "Security concerns", "Better alternatives"],
                            blocking_factors=["Migration cost", "Ecosystem lock-in", "Testing burden"],
                            risk_score=lib.abandonment_risk,
                            confidence=0.6,
                        ))

        return forecasts

    def compute_ecosystem_fragility(self) -> Dict:
        metrics = self.compute_stability()
        lock_in = self._graph.compute_lock_in_risk() if hasattr(self._graph, 'compute_lock_in_risk') else []
        chains = self._graph.compute_brittle_chains() if hasattr(self._graph, 'compute_brittle_chains') else []

        fragility_factors = []
        if metrics.breaking_change_frequency > 0.3:
            fragility_factors.append("high_breaking_change_frequency")
        if len(lock_in) > 5:
            fragility_factors.append("ecosystem_lock_in")
        if len(chains) > 10:
            fragility_factors.append("brittle_dependency_chains")
        if metrics.level in (StabilityLevel.UNSTABLE, StabilityLevel.CRITICAL):
            fragility_factors.append("low_ecosystem_stability")

        return {
            "fragility_score": round(1.0 - metrics.overall_score, 3),
            "stability_score": metrics.overall_score,
            "level": metrics.level.value,
            "fragility_factors": fragility_factors,
            "high_risk_libraries": [l["library"] for l in lock_in[:5]],
            "brittle_chain_count": len(chains),
            "recommendations": self._generate_stability_recommendations(metrics, fragility_factors),
        }

    def _generate_stability_recommendations(self, metrics: StabilityMetrics, factors: List[str]) -> List[str]:
        recs = []
        if "ecosystem_lock_in" in factors:
            recs.append("Reduce dependency on single-vendor libraries. Identify alternatives for critical paths.")
        if "brittle_dependency_chains" in factors:
            recs.append("Audit deep dependency chains. Consider dependency flattening or vendoring.")
        if "high_breaking_change_frequency" in factors:
            recs.append("Adopt semantic versioning strictly. Use dependency pinning for stability.")
        if "low_ecosystem_stability" in factors:
            recs.append("Consider ecosystem-wide health assessment. Identify systemic issues.")
        if metrics.community_health < 0.4:
            recs.append("Low community engagement detected. Evaluate long-term maintenance viability.")
        return recs

    def update_propagation_forecast(self, library_name: str, change_type: str = "major") -> Dict:
        libs = self._graph.libraries if hasattr(self._graph, 'libraries') else []
        target = None
        for lib in libs:
            if lib.name.lower() == library_name.lower():
                target = lib
                break

        if not target:
            return {"error": f"Library '{library_name}' not found"}

        dep_count = len(self._graph.get_dependents(target.id)) if hasattr(self._graph, 'get_dependents') else 0
        impact = "critical" if dep_count > 50 else "high" if dep_count > 20 else "medium" if dep_count > 5 else "low"

        return {
            "library": library_name,
            "change_type": change_type,
            "impact_level": impact,
            "downstream_dependents": dep_count,
            "estimated_adoption_time": f"{max(1, dep_count // 10)}-{max(2, dep_count // 5)} months",
            "community_size": target.community_size if hasattr(target, 'community_size') else 0,
            "stability_contribution": target.centrality if hasattr(target, 'centrality') else 0,
        }
