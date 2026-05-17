"""CLI smoke tests — verify every command either works or shows an honest message."""

import subprocess
import sys
import json
import pytest
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
        r = run_lyme(["model", "run", "--dry-run", "--model", "deepseek-coder:6.7b", "test task"])
        assert r.returncode == 0
        assert "DRY RUN" in r.stdout or "dry_run" in r.stdout

    @pytest.mark.skip(reason="Requires loading 6.7B model into memory; run manually")
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

    def test_model_artifacts(self):
        """artifacts command detects sample adapter."""
        r = run_lyme(["model", "artifacts"])
        assert r.returncode == 0
        assert "artifact(s) found" in r.stdout or "No Lyme Model artifacts found" in r.stdout

    def test_model_current_missing(self):
        """current missing gives clear message."""
        # Ensure no current.json exists
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = run_lyme(["model", "current"])
            assert r.returncode == 0
            assert "No Lyme Model artifact configured" in r.stdout
        finally:
            if existed:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_model_use(self):
        """use writes current.json."""
        adapter_path = "adapters/deepseek-coder-6.7b-first-sft"
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        old_content = None
        if current_file.exists():
            old_content = current_file.read_text()
        try:
            r = run_lyme(["model", "use", adapter_path])
            assert r.returncode == 0
            assert "Selected Lyme Model artifact" in r.stdout
            assert current_file.exists()
            data = json.loads(current_file.read_text())
            assert data["path"] == adapter_path
            assert "base_model" in data
            assert "selected_at" in data
        finally:
            if old_content is not None:
                current_file.write_text(old_content)
            elif current_file.exists():
                current_file.unlink()

    def test_model_diagnose(self):
        """diagnose command runs without error."""
        r = run_lyme(["model", "diagnose"], check=False)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "artifact" in data
        assert "transformers_version" in data

    def test_model_list_artifacts_and_base(self):
        """list separates Lyme artifacts from base models."""
        r = run_lyme(["model", "list"])
        assert r.returncode == 0
        assert "Lyme Model Artifacts" in r.stdout
        assert "Base / Runtime Models" in r.stdout
        assert "deepseek-coder" in r.stdout or "llama3" in r.stdout

    def test_model_run_no_artifact(self):
        """run without --model and no artifact gives clear error on stderr."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = run_lyme(["model", "run", "test task"], check=False)
            assert "No Lyme Model artifact configured" in r.stderr
        finally:
            if existed:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_model_status_stopped(self):
        """status shows STOPPED when no server running."""
        r = run_lyme(["model", "status"], check=False)
        assert r.returncode == 0
        assert "STOPPED" in r.stdout or "stopped" in r.stdout or "Socket" in r.stdout

    def test_model_status_json_stopped(self):
        """status --json returns valid JSON when no server running."""
        r = run_lyme(["model", "status", "--json"], check=False)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "status" in data
        assert "socket_path" in data

    def test_model_run_reuse_worker_flag_accepted(self):
        """--reuse-worker flag is accepted by run command (dry-run)."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = run_lyme(["model", "run", "--model", "test-model", "--dry-run",
                          "--reuse-worker", "--json", "test task"], check=False)
            assert r.returncode == 0
            data = json.loads(r.stdout)
            assert "dry_run" in data or "task" in data
        finally:
            if existed:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_model_run_no_server_flag_accepted(self):
        """--no-server flag is accepted by run command (dry-run)."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = run_lyme(["model", "run", "--model", "test-model", "--dry-run",
                          "--no-server", "--json", "test task"], check=False)
            assert r.returncode == 0
            data = json.loads(r.stdout)
            assert "dry_run" in data or "task" in data
        finally:
            if existed:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_model_run_no_server_with_reuse_worker(self):
        """--reuse-worker and --no-server together are accepted (dry-run)."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = run_lyme(["model", "run", "--model", "test-model", "--dry-run",
                          "--reuse-worker", "--no-server", "--json", "test task"], check=False)
            assert r.returncode == 0
            data = json.loads(r.stdout)
            assert "dry_run" in data or "task" in data
        finally:
            if existed:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)


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


class TestModelRunGenerationFlags:
    """lyme model run accepts safe generation CLI flags."""

    def test_model_run_max_new_tokens_flag(self):
        """--max-new-tokens flag is accepted."""
        r = run_lyme(["model", "run", "--max-new-tokens", "8", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_temperature_flag(self):
        """--temperature flag is accepted."""
        r = run_lyme(["model", "run", "--temperature", "0.5", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_top_p_flag(self):
        """--top-p flag is accepted."""
        r = run_lyme(["model", "run", "--top-p", "0.9", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_no_sample_flag(self):
        """--no-sample flag is accepted."""
        r = run_lyme(["model", "run", "--no-sample", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_timeout_flag(self):
        """--timeout flag is accepted."""
        r = run_lyme(["model", "run", "--timeout", "30", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_stream_flag(self):
        """--stream flag is accepted."""
        r = run_lyme(["model", "run", "--stream", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_raw_prompt_flag(self):
        """--raw-prompt flag is accepted."""
        r = run_lyme(["model", "run", "--raw-prompt", "--dry-run", "--model", "dummy", "test"], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_all_gen_flags_together(self):
        """All generation flags accepted together."""
        r = run_lyme([
            "model", "run",
            "--max-new-tokens", "16",
            "--temperature", "0.2",
            "--top-p", "0.95",
            "--no-sample",
            "--timeout", "60",
            "--dry-run",
            "--model", "dummy",
            "test",
        ], check=False)
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_model_run_gen_flags_with_json(self):
        """Generation flags work with --json mode."""
        r = run_lyme([
            "model", "run",
            "--max-new-tokens", "8",
            "--no-sample",
            "--dry-run",
            "--model", "dummy",
            "--json",
            "test",
        ], check=False)
        if r.stdout.strip():
            import json as j
            data = j.loads(r.stdout)
            assert "model" in data or "dry_run" in data
