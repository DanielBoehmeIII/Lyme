from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import time


class RiskScore(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class RiskCategory(str, Enum):
    ABANDONMENT = "abandonment"
    BREAKING_CHANGE = "breaking_change"
    VULNERABILITY = "vulnerability"
    DEPENDENCY_CHAIN = "dependency_chain"
    ECOSYSTEM_INSTABILITY = "ecosystem_instability"
    LOCK_IN = "lock_in"
    MIGRATION = "migration"
    LICENSE = "license"


@dataclass
class RiskSignal:
    category: RiskCategory
    signal_type: str
    description: str
    strength: float
    confidence: float
    source: str
    timestamp: float
    mitigation: str = ""

    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "signal_type": self.signal_type,
            "description": self.description,
            "strength": self.strength,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "mitigation": self.mitigation,
        }


@dataclass
class LibraryRiskProfile:
    library_name: str
    ecosystem: str
    current_version: str
    overall_risk: RiskScore
    risk_score: float
    confidence: float
    signals: List[RiskSignal]
    vulnerability_count: int
    abandonment_probability: float
    breaking_change_probability: float
    dependency_chain_risk: float
    recommended_action: str
    alternative_libraries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "library_name": self.library_name,
            "ecosystem": self.ecosystem,
            "current_version": self.current_version,
            "overall_risk": self.overall_risk.value,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "signals": [s.to_dict() for s in self.signals],
            "vulnerability_count": self.vulnerability_count,
            "abandonment_probability": self.abandonment_probability,
            "breaking_change_probability": self.breaking_change_probability,
            "dependency_chain_risk": self.dependency_chain_risk,
            "recommended_action": self.recommended_action,
            "alternative_libraries": self.alternative_libraries,
        }


@dataclass
class MigrationRiskAssessment:
    source_framework: str
    target_framework: str
    overall_risk: RiskScore
    risk_score: float
    breaking_change_count: int
    estimated_effort_person_weeks: int
    high_risk_components: List[str]
    recommended_approach: str
    signals: List[RiskSignal]

    def to_dict(self) -> Dict:
        return {
            "source_framework": self.source_framework,
            "target_framework": self.target_framework,
            "overall_risk": self.overall_risk.value,
            "risk_score": self.risk_score,
            "breaking_change_count": self.breaking_change_count,
            "estimated_effort_person_weeks": self.estimated_effort_person_weeks,
            "high_risk_components": self.high_risk_components,
            "recommended_approach": self.recommended_approach,
        }


@dataclass
class EcosystemRiskReport:
    generated_at: float
    total_libraries_assessed: int
    high_risk_libraries: List[LibraryRiskProfile]
    medium_risk_libraries: List[LibraryRiskProfile]
    critical_migration_risks: List[MigrationRiskAssessment]
    ecosystem_health_score: float
    top_recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "generated_at": self.generated_at,
            "total_libraries_assessed": self.total_libraries_assessed,
            "high_risk_libraries": [l.to_dict() for l in self.high_risk_libraries],
            "medium_risk_libraries": [l.to_dict() for l in self.medium_risk_libraries],
            "critical_migration_risks": [m.to_dict() for m in self.critical_migration_risks],
            "ecosystem_health_score": self.ecosystem_health_score,
            "top_recommendations": self.top_recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Ecosystem Risk Report",
            f"",
            f"- **Generated:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.generated_at))}",
            f"- **Libraries assessed:** {self.total_libraries_assessed}",
            f"- **Ecosystem health:** {self.ecosystem_health_score:.0%}",
            f"",
            f"## High Risk Libraries ({len(self.high_risk_libraries)})",
        ]
        for lr in self.high_risk_libraries:
            lines.append(f"- **{lr.library_name}** (risk: {lr.risk_score:.2f}): {lr.recommended_action}")
        lines.extend([
            f"",
            f"## Medium Risk Libraries ({len(self.medium_risk_libraries)})",
        ])
        for lr in self.medium_risk_libraries[:10]:
            lines.append(f"- {lr.library_name} (risk: {lr.risk_score:.2f})")
        lines.extend([
            f"",
            f"## Critical Migration Risks ({len(self.critical_migration_risks)})",
        ])
        for mr in self.critical_migration_risks:
            lines.append(f"- {mr.source_framework} → {mr.target_framework}: {mr.estimated_effort_person_weeks} weeks")
        lines.extend([
            f"",
            f"## Top Recommendations",
        ])
        for r in self.top_recommendations:
            lines.append(f"- {r}")
        return "\n".join(lines)


