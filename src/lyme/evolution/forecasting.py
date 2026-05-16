from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .evolution_model import EvolutionModel, EvolutionSnapshot, EvolutionTrend


class EvolutionForecaster:
    def forecast(self, model: EvolutionModel, horizon_snapshots: int = 5) -> Dict[str, Any]:
        forecasts: Dict[str, List[float]] = {}

        for metric_name, trend in model.timeline.trends.items():
            if len(trend.values) < 3:
                continue

            last_value = trend.values[-1]
            slope = trend.slope
            acceleration = trend.acceleration

            projected = []
            for i in range(1, horizon_snapshots + 1):
                next_val = last_value + slope * i + 0.5 * acceleration * (i ** 2)
                noise = (1 + (trend.volatility * 0.1) * (math.sin(i * 1.5)))
                projected.append(max(0, next_val * noise))
            forecasts[metric_name] = projected

        return {
            "horizon": horizon_snapshots,
            "forecasts": forecasts,
            "confidence": self._estimate_confidence(model),
        }

    def _estimate_confidence(self, model: EvolutionModel) -> float:
        if len(model.timeline.snapshots) < 3:
            return 0.1

        consistency = 0.0
        for trend in model.timeline.trends.values():
            if trend.volatility < 0.3:
                consistency += 0.2
            elif trend.volatility < 0.6:
                consistency += 0.1

        data_points = min(1.0, len(model.events) / 200)
        return min(1.0, 0.2 + consistency + data_points * 0.3)


class BottleneckPredictor:
    def predict(self, model: EvolutionModel) -> List[Dict[str, Any]]:
        bottlenecks: List[Dict[str, Any]] = []

        for metric_name, trend in model.timeline.trends.items():
            if trend.is_alarming:
                if metric_name == "avg_file_complexity" and trend.acceleration > 0:
                    bottlenecks.append({
                        "type": "complexity_growth",
                        "metric": metric_name,
                        "signal": "Average file complexity is accelerating",
                        "impact": "Files becoming harder to maintain, increased bug probability",
                        "urgency": "high" if trend.acceleration > 1 else "medium",
                        "suggested_action": "Plan refactoring of most complex files",
                    })
                elif metric_name == "total_lines" and trend.acceleration > 100:
                    bottlenecks.append({
                        "type": "uncontrolled_growth",
                        "metric": metric_name,
                        "signal": "Codebase growing at accelerating rate",
                        "impact": "Technical debt accumulation, slower development cycles",
                        "urgency": "high",
                        "suggested_action": "Review growth drivers, consider modularization",
                    })

        if len(model.timeline.snapshots) >= 3:
            latest = model.timeline.snapshots[-1]
            earliest = model.timeline.snapshots[0]
            file_growth = latest.metrics.total_files - earliest.metrics.total_files
            complexity_growth = latest.metrics.avg_file_complexity - earliest.metrics.avg_file_complexity

            if file_growth > 50 and complexity_growth > 0:
                bottlenecks.append({
                    "type": "scaling_pressure",
                    "metric": "files_and_complexity",
                    "signal": f"Codebase grew by {file_growth} files with increasing complexity",
                    "impact": "Architectural pressure: monolith tendencies emerging",
                    "urgency": "medium",
                    "suggested_action": "Evaluate modularization or service boundaries",
                })

        return bottlenecks[:10]
