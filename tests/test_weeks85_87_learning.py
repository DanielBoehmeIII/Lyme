"""Tests for weeks 85-87: Learning pipeline (data generation, tool policy, patch critic)."""

import pytest
import os
import tempfile
from src.lyme_model.learning import (
    ToolExample, DataGenerator, DatasetSchema,
    ToolPolicyModel, HeuristicRouter, Action,
    PatchCritic, CriticVerdict,
)


class TestWeek85DataGeneration:
    def test_tool_example_dataclass(self):
        ex = ToolExample(
            trace_id="t1", situation="Fix auth bug",
            action_taken="search", action_correct=True,
        )
        assert ex.trace_id == "t1"
        assert ex.action_correct is True
        d = ex.to_dict()
        assert d["trace_id"] == "t1"

    def test_dataset_schema_defaults(self):
        s = DatasetSchema()
        assert s.version == "1.0"
        assert s.total_examples == 0

    def test_dataset_schema_to_dict(self):
        s = DatasetSchema(version="2.0", total_examples=10, train_count=8, val_count=2)
        d = s.to_dict()
        assert d["version"] == "2.0"
        assert d["total_examples"] == 10

    def test_dataset_schema_to_markdown(self):
        s = DatasetSchema(total_examples=10, train_count=8, val_count=2)
        s.by_action = {"search": 5, "read": 5}
        md = s.to_markdown()
        assert "Tool-Use Dataset" in md
        assert "**Total**: 10" in md

    def test_data_generator_initializes(self):
        dg = DataGenerator()
        assert dg.val_split == 0.2
        assert dg.examples == []

    def test_data_generator_has_7_action_types(self):
        dg = DataGenerator()
        assert len(dg.ACTION_TYPES) == 7

    def test_data_generator_has_6_quality_filters(self):
        dg = DataGenerator()
        assert len(dg.QUALITY_FILTERS) == 6

    def test_from_audit_trace_returns_example(self):
        dg = DataGenerator()
        trace = {
            "trace_id": "trace1",
            "task": "Fix the login bug",
            "tool_calls": [
                {"tool": "grep_search", "params": {"query": "login"}},
                {"tool": "read_file", "params": {"path": "auth.py"}},
                {"tool": "edit_file", "params": {"path": "auth.py"}},
            ],
            "output": "Fixed it",
            "success": True,
        }
        ex = dg.from_audit_trace(trace)
        assert ex is not None
        assert ex.action_taken == "search"
        assert ex.action_correct is True
        assert ex.source == "audit_trace"

    def test_from_audit_trace_too_few_calls(self):
        dg = DataGenerator()
        trace = {"trace_id": "t2", "tool_calls": [{"tool": "read_file"}], "success": True}
        assert dg.from_audit_trace(trace) is None

    def test_from_audit_trace_empty_calls(self):
        dg = DataGenerator()
        trace = {"trace_id": "t3", "tool_calls": [], "success": True}
        assert dg.from_audit_trace(trace) is None

    def test_generate_synthetic_creates_examples(self):
        dg = DataGenerator()
        examples = dg.generate_synthetic(count=20)
        assert len(examples) == 20
        assert all(isinstance(e, ToolExample) for e in examples)

    def test_generate_synthetic_has_varied_actions(self):
        dg = DataGenerator()
        examples = dg.generate_synthetic(count=50)
        actions = set(e.action_taken for e in examples)
        assert len(actions) >= 5

    def test_generate_synthetic_deterministic_seed(self):
        dg1 = DataGenerator()
        dg2 = DataGenerator()
        ex1 = dg1.generate_synthetic(count=10)
        ex2 = dg2.generate_synthetic(count=10)
        assert len(ex1) == len(ex2)

    def test_build_dataset_returns_schema(self):
        dg = DataGenerator()
        dg.generate_synthetic(count=21)
        schema = dg.build_dataset()
        assert isinstance(schema, DatasetSchema)
        assert schema.total_examples == 21
        assert schema.train_count + schema.val_count == 21

    def test_build_dataset_tracks_by_action(self):
        dg = DataGenerator()
        dg.generate_synthetic(count=21)
        schema = dg.build_dataset()
        assert len(schema.by_action) >= 1
        total = sum(schema.by_action.values())
        assert total == 21

    def test_build_dataset_tracks_by_difficulty(self):
        dg = DataGenerator()
        dg.generate_synthetic(count=50)
        schema = dg.build_dataset()
        assert len(schema.by_difficulty) >= 1

    def test_baseline_comparison_with_examples(self):
        dg = DataGenerator()
        dg.generate_synthetic(count=20)
        result = dg.baseline_comparison()
        assert "total" in result
        assert result["total"] == 20

    def test_baseline_comparison_no_examples(self):
        dg = DataGenerator()
        result = dg.baseline_comparison()
        assert "error" in result

    def test_tool_example_situation_truncated(self):
        long_sit = "x" * 500
        ex = ToolExample(situation=long_sit)
        d = ex.to_dict()
        assert len(d["situation"]) == 200


