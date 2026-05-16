from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import time


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class VulnerabilityScore:
    library: str
    version: str
    cvss_score: float
    affected_versions: str
    description: str
    fix_version: str
    propagation_depth: int
    downstream_affected: int

    def to_dict(self) -> Dict:
        return {
            "library": self.library,
            "version": self.version,
            "cvss_score": self.cvss_score,
            "affected_versions": self.affected_versions,
            "description": self.description,
            "fix_version": self.fix_version,
            "propagation_depth": self.propagation_depth,
            "downstream_affected": self.downstream_affected,
        }


class RiskScoringEngine:
    def __init__(self, dependency_graph=None):
        self._graph = dependency_graph
        self._known_vulnerabilities: List[VulnerabilityScore] = self._build_known_vulnerabilities()

    def _build_known_vulnerabilities(self) -> List[VulnerabilityScore]:
        return [
            VulnerabilityScore("python-jose", "3.3", 7.5, "<3.3.2",
                               "Algorithm confusion vulnerability in JWT verification",
                               "3.3.2", 3, 15000),
            VulnerabilityScore("gunicorn", "22.0", 5.0, "<22.0.0",
                               "HTTP request smuggling vulnerability",
                               "22.0.0", 2, 50000),
            VulnerabilityScore("passlib", "1.7", 4.5, "<1.7.5",
                               "Weak bcrypt rounds default configuration",
                               "1.7.5", 1, 30000),
            VulnerabilityScore("pydantic", "1.10", 8.0, "<1.10.13",
                               "Denial of service via regex injection",
                               "1.10.13", 4, 80000),
            VulnerabilityScore("django", "5.0", 7.0, "<5.0.6",
                               "SQL injection in database router",
                               "5.0.6", 3, 100000),
            VulnerabilityScore("flask", "3.0", 4.0, "<3.0.3",
                               "Information disclosure via debug mode",
                               "3.0.3", 2, 60000),
        ]

    def score_library_vulnerability(self, library_name: str, version: str) -> Dict:
        matched = [v for v in self._known_vulnerabilities if v.library.lower() == library_name.lower()]
        if not matched:
            return {"library": library_name, "vulnerabilities": [], "score": 0, "risk": "low"}

        max_cvss = max(v.cvss_score for v in matched)
        risk = "critical" if max_cvss >= 9 else "high" if max_cvss >= 7 else "medium" if max_cvss >= 4 else "low"

        return {
            "library": library_name,
            "version": version,
            "vulnerabilities": [v.to_dict() for v in matched],
            "score": max_cvss,
            "risk": risk,
            "max_downstream_impact": max(v.downstream_affected for v in matched),
        }

    def compute_combined_risk(self, libraries: Dict[str, str]) -> Dict:
        scores = []
        for lib_name, version in libraries.items():
            score = self.score_library_vulnerability(lib_name, version)
            scores.append(score)

        total_risk = sum(s["score"] for s in scores) / max(1, len(scores))
        critical = sum(1 for s in scores if s["risk"] == "critical")
        high = sum(1 for s in scores if s["risk"] == "high")
        medium = sum(1 for s in scores if s["risk"] == "medium")

        return {
            "libraries_scanned": len(scores),
            "average_risk_score": round(total_risk, 2),
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "overall_risk": "critical" if critical > 0 else "high" if high > 2 else "medium" if high > 0 else "low",
            "vulnerability_details": scores,
        }


class VulnerabilityPropagationScorer:
    def __init__(self, dependency_graph):
        self._graph = dependency_graph

    def compute_propagation_score(self, source_id: str, cvss: float = 7.5) -> Dict:
        if not self._graph or not hasattr(self._graph, 'get_dependents'):
            return {"source": source_id, "propagation_score": 0, "total_affected": 0}

        visited = set()
        queue = [(source_id, 0)]
        affected_by_depth = defaultdict(int)
        total_affected = 0

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if depth > 0:
                affected_by_depth[depth] += 1
                total_affected += 1
            dependents = self._graph.get_dependents(current)
            for dep in dependents:
                dep_id = dep.id if hasattr(dep, 'id') else dep
                queue.append((dep_id, depth + 1))

        depth_weight = sum(affected_by_depth[d] / max(1, d) for d in affected_by_depth)
        max_possible = len(self._graph.libraries) if hasattr(self._graph, 'libraries') else 1
        propagation_score = min(1.0, (total_affected / max_possible) * 0.5 + (cvss / 10) * 0.3 + depth_weight * 0.2)

        return {
            "source_id": source_id,
            "cvss_score": cvss,
            "propagation_score": round(propagation_score, 3),
            "total_affected": total_affected,
            "affected_by_depth": dict(affected_by_depth),
            "max_depth": max(affected_by_depth.keys()) if affected_by_depth else 0,
            "risk_level": "critical" if propagation_score >= 0.7 else "high" if propagation_score >= 0.5 else "medium",
        }


