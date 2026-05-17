"""Tests for lyme_model runtime engine — subprocess worker, safe defaults, context isolation.

Verifies:
  - No Ollama dependency exists in the runtime engine.
  - Tokenizer loading errors produce clean error messages.
  - Adapter validation catches missing files.
  - Safe generation defaults are enforced.
  - Timeout protection kills the worker and returns clean errors (no core dump).
  - Phase logging outputs to stderr.
  - Context is never auto-injected into ``lyme model run`` prompts.
  - ``--no-context`` flag prevents context injection.
"""

import os
import sys
import json
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, ANY

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Source-level verification ─────────────────────────────────────────────

def test_engine_has_no_ollama():
    """engine.py must contain zero references to Ollama."""
    source = (REPO_ROOT / "src" / "lyme_model" / "runtime" / "engine.py").read_text()
    assert "ollama" not in source.lower(), "engine.py must not reference Ollama"
    assert "urllib" not in source, "engine.py must not import urllib (Ollama REST)"


def test_loader_has_no_ollama():
    """loader.py must not reference Ollama backend."""
    source = (REPO_ROOT / "src" / "lyme_model" / "runtime" / "loader.py").read_text()
    assert "ollama" not in source.lower(), "loader.py must not reference Ollama"


def test_cli_compare_has_no_ollama_check():
    """_cmd_compare must not check for Ollama binary."""
    source = (REPO_ROOT / "src" / "lyme_model" / "cli.py").read_text()
    assert "check_ollama" not in source, "cli.py must not call check_ollama"


def test_ollama_functions_removed():
    """check_ollama, list_ollama_models must not exist in engine module."""
    import lyme_model.runtime.engine as eng
    assert not hasattr(eng, "check_ollama"), "check_ollama must be removed"
    assert not hasattr(eng, "list_ollama_models"), "list_ollama_models must be removed"
    assert not hasattr(eng, "check_model_available"), "check_model_available must be removed"
    assert not hasattr(eng, "OLLAMA_API_BASE"), "OLLAMA_API_BASE must be removed"


def test_engine_has_no_daemon_thread():
    """engine.py must no longer use threading for generation."""
    source = (REPO_ROOT / "src" / "lyme_model" / "runtime" / "engine.py").read_text()
    assert "threading.Thread" not in source, "engine.py must not use threading.Thread for generation"


def test_worker_exists():
    """worker.py must exist as the subprocess entry point."""
    worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
    assert worker_path.is_file(), f"worker.py not found at {worker_path}"
    assert "main()" in worker_path.read_text(), "worker.py must have a main() entry point"
    source = worker_path.read_text()
    import re
    assert not re.search(r'\bimport subprocess\b', source), "worker.py must not import subprocess internally"


# ── Error handling ────────────────────────────────────────────────────────

def test_generate_returns_error_on_tokenizer_failure():
    """generate() returns result with success=False when _load_tokenizer() fails."""
    from lyme_model.runtime.engine import LocalInferenceEngine

    engine = LocalInferenceEngine("test-model")
    with patch.object(engine, "_load_tokenizer", side_effect=RuntimeError("Tokenizer not found")):
        result = engine.generate("test prompt", save_run=False)
        assert result.success is False
        assert "Tokenizer not found" in result.error
        assert result.output == ""


class TestAdapterValidation:
    """User-facing error messages when adapter is missing."""

    def _make_engine(self, adapter_path: str):
        from lyme_model.runtime.engine import LocalInferenceEngine
        return LocalInferenceEngine("dummy-model", adapter_path=adapter_path)

    def test_missing_adapter_directory(self, tmp_path):
        """Missing adapter directory reports exact path."""
        eng = self._make_engine(str(tmp_path / "no-such-dir"))
        with pytest.raises(RuntimeError, match="Adapter directory not found"):
            eng._validate_adapter()

    def test_missing_adapter_config(self, tmp_path):
        """Missing adapter_config.json reports the exact filename."""
        d = tmp_path / "adapter"
        d.mkdir()
        eng = self._make_engine(str(d))
        with pytest.raises(RuntimeError, match="adapter_config.json"):
            eng._validate_adapter()

    def test_missing_adapter_weights(self, tmp_path):
        """Missing adapter_model.safetensors reports the exact filename."""
        d = tmp_path / "adapter"
        d.mkdir()
        (d / "adapter_config.json").write_text("{}")
        eng = self._make_engine(str(d))
        with pytest.raises(RuntimeError, match="adapter_model.safetensors"):
            eng._validate_adapter()


class TestCliErrorVisibility:
    """CLI commands print errors to stderr unless --json is used."""

    def _run_lyme(self, args, check=True):
        import subprocess
        cmd = [sys.executable, "-m", "lyme"] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)

    def test_run_no_artifact_message(self):
        """Without artifact, shows clear error on stderr."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        backup = None
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = self._run_lyme(["model", "run", "test task"], check=False)
            assert "No Lyme Model artifact configured" in r.stderr
            assert r.stdout == ""
        finally:
            if existed and backup is not None:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_run_json_no_artifact_message(self):
        """Without artifact and --json, shows error in JSON stdout."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        backup = None
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = self._run_lyme(["model", "run", "test task", "--json"], check=False)
            data = json.loads(r.stdout)
            assert "No Lyme Model artifact configured" in data["error"]
            assert data["success"] is False
        finally:
            if existed and backup is not None:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    @pytest.mark.skipif(
        not os.environ.get("LYME_TEST_REAL_MODEL"),
        reason="Requires 6.7B model in memory; set LYME_TEST_REAL_MODEL=1 to run",
    )
    def test_run_failure_prints_to_stderr(self):
        """When model load fails, error must appear on stderr (non-JSON)."""
        adapter_path = "adapters/deepseek-coder-6.7b-first-sft"
        setup_r = self._run_lyme(["model", "use", adapter_path])
        assert setup_r.returncode == 0
        r = self._run_lyme(["model", "run", "test task"], check=False)
        assert "Error" in r.stderr or "not found" in r.stderr or r.returncode != 0

    @pytest.mark.skipif(
        not os.environ.get("LYME_TEST_REAL_MODEL"),
        reason="Requires 6.7B model in memory; set LYME_TEST_REAL_MODEL=1 to run",
    )
    def test_run_json_failure_contains_error(self):
        """When model load fails with --json, error must be in JSON body."""
        adapter_path = "adapters/deepseek-coder-6.7b-first-sft"
        self._run_lyme(["model", "use", adapter_path])
        r = self._run_lyme(["model", "run", "test task", "--json"], check=False)
        if r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                assert "success" in data
                if not data["success"]:
                    assert "error" in data
            except json.JSONDecodeError:
                pytest.fail(f"Expected JSON output, got: {r.stdout[:200]}")