class EcosystemRiskForecaster:
    def __init__(self, dependency_graph=None):
        self._graph = dependency_graph
        self._risk_history: Dict[str, List[LibraryRiskProfile]] = defaultdict(list)

    def assess_library_risk(self, library_name: str, ecosystem: str = "python",
                            signals: Optional[List[RiskSignal]] = None) -> LibraryRiskProfile:
        signals = signals or []
        lib = None
        if self._graph and hasattr(self._graph, 'libraries'):
            for l in self._graph.libraries:
                if l.name == library_name:
                    lib = l
                    break

        abandonment_prob = self._estimate_abandonment(lib, signals)
        breaking_prob = self._estimate_breaking_changes(lib, signals)
        chain_risk = self._estimate_dependency_chain_risk(lib)
        vuln_count = sum(1 for s in signals if s.category == RiskCategory.VULNERABILITY)

        composite = (abandonment_prob * 0.3 + breaking_prob * 0.25 +
                     chain_risk * 0.25 + min(1.0, vuln_count * 0.1) * 0.2)

        risk_score_val = RiskScore.CRITICAL if composite >= 0.75 else RiskScore.HIGH if composite >= 0.55 else RiskScore.MEDIUM if composite >= 0.35 else RiskScore.LOW if composite >= 0.15 else RiskScore.NEGLIGIBLE

        alternatives = self._find_alternatives(library_name, ecosystem)
        action = self._generate_action(composite, risk_score_val, alternatives)

        profile = LibraryRiskProfile(
            library_name=library_name, ecosystem=ecosystem,
            current_version=lib.version if lib else "unknown",
            overall_risk=risk_score_val, risk_score=round(composite, 3),
            confidence=0.7, signals=signals,
            vulnerability_count=vuln_count,
            abandonment_probability=round(abandonment_prob, 3),
            breaking_change_probability=round(breaking_prob, 3),
            dependency_chain_risk=round(chain_risk, 3),
            recommended_action=action, alternative_libraries=alternatives,
        )

        self._risk_history[library_name].append(profile)
        return profile

    def _estimate_abandonment(self, lib, signals: List[RiskSignal]) -> float:
        if not lib:
            base = 0.3
        else:
            base = getattr(lib, 'abandonment_risk', 0.3)
        for s in signals:
            if s.category == RiskCategory.ABANDONMENT:
                base = max(base, s.strength)
        return min(1.0, base * 1.2)

    def _estimate_breaking_changes(self, lib, signals: List[RiskSignal]) -> float:
        base = 0.2
        if lib:
            freq = getattr(lib, 'release_frequency', 0.5)
            base = min(1.0, (1.0 - freq) * 0.5)
        for s in signals:
            if s.category == RiskCategory.BREAKING_CHANGE:
                base = max(base, s.strength)
        return min(1.0, base)

    def _estimate_dependency_chain_risk(self, lib) -> float:
        if not self._graph or not lib:
            return 0.3
        lib_id = lib.id
        chains = getattr(self._graph, 'compute_transitive_dependencies', lambda x: [])(lib_id)
        if not chains:
            return 0.1
        return min(1.0, sum(c.risk_score for c in chains) / (len(chains) * 2))

    def _find_alternatives(self, library_name: str, ecosystem: str) -> List[str]:
        known = {
            "Flask": ["FastAPI", "Starlette"],
            "gunicorn": ["uvicorn", "hypercorn"],
            "celery": ["dramatiq", "arq", "huey"],
            "python-jose": ["PyJWT", "authlib"],
            "passlib": ["bcrypt", "argon2-cffi"],
            "redux": ["zustand", "jotai", "valtio"],
            "webpack": ["vite", "esbuild", "turbopack"],
            "jest": ["vitest", "playwright"],
            "async-std": ["tokio"],
            "rocket": ["axum", "actix-web"],
            "diesel": ["sqlx"],
        }
        return known.get(library_name, [])

    def _generate_action(self, score: float, risk: RiskScore, alternatives: List[str]) -> str:
        if risk == RiskScore.CRITICAL:
            return f"Immediate action required. {'Migrate to: ' + ', '.join(alternatives[:2]) if alternatives else 'Audit and replace.'}"
        if risk == RiskScore.HIGH:
            return f"Plan migration within next quarter. {'Consider: ' + ', '.join(alternatives[:2]) if alternatives else 'Monitor closely.'}"
        if risk == RiskScore.MEDIUM:
            return "Monitor regularly. Prepare contingency plan."
        return "No immediate action required. Continue monitoring."

    def assess_migration_risk(self, source: str, target: str) -> MigrationRiskAssessment:
        common_migrations = {
            ("Flask", "FastAPI"): (0.5, 15, ["Route decorators", "Dependency injection", "Async conversion"]),
            ("Django REST", "FastAPI"): (0.7, 25, ["ORM replacement", "Admin panel", "Auth system"]),
            ("redux", "zustand"): (0.3, 4, ["Store conversion", "Middleware migration"]),
            ("webpack", "vite"): (0.4, 8, ["Plugin migration", "Configuration rewrite"]),
            ("jest", "vitest"): (0.2, 3, ["Test file updates", "Configuration migration"]),
            ("Pages Router", "App Router"): (0.6, 12, ["Routing restructure", "Data fetching patterns"]),
            ("Pydantic v1", "Pydantic v2"): (0.4, 3, ["Validator updates", "Config changes"]),
        }

        key = (source, target)
        if key in common_migrations:
            risk_score_val, weeks, components = common_migrations[key]
            risk = RiskScore.HIGH if risk_score_val >= 0.6 else RiskScore.MEDIUM if risk_score_val >= 0.35 else RiskScore.LOW
            approach = "Phased migration with parallel run" if risk_score_val >= 0.5 else "Direct migration with thorough testing"
        else:
            risk_score_val = 0.5
            weeks = 8
            components = ["Unknown"]
            risk = RiskScore.MEDIUM
            approach = "Research migration path first"

        signals = [
            RiskSignal(RiskCategory.MIGRATION, f"{source} to {target}",
                       f"Migration from {source} to {target}", risk_score_val, 0.6, "risk_forecaster", time.time()),
        ]

        return MigrationRiskAssessment(
            source_framework=source, target_framework=target,
            overall_risk=risk, risk_score=risk_score_val,
            breaking_change_count=len(components),
            estimated_effort_person_weeks=weeks,
            high_risk_components=components,
            recommended_approach=approach, signals=signals,
        )

    def generate_ecosystem_report(self) -> EcosystemRiskReport:
        high_risk = []
        medium_risk = []
        all_signals: List[RiskSignal] = []

        if self._graph and hasattr(self._graph, 'libraries'):
            libs = self._graph.libraries
            for lib in libs:
                signals = self._detect_signals(lib)
                all_signals.extend(signals)
                profile = self.assess_library_risk(lib.name, lib.ecosystem, signals)
                if profile.overall_risk in (RiskScore.CRITICAL, RiskScore.HIGH):
                    high_risk.append(profile)
                elif profile.overall_risk == RiskScore.MEDIUM:
                    medium_risk.append(profile)

        migrations = self._detect_risky_migrations()

        health = 1.0 - (len(high_risk) * 0.1 + len(medium_risk) * 0.03) / max(1, len(self._graph.libraries)) if self._graph else 0.5

        recs = self._generate_report_recommendations(high_risk, migrations)

        return EcosystemRiskReport(
            generated_at=time.time(),
            total_libraries_assessed=len(self._graph.libraries) if self._graph else 0,
            high_risk_libraries=high_risk,
            medium_risk_libraries=medium_risk,
            critical_migration_risks=migrations,
            ecosystem_health_score=round(max(0, health), 3),
            top_recommendations=recs,
        )

    def _detect_signals(self, lib) -> List[RiskSignal]:
        signals = []
        now = time.time()

        if getattr(lib, 'phase', None) and lib.phase.value == "declining":
            signals.append(RiskSignal(
                RiskCategory.ABANDONMENT, "phase_decline",
                f"{lib.name} is in declining phase",
                getattr(lib, 'abandonment_risk', 0.5), 0.7, "ecosystem_phase", now,
                f"Consider migrating to alternatives",
            ))

        if getattr(lib, 'release_frequency', 1) < 0.1:
            signals.append(RiskSignal(
                RiskCategory.ABANDONMENT, "low_release_frequency",
                f"{lib.name} has very low release frequency",
                0.6, 0.6, "release_tracking", now,
                "Evaluate if library is still maintained",
            ))

        if getattr(lib, 'abandonment_risk', 0) > 0.5:
            signals.append(RiskSignal(
                RiskCategory.ABANDONMENT, "high_abandonment_risk",
                f"{lib.name} has high abandonment risk",
                lib.abandonment_risk, 0.65, "risk_model", now,
                "Identify replacement with active maintenance",
            ))

        return signals

    def _detect_risky_migrations(self) -> List[MigrationRiskAssessment]:
        migrations = [
            ("Flask", "FastAPI"),
            ("Django REST", "FastAPI"),
            ("Pydantic v1", "Pydantic v2"),
            ("webpack", "vite"),
            ("Pages Router", "App Router"),
        ]
        return [self.assess_migration_risk(s, t) for s, t in migrations]

    def _generate_report_recommendations(self, high_risk: List, migrations: List) -> List[str]:
        recs = []
        if high_risk:
            recs.append(f"Address {len(high_risk)} high-risk libraries immediately")
        for m in migrations[:3]:
            if m.overall_risk in (RiskScore.CRITICAL, RiskScore.HIGH):
                recs.append(f"Plan {m.source_framework} → {m.target_framework} migration ({m.estimated_effort_person_weeks} weeks)")
        if not recs:
            recs.append("Ecosystem is healthy. Continue monitoring.")
        return recs

    def risk_trend(self, library_name: str) -> List[Dict]:
        history = self._risk_history.get(library_name, [])
        return [
            {"timestamp": p.to_dict().get("signals", [{}])[0].get("timestamp", 0) if p.signals else 0,
             "risk_score": p.risk_score, "level": p.overall_risk.value}
            for p in history
        ]

    def save(self, path: str):
        report = self.generate_ecosystem_report()
        with open(path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

    @classmethod
    def load_report(cls, path: str) -> EcosystemRiskReport:
        with open(path) as f:
            data = json.load(f)
        return EcosystemRiskReport(
            generated_at=data["generated_at"],
            total_libraries_assessed=data["total_libraries_assessed"],
            high_risk_libraries=[LibraryRiskProfile(**lr) for lr in data["high_risk_libraries"]],
            medium_risk_libraries=[LibraryRiskProfile(**lr) for lr in data["medium_risk_libraries"]],
            critical_migration_risks=[MigrationRiskAssessment(**mr) for mr in data["critical_migration_risks"]],
            ecosystem_health_score=data["ecosystem_health_score"],
            top_recommendations=data["top_recommendations"],
        )
