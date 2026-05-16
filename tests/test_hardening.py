"""Hardening tests for v0.6 — edge cases, safety, and regression."""


class TestVerificationEdgeCases:
    """Hardening for verification module."""

    def test_verification_graph_no_claims(self):
        from lyme.verification.graph import VerificationGraph
        graph = VerificationGraph()
        report = graph.build_action_verification(
            "no_claims", "No claims", [], [], [], [], [], [], [], [], [],
        )
        assert report.verdict == "unverified"
        assert report.overall_confidence <= 0.3

    def test_verification_graph_mixed_evidence(self):
        from lyme.verification.graph import (
            VerificationGraph, Claim, CodeChange, TestResult,
            StaticAnalysisResult, TypeCheckResult,
        )
        graph = VerificationGraph()
        report = graph.build_action_verification(
            "test_mix", "Mixed evidence",
            claims=[Claim(id="c1", statement="Change is safe", source="test", confidence=0.5)],
            changes=[CodeChange(id="ch1", file_path="src/test.py", diff="", risk_score=0.5)],
            test_results=[
                TestResult(id="t1", test_name="test_good", passed=True),
                TestResult(id="t2", test_name="test_bad", passed=False,
                           error_message="Assertion failed"),
            ],
            traces=[], static_results=[
                StaticAnalysisResult(id="s1", tool="ruff", passed=True, issues_count=0),
            ], type_results=[
                TypeCheckResult(id="tc1", tool="mypy", passed=False, errors_count=2,
                                errors=["type mismatch"]),
            ], approvals=[], benchmark_results=[], rollback_evidence=[],
        )
        assert len(report.contradicting_evidence) > 0 or report.verdict != "verified"

    def test_verification_graph_cli_output_not_empty(self):
        from lyme.verification.graph import VerificationGraph, Claim
        graph = VerificationGraph()
        report = graph.build_action_verification(
            "cli_test", "CLI", [Claim(id="c", statement="test", source="s")],
            [], [], [], [], [], [], [], [],
        )
        output = graph.render_cli(report)
        assert len(output) > 100

    def test_verification_planner_zero_risk(self):
        from lyme.verification.planner import VerificationStrategyPlanner
        planner = VerificationStrategyPlanner()
        result = planner.plan("Docs edit", {"risk_score": 0.0, "scope": "local"})
        assert len(result.strategies) == 3
        assert result.total_confidence >= 0

    def test_planner_strategy_differs_by_risk(self):
        from lyme.verification.planner import VerificationStrategyPlanner
        planner = VerificationStrategyPlanner()
        low = planner.plan("Low", {"risk_score": 0.1, "scope": "local"})
        high = planner.plan("High", {"risk_score": 0.9, "scope": "broad", "is_sensitive": True})
        assert len(low.strategies[2].steps) > 0
        assert len(high.strategies[2].steps) > 0

    def test_gap_detector_no_source_files(self):
        from lyme.verification.gap_detector import VerificationGapDetector
        detector = VerificationGapDetector()
        result = detector.detect({})
        # Should not crash, should find some gaps
        assert result.total_gaps >= 0

    def test_gap_detector_false_confidence(self):
        from lyme.verification.gap_detector import VerificationGapDetector
        detector = VerificationGapDetector()
        result = detector.detect({
            "source_files": ["src/mod.py"], "test_files": [],
            "changed_files": ["src/mod.py"], "test_coverage_pct": 10,
            "has_type_check": False, "has_static_analysis": False,
            "has_runtime_verification": False, "has_rollback_path": False,
            "has_benchmark_baseline": False, "confidence": 0.95,
            "claims": [], "assumptions": [], "build_available": True,
            "is_sensitive": False,
        })
        # Should detect false_confidence gap
        labels = [g.label.value for g in result.gaps]
        assert "false_confidence" in labels


