from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..simulation.drift_detection import DriftDetector, DriftReport
from ..simulation.digital_twin import RepositoryTwin, TwinConfig
from ..runtime.runtime_store import RuntimeStore


@dataclass
class ObservatoryConfig:
    repository: str = ""
    branch: str = "main"
    poll_interval_seconds: float = 3600.0
    max_history_days: int = 365
    anomaly_sensitivity: float = 0.5
    trend_window_size: int = 7
    enable_continuous_analysis: bool = True
    enable_anomaly_detection: bool = True
    enable_trend_generation: bool = True
    enable_long_term_storage: bool = True
    storage_path: str = "./lyme-output/observatory"
    notification_callbacks: List[Callable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repository": self.repository,
            "branch": self.branch,
            "poll_interval_seconds": self.poll_interval_seconds,
            "max_history_days": self.max_history_days,
            "anomaly_sensitivity": self.anomaly_sensitivity,
            "trend_window_size": self.trend_window_size,
            "enable_continuous_analysis": self.enable_continuous_analysis,
            "enable_anomaly_detection": self.enable_anomaly_detection,
            "enable_trend_generation": self.enable_trend_generation,
            "enable_long_term_storage": self.enable_long_term_storage,
            "storage_path": self.storage_path,
        }


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class AnomalySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class EvolutionTrend:
    metric_name: str = ""
    subsystem: str = ""
    direction: TrendDirection = TrendDirection.STABLE
    values: List[Tuple[float, float]] = field(default_factory=list)
    slope: float = 0.0
    acceleration: float = 0.0
    volatility: float = 0.0
    forecast_next: Optional[float] = None
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "subsystem": self.subsystem,
            "direction": self.direction.value,
            "values": [(t, v) for t, v in self.values[-20:]],
            "slope": self.slope,
            "acceleration": self.acceleration,
            "volatility": self.volatility,
            "forecast_next": self.forecast_next,
            "confidence": self.confidence,
        }


@dataclass
class AnomalyEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    metric_name: str = ""
    subsystem: str = ""
    severity: AnomalySeverity = AnomalySeverity.INFO
    value: float = 0.0
    expected_range: Tuple[float, float] = (0.0, 0.0)
    deviation: float = 0.0
    description: str = ""
    possible_causes: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "metric_name": self.metric_name,
            "subsystem": self.subsystem,
            "severity": self.severity.value,
            "value": self.value,
            "expected_range": list(self.expected_range),
            "deviation": self.deviation,
            "description": self.description[:200],
            "possible_causes": self.possible_causes,
            "suggested_actions": self.suggested_actions,
        }


@dataclass
class SubsystemHealthReport:
    subsystem: str = ""
    health_score: float = 1.0
    drift_contribution: float = 0.0
    test_coverage_estimate: float = 0.0
    dependency_health: float = 1.0
    recent_changes: int = 0
    active_issues: List[str] = field(default_factory=list)
    trend: TrendDirection = TrendDirection.STABLE

    def to_dict(self) -> dict:
        return {
            "subsystem": self.subsystem,
            "health_score": self.health_score,
            "drift_contribution": self.drift_contribution,
            "test_coverage_estimate": self.test_coverage_estimate,
            "dependency_health": self.dependency_health,
            "recent_changes": self.recent_changes,
            "active_issues": self.active_issues[:5],
            "trend": self.trend.value,
        }


@dataclass
class TechnicalDebtIndicator:
    name: str = ""
    subsystem: str = ""
    severity: AnomalySeverity = AnomalySeverity.INFO
    estimated_effort: str = "medium"
    description: str = ""
    location: str = ""
    age_days: float = 0.0
    workaround_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "subsystem": self.subsystem,
            "severity": self.severity.value,
            "estimated_effort": self.estimated_effort,
            "description": self.description[:200],
            "location": self.location,
            "age_days": self.age_days,
            "workaround_count": self.workaround_count,
        }


@dataclass
class MigrationRisk:
    from_state: str = ""
    to_state: str = ""
    subsystem: str = ""
    risk_score: float = 0.0
    affected_components: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    suggested_approach: str = ""

    def to_dict(self) -> dict:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "subsystem": self.subsystem,
            "risk_score": self.risk_score,
            "affected_components": self.affected_components[:5],
            "breaking_changes": self.breaking_changes[:5],
            "suggested_approach": self.suggested_approach,
        }


