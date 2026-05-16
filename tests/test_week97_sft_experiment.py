"""Week 97 — SFT Feasibility Run tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.sft_experiment import (
    SFTExperimentConfig,
    ModelComparison,
    SFTExperimentResult,
    SFTTrainingHarness,
    BaseModelEvaluator,
    PromptedModelEvaluator,
    LymeRuntimeModelEvaluator,
    FineTunedModelEvaluator,
    SFTExperimentRunner,
    general_coding_probes,
)


class TestSFTExperimentConfig:
    def test_default_config(self):
        c = SFTExperimentConfig()
        assert c.model_name == "Qwen/Qwen2.5-Coder-1.5B"
        assert c.task_filter == "plan_patch"
        assert c.lora_r == 8

    def test_to_dict(self):
        c = SFTExperimentConfig()
        d = c.to_dict()
        assert d["model_name"] == "Qwen/Qwen2.5-Coder-1.5B"
        assert d["lora_r"] == 8
        assert d["num_epochs"] == 3

    def test_custom_config(self):
        c = SFTExperimentConfig(model_name="test-model", lora_r=16, num_epochs=5)
        assert c.model_name == "test-model"
        assert c.lora_r == 16
        assert c.num_epochs == 5


class TestModelComparison:
    def test_defaults(self):
        mc = ModelComparison()
        assert mc.variant_name == ""

    def test_to_dict(self):
        mc = ModelComparison(
            variant_name="test", quality_score=0.85, exact_match_rate=0.8,
            avg_latency_ms=500.0, peak_memory_mb=3000.0,
            general_coding_score=0.75, overfitting_gap=0.05,
        )
        d = mc.to_dict()
        assert d["variant_name"] == "test"
        assert d["quality_score"] == 0.85
        assert d["avg_latency_ms"] == 500.0


class TestSFTExperimentResult:
    def test_defaults(self):
        r = SFTExperimentResult()
        assert r.comparisons == []

    def test_to_dict(self):
        r = SFTExperimentResult(
            experiment_id="test-001",
            config=SFTExperimentConfig(),
            comparisons=[ModelComparison(variant_name="base", quality_score=0.5)],
            winner="base",
        )
        d = r.to_dict()
        assert d["experiment_id"] == "test-001"
        assert d["winner"] == "base"

    def test_to_markdown(self):
        r = SFTExperimentResult(
            experiment_id="test-001",
            config=SFTExperimentConfig(),
            comparisons=[
                ModelComparison(variant_name="base", quality_score=0.5, exact_match_rate=0.5,
                               avg_latency_ms=100, peak_memory_mb=1000, general_coding_score=0.8,
                               overfitting_gap=0.0),
                ModelComparison(variant_name="ft", quality_score=0.8, exact_match_rate=0.8,
                               avg_latency_ms=200, peak_memory_mb=2000, general_coding_score=0.79,
                               overfitting_gap=0.02),
            ],
            winner="ft",
            conclusions=["Fine-tuning helps"],
        )
        md = r.to_markdown()
        assert "SFT Feasibility Experiment" in md
        assert "base" in md
        assert "ft" in md
        assert "Fine-tuning helps" in md


class TestSFTTrainingHarness:
    def test_dependency_check(self):
        harness = SFTTrainingHarness(SFTExperimentConfig())
        deps = harness._check_dependencies()
        assert isinstance(deps, dict)
        for dep in ["torch", "transformers", "peft", "datasets", "bitsandbytes"]:
            assert dep in deps

    def test_is_available_returns_false(self):
        harness = SFTTrainingHarness(SFTExperimentConfig())
        assert harness.is_available() is False  # deps not installed

    def test_train_simulated(self):
        harness = SFTTrainingHarness(SFTExperimentConfig())
        result = harness.train(
            [{"instruction": "Fix bug", "output": "Change x"}],
            [{"instruction": "Fix bug", "output": "Change x"}],
        )
        assert result["status"] == "simulated"
        assert result["train_examples"] == 1
        assert result["val_examples"] == 1

    def test_estimate_memory(self):
        harness = SFTTrainingHarness(SFTExperimentConfig())
        estimate = harness.estimate_memory()
        assert "estimated_vram_gb" in estimate
        assert "model_params_b" in estimate
        assert estimate["model_params_b"] == 1.5

    def test_estimate_memory_qlora(self):
        config = SFTExperimentConfig(use_qlora=True)
        harness = SFTTrainingHarness(config)
        estimate = harness.estimate_memory()
        assert estimate["estimated_vram_gb"] > 0

    def test_get_training_guide(self):
        guide = SFTExperimentRunner.get_training_guide()
        assert "SFT Training Quick Start" in guide


class TestEvaluators:
    def test_base_model_evaluator(self):
        eval = BaseModelEvaluator("test-model")
        results = eval.evaluate([
            {"task_instruction": "Fix division by zero", "correct_answer": "Add zero check before division"},
        ])
        assert results["total"] == 1
        assert results["status"] == "simulated"

    def test_prompted_model_evaluator(self):
        eval = PromptedModelEvaluator("test-model", few_shot_examples=[
            {"task_instruction": "Example task", "correct_answer": "Example answer"},
        ])
        results = eval.evaluate([
            {"task_instruction": "Fix division by zero", "correct_answer": "Add zero check before division"},
        ])
        assert results["total"] == 1

    def test_lyme_runtime_evaluator(self):
        eval = LymeRuntimeModelEvaluator("test-model")
        results = eval.evaluate([
            {
                "task_instruction": "Fix division by zero",
                "correct_answer": "Add zero check before division",
                "repo_state": {"repo_name": "calc-app"},
                "relevant_files": [{"file_path": "calculator.py"}],
            },
        ])
        assert results["total"] == 1

    def test_fine_tuned_evaluator(self):
        eval = FineTunedModelEvaluator("/tmp/fake-model")
        results = eval.evaluate([
            {"task_instruction": "Fix division by zero", "correct_answer": "Add zero check before division: if b == 0: raise ValueError('Cannot divide by zero')"},
        ])
        assert results["total"] == 1


class TestGeneralCodingProbes:
    def test_probes_exist(self):
        probes = general_coding_probes()
        assert len(probes) == 5
        for p in probes:
            assert "question" in p
            assert "answer" in p

    def test_probes_correct(self):
        probes = general_coding_probes()
        answers = {p["question"]: p["answer"] for p in probes}
        assert answers["How do you open a file in Python?"] == "open('file.txt', 'r')"


class TestSFTExperimentRunner:
    def test_runner_initializes(self):
        runner = SFTExperimentRunner()
        assert runner.config.task_filter == "plan_patch"
        assert len(runner.probes) == 5

    def test_load_dataset_no_dataset(self, tmp_path):
        config = SFTExperimentConfig(dataset_path=str(tmp_path / "nonexistent"))
        runner = SFTExperimentRunner(config)
        data = runner.load_dataset()
        # Should handle missing dataset gracefully
        assert isinstance(data, dict)

    def test_run_simulated(self, tmp_path):
        config = SFTExperimentConfig(
            output_dir=str(tmp_path / "experiment"),
            dataset_path=str(tmp_path / "nonexistent"),
            task_filter="plan_patch",
        )
        runner = SFTExperimentRunner(config)
        result = runner.run()
        assert len(result.comparisons) == 4
        assert result.winner != ""
        assert len(result.conclusions) > 0

    def test_run_creates_output(self, tmp_path):
        config = SFTExperimentConfig(
            output_dir=str(tmp_path / "experiment"),
            dataset_path=str(tmp_path / "nonexistent"),
        )
        runner = SFTExperimentRunner(config)
        result = runner.run()
        json_path = tmp_path / "experiment" / "experiment_result.json"
        md_path = tmp_path / "experiment" / "experiment_result.md"
        assert json_path.exists()
        assert md_path.exists()

    def test_comparison_has_four_variants(self, tmp_path):
        config = SFTExperimentConfig(output_dir=str(tmp_path / "exp"))
        runner = SFTExperimentRunner(config)
        result = runner.run()
        variants = [c.variant_name for c in result.comparisons]
        assert any("base" in v for v in variants)
        assert any("prompted" in v for v in variants)
        assert any("Lyme runtime" in v for v in variants)
        assert any("fine-tuned" in v for v in variants)

    def test_winner_is_best_quality(self, tmp_path):
        config = SFTExperimentConfig(output_dir=str(tmp_path / "exp"))
        runner = SFTExperimentRunner(config)
        result = runner.run()
        best_quality = max(c.quality_score for c in result.comparisons)
        winner = next(c for c in result.comparisons if c.variant_name == result.winner)
        assert winner.quality_score == best_quality

    def test_experiment_id_has_timestamp(self, tmp_path):
        config = SFTExperimentConfig(output_dir=str(tmp_path / "exp"))
        runner = SFTExperimentRunner(config)
        result = runner.run()
        assert "sft-feasibility" in result.experiment_id
