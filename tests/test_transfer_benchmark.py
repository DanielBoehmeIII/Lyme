"""Tests for skill transfer benchmark."""


def test_transfer_benchmark_suite():
    """SkillTransferBenchmark runs a suite and produces metrics."""
    from lyme.skills.transfer_benchmark import SkillTransferBenchmark, TransferTestOutcome

    benchmark = SkillTransferBenchmark()
    cases = benchmark.define_suite()
    assert len(cases) >= 4

    result = benchmark.run_suite(cases)
    metrics = result.metrics

    assert metrics["total_tests"] == len(cases)
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["transfer_success_rate"] <= 1
    assert 0 <= metrics["false_transfer_rate"] <= 1
    assert 0 <= metrics["overgeneralization_rate"] <= 1
    assert 0 <= metrics["avg_calibration_error"] <= 1
    assert metrics["avg_verification_quality"] >= 0


def test_transfer_benchmark_summary():
    """Benchmark summary is well-formed."""
    from lyme.skills.transfer_benchmark import SkillTransferBenchmark

    benchmark = SkillTransferBenchmark()
    cases = benchmark.define_suite()
    benchmark.run_suite(cases)

    summary = benchmark.summarize()
    assert summary.startswith("#")
    assert "Accuracy" in summary or "Tests" in summary
