from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import time
import uuid
from pathlib import Path


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GapLabel(str, Enum):
    UNTESTED_CODE = "untested_code"
    MISSING_ASSERTION = "missing_assertion"
    WEAK_COVERAGE = "weak_coverage"
    UNAVAILABLE_BUILD = "unavailable_build"
    UNVERIFIABLE_CLAIM = "unverifiable_claim"
    RISKY_ASSUMPTION = "risky_assumption"
    FALSE_CONFIDENCE = "false_confidence"
    NO_TYPE_CHECK = "no_type_check"
    NO_STATIC_ANALYSIS = "no_static_analysis"
    NO_RUNTIME_VERIFICATION = "no_runtime_verification"
    MISSING_ROLLBACK_PATH = "missing_rollback_path"
    INSUFFICIENT_APPROVAL = "insufficient_approval"
    NO_BENCHMARK_BASELINE = "no_benchmark_baseline"
    UNREVIEWED_CHANGE = "unreviewed_change"
    SECURITY_SENSITIVE_UNSCANNED = "security_sensitive_unscanned"


@dataclass
class VerificationGap:
    label: GapLabel
    description: str
    severity: GapSeverity
    location: str = ""
    recommendation: str = ""
    score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "label": self.label.value,
            "description": self.description,
            "severity": self.severity.value,
            "location": self.location,
            "recommendation": self.recommendation,
            "score": self.score,
        }

    def to_markdown(self) -> str:
        icons = {
            GapSeverity.CRITICAL: "🔴", GapSeverity.HIGH: "🟠",
            GapSeverity.MEDIUM: "🟡", GapSeverity.LOW: "🟢", GapSeverity.INFO: "ℹ️",
        }
        return f"{icons.get(self.severity, '•')} **[{self.severity.value.upper()}]** {self.description}  \n   Location: {self.location}  \n   → {self.recommendation}"


@dataclass
class GapDetectionResult:
    gaps: List[VerificationGap]
    total_gaps: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    overall_severity: str = "low"
    top_recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "gaps": [g.to_dict() for g in self.gaps],
            "total_gaps": self.total_gaps,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "overall_severity": self.overall_severity,
            "top_recommendations": self.top_recommendations,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Verification Gap Detection Report")
        lines.append(f"")
        lines.append(f"**Total Gaps**: {self.total_gaps}")
        lines.append(f"**Overall Severity**: {self.overall_severity.upper()}")
        lines.append(f"")
        counts = []
        if self.critical_count:
            counts.append(f"🔴 Critical: {self.critical_count}")
        if self.high_count:
            counts.append(f"🟠 High: {self.high_count}")
        if self.medium_count:
            counts.append(f"🟡 Medium: {self.medium_count}")
        if self.low_count:
            lines.append(f" | ".join(counts))
        lines.append(f"")
        for gap in sorted(self.gaps, key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(g.severity.value, 5)):
            lines.append(gap.to_markdown())
            lines.append("")
        lines.append(f"## Top Recommendations")
        for i, rec in enumerate(self.top_recommendations, 1):
            lines.append(f"{i}. {rec}")
        return "\n".join(lines)

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  VERIFICATION GAP DETECTOR")
        lines.append("=" * 70)
        lines.append(f"  Total gaps: {self.total_gaps} | Severity: {self.overall_severity.upper()}")
        lines.append(f"  Critical: {self.critical_count} | High: {self.high_count} | Medium: {self.medium_count} | Low: {self.low_count}")
        lines.append("-" * 70)

        severity_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}
        for gap in sorted(self.gaps, key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(g.severity.value, 5)):
            icon = severity_icons.get(gap.severity.value, "•")
            lines.append(f"  {icon} [{gap.severity.value.upper()}] {gap.label.value}")
            lines.append(f"     {gap.description}")
            if gap.location:
                lines.append(f"     Location: {gap.location}")
            lines.append(f"     → {gap.recommendation}")
            lines.append("")

        lines.append("  Recommendations:")
        for rec in self.top_recommendations:
            lines.append(f"    • {rec}")
        lines.append("=" * 70)
        return "\n".join(lines)


