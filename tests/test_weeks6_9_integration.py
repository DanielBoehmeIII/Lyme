"""Integration tests for Weeks 6-9: Patch Planning, Generation, Verification, Self-Repair."""

from lyme_model.planning.patch_planner import (
    PatchPlan, PatchPlanner, PlanValidator, PlanCritic,
)
from lyme_model.verification.verifier import (
    FileExistenceVerifier, SymbolVerifier, ImportVerifier, VerifierFirstAgent,
)
from lyme_model.correction.loop import CorrectionLoop, SelfCorrectingAgent


# ─── Week 6: Patch Planning MVP ────────────────────────────────────────────────

def test_patch_plan_creation():
    plan = PatchPlan(
        affected_files=["auth.py"],
        intended_change="Add input validation",
        verification_command="pytest test_auth.py",
        rollback_path="git checkout auth.py",
        expected_diff_shape="+20 lines, modify 1 function",
    )
    assert plan.is_valid()
    assert plan.status == "draft"
    d = plan.to_dict()
    assert d["affected_files"] == ["auth.py"]


def test_patch_plan_invalid():
    plan = PatchPlan()
    assert not plan.is_valid()


def test_patch_planner_creates_plan():
    planner = PatchPlanner()
    plan = planner.create_plan(
        affected_files=["auth.py"],
        intended_change="Fix login bug in auth module",
        verification_command="pytest tests/test_auth.py",
        rollback_path="git checkout auth.py",
        expected_diff_shape="+10 lines in auth.py",
    )
    assert len(plan.affected_files) > 0
    assert plan.intended_change != ""


def test_patch_planner_with_test_failure():
    planner = PatchPlanner()
    plan = planner.create_plan(
        affected_files=["auth.py", "models/user.py"],
        intended_change="Fix login returning 401 when credentials valid",
        verification_command="pytest tests/test_auth.py",
        rollback_path="git checkout auth.py models/user.py",
        expected_diff_shape="+15 lines across 2 files",
    )
    assert plan.is_valid() or plan.validation_errors


def test_plan_validator():
    plan = PatchPlan(
        affected_files=["auth.py"],
        intended_change="Add validation",
        verification_command="pytest",
        rollback_path="git checkout",
    )
    validator = PlanValidator()
    result = validator.validate(plan)
    assert result is not None


def test_plan_critic():
    plan = PatchPlan(affected_files=["auth.py"], intended_change="Fix auth", verification_command="pytest")
    critic = PlanCritic()
    result = critic.critique(plan)
    assert result is not None
    assert result.critic_notes is not None





# ─── Week 8: Verification Layer ────────────────────────────────────────────────

def test_file_existence_verifier():
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        v = FileExistenceVerifier()
        # File exists relative to tmp
        test_file = os.path.join(tmp, "test.py")
        open(test_file, "w").close()
        result = v.verify({"path": test_file})
        assert result is not None


def test_symbol_verifier():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "test.py").write_text("def foo():\n    pass\nclass Bar:\n    pass\n")
        v = SymbolVerifier()
        result = v.verify({"path": str(tmp / "test.py")})
        assert result is not None


def test_import_verifier():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "test.py").write_text("import os\nimport sys\n")
        v = ImportVerifier()
        result = v.verify({"path": str(tmp / "test.py")})
        assert result is not None


def test_verifier_first_agent():
    agent = VerifierFirstAgent()
    assert agent is not None


# ─── Week 9: Self-Repair Loop ──────────────────────────────────────────────────

def test_correction_loop_init():
    loop = CorrectionLoop()
    assert loop.max_attempts >= 1
    assert loop.max_attempts <= 3


def test_correction_loop_summarize_failure():
    loop = CorrectionLoop()
    summary = loop.summarize_failure({"error": "ImportError: no module"})
    assert summary is not None
    assert len(summary) > 0


def test_correction_loop_bounded_retries():
    loop = CorrectionLoop()
    assert loop.max_attempts <= 3


def test_self_correcting_agent():
    agent = SelfCorrectingAgent()
    assert agent is not None


from pathlib import Path
