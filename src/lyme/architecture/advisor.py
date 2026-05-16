from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import math
import itertools


class ArchitectureType(str, Enum):
    MONOLITH = "monolith"
    MODULAR_MONOLITH = "modular_monolith"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    SERVERLESS = "serverless"
    CQRS = "cqrs"
    HEXAGONAL = "hexagonal"
    CLEAN_ARCH = "clean_architecture"
    LAYERED = "layered"
    P2P = "peer_to_peer"


@dataclass
class ArchitectureConstraint:
    name: str
    value: Any
    unit: str
    description: str

    def to_dict(self) -> Dict:
        return {"name": self.name, "value": self.value, "unit": self.unit, "description": self.description}


@dataclass
class ArchitectureSuggestion:
    architecture: ArchitectureType
    confidence: float
    fit_score: float
    strengths: List[str]
    weaknesses: List[str]
    predicted_failure_modes: List[str]
    hidden_complexity: List[str]
    maintenance_burden: str
    tradeoffs: Dict[str, float]
    migration_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "architecture": self.architecture.value,
            "confidence": self.confidence,
            "fit_score": self.fit_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "predicted_failure_modes": self.predicted_failure_modes,
            "hidden_complexity": self.hidden_complexity,
            "maintenance_burden": self.maintenance_burden,
            "tradeoffs": self.tradeoffs,
            "migration_path": self.migration_path,
        }