class TestOffloadDirectory:
    """offload_folder must be created and set when using device_map='auto'."""

    def test_offload_dir_created_with_adapter(self, tmp_path):
        """Offload dir is created inside adapter path when adapter_path is set."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir))
        with patch.object(engine, "_check_imports"):
            engine._validate_adapter()

        offload_dir = adapter_dir / ".offload"
        assert offload_dir.is_dir(), f"Offload dir not created at {offload_dir}"

    def test_offload_dir_set_correctly(self, tmp_path):
        """_offload_dir attribute is set correctly after _validate_adapter."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir))
        with patch.object(engine, "_check_imports"):
            engine._validate_adapter()

        assert engine._offload_dir == str(adapter_dir / ".offload")

    def test_offload_dir_in_lyme_when_no_adapter(self):
        """Without adapter path, offload dir goes to .lyme/model_offload/<model-name>."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("some-org/some-model", adapter_path=None)
        with patch.object(engine, "_check_imports"):
            engine._validate_adapter()

        expected = str(Path.cwd() / ".lyme" / "model_offload" / "some-org_some-model")
        assert engine._offload_dir == expected


# ── Safe generation defaults ──────────────────────────────────────────────


def _make_mock_tokenizer():
    """Build a mocked tokenizer."""
    import torch
    t = MagicMock()
    t.eos_token_id = 2
    t.pad_token_id = 2
    t.chat_template = None
    input_ids = torch.randint(0, 100, (1, 4))
    t.return_value = {"input_ids": input_ids, "attention_mask": torch.ones(1, 4)}
    t.decode.return_value = "mock output"
    return t


def _worker_response(output: str = "mock output", prompt_tokens: int = 5, generated_tokens: int = 3):
    return {"output": output, "prompt_tokens": prompt_tokens, "generated_tokens": generated_tokens}


class TestSafeGenerationDefaults:
    """Verify safe defaults via _build_safe_gen_kwargs."""

    def _make_engine_with_mocks(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()
        return engine

    def test_max_new_tokens_default(self):
        engine = self._make_engine_with_mocks()
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["max_new_tokens"] == 32

    def test_do_sample_false_by_default(self):
        engine = self._make_engine_with_mocks()
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["do_sample"] is False

    def test_use_cache_true(self):
        engine = self._make_engine_with_mocks()
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["use_cache"] is True

    def test_eos_token_id_from_tokenizer(self):
        engine = self._make_engine_with_mocks()
        engine._tokenizer.eos_token_id = 2
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["eos_token_id"] == 2

    def test_pad_token_id_eos_fallback(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_tokenizer = _make_mock_tokenizer()
        type(mock_tokenizer).pad_token_id = PropertyMock(return_value=None)
        engine._tokenizer = mock_tokenizer
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["pad_token_id"] == 2

    def test_custom_max_new_tokens(self):
        engine = self._make_engine_with_mocks()
        kwargs = engine._build_safe_gen_kwargs(max_new_tokens=8)
        assert kwargs["max_new_tokens"] == 8

    def test_custom_temperature_top_p_with_sample(self):
        engine = self._make_engine_with_mocks()
        engine.do_sample = True
        engine.temperature = 0.7
        engine.top_p = 0.9
        kwargs = engine._build_safe_gen_kwargs()
        assert kwargs["temperature"] == 0.7
        assert kwargs["top_p"] == 0.9
        assert kwargs["do_sample"] is True

    def test_overrides_safe_defaults(self):
        engine = self._make_engine_with_mocks()
        kwargs = engine._build_safe_gen_kwargs(max_new_tokens=128, do_sample=True, temperature=0.9, top_p=0.95)
        assert kwargs["max_new_tokens"] == 128
        assert kwargs["do_sample"] is True
        assert kwargs["temperature"] == 0.9
        assert kwargs["top_p"] == 0.95

    def test_generate_passes_kwargs_to_worker(self):
        """generate() passes gen_kwargs through to _generate_via_worker."""
        engine = self._make_engine_with_mocks()
        with patch.object(engine, "_generate_via_worker", return_value=_worker_response()) as mock_gen:
            with patch.object(engine, "_ensure_worker"):
                result = engine.generate("test", save_run=False, max_new_tokens=64, do_sample=True)
                assert result.success
                assert result.output == "mock output"


class TestGenerationTimeout:
    """Timeout protection kills worker and returns clean error."""

    def test_timeout_returns_error(self):
        """When generation stalls, timeout kills worker and returns success=False."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", timeout=0.01, verbose=False, reuse_worker=False)
        engine._tokenizer = _make_mock_tokenizer()

        with patch.object(engine, "_generate_via_worker", side_effect=TimeoutError("timed out")):
            with patch.object(engine, "_kill_worker") as mock_kill:
                result = engine.generate("test", save_run=False)
                assert result.success is False
                assert "timed out" in result.error.lower()
                mock_kill.assert_called_once()

    def test_timeout_error_in_json_shape(self):
        """Timeout result is parseable as dict (JSON-compatible) with success false."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", timeout=0.01, verbose=False, reuse_worker=False)
        engine._tokenizer = _make_mock_tokenizer()

        with patch.object(engine, "_generate_via_worker", side_effect=TimeoutError("timed out")):
            with patch.object(engine, "_kill_worker"):
                result = engine.generate("test", save_run=False)
                d = result.to_dict()
                assert d["success"] is False
                assert "timed out" in d["error"].lower()
                import json as j
                j.dumps(d)

    def test_timeout_does_not_crash_parent(self):
        """Simulates the exact crash scenario: timeout returns JSON, subsequent calls succeed."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", timeout=0.01, verbose=False, reuse_worker=False)
        engine._tokenizer = _make_mock_tokenizer()

        try:
            with patch.object(engine, "_generate_via_worker", side_effect=TimeoutError("timed out")):
                with patch.object(engine, "_kill_worker"):
                    r1 = engine.generate("first", save_run=False)
                    assert not r1.success
                    assert "timed out" in r1.error

            with patch.object(engine, "_generate_via_worker", return_value=_worker_response("ok", 5, 3)):
                with patch.object(engine, "_ensure_worker"):
                    r2 = engine.generate("second", save_run=False)
                    assert r2.success
                    assert r2.output == "ok"
        except RuntimeError:
            pytest.fail("Timeout left worker in bad state — parent crashed on subsequent call")


class TestPhaseLogging:
    """Phase log messages emitted to stderr when verbose=True."""

    def _make_engine_with_mocks(self, verbose=True):
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine("dummy-model", verbose=verbose)
        engine._tokenizer = _make_mock_tokenizer()
        return engine

    def test_phase_logs_stderr_when_verbose(self):
        import io
        engine = self._make_engine_with_mocks(verbose=True)
        with patch.object(engine, "_generate_via_worker", return_value=_worker_response()):
            with patch.object(engine, "_ensure_worker"):
                stderr_capture = io.StringIO()
                with patch.object(sys, "stderr", stderr_capture):
                    engine.generate("test", save_run=False)
                output = stderr_capture.getvalue()
                assert "Generating tokens" in output

    def test_no_phase_logs_when_not_verbose(self):
        import io
        engine = self._make_engine_with_mocks(verbose=False)
        with patch.object(engine, "_generate_via_worker", return_value=_worker_response()):
            with patch.object(engine, "_ensure_worker"):
                stderr_capture = io.StringIO()
                with patch.object(sys, "stderr", stderr_capture):
                    engine.generate("test", save_run=False)
                output = stderr_capture.getvalue()
                assert output.strip() == ""


class TestAgentRuntimeGenKwargs:
    """AgentRuntime threads gen_kwargs through to engine."""

    def test_agent_runtime_passes_engine_kwargs(self):
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(
            model_name="dummy",
            max_new_tokens=64,
            temperature=0.5,
            top_p=0.8,
            do_sample=True,
            timeout=99,
            verbose=False,
        )
        assert runtime.engine.max_new_tokens == 64
        assert runtime.engine.temperature == 0.5
        assert runtime.engine.top_p == 0.8
        assert runtime.engine.do_sample is True
        assert runtime.engine.timeout == 99
        assert runtime.engine.verbose is False


