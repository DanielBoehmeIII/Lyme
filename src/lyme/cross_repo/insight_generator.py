from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import uuid


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class InsightApplicability:
    repo_types: List[str]
    conditions: List[str]
    limitations: List[str]
    adaptation_steps: List[str] = field(default_factory=list)
    failure_risk: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class TransferableInsight:
    id: str
    title: str
    summary: str
    pattern_refs: List[str]
    evidence_count: int
    confidence: ConfidenceLevel
    applicability: InsightApplicability
    cross_ecosystem: bool = False
    prerequisites: List[str] = field(default_factory=list)
    expected_impact: str = ""
    verified_examples: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "pattern_refs": self.pattern_refs,
            "evidence_count": self.evidence_count,
            "confidence": self.confidence.value,
            "applicability": {
                "repo_types": self.applicability.repo_types,
                "conditions": self.applicability.conditions,
                "limitations": self.applicability.limitations,
                "adaptation_steps": self.applicability.adaptation_steps,
                "failure_risk": self.applicability.failure_risk.value,
            },
            "cross_ecosystem": self.cross_ecosystem,
            "prerequisites": self.prerequisites,
            "expected_impact": self.expected_impact,
            "verified_examples": self.verified_examples,
        }


class InsightGenerator:
    def __init__(self):
        self._insights: List[TransferableInsight] = []

    def generate(self, patterns: List, clusters: List) -> List[TransferableInsight]:
        insights = []
        insights.extend(self._architectural_insights(patterns))
        insights.extend(self._failure_mode_insights(patterns))
        insights.extend(self._testing_insights(patterns))
        insights.extend(self._dependency_insights(patterns))
        insights.extend(self._convention_insights(patterns))
        insights.extend(self._cross_cluster_insights(clusters))
        self._insights = insights
        return insights

    def _architectural_insights(self, patterns: List) -> List[TransferableInsight]:
        from lyme.cross_repo.pattern_extractor import PatternCategory
        arch_patterns = [p for p in patterns if p.category == PatternCategory.ARCHITECTURE and p.occurrences >= 3]

        insights = []
        for ap in arch_patterns:
            insight = TransferableInsight(
                id=f"arch_insight_{uuid.uuid4().hex[:12]}",
                title=f"Architecture Pattern: {ap.name}",
                summary=f"Repositories using {ap.name} show consistent structural patterns. "
                        f"This architecture is prevalent across {ap.occurrences} repositories.",
                pattern_refs=[ap.id],
                evidence_count=ap.occurrences,
                confidence=self._confidence_from_occurrences(ap.occurrences),
                applicability=InsightApplicability(
                    repo_types=[ap.tags[-1]] if ap.tags else ["general"],
                    conditions=[f"Project size > {10 * ap.occurrences} files"],
                    limitations=["May not suit microservice architectures"],
                    adaptation_steps=[
                        f"Map existing structure to {ap.name} conventions",
                        "Identify core domain boundaries",
                        "Align naming with pattern conventions",
                    ],
                    failure_risk=self._risk_from_occurrences(ap.occurrences),
                ),
                cross_ecosystem=ap.occurrences >= 5,
                prerequisites=["Understanding of current architecture"],
                expected_impact=f"Improved maintainability through {ap.name} conventions",
                verified_examples=min(ap.occurrences, 10),
            )
            insights.append(insight)
        return insights

    def _failure_mode_insights(self, patterns: List) -> List[TransferableInsight]:
        from lyme.cross_repo.pattern_extractor import PatternCategory
        fail_patterns = [p for p in patterns if p.category == PatternCategory.FAILURE_MODE and p.occurrences >= 2]

        insights = []
        risk_map = {
            "panic": "High risk: panic-based error handling causes crashes across 50%+ repos",
            "unwrap": "Medium risk: unwrap failures indicate insufficient error propagation",
            "try_except": "Low risk: broad try/except may mask specific errors",
        }

        for fp in fail_patterns:
            summary = risk_map.get(
                fp.signature.get("strategy", ""),
                f"Error handling pattern {fp.name} observed across {fp.occurrences} repos"
            )
            insight = TransferableInsight(
                id=f"fail_insight_{uuid.uuid4().hex[:12]}",
                title=f"Failure Mode: {fp.name}",
                summary=summary,
                pattern_refs=[fp.id],
                evidence_count=fp.occurrences,
                confidence=self._confidence_from_occurrences(fp.occurrences),
                applicability=InsightApplicability(
                    repo_types=["general"],
                    conditions=["Error handling patterns match"],
                    limitations=["Specific to language ecosystem"],
                    adaptation_steps=[
                        "Audit error handling against pattern",
                        "Identify high-risk unwrap/panic sites",
                        "Replace with structured error types",
                    ],
                    failure_risk=ConfidenceLevel.HIGH,
                ),
                cross_ecosystem=False,
                prerequisites=["Error handling audit tooling"],
                expected_impact="Reduced crash rate from unhandled errors",
                verified_examples=min(fp.occurrences, 8),
            )
            insights.append(insight)
        return insights

    def _testing_insights(self, patterns: List) -> List[TransferableInsight]:
        from lyme.cross_repo.pattern_extractor import PatternCategory
        test_patterns = [p for p in patterns if p.category == PatternCategory.TESTING_STRATEGY and p.occurrences >= 2]

        insights = []
        for tp in test_patterns:
            insight = TransferableInsight(
                id=f"test_insight_{uuid.uuid4().hex[:12]}",
                title=f"Testing Strategy: {tp.name}",
                summary=f"Testing pattern {tp.name} appears across {tp.occurrences} repositories. "
                        "Consider adoption for improved test coverage.",
                pattern_refs=[tp.id],
                evidence_count=tp.occurrences,
                confidence=self._confidence_from_occurrences(tp.occurrences),
                applicability=InsightApplicability(
                    repo_types=["python", "javascript", "rust"],
                    conditions=["Existing test framework compatible"],
                    limitations=["Requires test culture adoption"],
                    adaptation_steps=[
                        "Align test structure with pattern",
                        "Adopt parametrization if applicable",
                        "Implement fixture patterns",
                    ],
                    failure_risk=ConfidenceLevel.LOW,
                ),
                cross_ecosystem=True,
                prerequisites=["Test framework installed"],
                expected_impact="More consistent and maintainable test suite",
                verified_examples=min(tp.occurrences, 10),
            )
            insights.append(insight)
        return insights

    def _dependency_insights(self, patterns: List) -> List[TransferableInsight]:
        from lyme.cross_repo.pattern_extractor import PatternCategory
        dep_patterns = [p for p in patterns if p.category == PatternCategory.DEPENDENCY_MIGRATION and p.occurrences >= 3]

        migration_advice = {
            "web_framework": "Common dependency category. Consider evaluating alternatives.",
            "database": "Database dependency cluster. Migration path exists between ORMs.",
            "authentication": "Auth libraries change frequently. Consider abstraction layer.",
            "testing": "Testing utilities are ecosystem-dependent but patterns transfer.",
        }

        insights = []
        for dp in dep_patterns:
            category = dp.signature.get("category", "")
            summary = migration_advice.get(category, f"Dependency pattern {dp.name} in {dp.occurrences} repos")
            insight = TransferableInsight(
                id=f"dep_insight_{uuid.uuid4().hex[:12]}",
                title=f"Dependency Insight: {dp.name}",
                summary=summary,
                pattern_refs=[dp.id],
                evidence_count=dp.occurrences,
                confidence=self._confidence_from_occurrences(dp.occurrences),
                applicability=InsightApplicability(
                    repo_types=["general"],
                    conditions=["Dependency is present"],
                    limitations=["Ecosystem-specific versions"],
                    adaptation_steps=[
                        "Evaluate current dependency version",
                        "Check migration guides",
                        "Run compatibility tests",
                    ],
                    failure_risk=ConfidenceLevel.MEDIUM,
                ),
                cross_ecosystem=category in ("testing", "web_framework"),
                prerequisites=["Dependency audit"],
                expected_impact="Reduced dependency risk through informed migration",
                verified_examples=min(dp.occurrences, 8),
            )
            insights.append(insight)
        return insights

    def _convention_insights(self, patterns: List) -> List[TransferableInsight]:
        from lyme.cross_repo.pattern_extractor import PatternCategory
        conv_patterns = [p for p in patterns if p.category == PatternCategory.ECOSYSTEM_CONVENTION and p.occurrences >= 3]

        insights = []
        for cp in conv_patterns:
            insight = TransferableInsight(
                id=f"conv_insight_{uuid.uuid4().hex[:12]}",
                title=f"Convention: {cp.name}",
                summary=f"Naming convention {cp.name} dominates across {cp.occurrences} repos. "
                        "Adopting this convention improves cross-project readability.",
                pattern_refs=[cp.id],
                evidence_count=cp.occurrences,
                confidence=self._confidence_from_occurrences(cp.occurrences),
                applicability=InsightApplicability(
                    repo_types=["python", "javascript", "rust", "go"],
                    conditions=["Team consistency"],
                    limitations=["May conflict with existing style guide"],
                    adaptation_steps=[
                        "Update linter configuration",
                        "Run automated renaming",
                        "Update documentation",
                    ],
                    failure_risk=ConfidenceLevel.LOW,
                ),
                cross_ecosystem=True,
                prerequisites=["Linter/formatter installed"],
                expected_impact="Improved code consistency across repos",
                verified_examples=min(cp.occurrences, 10),
            )
            insights.append(insight)
        return insights

    def _cross_cluster_insights(self, clusters: List) -> List[TransferableInsight]:
        insights = []
        for cluster in clusters:
            if cluster.size < 3:
                continue
            insight = TransferableInsight(
                id=f"cluster_insight_{uuid.uuid4().hex[:12]}",
                title=f"Cluster Analysis: {cluster.label}",
                summary=f"Found cluster of {cluster.size} repos with {cluster.intra_cluster_similarity:.0%} internal similarity. "
                        "Patterns within this cluster are likely transferable with minimal adaptation.",
                pattern_refs=[],
                evidence_count=cluster.size,
                confidence=self._confidence_from_occurrences(cluster.size),
                applicability=InsightApplicability(
                    repo_types=[cluster.label],
                    conditions=[f"repo belongs to {cluster.label} cluster"],
                    limitations=["Cluster patterns may not generalize outside cluster"],
                    adaptation_steps=[
                        "Verify repo cluster membership",
                        "Apply top patterns from cluster",
                        "Validate transfer outcomes",
                    ],
                    failure_risk=ConfidenceLevel.LOW if cluster.intra_cluster_similarity > 0.7 else ConfidenceLevel.MEDIUM,
                ),
                cross_ecosystem=cluster.label == "unknown",
                prerequisites=["Repo fingerprinted"],
                expected_impact=f"Patterns transfer with ~{cluster.intra_cluster_similarity:.0%} expected similarity",
                verified_examples=cluster.size,
            )
            insights.append(insight)
        return insights

    def _confidence_from_occurrences(self, count: int) -> ConfidenceLevel:
        if count >= 20:
            return ConfidenceLevel.VERY_HIGH
        if count >= 10:
            return ConfidenceLevel.HIGH
        if count >= 5:
            return ConfidenceLevel.MEDIUM
        if count >= 3:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _risk_from_occurrences(self, count: int) -> ConfidenceLevel:
        if count >= 10:
            return ConfidenceLevel.LOW
        if count >= 5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH

    @property
    def insights(self) -> List[TransferableInsight]:
        return self._insights

    def save(self, path: Path):
        data = [i.to_dict() for i in self._insights]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> List[TransferableInsight]:
        data = json.loads(path.read_text())
        self._insights = []
        for d in data:
            app = InsightApplicability(
                repo_types=d["applicability"]["repo_types"],
                conditions=d["applicability"]["conditions"],
                limitations=d["applicability"]["limitations"],
                adaptation_steps=d["applicability"].get("adaptation_steps", []),
                failure_risk=ConfidenceLevel(d["applicability"]["failure_risk"]),
            )
            self._insights.append(TransferableInsight(
                id=d["id"],
                title=d["title"],
                summary=d["summary"],
                pattern_refs=d["pattern_refs"],
                evidence_count=d["evidence_count"],
                confidence=ConfidenceLevel(d["confidence"]),
                applicability=app,
                cross_ecosystem=d.get("cross_ecosystem", False),
                prerequisites=d.get("prerequisites", []),
                expected_impact=d.get("expected_impact", ""),
                verified_examples=d.get("verified_examples", 0),
            ))
        return self._insights