class ArchitectureAdvisor:
    def __init__(self):
        self._architecture_profiles = self._init_profiles()

    def _init_profiles(self) -> Dict[ArchitectureType, Dict]:
        return {
            ArchitectureType.MONOLITH: {
                "min_scale": 1, "max_scale": 20,
                "min_team": 1, "max_team": 10,
                "latency_sensitivity": "low",
                "reliability": 0.8,
                "strengths": ["Simple deployment", "Low operational cost", "Strong consistency",
                              "Easy debugging", "Low latency internal calls"],
                "weaknesses": ["Scaling limits", "Team coordination overhead", "Technology lock-in",
                               "Long build times", "Single point of failure"],
                "failure_modes": ["Big ball of mud", "Deployment bottlenecks", "Resource contention"],
                "hidden_complexity": ["Implicit module boundaries", "Global state", "Startup time"],
                "maintenance_burden": "medium",
            },
            ArchitectureType.MODULAR_MONOLITH: {
                "min_scale": 2, "max_scale": 50,
                "min_team": 2, "max_team": 25,
                "latency_sensitivity": "low",
                "reliability": 0.85,
                "strengths": ["Clear module boundaries", "Independent deployability", "Shared nothing modules",
                              "Good testability", "Reasonable operational cost"],
                "weaknesses": ["Requires discipline", "Module boundary erosion", "Shared database coupling",
                               "Module coordination overhead"],
                "failure_modes": ["Boundary erosion", "Module dependency cycles", "Shared mutable state"],
                "hidden_complexity": ["Module contract maintenance", "Cross-module transactions"],
                "maintenance_burden": "medium",
            },
            ArchitectureType.MICROSERVICES: {
                "min_scale": 20, "max_scale": 1000,
                "min_team": 5, "max_team": 100,
                "latency_sensitivity": "medium",
                "reliability": 0.7,
                "strengths": ["Independent scaling", "Team autonomy", "Technology diversity",
                              "Fault isolation", "Independent deployment"],
                "weaknesses": ["Network complexity", "Distributed transactions", "Operational overhead",
                               "Debugging difficulty", "Latency penalties"],
                "failure_modes": ["Network failures", "Distributed monolith", "Service mesh complexity",
                                  "Data consistency issues"],
                "hidden_complexity": ["Service discovery", "Distributed tracing", "Eventual consistency",
                                      "Schema evolution", "Retry storms"],
                "maintenance_burden": "high",
            },
            ArchitectureType.EVENT_DRIVEN: {
                "min_scale": 5, "max_scale": 500,
                "min_team": 3, "max_team": 40,
                "latency_sensitivity": "medium",
                "reliability": 0.75,
                "strengths": ["Loose coupling", "Scalability", "Auditability", "Reactive scaling",
                              "Event sourcing capabilities"],
                "weaknesses": ["Eventual consistency", "Debugging difficulty", "Schema evolution",
                               "Message ordering", "Dead letter handling"],
                "failure_modes": ["Event ordering issues", "Dead letters", "Cascading failures",
                                  "Schema versioning conflicts"],
                "hidden_complexity": ["Exactly-once processing", "Idempotency", "Schema registry",
                                      "Backpressure handling"],
                "maintenance_burden": "high",
            },
            ArchitectureType.SERVERLESS: {
                "min_scale": 1, "max_scale": 100,
                "min_team": 1, "max_team": 10,
                "latency_sensitivity": "high",
                "reliability": 0.6,
                "strengths": ["No server management", "Auto-scaling", "Pay-per-use",
                              "Rapid prototyping", "Low operational overhead"],
                "weaknesses": ["Cold starts", "Execution time limits", "Vendor lock-in",
                               "State management", "Debugging difficulty"],
                "failure_modes": ["Cold start latency", "Timeout failures", "Resource limits",
                                  "State synchronization issues"],
                "hidden_complexity": ["Cold start optimization", "Function orchestration", "State externalization"],
                "maintenance_burden": "low",
            },
        }

    def suggest(self, constraints: List[ArchitectureConstraint]) -> List[ArchitectureSuggestion]:
        parsed = self._parse_constraints(constraints)
        suggestions = []

        for arch_type, profile in self._architecture_profiles.items():
            score = self._compute_fit(parsed, profile)
            if score > 0.1:
                suggestion = ArchitectureSuggestion(
                    architecture=arch_type,
                    confidence=round(score, 3),
                    fit_score=round(score, 3),
                    strengths=list(profile["strengths"]),
                    weaknesses=list(profile["weaknesses"]),
                    predicted_failure_modes=list(profile["failure_modes"]),
                    hidden_complexity=list(profile["hidden_complexity"]),
                    maintenance_burden=profile["maintenance_burden"],
                    tradeoffs=self._compute_tradeoffs(arch_type, parsed),
                    migration_path=self._suggest_migration(arch_type, parsed),
                )
                suggestions.append(suggestion)

        return sorted(suggestions, key=lambda s: -s.fit_score)

    def _parse_constraints(self, constraints: List[ArchitectureConstraint]) -> Dict:
        parsed = {}
        for c in constraints:
            parsed[c.name] = c.value
        return parsed

    def _compute_fit(self, constraints: Dict, profile: Dict) -> float:
        score = 0.5

        if "scale" in constraints:
            scale = constraints["scale"]
            if profile["min_scale"] <= scale <= profile["max_scale"]:
                score += 0.2
            else:
                distance = min(abs(scale - profile["min_scale"]), abs(scale - profile["max_scale"]))
                score -= min(0.3, distance / 100)

        if "team_size" in constraints:
            team = constraints["team_size"]
            if profile["min_team"] <= team <= profile["max_team"]:
                score += 0.15
            else:
                score -= 0.15

        if "latency_sensitivity" in constraints:
            required = constraints["latency_sensitivity"]
            profile_sensitivity = profile["latency_sensitivity"]
            sensitivity_order = ["low", "medium", "high"]
            if required == profile_sensitivity:
                score += 0.1
            elif sensitivity_order.index(required) < sensitivity_order.index(profile_sensitivity):
                score -= 0.1

        if "reliability" in constraints:
            required_reliability = constraints["reliability"]
            if profile["reliability"] >= required_reliability:
                score += 0.1
            else:
                score -= 0.15

        return max(0.0, min(1.0, score))

    def _compute_tradeoffs(self, arch_type: ArchitectureType, constraints: Dict) -> Dict[str, float]:
        return {
            "simplicity": 0.9 if arch_type == ArchitectureType.MONOLITH else 0.3,
            "scalability": 0.9 if arch_type == ArchitectureType.MICROSERVICES else 0.4,
            "maintainability": 0.7 if arch_type == ArchitectureType.MODULAR_MONOLITH else 0.5,
            "development_speed": 0.8 if arch_type == ArchitectureType.MONOLITH else 0.4,
            "operational_complexity": 0.2 if arch_type == ArchitectureType.SERVERLESS else 0.6,
        }

    def _suggest_migration(self, target: ArchitectureType, constraints: Dict) -> Optional[str]:
        migrations = {
            ArchitectureType.MODULAR_MONOLITH: "Extract bounded contexts; add module boundaries; introduce API gates",
            ArchitectureType.MICROSERVICES: "Identify service boundaries; extract incrementally; strangler fig pattern",
            ArchitectureType.EVENT_DRIVEN: "Identify events; add message broker; implement event handlers",
            ArchitectureType.SERVERLESS: "Decompose into functions; add API gateway; externalize state",
        }
        return migrations.get(target)

    def compare_architectures(self, arch_a: ArchitectureType, arch_b: ArchitectureType) -> Dict:
        profile_a = self._architecture_profiles.get(arch_a, {})
        profile_b = self._architecture_profiles.get(arch_b, {})

        if not profile_a or not profile_b:
            return {"error": "Architecture type not found"}

        return {
            "comparison": f"{arch_a.value} vs {arch_b.value}",
            "a_advantages": list(set(profile_a.get("strengths", [])) - set(profile_b.get("strengths", []))),
            "b_advantages": list(set(profile_b.get("strengths", [])) - set(profile_a.get("strengths", []))),
            "a_failures": profile_a.get("failure_modes", []),
            "b_failures": profile_b.get("failure_modes", []),
            "a_maintenance_burden": profile_a.get("maintenance_burden", "unknown"),
            "b_maintenance_burden": profile_b.get("maintenance_burden", "unknown"),
            "suitability": self._decide_suitability(arch_a, arch_b),
        }

    def _decide_suitability(self, arch_a: ArchitectureType, arch_b: ArchitectureType) -> str:
        if arch_a == ArchitectureType.MODULAR_MONOLITH and arch_b == ArchitectureType.MICROSERVICES:
            return "Modular monolith is usually preferred unless team > 10 and scale > 50"
        if arch_a == ArchitectureType.MONOLITH and arch_b == ArchitectureType.MODULAR_MONOLITH:
            return "Modular monolith is almost always preferred over traditional monolith for new projects"
        if arch_a == ArchitectureType.SERVERLESS and arch_b == ArchitectureType.MICROSERVICES:
            return "Serverless suits variable workloads; microservices suit predictable high scale"
        return "Depends on specific constraints"

    def predict_failure_modes(self, architecture: ArchitectureType, 
                               constraints: List[ArchitectureConstraint]) -> List[Dict]:
        profile = self._architecture_profiles.get(architecture, {})
        parsed = self._parse_constraints(constraints)

        predictions = []
        for mode in profile.get("failure_modes", []):
            probability = 0.5
            if architecture == ArchitectureType.MICROSERVICES and "Network" in mode:
                probability = 0.7
            if architecture == ArchitectureType.EVENT_DRIVEN and "Event" in mode:
                probability = 0.6
            if architecture == ArchitectureType.MONOLITH and "Big ball" in mode:
                team = parsed.get("team_size", 5)
                probability = min(0.9, 0.3 + team * 0.05)

            predictions.append({
                "failure_mode": mode,
                "probability": round(probability, 2),
                "risk_level": "high" if probability > 0.6 else "medium" if probability > 0.3 else "low",
            })

        return sorted(predictions, key=lambda x: -x["probability"])

    def estimate_hidden_complexity(self, architecture: ArchitectureType) -> Dict:
        profile = self._architecture_profiles.get(architecture, {})
        hidden = profile.get("hidden_complexity", [])
        return {
            "architecture": architecture.value,
            "hidden_complexity_items": hidden,
            "estimated_overhead": "high" if len(hidden) > 4 else "medium" if len(hidden) > 2 else "low",
            "mitigation": "Invest in automation, documentation, and team training for each complexity item",
        }

    def architecture_search_space(self) -> List[Dict]:
        return [
            {
                "architecture": arch.value,
                "profiles": {
                    "scale_range": [p["min_scale"], p["max_scale"]],
                    "team_range": [p["min_team"], p["max_team"]],
                    "latency_sensitivity": p["latency_sensitivity"],
                    "reliability": p["reliability"],
                    "maintenance_burden": p["maintenance_burden"],
                },
            }
            for arch, p in self._architecture_profiles.items()
        ]
