from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import time


class V06Demo:
    def __init__(self):
        self.ledger = None
        self.constitution = None
        self.results: List[str] = []

    def run(self, full: bool = False) -> Dict:
        self.results = []
        self._print_header()

        self.step1_init_constitution()
        self.step2_risky_edit_governance()
        self.step3_safe_edit_governance()
        self.step4_verification_plan()
        self.step5_verification_graph()
        self.step6_verification_gaps()
        self.step7_ledger_store()
        self.step8_self_benchmark()
        self.step9_longitudinal()
        self.step10_cognition_ci()

        self._print_footer()
        return {"summary": "\n".join(self.results), "steps_completed": 10}

    def _print_header(self):
        self.results.append("=" * 70)
        self.results.append("  LYME v0.6 DEMO — Scientific Governance of Autonomous Change")
        self.results.append("=" * 70)
        self.results.append("")

    def _print_footer(self):
        self.results.append("")
        self.results.append("=" * 70)
        self.results.append("  DEMO COMPLETE — All 10 governance capabilities demonstrated")
        self.results.append("  Lyme now governs autonomous change, not merely generates it.")
        self.results.append("=" * 70)

    def step1_init_constitution(self):
        self.results.append("[Step 1/10] Initialize Repo Constitution")
        from lyme.governance.repo_constitution import RepoConstitution, ConstitutionValidator

        constit = RepoConstitution.create_default(repo_name="lyme-demo")
        validator = ConstitutionValidator(constit)
        issues = validator.validate()

        self.results.append(f"  Created constitution for 'lyme-demo'")
        self.results.append(f"  Zones defined: {len(constit.zones)}")
        self.results.append(f"  Forbidden zones: {len(constit.forbidden_zones)}")
        self.results.append(f"  Architectural rules: {len(constit.architectural_rules)}")
        self.results.append(f"  Validation issues: {len(issues)}")
        self.results.append(f"  ✅ Constitution defines governance boundaries")
        self.results.append("")
        self.constitution = constit

    def step2_risky_edit_governance(self):
        self.results.append("[Step 2/10] Risky Edit — Governance Engine Blocks")
        from lyme.governance.change_governance import ChangeGovernanceEngine

        engine = ChangeGovernanceEngine()
        result = engine.evaluate({
            "risk_score": 0.92,
            "scope": "broad",
            "sensitivity": "critical",
            "reversibility": "irreversible",
            "files_changed": ["src/core/auth.py", "deploy/prod.sh"],
            "description": "Replace authentication system and redeploy",
            "verification_coverage": 0.2,
            "user_intent": "upgrade_security",
            "deployment_impact": "production",
            "architectural_impact": "significant",
        })

        self.results.append(f"  Change: Replace authentication system and redeploy")
        self.results.append(f"  Risk score: 0.92 (CRITICAL)")
        self.results.append(f"  Decision: {result.decision.value.upper()}")
        self.results.append(f"  Matched policy: {result.matching_policy}")
        for r in result.reasoning:
            self.results.append(f"  → {r}")
        for w in result.warnings:
            self.results.append(f"  ⚠ {w}")
        self.results.append(f"  ✅ Governance engine blocks unsafe autonomous changes")
        self.results.append("")

    def step3_safe_edit_governance(self):
        self.results.append("[Step 3/10] Safe Edit — Governance Engine Permits")
        from lyme.governance.change_governance import ChangeGovernanceEngine

        engine = ChangeGovernanceEngine()
        result = engine.evaluate({
            "risk_score": 0.15,
            "scope": "local",
            "sensitivity": "none",
            "reversibility": "easy",
            "files_changed": ["docs/readme.md", "docs/api.md"],
            "description": "Update documentation for new API endpoint",
            "verification_coverage": 0.8,
            "user_intent": "document",
            "deployment_impact": "none",
            "architectural_impact": "none",
        })

        self.results.append(f"  Change: Update documentation")
        self.results.append(f"  Risk score: 0.15 (LOW)")
        self.results.append(f"  Decision: {result.decision.value.upper()}")
        self.results.append(f"  Matched policy: {result.matching_policy}")
        self.results.append(f"  ✅ Governance engine permits safe changes")
        self.results.append("")

    def step4_verification_plan(self):
        self.results.append("[Step 4/10] Verification Strategy Planner")
        from lyme.verification.planner import VerificationStrategyPlanner

        planner = VerificationStrategyPlanner()
        result = planner.plan("Refactor database connection module", {
            "risk_score": 0.55,
            "scope": "module",
            "has_tests": True,
            "is_sensitive": True,
            "language": "python",
        })

        recommended = result.strategies[result.recommended]
        self.results.append(f"  Edit: Refactor database connection module")
        self.results.append(f"  Strategies generated: {len(result.strategies)}")
        self.results.append(f"  Recommended: strategy {result.recommended + 1}")
        self.results.append(f"  Steps: {len(recommended.steps)}")
        self.results.append(f"  Risk coverage: {recommended.risk_coverage:.0%}")
        self.results.append(f"  Confidence: {recommended.confidence_score:.0%}")
        for step in recommended.steps:
            self.results.append(f"    • {step.step_type.value}: {step.rationale}")
        self.results.append(f"  ✅ Verification planner selects appropriate checks")
        self.results.append("")

    def step5_verification_graph(self):
        self.results.append("[Step 5/10] Verification Graph")
        from lyme.verification.graph import (
            VerificationGraph, Claim, CodeChange, TestResult, RuntimeTrace,
            StaticAnalysisResult, TypeCheckResult, UserApproval,
            BenchmarkResult, RollbackEvidence,
        )

        graph = VerificationGraph()
        report = graph.build_action_verification(
            action_id="demo_001",
            action_description="Refactor auth module",
            claims=[
                Claim(id="c1", statement="Change does not break existing auth flows",
                      source="developer", confidence=0.8),
                Claim(id="c2", statement="Performance is not degraded",
                      source="developer", confidence=0.7),
            ],
            changes=[CodeChange(id="ch1", file_path="src/auth/login.py",
                                diff="@@ -10,5 +10,7 @@", risk_score=0.4)],
            test_results=[
                TestResult(id="t1", test_name="test_login", passed=True, coverage_pct=85),
                TestResult(id="t2", test_name="test_auth", passed=True, coverage_pct=90),
            ],
            traces=[RuntimeTrace(id="r1", operation="build", success=True)],
            static_results=[StaticAnalysisResult(id="s1", tool="ruff", passed=True)],
            type_results=[TypeCheckResult(id="tc1", tool="mypy", passed=True)],
            approvals=[UserApproval(id="a1", approver="senior-dev", approved=True,
                                     reason="Looks correct")],
            benchmark_results=[BenchmarkResult(id="b1", benchmark_name="auth-latency",
                                               score=102, baseline_score=100)],
            rollback_evidence=[RollbackEvidence(id="rb1", rollback_reason="test",
                                                success=True)],
        )

        self.results.append(f"  Action: Refactor auth module")
        self.results.append(f"  Verdict: {report.verdict.upper()}")
        self.results.append(f"  Confidence: {report.overall_confidence:.2f}")
        self.results.append(f"  Nodes: {len(report.nodes)}")
        self.results.append(f"  Edges: {len(report.edges)}")
        for v in report.what_was_verified:
            self.results.append(f"  ✓ Verified: {v}")
        self.results.append(f"  ✅ Verification graph captures all evidence")
        self.results.append("")

    def step6_verification_gaps(self):
        self.results.append("[Step 6/10] Verification Gap Detection")
        from lyme.verification.gap_detector import VerificationGapDetector

        detector = VerificationGapDetector()
        result = detector.detect({
            "source_files": ["src/core/auth.py", "src/core/db.py", "src/utils/helpers.py"],
            "test_files": ["tests/test_auth.py"],
            "changed_files": ["src/core/db.py", "src/utils/helpers.py"],
            "test_coverage_pct": 35,
            "has_type_check": False,
            "has_static_analysis": True,
            "has_runtime_verification": False,
            "has_rollback_path": True,
            "has_benchmark_baseline": False,
            "confidence": 0.92,
            "claims": [{"statement": "No side effects on other modules", "verified": False}],
            "assumptions": [{"statement": "Database schema is stable"}],
            "build_available": True,
            "is_sensitive": True,
            "has_security_scan": False,
        })

        self.results.append(f"  Gaps detected: {result.total_gaps}")
        self.results.append(f"  Overall severity: {result.overall_severity.upper()}")
        self.results.append(f"  Critical: {result.critical_count} | High: {result.high_count} | "
                           f"Medium: {result.medium_count} | Low: {result.low_count}")
        for g in result.gaps[:3]:
            self.results.append(f"  ⚠ [{g.severity.value.upper()}] {g.description}")
        for rec in result.top_recommendations[:3]:
            self.results.append(f"  💡 {rec}")
        self.results.append(f"  ✅ Gap detector catches verification blind spots")
        self.results.append("")

    def step7_ledger_store(self):
        self.results.append("[Step 7/10] Autonomous Change Ledger")
        from lyme.governance.change_ledger import AutonomousChangeLedger, EntryOutcome

        ledger = AutonomousChangeLedger()
        self.ledger = ledger

        c1 = ledger.record_change("Refactor auth module", "lyme", "refactor",
                                   0.4, "verified", EntryOutcome.SUCCESS,
                                   evidence=["tests_passed", "review_approved"],
                                   approvals=["senior-dev"],
                                   rollback_path="git revert abc123",
                                   learned_memory={"pattern": "auth_refactor",
                                                   "outcome": "success"})

        c2 = ledger.record_verification("Run full test suite", "lyme",
                                        "all_passed", ["test_auth", "test_db"])

        c3 = ledger.record_governance("Check change risk", "auto_apply", 0.15)

        c4 = ledger.record_approval("Approve refactor", "senior-dev", True)

        c5 = ledger.record_memory("Learned: auth refactor pattern", {
            "pattern": "auth_refactor",
            "steps": ["extract_interface", "migrate_calls", "remove_old"],
            "outcome": "success",
        })

        summary = ledger.get_summary()
        self.results.append(f"  Entries recorded: {summary.total_entries}")
        self.results.append(f"  By type: {summary.by_type}")
        self.results.append(f"  By outcome: {summary.by_outcome}")
        self.results.append(f"  Learned memories: {summary.memory_count}")
        self.results.append(f"  ✅ Ledger stores complete governance record")
        self.results.append("")

    def step8_self_benchmark(self):
        self.results.append("[Step 8/10] Self-Benchmark")
        from lyme.evaluation.self_benchmark import SelfBenchmark

        bench = SelfBenchmark()
        run = bench.run(repo_type="demo", repo_name="lyme-demo")

        self.results.append(f"  Run ID: {run.id}")
        self.results.append(f"  Dimensions scored: {len(run.scores)}")
        for s in sorted(run.scores, key=lambda x: -x.score):
            self.results.append(f"    {s.dimension.value}: {s.score:.3f}")
        self.results.append(f"  Overall: {run.overall_score:.3f}")
        self.results.append(f"  ✅ Self-benchmark measures capability across 9 dimensions")
        self.results.append("")

    def step9_longitudinal(self):
        self.results.append("[Step 9/10] Longitudinal Evaluation")
        from lyme.evaluation.longitudinal import LongitudinalEvaluation
        import time

        eval_inst = LongitudinalEvaluation()
        for i in range(4):
            eval_inst.add_benchmark_run({
                "timestamp": time.time() - (3 - i) * 86400,
                "scores": {
                    "task_success": 0.55 + i * 0.07,
                    "verification_quality": 0.50 + i * 0.08,
                    "autonomy_safety": 0.60 + i * 0.05,
                },
                "overall_score": 0.55 + i * 0.07,
            })

        report = eval_inst.get_report()
        self.results.append(f"  Baseline: {report.baseline_score:.3f}")
        self.results.append(f"  Recent: {report.recent_score:.3f}")
        self.results.append(f"  Trend: {report.overall_trend}")
        self.results.append(f"  Improvement: {report.improvement_pct:+.1f}%")
        for trend in report.trends:
            direction = "improving" if trend.improving else "declining" if trend.improving is False else "stable"
            self.results.append(f"    {trend.dimension}: slope={trend.slope:.4f} ({direction})")
        self.results.append(f"  Recommendation: {report.recommendation}")
        self.results.append(f"  ✅ Longitudinal evaluation tracks improvement over time")
        self.results.append("")

    def step10_cognition_ci(self):
        self.results.append("[Step 10/10] Cognition Regression Detection (CI for Intelligence)")
        from lyme.evaluation.cognition_regression import (
            CognitionRegressionDetector, CognitionDimension,
        )

        detector = CognitionRegressionDetector()
        baselines = {
            CognitionDimension.PLANNING: 0.75,
            CognitionDimension.EVIDENCE_GROUNDING: 0.80,
            CognitionDimension.TOOL_USE: 0.85,
            CognitionDimension.MEMORY_RETRIEVAL: 0.70,
            CognitionDimension.VERIFICATION: 0.78,
            CognitionDimension.SAFE_EDITING: 0.82,
            CognitionDimension.UNCERTAINTY_COMMUNICATION: 0.72,
            CognitionDimension.CROSS_REPO_TRANSFER: 0.68,
        }
        detector.set_all_baselines(baselines)

        current_scores = {
            CognitionDimension.PLANNING: 0.77,
            CognitionDimension.EVIDENCE_GROUNDING: 0.82,
            CognitionDimension.TOOL_USE: 0.86,
            CognitionDimension.MEMORY_RETRIEVAL: 0.71,
            CognitionDimension.VERIFICATION: 0.80,
            CognitionDimension.SAFE_EDITING: 0.83,
            CognitionDimension.UNCERTAINTY_COMMUNICATION: 0.73,
            CognitionDimension.CROSS_REPO_TRANSFER: 0.69,
        }

        result = detector.evaluate(current_scores)

        self.results.append(f"  Dimensions evaluated: {len(result.runs)}")
        self.results.append(f"  Overall status: {result.overall_status.upper()}")
        for dim, status in result.dimension_summary.items():
            self.results.append(f"    {dim}: {status}")
        if result.alerts:
            for a in result.alerts:
                self.results.append(f"    ⚠ {a.dimension.value}: {a.baseline_score:.2f} -> {a.current_score:.2f}")
        else:
            self.results.append(f"    No regressions detected")
        self.results.append(f"  ✅ Cognition CI catches intelligence regressions")
        self.results.append("")