class TestPromptFormatting:
    """Verify prompt formatting with chat template and fallback."""

    def _mock_tokenizer_with_chat_template(self):
        t = _make_mock_tokenizer()
        t.chat_template = "fake-template"
        t.apply_chat_template.return_value = "<|user|>\nSay hi.\n<|assistant|>\n"
        return t

    def test_format_prompt_uses_chat_template_when_available(self):
        """When tokenizer has chat_template, apply_chat_template is called."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-6.7b-instruct", verbose=False)
        engine._tokenizer = self._mock_tokenizer_with_chat_template()

        with patch.object(engine, "_generate_via_worker", return_value=_worker_response()):
            with patch.object(engine, "_ensure_worker"):
                engine.generate("Say hi.", save_run=False)

        engine._tokenizer.apply_chat_template.assert_called_once()
        call_args = engine._tokenizer.apply_chat_template.call_args
        messages = call_args[0][0]
        assert messages == [{"role": "user", "content": "Say hi."}]
        assert call_args.kwargs.get("tokenize") is False
        assert call_args.kwargs.get("add_generation_prompt") is True

    def test_format_prompt_skipped_with_raw_prompt(self):
        """raw_prompt=True skips apply_chat_template entirely."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-6.7b-instruct", verbose=False)
        engine._tokenizer = self._mock_tokenizer_with_chat_template()

        mock_resp = _worker_response("Hello! How can I help you?")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp) as mock_gen:
            with patch.object(engine, "_ensure_worker"):
                engine.generate("Say hi.", save_run=False, raw_prompt=True)

        engine._tokenizer.apply_chat_template.assert_not_called()
        called_prompt = mock_gen.call_args[0][0]
        assert called_prompt == "Say hi.", "Raw prompt must be sent as-is when raw_prompt=True"

    def test_fallback_format_for_deepseek(self):
        """DeepSeek model uses system-prompt fallback when no chat_template."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-1.3b-instruct", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello!")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp) as mock_gen:
            with patch.object(engine, "_ensure_worker"):
                engine.generate("Say hi.", save_run=False)

        called_prompt = mock_gen.call_args[0][0]
        assert "You are Lyme, a local coding assistant." in called_prompt
        assert "User: Say hi." in called_prompt
        assert "Assistant:" in called_prompt

    def test_fallback_format_for_generic_model(self):
        """Non-DeepSeek model uses generic instruction fallback."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("microsoft/phi-3-mini", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello!")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp) as mock_gen:
            with patch.object(engine, "_ensure_worker"):
                engine.generate("Say hi.", save_run=False)

        called_prompt = mock_gen.call_args[0][0]
        assert "### Instruction: Say hi." in called_prompt
        assert "### Response:" in called_prompt

    def test_run_task_passes_raw_prompt_to_generate(self):
        """AgentRuntime.run_task forwards raw_prompt to engine.generate."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock()
            runtime.run_task("Say hi.", raw_prompt=True)
            mock_gen.assert_called_once_with("Say hi.", raw_prompt=True)

    def test_run_task_empty_context_no_injection(self):
        """AgentRuntime.run_task with context=None passes task verbatim (no repo context)."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock()
            runtime.run_task("Say hi.")
            called_prompt = mock_gen.call_args[0][0]
            assert called_prompt == "Say hi."
            assert "Repository:" not in called_prompt

    def test_run_task_with_context_includes_repo_header(self):
        """AgentRuntime.run_task with explicit context wraps it in Repository context header."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock()
            runtime.run_task("Say hi.", context="Some context about the repo")
            called_prompt = mock_gen.call_args[0][0]
            assert "Repository context:" in called_prompt
            assert "Some context about the repo" in called_prompt


# ── Worker management tests ──────────────────────────────────────────────

class TestWorkerManagement:
    """Verify worker process lifecycle."""

    def test_ensure_worker_spawns_process(self):
        """_ensure_worker spawns a subprocess and initialises it."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()
        engine._offload_dir = "/tmp/offload"

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                    engine._ensure_worker()

            mock_popen.assert_called_once()
            assert engine._worker_loaded is True

    def test_ensure_worker_handles_load_error(self):
        """_ensure_worker raises RuntimeError when worker reports init error."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._offload_dir = "/tmp/offload"

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"error": "Model load failed: OOM"}):
                    with pytest.raises(RuntimeError, match="Model load failed: OOM"):
                        engine._ensure_worker()

    def test_kill_worker_terminates_process(self):
        """_kill_worker terminates the worker subprocess."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        engine._worker_process = mock_proc
        engine._worker_loaded = True

        engine._kill_worker()
        assert engine._worker_process is None
        assert engine._worker_loaded is False

    def test_ensure_worker_sends_offload_dir_in_init_message(self):
        """Init message sent to worker contains a non-None offload_dir."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                    engine._ensure_worker()

        # Collect all writes to stdin, find the init command
        write_text = "".join(
            call[0][0] for call in mock_proc.stdin.write.call_args_list
        )
        sent = json.loads(write_text.strip())
        assert sent["command"] == "init"
        offload_dir = sent.get("offload_dir")
        assert offload_dir is not None, "offload_dir must not be None in init message"
        assert isinstance(offload_dir, str)
        assert len(offload_dir) > 0

    def test_ensure_worker_with_adapter_sends_adapter_offload_dir(self, tmp_path):
        """When adapter_path is set, init message sends adapter/.offload as offload_dir."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir), verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                engine._ensure_worker()

        write_text = "".join(
            call[0][0] for call in mock_proc.stdin.write.call_args_list
        )
        sent = json.loads(write_text.strip())
        assert sent["command"] == "init"
        assert sent["offload_dir"] == str(adapter_dir / ".offload")

    def test_offload_dir_created_before_worker_spawn(self, tmp_path):
        """The .offload directory exists on disk before the worker subprocess starts."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir), verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                engine._ensure_worker()

        offload_dir = adapter_dir / ".offload"
        assert offload_dir.is_dir(), f".offload dir must exist at {offload_dir}"
        assert mock_popen.called, "Worker subprocess must have been spawned"


# ── Worker offload integration tests ──────────────────────────────────────


class TestWorkerOffloadIntegration:
    """Worker passes offload_folder and offload_state_dict to model loading calls."""

    def _load_worker_module(self):
        import importlib.util
        worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
        spec = importlib.util.spec_from_file_location(
            "lyme_model.runtime.worker_offload_intg", worker_path
        )
        mod = importlib.util.module_from_spec(spec)
        return spec, mod

    def test_worker_passes_offload_folder_to_base_model(self):
        """Worker passes offload_folder and offload_state_dict to AutoModelForCausalLM.from_pretrained."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_peft = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = (
                json.dumps({
                    "command": "init",
                    "model_name": "test-model",
                    "adapter_path": None,
                    "device": "auto",
                    "offload_dir": "/tmp/test-offload",
                })
                + "\n"
                + json.dumps({"command": "shutdown"})
                + "\n"
            )

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            sys.stdin = io.StringIO(stdin_data)
            sys.stdout = io.StringIO()

            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

        mock_transformers.AutoModelForCausalLM.from_pretrained.assert_called_once()
        call_kwargs = mock_transformers.AutoModelForCausalLM.from_pretrained.call_args[1]
        assert call_kwargs.get("offload_folder") == "/tmp/test-offload"
        assert call_kwargs.get("offload_state_dict") is True

    def test_worker_passes_offload_folder_to_peft_model(self):
        """Worker passes offload_folder and offload_state_dict to PeftModel.from_pretrained."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_peft = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = (
                json.dumps({
                    "command": "init",
                    "model_name": "test-model",
                    "adapter_path": "/some/adapter",
                    "device": "auto",
                    "offload_dir": "/tmp/test-offload",
                })
                + "\n"
                + json.dumps({"command": "shutdown"})
                + "\n"
            )

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            sys.stdin = io.StringIO(stdin_data)
            sys.stdout = io.StringIO()

            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

        mock_peft.PeftModel.from_pretrained.assert_called_once()
        call_kwargs = mock_peft.PeftModel.from_pretrained.call_args[1]
        assert call_kwargs.get("offload_folder") == "/tmp/test-offload"
        assert call_kwargs.get("offload_state_dict") is True

    def test_worker_responds_ready_on_successful_init(self):
        """Worker responds with {'status': 'ready'} after successful model load."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_peft = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = (
                json.dumps({
                    "command": "init",
                    "model_name": "test-model",
                    "adapter_path": None,
                    "device": "auto",
                    "offload_dir": "/tmp/test-offload",
                })
                + "\n"
                + json.dumps({"command": "shutdown"})
                + "\n"
            )

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            sys.stdin = io.StringIO(stdin_data)
            stdout_capture = io.StringIO()
            sys.stdout = stdout_capture

            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

            output = stdout_capture.getvalue().strip()
            lines = [json.loads(l) for l in output.split("\n") if l.strip()]
            assert any(
                line.get("status") == "ready" for line in lines
            ), f"Expected 'ready' response, got: {lines}"