class AbandonmentDetector:
    def __init__(self, dependency_graph=None):
        self._graph = dependency_graph

    def detect_abandonment_signals(self, library_name: str) -> List[Dict]:
        signals = []

        stale_thresholds = {
            "release_stale": (0.1, "Release frequency below threshold"),
            "community_decline": (0.3, "Community activity declining"),
            "ecosystem_shift": (0.5, "Ecosystem shifting to alternatives"),
            "maintainer_burnout": (0.4, "Signs of maintainer burnout"),
        }

        for signal_type, (base_strength, description) in stale_thresholds.items():
            signals.append({
                "type": signal_type,
                "library": library_name,
                "strength": base_strength + (0.1 if signal_type == "ecosystem_shift" else 0),
                "description": description,
                "detectable": True,
                "confidence": 0.6,
            })

        return signals

    def compute_abandonment_risk(self, library_name: str) -> Dict:
        signals = self.detect_abandonment_signals(library_name)
        avg_strength = sum(s["strength"] for s in signals) / len(signals) if signals else 0

        risk = "high" if avg_strength >= 0.5 else "medium" if avg_strength >= 0.3 else "low"

        return {
            "library": library_name,
            "abandonment_risk_score": round(avg_strength, 3),
            "risk_level": risk,
            "signals": signals,
            "recommendation": "Begin migration planning" if risk == "high" else "Monitor",
            "estimated_timeframe": "3-6 months" if risk == "high" else "6-12 months" if risk == "medium" else ">12 months",
        }


class BreakingChangePredictor:
    def __init__(self):
        self._patterns: Dict[str, List[Dict]] = self._build_patterns()

    def _build_patterns(self) -> Dict[str, List[Dict]]:
        return {
            "python": [
                {"pattern": "major_version_bump", "probability": 0.7, "description": "Major version bump likely contains breaking changes"},
                {"pattern": "deprecated_api", "probability": 0.6, "description": "Deprecated API calls will be removed"},
                {"pattern": "python_version_drop", "probability": 0.4, "description": "Dropping Python 3.x support"},
            ],
            "javascript": [
                {"pattern": "major_version_bump", "probability": 0.6, "description": "Major semver bump often breaking"},
                {"pattern": "api_consolidation", "probability": 0.5, "description": "API consolidation/renaming"},
                {"pattern": "bundler_change", "probability": 0.4, "description": "Build tool migration"},
            ],
            "rust": [
                {"pattern": "edition_change", "probability": 0.5, "description": "Rust edition migration"},
                {"pattern": "async_runtime_shift", "probability": 0.4, "description": "Async runtime changes"},
                {"pattern": "trait_restructuring", "probability": 0.5, "description": "Trait organization changes"},
            ],
        }

    def predict_breaking_changes(self, library_name: str, current_version: str,
                                  target_version: str, ecosystem: str = "python") -> Dict:
        patterns = self._patterns.get(ecosystem, self._patterns["python"])

        cv = [int(x) for x in current_version.split(".")[:2] if x.isdigit()]
        tv = [int(x) for x in target_version.split(".")[:2] if x.isdigit()]

        is_major = len(cv) >= 1 and len(tv) >= 1 and tv[0] > cv[0]

        predictions = []
        for p in patterns:
            prob = p["probability"]
            if is_major and p["pattern"] == "major_version_bump":
                prob = min(1.0, prob * 1.3)
            if is_major:
                prob = min(1.0, prob * 1.1)

            predictions.append({
                "pattern": p["pattern"],
                "probability": round(prob, 3),
                "description": p["description"],
            })

        overall = sum(p["probability"] for p in predictions) / len(predictions) if predictions else 0
        risk = "high" if overall >= 0.5 else "medium" if overall >= 0.3 else "low"

        return {
            "library": library_name,
            "from_version": current_version,
            "to_version": target_version,
            "breaking_change_probability": round(overall, 3),
            "risk_level": risk,
            "major_upgrade": is_major,
            "predicted_patterns": predictions,
        }
