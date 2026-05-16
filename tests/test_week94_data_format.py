"""Week 94 — Lyme Model Canonical Data Format tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.data_format import (
    RepoState, RelevantFile, ToolCall, PatchPlan, Patch,
    VerificationResult, FailureRecovery,
    LymeTrainingExample, SFTExample, ToolUseExample,
    PatchCriticExample, RetrievalRankingExample, VerifierExample,
    PreferenceExample, LymeDataset, LymeDataFormat,
)


class TestCoreDataTypes:
    def test_repo_state_defaults(self):
        r = RepoState()
        assert r.repo_name == ""
        assert r.language == ""
        d = r.to_dict()
        assert d["repo_name"] == ""

    def test_repo_state_full(self):
        r = RepoState(repo_name="test-repo", language="python", file_count=100,
                      total_lines=5000, test_count=50, test_framework="pytest",
                      architecture_summary="monolith", conventions=["pep8"],
                      git_head="abc123")
        d = r.to_dict()
        assert d["repo_name"] == "test-repo"
        assert d["language"] == "python"
        assert d["file_count"] == 100

    def test_tool_call_to_dict(self):
        tc = ToolCall(sequence=0, tool_name="search", input_args={"query": "func"},
                      output_summary="found 3 results", observation="looks good",
                      latency_ms=150.0, success=True)
        d = tc.to_dict()
        assert d["sequence"] == 0
        assert d["tool_name"] == "search"
        assert d["success"] is True
        assert d["latency_ms"] == 150.0

    def test_patch_plan_to_dict(self):
        pp = PatchPlan(plan="Fix the bug", affected_files=["src/main.py"],
                       intended_change="change <= to <", risk_assessment="low",
                       verification_command="pytest", rollback_plan="git checkout",
                       confidence=0.8)
        d = pp.to_dict()
        assert "Fix the bug" in d["plan"]
        assert d["confidence"] == 0.8

    def test_patch_to_dict(self):
        p = Patch(file_path="src/main.py", old_content="x = 1", new_content="x = 2",
                  diff="@@ -1 +1 @@\n-x = 1\n+x = 2", lines_added=1, lines_removed=1,
                  hash="abc123")
        d = p.to_dict()
        assert d["file_path"] == "src/main.py"
        assert d["lines_added"] == 1
        assert d["hash"] == "abc123"

    def test_verification_result_to_dict(self):
        v = VerificationResult(verification_type="test", command="pytest", passed=True,
                               tests_passed=10, tests_failed=0, total_tests=10,
                               errors=[], coverage_percent=85.0,
                               findings=["All tests pass"])
        d = v.to_dict()
        assert d["passed"] is True
        assert d["coverage_percent"] == 85.0

    def test_failure_recovery_to_dict(self):
        fr = FailureRecovery(attempt_number=1, max_attempts=3,
                            failure_reason="test failed", failure_category="regression",
                            strategy_change="add compatibility",
                            retry_strategy="preserve_old", lessons_learned="test first",
                            confidence_before=0.8, confidence_after=0.5)
        d = fr.to_dict()
        assert d["attempt_number"] == 1
        assert d["confidence_before"] == 0.8


class TestLymeTrainingExample:
    def test_defaults(self):
        ex = LymeTrainingExample()
        assert ex.example_id == ""
        assert ex.task_instruction == ""
        assert ex.tool_calls == []
        assert ex.patches == []

    def test_to_dict_empty(self):
        ex = LymeTrainingExample()
        d = ex.to_dict()
        assert d["source"] == "unknown"
        assert d["is_correct"] is False

    def test_to_dict_full(self):
        ex = LymeTrainingExample(
            example_id="test-001",
            source_trace_id="trace-001",
            task_instruction="Fix the bug",
            task_type="apply_patch",
            difficulty="easy",
            repo_state=RepoState(repo_name="test", language="python"),
            relevant_files=[RelevantFile(file_path="src/main.py", file_role="source")],
            tool_calls=[ToolCall(sequence=0, tool_name="search", success=True)],
            patches=[Patch(file_path="src/main.py", diff="@@ -1 +1 @@")],
            verification=VerificationResult(passed=True),
            failure_recoveries=[FailureRecovery(attempt_number=1)],
            final_answer="Done",
            correct_answer="Fix the bug by changing x to y",
            is_correct=True,
            quality_score=1.0,
            intermediate_observations=["Bug is in the loop"],
        )
        d = ex.to_dict()
        assert d["example_id"] == "test-001"
        assert d["source_trace_id"] == "trace-001"
        assert d["source"] == "lyme_audit"
        assert d["is_correct"] is True
        assert d["quality_score"] == 1.0

    def test_to_dict_no_patches(self):
        ex = LymeTrainingExample(example_id="test-002", task_instruction="Just ask")
        d = ex.to_dict()
        assert "patches" not in d
        assert "verification" not in d


class TestModalityViews:
    def test_sft_from_lyme_example(self):
        ex = LymeTrainingExample(
            example_id="test-001",
            task_instruction="Fix the bug",
            repo_state=RepoState(repo_name="test", language="python"),
            relevant_files=[RelevantFile(file_path="src/main.py", file_role="source")],
            correct_answer="Change <= to <",
        )
        sft = SFTExample.from_lyme_example(ex)
        assert sft.instruction == "Fix the bug"
        assert "test" in sft.input_context
        assert sft.output == "Change <= to <"
        assert sft.source_example_id == "test-001"

    def test_sft_with_patches(self):
        ex = LymeTrainingExample(
            example_id="test-002",
            task_instruction="Fix the bug",
            patches=[Patch(file_path="src/main.py", diff="@@ -1 +1 @@\n-change\n+change")],
        )
        sft = SFTExample.from_lyme_example(ex)
        assert "diff" not in sft.output
        assert "src/main.py" in sft.output

    def test_tool_use_from_lyme_example(self):
        ex = LymeTrainingExample(
            example_id="test-003",
            task_instruction="Fix the bug",
            tool_calls=[
                ToolCall(sequence=0, tool_name="search", input_args={"q": "func"}),
                ToolCall(sequence=1, tool_name="read", input_args={"file": "main.py"}),
            ],
        )
        result = ToolUseExample.from_lyme_example(ex)
        assert result is not None
        assert result.correct_action == "read"

    def test_tool_use_no_tool_calls(self):
        ex = LymeTrainingExample(example_id="test-004")
        result = ToolUseExample.from_lyme_example(ex)
        assert result is None

    def test_patch_critic_from_lyme_example(self):
        ex = LymeTrainingExample(
            example_id="test-005",
            task_instruction="Fix the bug",
            patches=[Patch(file_path="src/main.py", diff="@@ -1 +1 @@")],
            repo_state=RepoState(language="python"),
            is_correct=True,
        )
        critic = PatchCriticExample.from_lyme_example(ex)
        assert critic is not None
        assert critic.label_safe is True
        assert critic.label_issues == []

    def test_patch_critic_no_patches(self):
        ex = LymeTrainingExample(example_id="test-006")
        result = PatchCriticExample.from_lyme_example(ex)
        assert result is None

    def test_retrieval_from_lyme_example(self):
        ex = LymeTrainingExample(
            example_id="test-007",
            task_instruction="Find where auth is handled",
            relevant_files=[
                RelevantFile(file_path="src/auth.py", file_role="source"),
                RelevantFile(file_path="src/main.py", file_role="source"),
            ],
        )
        ret = RetrievalRankingExample.from_lyme_example(ex)
        assert ret is not None
        assert "src/auth.py" in ret.relevant_docs
        assert ret.query == "Find where auth is handled"

    def test_retrieval_no_files(self):
        ex = LymeTrainingExample(example_id="test-008")
        result = RetrievalRankingExample.from_lyme_example(ex)
        assert result is None

    def test_verifier_from_lyme_example(self):
        ex = LymeTrainingExample(
            example_id="test-009",
            task_instruction="Fix the bug",
            patches=[Patch(file_path="src/main.py", diff="@@ -1 +1 @@")],
            verification=VerificationResult(passed=True, tests_passed=5, tests_failed=0),
            final_answer="Done",
        )
        ver = VerifierExample.from_lyme_example(ex)
        assert ver is not None
        assert ver.label_correct is True

    def test_verifier_no_verification(self):
        ex = LymeTrainingExample(example_id="test-010")
        result = VerifierExample.from_lyme_example(ex)
        assert result is None

    def test_preference_to_dict(self):
        pref = PreferenceExample(
            task="Fix bug",
            chosen_output="Change <= to <",
            rejected_output="Change >= to >",
            preference_reason="First fix is correct",
        )
        d = pref.to_dict()
        assert d["task"] == "Fix bug"
        assert "correct" in d["preference_reason"]


class TestLymeDataset:
    def test_empty_dataset(self):
        ds = LymeDataset()
        assert ds.version == "0.1"
        assert len(ds.examples) == 0
        d = ds.to_dict()
        assert d["sft_count"] == 0

    def test_dataset_with_examples(self):
        ds = LymeDataset(
            version="0.1",
            examples=[
                LymeTrainingExample(example_id="1", task_instruction="Fix bug",
                                  task_type="apply_patch", difficulty="easy"),
                LymeTrainingExample(example_id="2", task_instruction="Refactor",
                                  task_type="plan_patch", difficulty="hard"),
            ],
        )
        ds.compute_stats()
        assert ds.by_task_type["apply_patch"] == 1
        assert ds.by_task_type["plan_patch"] == 1
        assert ds.by_difficulty["easy"] == 1
        assert ds.by_difficulty["hard"] == 1

    def test_to_dict(self):
        ds = LymeDataset(version="0.1", examples=[], description="test dataset")
        d = ds.to_dict()
        assert d["version"] == "0.1"
        assert d["description"] == "test dataset"

    def test_to_markdown(self):
        ds = LymeDataset(
            version="0.1",
            description="test dataset",
            examples=[
                LymeTrainingExample(example_id="1", task_type="apply_patch", difficulty="easy"),
            ],
            sft_examples=[SFTExample(instruction="Fix", output="Done", source_example_id="1")],
            train_ids=["1"],
        )
        ds.compute_stats()
        md = ds.to_markdown()
        assert "Lyme Model Dataset" in md
        assert "0.1" in md
        assert "SFT" in md
        assert "train" in md.lower()


class TestLymeDataFormat:
    def test_create_example_id(self):
        eid = LymeDataFormat.create_example_id()
        assert eid.startswith("lyme-")
        assert len(eid) > 5

    def test_infer_task_type(self):
        assert LymeDataFormat._infer_task_type("fix bug", "completed") == "apply_patch"
        assert LymeDataFormat._infer_task_type("fix bug", "failed") == "plan_patch"
        assert LymeDataFormat._infer_task_type("refactor payment", "") == "plan_patch"
        assert LymeDataFormat._infer_task_type("fix crash", "") == "explain_failure"
        assert LymeDataFormat._infer_task_type("add feature", "") == "qa"
        assert LymeDataFormat._infer_task_type("", "") == "unknown"

    def test_from_trace_simple(self):
        trace = {
            "header": {
                "trace_id": "test-trace-001",
                "tags": {"task": "fix bug", "difficulty": "easy"},
                "agent": {"name": "test", "model": "m", "framework": "lyme"},
                "system": {"repo_name": "test-repo", "git_head": "abc123"},
            },
            "events": [
                {"id": "1", "type": "model_call", "sequence": 0, "status": "success",
                 "prompt_preview": "Fix it", "completion_preview": "Ok"},
                {"id": "2", "type": "file_read", "sequence": 1, "status": "success",
                 "file_path": "src/main.py", "lines_read": 100},
                {"id": "3", "type": "file_edit", "sequence": 2, "status": "success",
                 "file_path": "src/main.py", "old_text_preview": "x=1",
                 "new_text_preview": "x=2", "lines_added": 1, "lines_removed": 1,
                 "patch_hash": "abc"},
                {"id": "4", "type": "test_run", "sequence": 3, "status": "success",
                 "command": "pytest", "tests_passed": 5, "tests_failed": 0,
                 "total_tests": 5, "failure_messages": []},
                {"id": "5", "type": "verification_step", "sequence": 4, "status": "success",
                 "verification_type": "test", "result": "passed", "findings": ["OK"]},
                {"id": "6", "type": "evidence_claim", "sequence": 5, "status": "success",
                 "claim": "The fix is correct"},
            ],
            "summary": {"status": "completed"},
        }
        ex = LymeDataFormat.from_trace(trace)
        assert ex.source_trace_id == "test-trace-001"
        assert ex.task_instruction == "fix bug"
        assert ex.is_correct is True
        assert len(ex.relevant_files) == 1
        assert len(ex.patches) == 1
        assert ex.verification is not None
        assert ex.verification.passed is True
        assert len(ex.intermediate_observations) >= 1

    def test_from_trace_with_failure(self):
        trace = {
            "header": {"tags": {"task": "fix-crash", "difficulty": "hard"},
                       "agent": {"name": "test", "model": "m", "framework": "lyme"}},
            "events": [
                {"id": "1", "type": "model_call", "sequence": 0, "status": "success"},
                {"id": "2", "type": "failed_attempt", "sequence": 1, "status": "success",
                 "attempt_number": 1, "max_attempts": 3,
                 "failure_reason": "wrong approach",
                 "failure_category": "wrong_root_cause",
                 "strategy_change": "try different", "retry_strategy": "new",
                 "lessons_learned": "read first"},
                {"id": "3", "type": "confidence_change", "sequence": 2, "status": "success",
                 "prior_confidence": 0.8, "post_confidence": 0.4,
                 "change_reason": "failure"},
            ],
            "summary": {"status": "abandoned"},
        }
        ex = LymeDataFormat.from_trace(trace)
        assert ex.is_correct is False
        assert ex.quality_score == 0.3
        assert len(ex.failure_recoveries) == 1
        assert ex.failure_recoveries[0].failure_reason == "wrong approach"
        assert ex.failure_recoveries[0].confidence_before == 0.8
        assert ex.failure_recoveries[0].confidence_after == 0.4

    def test_build_dataset(self):
        examples = [
            LymeTrainingExample(example_id="1", task_instruction="Fix bug",
                              task_type="apply_patch", difficulty="easy",
                              tool_calls=[ToolCall(sequence=0, tool_name="search", success=True)],
                              patches=[Patch(file_path="main.py", diff="diff")],
                              verification=VerificationResult(passed=True)),
            LymeTrainingExample(example_id="2", task_instruction="Refactor",
                              task_type="plan_patch", difficulty="hard",
                              tool_calls=[ToolCall(sequence=0, tool_name="read", success=True)],
                              relevant_files=[RelevantFile(file_path="src/main.py")]),
            LymeTrainingExample(example_id="3", task_instruction="Explain",
                              task_type="qa", difficulty="medium"),
        ]
        dataset = LymeDataFormat.build_dataset(examples, val_split=0.2, test_split=0.2)
        assert len(dataset.examples) == 3
        assert len(dataset.train_ids) + len(dataset.val_ids) + len(dataset.test_ids) == 3

    def test_to_jsonl(self, tmp_path):
        examples = [
            SFTExample(instruction="Fix bug", output="Change x", source_example_id="1"),
            SFTExample(instruction="Refactor", output="Extract class", source_example_id="2"),
        ]
        out = tmp_path / "test.jsonl"
        LymeDataFormat.to_jsonl(examples, str(out))
        assert out.exists()
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["instruction"] == "Fix bug"

    def test_to_json_full_dataset(self, tmp_path):
        ds = LymeDataset(
            examples=[LymeTrainingExample(example_id="1", task_instruction="Fix bug")],
            sft_examples=[SFTExample(instruction="Fix bug", output="Done", source_example_id="1")],
        )
        out = tmp_path / "dataset.json"
        LymeDataFormat.to_json(ds, str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["version"] == "0.1"
        assert len(data["examples"]) == 1
        assert len(data["sft_examples"]) == 1