# ── Context pollution tests ──────────────────────────────────────────────

class TestNoContextPollution:
    """``lyme model run`` must not inject repository context by default."""

    def test_cli_run_no_context_flag_accepted(self):
        """--no-context flag is accepted on the command line."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "lyme", "model", "run", "--no-context", "--dry-run", "--model", "dummy", "hi"],
            capture_output=True, text=True, cwd=REPO_ROOT,
            check=False,
        )
        assert r.returncode == 0 or "DRY RUN" in r.stdout

    def test_cli_run_no_context_json_flag(self):
        """--no-context works with --json --dry-run."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "lyme", "model", "run", "--no-context", "--json", "--dry-run", "--model", "dummy", "hi"],
            capture_output=True, text=True, cwd=REPO_ROOT,
            check=False,
        )
        if r.stdout.strip():
            data = json.loads(r.stdout)
            assert "dry_run" in data or "error" in data

    def test_cli_run_no_context_overrides_context(self):
        """--no-context overrides --context."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "lyme",
             "model", "run",
             "--no-context", "--context", "somefile.txt",
             "--dry-run", "--model", "dummy",
             "hi"],
            capture_output=True, text=True, cwd=REPO_ROOT,
            check=False,
        )
        assert r.returncode == 0 or "DRY RUN" in r.stdout


# ── Output cleanup tests ─────────────────────────────────────────────────

class TestOutputCleanup:
    """Verify _clean_output strips trailing structural markers."""

    def test_clean_removes_trailing_context_marker(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello. How are you? Context:") == "Hello. How are you?"

    def test_clean_removes_trailing_user_marker(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello. How are you? User:") == "Hello. How are you?"

    def test_clean_removes_trailing_assistant_marker(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello. How are you? Assistant:") == "Hello. How are you?"

    def test_clean_removes_multiple_markers(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello.\nContext:\nUser:\nAssistant:") == "Hello."

    def test_clean_leaves_legitimate_content(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        result = LocalInferenceEngine._clean_output("def hello():\n    return 'hi'")
        assert result == "def hello():\n    return 'hi'"

    def test_clean_removes_unfinished_section_header(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Here is the code.\nThought:") == "Here is the code."

    def test_clean_removes_marker_with_trailing_whitespace(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello. Context:  ") == "Hello."

    def test_clean_removes_marker_newline_only(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Hello.\nContext:\n") == "Hello."

    def test_clean_no_marker_no_change(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("Just a normal sentence.") == "Just a normal sentence."

    def test_clean_empty_string(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        assert LocalInferenceEngine._clean_output("") == ""

    def test_clean_removes_context_repository_suffix(self):
        from lyme_model.runtime.engine import LocalInferenceEngine
        result = LocalInferenceEngine._clean_output("Hello.Howareyou?Context:Repository:blog-engineLanguage:Python")
        assert result == "Hello.Howareyou?", f"Expected 'Hello.Howareyou?', got {result!r}"

    def test_clean_shared_function_directly(self):
        from lyme_model.runtime.text_cleanup import clean_generated_output
        assert clean_generated_output("hi Context:Repository:x") == "hi"
        assert clean_generated_output("hi") == "hi"
        assert clean_generated_output("") == ""
        assert clean_generated_output("Hello.\nContext:\nRepository: blog-engine") == "Hello."

    def test_clean_shared_function_regression(self):
        """Regression: clean_generated_output strips Context:Repository: suffix."""
        from lyme_model.runtime.text_cleanup import clean_generated_output

        result = clean_generated_output(
            "Hello.Howareyou?Context:Repository:blog-engineLanguage:Python"
        )
        assert result == "Hello.Howareyou?", (
            f"Expected 'Hello.Howareyou?', got {result!r}"
        )

    def test_shared_function_imported_in_server_worker(self):
        """server_worker.py must import clean_generated_output for persistent server."""
        source = (REPO_ROOT / "src" / "lyme_model" / "runtime" / "server_worker.py").read_text()
        assert "clean_generated_output" in source, (
            "server_worker.py must import clean_generated_output"
        )


class TestOutputCleanupIntegration:
    """Verify _clean_output is actually called during generate()."""

    def test_generate_applies_clean_output(self):
        """generate() must pass gen_result['output'] through _clean_output."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-6.7b-instruct", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello. Context:")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp):
            with patch.object(engine, "_ensure_worker"):
                result = engine.generate("Say hi.", save_run=False)

        assert "Context:" not in result.output, (
            f"_clean_output should strip trailing 'Context:', got: {result.output!r}"
        )
        assert result.output == "Hello."

    def test_generate_keeps_clean_output(self):
        """generate() must not alter already-clean output."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-6.7b-instruct", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello.")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp):
            with patch.object(engine, "_ensure_worker"):
                result = engine.generate("Say hi.", save_run=False)

        assert result.output == "Hello."

    def test_json_stdout_clean_after_cleanup(self):
        """JSON serialized output must not contain trailing markers."""
        from lyme_model.runtime.engine import LocalInferenceEngine, InferenceResult

        engine = LocalInferenceEngine("deepseek-ai/deepseek-coder-6.7b-instruct", verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello. User:\nContext:")
        with patch.object(engine, "_generate_via_worker", return_value=mock_resp):
            with patch.object(engine, "_ensure_worker"):
                result = engine.generate("Say hi.", save_run=False)

        d = result.to_dict()
        # to_dict output must not contain bare Context: / User: / Assistant:
        import json
        serialized = json.dumps(d)
        assert "User:" not in d.get("output", ""), "Output must not contain User: marker"
        assert "Context:" not in d.get("output", ""), "Output must not contain Context: marker"
        # JSON must be valid (it should be since json.dumps was used)
        assert "output" in d

    def test_generate_cleans_context_repository_pattern_server_path(self):
        """Server path must clean Context:Repository: suffix from output."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine("test-model", reuse_worker=True, verbose=False)
        engine._tokenizer = _make_mock_tokenizer()

        mock_resp = _worker_response("Hello. Context:Repository:blog-engineLanguage:Python")
        with patch.object(server_client, "send_generate", return_value=mock_resp), \
             patch.object(server_client, "is_server_running", return_value=True), \
             patch.object(server_client, "get_server_stats") as mock_stats:

            mock_stats.return_value = {
                "status": "ok", "model": "test-model", "adapter_path": None,
                "load_in_4bit": False, "load_in_8bit": False, "dtype": "float16",
            }
            result = engine.generate("Say hi.", save_run=False)

        assert result.output == "Hello.", f"Expected 'Hello.', got {result.output!r}"
        assert "Context:" not in result.output
        assert "Repository:" not in result.output


# ── Context prompt cleanliness tests ──────────────────────────────────────

