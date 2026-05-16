from __future__ import annotations

import copy
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .edit_simulation import (
    EditHypothesis, EditSimulationResult, EditSimulator, SimulationConfig,
)
from .drift_detection import DriftDetector, DriftMetric, DriftReport


class TwinSyncState(str, Enum):
    SYNCHRONIZED = "synchronized"
    BEHIND = "behind"
    DIVERGED = "diverged"
    STALE = "stale"
    UNSYNCHRONIZED = "unsynchronized"


@dataclass
class TwinConfig:
    name: str = ""
    repository: str = ""
    branch: str = "main"
    auto_sync: bool = True
    sync_interval_seconds: float = 3600.0
    max_snapshots: int = 50
    simulation_depth: int = 3
    confidence_threshold: float = 0.3
    track_evolution_trends: bool = True
    track_runtime_behavior: bool = True
    track_team_conventions: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "repository": self.repository,
            "branch": self.branch,
            "auto_sync": self.auto_sync,
            "sync_interval_seconds": self.sync_interval_seconds,
            "max_snapshots": self.max_snapshots,
            "simulation_depth": self.simulation_depth,
            "confidence_threshold": self.confidence_threshold,
            "track_evolution_trends": self.track_evolution_trends,
            "track_runtime_behavior": self.track_runtime_behavior,
            "track_team_conventions": self.track_team_conventions,
        }


@dataclass
class TwinSnapshot:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    commit: str = ""
    branch: str = ""
    dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)
    file_structure: Dict[str, Any] = field(default_factory=dict)
    drift_report: Optional[DriftReport] = None
    risk_zones: List[Dict[str, Any]] = field(default_factory=list)
    evolution_velocity: float = 0.0
    subsystem_health: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "commit": self.commit,
            "branch": self.branch,
            "dependency_graph": {k: list(v) for k, v in self.dependency_graph.items()},
            "file_structure": self.file_structure,
            "drift_report": self.drift_report.to_dict() if self.drift_report else None,
            "risk_zones": self.risk_zones,
            "evolution_velocity": self.evolution_velocity,
            "subsystem_health": self.subsystem_health,
            "metadata": self.metadata,
        }


@dataclass
class TwinSimulationResult:
    simulation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    edit_result: Optional[EditSimulationResult] = None
    forecast_result: Optional[TwinForecast] = None
    risk_projection: Dict[str, Any] = field(default_factory=dict)
    affected_snapshots: List[str] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "simulation_id": self.simulation_id,
            "timestamp": self.timestamp,
            "edit_result": self.edit_result.to_dict() if self.edit_result else None,
            "forecast_result": self.forecast_result.to_dict() if self.forecast_result else None,
            "risk_projection": self.risk_projection,
            "affected_snapshots": self.affected_snapshots,
            "confidence": self.confidence,
            "summary": self.summary,
        }


@dataclass
class TwinForecast:
    timeframe: str = "short_term"
    horizon_days: float = 30.0
    predicted_drift: float = 0.0
    subsystem_degradation_risk: List[Dict[str, Any]] = field(default_factory=list)
    likely_breakage_zones: List[Dict[str, Any]] = field(default_factory=list)
    evolution_trend: str = "stable"
    confidence: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timeframe": self.timeframe,
            "horizon_days": self.horizon_days,
            "predicted_drift": self.predicted_drift,
            "subsystem_degradation_risk": self.subsystem_degradation_risk,
            "likely_breakage_zones": self.likely_breakage_zones,
            "evolution_trend": self.evolution_trend,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
        }


