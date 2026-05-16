"""Tests for verification (graph, planner, gap detector)."""


def test_verification_graph_basic():
    """VerificationGraph builds and renders a report."""
    from lyme.verification.graph import (
        VerificationGraph, Claim, CodeChange, TestResult, RuntimeTrace,
        StaticAnalysisResult, TypeCheckResult, UserApproval,
        BenchmarkResult, RollbackEvidence,
    )
    graph = VerificationGraph()
    report = graph.build_action_verification(
        action_id="test_001",
        action_description="Test change",
        claims=[Claim(id="c1", statement="Change is safe", source="test", confidence=0.8)],
        changes=[CodeChange(id="ch1", file_path="src/test.py", diff="", risk_score=0.3)],
        test_results=[TestResult(id="t1", test_name="test_feature", passed=True, coverage_pct=85)],
        traces=[RuntimeTrace(id="r1", operation="build", success=True)],
        static_results=[StaticAnalysisResult(id="s1", tool="ruff", passed=True)],
        type_results=[TypeCheckResult(id="tc1", tool="mypy", passed=True)],
        approvals=[UserApproval(id="a1", approver="user", approved=True)],
        benchmark_results=[BenchmarkResult(id="b1", benchmark_name="latency", score=100, baseline_score=95)],
        rollback_evidence=[RollbackEvidence(id="rb1", rollback_reason="test", success=True)],
    )
    assert report.verdict == "verified" or report.verdict == "partially_verified"
    assert report.overall_confidence > 0.5
    assert len(report.what_was_verified) > 0
    assert len(report.how_verified) > 0


def test_verification_graph_empty():
    """VerificationGraph handles minimal verification."""
    from lyme.verification.graph import VerificationGraph
    graph = VerificationGraph()
    report = graph.build_action_verification(
        action_id="test_empty", action_description="Empty change",
        claims=[], changes=[], test_results=[], traces=[],
        static_results=[], type_results=[], approvals=[],
        benchmark_results=[], rollback_evidence=[],
    )
    assert report.verdict == "unverified"
    assert report.overall_confidence <= 0.3
    assert len(report.unverified) > 0


def test_verification_graph_failed_tests():
    """VerificationGraph reports failures correctly."""
    from lyme.verification.graph import (
        VerificationGraph, Claim, CodeChange, TestResult,
    )
    graph = VerificationGraph()
    report = graph.build_action_verification(
        action_id="test_fail", action_description="Failing change",
        claims=[Claim(id="c1", statement="Works correctly", source="test", confidence=0.9)],
        changes=[CodeChange(id="ch1", file_path="src/test.py", diff="", risk_score=0.5)],
        test_results=[TestResult(id="t1", test_name="test_feature", passed=False,
                                  error_message="AssertionError")],
        traces=[], static_results=[], type_results=[], approvals=[],
        benchmark_results=[], rollback_evidence=[],
    )
    assert len(report.contradicting_evidence) > 0
    assert report.overall_confidence < 0.5


def test_verification_graph_cli_render():
    """CLI renderer produces output."""
    from lyme.verification.graph import (
        VerificationGraph, Claim, CodeChange, TestResult,
    )
    graph = VerificationGraph()
    report = graph.build_action_verification(
        action_id="test_cli", action_description="CLI test",
        claims=[Claim(id="c1", statement="Test claim", source="test", confidence=0.5)],
        changes=[CodeChange(id="ch1", file_path="src/test.py", diff="", risk_score=0.2)],
        test_results=[TestResult(id="t1", test_name="test_a", passed=True)],
        traces=[], static_results=[], type_results=[], approvals=[],
        benchmark_results=[], rollback_evidence=[],
    )
    output = graph.render_cli(report)
    assert "VERIFICATION GRAPH" in output
    assert "test_cli" in output
    assert len(output) > 50


