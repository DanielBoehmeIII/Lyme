"""Tests for Weeks 101-104: Preference Data, Reward Model, Self-Improvement, Multi-Candidate."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.preference_data import (
    PreferencePair, PreferenceDataset, PreferenceDataGenerator,
)
from src.lyme_model.learning.reward_model import (
    RewardScore, LocalRewardModel,
)
from src.lyme_model.learning.self_improvement import (
    ImprovementStep, ImprovementRun, SelfImprovementLoop,
)
from src.lyme_model.learning.multi_candidate import (
    Candidate, MultiCandidateResult, MultiCandidateDecoder,
)


# ─── Week 101: Preference Data ────────────────────────────────────────────────

class TestPreferencePair:
    def test_defaults(self):
        p = PreferencePair()
        assert p.pair_id == ""
        assert p.preference_type == ""

    def test_to_dict(self):
        p = PreferencePair(
            pair_id="pref-001", preference_type="plan_quality",
            task="Fix bug", chosen="good", rejected="bad",
            preference_reason="reason", label_source="human",
        )
        d = p.to_dict()
        assert d["pair_id"] == "pref-001"
        assert d["preference_type"] == "plan_quality"


class TestPreferenceDataset:
    def test_defaults(self):
        ds = PreferenceDataset()
        assert ds.version == "0.1"
        assert ds.pairs == []

    def test_compute_stats(self):
        ds = PreferenceDataset(pairs=[
            PreferencePair(preference_type="plan_quality", label_source="human", difficulty="easy"),
            PreferencePair(preference_type="patch_safety", label_source="critic", difficulty="hard"),
        ])
        ds.compute_stats()
        assert ds.by_type["plan_quality"] == 1
        assert ds.by_type["patch_safety"] == 1
        assert ds.by_source["human"] == 1
        assert ds.by_difficulty["hard"] == 1


class TestPreferenceDataGenerator:
    def test_generate_all(self):
        gen = PreferenceDataGenerator()
        ds = gen.generate_all()
        assert len(ds.pairs) >= 10
        types = set(p.preference_type for p in ds.pairs)
        assert "plan_quality" in types
        assert "patch_safety" in types
        assert "grounding" in types
        assert "edit_size" in types
        assert "verification" in types

    def test_save(self, tmp_path):
        gen = PreferenceDataGenerator()
        ds = gen.generate_all()
        out = gen.save(str(tmp_path / "pref"))
        assert Path(out).exists()
        data = json.loads(Path(out).read_text())
        assert "dataset" in data
        assert "pairs" in data


# ─── Week 102: Reward Model ───────────────────────────────────────────────────

class TestRewardScore:
    def test_defaults(self):
        s = RewardScore()
        assert s.overall == 0.0
        assert s.warnings == []

    def test_to_dict(self):
        s = RewardScore(plan_quality=0.8, patch_safety=0.9, overall=0.85, latency_ms=10.0)
        d = s.to_dict()
        assert d["plan_quality"] == 0.8
        assert d["patch_safety"] == 0.9


class TestLocalRewardModel:
    def test_score_patch_empty(self):
        model = LocalRewardModel()
        score = model.score_patch("")
        assert score.overall >= 0.0  # non-zero due to fallback defaults

    def test_score_good_patch(self):
        model = LocalRewardModel()
        patch = "if b == 0: raise ValueError('Cannot divide by zero')"
        score = model.score_patch(patch)
        assert score.overall > 0.3
        assert score.patch_safety > 0.3

    def test_score_risky_patch(self):
        model = LocalRewardModel()
        patch = "exec('delete all files')"
        score = model.score_patch(patch)
        assert score.patch_safety < 0.5

    def test_score_with_context(self):
        model = LocalRewardModel()
        patch = "Add validation for title field"
        ctx = {
            "known_symbols": ["validate", "title"],
            "verification_commands": ["pytest"],
            "tests_passed": 5,
            "total_tests": 5,
        }
        score = model.score_patch(patch, ctx)
        assert score.overall > 0.3
        assert score.evidence_grounding > 0.3
        assert score.likely_test_success > 0.5

    def test_evaluate_dataset(self):
        model = LocalRewardModel()
        results = model.evaluate_dataset([
            ("if b == 0: raise ValueError", {}),
            ("exec('rm -rf /')", {}),
        ])
        assert results["total_evaluated"] == 2

    def test_dimension_weights_sum_to_one(self):
        model = LocalRewardModel()
        total = sum(model.WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


# ─── Week 103: Self-Improvement ───────────────────────────────────────────────

class TestImprovementStep:
    def test_defaults(self):
        s = ImprovementStep()
        assert s.step_number == 0
        assert s.verified is False

    def test_to_dict(self):
        s = ImprovementStep(step_number=1, action="generate", score=0.8, verified=True)
        d = s.to_dict()
        assert d["step_number"] == 1
        assert d["action"] == "generate"


class TestImprovementRun:
    def test_defaults(self):
        r = ImprovementRun()
        assert r.guardrails_triggered == []

    def test_to_markdown(self):
        r = ImprovementRun(
            run_id="test-001", task="Fix bug",
            steps=[ImprovementStep(step_number=1, action="plan", verified=True)],
            final_verdict="completed", total_score=0.8, improvement_detected=True,
        )
        md = r.to_markdown()
        assert "Self-Improvement Run" in md
        assert "completed" in md


class TestSelfImprovementLoop:
    def test_safe_task_completes(self):
        loop = SelfImprovementLoop()
        run = loop.run_improvement("Fix division by zero in calculator.py")
        assert run.final_verdict == "completed"
        assert len(run.steps) >= 3

    def test_core_rewrite_blocked(self):
        loop = SelfImprovementLoop()
        run = loop.run_improvement("Rewrite the entire Lyme audit system")
        assert len(run.guardrails_triggered) > 0

    def test_audit_overwrite_blocked(self):
        loop = SelfImprovementLoop()
        run = loop.run_improvement("Delete all audit traces")
        assert len(run.guardrails_triggered) > 0

    def test_benchmark_returns_metrics(self):
        loop = SelfImprovementLoop()
        results = loop.benchmark()
        assert results["total_tasks"] == 6
        assert results["guardrail_hits"] >= 2
        assert results["unsafe_tasks_blocked"] >= 2

    def test_no_recursive_improvement(self):
        loop = SelfImprovementLoop()
        # Verify we don't claim recursive self-improvement
        assert "recursive" not in loop.__doc__

    def test_no_training_on_unverified(self):
        loop = SelfImprovementLoop()
        run = loop.run_improvement("Fix division by zero")
        for step in run.steps:
            if step.stored:
                assert step.verified  # Can't store unverified


# ─── Week 104: Multi-Candidate ────────────────────────────────────────────────

class TestCandidate:
    def test_defaults(self):
        c = Candidate()
        assert c.index == 0
        assert c.selected is False

    def test_to_dict(self):
        c = Candidate(index=1, content="fix bug", score=0.85, selected=True)
        d = c.to_dict()
        assert d["index"] == 1
        assert d["selected"] is True


class TestMultiCandidateResult:
    def test_defaults(self):
        r = MultiCandidateResult()
        assert r.num_candidates == 0

    def test_to_dict(self):
        r = MultiCandidateResult(
            task="Fix bug", num_candidates=3,
            candidates=[Candidate(index=0, score=0.5), Candidate(index=1, score=0.9)],
            best_score=0.9, selection_method="critic_ranked",
        )
        d = r.to_dict()
        assert d["best_score"] == 0.9
        assert d["num_candidates"] == 3


class TestMultiCandidateDecoder:
    def test_generate_and_rank(self):
        decoder = MultiCandidateDecoder(num_candidates=3)
        result = decoder.generate_and_rank("Fix division by zero")
        assert len(result.candidates) == 3
        assert result.best_score > 0

    def test_selection_picks_best(self):
        decoder = MultiCandidateDecoder(num_candidates=3)
        result = decoder.generate_and_rank("Fix division by zero")
        selected = [c for c in result.candidates if c.selected]
        assert len(selected) == 1
        assert selected[0].score == result.best_score

    def test_benchmark(self):
        decoder = MultiCandidateDecoder(num_candidates=3)
        results = decoder.benchmark()
        assert results["num_tasks"] == 5
        assert results["candidates_per_task"] == 3
        assert results["avg_best_score"] > 0

    def test_best_of_n_gains(self):
        gains = MultiCandidateDecoder.best_of_n_gains()
        assert "n=1" in gains
        assert "n=3" in gains
        assert "n=5" in gains

    def test_custom_generator(self):
        decoder = MultiCandidateDecoder(num_candidates=2)
        def custom_gen(task, idx):
            return f"Custom solution {idx}: {task}"
        result = decoder.generate_and_rank("Fix bug", custom_gen)
        assert "Custom" in result.candidates[0].content

    def test_ranking_by_score(self):
        decoder = MultiCandidateDecoder(num_candidates=3)
        # All candidates generated; ranking puts highest score first
        result = decoder.generate_and_rank("Fix something")
        scores = [c.score for c in result.candidates]
        assert scores == sorted(scores, reverse=True)
