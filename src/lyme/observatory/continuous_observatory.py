from __future__ import annotations

import json
import math
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .observatory import (
    ObservatoryConfig, ObservatorySnapshot, ObservatoryMode,
    EvolutionTrend as ObsEvolutionTrend,
    AnomalyEvent, AnomalySeverity, SubsystemHealthReport,
    TechnicalDebtIndicator, MigrationRisk, RepairPattern, TrendDirection,
)


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class RiskAlert:
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    risk_level: RiskLevel = RiskLevel.INFO
    category: str = ""
    title: str = ""
    description: str = ""
    affected_subsystems: List[str] = field(default_factory=list)
    metric_values: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    suggested_action: str = ""
    acknowledged: bool = False

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level.value,
            "category": self.category,
            "title": self.title[:100],
            "description": self.description[:200],
            "affected_subsystems": self.affected_subsystems[:3],
            "evidence": self.evidence[:3],
            "suggested_action": self.suggested_action[:200],
            "acknowledged": self.acknowledged,
        }


@dataclass
class StructuralForecast:
    forecast_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    metric: str = ""
    horizon_days: int = 30
    current_value: float = 0.0
    projected_value: float = 0.0
    confidence: float = 0.5
    confidence_lower: float = 0.0
    confidence_upper: float = 0.0
    trend: str = "stable"
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "forecast_id": self.forecast_id,
            "metric": self.metric,
            "horizon_days": self.horizon_days,
            "current_value": self.current_value,
            "projected_value": self.projected_value,
            "confidence": self.confidence,
            "confidence_interval": [self.confidence_lower, self.confidence_upper],
            "trend": self.trend,
            "evidence": self.evidence[:3],
        }


@dataclass
class DailySummary:
    date: str = ""
    subsystem_count: int = 0
    total_health_score: float = 0.5
    anomalies_detected: int = 0
    risk_alerts_active: int = 0
    metrics_tracked: int = 0
    trends_degrading: int = 0
    trends_improving: int = 0
    top_risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "subsystem_count": self.subsystem_count,
            "total_health": self.total_health_score,
            "anomalies": self.anomalies_detected,
            "alerts": self.risk_alerts_active,
            "degrading_trends": self.trends_degrading,
            "improving_trends": self.trends_improving,
            "top_risks": self.top_risks[:3],
            "recommendations": self.recommendations[:3],
        }


