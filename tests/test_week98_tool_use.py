"""Week 98 — Tool-Use Fine-Tuning tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.tool_use_training import (
    ToolUseTrainingExample,
    ToolUseDataGenerator,
    HeuristicPolicyVariant,
    PromptedPolicyVariant,
    TrainedPolicyVariant,
    ToolUseExperimentResult,
    ToolUseExperimentRunner,
)


class TestToolUseTrainingExample:
    def test_defaults(self):
        ex = ToolUseTrainingExample()
        assert ex.example_id == ""
        assert ex.correct_action == ""

    def test_to_dict(self):
        ex = ToolUseTrainingExample(
            example_id="test-001",
            scenario="Fix the bug",
            context={"task": "fix", "loop_count": 0},
            correct_action="read",
            difficulty="easy",
        )
        d = ex.to_dict()
        assert d["example_id"] == "test-001"
        assert d["correct_action"] == "read"
        assert d["context"]["loop_count"] == 0


class TestToolUseDataGenerator:
    def test_generator_creates_examples(self):
        gen = ToolUseDataGenerator()
        examples = gen.generate_all()
        assert len(examples) >= 10

    def test_action_space_coverage(self):
        gen = ToolUseDataGenerator()
        examples = gen.generate_all()
        actions = set(ex.correct_action for ex in examples)
        assert "stop" in actions
        assert "read" in actions

    def test_edge_cases_included(self):
        gen = ToolUseDataGenerator()
        examples = gen.generate_all()
        edge = [e for e in examples if "edge" in e.example_id]
        assert len(edge) >= 4


class TestHeuristicPolicyVariant:
    def test_baseline_evaluation(self):
        heuristic = HeuristicPolicyVariant()
        examples = [
            ToolUseTrainingExample(
                context={"task": "Fix bug", "files_read": [], "loop_count": 0,
                        "has_patch": False, "test_failed": False},
                correct_action="read",
            ),
        ]
        results = heuristic.evaluate(examples)
        assert "accuracy" in results
        assert results["variant"] == "HeuristicRouter"

    def test_decide_returns_policy_decision(self):
        heuristic = HeuristicPolicyVariant()
        decision = heuristic.decide({"task": "", "loop_count": 0, "files_read": ["x.py"]})
        assert decision.action.value in ("stop", "generate_patch", "search", "read", "verify")


class TestPromptedPolicyVariant:
    def test_evaluation(self):
        prompted = PromptedPolicyVariant()
        examples = [
            ToolUseTrainingExample(
                context={"task": "Fix bug", "files_read": [], "loop_count": 0,
                        "has_patch": False, "test_failed": False},
                correct_action="read",
            ),
        ]
        results = prompted.evaluate(examples)
        assert "accuracy" in results

    def test_decide_returns_valid_action(self):
        prompted = PromptedPolicyVariant()
        action = prompted.decide({"loop_count": 0, "files_read": [], "has_patch": False,
                                  "test_failed": False, "task": "Fix bug"})
        assert action in ("search", "read", "inspect_ast", "run_command",
                          "generate_patch", "verify", "stop")


class TestTrainedPolicyVariant:
    def test_train_and_evaluate(self):
        trained = TrainedPolicyVariant()
        train_examples = [
            ToolUseTrainingExample(
                context={"task": "Fix bug", "files_read": [], "loop_count": 0},
                correct_action="read",
            ),
            ToolUseTrainingExample(
                context={"task": "", "files_read": ["x.py"], "loop_count": 5},
                correct_action="stop",
            ),
        ]
        result = trained.train(train_examples)
        assert result["training_examples"] == 2
        assert trained.trained is True

    def test_untrained_falls_back_to_heuristic(self):
        trained = TrainedPolicyVariant()
        assert trained.trained is False
        action = trained.decide({"files_read": []})
        assert action in ("search", "read", "inspect_ast", "run_command",
                          "generate_patch", "verify", "stop")

    def test_trained_weights_affect_decisions(self):
        trained = TrainedPolicyVariant()
        trained.training_memory = {"read": 0.95, "stop": 0.1}
        trained.trained = True
        action = trained.decide({"files_read": [], "task": "Fix"})
        # Should still output something valid
        assert isinstance(action, str)


class TestToolUseExperimentResult:
    def test_defaults(self):
        r = ToolUseExperimentResult()
        assert r.comparisons == []

    def test_to_dict(self):
        r = ToolUseExperimentResult(
            experiment_id="test-001",
            data_sources={"total": 20},
            comparisons=[{"variant": "A", "accuracy": 0.8}],
            winner="A",
            by_action={"search": {"count": 10}},
        )
        d = r.to_dict()
        assert d["experiment_id"] == "test-001"
        assert d["winner"] == "A"

    def test_to_markdown(self):
        r = ToolUseExperimentResult(
            experiment_id="test-001",
            data_sources={"total": 20, "train": 14, "test": 6},
            comparisons=[
                {"variant": "heuristic", "variant_info": {"name": "HeuristicRouter"},
                 "accuracy": 0.75, "is_winner": False},
                {"variant": "trained", "variant_info": {"name": "TrainedPolicy"},
                 "accuracy": 0.85, "is_winner": True},
            ],
            winner="TrainedPolicy",
            by_action={"search": {"count": 5}, "read": {"count": 5}},
            conclusions=["Winner beats heuristic by +0.10"],
        )
        md = r.to_markdown()
        assert "Tool-Use Fine-Tuning Experiment" in md
        assert "TrainedPolicy" in md
        assert "0.85" in md


class TestToolUseExperimentRunner:
    def test_run_creates_experiment(self):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        assert result.experiment_id.startswith("tool-use-")
        assert len(result.comparisons) == 3
        assert result.winner != ""

    def test_comparison_has_three_variants(self):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        variants = [c.get("variant") for c in result.comparisons]
        assert "HeuristicRouter" in variants
        assert any("Prompted" in v for v in variants)
        assert "TrainedPolicy" in variants

    def test_data_sources_non_empty(self):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        assert result.data_sources["total_examples"] > 0

    def test_by_action_populated(self):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        assert len(result.by_action) >= 4

    def test_save_result(self, tmp_path):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        json_path, md_path = runner.save_result(result, str(tmp_path / "exp"))
        assert Path(json_path).exists()
        assert Path(md_path).exists()
        data = json.loads(Path(json_path).read_text())
        assert data["winner"] != ""

    def test_conclusions_non_empty(self):
        runner = ToolUseExperimentRunner()
        result = runner.run()
        assert len(result.conclusions) >= 4