@dataclass
class RepairPattern:
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    frequency: int = 1
    typical_files: List[str] = field(default_factory=list)
    typical_fix_type: str = ""
    avg_time_to_repair: float = 0.0
    recurrence_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "description": self.description[:200],
            "frequency": self.frequency,
            "typical_files": self.typical_files[:5],
            "typical_fix_type": self.typical_fix_type,
            "avg_time_to_repair": self.avg_time_to_repair,
            "recurrence_rate": self.recurrence_rate,
        }


@dataclass
class ObservatorySnapshot:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    commit: str = ""
    branch: str = ""
    subsystem_health: Dict[str, SubsystemHealthReport] = field(default_factory=dict)
    evolution_trends: List[EvolutionTrend] = field(default_factory=list)
    anomalies: List[AnomalyEvent] = field(default_factory=list)
    debt_indicators: List[TechnicalDebtIndicator] = field(default_factory=list)
    migration_risks: List[MigrationRisk] = field(default_factory=list)
    repair_patterns: List[RepairPattern] = field(default_factory=list)
    drift_report: Optional[DriftReport] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "commit": self.commit,
            "branch": self.branch,
            "subsystem_health": {k: v.to_dict() for k, v in self.subsystem_health.items()},
            "evolution_trends": [t.to_dict() for t in self.evolution_trends],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "debt_indicators": [d.to_dict() for d in self.debt_indicators],
            "migration_risks": [r.to_dict() for r in self.migration_risks],
            "repair_patterns": [p.to_dict() for p in self.repair_patterns],
            "drift_report": self.drift_report.to_dict() if self.drift_report else None,
            "metadata": self.metadata,
        }


