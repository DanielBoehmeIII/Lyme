from __future__ import annotations

import math
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .evolution_model import (
    EvolutionModel, EvolutionSnapshot, EvolutionMetrics, EvolutionTrend,
    TemporalEvent, TemporalEventType,
)


class MotifType(str, Enum):
    MONOLITH_TO_MODULAR = "monolith_to_modular"
    ABSTRACTION_LEAKAGE = "abstraction_leakage"
    CYCLIC_DEPENDENCY_GROWTH = "cyclic_dependency_growth"
    MIGRATION_WAVE = "migration_wave"
    TEST_STABILIZATION = "test_stabilization"
    INFRASTRUCTURE_CENTRALIZATION = "infrastructure_centralization"
    ACCIDENTAL_FRAMEWORK = "accidental_framework"
    REFACTOR_CASCADE = "refactor_cascade"
    OWNERSHIP_CONCENTRATION = "ownership_concentration"
    BOILING_OCEAN = "boiling_ocean"
    DECAYING_CORE = "decaying_core"
    STABLE_EVOLUTION = "stable_evolution"


class MotifHealth(str, Enum):
    HEALTHY = "healthy"
    NEUTRAL = "neutral"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class MotifSignature:
    motif_type: MotifType
    confidence: float = 0.0
    severity: float = 0.0
    description: str = ""
    indicators: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    health: MotifHealth = MotifHealth.NEUTRAL
    detected_at: float = field(default_factory=time.time)
    time_bounds: Tuple[float, float] = (0.0, 0.0)
    involved_subsystems: List[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "motif_type": self.motif_type.value,
            "confidence": self.confidence,
            "severity": self.severity,
            "description": self.description[:200],
            "indicators": self.indicators[:5],
            "evidence": self.evidence[:5],
            "health": self.health.value,
            "detected_at": self.detected_at,
            "time_bounds": list(self.time_bounds),
            "involved_subsystems": self.involved_subsystems[:5],
            "recommended_action": self.recommended_action[:200],
        }


@dataclass
class MotifCluster:
    cluster_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    motif_type: MotifType = MotifType.STABLE_EVOLUTION
    trajectories: List[List[Dict[str, float]]] = field(default_factory=list)
    avg_health_score: float = 0.5
    trajectory_count: int = 0
    centroids: Dict[str, float] = field(default_factory=dict)
    dispersion: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "motif_type": self.motif_type.value,
            "avg_health_score": self.avg_health_score,
            "trajectory_count": self.trajectory_count,
            "dispersion": self.dispersion,
        }


