"""Tests for Week 73 — Local Coding Agent Error Taxonomy."""

import pytest
from src.lyme_model.failures.taxonomy import (
    LocalCodingFailureCategory,
    LOCAL_CODING_TAXONOMY,
    LocalCodingFailureRecord,
    LocalCodingFailureAnalysis,
)
from src.lyme_model.failures.detector import (
    LocalCodingFailureDetector,
    DETECTOR_RULES,
)
from src.lyme_model.failures.metrics import compute_failure_metrics
from src.lyme_model.failures.report import generate_cli_report


class TestTaxonomy:
    def test_has_12_categories(self):
        assert len(list(LocalCodingFailureCategory)) == 12

    def test_all_categories_have_taxonomy_entry(self):
        for cat in LocalCodingFailureCategory:
            assert cat in LOCAL_CODING_TAXONOMY
            entry = LOCAL_CODING_TAXONOMY[cat]
            assert "description" in entry
            assert "severity" in entry
            assert "mitigation" in entry
            assert "detectable_by" in entry

    def test_critical_severity_exists(self):
        critical = [
            cat for cat, info in LOCAL_CODING_TAXONOMY.items()
            if info["severity"] == "critical"
        ]
        assert len(critical) >= 1

    def test_all_severities_valid(self):
        valid = {"low", "medium", "high", "critical"}
        for info in LOCAL_CODING_TAXONOMY.values():
            assert info["severity"] in valid


class TestRecords:
    def test_record_creation(self):
        record = LocalCodingFailureRecord(
            failure_id="test_001",
            category=LocalCodingFailureCategory.HALLUCINATED_API,
            description="Referenced nonexistent function",
            severity="critical",
        )
        assert record.category.value == "hallucinated_api"
        assert record.severity == "critical"

    def test_record_to_dict(self):
        record = LocalCodingFailureRecord(
            failure_id="test_002",
            category=LocalCodingFailureCategory.MISSING_CONTEXT,
            description="No context",
            severity="high",
        )
        d = record.to_dict()
        assert d["category"] == "missing_context"
        assert d["failure_id"] == "test_002"

    def test_record_cli_line(self):
        record = LocalCodingFailureRecord(
            failure_id="test_003",
            category=LocalCodingFailureCategory.BAD_PATCH,
            description="Patch failed to apply",
            severity="high",
        )
        line = record.cli_line()
        assert "bad_patch" in line
        assert "HIGH" in line


class TestDetector:
    def test_has_22_rules(self):
        assert len(DETECTOR_RULES) == 22

    def test_all_rules_have_unique_names(self):
        names = [r.name for r in DETECTOR_RULES]
        assert len(names) == len(set(names))

    def test_detect_no_failures_on_clean_trace(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "tool_calls": [],
            "output": "print('hello')",
            "total_time_ms": 100,
            "context_tokens": 100,
            "test_results": {"failed": 0, "total": 5},
        }
        failures = detector.detect(trace)
        assert len(failures) == 0

    def test_detect_hallucinated_api(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "output": "import nonexistent_module\n",
            "existing_modules": ["os", "sys", "json"],
            "tool_calls": [],
        }
        failures = detector.detect(trace)
        hallucinated = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.HALLUCINATED_API
        ]
        assert len(hallucinated) >= 1

    def test_detect_test_still_failing(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "test_results": {"failed": 2, "total": 10},
            "tool_calls": [],
        }
        failures = detector.detect(trace)
        incomplete = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.INCOMPLETE_PATCH
        ]
        assert len(incomplete) >= 1

    def test_detect_excessive_latency(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "total_time_ms": 60000,
            "latency_threshold_ms": 30000,
            "tool_calls": [],
        }
        failures = detector.detect(trace)
        latency = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.EXCESSIVE_LATENCY
        ]
        assert len(latency) >= 1

    def test_detect_context_overflow(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "context_tokens": 8000,
            "model_max_tokens": 4096,
            "tool_calls": [],
        }
        failures = detector.detect(trace)
        overflow = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.CONTEXT_OVERFLOW
        ]
        assert len(overflow) >= 1

    def test_detect_tool_loop(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "tool_calls": [
                {"tool": "read_file", "params": {"path": "foo.py"}},
                {"tool": "read_file", "params": {"path": "foo.py"}},
                {"tool": "read_file", "params": {"path": "foo.py"}},
                {"tool": "read_file", "params": {"path": "foo.py"}},
            ],
        }
        failures = detector.detect(trace)
        loop = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.TOOL_LOOP_FAILURE
        ]
        assert len(loop) >= 1

    def test_detect_wrong_file(self):
        detector = LocalCodingFailureDetector()
        trace = {
            "task": "Fix the bug in auth/login.py",
            "tool_calls": [
                {"tool": "edit_file", "params": {"path": "utils/helpers.py"}},
            ],
        }
        failures = detector.detect(trace)
        wrong_file = [
            f for f in failures
            if f.category == LocalCodingFailureCategory.WRONG_FILE_SELECTED
        ]
        assert len(wrong_file) >= 1


class TestMetrics:
    def test_empty_metrics(self):
        metrics = compute_failure_metrics([], total_runs=10)
        assert metrics.total_failures == 0
        assert metrics.failure_rate == 0.0

    def test_metrics_with_failures(self):
        records = [
            LocalCodingFailureRecord(
                failure_id="m1", category=LocalCodingFailureCategory.BAD_PATCH,
                description="bad", severity="high",
            ),
            LocalCodingFailureRecord(
                failure_id="m2", category=LocalCodingFailureCategory.BAD_PATCH,
                description="bad", severity="high",
            ),
            LocalCodingFailureRecord(
                failure_id="m3", category=LocalCodingFailureCategory.TOOL_LOOP_FAILURE,
                description="loop", severity="high", mitigated_by="loop_detector",
            ),
        ]
        metrics = compute_failure_metrics(records, total_runs=10)
        assert metrics.total_failures == 3
        assert metrics.failure_rate == 0.3
        assert metrics.by_category_rate.get("bad_patch", 0) == 0.2
        assert metrics.mitigation_success_rate == pytest.approx(1 / 3)


class TestAnalysis:
    def test_analyze_empty(self):
        detector = LocalCodingFailureDetector()
        analysis = detector.analyze([])
        assert analysis.total_count == 0
        assert "No local coding agent failures detected" in analysis.summary

    def test_analyze_with_failures(self):
        detector = LocalCodingFailureDetector()
        records = [
            LocalCodingFailureRecord(
                failure_id="a1", category=LocalCodingFailureCategory.HALLUCINATED_API,
                description="hallucinated", severity="critical",
            ),
        ]
        analysis = detector.analyze(records)
        assert analysis.total_count == 1
        assert "Hallucinated Api" in analysis.by_category


class TestReport:
    def test_report_generation(self):
        report = generate_cli_report()
        assert "LOCAL CODING AGENT ERROR TAXONOMY REPORT" in report
        assert "12 categories" in report
        assert "DETECTOR RULES" in report

    def test_report_with_analysis(self):
        analysis = LocalCodingFailureAnalysis(
            total_count=2,
            by_category={"Bad Patch": 2},
            by_severity={"high": 2},
            summary="2 failures found.",
        )
        report = generate_cli_report(analysis=analysis)
        assert "2 failures" in report

    def test_report_with_metrics(self):
        from src.lyme_model.failures.metrics import FailureMetrics
        metrics = FailureMetrics(total_runs=10, total_failures=3, failure_rate=0.3)
        report = generate_cli_report(metrics=metrics)
        assert "30.0%" in report or "30%" in report