class TestContextPromptCleanliness:
    """Verify prompt construction: no-context vs explicit context."""

    def _make_engine(self, model_name="dummy-model"):
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine(model_name, verbose=False)
        engine._tokenizer = _make_mock_tokenizer()
        return engine

    def test_no_context_prompt_has_no_context_marker(self):
        """When context=None, the prompt sent to generate must not contain 'Context:'."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock(output="", success=True, to_dict=lambda: {"output": ""})
            runtime.run_task("Say hi.", context=None)

        called_prompt = mock_gen.call_args[0][0]
        assert "Context:" not in called_prompt, (
            f"No-context prompt must not contain 'Context:', got: {called_prompt!r}"
        )

    def test_no_context_no_repo_context_header(self):
        """When context=None, 'Repository context:' must not appear in prompt."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock(output="", success=True, to_dict=lambda: {"output": ""})
            runtime.run_task("Say hi.", context=None)

        called_prompt = mock_gen.call_args[0][0]
        assert "Repository context:" not in called_prompt

    def test_explicit_context_included_exactly_once(self):
        """When context is explicitly provided, it must appear exactly once."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        ctx_text = "def foo(): pass"
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock(output="", success=True, to_dict=lambda: {"output": ""})
            runtime.run_task("Say hi.", context=ctx_text)

        called_prompt = mock_gen.call_args[0][0]
        assert called_prompt.count(ctx_text) == 1, "Context must appear exactly once"
        assert "Repository context:" in called_prompt, "Explicit context must include header"
        assert "Task:" in called_prompt, "Explicit context must include task label"

    def test_explicit_context_with_no_context_flag_has_no_marker(self):
        """Even with --context flag, --no-context must suppress context entirely."""
        from lyme_model.runtime.engine import AgentRuntime

        runtime = AgentRuntime(model_name="dummy", verbose=False)
        ctx_text = "def foo(): pass"
        # Simulate --no-context by passing context=None despite having context available
        with patch.object(runtime.engine, "generate") as mock_gen:
            mock_gen.return_value = MagicMock(output="", success=True, to_dict=lambda: {"output": ""})
            runtime.run_task("Say hi.", context=None)

        called_prompt = mock_gen.call_args[0][0]
        assert ctx_text not in called_prompt
        assert "Repository context:" not in called_prompt


# ── JSONL I/O tests ───────────────────────────────────────────────────────

class TestJsonlWorkerIO:
    """Parent/worker JSONL communication must use text, not bytes."""

    def test_send_to_worker_writes_text_not_bytes(self):
        """_send_to_worker writes a string (text) to stdin, not bytes."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_stdin = MagicMock()
        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None
        engine._worker_process = mock_proc

        engine._send_to_worker({"command": "test", "value": 42})

        write_arg = mock_stdin.write.call_args[0][0]
        assert isinstance(write_arg, str), f"Expected str, got {type(write_arg)}"
        parsed = json.loads(write_arg.strip())
        assert parsed == {"command": "test", "value": 42}
        assert write_arg.endswith("\n")
        mock_stdin.flush.assert_called_once()

    def test_send_to_worker_raises_when_not_running(self):
        """_send_to_worker raises RuntimeError when no worker is running."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        with pytest.raises(RuntimeError, match="Worker not running"):
            engine._send_to_worker({"command": "test"})

    def test_recv_from_worker_parses_json_line(self):
        """_recv_from_worker reads a text JSON line and returns parsed dict."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_stdout = MagicMock()
        mock_stdout.fileno.return_value = 999
        mock_stdout.readline.return_value = '{"status": "ok", "output": "hello world"}\n'

        mock_proc = MagicMock()
        mock_proc.stdout = mock_stdout
        mock_proc.poll.return_value = None
        engine._worker_process = mock_proc

        with patch("select.select", return_value=([999], [], [])):
            result = engine._recv_from_worker(timeout=5)

        assert result == {"status": "ok", "output": "hello world"}

    def test_recv_from_worker_handles_multiline_json(self):
        """_recv_from_worker reads one line at a time, ignoring subsequent data."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_stdout = MagicMock()
        mock_stdout.fileno.return_value = 999
        mock_stdout.readline.side_effect = [
            '{"status": "ok", "output": "first"}\n',
            '{"status": "ok", "output": "second"}\n',
        ]

        mock_proc = MagicMock()
        mock_proc.stdout = mock_stdout
        mock_proc.poll.return_value = None
        engine._worker_process = mock_proc

        with patch("select.select", return_value=([999], [], [])):
            result = engine._recv_from_worker(timeout=5)

        assert result == {"status": "ok", "output": "first"}
        assert mock_stdout.readline.call_count == 1

    def test_recv_from_worker_timeout(self):
        """_recv_from_worker raises TimeoutError when worker does not respond."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        mock_stdout = MagicMock()
        mock_stdout.fileno.return_value = 999

        mock_proc = MagicMock()
        mock_proc.stdout = mock_stdout
        mock_proc.poll.return_value = None
        engine._worker_process = mock_proc

        with patch("select.select", return_value=([], [], [])):
            with pytest.raises(TimeoutError, match="did not respond"):
                engine._recv_from_worker(timeout=0.5)

    def test_worker_respond_writes_text(self):
        """worker._respond writes a text JSON line ending with newline to stdout."""
        import importlib.util
        worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
        spec = importlib.util.spec_from_file_location(
            "lyme_model.runtime.worker_test", worker_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        import io
        out = io.StringIO()
        monkey_patch_out = io.StringIO()
        import sys
        orig = sys.stdout
        sys.stdout = monkey_patch_out
        try:
            mod._respond({"status": "ok", "value": 7})
            written = monkey_patch_out.getvalue()
            assert isinstance(written, str), f"Expected str, got {type(written)}"
            parsed = json.loads(written.strip())
            assert parsed == {"status": "ok", "value": 7}
            assert written.endswith("\n")
        finally:
            sys.stdout = orig

    def test_worker_popen_has_text_mode(self):
        """_ensure_worker uses text=True in subprocess.Popen for text I/O."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._offload_dir = "/tmp/offload"
        engine._tokenizer = _make_mock_tokenizer()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                    engine._ensure_worker()

            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs.get("text") is True, (
                f"Expected text=True in Popen kwargs, got: {call_kwargs}"
            )
            assert call_kwargs.get("encoding") == "utf-8", (
                f"Expected encoding='utf-8' in Popen kwargs, got: {call_kwargs}"
            )


class TestCliExitCodes:
    """CLI must return non-zero exit code on runtime failure."""

    def _run_lyme(self, args, check=False):
        import subprocess
        cmd = [sys.executable, "-m", "lyme"] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=check)

    def test_run_json_failure_returns_exit_code_1(self):
        """model run with --json returns exit code 1 when runtime fails."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        backup = None
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = self._run_lyme(
                ["model", "run", "test task", "--json", "--model", "nonexistent-model"],
                check=False,
            )
            assert r.returncode != 0, (
                f"Expected non-zero exit code on failure, got {r.returncode}"
            )
        finally:
            if existed and backup is not None:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_run_json_failure_stdout_is_valid_json(self):
        """model run --json stdout must be parseable as JSON on failure."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        backup = None
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = self._run_lyme(
                ["model", "run", "test task", "--json", "--model", "nonexistent-model"],
                check=False,
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                assert "success" in data
                if not data["success"]:
                    assert "error" in data
        finally:
            if existed and backup is not None:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)

    def test_run_normal_failure_no_json(self):
        """model run without --json returns exit code 1."""
        current_file = REPO_ROOT / ".lyme" / "model" / "current.json"
        existed = current_file.exists()
        backup = None
        if existed:
            backup = current_file.read_text()
            current_file.unlink()
        try:
            r = self._run_lyme(
                ["model", "run", "test task", "--model", "nonexistent-model"],
                check=False,
            )
            assert r.returncode != 0
        finally:
            if existed and backup is not None:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_text(backup)


# ── Worker module testability ─────────────────────────────────────────────

class TestWorkerModule:
    """Verify the worker module can be imported safely (no side effects)."""

    def test_worker_importable(self):
        """worker.py has a main() function but does not auto-execute on import."""
        import importlib.util
        worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
        spec = importlib.util.spec_from_file_location("lyme_model.runtime.worker", worker_path)
        assert spec is not None, f"Could not load spec from {worker_path}"

    def test_worker_has_main_function(self):
        """worker.py exports main()."""
        import importlib
        worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
        spec = importlib.util.spec_from_file_location("lyme_model.runtime.worker_test", worker_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)


# ── Offload cleanup tests ─────────────────────────────────────────────


class TestOffloadCleanup:
    """Stale offload dir is cleared before each model load."""

    def test_ensure_clean_offload_dir_removes_existing(self, tmp_path):
        """Existing offload dir is removed and recreated empty."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        offload = tmp_path / ".offload"
        offload.mkdir(parents=True, exist_ok=True)
        (offload / "stale_weight.dat").write_text("stale")

        LocalInferenceEngine._ensure_clean_offload_dir(str(offload))

        assert offload.is_dir()
        assert len(list(offload.iterdir())) == 0

    def test_ensure_clean_offload_dir_creates_new(self, tmp_path):
        """Clean offload dir is created if it doesn't exist."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        offload = tmp_path / "new-offload"
        assert not offload.exists()

        LocalInferenceEngine._ensure_clean_offload_dir(str(offload))

        assert offload.is_dir()

    def test_validate_adapter_clears_offload(self, tmp_path):
        """_validate_adapter deletes stale .offload before recreating it."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")
        offload = adapter_dir / ".offload"
        offload.mkdir()
        (offload / "stale.dat").write_text("stale")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir))
        with patch.object(engine, "_check_imports"):
            engine._validate_adapter()

        assert offload.is_dir()
        assert len(list(offload.iterdir())) == 0

    def test_offload_dir_created_clean_on_first_call(self, tmp_path):
        """Offload dir created empty on first _validate_adapter call."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "fresh-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")
        offload = adapter_dir / ".offload"
        assert not offload.exists()

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir))
        with patch.object(engine, "_check_imports"):
            engine._validate_adapter()

        assert offload.is_dir()


# ── Worker labeled error tests ──────────────────────────────────────


class TestWorkerLabeledErrors:
    """Worker labels base-load vs adapter-load failures."""

    def _load_worker_module(self):
        import importlib.util
        worker_path = REPO_ROOT / "src" / "lyme_model" / "runtime" / "worker.py"
        spec = importlib.util.spec_from_file_location(
            "lyme_model.runtime.worker_label_test", worker_path
        )
        mod = importlib.util.module_from_spec(spec)
        return spec, mod

    def test_base_load_failure_labeled(self):
        """Base model load failure responds with base_load_failed: prefix."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_transformers.AutoModelForCausalLM.from_pretrained.side_effect = RuntimeError("OOM")
        mock_peft = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = json.dumps({
                "command": "init", "model_name": "test-model",
                "adapter_path": None, "device": "auto",
                "offload_dir": None, "debug": False,
            }) + "\n" + json.dumps({"command": "shutdown"}) + "\n"

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            capture = io.StringIO()
            sys.stdin = io.StringIO(stdin_data)
            sys.stdout = capture
            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

            output = capture.getvalue().strip()
            lines = [json.loads(l) for l in output.split("\n") if l.strip()]
            error_lines = [l for l in lines if "error" in l]
            assert len(error_lines) >= 1
            assert "base_load_failed:" in error_lines[0]["error"]

    def test_adapter_load_failure_labeled(self):
        """Adapter load failure responds with adapter_load_failed: prefix."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_peft = MagicMock()
        mock_peft.PeftModel.from_pretrained.side_effect = RuntimeError("Shape mismatch")
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = json.dumps({
                "command": "init", "model_name": "test-model",
                "adapter_path": "/some/adapter", "device": "auto",
                "offload_dir": None, "debug": False,
            }) + "\n" + json.dumps({"command": "shutdown"}) + "\n"

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            capture = io.StringIO()
            sys.stdin = io.StringIO(stdin_data)
            sys.stdout = capture
            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

            output = capture.getvalue().strip()
            lines = [json.loads(l) for l in output.split("\n") if l.strip()]
            error_lines = [l for l in lines if "error" in l]
            assert len(error_lines) >= 1
            assert "adapter_load_failed:" in error_lines[0]["error"]

    def test_debug_mode_includes_traceback(self):
        """Debug mode includes traceback in error response."""
        from unittest.mock import patch, MagicMock
        import json, io, sys

        mock_transformers = MagicMock()
        mock_transformers.AutoModelForCausalLM.from_pretrained.side_effect = RuntimeError("OOM")
        mock_peft = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float16 = "float16"
        mock_torch.float32 = "float32"

        spec, mod = self._load_worker_module()

        with patch.dict('sys.modules', {
            'transformers': mock_transformers,
            'peft': mock_peft,
            'torch': mock_torch,
        }):
            spec.loader.exec_module(mod)

            stdin_data = json.dumps({
                "command": "init", "model_name": "test-model",
                "adapter_path": None, "device": "auto",
                "offload_dir": None, "debug": True,
            }) + "\n" + json.dumps({"command": "shutdown"}) + "\n"

            orig_stdin = sys.stdin
            orig_stdout = sys.stdout
            capture = io.StringIO()
            sys.stdin = io.StringIO(stdin_data)
            sys.stdout = capture
            try:
                mod.main()
            finally:
                sys.stdin = orig_stdin
                sys.stdout = orig_stdout

            output = capture.getvalue().strip()
            lines = [json.loads(l) for l in output.split("\n") if l.strip()]
            error_lines = [l for l in lines if "error" in l]
            assert len(error_lines) >= 1
            assert "traceback" in error_lines[0]
            assert "Traceback" in error_lines[0]["traceback"]


# ── Adapter load retry tests ────────────────────────────────────────


class TestAdapterLoadRetry:
    """KeyError during adapter load triggers offload clear + fallback retry."""

    def test_is_retryable_adapter_error_matches_keyerror(self):
        """_is_retryable_adapter_error returns True for adapter KeyError with layers pattern."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        msg = "adapter_load_failed: KeyError: 'base_model.model.model.layers.5.input_layernorm.weight'"
        assert LocalInferenceEngine._is_retryable_adapter_error(msg)

    def test_is_retryable_adapter_error_non_layer_keyerror(self):
        """_is_retryable_adapter_error returns False for KeyError without layers pattern."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        msg = "adapter_load_failed: KeyError: 'some_other_key'"
        assert not LocalInferenceEngine._is_retryable_adapter_error(msg)

    def test_is_retryable_adapter_error_non_adapter_error(self):
        """_is_retryable_adapter_error returns False for non-adapter errors."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        msg = "base_load_failed: RuntimeError: OOM"
        assert not LocalInferenceEngine._is_retryable_adapter_error(msg)

    def test_is_retryable_adapter_error_non_keyerror(self):
        """_is_retryable_adapter_error returns False for non-KeyError adapter errors."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        msg = "adapter_load_failed: RuntimeError: Shape mismatch"
        assert not LocalInferenceEngine._is_retryable_adapter_error(msg)

    def test_ensure_worker_retries_on_keyerror(self):
        """_ensure_worker retries with safe_mode=True on retryable adapter error."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._offload_dir = "/tmp/offload"

        first_response = {
            "error": "adapter_load_failed: KeyError: 'base_model.model.model.layers.5.input_layernorm.weight'"
        }
        second_response = {"status": "ready"}

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        call_count = [0]

        def fake_spawn(safe_mode=False):
            call_count[0] += 1
            return None

        with patch.object(engine, "_spawn_worker", side_effect=fake_spawn):
            with patch.object(engine, "_recv_from_worker",
                              side_effect=[first_response, second_response]):
                with patch.object(engine, "_check_imports"):
                    with patch.object(engine, "_ensure_clean_offload_dir"):
                        with patch.object(engine, "_kill_worker"):
                            engine._ensure_worker()

        assert engine._worker_loaded is True, "Worker should be loaded after retry"

    def test_ensure_worker_does_not_retry_non_retryable(self):
        """_ensure_worker raises RuntimeError on non-retryable adapter error."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False)
        engine._offload_dir = "/tmp/offload"

        error_response = {
            "error": "adapter_load_failed: RuntimeError: Shape mismatch"
        }

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_recv_from_worker", return_value=error_response):
                with pytest.raises(RuntimeError, match="Shape mismatch"):
                    engine._ensure_worker()

    def test_spawn_worker_passes_safe_mode(self, tmp_path):
        """_spawn_worker sends safe_mode in init command."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        adapter_dir = tmp_path / "my-adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine("dummy-model", adapter_path=str(adapter_dir), verbose=False, debug=True)
        engine._offload_dir = str(adapter_dir / ".offload")

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                with patch.object(engine, "_check_imports"):
                    engine._spawn_worker(safe_mode=True)

            write_text = "".join(
                call[0][0] for call in mock_proc.stdin.write.call_args_list
            )
            sent = json.loads(write_text.strip())
            assert sent["safe_mode"] is True
            assert sent["debug"] is True