class MotifDiscoveryEngine:
    def __init__(self):
        self._motifs: List[MotifSignature] = []
        self._clusters: List[MotifCluster] = []

    def analyze(self, model: EvolutionModel) -> List[MotifSignature]:
        self._motifs = []

        motif = self._detect_monolith_to_modular(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_abstraction_leakage(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_cyclic_dependency_growth(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_migration_wave(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_test_stabilization(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_infrastructure_centralization(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_accidental_framework(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_refactor_cascade(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_ownership_concentration(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_boiling_ocean(model)
        if motif:
            self._motifs.append(motif)

        motif = self._detect_decaying_core(model)
        if motif:
            self._motifs.append(motif)

        if not self._motifs:
            self._motifs.append(MotifSignature(
                motif_type=MotifType.STABLE_EVOLUTION,
                confidence=0.7,
                description="Repository shows stable evolutionary patterns with no strong motif signatures.",
                health=MotifHealth.HEALTHY,
            ))

        return self._motifs

    def cluster_trajectories(self, trajectories: List[List[Dict[str, float]]]) -> List[MotifCluster]:
        if not trajectories:
            return []

        self._clusters = []
        for traj in trajectories:
            matched = False
            for cluster in self._clusters:
                similarity = self._trajectory_similarity(traj, cluster.centroids)
                if similarity > 0.7:
                    cluster.trajectories.append(traj)
                    cluster.trajectory_count += 1
                    cluster.dispersion += (1 - similarity)
                    matched = True
                    break
            if not matched:
                centroid = self._compute_centroid(traj)
                self._clusters.append(MotifCluster(
                    centroids=centroid,
                    trajectories=[traj],
                    trajectory_count=1,
                ))

        for cluster in self._clusters:
            cluster.dispersion /= max(cluster.trajectory_count, 1)
            if cluster.dispersion < 0.2:
                cluster.avg_health_score = 0.8
            elif cluster.dispersion < 0.4:
                cluster.avg_health_score = 0.6
            else:
                cluster.avg_health_score = 0.4

        return self._clusters

    def estimate_future_path(self, model: EvolutionModel,
                              motif: MotifSignature) -> Dict[str, Any]:
        if not model.timeline.snapshots:
            return {"prediction": "unknown", "confidence": 0.0}

        if motif.motif_type == MotifType.MONOLITH_TO_MODULAR:
            subsystem_trend = self._get_subsystem_count_trend(model)
            if subsystem_trend > 0:
                return {
                    "prediction": "continuing modularization with further subsystem extraction",
                    "confidence": 0.7,
                    "timeframe": "next 3-6 months",
                    "risk": "low",
                }
            return {
                "prediction": "modularization may plateau; monitor for re-consolidation",
                "confidence": 0.5,
                "timeframe": "next 6 months",
                "risk": "medium",
            }

        if motif.motif_type == MotifType.CYCLIC_DEPENDENCY_GROWTH:
            return {
                "prediction": "increasing maintenance cost; likely need for dependency restructuring",
                "confidence": 0.75,
                "timeframe": "next 1-3 months",
                "risk": "high",
            }

        if motif.motif_type == MotifType.ACCIDENTAL_FRAMEWORK:
            return {
                "prediction": "a hidden platform will emerge, increasing coupling and reducing flexibility",
                "confidence": 0.65,
                "timeframe": "next 6-12 months",
                "risk": "high",
            }

        if motif.motif_type == MotifType.DECAYING_CORE:
            return {
                "prediction": "core modules will require increasing maintenance effort; consider rewrite",
                "confidence": 0.8,
                "timeframe": "next 3 months",
                "risk": "critical",
            }

        return {
            "prediction": "continued gradual evolution",
            "confidence": 0.4,
            "timeframe": "next 6 months",
            "risk": "low",
        }

    def _get_subsystem_count_trend(self, model: EvolutionModel) -> float:
        if len(model.timeline.snapshots) < 2:
            return 0.0
        counts = [s.metrics.subsystem_count for s in model.timeline.snapshots]
        if len(counts) >= 2:
            return (counts[-1] - counts[0]) / max(len(counts) - 1, 1)
        return 0.0

    def _compute_centroid(self, trajectory: List[Dict[str, float]]) -> Dict[str, float]:
        if not trajectory:
            return {}
        centroid: Dict[str, float] = {}
        keys = trajectory[0].keys()
        for key in keys:
            centroid[key] = sum(t.get(key, 0) for t in trajectory) / len(trajectory)
        return centroid

    def _trajectory_similarity(self, traj: List[Dict[str, float]],
                                centroid: Dict[str, float]) -> float:
        if not traj or not centroid:
            return 0.0

        traj_centroid = self._compute_centroid(traj)
        if not traj_centroid:
            return 0.0

        common_keys = set(traj_centroid.keys()) & set(centroid.keys())
        if not common_keys:
            return 0.0

        diffs = []
        for key in common_keys:
            diffs.append(abs(traj_centroid[key] - centroid[key]))

        avg_diff = sum(diffs) / len(diffs)
        return max(0.0, 1.0 - avg_diff)

    def _detect_monolith_to_modular(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 3:
            return None

        subsystem_counts = [s.metrics.subsystem_count for s in model.timeline.snapshots]
        if len(subsystem_counts) < 2:
            return None

        increasing = sum(
            1 for i in range(1, len(subsystem_counts))
            if subsystem_counts[i] > subsystem_counts[i - 1]
        )
        ratio = increasing / (len(subsystem_counts) - 1)

        refactor_ratio = 0
        if model.events:
            refactors = sum(1 for e in model.events if e.event_type == TemporalEventType.REFACTOR)
            refactor_ratio = refactors / len(model.events)

        if ratio > 0.6 and refactor_ratio > 0.15:
            return MotifSignature(
                motif_type=MotifType.MONOLITH_TO_MODULAR,
                confidence=min(1.0, ratio * refactor_ratio * 3),
                severity=0.3,
                description="Repository transitioning from monolith to modular architecture. Subsystem count is increasing with refactoring activity.",
                indicators=[
                    f"Subsystem count increasing ({subsystem_counts[0]} -> {subsystem_counts[-1]})",
                    f"Refactor ratio: {refactor_ratio:.0%} of commits",
                ],
                health=MotifHealth.HEALTHY,
                involved_subsystems=list(set(
                    s for snap in model.timeline.snapshots[-3:]
                    for s in model.subsystem_history.keys()
                )),
                recommended_action="Continue modularization with clear boundary definitions. Monitor for interface stability.",
            )

        return None

    def _detect_abstraction_leakage(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 3:
            return None

        complexity_trend = model.timeline.trends.get("avg_file_complexity")
        if not complexity_trend or len(complexity_trend.values) < 2:
            return None

        delta = complexity_trend.values[-1] - complexity_trend.values[0]
        volatility = complexity_trend.volatility

        if delta > 0 and volatility > 0.4:
            return MotifSignature(
                motif_type=MotifType.ABSTRACTION_LEAKAGE,
                confidence=min(1.0, abs(delta) * volatility),
                severity=0.6,
                description="Abstraction layers are leaking: complexity and volatility are both rising, suggesting abstractions are failing to contain complexity.",
                indicators=[
                    f"Complexity delta: {delta:.2f}",
                    f"Volatility: {volatility:.2f}",
                ],
                health=MotifHealth.UNHEALTHY,
                recommended_action="Audit abstraction boundaries. Look for leaky interfaces and layer-skip patterns.",
            )

        return None

    def _detect_cyclic_dependency_growth(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 2:
            return None

        circular_counts = [
            s.metrics.circular_dependency_count for s in model.timeline.snapshots
        ]
        if max(circular_counts) == 0:
            return None

        growing = circular_counts[-1] > circular_counts[0] if len(circular_counts) >= 2 else False
        if growing:
            return MotifSignature(
                motif_type=MotifType.CYCLIC_DEPENDENCY_GROWTH,
                confidence=0.7,
                severity=0.8,
                description="Circular dependencies are growing over time, indicating structural decay.",
                indicators=[
                    f"Circular deps: {circular_counts[0]} -> {circular_counts[-1]}",
                ],
                health=MotifHealth.CRITICAL,
                recommended_action="Break dependency cycles. Extract shared dependencies into separate modules. Use dependency inversion.",
            )

        return None

    def _detect_migration_wave(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if not model.events:
            return None

        migration_events = [
            e for e in model.events
            if e.event_type == TemporalEventType.MIGRATION
        ]

        if len(migration_events) >= 3:
            time_span = migration_events[-1].timestamp - migration_events[0].timestamp
            density = len(migration_events) / max(time_span / 86400, 1)

            if density > 0.1:
                return MotifSignature(
                    motif_type=MotifType.MIGRATION_WAVE,
                    confidence=min(1.0, density),
                    severity=0.5,
                    description=f"Migration wave detected: {len(migration_events)} migration events over {time_span/86400:.0f} days.",
                    indicators=[
                        f"{len(migration_events)} migration commits",
                        f"Density: {density:.2f} migrations/day",
                    ],
                    health=MotifHealth.NEUTRAL,
                    recommended_action="Ensure migration is well-documented and has rollback plans. Monitor for incomplete migrations.",
                )

        return None

    def _detect_test_stabilization(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 3:
            return None

        test_cov_estimates = [
            s.metrics.test_coverage_estimate for s in model.timeline.snapshots
        ]

        if len(test_cov_estimates) < 2:
            return None

        improving = test_cov_estimates[-1] - test_cov_estimates[0] > 0.05
        stable = max(test_cov_estimates) - min(test_cov_estimates) < 0.1

        if improving or stable:
            return MotifSignature(
                motif_type=MotifType.TEST_STABILIZATION,
                confidence=0.6 if improving else 0.8,
                severity=0.2,
                description="Test coverage is " + ("improving" if improving else "stable") + ", indicating healthy testing practices.",
                indicators=[
                    f"Coverage: {test_cov_estimates[0]:.0%} -> {test_cov_estimates[-1]:.0%}",
                    "Coverage is stable" if stable else "Coverage improving",
                ],
                health=MotifHealth.HEALTHY,
                recommended_action="Continue current testing practices. Consider property-based testing for critical subsystems.",
            )

        return None

    def _detect_infrastructure_centralization(self, model: EvolutionModel) -> Optional[MotifSignature]:
        infra_keywords = ["config", "infra", "ci", "docker", "deploy", "build", "setup"]
        if not model.events:
            return None

        infra_events = [
            e for e in model.events
            if any(kw in e.message.lower() for kw in infra_keywords)
        ]

        if len(infra_events) > len(model.events) * 0.15 and len(infra_events) > 5:
            return MotifSignature(
                motif_type=MotifType.INFRASTRUCTURE_CENTRALIZATION,
                confidence=0.6,
                severity=0.4,
                description=f"Infrastructure centralization trend: {len(infra_events)}/{len(model.events)} commits touch infra.",
                indicators=[
                    f"{len(infra_events)} infrastructure commits",
                    f"{len(infra_events)/max(len(model.events),1):.0%} of total commits",
                ],
                health=MotifHealth.NEUTRAL,
                recommended_action="Ensure infra changes are reviewed. Consider infrastructure-as-code practices.",
            )

        return None

    def _detect_accidental_framework(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 3:
            return None

        core_files_touched = Counter()
        for e in model.events:
            if e.event_type in (
                TemporalEventType.FEATURE_ADD, TemporalEventType.ARCHITECTURE_CHANGE
            ):
                for sub in e.subsystems:
                    core_files_touched[sub] += 1

        if core_files_touched:
            top_subsystem = core_files_touched.most_common(1)[0]
            concentration = top_subsystem[1] / max(sum(core_files_touched.values()), 1)

            if concentration > 0.4 and len(core_files_touched) > 3:
                return MotifSignature(
                    motif_type=MotifType.ACCIDENTAL_FRAMEWORK,
                    confidence=min(1.0, concentration * 1.5),
                    severity=0.7,
                    description=f"'{top_subsystem[0]}' is receiving {concentration:.0%} of architectural changes, suggesting it is becoming an accidental framework.",
                    indicators=[
                        f"{concentration:.0%} of arch changes in {top_subsystem[0]}",
                        f"Subsystems: {len(core_files_touched)}",
                    ],
                    health=MotifHealth.UNHEALTHY,
                    involved_subsystems=[top_subsystem[0]],
                    recommended_action="Evaluate whether {top_subsystem[0]} should be formalized as a platform or broken apart.",
                )

        return None

    def _detect_refactor_cascade(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.events) < 20:
            return None

        refactors = sorted(
            [e for e in model.events if e.event_type == TemporalEventType.REFACTOR],
            key=lambda e: e.timestamp,
        )

        if len(refactors) >= 5:
            gaps = []
            for i in range(1, len(refactors)):
                gap = refactors[i].timestamp - refactors[i - 1].timestamp
                gaps.append(gap)

            avg_gap = sum(gaps) / len(gaps) if gaps else float("inf")
            consecutive = sum(1 for g in gaps if g < avg_gap * 0.5)

            if consecutive > len(gaps) * 0.5 and consecutive > 2:
                return MotifSignature(
                    motif_type=MotifType.REFACTOR_CASCADE,
                    confidence=0.65,
                    severity=0.5,
                    description=f"Refactor cascade detected: {consecutive}/{len(gaps)} refactors are clustered tightly, suggesting reactive rather than planned refactoring.",
                    indicators=[
                        f"{len(refactors)} refactor events",
                        f"{consecutive} tightly clustered",
                        f"Avg gap: {avg_gap/86400:.1f} days",
                    ],
                    health=MotifHealth.UNHEALTHY,
                    recommended_action="Schedule dedicated refactoring sprints rather than intermixing with feature work.",
                )

        return None

    def _detect_ownership_concentration(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if not model.events:
            return None

        author_commit_count = Counter(e.author for e in model.events)
        if not author_commit_count:
            return None

        top_author = author_commit_count.most_common(1)[0]
        concentration = top_author[1] / len(model.events)

        if concentration > 0.5:
            return MotifSignature(
                motif_type=MotifType.OWNERSHIP_CONCENTRATION,
                confidence=min(1.0, concentration * 1.5),
                severity=0.6,
                description=f"Single author ({top_author[0]}) accounts for {concentration:.0%} of commits. High bus-factor risk.",
                indicators=[
                    f"Top author: {top_author[0]} ({concentration:.0%})",
                    f"Total authors: {len(author_commit_count)}",
                ],
                health=MotifHealth.UNHEALTHY,
                recommended_action="Distribute knowledge through pair programming, documentation, and task rotation.",
            )

        return None

    def _detect_boiling_ocean(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 5:
            return None

        churn_rates = [s.churn_rate for s in model.timeline.snapshots]
        if len(churn_rates) < 3:
            return None

        mean_churn = sum(churn_rates) / len(churn_rates)
        recent = churn_rates[-3:]
        rising = recent[-1] > recent[0] and recent[-1] > mean_churn * 1.2

        if rising:
            return MotifSignature(
                motif_type=MotifType.BOILING_OCEAN,
                confidence=0.7,
                severity=0.7,
                description="Churn rate is rising across the codebase. Many files being modified without clear direction.",
                indicators=[
                    f"Current churn: {churn_rates[-1]:.1f}",
                    f"Mean churn: {mean_churn:.1f}",
                    "Rising trend",
                ],
                health=MotifHealth.CRITICAL,
                recommended_action="Investigate root cause of increasing churn. Consider a stabilization period.",
            )

        return None

    def _detect_decaying_core(self, model: EvolutionModel) -> Optional[MotifSignature]:
        if len(model.timeline.snapshots) < 3:
            return None

        complexity_trend = model.timeline.trends.get("avg_file_complexity")
        if not complexity_trend or len(complexity_trend.values) < 2:
            return None

        complexity_rising = complexity_trend.slope > 0
        bug_trend = sum(
            1 for e in model.events[-50:] if e.event_type == TemporalEventType.BUG_FIX
        ) if len(model.events) >= 50 else 0

        core_subsystems = list(model.subsystem_history.keys())[:3]
        core_bugs = sum(
            1 for e in model.events[-100:]
            if e.event_type == TemporalEventType.BUG_FIX
            and any(s in core_subsystems for s in e.subsystems)
        ) if model.events else 0

        if complexity_rising and core_bugs > 5:
            return MotifSignature(
                motif_type=MotifType.DECAYING_CORE,
                confidence=0.7,
                severity=0.8,
                description="Core subsystems are accumulating complexity and bugs, indicating architectural decay.",
                indicators=[
                    f"Complexity trend: {'rising' if complexity_rising else 'stable'}",
                    f"Core bug count: {core_bugs}",
                    f"Core subsystems: {', '.join(core_subsystems[:3])}",
                ],
                health=MotifHealth.CRITICAL,
                involved_subsystems=core_subsystems,
                recommended_action="Plan a core refactoring initiative. Extract stable interfaces, improve test coverage on core modules.",
            )

        return None

    def get_motifs(self) -> List[MotifSignature]:
        return self._motifs

    def get_clusters(self) -> List[MotifCluster]:
        return self._clusters

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motifs": [m.to_dict() for m in self._motifs],
            "clusters": [c.to_dict() for c in self._clusters],
        }
