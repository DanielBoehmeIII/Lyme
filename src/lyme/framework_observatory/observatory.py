from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import uuid


class ChangeSeverity(str, Enum):
    BREAKING = "breaking"
    DEPRECATION = "deprecation"
    ADDITION = "addition"
    CHANGE = "change"
    FIX = "fix"


class ConventionCategory(str, Enum):
    ARCHITECTURE = "architecture"
    API_DESIGN = "api_design"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    STATE_MANAGEMENT = "state_management"
    STYLING = "styling"
    DATA_FETCHING = "data_fetching"
    ERROR_HANDLING = "error_handling"


@dataclass
class APISnapshot:
    framework: str
    version: str
    timestamp: float
    public_api_count: int
    exported_symbols: List[str]
    method_signatures: Dict[str, str]
    decorator_patterns: List[str]
    configuration_keys: List[str]

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework,
            "version": self.version,
            "timestamp": self.timestamp,
            "public_api_count": self.public_api_count,
            "exported_symbols": self.exported_symbols[:50],
            "method_signatures": dict(list(self.method_signatures.items())[:50]),
            "decorator_patterns": self.decorator_patterns,
            "configuration_keys": self.configuration_keys,
        }


@dataclass
class BreakingChange:
    framework: str
    from_version: str
    to_version: str
    api_element: str
    change_type: str
    description: str
    migration_steps: List[str]
    impact_score: float
    affected_users_estimate: float
    codemod_available: bool = False

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "api_element": self.api_element,
            "change_type": self.change_type,
            "description": self.description,
            "migration_steps": self.migration_steps,
            "impact_score": self.impact_score,
            "affected_users_estimate": self.affected_users_estimate,
            "codemod_available": self.codemod_available,
        }


@dataclass
class MigrationTrend:
    from_framework: str
    to_framework: str
    peak_period: str
    estimated_migrations: int
    driving_factors: List[str]
    blocking_factors: List[str]
    acceleration_rate: float
    completed_share: float

    def to_dict(self) -> Dict:
        return {
            "from_framework": self.from_framework,
            "to_framework": self.to_framework,
            "peak_period": self.peak_period,
            "estimated_migrations": self.estimated_migrations,
            "driving_factors": self.driving_factors,
            "blocking_factors": self.blocking_factors,
            "acceleration_rate": self.acceleration_rate,
            "completed_share": self.completed_share,
        }


@dataclass
class ConventionEvolution:
    category: ConventionCategory
    convention: str
    emerged_version: str
    peak_adoption_version: str
    decline_version: Optional[str] = None
    replacement: Optional[str] = None
    adoption_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "convention": self.convention,
            "emerged_version": self.emerged_version,
            "peak_adoption_version": self.peak_adoption_version,
            "decline_version": self.decline_version,
            "replacement": self.replacement,
            "adoption_curve": self.adoption_curve,
        }


@dataclass
class FrameworkSnapshot:
    framework: str
    version: str
    timestamp: float
    api: APISnapshot
    common_bug_patterns: List[Dict]
    convention_shifts: List[ConventionEvolution]
    ecosystem_migrations: List[MigrationTrend]
    architectural_trends: List[str]
    community_health: Dict

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework,
            "version": self.version,
            "timestamp": self.timestamp,
            "api": self.api.to_dict(),
            "common_bug_patterns": self.common_bug_patterns,
            "convention_shifts": [c.to_dict() for c in self.convention_shifts],
            "ecosystem_migrations": [m.to_dict() for m in self.ecosystem_migrations],
            "architectural_trends": self.architectural_trends,
            "community_health": self.community_health,
        }


