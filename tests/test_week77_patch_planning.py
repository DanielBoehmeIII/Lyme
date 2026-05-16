"""Tests for Week 77 — Patch Planning for Weak Models."""

import pytest
from src.lyme_model.planning.patch_planner import (
    PatchPlan,
    PatchPlanner,
    PlanValidator,
    PlanCritic,
    DirectPatchStrategy,
    PlanThenPatchStrategy,
    PlanCriticPatchStrategy,
    PATCH_STRATEGIES,
    RUNTIME_COMPARISON_METRICS,
    run_patch_comparison,
)


class TestPatchPlan:
    def test_plan_creation(self):
        plan = PatchPlan(
            affected_files=["auth.py"],
            intended_change="Add input validation",
            verification_command="pytest test_auth.py",
            rollback_path="git checkout auth.py",
            expected_diff_shape="+20 lines, modify 1 function",
        )
        assert len(plan.affected_files) == 1
        assert plan.status == "draft"

    def test_plan_is_valid(self):
        plan = PatchPlan(
            affected_files=["auth.py"],
            intended_change="Add validation",
            verification_command="pytest",
            rollback_path="git checkout",
            expected_diff_shape="+10 lines",
        )
        assert plan.is_valid() is True

    def test_plan_invalid_empty(self):
        plan = PatchPlan()
        assert plan.is_valid() is False

    def test_plan_to_dict(self):
        plan = PatchPlan(
            affected_files=["a.py"],
            intended_change="Fix bug",
            verification_command="pytest",
            rollback_path="git checkout",
            expected_diff_shape="+5 lines",
            plan_id="test_001",
        )
        d = plan.to_dict()
        assert d["plan_id"] == "test_001"
        assert d["valid"] is True


class TestPlanValidator:
    def test_validator_accepts_good_plan(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        validator = PlanValidator(repo_path=str(tmp_path))
        plan = PatchPlan(
            affected_files=["test.py"],
            intended_change="Add a function",
            verification_command="pytest",
            rollback_path="git checkout test.py",
            expected_diff_shape="+5 lines",
        )
        validated = validator.validate(plan)
        assert validated.status == "validated"
        assert len(validated.validation_errors) == 0

    def test_validator_rejects_bad_plan(self):
        validator = PlanValidator(repo_path=".")
        plan = PatchPlan()
        validated = validator.validate(plan)
        assert validated.status == "rejected"
        assert len(validated.validation_errors) > 0

    def test_validator_checks_file_existence(self, tmp_path):
        validator = PlanValidator(repo_path=str(tmp_path))
        plan = PatchPlan(
            affected_files=["nonexistent.py"],
            intended_change="Fix the bug that needs fixing",
            verification_command="pytest",
            rollback_path="git checkout",
            expected_diff_shape="+5 lines",
        )
        validated = validator.validate(plan)
        assert len(validated.validation_errors) >= 1
        assert "nonexistent" in validated.validation_errors[0]


class TestPlanCritic:
    def test_critic_adds_notes(self):
        critic = PlanCritic()
        plan = PatchPlan(
            affected_files=["auth.py"],
            intended_change="Add import for new module and modify login function",
        )
        plan = critic.critique(plan)
        assert len(plan.critic_notes) >= 1

    def test_critic_notes_import_risk(self):
        critic = PlanCritic()
        plan = PatchPlan(
            affected_files=["main.py"],
            intended_change="Import new library and use it",
        )
        plan = critic.critique(plan)
        import_notes = [n for n in plan.critic_notes if "Import" in n]
        assert len(import_notes) >= 1

    def test_critic_warns_test_files(self):
        critic = PlanCritic()
        plan = PatchPlan(
            affected_files=["tests/test_auth.py"],
            intended_change="Fix test assertion",
        )
        plan = critic.critique(plan)
        test_notes = [n for n in plan.critic_notes if "test file" in n.lower()]
        assert len(test_notes) >= 1


class TestPatchPlanner:
    def test_planner_creates_plan(self):
        planner = PatchPlanner()
        plan = planner.create_plan(
            affected_files=["auth.py"],
            intended_change="Add validation",
            verification_command="pytest",
            rollback_path="git checkout",
            expected_diff_shape="+10 lines",
        )
        assert plan.plan_id.startswith("plan_")
        assert plan in planner.plans.values()

    def test_validate_and_critique(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        planner = PatchPlanner(repo_path=str(tmp_path))
        plan = planner.create_plan(
            affected_files=["test.py"],
            intended_change="Add validation to the login function",
            verification_command="pytest",
            rollback_path="git checkout",
            expected_diff_shape="+10 lines",
        )
        result = planner.validate_and_critique(plan)
        assert result.status == "validated"
        assert len(result.validation_errors) == 0

    def test_validate_and_critique_rejected(self):
        planner = PatchPlanner()
        plan = planner.create_plan(
            affected_files=[],
            intended_change="",
        )
        result = planner.validate_and_critique(plan)
        assert result.status == "rejected"


class TestStrategies:
    def test_direct_patch_strategy(self):
        strategy = DirectPatchStrategy()
        result = strategy.execute("test", lambda t: "patch output")
        assert result.strategy == "direct"
        assert result.success is True
        assert result.validation_time_ms == 0

    def test_direct_patch_failure(self):
        strategy = DirectPatchStrategy()

        def failing(t):
            raise ValueError("patch failed")

        result = strategy.execute("test", failing)
        assert result.success is False
        assert len(result.errors) > 0

    def test_plan_then_patch_success(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        planner = PatchPlanner(repo_path=str(tmp_path))
        strategy = PlanThenPatchStrategy(planner)

        def plan_fn(t):
            return planner.create_plan(
                affected_files=["test.py"],
                intended_change="Add a function",
                verification_command="pytest",
                rollback_path="git checkout",
                expected_diff_shape="+5 lines",
            )

        def patch_fn(t):
            return "patched content"

        result = strategy.execute("test", patch_fn, plan_fn)
        assert result.success is True
        assert result.plan is not None

    def test_plan_then_patch_rejected(self):
        planner = PatchPlanner()
        strategy = PlanThenPatchStrategy(planner)

        def plan_fn(t):
            return planner.create_plan(affected_files=[], intended_change="")

        def patch_fn(t):
            return "patched"

        result = strategy.execute("test", patch_fn, plan_fn)
        assert result.success is False
        assert len(result.errors) > 0

    def test_three_strategies_available(self):
        assert "direct" in PATCH_STRATEGIES
        assert "plan_then_patch" in PATCH_STRATEGIES
        assert "plan_critic_patch" in PATCH_STRATEGIES

    def test_comparison_metrics_defined(self):
        assert "success_rate" in RUNTIME_COMPARISON_METRICS
        assert "blocked_bad_patches" in RUNTIME_COMPARISON_METRICS
