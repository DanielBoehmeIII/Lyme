"""Tests for Phase 11 Week 5 — Trust Through Predictability."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _isolate():
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/predictability")
    return td, old


def test_engine_create_plan():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        steps = [
            {"description": "Run tests", "command": "echo ok", "expected": "pass"},
            {"description": "Check coverage", "command": "echo done", "expected": "pass"},
        ]
        plan = engine.create_plan("Test the project", steps)
        assert plan.plan_id is not None
        assert len(plan.steps) == 2
        assert plan.goal == "Test the project"
    finally:
        os.chdir(old)


def test_engine_execute_step():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        steps = [{"description": "Say hello", "command": "echo hello", "expected": "hello"}]
        plan = engine.create_plan("Greet", steps)
        step = engine.execute_step("step_1")
        assert step.status == "passed"
    finally:
        os.chdir(old)


def test_engine_execute_all():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        steps = [
            {"description": "Step 1", "command": "echo one", "expected": "one"},
            {"description": "Step 2", "command": "echo two", "expected": "two"},
        ]
        engine.create_plan("Two steps", steps)
        result = engine.execute_all()
        assert result.status == "completed"
        assert all(s.status == "passed" for s in result.steps)
    finally:
        os.chdir(old)


def test_engine_plan_progress():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        steps = [{"description": "Step 1", "command": "echo ok", "expected": "ok"}]
        engine.create_plan("Progress", steps)
        status = engine.plan_status()
        assert status["progress"] == 0.0
        assert status["status"] == "planned"
        engine.execute_step("step_1")
        status = engine.plan_status()
        assert status["progress"] == 100.0
    finally:
        os.chdir(old)


def test_engine_reproducibility():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        steps = [{"description": "Test", "command": "echo ok", "expected": "ok"}]
        plan = engine.create_plan("Repro test", steps)
        result = engine.verify_reproducibility(plan.plan_id)
        assert "error" not in result
        assert result["plan_id"] == plan.plan_id
    finally:
        os.chdir(old)


def test_engine_list_plans():
    from lyme.predictability.engine import PredictabilityEngine
    td, old = _isolate()
    try:
        engine = PredictabilityEngine()
        plans = engine.list_plans()
        assert isinstance(plans, list)
        assert len(plans) == 0
        steps = [{"description": "Test", "command": "echo ok", "expected": "ok"}]
        engine.create_plan("List test", steps)
        plans = engine.list_plans()
        assert len(plans) == 1
        assert "List test" in plans[0]["goal"]
    finally:
        os.chdir(old)


def test_preview_no_changes():
    from lyme.predictability.preview import create_preview
    td, old = _isolate()
    try:
        subprocess.run(["git", "init"], capture_output=True, cwd=td)
        preview = create_preview()
        assert preview.files_changed == 0
    finally:
        os.chdir(old)


def test_preview_with_changes():
    from lyme.predictability.preview import create_preview
    td, old = _isolate()
    try:
        subprocess.run(["git", "init"], capture_output=True, cwd=td)
        subprocess.run(["git", "config", "user.email", "t@t.com"], capture_output=True, cwd=td)
        subprocess.run(["git", "config", "user.name", "T"], capture_output=True, cwd=td)
        Path(td, "test.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], capture_output=True, cwd=td)
        subprocess.run(["git", "commit", "-m", "init"], capture_output=True, cwd=td)
        Path(td, "test.py").write_text("x = 2\n")
        preview = create_preview()
        assert preview.files_changed >= 1
        assert preview.total_insertions >= 0
    finally:
        os.chdir(old)


def test_confidence_explainer():
    from lyme.predictability.explain import ConfidenceExplainer
    explainer = ConfidenceExplainer()
    plan = {
        "steps": [
            {"status": "passed", "description": "Step 1"},
            {"status": "pending", "description": "Step 2"},
        ],
        "reproducibility_hash": "abc123",
        "environment": {"python": "3.12", "git": "main"},
    }
    explanation = explainer.explain(plan)
    assert explanation.overall > 0
    assert explanation.verdict in ("high_confidence", "moderate_confidence", "low_confidence")
    assert len(explanation.factors) >= 3
    md = explanation.to_markdown()
    assert "Confidence" in md


def test_confidence_explainer_empty():
    from lyme.predictability.explain import ConfidenceExplainer
    explainer = ConfidenceExplainer()
    plan = {"steps": []}
    explanation = explainer.explain(plan)
    assert explanation.overall >= 0


def test_cli_predictable_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "predictable", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_predictable_preview():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "predictable", "preview"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_predictable_plan_status():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "predictable", "plan", "status"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_predictable_plan_list():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "predictable", "plan", "list"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
