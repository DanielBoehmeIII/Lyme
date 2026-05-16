from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict, Counter
import json
import math
import uuid


class ArchitecturePatternType(str, Enum):
    LAYERED_MONOLITH = "layered_monolith"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    MICROSERVICE_CLUSTER = "microservice_cluster"
    FRONTEND_STATE = "frontend_state"
    PLUGIN_SYSTEM = "plugin_system"
    ORCHESTRATION = "orchestration"
    PIPELINE = "pipeline"
    HEXAGONAL = "hexagonal"
    CLEAN_ARCHITECTURE = "clean_architecture"
    SERVERLESS = "serverless"
    P2P = "peer_to_peer"
    PUB_SUB = "publish_subscribe"
    SAGA = "saga"
    STRANGLER = "strangler_fig"
    BACKEND_FOR_FRONTEND = "backend_for_frontend"


class PatternMaturity(str, Enum):
    EMBRYONIC = "embryonic"
    EMERGING = "emerging"
    ESTABLISHED = "established"
    DOMINANT = "dominant"
    DECLINING = "declining"


@dataclass
class ArchitecturePattern:
    pattern_type: ArchitecturePatternType
    confidence: float
    evidence: List[str]
    components: List[str]
    relationships: List[Dict]
    variants: List[str]
    failure_tendencies: List[str]
    tradeoffs: Dict[str, float]
    maturity: PatternMaturity
    occurrence_count: int = 1

    def to_dict(self) -> Dict:
        return {
            "pattern_type": self.pattern_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "components": self.components,
            "relationships": self.relationships,
            "variants": self.variants,
            "failure_tendencies": self.failure_tendencies,
            "tradeoffs": self.tradeoffs,
            "maturity": self.maturity.value,
            "occurrence_count": self.occurrence_count,
        }


@dataclass
class ArchitectureFingerprint:
    patterns: List[ArchitecturePattern]
    complexity_score: float
    coupling_score: float
    cohesion_score: float
    layer_count: int
    service_count: int
    primary_pattern: Optional[ArchitecturePatternType]
    secondary_patterns: List[ArchitecturePatternType]

    def to_dict(self) -> Dict:
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "complexity_score": self.complexity_score,
            "coupling_score": self.coupling_score,
            "cohesion_score": self.cohesion_score,
            "layer_count": self.layer_count,
            "service_count": self.service_count,
            "primary_pattern": self.primary_pattern.value if self.primary_pattern else None,
            "secondary_patterns": [p.value for p in self.secondary_patterns],
        }


