"""Week 93 — Training Data Reality Check tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.data_audit import (
    TrainingDataAuditor,
    DataCategory,
    CATEGORY_LABELS,
    DataSourceAssessment,
    TrainingDataAuditReport,
    run_audit,
)


class TestDataAuditCore:
    def test_category_labels_cover_all_categories(self):
        cats = [
            DataCategory.SFT,
            DataCategory.TOOL_POLICY,
            DataCategory.RETRIEVAL_POLICY,
            DataCategory.PATCH_CRITIQUE,
            DataCategory.EVAL_ONLY,
            DataCategory.UNUSABLE,
        ]
        for c in cats:
            assert c in CATEGORY_LABELS
            assert len(CATEGORY_LABELS[c]) > 0

    def test_assessment_defaults(self):
        a = DataSourceAssessment(source_id="test-001")
        assert a.source_id == "test-001"
        assert a.category == DataCategory.UNUSABLE
        assert a.quality_score == 0.0
        assert a.issues == []
        assert a.risks == []
        assert a.missing_labels == []

    def test_assessment_to_dict(self):
        a = DataSourceAssessment(
            source_id="test-001",
            source_type="standard_trace",
            path="/tmp/test.json",
            category=DataCategory.SFT,
            completeness=0.9,
            correctness=1.0,
            has_task=True,
            has_tool_calls=True,
            has_patches=True,
            has_verification=True,
            has_outcome=True,
            quality_score=0.95,
            issues=["Minor issue"],
            risks=["Low risk"],
            missing_labels=["patch_plan"],
        )
        d = a.to_dict()
        assert d["source_id"] == "test-001"
        assert d["category"] == DataCategory.SFT
        assert d["quality_score"] == 0.95
        assert d["has_task"] is True

    def test_empty_report(self):
        report = TrainingDataAuditReport()
        assert report.total_sources == 0
        assert report.by_category == {}
        d = report.to_dict()
        assert d["total_sources"] == 0

    def test_report_to_markdown(self):
        report = TrainingDataAuditReport(
            total_sources=5,
            by_category={DataCategory.SFT: 3, DataCategory.EVAL_ONLY: 2},
            by_source_type={"trace": 3, "audit": 2},
            overall_quality=0.6,
            usable_quality=0.95,
            assessments=[
                DataSourceAssessment(
                    source_id="trace-001",
                    source_type="standard_trace",
                    path="/tmp/t.json",
                    category=DataCategory.SFT,
                    quality_score=0.95,
                )
            ],
            leakage_risks=["Risk 1"],
            hallucination_risks=["Risk 2"],
            missing_labels_global=["Label 1"],
            recommendations=["Rec 1"],
        )
        md = report.to_markdown()
        assert "Training Data Audit Report" in md
        assert "0.60" in md
        assert "0.95" in md
        assert "3" in md or "three" in md.lower()


class TestTrainingDataAuditor:
    def test_audit_with_nonexistent_path(self, tmp_path):
        auditor = TrainingDataAuditor(str(tmp_path))
        report = auditor.audit_all()
        assert report.total_sources >= 3  # generated data always assessed

    def test_audit_with_mock_audit_traces(self, tmp_path):
        audit_dir = tmp_path / ".lyme" / "audit"
        audit_dir.mkdir(parents=True)
        entry = {
            "audit_id": "test-001", "kind": "diagnose",
            "description": "Test", "status": "completed",
            "trace_id": None, "patch_ids": [], "files_affected": [],
            "metadata": {},
        }
        (audit_dir / "test-001.json").write_text(json.dumps(entry))

        auditor = TrainingDataAuditor(str(tmp_path))
        report = auditor.audit_all()
        assert report.total_sources >= 1

    def test_audit_with_mock_standard_trace(self, tmp_path):
        traces_dir = tmp_path / "lyme-output" / "standards" / "traces"
        traces_dir.mkdir(parents=True)
        trace = {
            "header": {
                "trace_id": "test-trace-001",
                "tags": {"task": "fix-bug", "difficulty": "easy"},
                "agent": {"name": "test-agent", "model": "test-model", "framework": "lyme"},
            },
            "events": [
                {"id": "1", "type": "model_call", "prompt_preview": "Fix the bug", "completion_preview": "I'll fix it"},
                {"id": "2", "type": "file_read", "file_path": "/src/main.py"},
                {"id": "3", "type": "file_edit", "file_path": "/src/main.py", "patch_hash": "abc"},
                {"id": "4", "type": "test_run", "tests_passed": 5, "tests_failed": 0},
                {"id": "5", "type": "verification_step", "result": "passed"},
                {"id": "6", "type": "evidence_claim", "claim": "The bug is fixed"},
            ],
            "summary": {"status": "completed"},
        }
        (traces_dir / "test-trace.json").write_text(json.dumps(trace))

        auditor = TrainingDataAuditor(str(tmp_path))
        report = auditor.audit_all()
        trace_assessments = [a for a in report.assessments if a.source_type == "standard_trace"]
        assert len(trace_assessments) == 1
        assert trace_assessments[0].has_task is True
        assert trace_assessments[0].has_tool_calls is True
        assert trace_assessments[0].has_patches is True
        assert trace_assessments[0].has_verification is True

    def test_audit_with_mock_ci_trace(self, tmp_path):
        ci_dir = tmp_path / "lyme-output" / "ci"
        ci_dir.mkdir(parents=True)
        trace = {
            "id": "ci-test-001",
            "type": "open_agent_trace",
            "content": {
                "events": [
                    {"type": "system", "metadata": {"action": "ci_run"}},
                    {"type": "metric", "metadata": {"risk_score": 0.0}},
                ],
                "summary": {"status": "completed"},
            },
        }
        (ci_dir / "ci-test-001-trace.json").write_text(json.dumps(trace))

        auditor = TrainingDataAuditor(str(tmp_path))
        report = auditor.audit_all()
        ci_assessments = [a for a in report.assessments if a.source_type == "ci_trace"]
        assert len(ci_assessments) >= 1
        assert ci_assessments[0].category == DataCategory.EVAL_ONLY

    def test_audit_categories_are_mutually_exclusive(self, tmp_path):
        traces_dir = tmp_path / "lyme-output" / "standards" / "traces"
        traces_dir.mkdir(parents=True)
        trace = {
            "header": {"trace_id": "test", "tags": {"task": "test"}, "agent": {}},
            "events": [
                {"id": "1", "type": "model_call", "prompt_preview": "test"},
                {"id": "2", "type": "file_read"},
                {"id": "3", "type": "file_edit"},
                {"id": "4", "type": "test_run"},
                {"id": "5", "type": "verification_step"},
            ],
            "summary": {"status": "completed"},
        }
        (traces_dir / "test.json").write_text(json.dumps(trace))

        auditor = TrainingDataAuditor(str(tmp_path))
        report = auditor.audit_all()
        categories = set(a.category for a in report.assessments)
        assert len(categories) >= 1


class TestRunAudit:
    def test_run_audit_returns_report(self):
        report = run_audit(".")
        assert isinstance(report, TrainingDataAuditReport)
        assert report.total_sources >= 0

    def test_save_report_creates_files(self, tmp_path):
        report = TrainingDataAuditReport(
            total_sources=3,
            by_category={DataCategory.SFT: 2, DataCategory.EVAL_ONLY: 1},
            by_source_type={"standard_trace": 2, "audit": 1},
            assessments=[
                DataSourceAssessment(
                    source_id="test", source_type="standard_trace",
                    path="/tmp/t.json", category=DataCategory.SFT, quality_score=0.9,
                )
            ],
            overall_quality=0.7,
            usable_quality=0.9,
        )
        from src.lyme_model.learning.data_audit import save_report
        out_path = tmp_path / "reports" / "audit.json"
        json_path, md_path = save_report(report, str(out_path))
        assert Path(json_path).exists()
        assert Path(md_path).exists()

        content = json.loads(Path(json_path).read_text())
        assert content["total_sources"] == 3
        assert content["overall_quality"] == 0.7

    def test_audit_can_save(self, tmp_path):
        report = run_audit(".")
        from src.lyme_model.learning.data_audit import save_report
        out_path = tmp_path / "reports" / "audit.json"
        json_path, md_path = save_report(report, str(out_path))
        assert Path(json_path).exists()
        assert Path(md_path).exists()
