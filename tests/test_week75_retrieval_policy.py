"""Tests for Week 75 — Retrieval Policy Learning."""

import pytest
from src.lyme_model.retrieval.policies import (
    RETRIEVAL_POLICIES,
    KeywordRetrieval,
    RetrievalResult,
)
from src.lyme_model.retrieval.experiment import (
    RetrievalExperiment,
    RetrievalTrial,
    ExperimentReport,
)


class TestRetrievalPolicies:
    def test_has_7_policies(self):
        assert len(RETRIEVAL_POLICIES) == 7

    def test_all_policies_have_names(self):
        for p in RETRIEVAL_POLICIES:
            assert p.name
            assert p.description

    def test_all_policy_names_unique(self):
        names = [p.name for p in RETRIEVAL_POLICIES]
        assert len(names) == len(set(names))

    def test_policy_names(self):
        expected = {"keyword", "embedding", "graph", "ast", "git_history", "hybrid", "model_planned"}
        found = {p.name for p in RETRIEVAL_POLICIES}
        assert found == expected

    def test_retrieval_result_dataclass(self):
        result = RetrievalResult(
            files=[{"path": "test.py", "score": 0.9, "method": "keyword"}],
            context_size_tokens=50,
            latency_ms=10,
            policy_name="keyword",
            total_candidates=100,
        )
        assert len(result.files) == 1
        assert result.policy_name == "keyword"

    def test_keyword_retrieval_on_lyme_repo(self):
        policy = KeywordRetrieval()
        result = policy.retrieve("failure taxonomy", "src/lyme_model")
        assert result.policy_name == "keyword"
        assert result.total_candidates >= 0

    def test_retrieval_result_to_dict(self):
        result = RetrievalResult(
            files=[{"path": "a.py", "score": 0.5, "method": "test"}],
            context_size_tokens=10,
            latency_ms=5,
            policy_name="test",
        )
        d = result.to_dict()
        assert d["policy_name"] == "test"
        assert d["context_size_tokens"] == 10


class TestRetrievalExperiment:
    def test_experiment_initializes(self):
        exp = RetrievalExperiment(repo_path=".")
        assert exp.repo_path == "."
        assert exp.trials == []

    def test_run_trial(self):
        exp = RetrievalExperiment(repo_path="src/lyme_model")
        trial = exp.run_trial("keyword", "test task", ["__init__.py"])
        assert trial.policy_name == "keyword"
        assert isinstance(trial.result, RetrievalResult)

    def test_unknown_policy_raises(self):
        exp = RetrievalExperiment(repo_path=".")
        with pytest.raises(ValueError):
            exp.run_trial("nonexistent", "task")

    def test_run_all_policies(self):
        exp = RetrievalExperiment(repo_path="src/lyme_model")
        trials = exp.run_all_policies("find error handling")
        assert len(trials) == 7
        for t in trials:
            assert t.policy_name in {p.name for p in RETRIEVAL_POLICIES}

    def test_report_after_trials(self):
        exp = RetrievalExperiment(repo_path="src/lyme_model")
        exp.run_all_policies("find error handling")
        report = exp.report()
        assert report.winner
        assert len(report.policy_results) == 7

    def test_report_no_trials(self):
        exp = RetrievalExperiment(repo_path=".")
        report = exp.report()
        assert "No trials" in report.summary

    def test_report_to_markdown(self):
        exp = RetrievalExperiment(repo_path="src/lyme_model")
        exp.run_all_policies("find error handling")
        report = exp.report()
        md = report.to_markdown()
        assert "Retrieval Policy Experiment Report" in md
        assert "Winner" in md


class TestRetrievalTrial:
    def test_trial_properties(self):
        trial = RetrievalTrial(
            policy_name="test",
            task="find error handling",
            result=RetrievalResult(
                files=[
                    {"path": "src/a.py", "score": 0.9, "method": "test"},
                    {"path": "src/b.py", "score": 0.5, "method": "test"},
                ],
                context_size_tokens=100,
                latency_ms=50,
                policy_name="test",
            ),
            ground_truth_files=["src/a.py"],
        )
        assert trial.irrelevant_context_rate == 0.5
        assert trial.missing_evidence_rate == 0.0

    def test_trial_no_ground_truth(self):
        trial = RetrievalTrial(
            policy_name="test",
            task="task",
            result=RetrievalResult(
                files=[{"path": "a.py", "score": 0.5, "method": "test"}],
                context_size_tokens=10,
                latency_ms=5,
                policy_name="test",
            ),
        )
        assert trial.irrelevant_context_rate == 0.0
        assert trial.missing_evidence_rate == 0.0
