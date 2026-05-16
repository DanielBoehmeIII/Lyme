from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ForecastEvidence:
    source: str = ""
    observation: str = ""
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "observation": self.observation[:100],
            "weight": self.weight,
        }


@dataclass
class CausalFactor:
    name: str = ""
    impact_direction: str = "positive"
    impact_magnitude: float = 0.0
    confidence: float = 0.5
    evidence: List[ForecastEvidence] = field(default_factory=list)
    secondary_effects: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "impact_direction": self.impact_direction,
            "impact_magnitude": self.impact_magnitude,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence[:3]],
            "secondary_effects": self.secondary_effects[:3],
        }


@dataclass
class HealthForecast:
    forecast_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    subsystem: str = "overall"
    horizon_days: int = 30
    current_health: float = 0.5
    projected_health: float = 0.5
    confidence: float = 0.5
    confidence_interval: Tuple[float, float] = (0.3, 0.7)
    trend: str = "stable"
    causal_factors: List[CausalFactor] = field(default_factory=list)
    evidence_trail: List[ForecastEvidence] = field(default_factory=list)
    maintenance_burden_projection: float = 0.5
    refactor_probability: float = 0.3
    scaling_risk: float = 0.3
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "forecast_id": self.forecast_id,
            "subsystem": self.subsystem,
            "horizon_days": self.horizon_days,
            "current_health": self.current_health,
            "projected_health": self.projected_health,
            "confidence": self.confidence,
            "confidence_interval": list(self.confidence_interval),
            "trend": self.trend,
            "causal_factors": [f.to_dict() for f in self.causal_factors[:5]],
            "evidence_trail": [e.to_dict() for e in self.evidence_trail[:5]],
            "maintenance_burden": self.maintenance_burden_projection,
            "refactor_probability": self.refactor_probability,
            "scaling_risk": self.scaling_risk,
        }


class CausalGraphAnalyzer:
    def __init__(self):
        self._edges: Dict[str, Dict[str, float]] = defaultdict(dict)

    def add_causal_edge(self, from_metric: str, to_metric: str, strength: float):
        self._edges[from_metric][to_metric] = strength

    def get_downstream_effects(self, metric: str, depth: int = 3) -> List[Dict[str, Any]]:
        effects = []
        visited: Set[str] = set()

        def traverse(current: str, remaining_depth: int, path_strength: float):
            if remaining_depth <= 0 or current in visited:
                return
            visited.add(current)
            for neighbor, strength in self._edges.get(current, {}).items():
                combined = path_strength * strength
                effects.append({
                    "source": current,
                    "target": neighbor,
                    "path_strength": combined,
                    "remaining_depth": remaining_depth - 1,
                })
                traverse(neighbor, remaining_depth - 1, combined)

        traverse(metric, depth, 1.0)
        effects.sort(key=lambda x: -x["path_strength"])
        return effects[:20]

    def find_root_causes(self, symptoms: List[str], depth: int = 3) -> Dict[str, float]:
        causes: Dict[str, float] = defaultdict(float)

        for symptom in symptoms:
            for source, targets in self._edges.items():
                if symptom in targets:
                    strength = targets[symptom]
                    causes[source] += strength

                    for root, intermediates in self._edges.items():
                        if source in intermediates:
                            causes[root] += strength * intermediates[source] * 0.5

        return dict(sorted(causes.items(), key=lambda x: -x[1])[:10])