@dataclass
class FrameworkEvolutionReport:
    framework: str
    first_version: str
    current_version: str
    total_versions_analyzed: int
    breaking_changes: List[BreakingChange]
    migration_trends: List[MigrationTrend]
    convention_evolutions: List[ConventionEvolution]
    ecosystem_health_score: float
    stability_trend: str
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework,
            "first_version": self.first_version,
            "current_version": self.current_version,
            "total_versions_analyzed": self.total_versions_analyzed,
            "breaking_changes": [b.to_dict() for b in self.breaking_changes],
            "migration_trends": [m.to_dict() for m in self.migration_trends],
            "convention_evolutions": [c.to_dict() for c in self.convention_evolutions],
            "ecosystem_health_score": self.ecosystem_health_score,
            "stability_trend": self.stability_trend,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Framework Evolution Report: {self.framework}",
            f"",
            f"- **First version analyzed:** {self.first_version}",
            f"- **Current version:** {self.current_version}",
            f"- **Versions analyzed:** {self.total_versions_analyzed}",
            f"- **Ecosystem health:** {self.ecosystem_health_score:.0%}",
            f"- **Stability trend:** {self.stability_trend}",
            f"",
            f"## Breaking Changes ({len(self.breaking_changes)})",
        ]
        for bc in self.breaking_changes[:10]:
            lines.append(f"- **{bc.api_element}** ({bc.from_version} → {bc.to_version}): {bc.description}")
        lines.extend([
            f"",
            f"## Migration Trends ({len(self.migration_trends)})",
        ])
        for mt in self.migration_trends[:5]:
            lines.append(f"- {mt.from_framework} → {mt.to_framework}: {mt.estimated_migrations} migrations (peak: {mt.peak_period})")
        lines.extend([
            f"",
            f"## Convention Evolution ({len(self.convention_evolutions)})",
        ])
        for ce in self.convention_evolutions[:8]:
            decline = f" → declined in {ce.decline_version}" if ce.decline_version else ""
            lines.append(f"- **{ce.convention}** (emerged: {ce.emerged_version}, peak: {ce.peak_adoption_version}{decline})")
        lines.extend([
            f"",
            f"## Recommendations",
        ])
        for r in self.recommendations:
            lines.append(f"- {r}")
        return "\n".join(lines)