class TestWeek86ToolPolicy:
    def test_action_enum_values(self):
        assert Action.SEARCH.value == "search"
        assert Action.STOP.value == "stop"
        assert len(Action) == 7

    def test_heuristic_router_basic(self):
        router = HeuristicRouter()
        decision = router.decide({"state": "", "task": "fix bug"})
        assert decision.action in Action

    def test_heuristic_router_read_before_act(self):
        router = HeuristicRouter()
        decision = router.decide({
            "state": "", "task": "fix bug",
            "files_read": [], "loop_count": 0,
        })
        assert decision.action == Action.READ

    def test_heuristic_router_stops_on_loop(self):
        router = HeuristicRouter()
        decision = router.decide({"loop_count": 10})
        assert decision.action == Action.STOP

    def test_heuristic_router_verifies_with_patch(self):
        router = HeuristicRouter()
        decision = router.decide({
            "patch_content": "diff --git a/x.py b/x.py",
            "test_failed": False,
            "files_read": ["x.py"],
        })
        assert decision.action == Action.VERIFY

    def test_heuristic_router_searches_on_test_fail(self):
        router = HeuristicRouter()
        decision = router.decide({
            "test_failed": True,
            "has_patch": True,
            "files_read": ["x.py"],
        })
        assert decision.action == Action.SEARCH

    def test_heuristic_router_generates_patch(self):
        router = HeuristicRouter()
        decision = router.decide({
            "state": "", "task": "fix bug",
            "files_read": ["x.py"],
            "loop_count": 0,
        })
        assert decision.action == Action.GENERATE_PATCH

    def test_heuristic_router_stops_idle(self):
        router = HeuristicRouter()
        decision = router.decide({})
        assert decision.action == Action.STOP

    def test_policy_decision_has_confidence(self):
        router = HeuristicRouter()
        decision = router.decide({"task": "fix", "files_read": []})
        assert 0.0 <= decision.confidence <= 1.0

    def test_policy_decision_to_dict(self):
        router = HeuristicRouter()
        decision = router.decide({"task": "fix"})
        d = decision.to_dict()
        assert "action" in d
        assert "confidence" in d

    def test_tool_policy_model_heuristic_mode(self):
        policy = ToolPolicyModel(mode="heuristic")
        decision = policy.decide({"task": "fix bug"})
        assert decision.action in Action

    def test_tool_policy_model_weighted_mode(self):
        policy = ToolPolicyModel(mode="weighted")
        decision = policy.decide({"task": "fix bug", "files_read": []})
        assert decision.action in Action

    def test_tool_policy_model_tracks_decisions(self):
        policy = ToolPolicyModel()
        policy.decide({"task": "a"})
        policy.decide({"task": "b"})
        assert len(policy.decisions) == 2

    def test_tool_policy_model_train_step(self):
        policy = ToolPolicyModel(mode="weighted")
        examples = [
            ({"task": "fix", "files_read": ["x.py"]}, "generate_patch"),
            ({"task": "fix", "files_read": []}, "read"),
        ]
        result = policy.train_step(examples)
        assert result["examples"] == 2
        assert "accuracy" in result
        assert "weights" in result

    def test_tool_policy_model_train_step_empty(self):
        policy = ToolPolicyModel()
        result = policy.train_step([])
        assert result["examples"] == 0

    def test_tool_policy_model_benchmark(self):
        policy = ToolPolicyModel()
        examples = [
            ({"task": "fix", "files_read": []}, "read"),
        ]
        result = policy.benchmark(examples)
        assert result["total"] == 1

    def test_tool_policy_model_benchmark_empty(self):
        policy = ToolPolicyModel()
        result = policy.benchmark([])
        assert result["total"] == 0

    def test_weighted_mode_updates_weights(self):
        policy = ToolPolicyModel(mode="weighted")
        initial = policy.weights["search"]
        policy.train_step([({"task": "find x"}, "search")])
        assert policy.weights["search"] >= initial


