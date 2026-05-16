"""CLI smoke tests — verify every command either works or shows an honest message."""

import subprocess
import sys
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_lyme(args, check=True):
    cmd = [sys.executable, "-m", "lyme"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if check and result.returncode != 0:
        print(f"STDERR: {result.stderr[:500]}")
        print(f"STDOUT: {result.stdout[:500]}")
    return result


class TestHelpCommands:
    def test_help(self):
        r = run_lyme(["--help"])
        assert r.returncode == 0
        assert "Commands" in r.stdout

    def test_version(self):
        r = run_lyme(["--version"])
        assert r.returncode == 0

    def test_no_args_shows_help(self):
        r = run_lyme([], check=False)
        # No args should show help or error, not crash
        assert r.returncode == 0


class TestModelCommands:
    def test_model_help(self):
        r = run_lyme(["model", "--help"])
        assert r.returncode == 0
        assert "subcommands" in r.stdout or "positional" in r.stdout or "ask" in r.stdout

    def test_model_hardware(self):
        r = run_lyme(["model", "hardware"])
        assert r.returncode == 0
        assert "cpu" in r.stdout or "hardware" in r.stdout

    def test_model_context(self):
        r = run_lyme(["model", "context"])
        assert r.returncode == 0
        assert "Repository:" in r.stdout or "repo_summary" in r.stdout

    def test_model_context_json(self):
        r = run_lyme(["model", "context", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "repo_summary" in data

    def test_model_summary(self):
        r = run_lyme(["model", "summary"])
        assert r.returncode == 0
        assert "Repository:" in r.stdout or "repo" in r.stdout.lower()

    def test_model_ask(self):
        r = run_lyme(["model", "ask", "What language is this?"])
        assert r.returncode == 0
        assert "Domain:" in r.stdout or "supported" in r.stdout

    def test_model_plan(self):
        r = run_lyme(["model", "plan", "fix the tests"], check=False)
        # Plan may or may not succeed but should not crash
        assert "Error" not in r.stderr[:200] or "Error: Task" in r.stderr[:200]

    def test_model_run_dry_run(self):
        r = run_lyme(["model", "run", "--dry-run", "test task"])
        assert r.returncode == 0
        assert "DRY RUN" in r.stdout or "dry_run" in r.stdout

    def test_model_compare(self):
        r = run_lyme(["model", "compare"])
        assert r.returncode == 0

    def test_model_modes(self):
        r = run_lyme(["model", "modes"])
        assert r.returncode == 0

    def test_model_fix_dry_run(self):
        r = run_lyme(["model", "fix", "--dry-run", "--no-test-run", "fix something"])
        assert r.returncode == 0
        assert "FIX DRY RUN" in r.stdout or "dry_run" in r.stdout

    def test_model_fix_dry_run_json(self):
        r = run_lyme(["model", "fix", "--dry-run", "--no-test-run", "fix tests", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "intended_prompt" in data
        assert "likely_files" in data

    def test_model_tests_detect(self):
        r = run_lyme(["model", "tests", "detect"])
        assert r.returncode == 0
        assert "Test commands found" in r.stdout or "pytest" in r.stdout

    def test_model_tests_detect_json(self):
        r = run_lyme(["model", "tests", "detect", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "detected_commands" in data
        assert "recommended" in data

    def test_model_profile(self):
        r = run_lyme(["model", "profile"])
        assert r.returncode == 0
        assert "LYME MODEL PROFILE" in r.stdout or "CPU" in r.stdout

    def test_model_profile_json(self):
        r = run_lyme(["model", "profile", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "cpu" in data
        assert "ram" in data
        assert "os" in data

    def test_model_history(self):
        r = run_lyme(["model", "history"])
        assert r.returncode == 0

    def test_model_history_json(self):
        r = run_lyme(["model", "history", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "runs" in data

    def test_model_show_missing(self):
        r = run_lyme(["model", "show", "nonexistent-run-id"], check=False)
        assert "not found" in r.stdout

    def test_model_report(self):
        r = run_lyme(["model", "report"])
        assert r.returncode == 0
        assert "Total runs" in r.stdout or "No model runs" in r.stdout

    def test_model_report_json(self):
        r = run_lyme(["model", "report", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_runs" in data

    def test_model_locate(self):
        r = run_lyme(["model", "locate", "test command detection"])
        assert r.returncode == 0
        assert "candidates" in r.stdout or "Top file" in r.stdout

    def test_model_locate_json(self):
        r = run_lyme(["model", "locate", "test command detection", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "candidates" in data


class TestNewlyWiredCommands:
    def test_diff(self):
        r = run_lyme(["diff", "."])
        assert r.returncode == 0

    def test_diff_help(self):
        r = run_lyme(["diff", "--help"])
        assert r.returncode == 0

    def test_trace_no_id(self):
        r = run_lyme(["trace"], check=False)
        assert r.returncode == 0 or "required" in r.stderr or "run_id" in r.stdout

    def test_trace_nonexistent(self):
        r = run_lyme(["trace", "nonexistent-run-id-xyz"])
        assert "not found" in r.stdout

    def test_trace_model_run(self):
        r = run_lyme(["trace", "compare-55b816d4a6af"])
        assert r.returncode == 0
        assert "TRACE" in r.stdout

    def test_fix_dry_run(self):
        r = run_lyme(["fix", "--dry-run", "test edit"])
        assert r.returncode == 0

    def test_bench_help(self):
        r = run_lyme(["bench", "--help"])
        assert r.returncode == 0

    def test_memory_help(self):
        r = run_lyme(["memory", "--help"])
        assert r.returncode == 0

    def test_memory_list(self):
        r = run_lyme(["memory", "list"])
        assert r.returncode == 0


class TestInfoCommand:
    def test_info(self):
        r = run_lyme(["info"])
        assert r.returncode == 0
        assert "LYME PROJECT HEALTH" in r.stdout or "version" in r.stdout

    def test_info_json(self):
        r = run_lyme(["info", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "version" in data
        assert "python_version" in data
        assert "git_available" in data


class TestExistingCommands:
    def test_doctor(self):
        r = run_lyme(["doctor", "."])
        assert r.returncode == 0
        assert "Confidence" in r.stdout

    def test_doctor_json(self):
        r = run_lyme(["doctor", ".", "--format", "json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "diagnosis_confidence" in data or "confidence" in str(data.keys())

    def test_ask(self):
        r = run_lyme(["ask", "What language is this?"])
        assert r.returncode == 0
        assert "Confidence" in r.stdout

    def test_history(self):
        r = run_lyme(["history"], check=False)
        assert r.returncode == 0

    def test_semantic_diff_help(self):
        r = run_lyme(["semantic-diff", "--help"])
        assert r.returncode == 0

    def test_semantic_diff_classify(self):
        r = run_lyme(["semantic-diff", "classify"])
        assert r.returncode == 0
        assert "SEMANTIC DIFF" in r.stdout

    def test_semantic_diff_classify_json(self):
        r = run_lyme(["semantic-diff", "classify", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "intent" in data
        assert "risk" in data

    def test_govern_help(self):
        r = run_lyme(["govern", "--help"])
        assert r.returncode == 0

    def test_policy_help(self):
        r = run_lyme(["policy", "--help"])
        assert r.returncode == 0

    def test_verify_help(self):
        r = run_lyme(["verify", "--help"])
        assert r.returncode == 0

    def test_graph_help(self):
        r = run_lyme(["graph", "--help"])
        assert r.returncode == 0

    def test_discover_help(self):
        r = run_lyme(["discover", "--help"])
        assert r.returncode == 0

    def test_constitution_help(self):
        r = run_lyme(["constitution", "--help"])
        assert r.returncode == 0

    def test_research_help(self):
        r = run_lyme(["research", "--help"])
        assert r.returncode == 0