class ArchitecturePatternDiscovery:
    def __init__(self):
        self._known_patterns: Dict[ArchitecturePatternType, Dict] = self._init_known_patterns()
        self._discovered: Dict[str, ArchitectureFingerprint] = {}

    def _init_known_patterns(self) -> Dict[ArchitecturePatternType, Dict]:
        return {
            ArchitecturePatternType.LAYERED_MONOLITH: {
                "signals": ["presentation", "business", "data", "service", "repository", "controller"],
                "indicators": ["models/", "views/", "controllers/", "services/", "repositories/"],
                "failure_tendencies": ["Leaky abstraction", "Layer bypass", "Big ball of mud"],
                "tradeoffs": {"simplicity": 0.9, "testability": 0.5, "scalability": 0.3, "maintainability": 0.5},
            },
            ArchitecturePatternType.EVENT_DRIVEN: {
                "signals": ["event", "handler", "publish", "subscribe", "emit", "listen", "bus", "broker"],
                "indicators": ["events/", "handlers/", "listeners/", "broker", "message"],
                "failure_tendencies": ["Event ordering", "Dead letters", "Cascading failures", "Debugging difficulty"],
                "tradeoffs": {"simplicity": 0.3, "testability": 0.4, "scalability": 0.8, "decoupling": 0.9},
            },
            ArchitecturePatternType.MICROSERVICE_CLUSTER: {
                "signals": ["service", "api-gateway", "discovery", "config-server", "docker-compose", "k8s"],
                "indicators": ["services/", "api-gateway", "docker-compose", "Dockerfile", "helm"],
                "failure_tendencies": ["Network complexity", "Distributed transactions", "Service mesh overhead", "Debugging"],
                "tradeoffs": {"simplicity": 0.2, "testability": 0.5, "scalability": 0.9, "deployability": 0.8},
            },
            ArchitecturePatternType.CQRS: {
                "signals": ["command", "query", "separate", "read_model", "write_model", "mediator"],
                "indicators": ["commands/", "queries/", "read/", "write/", "dto/"],
                "failure_tendencies": ["Eventual consistency bugs", "Command/query mismatch", "Duplicated logic"],
                "tradeoffs": {"performance": 0.8, "complexity": 0.3, "scalability": 0.7, "consistency": 0.4},
            },
            ArchitecturePatternType.FRONTEND_STATE: {
                "signals": ["store", "reducer", "dispatch", "action", "state", "selector", "provider"],
                "indicators": ["store/", "reducers/", "actions/", "state/", "selectors/"],
                "failure_tendencies": ["State duplication", "Action spaghetti", "Selector performance", "Middleware complexity"],
                "tradeoffs": {"predictability": 0.8, "debugging": 0.7, "boilerplate": 0.3, "flexibility": 0.5},
            },
            ArchitecturePatternType.PLUGIN_SYSTEM: {
                "signals": ["plugin", "extension", "hook", "module", "addon", "middleware"],
                "indicators": ["plugins/", "extensions/", "hooks/", "modules/"],
                "failure_tendencies": ["Plugin conflicts", "Version incompatibility", "Security surface area"],
                "tradeoffs": {"extensibility": 0.9, "complexity": 0.4, "security": 0.5, "performance": 0.5},
            },
            ArchitecturePatternType.ORCHESTRATION: {
                "signals": ["orchestrator", "workflow", "pipeline", "step", "stage", "coordinator", "state_machine"],
                "indicators": ["workflows/", "orchestration/", "pipelines/", "steps/"],
                "failure_tendencies": ["Orchestrator bottleneck", "State explosion", "Error handling complexity"],
                "tradeoffs": {"control": 0.9, "visibility": 0.8, "flexibility": 0.4, "scalability": 0.5},
            },
            ArchitecturePatternType.HEXAGONAL: {
                "signals": ["port", "adapter", "driven", "driving", "inbound", "outbound", "core", "infrastructure"],
                "indicators": ["ports/", "adapters/", "core/", "domain/", "infrastructure/"],
                "failure_tendencies": ["Over-abstraction", "Port proliferation", "Testing overhead"],
                "tradeoffs": {"testability": 0.9, "maintainability": 0.8, "complexity": 0.4, "development_speed": 0.5},
            },
        }

    def discover_patterns(self, module_names: List[str], file_paths: List[str],
                          import_structure: Dict[str, List[str]]) -> ArchitectureFingerprint:
        patterns = []
        all_names_lower = [m.lower() for m in module_names]
        all_paths_lower = [p.lower() for p in file_paths]

        for pattern_type, spec in self._known_patterns.items():
            evidence = []
            matched_signals = []
            matched_indicators = []

            for signal in spec["signals"]:
                if any(signal in name for name in all_names_lower):
                    matched_signals.append(signal)

            for indicator in spec["indicators"]:
                if any(indicator in path for path in all_paths_lower):
                    matched_indicators.append(indicator)

            signal_score = len(matched_signals) / max(1, len(spec["signals"]))
            indicator_score = len(matched_indicators) / max(1, len(spec["indicators"]))
            confidence = (signal_score * 0.5 + indicator_score * 0.5)

            if confidence > 0.15:
                evidence.append(f"Matched {len(matched_signals)} signals: {', '.join(matched_signals[:5])}")
                evidence.append(f"Found {len(matched_indicators)} structural indicators")

                relationships = self._extract_relationships(import_structure, pattern_type)

                maturity = self._estimate_maturity(confidence, len(matched_indicators))

                arch_pattern = ArchitecturePattern(
                    pattern_type=pattern_type,
                    confidence=round(confidence, 3),
                    evidence=evidence,
                    components=matched_indicators,
                    relationships=relationships,
                    variants=[f"{pattern_type.value}_default"],
                    failure_tendencies=spec["failure_tendencies"],
                    tradeoffs=spec["tradeoffs"],
                    maturity=maturity,
                )
                patterns.append(arch_pattern)

        patterns.sort(key=lambda p: -p.confidence)
        primary = patterns[0].pattern_type if patterns else None
        secondary = [p.pattern_type for p in patterns[1:4]]

        return ArchitectureFingerprint(
            patterns=patterns,
            complexity_score=round(self._compute_complexity(patterns), 3),
            coupling_score=round(self._compute_coupling(patterns, import_structure), 3),
            cohesion_score=round(self._compute_cohesion(patterns, import_structure), 3),
            layer_count=self._count_layers(patterns),
            service_count=self._count_services(file_paths),
            primary_pattern=primary,
            secondary_patterns=secondary,
        )

    def _extract_relationships(self, import_structure: Dict[str, List[str]], 
                                pattern_type: ArchitecturePatternType) -> List[Dict]:
        relationships = []
        for source, targets in list(import_structure.items())[:20]:
            for target in targets[:10]:
                relationships.append({
                    "source": source,
                    "target": target,
                    "type": "depends_on",
                    "context": pattern_type.value,
                })
        return relationships

    def _estimate_maturity(self, confidence: float, indicator_count: int) -> PatternMaturity:
        if confidence > 0.7 and indicator_count > 3:
            return PatternMaturity.DOMINANT
        if confidence > 0.5:
            return PatternMaturity.ESTABLISHED
        if confidence > 0.3:
            return PatternMaturity.EMERGING
        return PatternMaturity.EMBRYONIC

    def _compute_complexity(self, patterns: List[ArchitecturePattern]) -> float:
        if not patterns:
            return 0
        return min(1.0, len(patterns) * 0.15 + sum(p.confidence for p in patterns) * 0.1)

    def _compute_coupling(self, patterns: List[ArchitecturePattern],
                          import_structure: Dict[str, List[str]]) -> float:
        if not import_structure:
            return 0.5
        total_imports = sum(len(targets) for targets in import_structure.values())
        total_modules = len(import_structure)
        return min(1.0, total_imports / max(1, total_modules * 3))

    def _compute_cohesion(self, patterns: List[ArchitecturePattern],
                          import_structure: Dict[str, List[str]]) -> float:
        if not patterns or not import_structure:
            return 0.5
        pattern_modules = set()
        for p in patterns:
            pattern_modules.update(p.components)
        internal_refs = sum(
            1 for targets in import_structure.values()
            for t in targets if t in pattern_modules
        )
        total_refs = sum(len(targets) for targets in import_structure.values())
        return internal_refs / max(1, total_refs)

    def _count_layers(self, patterns: List[ArchitecturePattern]) -> int:
        layered = [p for p in patterns if p.pattern_type == ArchitecturePatternType.LAYERED_MONOLITH]
        if layered:
            return len(layered[0].components)
        return 1

    def _count_services(self, file_paths: List[str]) -> int:
        service_count = sum(1 for p in file_paths if "service" in p.lower())
        return max(1, service_count)

    def compare_variants(self, fingerprint_a: ArchitectureFingerprint,
                         fingerprint_b: ArchitectureFingerprint) -> Dict:
        return {
            "complexity_delta": round(fingerprint_a.complexity_score - fingerprint_b.complexity_score, 3),
            "coupling_delta": round(fingerprint_a.coupling_score - fingerprint_b.coupling_score, 3),
            "cohesion_delta": round(fingerprint_a.cohesion_score - fingerprint_b.cohesion_score, 3),
            "pattern_overlap": list(set(p.pattern_type for p in fingerprint_a.patterns) &
                                     set(p.pattern_type for p in fingerprint_b.patterns)),
            "unique_to_a": [p.pattern_type.value for p in fingerprint_a.patterns
                           if p not in fingerprint_b.patterns],
            "unique_to_b": [p.pattern_type.value for p in fingerprint_b.patterns
                           if p not in fingerprint_a.patterns],
        }

    def estimate_failure_tendencies(self, fingerprint: ArchitectureFingerprint) -> List[Dict]:
        tendencies = []
        for pattern in fingerprint.patterns:
            for tendency in pattern.failure_tendencies:
                tendencies.append({
                    "pattern": pattern.pattern_type.value,
                    "tendency": tendency,
                    "risk_score": round(pattern.confidence * 0.7, 3),
                    "mitigation": self._get_mitigation(pattern.pattern_type, tendency),
                })
        return tendencies

    def _get_mitigation(self, pattern_type: ArchitecturePatternType, tendency: str) -> str:
        mitigations = {
            "Leaky abstraction": "Enforce strict layer boundaries with archunit-style tests",
            "Layer bypass": "Use architectural linting rules",
            "Big ball of mud": "Apply strangler fig pattern incrementally",
            "Event ordering": "Use event sourcing with idempotent handlers",
            "Network complexity": "Adopt service mesh with circuit breakers",
            "State duplication": "Normalize state shape, use selectors",
            "Orchestrator bottleneck": "Consider choreography or saga patterns",
        }
        return mitigations.get(tendency, "Monitor and address as part of technical debt management")

    def track_evolutionary_pressure(self, fingerprint: ArchitectureFingerprint) -> Dict:
        pressures = []
        for pattern in fingerprint.patterns:
            if maturity := pattern.maturity:
                if maturity in (PatternMaturity.DECLINING, PatternMaturity.EMBRYONIC):
                    pressures.append({
                        "pattern": pattern.pattern_type.value,
                        "pressure": "declining_adoption",
                        "recommendation": "Consider migrating to established alternatives",
                    })
        return {
            "evolutionary_pressures": pressures,
            "dominant_patterns": [p.pattern_type.value for p in fingerprint.patterns
                                  if p.maturity == PatternMaturity.DOMINANT],
            "emerging_patterns": [p.pattern_type.value for p in fingerprint.patterns
                                 if p.maturity == PatternMaturity.EMERGING],
        }