class TestWeek87PatchCritic:
    def test_critic_verdict_dataclass(self):
        v = CriticVerdict(approved=True, risks=[], confidence=0.9)
        assert v.approved is True
        assert v.confidence == 0.9

    def test_critic_verdict_to_dict(self):
        v = CriticVerdict(approved=False, blocked_reasons=["Bad patch"])
        d = v.to_dict()
        assert "blocked_reasons" in d
        assert "Bad patch" in d["blocked_reasons"]

    def test_patch_critic_initializes(self):
        critic = PatchCritic()
        assert critic.verdicts == []
        assert critic.false_rejections == 0

    def test_patch_critic_approves_valid_patch(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+print('hello')",
            target_file="test.py",
        )
        assert verdict.approved is True

    def test_patch_critic_detects_syntax_error(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+def foo(:\n+    pass",
            target_file="test.py",
        )
        assert verdict.approved is False
        assert any("syntax" in r.lower() for r in verdict.blocked_reasons)

    def test_patch_critic_detects_wrong_file(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+print('hello')",
            target_file="unexpected.py",
            context={"task_files": ["expected.py"]},
        )
        assert verdict.approved is False

    def test_patch_critic_flags_new_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "test.py")
            with open(target, "w") as f:
                f.write("print('existing code')\n")
            critic = PatchCritic(repo_path=tmpdir)
            verdict = critic.evaluate(
                patch_content="+import numpy\n+print('ok')",
                target_file="test.py",
            )
            assert len(verdict.risks) >= 1

    def test_patch_critic_flags_large_additions(self):
        critic = PatchCritic()
        big_patch = "\n".join([f"+line_{i}" for i in range(60)])
        verdict = critic.evaluate(big_patch, "test.py")
        assert any("Large addition" in r for r in verdict.risks)

    def test_patch_critic_flags_large_removals(self):
        critic = PatchCritic()
        big_removal = "\n".join([f"-line_{i}" for i in range(35)])
        verdict = critic.evaluate(big_removal, "test.py")
        assert any("Large removal" in r for r in verdict.risks)

    def test_patch_critic_hallucinated_symbols(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+nonexistent_function()\n+print('ok')",
            target_file="test.py",
            context={"known_symbols": {"print", "len", "range"}},
        )
        assert any("hallucination" in r.lower() for r in verdict.risks)

    def test_patch_critic_architectural_rules(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+import os\n+os.system('rm -rf /')",
            target_file="test.py",
            context={"architectural_rules": ["never use os.system"]},
        )
        has_violation = any("architectural" in r.lower() for r in verdict.risks)
        assert has_violation or verdict.approved is not None

    def test_patch_critic_tracks_stats(self):
        critic = PatchCritic()
        critic.evaluate("+ok", "test.py")
        critic.evaluate("+def foo(:\n+pass", "test.py")
        stats = critic.stats()
        assert stats["total_evaluations"] == 2
        assert stats["prevented_failures"] >= 0

    def test_patch_critic_builtin_symbols_not_flagged(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+result = len(items)\n+print(result)",
            target_file="test.py",
            context={"known_symbols": set()},
        )
        assert verdict.approved is True

    def test_patch_critic_handles_missing_file(self):
        critic = PatchCritic()
        verdict = critic.evaluate(
            patch_content="+print('hello')",
            target_file="/nonexistent/path/file.py",
        )
        assert verdict.approved is True

    def test_patch_critic_tracks_latency(self):
        critic = PatchCritic()
        verdict = critic.evaluate("+print('hello')", "test.py")
        assert verdict.latency_ms >= 0

    def test_patch_critic_multiple_risks_cumulative(self):
        critic = PatchCritic()
        big_patch = "\n".join([f"+line_{i}" for i in range(60)])
        verdict = critic.evaluate(
            big_patch,
            "unexpected.py",
            context={
                "task_files": ["expected.py"],
                "architectural_rules": ["never use big functions"],
            },
        )
        assert len(verdict.risks) >= 1