class RepositoryTwin:
    def __init__(self, config: TwinConfig = None):
        self.config = config or TwinConfig()
        self.snapshots: List[TwinSnapshot] = []
        self.edit_simulator = EditSimulator(SimulationConfig(
            max_propagation_depth=self.config.simulation_depth,
            min_confidence_threshold=self.config.confidence_threshold,
        ))
        self.drift_detector = DriftDetector()
        self._sync_state = TwinSyncState.UNSYNCHRONIZED
        self._created_at = time.time()
        self._last_sync: Optional[float] = None
        self._failure_history: List[Dict[str, Any]] = []

    def sync(self, file_structure: Dict[str, Any] = None,
             dependency_graph: Dict[str, Set[str]] = None,
             source_files: Dict[str, str] = None,
             test_files: Dict[str, str] = None,
             git_history: List[Dict[str, Any]] = None,
             runtime_traces: List[Dict[str, Any]] = None,
             commit: str = "", branch: str = ""):
        drift_report = self.drift_detector.analyze(
            file_structure=file_structure or {},
            dependency_graph=dependency_graph,
            source_files=source_files,
            test_files=test_files,
            git_history=git_history,
            previous_report=self.snapshots[-1].drift_report if self.snapshots else None,
        )

        risk_zones = self._identify_risk_zones(
            drift_report, dependency_graph, source_files
        )

        subsystem_health = self._compute_subsystem_health(drift_report)

        snapshot = TwinSnapshot(
            commit=commit or "",
            branch=branch or self.config.branch,
            dependency_graph=dependency_graph or {},
            file_structure=file_structure or {},
            drift_report=drift_report,
            risk_zones=risk_zones,
            evolution_velocity=self._compute_evolution_velocity(git_history),
            subsystem_health=subsystem_health,
        )
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.config.max_snapshots:
            self.snapshots = self.snapshots[-self.config.max_snapshots:]

        self._sync_state = TwinSyncState.SYNCHRONIZED
        self._last_sync = time.time()

        return snapshot

    def simulate_edit(self, edit: EditHypothesis,
                      source_files: Dict[str, str] = None,
                      test_files: Dict[str, str] = None) -> TwinSimulationResult:
        current = self.current_snapshot()
        if not current:
            return TwinSimulationResult(
                summary="No snapshot available - sync twin first",
                confidence=0.0,
            )

        edit_result = self.edit_simulator.simulate(
            edit=edit,
            dependency_graph=current.dependency_graph,
            source_files=source_files,
            test_files=test_files,
        )

        risk_projection = self._project_risk(edit_result, current)
        affected = [
            s.snapshot_id for s in self.snapshots[-5:]
            if self._is_affected(edit, s)
        ]

        return TwinSimulationResult(
            edit_result=edit_result,
            risk_projection=risk_projection,
            affected_snapshots=affected,
            confidence=edit_result.confidence.value,
            summary=f"Edit simulation: risk={edit_result.overall_risk:.1%}, confidence={edit_result.confidence.value}",
        )

    def forecast(self, horizon_days: float = 30.0) -> TwinForecast:
        current = self.current_snapshot()
        if not current or not current.drift_report:
            return TwinForecast(confidence=0.0)

        drift_trend = self._compute_drift_trend()
        degraded_subsystems = self._find_degrading_subsystems(current)
        breakage_zones = self._project_breakage_zones(current)

        confidence = min(1.0, len(self.snapshots) * 0.1 + 0.2)

        recommendations = []
        if drift_trend > 0.3:
            recommendations.append("Architectural drift accelerating - consider stabilization sprints")
        if degraded_subsystems:
            worst = max(degraded_subsystems, key=lambda x: x.get("risk", 0))
            recommendations.append(
                f"Subsystem '{worst.get('subsystem', '')}' showing highest degradation risk ({worst.get('risk', 0):.1%})"
            )
        if breakage_zones:
            recommendations.append(f"{len(breakage_zones)} breakage zones projected - prioritize test coverage")
        if not recommendations:
            recommendations.append("Architecture appears stable")

        return TwinForecast(
            timeframe="medium_term" if horizon_days > 60 else "short_term",
            horizon_days=horizon_days,
            predicted_drift=min(1.0, drift_trend + 0.1),
            subsystem_degradation_risk=degraded_subsystems[:5],
            likely_breakage_zones=breakage_zones[:5],
            evolution_trend="degrading" if drift_trend > 0.3 else "stable",
            confidence=confidence,
            recommendations=recommendations,
        )

    def current_snapshot(self) -> Optional[TwinSnapshot]:
        return self.snapshots[-1] if self.snapshots else None

    def get_evolution_history(self) -> List[Dict[str, Any]]:
        history = []
        for i, snap in enumerate(self.snapshots):
            entry = {
                "snapshot_id": snap.snapshot_id,
                "timestamp": snap.timestamp,
                "commit": snap.commit,
                "evolution_velocity": snap.evolution_velocity,
                "risk_zone_count": len(snap.risk_zones),
                "overall_drift": snap.drift_report.overall_drift_score if snap.drift_report else 0.0,
            }
            if i > 0:
                prev = self.snapshots[i - 1]
                entry["drift_delta"] = (
                    (snap.drift_report.overall_drift_score if snap.drift_report else 0) -
                    (prev.drift_report.overall_drift_score if prev.drift_report else 0)
                )
            history.append(entry)
        return history

    def get_risk_report(self) -> Dict[str, Any]:
        current = self.current_snapshot()
        if not current:
            return {"error": "No snapshot available"}
        return {
            "twin_name": self.config.name,
            "repository": self.config.repository,
            "branch": self.config.branch,
            "sync_state": self._sync_state.value,
            "age_seconds": time.time() - self._created_at,
            "last_sync": self._last_sync,
            "snapshot_count": len(self.snapshots),
            "overall_drift": current.drift_report.overall_drift_score if current.drift_report else 0.0,
            "risk_zones": current.risk_zones[:10],
            "subsystem_health": current.subsystem_health,
            "evolution_trend": self._compute_drift_trend(),
            "failure_history_count": len(self._failure_history),
        }

    def add_failure_event(self, failure: Dict[str, Any]):
        self._failure_history.append({
            **failure,
            "recorded_at": time.time(),
            "snapshot_id": self.current_snapshot().snapshot_id if self.current_snapshot() else "",
        })

    def compare_snapshots(self, snap_a_id: str, snap_b_id: str) -> Dict[str, Any]:
        snap_a = next((s for s in self.snapshots if s.snapshot_id == snap_a_id), None)
        snap_b = next((s for s in self.snapshots if s.snapshot_id == snap_b_id), None)
        if not snap_a or not snap_b:
            return {"error": "Snapshot not found"}
        return {
            "time_span": snap_b.timestamp - snap_a.timestamp,
            "drift_change": (
                (snap_b.drift_report.overall_drift_score if snap_b.drift_report else 0) -
                (snap_a.drift_report.overall_drift_score if snap_a.drift_report else 0)
            ),
            "velocity_change": snap_b.evolution_velocity - snap_a.evolution_velocity,
            "risk_zone_delta": len(snap_b.risk_zones) - len(snap_a.risk_zones),
            "subsystem_health_deltas": {
                sub: snap_b.subsystem_health.get(sub, 0) - snap_a.subsystem_health.get(sub, 0)
                for sub in set(list(snap_a.subsystem_health.keys()) + list(snap_b.subsystem_health.keys()))
                if abs(snap_b.subsystem_health.get(sub, 0) - snap_a.subsystem_health.get(sub, 0)) > 0.05
            },
        }

    def _identify_risk_zones(self, drift_report: DriftReport,
                              dependency_graph: Dict[str, Set[str]] = None,
                              source_files: Dict[str, str] = None) -> List[Dict[str, Any]]:
        zones = []
        for metric in drift_report.metrics:
            if metric.severity in ("critical", "high") or metric.current_value > metric.threshold * 1.5:
                zones.append({
                    "type": metric.metric_type.value,
                    "name": metric.name,
                    "file_path": metric.file_path,
                    "subsystem": metric.subsystem,
                    "severity": metric.severity.value,
                    "current_value": metric.current_value,
                    "threshold": metric.threshold,
                    "description": metric.description,
                })
        if dependency_graph:
            betweenness = self._compute_betweenness_centrality(dependency_graph)
            for file_path, centrality in sorted(betweenness.items(), key=lambda x: -x[1])[:5]:
                if centrality > 0.3:
                    zones.append({
                        "type": "high_betweenness",
                        "name": f"central:{file_path}",
                        "file_path": file_path,
                        "severity": "high",
                        "current_value": centrality,
                        "description": f"High betweenness centrality ({centrality:.2f}) - single point of failure risk",
                    })
        return zones[:20]

    def _compute_betweenness_centrality(self, graph: Dict[str, Set[str]]) -> Dict[str, float]:
        centrality: Dict[str, float] = defaultdict(float)
        nodes = list(graph.keys())
        for i, s in enumerate(nodes):
            stack = [(s, [s])]
            visited = {s}
            while stack:
                node, path = stack.pop()
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_path = path + [neighbor]
                        for intermediate in new_path[1:-1]:
                            centrality[intermediate] += 1.0
                        stack.append((neighbor, new_path))
        total = sum(centrality.values())
        if total > 0:
            for k in centrality:
                centrality[k] /= total
        return dict(centrality)

    def _compute_subsystem_health(self, drift_report: DriftReport) -> Dict[str, float]:
        health: Dict[str, float] = {}
        subsystem_metrics: Dict[str, List[DriftMetric]] = defaultdict(list)
        for metric in drift_report.metrics:
            if metric.subsystem:
                subsystem_metrics[metric.subsystem].append(metric)
        for subsystem, metrics in subsystem_metrics.items():
            if not metrics:
                health[subsystem] = 1.0
                continue
            avg_drift = sum(m.current_value for m in metrics) / len(metrics)
            health[subsystem] = max(0.0, 1.0 - avg_drift)
        return health

    def _compute_evolution_velocity(self, git_history: List[Dict[str, Any]] = None) -> float:
        if not git_history or len(git_history) < 2:
            return 0.0
        time_span = git_history[-1].get("timestamp", 0) - git_history[0].get("timestamp", 0)
        if time_span <= 0:
            return 0.0
        return len(git_history) / (time_span / 86400)

    def _compute_drift_trend(self) -> float:
        if len(self.snapshots) < 2:
            return 0.0
        recent = self.snapshots[-5:]
        if len(recent) < 2:
            return 0.0
        drift_values = [
            s.drift_report.overall_drift_score if s.drift_report else 0
            for s in recent
        ]
        if not drift_values:
            return 0.0
        deltas = [drift_values[i] - drift_values[i - 1] for i in range(1, len(drift_values))]
        return sum(deltas) / len(deltas) if deltas else 0.0

    def _find_degrading_subsystems(self, snapshot: TwinSnapshot) -> List[Dict[str, Any]]:
        degraded = []
        for subsystem, health in snapshot.subsystem_health.items():
            if health < 0.6:
                degraded.append({
                    "subsystem": subsystem,
                    "health": health,
                    "risk": 1.0 - health,
                })
        return degraded

    def _project_breakage_zones(self, snapshot: TwinSnapshot) -> List[Dict[str, Any]]:
        zones = []
        for risk in snapshot.risk_zones:
            zones.append({
                "file_path": risk.get("file_path", ""),
                "risk_type": risk.get("type", ""),
                "projected_risk": min(1.0, risk.get("current_value", 0) * 1.2),
                "timeframe": "short_term" if risk.get("current_value", 0) > 0.7 else "medium_term",
            })
        return zones

    def _project_risk(self, edit_result: EditSimulationResult,
                      snapshot: TwinSnapshot) -> Dict[str, Any]:
        return {
            "edit_risk": edit_result.overall_risk,
            "current_drift": snapshot.drift_report.overall_drift_score if snapshot.drift_report else 0,
            "combined_risk": min(1.0, edit_result.overall_risk * 0.6 + (
                snapshot.drift_report.overall_drift_score if snapshot.drift_report else 0
            ) * 0.4),
            "breakage_count": len(edit_result.breakage_estimates),
            "violation_count": len(edit_result.invariant_violations),
        }

    def _is_affected(self, edit: EditHypothesis, snapshot: TwinSnapshot) -> bool:
        return edit.file_path in snapshot.dependency_graph if snapshot.dependency_graph else False

    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "snapshot_count": len(self.snapshots),
            "latest_snapshot": self.current_snapshot().to_dict() if self.current_snapshot() else None,
            "sync_state": self._sync_state.value,
            "created_at": self._created_at,
            "last_sync": self._last_sync,
        }


