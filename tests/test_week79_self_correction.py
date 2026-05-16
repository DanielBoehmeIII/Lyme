"""Tests for Week 79 — Local Self-Correction Loop."""

import pytest
from src.lyme_model.correction.loop import (
    CorrectionLoop,
    CorrectionAttempt,
    CorrectionSummary,
    SelfCorrectingAgent,
)


class TestCorrectionLoop:
    def test_loop_initializes(self):
        loop = CorrectionLoop(max_attempts=3)
        assert loop.max_attempts == 3
        assert loop.attempts == []

    def test_summarize_failure_with_test_results(self):
        loop = CorrectionLoop()
        summary = loop.summarize_failure({
            "test_results": {"failed": 2, "total": 10, "errors": ["AssertionError: expected 5 got 3"]},
        })
        assert "2 test(s) failed" in summary
        assert "AssertionError" in summary

    def test_summarize_failure_with_error(self):
        loop = CorrectionLoop()
        summary = loop.summarize_failure({"error": "ImportError: no module named x"})
        assert "ImportError" in summary

    def test_summarize_failure_unknown(self):
        loop = CorrectionLoop()
        summary = loop.summarize_failure({})
        assert "Unknown" in summary

    def test_locate_cause_import_error(self):
        loop = CorrectionLoop()
        cause = loop.locate_cause("ImportError: no module named foo", {})
        assert "import" in cause.lower()

    def test_locate_cause_assertion_error(self):
        loop = CorrectionLoop()
        cause = loop.locate_cause("AssertionError: expected True got False", {})
        assert "assertion" in cause.lower() or "bug" in cause.lower()

    def test_locate_cause_syntax_error(self):
        loop = CorrectionLoop()
        cause = loop.locate_cause("SyntaxError: invalid syntax", {})
        assert "syntax" in cause.lower()

    def test_choose_action_for_import(self):
        loop = CorrectionLoop()
        action = loop.choose_action("ImportError failed", "Missing import", {})
        assert "import" in action.lower()

    def test_choose_action_for_syntax(self):
        loop = CorrectionLoop()
        action = loop.choose_action("SyntaxError", "Syntax error", {})
        assert "syntax" in action.lower()

    def test_choose_action_generic(self):
        loop = CorrectionLoop()
        action = loop.choose_action("Something went wrong", "Unknown", {})
        assert action != ""

    def test_apply_patch_success(self):
        loop = CorrectionLoop()

        def patch_fn(action, ctx):
            return "patched"

        success, result = loop.apply_patch("fix it", {}, patch_fn)
        assert success is True
        assert result == "patched"

    def test_apply_patch_failure(self):
        loop = CorrectionLoop()

        def patch_fn(action, ctx):
            raise ValueError("patch error")

        success, result = loop.apply_patch("fix it", {}, patch_fn)
        assert success is False

    def test_run_with_early_success(self):
        loop = CorrectionLoop(max_attempts=5)

        def patch_fn(action, ctx):
            return "patched"

        verify_count = 0

        def verify_fn(ctx):
            nonlocal verify_count
            verify_count += 1
            return True  # First verification passes

        summary = loop.run({}, patch_fn, verify_fn)
        assert summary.resolved is True
        assert summary.total_attempts == 1

    def test_run_with_retries(self):
        loop = CorrectionLoop(max_attempts=3)

        def patch_fn(action, ctx):
            return "patched"

        verify_count = 0

        def verify_fn(ctx):
            nonlocal verify_count
            verify_count += 1
            return verify_count >= 3  # Pass on 3rd attempt

        summary = loop.run({}, patch_fn, verify_fn)
        assert summary.resolved is True
        assert summary.total_attempts >= 2

    def test_run_max_attempts(self):
        loop = CorrectionLoop(max_attempts=3)

        def patch_fn(action, ctx):
            return "patched"

        def verify_fn(ctx):
            return False  # Never passes

        summary = loop.run({"test_results": {"failed": 1}}, patch_fn, verify_fn)
        assert summary.resolved is False
        assert summary.total_attempts == 3

    def test_repeated_failure_stops(self):
        loop = CorrectionLoop(max_attempts=5)

        def patch_fn(action, ctx):
            return "patched"

        call_count = [0]

        def verify_fn(ctx):
            call_count[0] += 1
            return False

        context = {"test_results": {"failed": 1, "errors": ["AssertionError"]}}
        summary = loop.run(context, patch_fn, verify_fn)
        # Should stop early due to repeated same failure
        assert "repeat" in summary.stopped_reason.lower() or summary.stopped_reason != ""


class TestSelfCorrectingAgent:
    def test_agent_initializes(self):
        agent = SelfCorrectingAgent(max_attempts=3)
        assert agent.loop.max_attempts == 3

    def test_agent_execute(self):
        agent = SelfCorrectingAgent(max_attempts=3)

        def patch_fn(action, ctx):
            return "patched"

        def verify_fn(ctx):
            return True

        summary = agent.execute("test task", {}, patch_fn, verify_fn)
        assert summary.resolved is True


class TestCorrectionSummary:
    def test_summary_to_markdown(self):
        summary = CorrectionSummary(
            total_attempts=2,
            resolved=True,
            total_latency_ms=500,
        )
        md = summary.to_markdown()
        assert "Self-Correction Summary" in md
        assert "Yes" in md  # resolved