class HealthForecastingEngine:
    def __init__(self):
        self._health_history: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self._dependency_trends: Dict[str, List[float]] = defaultdict(list)
        self._invariant_violations: Dict[str, int] = defaultdict(int)
        self._causal_analyzer = CausalGraphAnalyzer()
        self._forecasts: List[HealthForecast] = []

    def record_health(self, subsystem: str, health: float, timestamp: Optional[float] = None):
        self._health_history[subsystem].append((timestamp or time.time(), health))

    def record_dependency_trend(self, metric: str, value: float):
        self._dependency_trends[metric].append(value)

    def record_invariant_violation(self, subsystem: str):
        self._invariant_violations[subsystem] += 1

    def add_causal_edge(self, from_metric: str, to_metric: str, strength: float = 0.5):
        self._causal_analyzer.add_causal_edge(from_metric, to_metric, strength)

    def forecast(self, subsystem: str = "overall", horizon_days: int = 30) -> HealthForecast:
        history = self._health_history.get(subsystem, [])
        forecast = HealthForecast(
            subsystem=subsystem,
            horizon_days=horizon_days,
        )

        if len(history) < 2:
            forecast.current_health = history[-1][1] if history else 0.5
            forecast.confidence = 0.2
            forecast.evidence_trail.append(ForecastEvidence(
                source="health_history",
                observation="Insufficient data for reliable forecast",
                weight=0.3,
            ))
            self._forecasts.append(forecast)
            return forecast

        values = [v for _, v in history]
        timestamps = [t for t, _ in history]

        n = len(values)
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(values) / n

        slope = 0.0
        r_squared = 0.0
        if n >= 2:
            num = sum((xs[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            den = sum((x - x_mean) ** 2 for x in xs)
            slope = num / den if den != 0 else 0.0

            if den > 0:
                ss_reg = num ** 2 / den
                ss_tot = sum((v - y_mean) ** 2 for v in values)
                r_squared = ss_reg / ss_tot if ss_tot > 0 else 0

        projected = max(0.0, min(1.0, values[-1] + slope * horizon_days / max(n, 1)))

        std = math.sqrt(sum((v - y_mean) ** 2 for v in values) / n) if n > 0 else 0.1
        ci_lower = max(0.0, projected - 1.96 * std)
        ci_upper = min(1.0, projected + 1.96 * std)

        if slope > 0.01:
            trend = "improving"
        elif slope < -0.01:
            trend = "degrading"
        else:
            trend = "stable"

        previous_trend = self._dependency_trends.get(f"{subsystem}_dependency", [])
        maintenance_burden = 0.5
        if previous_trend:
            recent = previous_trend[-5:]
            if recent:
                avg_recent = sum(recent) / len(recent)
                maintenance_burden = min(1.0, avg_recent * 0.5 + (1.0 - projected) * 0.5)

        violations = self._invariant_violations.get(subsystem, 0)
        refactor_prob = min(1.0, 0.2 + violations * 0.05 + max(0, 0.5 - projected) * 0.3)
        scaling_risk = min(1.0, 0.2 + (1.0 - projected) * 0.4 + max(0, slope * -10) * 0.3)

        forecast.current_health = values[-1]
        forecast.projected_health = projected
        forecast.confidence = min(1.0, max(0.1, r_squared * (1 - 1 / max(n, 1))))
        forecast.confidence_interval = (ci_lower, ci_upper)
        forecast.trend = trend
        forecast.maintenance_burden_projection = maintenance_burden
        forecast.refactor_probability = refactor_prob
        forecast.scaling_risk = scaling_risk

        forecast.evidence_trail = [
            ForecastEvidence(source="health_trend", observation=f"Health slope: {slope:.4f}/day", weight=0.8),
            ForecastEvidence(source="regression", observation=f"R² = {r_squared:.3f} with {n} data points", weight=0.6),
            ForecastEvidence(source="projection", observation=f"Projected health in {horizon_days}d: {projected:.3f}", weight=0.5),
        ]

        if violations > 0:
            forecast.evidence_trail.append(ForecastEvidence(
                source="invariant_violations",
                observation=f"{violations} invariant violations recorded",
                weight=min(1.0, violations * 0.2),
            ))

        causal_factors = self._causal_analyzer.find_root_causes([subsystem])
        for cause, strength in causal_factors.items():
            forecast.causal_factors.append(CausalFactor(
                name=cause,
                impact_direction="negative" if strength < 0.5 else "positive",
                impact_magnitude=strength,
                confidence=min(1.0, strength * 0.8),
                evidence=[ForecastEvidence(
                    source="causal_graph",
                    observation=f"Causal path strength: {strength:.3f}",
                )],
            ))

        self._forecasts.append(forecast)
        return forecast

    def forecast_all(self, subsystems: List[str], horizon_days: int = 30) -> List[HealthForecast]:
        return [self.forecast(sub, horizon_days) for sub in subsystems]

    def get_forecast_summary(self) -> Dict[str, Any]:
        if not self._forecasts:
            return {"error": "no forecasts"}

        latest = self._forecasts[-1]
        degrading = [f for f in self._forecasts if f.trend == "degrading"]
        improving = [f for f in self._forecasts if f.trend == "improving"]

        return {
            "forecasts_made": len(self._forecasts),
            "latest_forecast": latest.to_dict(),
            "degrading_count": len(degrading),
            "improving_count": len(improving),
            "avg_confidence": sum(f.confidence for f in self._forecasts) / max(len(self._forecasts), 1),
            "highest_risk": max(self._forecasts, key=lambda f: f.scaling_risk).to_dict() if self._forecasts else None,
            "needs_refactor": [f.subsystem for f in self._forecasts if f.refactor_probability > 0.6],
        }

    def get_causal_explanation(self, subsystem: str) -> Dict[str, Any]:
        forecast = next(
            (f for f in self._forecasts if f.subsystem == subsystem),
            None,
        )
        if not forecast:
            return {"error": f"No forecast for subsystem '{subsystem}'"}

        return {
            "subsystem": subsystem,
            "projected_health": forecast.projected_health,
            "trend": forecast.trend,
            "confidence": forecast.confidence,
            "causal_factors": [f.to_dict() for f in forecast.causal_factors],
            "evidence_trail": [e.to_dict() for e in forecast.evidence_trail],
            "recommendations": self._generate_recommendations(forecast),
        }

    def _generate_recommendations(self, forecast: HealthForecast) -> List[str]:
        recs = []
        if forecast.projected_health < 0.3:
            recs.append("CRITICAL: Immediate intervention required. Schedule architectural review.")
        elif forecast.projected_health < 0.5:
            recs.append("WARNING: Health projected to decline. Plan preventive maintenance.")

        if forecast.refactor_probability > 0.6:
            recs.append(f"High refactor probability ({forecast.refactor_probability:.0%}). Begin planning refactoring.")

        if forecast.scaling_risk > 0.6:
            recs.append(f"High scaling risk ({forecast.scaling_risk:.0%}). Review architectural boundaries.")

        if forecast.maintenance_burden_projection > 0.7:
            recs.append("Maintenance burden is high. Consider dedicated maintenance sprints.")

        if not recs:
            recs.append("No critical issues forecast. Continue standard monitoring.")

        return recs[:5]