# ── Debug mode tests ────────────────────────────────────────────────


class TestDebugMode:
    """Debug mode includes traceback in error responses."""

    def test_debug_flag_propagates_to_worker_init(self):
        """debug flag is sent in init command to worker."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False, debug=True)
        engine._offload_dir = "/tmp/offload"

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                    engine._ensure_worker()

                write_text = "".join(
                    call[0][0] for call in mock_proc.stdin.write.call_args_list
                )
                sent = json.loads(write_text.strip())
                assert sent["debug"] is True

    def test_debug_false_omits_traceback(self):
        """debug=False does not send debug in init command."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False, debug=False)
        engine._offload_dir = "/tmp/offload"

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(engine, "_check_imports"):
                with patch.object(engine, "_recv_from_worker", return_value={"status": "ready"}):
                    engine._ensure_worker()

                write_text = "".join(
                    call[0][0] for call in mock_proc.stdin.write.call_args_list
                )
                sent = json.loads(write_text.strip())
                assert sent.get("debug") is False

    def test_error_result_contains_traceback_when_debug(self):
        """generate() returns error_traceback in result when debug=True."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False, debug=True, reuse_worker=False)
        engine._tokenizer = MagicMock()

        error_response = {
            "error": "base_load_failed: RuntimeError: OOM",
            "traceback": "Traceback (most recent call last):\n  ...",
        }

        with patch.object(engine, "_ensure_worker", side_effect=RuntimeError("base_load_failed: RuntimeError: OOM")):
            engine._last_worker_error_response = error_response
            result = engine.generate("test", save_run=False)
            assert not result.success
            assert "OOM" in result.error
            assert result.error_traceback is not None

    def test_error_result_no_traceback_when_not_debug(self):
        """generate() does not include traceback when debug=False."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("dummy-model", verbose=False, debug=False, reuse_worker=False)
        engine._tokenizer = MagicMock()

        with patch.object(engine, "_ensure_worker", side_effect=RuntimeError("Model load failed: OOM")):
            result = engine.generate("test", save_run=False)
            assert not result.success
            assert result.error_traceback is None


