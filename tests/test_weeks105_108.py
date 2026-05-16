"""Tests for Weeks 105-108: Repo conditioning, scale experiments, model mixture."""

import pytest
from src.lyme_model.learning.repo_conditioning import (
    ConditioningPacket, RepoConditioner, REPO_CONDITIONING_PACKETS,
)
from src.lyme_model.learning.scale_experiments import (
    ScaleComparison, ScaleExperimentRunner,
)
from src.lyme_model.learning.model_mixture import (
    SpecialistModel, ModelMixtureRunner, SPECIALISTS,
)


class TestRepoConditioning:
    def test_all_packets_have_fields(self):
        for name, p in REPO_CONDITIONING_PACKETS.items():
            assert p.repo_type == name
            assert len(p.framework_conventions) > 0
            assert len(p.architecture_rules) > 0
            assert len(p.common_failure_modes) > 0

    def test_detect_repo_type(self):
        assert RepoConditioner.detect_repo_type(["pyproject.toml", "src/main.py"]) == "python_package"

    def test_undocumented_fallback(self):
        assert RepoConditioner.detect_repo_type(["random.bin"]) == "undocumented"

    @pytest.mark.parametrize("repo_type", ["python_package", "fastapi_service", "react_app",
                                            "cli_tool", "test_heavy", "undocumented"])
    def test_get_packet_for_all_types(self, repo_type):
        p = RepoConditioner.get_packet(repo_type)
        assert p.repo_type == repo_type

    def test_build_prompt(self):
        prompt = RepoConditioner.build_conditioning_prompt("python_package", "Add a module")
        assert "Repository type: python_package" in prompt
        assert "Conventions:" in prompt
        assert "Task: Add a module" in prompt

    def test_benchmark(self):
        r = RepoConditioner.benchmark()
        assert r["total_types"] == 6
        assert len(r["tasks"]) == 6


class TestScaleExperiments:
    def test_retrieval_experiment(self):
        runner = ScaleExperimentRunner()
        r = runner.run_retrieval_experiment()
        assert r["experiment"] == "Small Model + Big Retrieval"
        assert len(r["comparisons"]) == 5

    def test_critic_experiment(self):
        runner = ScaleExperimentRunner()
        r = runner.run_critic_experiment()
        assert r["experiment"] == "Small Model + Strong Critic"
        assert len(r["comparisons"]) == 4

    def test_retrieval_key_finding(self):
        runner = ScaleExperimentRunner()
        r = runner.run_retrieval_experiment()
        assert "retrieval" in r["key_finding"].lower()


class TestModelMixture:
    def test_specialists_defined(self):
        roles = {"planner", "retriever", "patch_generator", "critic",
                 "summarizer", "verifier", "refusal_detector"}
        assert set(SPECIALISTS.keys()) == roles

    def test_single_model_agent(self):
        r = ModelMixtureRunner.single_model_agent()
        assert r["variant"] == "Single model (7B)"
        assert r["quality"] == 0.50

    def test_heuristic_mixture(self):
        r = ModelMixtureRunner.heuristic_mixture()
        assert "specialists" in r
        assert len(r["specialists"]) == 7

    def test_benchmark(self):
        r = ModelMixtureRunner.benchmark()
        assert "single_model" in r
        assert "heuristic_mixture" in r
        assert "comparison" in r
