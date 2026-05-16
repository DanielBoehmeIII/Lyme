import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class ImpactLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    INTERFACE_BREAK = "interface_break"
    INVARIANT_VIOLATION = "invariant_violation"
    DEPENDENCY_CYCLE = "dependency_cycle"
    LAYERING_VIOLATION = "layering_violation"
    SECURITY_REGRESSION = "security_regression"
    PERFORMANCE_REGRESSION = "performance_regression"
    API_COMPATIBILITY = "api_compatibility"
    TYPE_SAFETY = "type_safety"


@dataclass
class SemanticImpact:
    scope: str = ""
    impact_level: str = ImpactLevel.LOW
    affected_files: List[str] = field(default_factory=list)
    affected_interfaces: List[str] = field(default_factory=list)
    behavioral_change: str = ""
    reasoning: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvariantViolation:
    invariant_type: str = ""
    description: str = ""
    location: str = ""
    severity: str = ImpactLevel.MEDIUM
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    suggested_fix: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArchitecturalDrift:
    description: str = ""
    original_intent: str = ""
    current_pattern: str = ""
    severity: str = ImpactLevel.LOW
    affected_subsystems: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskZone:
    file_path: str = ""
    risk_type: str = ""
    risk_level: str = ImpactLevel.LOW
    description: str = ""
    lines: str = ""
    mitigation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestGap:
    area: str = ""
    gap_type: str = ""  # missing, insufficient, flaky, no_coverage
    severity: str = ImpactLevel.MEDIUM
    description: str = ""
    suggested_tests: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MissingEvidence:
    claim: str = ""
    evidence_needed: str = ""
    evidence_type: str = ""  # test, static_analysis, review, benchmark
    severity: str = ImpactLevel.MEDIUM

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RollbackDifficulty:
    level: str = ImpactLevel.LOW
    estimated_time_minutes: int = 0
    strategy: str = ""
    risks: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskScore:
    overall: str = ImpactLevel.LOW
    score: float = 0.0
    regression_risk: str = ImpactLevel.LOW
    security_risk: str = ImpactLevel.NONE
    deploy_risk: str = ImpactLevel.LOW
    factors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewSummary:
    verdict: str = ""  # approve, needs_work, block
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationChecklist:
    items: List[Dict[str, str]] = field(default_factory=list)

    def add_item(self, check: str, status: str = "pending", details: str = ""):
        self.items.append({"check": check, "status": status, "details": details})

    def to_dict(self) -> dict:
        return {"items": self.items}


@dataclass
class SuggestedReviewerFocus:
    primary_focus: str = ""
    files_to_review: List[str] = field(default_factory=list)
    expertise_needed: List[str] = field(default_factory=list)
    risk_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PRIntelligenceReport:
    pr_number: int = 0
    pr_title: str = ""
    pr_url: str = ""
    repository: str = ""
    branch: str = ""
    author: str = ""
    semantic_impact: List[dict] = field(default_factory=list)
    invariant_violations: List[dict] = field(default_factory=list)
    architectural_drifts: List[dict] = field(default_factory=list)
    risk_zones: List[dict] = field(default_factory=list)
    test_gaps: List[dict] = field(default_factory=list)
    missing_evidence: List[dict] = field(default_factory=list)
    rollback_difficulty: Optional[dict] = None
    risk_score: Optional[dict] = None
    review_summary: Optional[dict] = None
    verification_checklist: Optional[dict] = None
    suggested_focus: Optional[dict] = None
    trace_export: Optional[dict] = None
    generated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "pr_title": self.pr_title,
            "pr_url": self.pr_url,
            "repository": self.repository,
            "branch": self.branch,
            "author": self.author,
            "semantic_impact": self.semantic_impact,
            "invariant_violations": self.invariant_violations,
            "architectural_drifts": self.architectural_drifts,
            "risk_zones": self.risk_zones,
            "test_gaps": self.test_gaps,
            "missing_evidence": self.missing_evidence,
            "rollback_difficulty": self.rollback_difficulty,
            "risk_score": self.risk_score,
            "review_summary": self.review_summary,
            "verification_checklist": self.verification_checklist,
            "suggested_focus": self.suggested_focus,
            "trace_export": self.trace_export,
            "generated_at": self.generated_at,
        }