class TwinCoordinator:
    def __init__(self):
        self._twins: Dict[str, RepositoryTwin] = {}

    def create_twin(self, config: TwinConfig) -> RepositoryTwin:
        twin = RepositoryTwin(config)
        self._twins[config.name or twin.config.name] = twin
        return twin

    def get_twin(self, name: str) -> Optional[RepositoryTwin]:
        return self._twins.get(name)

    def list_twins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": twin.config.name,
                "repository": twin.config.repository,
                "branch": twin.config.branch,
                "snapshot_count": len(twin.snapshots),
                "sync_state": twin._sync_state.value,
                "last_sync": twin._last_sync,
            }
            for twin in self._twins.values()
        ]

    def compare_twins(self, name_a: str, name_b: str) -> Dict[str, Any]:
        twin_a = self._twins.get(name_a)
        twin_b = self._twins.get(name_b)
        if not twin_a or not twin_b:
            return {"error": "Twin not found"}
        return {
            "twin_a": name_a,
            "twin_b": name_b,
            "drift_comparison": {
                name_a: twin_a.current_snapshot().drift_report.overall_drift_score if twin_a.current_snapshot() and twin_a.current_snapshot().drift_report else 0,
                name_b: twin_b.current_snapshot().drift_report.overall_drift_score if twin_b.current_snapshot() and twin_b.current_snapshot().drift_report else 0,
            },
            "subsystem_health_comparison": self._compare_health(twin_a, twin_b),
        }

    def _compare_health(self, twin_a: RepositoryTwin, twin_b: RepositoryTwin) -> Dict[str, Any]:
        snap_a = twin_a.current_snapshot()
        snap_b = twin_b.current_snapshot()
        if not snap_a or not snap_b:
            return {}
        all_subsystems = set(list(snap_a.subsystem_health.keys()) + list(snap_b.subsystem_health.keys()))
        comparison = {}
        for sub in all_subsystems:
            ha = snap_a.subsystem_health.get(sub, 0)
            hb = snap_b.subsystem_health.get(sub, 0)
            if abs(ha - hb) > 0.1:
                comparison[sub] = {"twin_a": ha, "twin_b": hb, "delta": hb - ha}
        return comparison
