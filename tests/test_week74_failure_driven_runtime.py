"""Tests for Week 74 — Failure-Driven Runtime Design."""

import pytest
from src.lyme_model.runtime.failure_driven import (
    FailureDrivenRuntime,
    FAILURE_MITIGATIONS,
    Guardrail,
    MeasurementHook,
    BenchmarkScenario,
)
from src.lyme_model.failures.taxonomy import LocalCodingFailureCategory


class TestFailureMitigations:
    def test_all_12_categories_have_mitigations(self):
        assert len(FAILURE_MITIGATIONS) == 12

    def test_each_mitigation_has_all_fields(self):
        required = {"root_cause", "mitigation", "guardrail", "measurement", "benchmark"}
        for info in FAILURE_MITIGATIONS.values():
            for field in required:
                assert field in info, f"Missing field: {field}"
                assert info[field], f"Empty field: {field}"


class TestFailureDrivenRuntime:
    def test_runtime_initializes(self):
        runtime = FailureDrivenRuntime()
        assert len(runtime.guardrails) == 12
        assert len(runtime.get_mitigations()) == 12

    def test_pre_flight_context_warning(self):
        runtime = FailureDrivenRuntime()
        trace = {"context_tokens": 3800, "model_max_tokens": 4096}
        triggered = runtime._pre_flight_check("test", trace)
        assert len(triggered) >= 1
        assert triggered[0]["guardrail"] == "GuardrailContextWindow"

    def test_pre_flight_context_ok(self):
        runtime = FailureDrivenRuntime()
        trace = {"context_tokens": 1000, "model_max_tokens": 4096}
        triggered = runtime._pre_flight_check("test", trace)
        assert len(triggered) == 0

    def test_apply_mitigations_to_failures(self):
        runtime = FailureDrivenRuntime()
        from src.lyme_model.failures.taxonomy import LocalCodingFailureRecord
        failures = [
            LocalCodingFailureRecord(
                failure_id="t1",
                category=LocalCodingFailureCategory.HALLUCINATED_API,
                description="bad symbol",
                severity="critical",
            ),
        ]
        applied = runtime._apply_mitigations(failures, {})
        assert len(applied) == 1
        assert applied[0]["category"] == "hallucinated_api"
        assert failures[0].mitigated_by is not None

    def test_post_flight_loop_detection(self):
        runtime = FailureDrivenRuntime()
        trace = {
            "tool_calls": [
                {"tool": "read_file", "params": {"path": "x.py"}},
                {"tool": "read_file", "params": {"path": "x.py"}},
                {"tool": "read_file", "params": {"path": "x.py"}},
                {"tool": "read_file", "params": {"path": "x.py"}},
            ]
        }
        triggered = runtime._post_flight_check("test", trace, [])
        loop_guardrails = [t for t in triggered if "loop" in t["guardrail"].lower()]
        assert len(loop_guardrails) >= 1

    def test_run_with_mitigation_clean(self):
        runtime = FailureDrivenRuntime()
        trace = {
            "tool_calls": [
                {"tool": "read_file", "params": {"path": "foo.py"}},
                {"tool": "edit_file", "params": {"path": "foo.py"}},
            ],
            "output": "import os\nx = 1",
            "total_time_ms": 100,
            "context_tokens": 100,
            "model_max_tokens": 4096,
            "test_results": {"failed": 0},
            "existing_modules": ["os"],
        }
        result = runtime.run_with_mitigation("test task", trace)
        assert "guardrails_triggered" in result
        assert "mitigations_applied" in result
        assert isinstance(result["failures_detected"], list)

    def test_run_with_hallucination(self):
        runtime = FailureDrivenRuntime()
        trace = {
            "tool_calls": [],
            "output": "import nonexistent_thing\n",
            "existing_modules": ["os", "sys"],
            "total_time_ms": 100,
            "context_tokens": 100,
            "model_max_tokens": 4096,
            "test_results": {"failed": 0},
        }
        result = runtime.run_with_mitigation("test task", trace)
        hall_failures = [
            f for f in result["failures_detected"]
            if f["category"] == "hallucinated_api"
        ]
        assert len(hall_failures) >= 1

    def test_guardrails_start_enabled(self):
        runtime = FailureDrivenRuntime()
        for g in runtime.guardrails.values():
            assert g.enabled is True

    def test_benchmark_scenarios_returned(self):
        runtime = FailureDrivenRuntime()
        scenarios = runtime.get_benchmark_scenarios()
        assert len(scenarios) == 12
        for s in scenarios:
            assert s.name.startswith("bench_")
            assert s.failure_category in [c.value for c in LocalCodingFailureCategory]

    def test_measurements_recorded(self):
        runtime = FailureDrivenRuntime()
        trace = {
            "tool_calls": [{"tool": "read_file", "params": {"path": "x.py"}}],
            "output": "ok",
            "context_tokens": 4000,
            "model_max_tokens": 4096,
        }
        hooks = runtime._record_measurements(trace, [], 5000)
        assert "read_edit_ratio" in hooks
        assert "hallucination_rate" in hooks
        assert "context_utilization" in hooks

    def test_report_generates(self):
        runtime = FailureDrivenRuntime()
        report = runtime.report()
        assert "FAILURE-DRIVEN RUNTIME REPORT" in report
        assert "MITIGATIONS" in report
        assert "GUARDRAIL" in report
        assert "BENCHMARK" in report


class TestGuardrail:
    def test_guardrail_creation(self):
        g = Guardrail(
            name="TestGuard",
            description="Test description",
            failure_category="test",
        )
        assert g.name == "TestGuard"
        assert g.enabled is True
        assert g.trigger_count == 0

    def test_guardrail_to_dict(self):
        g = Guardrail(
            name="TestGuard",
            description="Test",
            failure_category="test",
            trigger_count=3,
        )
        d = g.to_dict()
        assert d["trigger_count"] == 3
