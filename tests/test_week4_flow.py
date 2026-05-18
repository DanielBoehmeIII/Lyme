"""Tests for Phase 11 Week 4 — Zero-Friction Workflow."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_intent_inferrer_exact_command():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("lyme heal")
    assert intent.command == "lyme heal"
    assert intent.confidence == 1.0


def test_intent_inferrer_short_alias():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("h")
    assert intent.command == "lyme heal"
    assert intent.confidence == 0.95


def test_intent_inferrer_keyword():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("fix the broken tests")
    assert "fix" in intent.command or "heal" in intent.command
    assert intent.confidence >= 0.7


def test_intent_inferrer_natural_language():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("what is this repo about")
    assert intent.command == "lyme ask"
    assert intent.confidence >= 0.7


def test_intent_inferrer_multi_keyword():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("check the status of my session")
    assert intent.command is not None
    assert intent.confidence >= 0.5


def test_intent_inferrer_unknown():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("xyzzy")
    assert intent.command is not None


def test_intent_to_dict():
    from lyme.flow.inference import InferredIntent
    intent = InferredIntent(command="lyme heal", confidence=0.9, original_input="fix it")
    d = intent.to_dict()
    assert d["command"] == "lyme heal"
    assert d["confidence"] == 0.9


def test_suggestions_provides_items():
    from lyme.flow.suggestions import ContextualSuggestions
    import tempfile
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    try:
        suggester = ContextualSuggestions()
        suggestions = suggester.get_suggestions(max_items=3)
        assert len(suggestions) >= 1
        assert all("command" in s for s in suggestions)
        assert all("label" in s for s in suggestions)
    finally:
        os.chdir(old)


def test_suggestions_print():
    from lyme.flow.suggestions import contextual_suggestions
    import tempfile
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    try:
        # Should not crash
        contextual_suggestions.print_suggestions()
    finally:
        os.chdir(old)


def test_nl_executor_suggest():
    from lyme.flow.execute import NaturalLanguageExecutor
    executor = NaturalLanguageExecutor()
    intent = executor.suggest_execution("fix the tests")
    assert intent.command is not None
    assert intent.confidence >= 0


def test_intent_inferrer_continue_alias():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("continue")
    assert intent.command == "lyme continue"


def test_intent_inferrer_start_alias():
    from lyme.flow.inference import IntentInferrer
    inferrer = IntentInferrer()
    intent = inferrer.infer("start")
    assert intent.command == "lyme start"


def test_cli_infer_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "infer", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_infer_natural():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "infer", "fix", "the", "tests"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "Intent" in result.stdout or "fix" in result.stdout or "heal" in result.stdout


def test_cli_suggest():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "suggest"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