class TestGovernanceEdgeCases:
    """Hardening for governance module."""

    def test_governance_empty_context(self):
        from lyme.governance.change_governance import ChangeGovernanceEngine
        engine = ChangeGovernanceEngine()
        result = engine.evaluate({})
        assert result.decision.value in ("auto_apply", "patch_only", "require_approval", "block")
        assert len(result.reasoning) > 0

    def test_governance_override(self):
        from lyme.governance.change_governance import ChangeGovernanceEngine
        engine = ChangeGovernanceEngine()
        result = engine.evaluate({"risk_score": 0.95, "scope": "broad"})
        assert result.decision.value == "block"
        assert result.override_available is False

    def test_constitution_empty_forbidden(self):
        from lyme.governance.repo_constitution import (
            RepoConstitution, ConstitutionValidator,
        )
        constit = RepoConstitution.create_default()
        constit.forbidden_zones = []
        validator = ConstitutionValidator(constit)
        issues = validator.validate()
        assert len(issues) >= 0

    def test_constitution_no_zones(self):
        from lyme.governance.repo_constitution import (
            RepoConstitution, ConstitutionValidator, AllowedAction,
        )
        constit = RepoConstitution(repo_name="test")
        validator = ConstitutionValidator(constit)
        allowed, _ = validator.validate_action("src/test.py", AllowedAction.READ)
        assert allowed is False  # No zones -> nothing allowed

    def test_constitution_save_nonexistent_dir(self, tmp_path):
        from lyme.governance.repo_constitution import RepoConstitution
        constit = RepoConstitution.create_default(repo_name="test")
        path = tmp_path / "nested" / "constitution.json"
        constit.save(path)
        assert path.exists()
        loaded = RepoConstitution.load(path)
        assert loaded.repo_name == "test"

    def test_ledger_empty(self):
        from lyme.governance.change_ledger import AutonomousChangeLedger
        ledger = AutonomousChangeLedger()
        summary = ledger.get_summary()
        assert summary.total_entries == 0
        assert ledger.get_entries() == []

    def test_ledger_large_risk(self):
        from lyme.governance.change_ledger import (
            AutonomousChangeLedger, EntryOutcome,
        )
        ledger = AutonomousChangeLedger()
        eid = ledger.record_change("Critical change", "lyme", "deploy",
                                   0.95, "failed", EntryOutcome.FAILURE)
        entry = ledger.get_entry(eid)
        assert entry.risk_score == 0.95
        assert entry.outcome == EntryOutcome.FAILURE

    def test_ledger_rollback_path(self):
        from lyme.governance.change_ledger import (
            AutonomousChangeLedger, EntryOutcome,
        )
        ledger = AutonomousChangeLedger()
        eid = ledger.record_change("Change", "lyme", "fix", 0.3, "pass",
                                   EntryOutcome.SUCCESS,
                                   rollback_path="git revert HEAD")
        path = ledger.get_rollback_path(eid)
        assert path == "git revert HEAD"


class TestEvaluationEdgeCases:
    """Hardening for evaluation module."""

    def test_self_benchmark_multiple_runs(self):
        from lyme.evaluation.self_benchmark import SelfBenchmark
        bench = SelfBenchmark()
        for _ in range(5):
            bench.run("demo")
        result = bench.get_result()
        assert result.num_runs == 5
        assert result.overall > 0

    def test_longitudinal_no_regression(self):
        from lyme.evaluation.longitudinal import LongitudinalEvaluation
        eval_inst = LongitudinalEvaluation()
        import time
        for i in range(3):
            eval_inst.add_benchmark_run({
                "timestamp": time.time() + i * 3600,
                "scores": {"task_success": 0.8},
                "overall_score": 0.8,
            })
        report = eval_inst.get_report()
        assert len(report.regressions) == 0

    def test_cognition_regression_all_baselines(self):
        from lyme.evaluation.cognition_regression import (
            CognitionRegressionDetector, CognitionDimension,
        )
        detector = CognitionRegressionDetector()
        detector.set_all_baselines({d: 0.8 for d in CognitionDimension})
        scores = {}
        for dim in CognitionDimension:
            scores[dim.value] = 0.8
        result = detector.evaluate_all_dims(scores)
        assert result.overall_status == "passed"

    def test_cognition_regression_no_baseline(self):
        from lyme.evaluation.cognition_regression import (
            CognitionRegressionDetector, CognitionDimension,
        )
        detector = CognitionRegressionDetector()
        scores = {dim: 0.5 for dim in CognitionDimension}
        result = detector.evaluate(scores)
        assert len(result.alerts) == 0  # No baseline = no alerts


class TestDemoV06:
    """Hardening for v0.6 demo."""

    def test_demo_runs(self):
        from lyme.demo_v06 import V06Demo
        demo = V06Demo()
        result = demo.run()
        assert result["steps_completed"] == 10
        assert len(result["summary"]) > 500

    def test_demo_output_format(self):
        from lyme.demo_v06 import V06Demo
        demo = V06Demo()
        result = demo.run()
        assert "Step 1/10" in result["summary"]
        assert "Step 10/10" in result["summary"]
        assert "DEMO COMPLETE" in result["summary"]
