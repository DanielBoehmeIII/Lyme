from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict, deque
import json
import math


class PropagationDirection(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"


class PropagationSpeed(str, Enum):
    IMMEDIATE = "immediate"
    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"
    NEGLIGIBLE = "negligible"


@dataclass
class PropagationEvent:
    source: str
    target: str
    event_type: str
    timestamp: float
    impact_score: float
    delay: float
    confidence: float
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "impact_score": self.impact_score,
            "delay": self.delay,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class PropagationPath:
    chain: List[str]
    events: List[PropagationEvent]
    total_impact: float
    mean_delay: float
    bottleneck_nodes: List[str]
    estimated_arrival: float

    def to_dict(self) -> Dict:
        return {
            "chain": self.chain,
            "events": [e.to_dict() for e in self.events],
            "total_impact": self.total_impact,
            "mean_delay": self.mean_delay,
            "bottleneck_nodes": self.bottleneck_nodes,
            "estimated_arrival": self.estimated_arrival,
        }


@dataclass
class PropagationForecast:
    event_type: str
    source: str
    affected_libraries: List[Dict]
    total_affected: int
    total_impact_score: float
    mean_propagation_time: float
    max_depth: int
    confidence: float
    temporal_distribution: List[Dict]

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "affected_libraries": self.affected_libraries[:20],
            "total_affected": self.total_affected,
            "total_impact_score": self.total_impact_score,
            "mean_propagation_time": self.mean_propagation_time,
            "max_depth": self.max_depth,
            "confidence": self.confidence,
        }