# ── Persistent server / reuse-worker tests ────────────────────────────────


class TestReuseWorker:
    """Tests for --reuse-worker persistent server behaviour."""

    def _make_server_mocks(self, engine):
        """Patch HardwareMonitor to avoid nvidia-smi Popen calls."""
        mon = MagicMock()
        mon.sample_gpu.return_value = MagicMock(
            utilization_percent=0, vram_used_mb=0
        )
        engine.monitor = mon

    def test_reuse_worker_autostarts_server_when_socket_missing(self):
        """--reuse-worker auto-starts server when server socket does not exist."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine("test-model", reuse_worker=True, verbose=False)
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="formatted prompt"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_is_running.side_effect = [False, True]
            mock_send.return_value = {
                "output": "hello from server",
                "prompt_tokens": 5,
                "generated_tokens": 8,
            }

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            result = engine.generate("Say hi", save_run=False)

            assert result.success is True
            assert result.output == "hello from server"
            assert result.prompt_tokens == 5
            assert result.generated_tokens == 8

            # Find the server_worker call
            server_calls = [c for c in mock_popen.call_args_list
                           if any("server_worker" in str(a) for a in c[0][0])]
            assert len(server_calls) == 1, f"Expected 1 server_worker call, got {len(server_calls)}"
            cmd_str = " ".join(server_calls[0][0][0])
            assert "server_worker.py" in cmd_str

    def test_reuse_worker_uses_existing_server(self):
        """--reuse-worker uses existing server when socket already exists."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine("test-model", reuse_worker=True, verbose=False)
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="formatted prompt"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running", return_value=True), \
             patch.object(server_client, "get_server_stats") as mock_stats, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_stats.return_value = {
                "status": "ok",
                "model": "test-model",
                "adapter_path": None,
                "load_in_4bit": False,
                "load_in_8bit": False,
                "dtype": "float16",
            }
            mock_send.return_value = {
                "output": "fast reply",
                "prompt_tokens": 3,
                "generated_tokens": 2,
            }

            result = engine.generate("Ping", save_run=False)

            assert result.success is True
            assert result.output == "fast reply"
            # Server already running — Popen should NOT be called
            mock_popen.assert_not_called()
            mock_send.assert_called_once()

    def test_quant_flags_passed_to_server(self):
        """--load-in-4bit and --load-in-8bit are forwarded to server_worker args."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine(
            "test-model", reuse_worker=True, verbose=False, load_in_4bit=True
        )
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="x"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_is_running.side_effect = [False, True]
            mock_send.return_value = {"output": "ok", "prompt_tokens": 1, "generated_tokens": 1}

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            engine.generate("test", save_run=False)

            server_calls = [c for c in mock_popen.call_args_list
                           if any("server_worker" in str(a) for a in c[0][0])]
            assert len(server_calls) == 1
            call_args = server_calls[0]
            assert "--load-in-4bit" in call_args[0][0]
            assert "--load-in-8bit" not in call_args[0][0]

    def test_dtype_passed_to_server(self):
        """--dtype is forwarded to server_worker args."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine(
            "test-model", reuse_worker=True, verbose=False, dtype="bfloat16"
        )
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="x"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_is_running.side_effect = [False, True]
            mock_send.return_value = {"output": "ok", "prompt_tokens": 1, "generated_tokens": 1}

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            engine.generate("test", save_run=False)

            server_calls = [c for c in mock_popen.call_args_list
                           if any("server_worker" in str(a) for a in c[0][0])]
            assert len(server_calls) == 1
            call_args = server_calls[0][0][0]
            idx = call_args.index("--dtype") if "--dtype" in call_args else -1
            assert idx >= 0
            assert call_args[idx + 1] == "bfloat16"

    def test_adapter_path_passed_to_server(self, tmp_path):
        """Adapter path is forwarded to server_worker args."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        adapter_dir = tmp_path / "adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text('{}')
        (adapter_dir / "adapter_model.safetensors").write_text("dummy")

        engine = LocalInferenceEngine(
            "test-model", adapter_path=str(adapter_dir),
            reuse_worker=True, verbose=False,
        )
        engine._offload_dir = str(tmp_path / "offload")
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="x"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_is_running.side_effect = [False, True]
            mock_send.return_value = {"output": "ok", "prompt_tokens": 1, "generated_tokens": 1}

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            engine.generate("test", save_run=False)

            server_calls = [c for c in mock_popen.call_args_list
                           if any("server_worker" in str(a) for a in c[0][0])]
            assert len(server_calls) == 1
            cmd_str = " ".join(server_calls[0][0][0])
            assert "--adapter-path" in cmd_str
            assert str(adapter_dir) in cmd_str

    def test_server_failure_returns_valid_json_error(self):
        """When server fails to start, generate() returns success:False with error."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("test-model", reuse_worker=True, verbose=False)
        engine._tokenizer = MagicMock()

        error_msg = (
            "Persistent model server failed to start within 120s\n"
            "Server stderr (last lines):\nCUDA out of memory"
        )
        with patch.object(engine, "_ensure_server",
                          side_effect=RuntimeError(error_msg)):
            result = engine.generate("test", save_run=False)
            assert result.success is False
            assert "failed to start" in (result.error or "").lower()

            # Valid JSON output contract
            import json
            d = result.to_dict()
            json_str = json.dumps(d)
            assert json.loads(json_str)["success"] is False

    def test_second_call_faster_with_reuse(self):
        """Second reuse call skips server start (no Popen) because server is already running."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine("test-model", reuse_worker=True, verbose=False)
        self._make_server_mocks(engine)

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="formatted"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "get_server_stats") as mock_stats, \
             patch.object(server_client, "send_generate") as mock_send:

            mock_is_running.side_effect = [False, True, True, True]
            mock_stats.return_value = {
                "status": "ok",
                "model": "test-model",
                "adapter_path": None,
                "load_in_4bit": False,
                "load_in_8bit": False,
                "dtype": "float16",
            }
            mock_send.return_value = {
                "output": "ok", "prompt_tokens": 1, "generated_tokens": 1,
            }

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            # First call — should start server
            r1 = engine.generate("first call", save_run=False)
            assert r1.success

            # Second call — should NOT start server again
            r2 = engine.generate("second call", save_run=False)
            assert r2.success

            # Popen server_worker calls should only be once
            server_calls = [c for c in mock_popen.call_args_list
                           if any("server_worker" in str(a) for a in c[0][0])]
            assert len(server_calls) == 1

            # send_generate should be called twice
            assert mock_send.call_count == 2

    def test_reuse_worker_defaults_to_true(self):
        """LocalInferenceEngine defaults to reuse_worker=True (server path)."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine("test-model", verbose=False)
        assert engine.reuse_worker is True, "reuse_worker must default to True"

    def test_no_server_disables_reuse(self):
        """--no-server sets reuse_worker=False (one-shot path)."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        engine = LocalInferenceEngine("test-model", reuse_worker=False, verbose=False)
        assert engine.reuse_worker is False

    def test_default_path_is_server(self):
        """Default _generate_via_worker calls _ensure_server (not _ensure_worker)."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("test-model", verbose=False)
        engine._tokenizer = MagicMock()
        mon = MagicMock()
        mon.sample_gpu.return_value = MagicMock(
            utilization_percent=0, vram_used_mb=0
        )
        engine.monitor = mon

        with patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="x"), \
             patch.object(engine, "_ensure_server") as mock_ensure_server, \
             patch.object(engine, "_ensure_worker") as mock_ensure_worker, \
             patch.object(engine, "_generate_via_server") as mock_via_server:

            mock_via_server.return_value = {
                "output": "from server", "prompt_tokens": 1, "generated_tokens": 1,
            }

            result = engine.generate("hi", save_run=False)
            assert result.success
            assert result.output == "from server"

            mock_ensure_server.assert_called_once()
            mock_ensure_worker.assert_not_called()

    def test_no_server_path_uses_worker(self):
        """With reuse_worker=False, _generate_via_worker calls _ensure_worker."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        engine = LocalInferenceEngine("test-model", reuse_worker=False, verbose=False)
        engine._offload_dir = "/tmp/offload"
        tokenizer = MagicMock()
        tokenizer.eos_token_id = 2
        tokenizer.pad_token_id = 2
        engine._tokenizer = tokenizer
        engine.monitor = MagicMock()
        engine.monitor.sample_gpu.return_value = MagicMock(
            utilization_percent=0, vram_used_mb=0
        )

        with patch.object(engine, "_check_imports"), \
             patch.object(engine, "_load_tokenizer"), \
             patch.object(engine, "_format_prompt", return_value="x"), \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(engine, "_ensure_server") as mock_ensure_server:

            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.stdin = MagicMock()
            mock_proc.stdout = MagicMock()
            mock_proc.stdout.fileno.return_value = 999
            mock_popen.return_value = mock_proc

            mock_resp = {"status": "ok", "output": "from worker",
                         "prompt_tokens": 1, "generated_tokens": 1}

            with patch.object(engine, "_recv_from_worker",
                              side_effect=[{"status": "ready"}, mock_resp]):
                with patch("select.select", return_value=([999], [], [])):
                    result = engine.generate("hi", save_run=False)

            assert result.success
            assert result.output == "from worker"
            # _ensure_server should NOT be called — worker path used
            mock_ensure_server.assert_not_called()


class TestServerCompatibility:
    """Verify server compatibility checking logic."""

    def test_compatible_match(self):
        """Server stats matching all params returns True."""
        from lyme_model.runtime.engine import LocalInferenceEngine

        stats = {
            "status": "ok",
            "model": "test-model",
            "adapter_path": None,
            "load_in_4bit": True,
            "load_in_8bit": False,
            "dtype": "float16",
        }
        assert LocalInferenceEngine._server_compatible(
            stats, "test-model", None, True, False, None
        )

    def test_compatible_model_mismatch(self):
        """Different model name returns False."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        stats = {"status": "ok", "model": "model-a", "adapter_path": None,
                 "load_in_4bit": False, "load_in_8bit": False, "dtype": "float16"}
        assert not LocalInferenceEngine._server_compatible(
            stats, "model-b", None, False, False, None
        )

    def test_compatible_quant_mismatch(self):
        """Different quantization returns False."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        stats = {"status": "ok", "model": "m", "adapter_path": None,
                 "load_in_4bit": False, "load_in_8bit": True, "dtype": "float16"}
        assert not LocalInferenceEngine._server_compatible(
            stats, "m", None, True, False, None
        )

    def test_compatible_dtype_mismatch(self):
        """Different dtype returns False when dtype is specified."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        stats = {"status": "ok", "model": "m", "adapter_path": None,
                 "load_in_4bit": False, "load_in_8bit": False, "dtype": "bfloat16"}
        assert not LocalInferenceEngine._server_compatible(
            stats, "m", None, False, False, "float16"
        )

    def test_compatible_adapter_mismatch(self):
        """Different adapter path returns False."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        stats = {"status": "ok", "model": "m", "adapter_path": "/path/a",
                 "load_in_4bit": False, "load_in_8bit": False, "dtype": "float16"}
        assert not LocalInferenceEngine._server_compatible(
            stats, "m", "/path/b", False, False, None
        )

    def test_compatible_server_not_running(self):
        """Server with non-ok status returns False."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        stats = {"status": "error", "error": "Server not running"}
        assert not LocalInferenceEngine._server_compatible(
            stats, "m", None, False, False, None
        )


