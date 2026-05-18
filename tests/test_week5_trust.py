"""Tests for Week 5 — Trust."""


def test_reproducibility_empty():
    from lyme.trust import ReproducibilityEngine
    re = ReproducibilityEngine()
    report = re.report()
    assert report.total_executions == 0


def test_reproducibility_verify():
    from lyme.trust import ReproducibilityEngine
    re = ReproducibilityEngine()
    report = re.verify_execution(lambda x: {"r": x}, "test", model_name="m", seed=0)
    assert report.total_executions == 1
    assert report.determinism_rate == 1.0


def test_reproducibility_deterministic():
    from lyme.trust import ReproducibilityEngine
    re = ReproducibilityEngine()
    report = re.verify_execution(lambda x: x + 1, 5, runs=3)
    assert report.deterministic_count == 1


def test_reproducibility_snapshot():
    from lyme.trust import ReproducibilityEngine
    re = ReproducibilityEngine()
    snap = re.snapshot_environment()
    assert len(snap) > 0


def test_reproducibility_report():
    from lyme.trust import ReproducibilityEngine
    re = ReproducibilityEngine()
    re.verify_execution(lambda x: x, 1, runs=2)
    report = re.report()
    output = report.render_cli()
    assert "REPRODUCIBILITY" in output


def test_explainability_basic():
    from lyme.trust import ExplainabilityEngine, DecisionType
    ee = ExplainabilityEngine()
    exp = ee.explain(DecisionType.EDIT, "Fix bug",
                     ["Premise 1"], [["Evidence 1"]], ["Conclusion 1"])
    assert len(exp.reasoning_chain) == 1
    assert exp.decision_type == DecisionType.EDIT


def test_explainability_multi_step():
    from lyme.trust import ExplainabilityEngine, DecisionType
    ee = ExplainabilityEngine()
    exp = ee.explain(DecisionType.APPROVE, "Approve PR",
                     ["Code compiles", "Tests pass", "Reviewed"],
                     [["exit 0"], ["all green"], ["2 approvals"]],
                     ["Build OK", "Tests OK", "Review OK"],
                     alternatives=["Request changes", "Defer"],
                     risks=["Merge conflict"])
    assert len(exp.reasoning_chain) == 3
    assert len(exp.alternative_considered) == 2


def test_explainability_markdown():
    from lyme.trust import ExplainabilityEngine, DecisionType
    ee = ExplainabilityEngine()
    exp = ee.explain(DecisionType.EDIT, "Test",
                     ["P"], [["E"]], ["C"])
    md = exp.to_markdown()
    assert "Decision:" in md


def test_explainability_report():
    from lyme.trust import ExplainabilityEngine, DecisionType
    ee = ExplainabilityEngine()
    ee.explain(DecisionType.EDIT, "T1", ["P1"], [["E1"]], ["C1"])
    ee.explain(DecisionType.REJECT, "T2", ["P2"], [["E2"]], ["C2"])
    report = ee.report()
    assert report.total_explanations == 2
    assert len(report.by_type) >= 1
    output = report.render_cli()
    assert "EXPLAINABILITY" in output


def test_rollback_safety_empty():
    from lyme.trust import RollbackSafety
    rs = RollbackSafety()
    report = rs.report()
    assert report.total_procedures == 0
    assert report.overall_status.value == "unsafe"


def test_rollback_safety_register():
    from lyme.trust import RollbackSafety
    rs = RollbackSafety()
    rs.register("revert", "Revert change", ["step1", "step2"])
    report = rs.report()
    assert report.total_procedures == 1


def test_rollback_safety_outcome():
    from lyme.trust import RollbackSafety
    rs = RollbackSafety()
    rs.register("revert", "Revert", ["step1"])
    rs.record_outcome("revert", True, 10.0)
    rs.record_outcome("revert", True, 15.0)
    assert rs.check("revert").value in ("safe", "conditional")