class ObservatoryMode:
    def __init__(self, config: ObservatoryConfig = None):
        self.config = config or ObservatoryConfig()
        self._snapshots: List[ObservatorySnapshot] = []
        self._drift_detector = DriftDetector()
        self._runtime_store = RuntimeStore(
            base_dir=f"{self.config.storage_path}/runtime"
        )
        self._active = False
        self._start_time = 0.0
        self._observation_count = 0

    def start(self):
        self._active = True
        self._start_time = time.time()

    def stop(self):
        self._active = False

    def observe(self, file_structure: Dict[str, Any] = None,
                dependency_graph: Dict[str, Set[str]] = None,
                source_files: Dict[str, str] = None,
                test_files: Dict[str, str] = None,
                git_history: List[Dict[str, Any]] = None,
                runtime_traces: List[Dict[str, Any]] = None,
                commit: str = "", branch: str = "") -> ObservatorySnapshot:
        drift_report = self._drift_detector.analyze(
            file_structure=file_structure or {},
            dependency_graph=dependency_graph,
            source_files=source_files,
            test_files=test_files,
            git_history=git_history,
        )

        subsystem_health = self._compute_subsystem_health(drift_report)
        trends = self._compute_trends(drift_report)
        anomalies = self._detect_anomalies(drift_report, subsystem_health)
        debt = self._detect_technical_debt(drift_report, source_files)
        migrations = self._assess_migration_risks(drift_report, dependency_graph)
        repairs = self._extract_repair_patterns(git_history)

        snapshot = ObservatorySnapshot(
            commit=commit,
            branch=branch or self.config.branch,
            subsystem_health=subsystem_health,
            evolution_trends=trends,
            anomalies=anomalies,
            debt_indicators=debt,
            migration_risks=migrations,
            repair_patterns=repairs,
            drift_report=drift_report,
        )
        self._snapshots.append(snapshot)
        self._observation_count += 1

        if self.config.enable_long_term_storage:
            self._store_snapshot(snapshot)

        for callback in self.config.notification_callbacks:
            try:
                callback(snapshot)
            except Exception:
                pass

        return snapshot

    def get_current_state(self) -> Dict[str, Any]:
        current = self.current_snapshot()
        if not current:
            return {"status": "no_observations"}
        return {
            "status": "active" if self._active else "paused",
            "observations": self._observation_count,
            "uptime_seconds": time.time() - self._start_time if self._active else 0,
            "latest_snapshot": current.to_dict(),
            "snapshot_history": len(self._snapshots),
            "anomaly_count": sum(len(s.anomalies) for s in self._snapshots),
            "overall_health": self._compute_overall_health(current),
        }

    def current_snapshot(self) -> Optional[ObservatorySnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def get_snapshot_history(self, n: int = 10) -> List[ObservatorySnapshot]:
        return self._snapshots[-n:]

    def get_health_timeline(self, subsystem: str = "") -> List[Dict[str, Any]]:
        timeline = []
        for snap in self._snapshots:
            if subsystem and subsystem in snap.subsystem_health:
                health = snap.subsystem_health[subsystem]
                timeline.append({
                    "timestamp": snap.timestamp,
                    "subsystem": subsystem,
                    "health_score": health.health_score,
                })
            elif not subsystem:
                avg = sum(
                    h.health_score for h in snap.subsystem_health.values()
                ) / max(len(snap.subsystem_health), 1)
                timeline.append({
                    "timestamp": snap.timestamp,
                    "health_score": avg,
                    "subsystem_count": len(snap.subsystem_health),
                })
        return timeline

    def get_anomaly_history(self, severity: AnomalySeverity = None) -> List[AnomalyEvent]:
        all_anomalies = []
        for snap in self._snapshots:
            for anomaly in snap.anomalies:
                if severity is None or anomaly.severity == severity:
                    all_anomalies.append(anomaly)
        return sorted(all_anomalies, key=lambda a: a.timestamp, reverse=True)

    def get_forecast(self, horizon_days: float = 30.0) -> Dict[str, Any]:
        if len(self._snapshots) < 2:
            return {"error": "Insufficient data for forecast"}
        recent = self._snapshots[-min(30, len(self._snapshots)):]
        health_trend = []
        for snap in recent:
            avg_health = sum(
                h.health_score for h in snap.subsystem_health.values()
            ) / max(len(snap.subsystem_health), 1)
            health_trend.append(avg_health)
        if len(health_trend) >= 2:
            slope = (health_trend[-1] - health_trend[0]) / max(len(health_trend), 1)
            projected_health = max(0.0, min(1.0, health_trend[-1] + slope * horizon_days))
        else:
            projected_health = health_trend[-1] if health_trend else 0.5
        anomaly_rate = sum(len(s.anomalies) for s in recent) / max(len(recent), 1)
        projected_anomalies = int(anomaly_rate * horizon_days)
        worst_subsystem = min(
            recent[-1].subsystem_health.items(),
            key=lambda x: x[1].health_score,
            default=(None, None),
        )
        return {
            "horizon_days": horizon_days,
            "projected_health": projected_health,
            "projected_anomalies": projected_anomalies,
            "current_health": health_trend[-1] if health_trend else 0.5,
            "health_slope": slope if len(health_trend) >= 2 else 0,
            "at_risk_subsystem": worst_subsystem[0] if worst_subsystem[0] else None,
            "at_risk_health": worst_subsystem[1].health_score if worst_subsystem[1] else None,
        }

    def _compute_subsystem_health(self, drift_report: DriftReport) -> Dict[str, SubsystemHealthReport]:
        health: Dict[str, SubsystemHealthReport] = {}
        subsystem_metrics: Dict[str, List[Any]] = defaultdict(list)
        for metric in drift_report.metrics:
            if metric.subsystem:
                subsystem_metrics[metric.subsystem].append(metric)
        for subsystem, metrics in subsystem_metrics.items():
            avg_drift = sum(m.current_value for m in metrics) / len(metrics)
            critical = sum(1 for m in metrics if m.severity.value == "critical")
            health_score = max(0.0, 1.0 - avg_drift - critical * 0.1)
            health[subsystem] = SubsystemHealthReport(
                subsystem=subsystem,
                health_score=health_score,
                drift_contribution=avg_drift,
                active_issues=[m.description for m in metrics[:3]],
            )
        return health

    def _compute_trends(self, drift_report: DriftReport) -> List[EvolutionTrend]:
        trends = []
        metric_types: Dict[str, List[float]] = defaultdict(list)
        for metric in drift_report.metrics:
            metric_types[metric.metric_type.value].append(metric.current_value)
        for metric_type, values in metric_types.items():
            avg = sum(values) / len(values)
            if len(self._snapshots) >= 2:
                prev = self._snapshots[-1]
                prev_avg = sum(
                    m.current_value for m in prev.drift_report.metrics
                    if m.metric_type.value == metric_type
                ) / max(len(values), 1) if values else 0.5
                slope = avg - prev_avg
            else:
                slope = 0.0
            if slope > 0.05:
                direction = TrendDirection.DEGRADING
            elif slope < -0.05:
                direction = TrendDirection.IMPROVING
            else:
                direction = TrendDirection.STABLE
            trends.append(EvolutionTrend(
                metric_name=metric_type,
                direction=direction,
                values=[(time.time(), avg)],
                slope=slope,
                confidence=0.6,
            ))
        return trends

    def _detect_anomalies(self, drift_report: DriftReport,
                          subsystem_health: Dict[str, SubsystemHealthReport]) -> List[AnomalyEvent]:
        anomalies = []
        for metric in drift_report.metrics:
            if metric.current_value > metric.threshold * 2:
                anomalies.append(AnomalyEvent(
                    metric_name=metric.metric_type.value,
                    subsystem=metric.subsystem,
                    severity=AnomalySeverity.CRITICAL,
                    value=metric.current_value,
                    expected_range=(0, metric.threshold),
                    deviation=metric.current_value - metric.threshold,
                    description=f"{metric.metric_type.value} exceeds threshold: {metric.current_value:.2f} > {metric.threshold:.2f}",
                    possible_causes=["Accumulated technical debt", "Architecture violation"],
                    suggested_actions=["Review and refactor affected area", "Schedule stabilization sprint"],
                ))
        for sub, health in subsystem_health.items():
            if health.health_score < 0.3:
                anomalies.append(AnomalyEvent(
                    metric_name="subsystem_health",
                    subsystem=sub,
                    severity=AnomalySeverity.HIGH,
                    value=health.health_score,
                    expected_range=(0.5, 1.0),
                    deviation=0.5 - health.health_score,
                    description=f"Subsystem '{sub}' health critically low ({health.health_score:.2f})",
                    possible_causes=["Accumulated drift", "Insufficient maintenance"],
                    suggested_actions=["Targeted cleanup", "Dependency review"],
                ))
        return anomalies[:20]

    def _detect_technical_debt(self, drift_report: DriftReport,
                               source_files: Dict[str, str] = None) -> List[TechnicalDebtIndicator]:
        indicators = []
        for metric in drift_report.metrics:
            if metric.severity.value == "critical":
                indicators.append(TechnicalDebtIndicator(
                    name=metric.name,
                    subsystem=metric.subsystem,
                    severity=AnomalySeverity.CRITICAL,
                    description=f"Critical {metric.metric_type.value}: {metric.description}",
                    location=metric.file_path,
                ))
            elif metric.severity.value == "high":
                indicators.append(TechnicalDebtIndicator(
                    name=metric.name,
                    subsystem=metric.subsystem,
                    severity=AnomalySeverity.HIGH,
                    description=f"High {metric.metric_type.value}: {metric.description}",
                    location=metric.file_path,
                ))
        return indicators[:20]

    def _assess_migration_risks(self, drift_report: DriftReport,
                                 dependency_graph: Dict[str, Set[str]] = None) -> List[MigrationRisk]:
        risks = []
        for metric in drift_report.metrics:
            if metric.metric_type.value == "circular_dependency":
                risks.append(MigrationRisk(
                    from_state="circular",
                    to_state="acyclic",
                    subsystem=metric.subsystem or "unknown",
                    risk_score=metric.current_value,
                    affected_components=[metric.file_path] if metric.file_path else [],
                    breaking_changes=["Dependency cycle must be broken"],
                    suggested_approach="Extract shared dependency into separate module",
                ))
        return risks[:5]

    def _extract_repair_patterns(self, git_history: List[Dict[str, Any]]) -> List[RepairPattern]:
        if not git_history:
            return []
        fix_keywords = ["fix", "repair", "bug", "hotfix", "patch", "resolve"]
        fix_commits = [
            c for c in git_history
            if any(kw in c.get("message", "").lower() for kw in fix_keywords)
        ]
        file_fixes: Dict[str, int] = defaultdict(int)
        for c in fix_commits:
            for f in c.get("files", []):
                file_fixes[f] += 1
        return [
            RepairPattern(
                description=f"Frequent fixes in {file_path}",
                frequency=count,
                typical_files=[file_path],
                typical_fix_type="bug_fix",
                recurrence_rate=count / max(len(fix_commits), 1),
            )
            for file_path, count in sorted(file_fixes.items(), key=lambda x: -x[1])[:10]
        ]

    def _compute_overall_health(self, snapshot: ObservatorySnapshot) -> float:
        if not snapshot.subsystem_health:
            return 0.5
        return sum(
            h.health_score for h in snapshot.subsystem_health.values()
        ) / len(snapshot.subsystem_health)

    def _store_snapshot(self, snapshot: ObservatorySnapshot):
        import json
        import os
        path = os.path.join(
            self.config.storage_path, "snapshots", f"{snapshot.snapshot_id}.json"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)