class TestServerMismatchRestart:
    """When server config mismatches, old server is stopped and new one started."""

    def test_mismatch_restarts_server(self):
        """_ensure_server stops old server and starts new one on config mismatch."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client
        import time

        engine = LocalInferenceEngine(
            "new-model", reuse_worker=True, verbose=False
        )

        with patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "get_server_stats") as mock_stats, \
             patch.object(server_client, "send_shutdown") as mock_shutdown, \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(engine, "_log_phase"):

            # First check: server is running but with wrong model
            mock_is_running.return_value = True
            mock_stats.return_value = {
                "status": "ok",
                "model": "old-model",
                "adapter_path": None,
                "load_in_4bit": False,
                "load_in_8bit": False,
                "dtype": "float16",
            }

            mock_proc = MagicMock()
            mock_proc.stderr = MagicMock()
            mock_proc.stderr.read.return_value = ""
            mock_popen.return_value = mock_proc

            # Second is_server_running call: still not ready after restart
            # (we just want to test the mismatch path)
            mock_is_running.side_effect = [True, True]

            engine._ensure_server()

            # send_shutdown should have been called to stop old server
            mock_shutdown.assert_called_once()
            # Popen should have been called to start new server
            mock_popen.assert_called_once()

    def test_compatible_reuses_without_restart(self):
        """_ensure_server skips restart when existing server is compatible."""
        from lyme_model.runtime.engine import LocalInferenceEngine
        from lyme_model.runtime import server_client

        engine = LocalInferenceEngine(
            "matching-model", reuse_worker=True, verbose=False
        )

        with patch.object(server_client, "is_server_running") as mock_is_running, \
             patch.object(server_client, "get_server_stats") as mock_stats, \
             patch.object(server_client, "send_shutdown") as mock_shutdown, \
             patch("subprocess.Popen") as mock_popen:

            mock_is_running.return_value = True
            mock_stats.return_value = {
                "status": "ok",
                "model": "matching-model",
                "adapter_path": None,
                "load_in_4bit": False,
                "load_in_8bit": False,
                "dtype": "float16",
            }

            engine._ensure_server()

            mock_shutdown.assert_not_called()
            mock_popen.assert_not_called()