def test_rollback_safety_verify():
    from lyme.trust import RollbackSafety
    rs = RollbackSafety()
    rs.register("test", "Test proc", ["step"])
    rs.verify("test", lambda p: True)
    assert rs.check("test").value in ("safe", "conditional")


def test_rollback_safety_report():
    from lyme.trust import RollbackSafety
    rs = RollbackSafety()
    rs.register("p1", "P1", ["s1"])
    rs.record_outcome("p1", True, 5.0)
    report = rs.report()
    output = report.render_cli()
    assert "ROLLBACK SAFETY" in output


def test_architectural_reasoning_empty():
    from lyme.trust import ArchitecturalReasoning
    ar = ArchitecturalReasoning()
    report = ar.report()
    assert report.total_decisions == 0


def test_architectural_reasoning_record():
    from lyme.trust import ArchitecturalReasoning, ArchitecturalDecisionType
    ar = ArchitecturalReasoning()
    dec = ar.record_decision(ArchitecturalDecisionType.PATTERN_SELECTION,
                             "Use microservices", "Need scaling",
                             alternatives=["Monolith"],
                             constraints=["10K TPS"],
                             consequences=["Complexity"])
    assert dec.decision_type == ArchitecturalDecisionType.PATTERN_SELECTION


def test_architectural_reasoning_validate():
    from lyme.trust import ArchitecturalReasoning, ArchitecturalDecisionType
    ar = ArchitecturalReasoning()
    dec = ar.record_decision(ArchitecturalDecisionType.PATTERN_SELECTION,
                             "Good decision with details", "Well reasoned choice",
                             alternatives=["A", "B"], constraints=["C1"], consequences=[])
    val = ar.validate(dec)
    assert val.result.value in ("pass", "warning", "fail")


def test_architectural_reasoning_report():
    from lyme.trust import ArchitecturalReasoning, ArchitecturalDecisionType
    ar = ArchitecturalReasoning()
    ar.record_decision(ArchitecturalDecisionType.API_DESIGN, "REST API", "Standard",
                       alternatives=["GraphQL"])
    report = ar.report()
    assert report.total_decisions >= 1
    output = report.render_cli()
    assert "ARCHITECTURAL REASONING" in output


def test_reliability_dashboard_empty():
    from lyme.trust import ReliabilityDashboard
    dash = ReliabilityDashboard()
    report = dash.generate()
    assert report.total_systems_reporting == 0
    assert report.overall_health.value == "critical"


def test_reliability_dashboard_metrics():
    from lyme.trust import ReliabilityDashboard, TrustMetric
    dash = ReliabilityDashboard()
    dash.report_metric(TrustMetric.REPRODUCIBILITY, 0.9)
    dash.report_metric(TrustMetric.EXPLAINABILITY, 0.85)
    dash.report_metric(TrustMetric.ROLLBACK_SAFETY, 0.95)
    report = dash.generate()
    assert report.total_systems_reporting == 3
    assert len(report.metrics) == len(list(TrustMetric))


def test_reliability_dashboard_health():
    from lyme.trust import ReliabilityDashboard, TrustMetric
    dash = ReliabilityDashboard()
    for m in list(TrustMetric):
        dash.report_metric(m, 0.95)
    report = dash.generate()
    assert report.overall_health.value == "excellent"


def test_reliability_dashboard_low():
    from lyme.trust import ReliabilityDashboard, TrustMetric
    dash = ReliabilityDashboard()
    for m in list(TrustMetric):
        dash.report_metric(m, 0.15)
    report = dash.generate()
    assert report.overall_health.value == "poor" or report.overall_health.value == "critical"


def test_reliability_dashboard_cli():
    from lyme.trust import ReliabilityDashboard, TrustMetric
    dash = ReliabilityDashboard()
    dash.report_metric(TrustMetric.REPRODUCIBILITY, 0.8)
    report = dash.generate()
    output = report.render_cli()
    assert "RELIABILITY DASHBOARD" in output