class TemporalPropagationAnalyzer:
    def __init__(self, dependency_graph):
        self._graph = dependency_graph
        self._propagation_history: List[PropagationEvent] = []

    def record_propagation(self, event: PropagationEvent):
        self._propagation_history.append(event)

    def analyze_update_propagation(self, source_id: str, update_type: str = "major") -> PropagationForecast:
        affected = []
        visited = set()
        queue = deque([(source_id, 0, 0.0)])
        total_impact = 0.0
        max_depth = 0
        delays = []

        speed_map = {
            "major": (PropagationSpeed.FAST, 0.8),
            "minor": (PropagationSpeed.MODERATE, 0.4),
            "patch": (PropagationSpeed.SLOW, 0.2),
            "security": (PropagationSpeed.IMMEDIATE, 1.0),
        }
        speed, base_impact = speed_map.get(update_type, (PropagationSpeed.MODERATE, 0.5))

        while queue:
            current, depth, cumulative_delay = queue.popleft()
            if current in visited or depth > 15:
                continue
            visited.add(current)
            max_depth = max(max_depth, depth)

            dependents = self._graph.get_dependents(current) if hasattr(self._graph, 'get_dependents') else []
            for dep in dependents:
                dep_id = dep.id if hasattr(dep, 'id') else dep
                dep_name = dep.name if hasattr(dep, 'name') else dep_id
                delay = (depth + 1) * 0.5
                impact = base_impact * (1.0 / (depth + 1))
                total_impact += impact
                delays.append(delay)

                affected.append({
                    "library": dep_name,
                    "depth": depth + 1,
                    "delay_estimate": round(delay, 2),
                    "impact": round(impact, 3),
                    "propagation_speed": speed.value,
                })
                queue.append((dep_id, depth + 1, cumulative_delay + delay))

        mean_delay = sum(delays) / len(delays) if delays else 0

        return PropagationForecast(
            event_type=f"{update_type}_update",
            source=source_id,
            affected_libraries=affected,
            total_affected=len(affected),
            total_impact_score=round(total_impact, 3),
            mean_propagation_time=round(mean_delay, 2),
            max_depth=max_depth,
            confidence=0.8 if speed == PropagationSpeed.IMMEDIATE else 0.6,
            temporal_distribution=[
                {"depth": d, "count": sum(1 for a in affected if a["depth"] == d),
                 "total_impact": round(sum(a["impact"] for a in affected if a["depth"] == d), 3)}
                for d in range(1, max_depth + 1)
            ],
        )

    def analyze_security_vulnerability_propagation(self, source_id: str, cvss_score: float = 7.5) -> PropagationForecast:
        severity = "critical" if cvss_score >= 9.0 else "high" if cvss_score >= 7.0 else "medium"
        return self.analyze_update_propagation(source_id, "security")

    def estimate_ecosystem_impact(self, library_id: str, change_type: str) -> Dict:
        forecast = self.analyze_update_propagation(library_id, change_type)
        lib = self._graph.get_library(library_id) if hasattr(self._graph, 'get_library') else None
        centrality = self._graph.compute_centrality().get(library_id, 0) if hasattr(self._graph, 'compute_centrality') else 0

        return {
            "library": lib.name if lib else library_id,
            "change_type": change_type,
            "criticality": "critical" if forecast.total_affected > 50 else "high" if forecast.total_affected > 20 else "medium",
            "total_downstream_impact": forecast.total_affected,
            "total_impact_score": forecast.total_impact_score,
            "mean_propagation_delay": forecast.mean_propagation_time,
            "max_propagation_depth": forecast.max_depth,
            "centrality": centrality,
            "forecast_confidence": forecast.confidence,
            "recommendation": self._generate_recommendation(forecast, change_type),
        }

    def _generate_recommendation(self, forecast: PropagationForecast, change_type: str) -> str:
        if forecast.total_affected == 0:
            return "No downstream dependents. Safe to proceed."
        if forecast.total_affected < 5:
            return f"Minor impact. Notify {forecast.total_affected} downstream dependents."
        if forecast.total_affected < 20:
            return f"Moderate impact. Coordinate release with {forecast.total_affected} dependents. Consider deprecation warnings."
        if forecast.total_affected < 100:
            return (f"Large impact across {forecast.total_affected} libraries. "
                    f"Phased rollout recommended. Provide migration guide and codemods.")
        return (f"Ecosystem-wide impact ({forecast.total_affected} libraries). "
                f"Requires release candidate period, migration guide, codemods, and community coordination.")

    def analyze_breaking_change_propagation(self, source_id: str, breaking_level: str = "major") -> PropagationForecast:
        return self.analyze_update_propagation(source_id, breaking_level)

    def find_high_risk_dependency_chains(self) -> List[PropagationPath]:
        chains = []
        for lib_id, lib in enumerate(self._graph.libraries[:50] if hasattr(self._graph, 'libraries') else []):
            lib_id = lib.id if hasattr(lib, 'id') else str(lib_id)
            forecast = self.analyze_update_propagation(lib_id, "major")
            if forecast.total_affected > 10:
                path = PropagationPath(
                    chain=[lib_id] + [a["library"] for a in forecast.affected_libraries[:5]],
                    events=[],
                    total_impact=forecast.total_impact_score,
                    mean_delay=forecast.mean_propagation_time,
                    bottleneck_nodes=[a["library"] for a in forecast.affected_libraries if a["depth"] <= 2][:5],
                    estimated_arrival=forecast.mean_propagation_time,
                )
                chains.append(path)
        return sorted(chains, key=lambda x: -x.total_impact)[:20]

    def temporal_propagation_heatmap(self) -> Dict:
        if not self._propagation_history:
            return {"events": [], "summary": "No propagation history recorded"}

        type_dist = defaultdict(int)
        source_dist = defaultdict(int)
        total_impact = 0

        for event in self._propagation_history:
            type_dist[event.event_type] += 1
            source_dist[event.source] += 1
            total_impact += event.impact_score

        return {
            "total_events": len(self._propagation_history),
            "type_distribution": dict(type_dist),
            "source_distribution": dict(source_dist),
            "total_impact_accumulated": round(total_impact, 3),
            "high_impact_events": [e.to_dict() for e in self._propagation_history if e.impact_score > 0.7][:20],
        }

    def save_history(self, path: str):
        data = [e.to_dict() for e in self._propagation_history]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_history(self, path: str):
        with open(path) as f:
            data = json.load(f)
        for ed in data:
            self._propagation_history.append(PropagationEvent(**ed))
