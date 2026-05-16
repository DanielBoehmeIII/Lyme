"""Tests for evaluation (self-benchmark, longitudinal, cognition)."""


def test_self_benchmark_run():
    """SelfBenchmark produces a run with all dimensions."""
    from lyme.evaluation.self_benchmark import SelfBenchmark
    bench = SelfBenchmark()
    run = bench.run(repo_type="demo", repo_name="test")
    assert len(run.scores) == 9
    assert 0 <= run.overall_score <= 1
    assert run.repo_type == "demo"


def test_self_benchmark_result():
    """SelfBenchmark aggregates results correctly."""
    from lyme.evaluation.self_benchmark import SelfBenchmark
    bench = SelfBenchmark()
    bench.run("demo", "test-1")
    bench.run("demo", "test-2")
    result = bench.get_result()
    assert result.num_runs == 2
    assert len(result.aggregated_scores) == 9
    assert 0 <= result.overall <= 1


def test_self_benchmark_markdown():
    """BenchmarkResult renders markdown."""
    from lyme.evaluation.self_benchmark import SelfBenchmark
    bench = SelfBenchmark()
    bench.run("demo", "test")
    result = bench.get_result()
    md = result.to_markdown()
    assert "Self-Benchmark" in md
    assert "Overall Score" in md


def test_longitudinal_empty():
    """LongitudinalEvaluation handles empty data."""
    from lyme.evaluation.longitudinal import LongitudinalEvaluation
    eval_inst = LongitudinalEvaluation()
    report = eval_inst.get_report()
    assert report.overall_trend == "stable"
    assert "No benchmark data" in report.recommendation


def test_longitudinal_with_data():
    """LongitudinalEvaluation detects trends."""
    from lyme.evaluation.longitudinal import LongitudinalEvaluation
    import time
    eval_inst = LongitudinalEvaluation()

    for i in range(5):
        eval_inst.add_benchmark_run({
            "timestamp": time.time() + i * 86400,
            "scores": {"task_success": 0.5 + i * 0.08, "verification_quality": 0.6},
            "overall_score": 0.5 + i * 0.08,
        })

    report = eval_inst.get_report()
    assert len(report.trends) > 0
    assert report.improvement_pct != 0
    assert report.overall_trend in ("improving", "stable")


def test_longitudinal_regression_detection():
    """LongitudinalEvaluation detects regressions."""
    from lyme.evaluation.longitudinal import LongitudinalEvaluation
    import time
    eval_inst = LongitudinalEvaluation()

    eval_inst.add_benchmark_run({
        "timestamp": time.time(),
        "scores": {"task_success": 0.8},
        "overall_score": 0.8,
    })
    eval_inst.add_benchmark_run({
        "timestamp": time.time() + 3600,
        "scores": {"task_success": 0.5},
        "overall_score": 0.5,
    })

    report = eval_inst.get_report()
    assert len(report.regressions) > 0


def test_cognition_regression_basic():
    """CognitionRegressionDetector evaluates dimensions."""
    from lyme.evaluation.cognition_regression import (
        CognitionRegressionDetector, CognitionDimension,
    )
    detector = CognitionRegressionDetector()
    detector.set_all_baselines({d: 0.8 for d in CognitionDimension})

    scores = {d: 0.75 for d in CognitionDimension}
    result = detector.evaluate(scores)
    assert len(result.runs) == len(CognitionDimension)
    assert result.overall_status in ("passed", "warning")


def test_cognition_regression_detects_drops():
    """CognitionRegressionDetector flags significant regressions."""
    from lyme.evaluation.cognition_regression import (
        CognitionRegressionDetector, CognitionDimension,
    )
    detector = CognitionRegressionDetector()
    detector.set_baseline(CognitionDimension.PLANNING, 0.9)
    detector.set_baseline(CognitionDimension.TOOL_USE, 0.9)

    result = detector.evaluate({
        CognitionDimension.PLANNING: 0.4,
        CognitionDimension.EVIDENCE_GROUNDING: 0.8,
        CognitionDimension.TOOL_USE: 0.85,
        CognitionDimension.MEMORY_RETRIEVAL: 0.8,
        CognitionDimension.VERIFICATION: 0.8,
        CognitionDimension.SAFE_EDITING: 0.8,
        CognitionDimension.UNCERTAINTY_COMMUNICATION: 0.8,
        CognitionDimension.CROSS_REPO_TRANSFER: 0.8,
    })
    assert len(result.alerts) >= 1
    assert result.dimension_summary.get("planning") == "regression"
    assert result.overall_status in ("regression", "warning")


def test_cognition_regression_cli_render():
    """RegressionResult CLI renderer works."""
    from lyme.evaluation.cognition_regression import (
        CognitionRegressionDetector, CognitionDimension,
    )
    detector = CognitionRegressionDetector()
    detector.set_baseline(CognitionDimension.PLANNING, 0.9)

    result = detector.evaluate({
        CognitionDimension.PLANNING: 0.5,
        CognitionDimension.EVIDENCE_GROUNDING: 0.8,
        CognitionDimension.TOOL_USE: 0.8,
        CognitionDimension.MEMORY_RETRIEVAL: 0.8,
        CognitionDimension.VERIFICATION: 0.8,
        CognitionDimension.SAFE_EDITING: 0.8,
        CognitionDimension.UNCERTAINTY_COMMUNICATION: 0.8,
        CognitionDimension.CROSS_REPO_TRANSFER: 0.8,
    })
    output = result.render_cli()
    assert "COGNITION REGRESSION" in output
    assert "planning" in output.lower()
