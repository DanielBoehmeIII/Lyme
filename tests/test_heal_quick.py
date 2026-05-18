"""Regression tests: lyme heal --verify quick must use a small smoke command, never the full suite."""

import json
import subprocess
import sys
import pytest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_heal_quick(timeout: int = 60) -> dict:
    cmd = [
        sys.executable, "-m", "lyme", "heal",
        "--dry-run", "--json", "--verify", "quick",
        "--timeout", str(timeout),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10, cwd=REPO_ROOT)
    assert result.returncode == 0, f"heal failed:\nstdout:{result.stdout[:500]}\nstderr:{result.stderr[:500]}"
    return json.loads(result.stdout)


class TestHealQuickMode:
    def test_quick_mode_finishes_without_timeout(self):
        """quick mode must finish well within the default 60s timeout."""
        data = run_heal_quick(timeout=60)
        assert data["status"] == "complete"
        assert data["timed_out"] is False, f"quick mode timed out: {data.get('test_command', 'N/A')}"
        assert data["verification_mode"] == "quick"
        assert data["duration_s"] < 55, f"quick mode took {data['duration_s']}s — too close to 60s timeout"

    def test_quick_mode_uses_small_test_command(self):
        """quick mode must only run TestHelpCommands, never the full test_cli_smoke.py."""
        data = run_heal_quick(timeout=60)
        cmd = data.get("test_command", "")
        assert "TestHelpCommands" in cmd, f"Expected TestHelpCommands in command, got: {cmd}"
        assert "pytest" in cmd, f"Expected pytest in command, got: {cmd}"

    def test_quick_mode_json_has_required_fields(self):
        """heal --json --verify quick must include verification_mode, test_command, timed_out."""
        data = run_heal_quick(timeout=60)
        assert "verification_mode" in data, "Missing verification_mode in JSON output"
        assert "test_command" in data, "Missing test_command in JSON output"
        assert "timed_out" in data, "Missing timed_out in JSON output"
        assert data["verification_mode"] == "quick"
        assert isinstance(data["timed_out"], bool)
        assert isinstance(data["test_command"], str)
        assert len(data["test_command"]) > 0

    def test_quick_mode_does_not_collect_full_suite_issues(self):
        """quick mode should not report issues from tests outside TestHelpCommands."""
        data = run_heal_quick(timeout=60)
        for issue in data.get("issues", []):
            if issue.get("category") == "test_failure":
                pytest.fail(f"quick mode should not find test failures: {issue}")
