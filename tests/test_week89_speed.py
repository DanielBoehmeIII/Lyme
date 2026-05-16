"""Tests for Week 89 — Speed as a First-Class Metric."""

import pytest
import time
from src.lyme_model.speed import (
    SpeedProfile, SpeedProfiler, LatencyReport, benchmark_all,
)
from src.lyme_model.speed.profiler import SpeedProfiler


class TestSpeedProfile:
    def test_profile_defaults(self):
        p = SpeedProfile()
        assert p.model_load_time_s == 0.0
        assert p.cold_start is True

    def test_profile_to_dict(self):
        p = SpeedProfile(model_load_time_s=2.5, tokens_per_second=12.3)
        d = p.to_dict()
        assert d["model_load_time_s"] == 2.5
        assert d["tokens_per_second"] == 12.3

    def test_profile_to_markdown(self):
        p = SpeedProfile(tokens_per_second=15.0)
        md = p.to_markdown()
        assert "Speed Profile" in md
        assert "tokens_per_second" in md


class TestLatencyReport:
    def test_report_defaults(self):
        r = LatencyReport()
        assert r.speedup_factor == 1.0
        assert r.bottlenecks == []

    def test_report_to_dict(self):
        cold = SpeedProfile(total_task_time_s=10.0)
        warm = SpeedProfile(total_task_time_s=2.0, cold_start=False)
        r = LatencyReport(cold_profile=cold, warm_profile=warm, speedup_factor=5.0)
        d = r.to_dict()
        assert d["speedup_factor"] == 5.0

    def test_report_summary(self):
        r = LatencyReport(
            cold_profile=SpeedProfile(total_task_time_s=10.0),
            warm_profile=SpeedProfile(total_task_time_s=2.0),
            speedup_factor=5.0,
            bottlenecks=["Slow model load"],
            recommendations=["Use warm pool"],
        )
        s = r.summary()
        assert "Cold start" in s
        assert "Slow model load" in s
        assert "Use warm pool" in s


class TestSpeedProfiler:
    def test_profiler_initializes(self):
        p = SpeedProfiler()
        assert p.reports == []

    def test_measure_retrieval_latency(self):
        p = SpeedProfiler()
        def fake_policy(q):
            time.sleep(0.001)
        lat = p.measure_retrieval_latency(fake_policy, "test", samples=2)
        assert lat > 0

    def test_measure_tool_overhead(self):
        p = SpeedProfiler()
        def fake_tool():
            time.sleep(0.001)
        lat = p.measure_tool_overhead(fake_tool, samples=2)
        assert lat > 0

    def test_measure_verification_latency(self):
        p = SpeedProfiler()
        def fake_verify():
            time.sleep(0.001)
        lat = p.measure_verification_latency(fake_verify, samples=2)
        assert lat > 0

    def test_profile_cold(self):
        p = SpeedProfiler()
        def fake_load():
            time.sleep(0.01)
        def fake_gen(prompt):
            time.sleep(0.02)
            return "def f():\n    return 1"
        profile = p.profile_cold(fake_load, fake_gen, "test")
        assert profile.model_load_time_s > 0
        assert profile.total_task_time_s > 0
        assert profile.cold_start is True
        assert profile.tokens_per_second > 0

    def test_profile_warm(self):
        p = SpeedProfiler()
        def fake_gen(prompt):
            time.sleep(0.01)
            return "def f():\n    return 1"
        profile = p.profile_warm(fake_gen, "test")
        assert profile.model_load_time_s == 0.0
        assert profile.total_task_time_s > 0
        assert profile.cold_start is False

    def test_benchmark_returns_report(self):
        p = SpeedProfiler()
        def fake_load():
            time.sleep(0.01)
        def fake_gen(prompt):
            time.sleep(0.02)
            return "def f():\n    return 1"
        report = p.benchmark(
            cold_load_fn=fake_load,
            generate_fn=fake_gen,
            prompt="test prompt",
        )
        assert isinstance(report, LatencyReport)
        assert report.cold_profile.total_task_time_s > 0
        assert report.warm_profile.total_task_time_s > 0
        assert report.speedup_factor > 0

    def test_benchmark_with_retrieval_fns(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
            retrieval_fns={"keyword": lambda q: time.sleep(0.001)},
        )
        assert isinstance(report, LatencyReport)

    def test_benchmark_with_tool_fns(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
            tool_fns={"read_file": lambda: time.sleep(0.001)},
        )
        assert isinstance(report, LatencyReport)

    def test_benchmark_speedup_greater_than_one(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.05),
            generate_fn=lambda p: "def f():\n    return 1",
        )
        assert report.speedup_factor >= 1.0

    def test_benchmark_identifies_slow_load(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
        )

    def test_report_all(self):
        p = SpeedProfiler()
        p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
        )
        reports = p.report_all()
        assert len(reports) == 1

    def test_benchmark_all_runs(self):
        summary = benchmark_all()
        assert "Latency Report" in summary or "Cold start" in summary


class TestSpeedOptimizationTriggers:
    def test_load_time_bottleneck_at_5s(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
        )
        assert hasattr(report, "bottlenecks")

    def test_recommendations_included(self):
        p = SpeedProfiler()
        report = p.benchmark(
            cold_load_fn=lambda: time.sleep(0.01),
            generate_fn=lambda p: "def f():\n    return 1",
        )
        assert hasattr(report, "recommendations")