class FrameworkObservatory:
    def __init__(self):
        self._snapshots: Dict[str, List[FrameworkSnapshot]] = defaultdict(list)
        self._breaking_changes: Dict[str, List[BreakingChange]] = defaultdict(list)

    def record_snapshot(self, snapshot: FrameworkSnapshot):
        self._snapshots[snapshot.framework].append(snapshot)

    def record_breaking_change(self, change: BreakingChange):
        self._breaking_changes[change.framework].append(change)

    def get_framework_history(self, framework: str) -> List[FrameworkSnapshot]:
        return sorted(self._snapshots.get(framework, []), key=lambda s: s.timestamp)

    def compute_evolution_report(self, framework: str) -> Optional[FrameworkEvolutionReport]:
        history = self.get_framework_history(framework)
        if not history:
            return None

        changes = self._breaking_changes.get(framework, [])

        versions = sorted(set(s.version for s in history))
        conventions = []
        for s in history:
            conventions.extend(s.convention_shifts)

        migrations = []
        for s in history:
            migrations.extend(s.ecosystem_migrations)

        health_scores = []
        for s in history:
            health_scores.append(s.community_health.get("overall_score", 0.5))
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0.5

        recent = history[-1] if len(history) >= 3 else None
        older = history[0] if history else None
        if recent and older:
            recent_bugs = len(recent.common_bug_patterns)
            older_bugs = len(older.common_bug_patterns)
            trend = "improving" if recent_bugs < older_bugs else "declining" if recent_bugs > older_bugs else "stable"
        else:
            trend = "insufficient_data"

        breaking_count = len(changes)
        recommendations = self._generate_recommendations(framework, changes, trend, avg_health)

        return FrameworkEvolutionReport(
            framework=framework,
            first_version=versions[0] if versions else "",
            current_version=versions[-1] if versions else "",
            total_versions_analyzed=len(versions),
            breaking_changes=changes,
            migration_trends=migrations,
            convention_evolutions=conventions,
            ecosystem_health_score=round(avg_health, 3),
            stability_trend=trend,
            recommendations=recommendations,
        )

    def _generate_recommendations(self, framework: str, changes: List[BreakingChange],
                                  trend: str, health: float) -> List[str]:
        recs = []
        if trend == "declining":
            recs.append(f"Monitor {framework} stability — increasing bug pattern density detected.")
        if health < 0.4:
            recs.append(f"Community health below threshold. Evaluate long-term dependency on {framework}.")
        breaking_count = len([c for c in changes if c.impact_score > 0.7])
        if breaking_count > 3:
            recs.append(f"High-impact breaking changes accumulating. Budget migration effort proactively.")
        recent = [c for c in changes if c.impact_score > 0.5][:3]
        for c in recent:
            recs.append(f"Plan migration for {c.api_element}: {c.description[:80]}")
        if not recs:
            recs.append(f"{framework} ecosystem appears stable. Continue monitoring.")
        return recs

    def compare_frameworks(self, framework_a: str, framework_b: str) -> Dict:
        report_a = self.compute_evolution_report(framework_a)
        report_b = self.compute_evolution_report(framework_b)

        if not report_a or not report_b:
            return {"error": "One or both frameworks not found"}

        return {
            "comparison": f"{framework_a} vs {framework_b}",
            "health_delta": round(report_a.ecosystem_health_score - report_b.ecosystem_health_score, 3),
            "breaking_change_delta": len(report_a.breaking_changes) - len(report_b.breaking_changes),
            "migration_activity_ratio": round(
                len(report_a.migration_trends) / max(1, len(report_b.migration_trends)), 2
            ),
            "convention_evolution_rate": round(
                len(report_a.convention_evolutions) / max(1, len(report_b.convention_evolutions)), 2
            ),
            "a_healthier": report_a.ecosystem_health_score > report_b.ecosystem_health_score,
            "a_stabler": report_a.stability_trend == "stable" and report_b.stability_trend != "stable",
        }

    def detect_convention_drift(self, framework: str) -> List[Dict]:
        history = self.get_framework_history(framework)
        if len(history) < 2:
            return []

        drifts = []
        earlier = history[0].convention_shifts
        later = history[-1].convention_shifts

        earlier_names = {c.convention for c in earlier}
        later_names = {c.convention for c in later}

        emerged = later_names - earlier_names
        declined = earlier_names - later_names

        for c in later:
            if c.convention in emerged:
                drifts.append({"type": "emerged", "convention": c.convention, "version": c.emerged_version})
        for c in earlier:
            if c.convention in declined:
                drifts.append({"type": "declined", "convention": c.convention, "version": c.decline_version or "unknown"})

        return drifts

    def get_common_bug_trends(self, framework: str) -> List[Dict]:
        history = self.get_framework_history(framework)
        bug_counts = defaultdict(int)
        for s in history:
            for bug in s.common_bug_patterns:
                bug_counts[bug.get("pattern", "unknown")] += 1

        return [
            {"pattern": pattern, "occurrences": count, "framework": framework}
            for pattern, count in sorted(bug_counts.items(), key=lambda x: -x[1])[:15]
        ]

    def save(self, path: str):
        data = {
            "snapshots": {
                fw: [s.to_dict() for s in snaps]
                for fw, snaps in self._snapshots.items()
            },
            "breaking_changes": {
                fw: [c.to_dict() for c in changes]
                for fw, changes in self._breaking_changes.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> FrameworkObservatory:
        with open(path) as f:
            data = json.load(f)
        obs = cls()
        for fw, snaps in data.get("snapshots", {}).items():
            for sd in snaps:
                api_data = sd.get("api", {})
                api = APISnapshot(**api_data)
                snapshot = FrameworkSnapshot(
                    framework=sd["framework"], version=sd["version"],
                    timestamp=sd["timestamp"], api=api,
                    common_bug_patterns=sd.get("common_bug_patterns", []),
                    convention_shifts=[ConventionEvolution(**c) for c in sd.get("convention_shifts", [])],
                    ecosystem_migrations=[MigrationTrend(**m) for m in sd.get("ecosystem_migrations", [])],
                    architectural_trends=sd.get("architectural_trends", []),
                    community_health=sd.get("community_health", {}),
                )
                obs.record_snapshot(snapshot)
        for fw, changes in data.get("breaking_changes", {}).items():
            for cd in changes:
                obs.record_breaking_change(BreakingChange(**cd))
        return obs