class VerificationGapDetector:
    def __init__(self):
        self._severity_weights = {
            GapSeverity.CRITICAL: 4, GapSeverity.HIGH: 3,
            GapSeverity.MEDIUM: 2, GapSeverity.LOW: 1, GapSeverity.INFO: 0,
        }

    def detect(self, context: Dict) -> GapDetectionResult:
        gaps: List[VerificationGap] = []

        source_files = context.get("source_files", [])
        test_files = context.get("test_files", [])
        changed_files = context.get("changed_files", [])
        has_type_check = context.get("has_type_check", False)
        has_static_analysis = context.get("has_static_analysis", False)
        has_runtime_verification = context.get("has_runtime_verification", False)
        has_rollback = context.get("has_rollback_path", False)
        has_benchmark_baseline = context.get("has_benchmark_baseline", False)
        has_approval = context.get("has_approval", True)
        test_coverage_pct = context.get("test_coverage_pct", 0.0)
        claims = context.get("claims", [])
        assumptions = context.get("assumptions", [])
        build_available = context.get("build_available", True)
        is_sensitive = context.get("is_sensitive", False)
        has_security_scan = context.get("has_security_scan", False)
        reviewed = context.get("reviewed", False)
        confidence = context.get("confidence", 1.0)

        if changed_files and not test_files:
            for f in changed_files:
                if not any(t in f.lower() for t in [".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml"]):
                    if not any("test" in f.lower() or "spec" in f.lower() for f in changed_files):
                        gaps.append(VerificationGap(
                            label=GapLabel.UNTESTED_CODE,
                            description=f"Changed files have no corresponding test files",
                            severity=GapSeverity.HIGH,
                            location=", ".join(changed_files[:5]),
                            recommendation="Add unit tests covering the changed functionality",
                            score=0.8,
                        ))
                        break

        if source_files and test_files:
            uncovered = []
            for sf in source_files:
                has_test = False
                for tf in test_files:
                    sf_stem = Path(sf).stem
                    if sf_stem in tf or sf_stem.replace("_", "") in tf:
                        has_test = True
                        break
                if not has_test:
                    uncovered.append(sf)
            if uncovered:
                gaps.append(VerificationGap(
                    label=GapLabel.WEAK_COVERAGE,
                    description=f"{len(uncovered)} source files missing test coverage",
                    severity=GapSeverity.MEDIUM,
                    location=", ".join(uncovered[:5]),
                    recommendation=f"Add tests for: {', '.join(uncovered[:3])}",
                    score=0.6,
                ))

        if test_coverage_pct < 80.0 and source_files:
            gaps.append(VerificationGap(
                label=GapLabel.WEAK_COVERAGE,
                description=f"Test coverage is {test_coverage_pct:.0f}% (target: 80%+)",
                severity=GapSeverity.HIGH if test_coverage_pct < 50 else GapSeverity.MEDIUM,
                recommendation="Increase test coverage with additional unit and integration tests",
                score=1.0 - (test_coverage_pct / 100.0),
            ))

        if not has_type_check:
            gaps.append(VerificationGap(
                label=GapLabel.NO_TYPE_CHECK,
                description="No type checking configured for the project",
                severity=GapSeverity.MEDIUM,
                recommendation="Add type checking (e.g., mypy for Python, TypeScript for JS)",
                score=0.5,
            ))

        if not has_static_analysis:
            gaps.append(VerificationGap(
                label=GapLabel.NO_STATIC_ANALYSIS,
                description="No static analysis configured for the project",
                severity=GapSeverity.MEDIUM,
                recommendation="Add static analysis (e.g., ruff, pylint, bandit)",
                score=0.4,
            ))

        if not has_runtime_verification and source_files:
            gaps.append(VerificationGap(
                label=GapLabel.NO_RUNTIME_VERIFICATION,
                description="No runtime verification or smoke testing in place",
                severity=GapSeverity.HIGH,
                recommendation="Add runtime smoke tests to verify application behavior post-change",
                score=0.7,
            ))

        if not has_rollback:
            gaps.append(VerificationGap(
                label=GapLabel.MISSING_ROLLBACK_PATH,
                description="No rollback path verified for changes",
                severity=GapSeverity.HIGH,
                recommendation="Verify git-based rollback path and test recovery procedure",
                score=0.7,
            ))

        if not has_benchmark_baseline:
            gaps.append(VerificationGap(
                label=GapLabel.NO_BENCHMARK_BASELINE,
                description="No benchmark baseline for performance comparison",
                severity=GapSeverity.LOW,
                recommendation="Establish benchmark baselines to detect regressions",
                score=0.3,
            ))

        for claim in claims:
            if not claim.get("verified", False):
                gaps.append(VerificationGap(
                    label=GapLabel.UNVERIFIABLE_CLAIM,
                    description=f"Claim cannot be verified: {claim.get('statement', 'unknown')[:60]}",
                    severity=GapSeverity.HIGH,
                    location=claim.get("source", ""),
                    recommendation="Restate claim in testable/falsifiable terms or remove it",
                    score=0.8,
                ))

        for assumption in assumptions:
            gaps.append(VerificationGap(
                label=GapLabel.RISKY_ASSUMPTION,
                description=f"Risky assumption without verification: {assumption.get('statement', 'unknown')[:60]}",
                severity=GapSeverity.MEDIUM,
                recommendation=f"Add verification for: {assumption.get('statement', 'unknown')[:40]}",
                score=0.5,
            ))

        if not build_available:
            gaps.append(VerificationGap(
                label=GapLabel.UNAVAILABLE_BUILD,
                description="Build step not available or configured",
                severity=GapSeverity.CRITICAL,
                recommendation="Configure build system and verify build succeeds before change",
                score=0.9,
            ))

        if is_sensitive and not has_security_scan:
            gaps.append(VerificationGap(
                label=GapLabel.SECURITY_SENSITIVE_UNSCANNED,
                description="Sensitive code without security scanning",
                severity=GapSeverity.CRITICAL,
                recommendation="Run security scanner on all sensitive code paths",
                score=0.95,
            ))

        if not reviewed and not source_files:
            gaps.append(VerificationGap(
                label=GapLabel.UNREVIEWED_CHANGE,
                description="Change has not been reviewed",
                severity=GapSeverity.LOW,
                recommendation="Consider peer review for non-trivial changes",
                score=0.3,
            ))

        if confidence > 0.9 and (not has_type_check or not has_static_analysis):
            gaps.append(VerificationGap(
                label=GapLabel.FALSE_CONFIDENCE,
                description=f"Confidence ({confidence:.0%}) is high but key verification steps are missing",
                severity=GapSeverity.HIGH,
                recommendation="Calibrate confidence against actual verification coverage",
                score=0.75,
            ))

        critical = len([g for g in gaps if g.severity == GapSeverity.CRITICAL])
        high = len([g for g in gaps if g.severity == GapSeverity.HIGH])
        medium = len([g for g in gaps if g.severity == GapSeverity.MEDIUM])
        low = len([g for g in gaps if g.severity == GapSeverity.LOW])

        if critical > 0:
            overall = "critical"
        elif high > 2:
            overall = "high"
        elif high > 0 or medium > 3:
            overall = "medium"
        elif medium > 0:
            overall = "low"
        else:
            overall = "info"

        top_recs = []
        seen_recs: Set[str] = set()
        for gap in sorted(gaps, key=lambda g: g.score, reverse=True):
            if gap.recommendation not in seen_recs:
                top_recs.append(gap.recommendation)
                seen_recs.add(gap.recommendation)
                if len(top_recs) >= 5:
                    break

        return GapDetectionResult(
            gaps=gaps,
            total_gaps=len(gaps),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            overall_severity=overall,
            top_recommendations=top_recs,
        )