def test_verification_planner_basic():
    """VerificationStrategyPlanner produces strategies."""
    from lyme.verification.planner import VerificationStrategyPlanner
    planner = VerificationStrategyPlanner()
    result = planner.plan("Add new feature", {
        "risk_score": 0.3, "scope": "local", "has_tests": True,
        "is_sensitive": False, "language": "python",
    })
    assert len(result.strategies) == 3
    assert 0 <= result.recommended < 3
    assert result.total_confidence > 0


def test_verification_planner_high_risk():
    """High-risk edits get thorough strategies."""
    from lyme.verification.planner import VerificationStrategyPlanner
    planner = VerificationStrategyPlanner()
    result = planner.plan("Modify auth system", {
        "risk_score": 0.8, "scope": "broad", "has_tests": True,
        "is_sensitive": True, "language": "python",
    })
    thorough = result.strategies[2]
    fast = result.strategies[0]
    assert len(thorough.steps) >= len(fast.steps)
    assert result.total_confidence > 0


def test_verification_planner_render():
    """PlannerResult renders CLI output."""
    from lyme.verification.planner import VerificationStrategyPlanner
    planner = VerificationStrategyPlanner()
    result = planner.plan("Test edit", {"risk_score": 0.2, "scope": "local"})
    output = result.render_cli()
    assert "VERIFICATION STRATEGY PLANNER" in output
    assert "RECOMMENDED" in output


def test_gap_detector_basic():
    """VerificationGapDetector finds gaps."""
    from lyme.verification.gap_detector import VerificationGapDetector
    detector = VerificationGapDetector()
    result = detector.detect({
        "source_files": ["src/module.py", "src/utils.py"],
        "test_files": [],
        "changed_files": ["src/module.py"],
        "test_coverage_pct": 30,
        "has_type_check": False,
        "has_static_analysis": False,
        "has_runtime_verification": False,
        "has_rollback_path": False,
        "has_benchmark_baseline": False,
        "confidence": 0.95,
        "claims": [{"statement": "Safe change", "verified": False}],
        "assumptions": [{"statement": "No side effects"}],
        "build_available": True,
        "is_sensitive": False,
    })
    assert result.total_gaps > 0
    assert result.critical_count >= 0
    assert len(result.top_recommendations) > 0


def test_gap_detector_clean():
    """VerificationGapDetector finds few gaps for well-verified code."""
    from lyme.verification.gap_detector import VerificationGapDetector
    detector = VerificationGapDetector()
    result = detector.detect({
        "source_files": ["src/module.py", "src/utils.py"],
        "test_files": ["tests/test_module.py", "tests/test_utils.py"],
        "changed_files": ["src/module.py"],
        "test_coverage_pct": 85,
        "has_type_check": True,
        "has_static_analysis": True,
        "has_runtime_verification": True,
        "has_rollback_path": True,
        "has_benchmark_baseline": True,
        "confidence": 0.8,
        "claims": [{"statement": "Safe change", "verified": True}],
        "assumptions": [],
        "build_available": True,
        "is_sensitive": False,
        "reviewed": True,
    })
    assert result.overall_severity in ("low", "info")


def test_gap_detector_render():
    """GapDetectionResult CLI renderer works."""
    from lyme.verification.gap_detector import VerificationGapDetector
    detector = VerificationGapDetector()
    result = detector.detect({
        "source_files": ["src/module.py"],
        "test_files": [],
        "changed_files": ["src/module.py"],
        "test_coverage_pct": 30,
        "has_type_check": False,
        "has_static_analysis": False,
        "has_runtime_verification": False,
        "has_rollback_path": False,
        "has_benchmark_baseline": False,
        "confidence": 0.95,
        "claims": [],
        "assumptions": [],
        "build_available": True,
        "is_sensitive": False,
    })
    output = result.render_cli()
    assert "VERIFICATION GAP DETECTOR" in output
    assert "total gaps" in output.lower() or "Total gaps" in output