class ContinuousObservatory:
    def __init__(self, config: Optional[ObservatoryConfig] = None):
        self.config = config or ObservatoryConfig()
        self._observatory = ObservatoryMode(self.config)
        self._snapshots: List[ObservatorySnapshot] = []
        self._alerts: List[RiskAlert] = []
        self._forecasts: List[StructuralForecast] = []
        self._daily_summaries: List[DailySummary] = []
        self._health_history: Dict[str, List[float]] = defaultdict(list)
        self._metric_history: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self._active = False
        self._start_time = 0.0
        self._observation_count = 0
        self._alert_thresholds = {
            "health_critical": 0.3,
            "health_warning": 0.5,
            "anomaly_burst": 3,
            "trend_degradation": -0.05,
            "debt_critical": 0.7,
        }

    def start(self):
        self._active = True
        self._start_time = time.time()
        self._observatory.start()

    def stop(self):
        self._active = False
        self._observatory.stop()

    def observe(self, **kwargs) -> ObservatorySnapshot:
        snapshot = self._observatory.observe(**kwargs)
        self._snapshots.append(snapshot)
        self._observation_count += 1

        self._update_health_history(snapshot)
        self._update_metric_history(snapshot)
        self._detect_risks(snapshot)
        self._generate_forecasts()

        return snapshot

    def _update_health_history(self, snapshot: ObservatorySnapshot):
        for sub, health in snapshot.subsystem_health.items():
            self._health_history[sub].append(health.health_score)

    def _update_metric_history(self, snapshot: ObservatorySnapshot):
        for trend in snapshot.evolution_trends:
            for ts, val in trend.values:
                self._metric_history[trend.metric_name].append((ts, val))

    def _detect_risks(self, snapshot: ObservatorySnapshot):
        for sub, health in snapshot.subsystem_health.items():
            if health.health_score < self._alert_thresholds["health_critical"]:
                self._alerts.append(RiskAlert(
                    risk_level=RiskLevel.CRITICAL,
                    category="subsystem_health",
                    title=f"Critical health: {sub}",
                    description=f"Subsystem '{sub}' health at {health.health_score:.2f}",
                    affected_subsystems=[sub],
                    metric_values={"health": health.health_score},
                    evidence=[f"Health score: {health.health_score:.2f}",
                              f"Drift: {health.drift_contribution:.2f}"],
                    suggested_action="Immediate investigation and stabilization sprint required",
                ))

        anomaly_burst = len(snapshot.anomalies)
        if anomaly_burst >= self._alert_thresholds["anomaly_burst"]:
            self._alerts.append(RiskAlert(
                risk_level=RiskLevel.HIGH,
                category="anomaly_burst",
                title=f"Anomaly burst: {anomaly_burst} anomalies",
                description=f"Detected {anomaly_burst} anomalies in current observation",
                metric_values={"anomaly_count": float(anomaly_burst)},
                evidence=[f"{a.description[:80]}" for a in snapshot.anomalies[:3]],
                suggested_action="Review anomaly patterns and address root causes",
            ))

        vulnerability_count = sum(
            1 for t in snapshot.evolution_trends
            if t.direction in (TrendDirection.DEGRADING, TrendDirection.VOLATILE)
        )
        if vulnerability_count >= 3:
            self._alerts.append(RiskAlert(
                risk_level=RiskLevel.HIGH,
                category="trend_degradation",
                title=f"{vulnerability_count} degrading trends",
                description=f"Multiple metrics showing degradation patterns",
                metric_values={"degrading_count": float(vulnerability_count)},
                evidence=[f"{t.metric_name}: {t.direction.value}" for t in snapshot.evolution_trends[:3]],
                suggested_action="Prioritize addressing degrading trends in planning",
            ))

        debt_count = len(snapshot.debt_indicators)
        if debt_count >= 5:
            self._alerts.append(RiskAlert(
                risk_level=RiskLevel.MEDIUM,
                category="technical_debt",
                title=f"Technical debt: {debt_count} indicators",
                description=f"High number of technical debt indicators detected",
                metric_values={"debt_count": float(debt_count)},
                evidence=[f"{d.name}" for d in snapshot.debt_indicators[:3]],
                suggested_action="Schedule technical debt reduction sprint",
            ))

    def _generate_forecasts(self):
        if len(self._snapshots) < 3:
            return

        for metric_name, history in self._metric_history.items():
            if len(history) < 3:
                continue

            values = [v for _, v in history[-10:]]
            timestamps = [t for t, _ in history[-10:]]

            if len(values) >= 2:
                slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
                n = len(values)
                x_mean = sum(range(n)) / n
                y_mean = sum(values) / n
                ss_xx = sum((i - x_mean) ** 2 for i in range(n))
                ss_yy = sum((v - y_mean) ** 2 for v in values)
                r_squared = ((sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values)) ** 2) /
                             max(ss_xx * ss_yy, 0.001)) if ss_xx > 0 and ss_yy > 0 else 0

                horizon = 30
                projected = values[-1] + slope * horizon

                residual_std = math.sqrt(
                    sum((v - (y_mean + slope * (i - x_mean))) ** 2 for i, v in enumerate(values))
                    / max(n - 2, 1)
                ) if n > 2 else 0.1

                ci = 1.96 * residual_std * math.sqrt(1 + 1 / n + (horizon - x_mean) ** 2 / max(ss_xx, 0.001))

                trend_label = "improving" if slope < -0.01 else "degrading" if slope > 0.01 else "stable"

                forecast = StructuralForecast(
                    metric=metric_name,
                    horizon_days=horizon,
                    current_value=values[-1],
                    projected_value=projected,
                    confidence=min(1.0, max(0.1, r_squared)),
                    confidence_lower=projected - ci,
                    confidence_upper=projected + ci,
                    trend=trend_label,
                    evidence=[f"Slope: {slope:.4f}/day",
                              f"R²: {r_squared:.3f}",
                              f"Data points: {len(values)}"],
                )

                existing = [f for f in self._forecasts if f.metric == metric_name]
                if existing:
                    self._forecasts.remove(existing[0])
                self._forecasts.append(forecast)

    def generate_daily_summary(self) -> DailySummary:
        current = self.current_snapshot()
        if not current:
            return DailySummary(date=str(datetime.now().date()))

        health_scores = [h.health_score for h in current.subsystem_health.values()]
        avg_health = sum(health_scores) / max(len(health_scores), 1)

        degrading = sum(1 for t in current.evolution_trends
                        if t.direction in (TrendDirection.DEGRADING, TrendDirection.VOLATILE))
        improving = sum(1 for t in current.evolution_trends
                        if t.direction == TrendDirection.IMPROVING)

        active_alerts = [a for a in self._alerts if not a.acknowledged]

        summary = DailySummary(
            date=str(datetime.now().date()),
            subsystem_count=len(current.subsystem_health),
            total_health_score=avg_health,
            anomalies_detected=len(current.anomalies),
            risk_alerts_active=len(active_alerts),
            metrics_tracked=len(current.evolution_trends),
            trends_degrading=degrading,
            trends_improving=improving,
            top_risks=[a.title[:80] for a in active_alerts[:5]],
            recommendations=self._generate_recommendations(current),
        )
        self._daily_summaries.append(summary)
        return summary

    def _generate_recommendations(self, snapshot: ObservatorySnapshot) -> List[str]:
        recommendations = []

        for sub, health in snapshot.subsystem_health.items():
            if health.health_score < 0.4:
                recommendations.append(f"Critical: Schedule stabilization for '{sub}' subsystem")
            elif health.health_score < 0.6:
                recommendations.append(f"Attention: Review '{sub}' subsystem for architectural drift")

        for trend in snapshot.evolution_trends:
            if trend.direction == TrendDirection.DEGRADING:
                recommendations.append(f"Trend: {trend.metric_name} is degrading (slope={trend.slope:.3f})")

        if snapshot.debt_indicators:
            recommendations.append(
                f"Debt: {len(snapshot.debt_indicators)} technical debt items need addressing"
            )

        if not recommendations:
            recommendations.append("No critical issues detected. Continue monitoring.")

        return recommendations[:5]

    def current_snapshot(self) -> Optional[ObservatorySnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def get_health_trajectory(self, subsystem: str = "") -> Dict[str, Any]:
        if subsystem and subsystem in self._health_history:
            history = self._health_history[subsystem]
        else:
            all_histories = list(self._health_history.values())
            if not all_histories:
                return {"error": "no data"}
            min_len = min(len(h) for h in all_histories) if all_histories else 0
            history = [sum(h[i] for h in all_histories) / len(all_histories)
                       for i in range(min_len)] if min_len > 0 else []

        if len(history) >= 2:
            slope = (history[-1] - history[0]) / max(len(history) - 1, 1)
        else:
            slope = 0.0

        return {
            "subsystem": subsystem or "overall",
            "history": history,
            "current": history[-1] if history else 0.5,
            "trend_slope": slope,
            "direction": "improving" if slope > 0.01 else "degrading" if slope < -0.01 else "stable",
        }

    def get_active_alerts(self, min_level: RiskLevel = RiskLevel.LOW) -> List[RiskAlert]:
        levels = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.INFO: 4,
        }
        min_priority = levels.get(min_level, 0)
        return [
            a for a in self._alerts
            if not a.acknowledged and levels.get(a.risk_level, 99) <= min_priority
        ]

    def get_state(self) -> Dict[str, Any]:
        current = self.current_snapshot()
        return {
            "status": "active" if self._active else "paused",
            "uptime_seconds": time.time() - self._start_time if self._active else 0,
            "observations": self._observation_count,
            "alerts_active": len(self.get_active_alerts()),
            "forecasts": len(self._forecasts),
            "daily_summaries": len(self._daily_summaries),
            "latest_snapshot": current.to_dict() if current else None,
            "overall_health": self._compute_overall_health(current) if current else 0.5,
        }

    def _compute_overall_health(self, snapshot: ObservatorySnapshot) -> float:
        if not snapshot.subsystem_health:
            return 0.5
        return sum(h.health_score for h in snapshot.subsystem_health.values()) / len(snapshot.subsystem_health)
