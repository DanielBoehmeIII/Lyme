"""Week 5 — Benchmark Harness tests."""

import tempfile
from pathlib import Path
from lyme_model.eval.benchmark_harness import (
    ModelBenchmarkHarness, BenchmarkTask, TaskResult, BenchmarkReport,
    BENCHMARK_TASKS, REGRESSION_TASKS,
)


def test_benchmark_harness_imports():
    assert ModelBenchmarkHarness is not None
    assert BenchmarkTask is not None


def test_benchmark_task_dataclass():
    t = BenchmarkTask(name="test", category="repo_id", prompt="What lang?")
    assert t.name == "test"
    assert t.category == "repo_id"


def test_task_result_dataclass():
    r = TaskResult(task_name="test", category="repo_id", success=True, latency_s=0.5)
    assert r.success
    assert r.latency_s == 0.5
    d = r.to_dict()
    assert d["task_name"] == "test"


def test_benchmark_report_dataclass():
    r = BenchmarkReport(run_id="abc", timestamp="now", total_tasks=10, passed=8, failed=2)
    assert r.passed == 8
    d = r.to_dict()
    assert d["run_id"] == "abc"


def test_benchmark_tasks_defined():
    assert len(BENCHMARK_TASKS) > 0
    assert len(REGRESSION_TASKS) > 0
    for t in BENCHMARK_TASKS:
        assert t.name
        assert t.category
        assert t.prompt


def test_benchmark_harness_runs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        (tmp / "test.py").write_text("def test():\n    pass\n")

        harness = ModelBenchmarkHarness(str(tmp))
        # Run with a small subset
        tasks = [BENCHMARK_TASKS[0]]
        report = harness.run_benchmark(tasks)
        assert report.total_tasks == 1
        assert report.run_id is not None


def test_benchmark_harness_all():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        (tmp / "src").mkdir()
        (tmp / "src" / "main.py").write_text("print('hello')\n")

        harness = ModelBenchmarkHarness(str(tmp))
        tasks = BENCHMARK_TASKS[:3]
        report = harness.run_benchmark(tasks)
        assert report.total_tasks == 3
        assert report.passed + report.failed == 3


def test_benchmark_harness_regression():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        harness = ModelBenchmarkHarness(str(tmp))
        report = harness.run_regression()
        assert report.run_id is not None


def test_benchmark_harness_run_all():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        harness = ModelBenchmarkHarness(str(tmp))
        result = harness.run_all()
        assert "standard" in result
        assert "regression" in result
        assert "combined" in result


def test_benchmark_harness_saves_report():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        harness = ModelBenchmarkHarness(str(tmp))
        tasks = BENCHMARK_TASKS[:2]
        report = harness.run_benchmark(tasks)
        expected_file = Path("lyme-output") / "benchmarks" / f"harness-{report.run_id}.json"
        assert expected_file.exists()