class PRAnalyzer:
    def __init__(self):
        self._analyses = 0

    def analyze(self, pr_data: dict) -> PRIntelligenceReport:
        self._analyses += 1
        report = PRIntelligenceReport(
            pr_number=pr_data.get("number", 0),
            pr_title=pr_data.get("title", ""),
            pr_url=pr_data.get("url", ""),
            repository=pr_data.get("repository", ""),
            branch=pr_data.get("branch", ""),
            author=pr_data.get("author", ""),
        )

        files = pr_data.get("files", [])
        diff_data = pr_data.get("diff", "")
        changed_files = [f.get("filename", f.get("path", "")) for f in files]

        report.semantic_impact = self._analyze_semantic_impact(files, diff_data)
        report.invariant_violations = self._detect_invariant_violations(files, diff_data)
        report.architectural_drifts = self._detect_architectural_drift(files)
        report.risk_zones = self._identify_risk_zones(files, diff_data)
        report.test_gaps = self._find_test_gaps(changed_files)
        report.missing_evidence = self._find_missing_evidence(files)
        report.rollback_difficulty = self._assess_rollback(files)
        report.risk_score = self._calculate_risk(report)
        report.review_summary = self._generate_summary(report)
        report.verification_checklist = self._build_checklist(report)
        report.suggested_focus = self._suggest_focus(report)

        import time
        report.generated_at = time.time()
        return report

    def _analyze_semantic_impact(self, files: List[dict], diff_data: str) -> List[dict]:
        impacts = []
        for f in files:
            filename = f.get("filename", f.get("path", ""))
            additions = f.get("additions", f.get("lines_added", 0))
            deletions = f.get("deletions", f.get("lines_removed", 0))
            status = f.get("status", "modified")

            impact_level = ImpactLevel.LOW
            if additions > 100 or deletions > 50:
                impact_level = ImpactLevel.HIGH
            elif additions > 50 or deletions > 20:
                impact_level = ImpactLevel.MEDIUM

            impacts.append(SemanticImpact(
                scope=filename,
                impact_level=impact_level,
                affected_files=[filename],
                behavioral_change=f"{status}: +{additions}/-{deletions} lines",
                reasoning=f"{additions} additions, {deletions} deletions, status: {status}",
            ).to_dict())
        return impacts

    def _detect_invariant_violations(self, files: List[dict], diff_data: str) -> List[dict]:
        violations = []
        for f in files:
            filename = f.get("filename", f.get("path", ""))
            patch = f.get("patch", "")
            if not patch:
                continue

            if "None" in patch and "-> None" not in patch and "Optional" in patch:
                violations.append(InvariantViolation(
                    invariant_type="type_safety",
                    description=f"Possible None-unsafe change in {filename}",
                    location=filename,
                    severity=ImpactLevel.MEDIUM,
                    confidence=0.5,
                    evidence=[f"patch contains 'None' in {filename}"],
                ).to_dict())

            if "import" in patch and "removed" in patch.lower():
                violations.append(InvariantViolation(
                    invariant_type="dependency_rule",
                    description=f"Remove imports in {filename} may break downstream",
                    location=filename,
                    severity=ImpactLevel.LOW,
                    confidence=0.3,
                ).to_dict())

        return violations

    def _detect_architectural_drift(self, files: List[dict]) -> List[dict]:
        drifts = []
        for f in files:
            fn = f.get("filename", f.get("path", ""))
            if "controller" in fn and "service" in fn.replace("controller", ""):
                continue
            if "services/" in fn or "service/" in fn:
                if any(kw in fn for kw in ["controller", "view", "template"]):
                    drifts.append(ArchitecturalDrift(
                        description=f"Service layer file in unexpected location: {fn}",
                        original_intent="Service layer contains business logic only",
                        current_pattern=f"File {fn} may mix concerns",
                        severity=ImpactLevel.LOW,
                        affected_subsystems=["service_layer"],
                        recommendation="Verify this file follows layering conventions",
                    ).to_dict())
        return drifts

    def _identify_risk_zones(self, files: List[dict], diff_data: str) -> List[dict]:
        zones = []
        for f in files:
            fn = f.get("filename", f.get("path", ""))
            status = f.get("status", "modified")
            patch = f.get("patch", "")
            additions = f.get("additions", 0)
            deletions = f.get("deletions", 0)

            if status == "deleted" and additions == 0:
                zones.append(RiskZone(
                    file_path=fn, risk_type="file_deletion",
                    risk_level=ImpactLevel.HIGH,
                    description=f"File {fn} deleted - verify no consumers depend on it",
                    lines="entire file",
                    mitigation="Check for import references and callers",
                ).to_dict())

            if additions > 200:
                zones.append(RiskZone(
                    file_path=fn, risk_type="large_change",
                    risk_level=ImpactLevel.MEDIUM,
                    description=f"Very large change (+{additions} lines) in {fn}",
                    lines=f"+{additions}/-{deletions}",
                    mitigation="Consider splitting into smaller PRs",
                ).to_dict())

        return zones

    def _find_test_gaps(self, changed_files: List[str]) -> List[dict]:
        gaps = []
        has_test_changes = any("test" in f.lower() for f in changed_files)
        source_files = [f for f in changed_files if "test" not in f.lower()
                        and f.endswith((".py", ".js", ".ts", ".rs", ".go", ".java"))]

        for sf in source_files:
            gap = TestGap(
                area=sf,
                gap_type="missing" if not has_test_changes else "insufficient",
                severity=ImpactLevel.MEDIUM if not has_test_changes else ImpactLevel.LOW,
                description=f"Source change in {sf} without corresponding test changes" if not has_test_changes
                else f"Test coverage may be insufficient for {sf}",
                suggested_tests=[f"test_{sf.split('/')[-1]}"] if "/" in sf else [],
            ).to_dict()
            gaps.append(gap)

        return gaps

    def _find_missing_evidence(self, files: List[dict]) -> List[dict]:
        missing = []
        large_changes = [f for f in files if f.get("additions", 0) > 100]

        if large_changes:
            for f in large_changes:
                missing.append(MissingEvidence(
                    claim=f"Large change in {f.get('filename')} is safe",
                    evidence_needed="Benchmark results or performance impact analysis",
                    evidence_type="benchmark",
                    severity=ImpactLevel.MEDIUM,
                ).to_dict())

        return missing

    def _assess_rollback(self, files: List[dict]) -> dict:
        has_deletions = any(f.get("status") == "deleted" for f in files)
        has_schema = any("schema" in f.get("filename", "").lower() for f in files)
        has_migrations = any("migration" in f.get("filename", "").lower() for f in files)

        if has_migrations or (has_schema and has_deletions):
            return RollbackDifficulty(
                level=ImpactLevel.HIGH,
                estimated_time_minutes=30,
                strategy="schema_rollback + data_migration",
                risks=["Data loss possible", "Migration may not be reversible"],
                steps=[
                    "Revert schema migration",
                    "Restore deleted files",
                    "Run data backfill if needed",
                    "Verify with integration tests",
                ],
            ).to_dict()
        elif has_deletions:
            return RollbackDifficulty(
                level=ImpactLevel.MEDIUM,
                estimated_time_minutes=10,
                strategy="git_revert",
                risks=["Deleted files may have external consumers"],
                steps=["git revert HEAD", "Verify no broken imports"],
            ).to_dict()
        else:
            return RollbackDifficulty(
                level=ImpactLevel.LOW,
                estimated_time_minutes=2,
                strategy="git_revert",
                steps=["git revert <commit>", "Run tests"],
            ).to_dict()

    def _calculate_risk(self, report: PRIntelligenceReport) -> dict:
        factors = []
        score = 0.0

        for v in report.invariant_violations:
            score += {"low": 0.1, "medium": 0.2, "high": 0.4}.get(v.get("severity", "low"), 0.2)
            factors.append(f"Invariant violation: {v.get('description', '')}")

        for z in report.risk_zones:
            score += {"low": 0.05, "medium": 0.15, "high": 0.3}.get(z.get("risk_level", "low"), 0.15)
            factors.append(f"Risk zone: {z.get('description', '')}")

        for g in report.test_gaps:
            score += {"low": 0.05, "medium": 0.1, "high": 0.2}.get(g.get("severity", "low"), 0.1)

        for m in report.missing_evidence:
            score += 0.1

        if report.rollback_difficulty:
            rd = report.rollback_difficulty
            score += {"low": 0.0, "medium": 0.1, "high": 0.2}.get(rd.get("level", "low"), 0.1)

        score = min(score, 1.0)
        overall = ImpactLevel.LOW
        if score >= 0.7:
            overall = ImpactLevel.CRITICAL
        elif score >= 0.5:
            overall = ImpactLevel.HIGH
        elif score >= 0.3:
            overall = ImpactLevel.MEDIUM

        return RiskScore(
            overall=overall,
            score=round(score, 2),
            regression_risk=ImpactLevel.HIGH if score >= 0.4 else ImpactLevel.LOW,
            security_risk=ImpactLevel.HIGH if any("security" in f.lower() for f in factors) else ImpactLevel.NONE,
            deploy_risk=overall,
            factors=factors,
        ).to_dict()

    def _generate_summary(self, report: PRIntelligenceReport) -> dict:
        n_violations = len(report.invariant_violations)
        n_zones = len(report.risk_zones)
        n_gaps = len(report.test_gaps)
        total_issues = n_violations + n_zones + n_gaps

        risk = report.risk_score or {"overall": "unknown", "score": 0}
        concerns = [f"Invariant violations: {n_violations}"] if n_violations else []
        if n_zones:
            concerns.append(f"Risk zones: {n_zones}")
        if n_gaps:
            concerns.append(f"Test gaps: {n_gaps}")

        if risk.get("score", 0) >= 0.5:
            verdict = "block"
        elif risk.get("score", 0) >= 0.3:
            verdict = "needs_work"
        else:
            verdict = "approve"

        return ReviewSummary(
            verdict=verdict,
            summary=f"PR #{report.pr_number}: {total_issues} issues found. "
                    f"Risk score: {risk.get('score', 0):.2f} ({risk.get('overall', 'unknown')}). "
                    f"Verdict: {verdict}.",
            concerns=concerns,
            blocking_issues=[v.get("description", "") for v in report.invariant_violations
                            if v.get("severity") in ("high", "critical")],
        ).to_dict()

    def _build_checklist(self, report: PRIntelligenceReport) -> dict:
        checklist = VerificationChecklist()
        checklist.add_item("Semantic impact assessed", "done" if report.semantic_impact else "pending")
        checklist.add_item("Invariant violations checked", "fail" if report.invariant_violations else "pass")
        checklist.add_item("Architectural drift analyzed", "warn" if report.architectural_drifts else "pass")
        checklist.add_item("Risk zones identified", "warn" if report.risk_zones else "pass")
        checklist.add_item("Test gaps detected", "fail" if report.test_gaps else "pass")
        checklist.add_item("Missing evidence flagged", "warn" if report.missing_evidence else "pass")
        checklist.add_item("Rollback strategy defined", "done")
        checklist.add_item("Reviewer focus areas suggested", "done")
        return checklist.to_dict()

    def _suggest_focus(self, report: PRIntelligenceReport) -> dict:
        risk_files = [z.get("file_path", "") for z in report.risk_zones]
        violation_files = [v.get("location", "") for v in report.invariant_violations]
        all_risk = list(set(risk_files + violation_files))

        return SuggestedReviewerFocus(
            primary_focus=f"Review {len(all_risk)} high-attention files first" if all_risk else "Standard review",
            files_to_review=all_risk if all_risk else ["All changed files"],
            expertise_needed=list(set(
                [v.get("invariant_type", "general") for v in report.invariant_violations]
            )) or ["general"],
            risk_areas=[f"{z.get('file_path', '')} ({z.get('risk_type', '')})" for z in report.risk_zones],
        ).to_dict()
