"""Week 99 — Patch Planning Fine-Tuning tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.patch_plan_training import (
    PatchPlanExample,
    PatchPlanResult,
    PatchPlanExperimentResult,
    PatchPlanDataGenerator,
    DirectPatchVariant,
    PromptedPlanVariant,
    TrainedPlanVariant,
    PlanCriticVariant,
    PatchPlanExperimentRunner,
)


class TestPatchPlanExample:
    def test_defaults(self):
        ex = PatchPlanExample()
        assert ex.example_id == ""
        assert ex.correct_affected_files == []

    def test_to_dict(self):
        ex = PatchPlanExample(
            example_id="test-001",
            task="Fix the bug",
            repo_summary="calc-app",
            relevant_files=["calculator.py"],
            error_output="ZeroDivisionError",
            correct_affected_files=["calculator.py"],
            correct_intended_patch="if b == 0: raise ValueError",
            correct_risk_assessment="low",
            correct_verification_command="pytest",
            correct_rollback_plan="git checkout",
        )
        d = ex.to_dict()
        assert d["example_id"] == "test-001"
        assert "calculator.py" in d["correct_affected_files"]
        assert d["correct_risk_assessment"] == "low"


class TestPatchPlanResult:
    def test_defaults(self):
        r = PatchPlanResult()
        assert r.variant_name == ""

    def test_to_dict(self):
        r = PatchPlanResult(
            variant_name="Test", accuracy=0.85, affected_files_correct=0.9,
            patch_correctness=0.8, risk_assessment_quality=0.7,
            verification_completeness=0.9, total=10, avg_latency_ms=100,
        )
        d = r.to_dict()
        assert d["variant_name"] == "Test"
        assert d["accuracy"] == 0.85


class TestPatchPlanExperimentResult:
    def test_defaults(self):
        r = PatchPlanExperimentResult()
        assert r.comparisons == []

    def test_to_markdown(self):
        r = PatchPlanExperimentResult(
            experiment_id="test-001",
            data_sources={"total": 20, "train": 14},
            comparisons=[
                {"variant": "DirectPatch", "accuracy": 0.75, "is_winner": False,
                 "affected_files_correct": 0.8, "patch_correctness": 0.7,
                 "risk_assessment_quality": 0.5, "verification_completeness": 0.5,
                 "avg_latency_ms": 50, "total": 20},
                {"variant": "PlanCritic", "accuracy": 0.90, "is_winner": True,
                 "affected_files_correct": 0.9, "patch_correctness": 0.85,
                 "risk_assessment_quality": 0.9, "verification_completeness": 0.95,
                 "avg_latency_ms": 120, "total": 20},
            ],
            winner="PlanCritic",
            conclusions=["PlanCritic wins"],
        )
        md = r.to_markdown()
        assert "Patch Planning Fine-Tuning Experiment" in md
        assert "PlanCritic" in md


class TestPatchPlanDataGenerator:
    def test_generates_examples(self):
        gen = PatchPlanDataGenerator()
        examples = gen.generate_all()
        assert len(examples) >= 4  # synthetic examples

    def test_synthetic_includes_all_fields(self):
        gen = PatchPlanDataGenerator()
        examples = gen.generate_all()
        synthetic = [ex for ex in examples if "syn" in ex.example_id]
        assert len(synthetic) >= 4
        for ex in synthetic:
            assert ex.task
            assert ex.correct_intended_patch
            assert ex.correct_verification_command


class TestDirectPatchVariant:
    def test_plan_returns_result(self):
        variant = DirectPatchVariant()
        result = variant.plan("Fix division by zero", ["calculator.py"], "ZeroDivisionError")
        assert "affected_files" in result
        assert "patch" in result

    def test_evaluate_returns_metrics(self):
        variant = DirectPatchVariant()
        examples = [
            PatchPlanExample(task="Fix division by zero",
                           correct_affected_files=["calculator.py"],
                           correct_intended_patch="if b == 0: raise ValueError"),
        ]
        result = variant.evaluate(examples)
        assert isinstance(result, PatchPlanResult)
        assert result.total == 1


class TestPromptedPlanVariant:
    def test_plan_includes_all_fields(self):
        variant = PromptedPlanVariant()
        result = variant.plan("Fix the null values", ["transform.py"], "dropna()", "data-pipeline")
        assert "affected_files" in result
        assert "intended_patch" in result
        assert "risk_assessment" in result
        assert "verification_command" in result
        assert "rollback_plan" in result

    def test_evaluate_returns_metrics(self):
        variant = PromptedPlanVariant()
        examples = [PatchPlanExample(task="Fix division", correct_affected_files=["calc.py"],
                                     correct_intended_patch="raise ValueError")]
        r = variant.evaluate(examples)
        assert r.total == 1


class TestTrainedPlanVariant:
    def test_train_and_evaluate(self):
        variant = TrainedPlanVariant()
        examples = [
            PatchPlanExample(task="Fix division", correct_affected_files=["calc.py"],
                           correct_intended_patch="raise ValueError"),
        ]
        variant.train(examples)
        assert variant.trained is True
        result = variant.evaluate(examples)
        assert result.total == 1


class TestPlanCriticVariant:
    def test_plan_and_critique(self):
        variant = PlanCriticVariant()
        result = variant.plan_and_critique("Fix division by zero", ["calculator.py"], "error")
        assert "critic_verdict" in result
        assert "critic_confidence" in result

    def test_evaluate(self):
        variant = PlanCriticVariant()
        examples = [PatchPlanExample(task="Fix division", correct_affected_files=["calc.py"],
                                     correct_intended_patch="raise ValueError")]
        r = variant.evaluate(examples)
        assert isinstance(r, PatchPlanResult)


class TestPatchPlanExperimentRunner:
    def test_run_creates_experiment(self):
        runner = PatchPlanExperimentRunner()
        result = runner.run()
        assert result.experiment_id.startswith("patch-plan-")
        assert len(result.comparisons) == 4
        assert result.winner != ""

    def test_four_variants(self):
        runner = PatchPlanExperimentRunner()
        result = runner.run()
        variants = [c.get("variant") for c in result.comparisons]
        assert "DirectPatch" in variants
        assert "PromptedPlan" in variants
        assert "TrainedPlan" in variants
        assert "PlanCritic" in variants

    def test_save_result(self, tmp_path):
        runner = PatchPlanExperimentRunner()
        result = runner.run()
        json_path, md_path = runner.save_result(result, str(tmp_path / "exp"))
        assert Path(json_path).exists()
        assert Path(md_path).exists()

    def test_conclusions_non_empty(self):
        runner = PatchPlanExperimentRunner()
        result = runner.run()
        assert len(result.conclusions) >= 4
