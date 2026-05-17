"""Runtime engine for Lyme Model — the core inference orchestrator.

Loads models locally using Transformers + PEFT, manages inference,
and coordinates the agent loop. No external API calls — everything runs
on local hardware.

Generation runs in an isolated subprocess worker so that timeouts can
safely kill the worker without leaving dangling threads or crashing the
parent process.
"""

import json
import time
import uuid
import sys
import subprocess
import atexit
import select
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import re
import shutil

from ..hardware.monitor import HardwareMonitor
from . import server_client
from .text_cleanup import clean_generated_output


@dataclass
class InferenceResult:
    model_name: str
    task: str
    output: str
    success: bool = False
    prompt_tokens: int = 0
    generated_tokens: int = 0
    time_s: float = 0.0
    tokens_per_second: float = 0.0
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    gpu_utilization: float = 0.0
    vram_used_mb: int = 0
    run_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("error_traceback") is None:
            del d["error_traceback"]
        return d


def save_run_metadata(result: InferenceResult, metadata: dict = None):
    run_dir = Path.cwd() / ".lyme" / "model-runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / f"{result.run_id}.json"
    data = result.to_dict()
    if metadata:
        data["metadata"] = metadata
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    run_file.write_text(json.dumps(data, indent=2))


class LocalInferenceEngine:
    """Core inference engine using a subprocess worker.

Loads a base model via HuggingFace ``transformers`` and optionally
applies a PEFT LoRA adapter on top.  All computation is local —
no external API calls.

Generation runs in an isolated subprocess (worker.py).  On timeout
the worker process is killed, freeing all GPU/CPU resources without
crashing the parent process.
    """

    def __init__(
        self,
        model_name: str = "deepseek-ai/deepseek-coder-6.7b-instruct",
        adapter_path: Optional[str] = None,
        device: str = "auto",
        max_new_tokens: int = 32,
        temperature: float = 0.1,
        top_p: float = 0.95,
        do_sample: bool = False,
        timeout: int = 180,
        verbose: bool = True,
        debug: bool = False,
        reuse_worker: bool = True,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        dtype: Optional[str] = None,
    ):
        self.model_name = model_name
        self.adapter_path = Path(adapter_path) if adapter_path else None
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample
        self.timeout = timeout
        self.verbose = verbose
        self.debug = debug
        self.reuse_worker = reuse_worker
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.dtype = dtype
        self._tokenizer = None
        self._worker_process: Optional[subprocess.Popen] = None
        self._worker_loaded = False
        self._offload_dir: Optional[str] = None
        self.monitor = HardwareMonitor()
        self._last_worker_error_response: Optional[dict] = None
        atexit.register(self._cleanup_worker)

    @staticmethod
    def _server_compatible(stats: dict, model_name: str, adapter_path, load_in_4bit: bool, load_in_8bit: bool, dtype: Optional[str]) -> bool:
        if stats.get("status") != "ok":
            return False
        if stats.get("model") != model_name:
            return False
        server_adapter = stats.get("adapter_path") or None
        if adapter_path and server_adapter:
            if Path(adapter_path).resolve() != Path(server_adapter).resolve():
                return False
        elif adapter_path or server_adapter:
            return False
        if load_in_4bit != stats.get("load_in_4bit", False):
            return False
        if load_in_8bit != stats.get("load_in_8bit", False):
            return False
        if dtype is not None and stats.get("dtype") != dtype:
            return False
        return True

    def _cleanup_worker(self):
        self._kill_worker()

    # ── internal helpers ──────────────────────────────────────────────────

    def _log_phase(self, message: str):
        if self.verbose:
            print(message, file=sys.stderr, flush=True)

    def _check_imports(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "PyTorch is required for local inference.\n"
                "  Install with:  pip install lyme[ml]\n"
                "  or:            pip install torch"
            )
        try:
            import transformers  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "Transformers is required for local inference.\n"
                "  Install with:  pip install lyme[ml]\n"
                "  or:            pip install transformers"
            )
        try:
            import peft  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "PEFT is required for loading adapters.\n"
                "  Install with:  pip install lyme[ml]\n"
                "  or:            pip install peft"
            )
        try:
            import accelerate  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "Accelerate is required for device mapping.\n"
                "  Install with:  pip install lyme[ml]\n"
                "  or:            pip install accelerate"
            )

    def _load_tokenizer(self):
        """Lazy-load the tokenizer (for prompt formatting and output decoding)."""
        if self._tokenizer is not None:
            return

        self._check_imports()
        from transformers import AutoTokenizer

        self._log_phase("Loading tokenizer...")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Tokenizer for '{self.model_name}' not found.\n"
                f"  Detail: {exc}\n"
                f"  Download the base model first:\n"
                f"    huggingface-cli download {self.model_name}"
            )

    def _validate_adapter(self):
        """Validate that the adapter directory has the required files."""
        if self.adapter_path is None:
            self._offload_dir = str(
                Path.cwd() / ".lyme" / "model_offload" / self.model_name.replace("/", "_")
            )
            self._ensure_clean_offload_dir(self._offload_dir)
            return

        adapter_dir = Path(self.adapter_path)
        if not adapter_dir.is_dir():
            raise RuntimeError(
                f"Adapter directory not found: {adapter_dir}\n"
                "  Run  lyme model use <path>  to point to a valid artifact."
            )

        config_file = adapter_dir / "adapter_config.json"
        weights_file = adapter_dir / "adapter_model.safetensors"
        missing = []
        if not config_file.exists():
            missing.append(str(config_file))
        if not weights_file.exists():
            missing.append(str(weights_file))
        if missing:
            raise RuntimeError(
                "Missing adapter file(s):\n"
                + "\n".join(f"  {p}" for p in missing)
                + "\n\nNext command to fix:\n"
                + f"  lyme model use <path-to-valid-artifact>"
            )

        self._offload_dir = str(adapter_dir / ".offload")
        self._ensure_clean_offload_dir(self._offload_dir)

    @staticmethod
    def _ensure_clean_offload_dir(offload_dir: str):
        p = Path(offload_dir)
        if p.is_dir():
            shutil.rmtree(str(p))
        p.mkdir(parents=True, exist_ok=True)

    # ── worker subprocess management ──────────────────────────────────────

    def _get_worker_script(self) -> str:
        return str(Path(__file__).resolve().parent / "worker.py")

    def _get_server_script(self) -> str:
        return str(Path(__file__).resolve().parent / "server_worker.py")

    def _ensure_worker(self):
        """Spawn and initialise the worker subprocess if needed."""
        if self._worker_process is not None and self._worker_loaded:
            poll = self._worker_process.poll()
            if poll is None:
                return
            self._kill_worker()

        # Must happen before spawning — sets self._offload_dir and creates
        # the directory on disk so the worker can write offloaded weights.
        self._validate_adapter()

        self._last_worker_error_response = None
        self._spawn_worker(safe_mode=False)
        response = self._recv_from_worker(timeout=600)
        if response.get("error"):
            error_msg = response["error"]
            if self.debug and response.get("traceback"):
                self._last_worker_error_response = response
            self._kill_worker()
            if self._is_retryable_adapter_error(error_msg):
                self._log_phase("Adapter load failed, retrying with safe mode...")
                self._ensure_clean_offload_dir(self._offload_dir)
                self._spawn_worker(safe_mode=True)
                response = self._recv_from_worker(timeout=600)
                if response.get("error"):
                    self._kill_worker()
                    raise RuntimeError(response["error"])
                if response.get("status") == "ready":
                    self._worker_loaded = True
                    self._log_phase("Worker model loaded (safe fallback).")
                    return
                self._kill_worker()
                raise RuntimeError(f"Worker init failed: unexpected response {response}")
            raise RuntimeError(error_msg)
        if response.get("status") != "ready":
            self._kill_worker()
            raise RuntimeError(f"Worker init failed: unexpected response {response}")

        self._worker_loaded = True
        self._log_phase("Worker model loaded.")

    def _spawn_worker(self, safe_mode: bool = False):
        self._worker_process = subprocess.Popen(
            [sys.executable, self._get_worker_script()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        init_cmd = {
            "command": "init",
            "model_name": self.model_name,
            "adapter_path": str(self.adapter_path) if self.adapter_path else None,
            "device": self.device,
            "offload_dir": self._offload_dir,
            "debug": self.debug,
            "safe_mode": safe_mode,
            "load_in_4bit": self.load_in_4bit,
            "load_in_8bit": self.load_in_8bit,
            "dtype": self.dtype,
        }
        self._send_to_worker(init_cmd)

    @staticmethod
    def _is_retryable_adapter_error(error_msg: str) -> bool:
        if "adapter_load_failed:" not in error_msg:
            return False
        if "KeyError:" not in error_msg:
            return False
        if re.search(r"base_model\.model\.model\.layers\.\d+", error_msg):
            return True
        return False

    def _ensure_server(self):
        """Ensure the persistent model server is running; auto-start if needed."""
        if server_client.is_server_running():
            stats = server_client.get_server_stats(timeout=3)
            if LocalInferenceEngine._server_compatible(
                stats, self.model_name, self.adapter_path,
                self.load_in_4bit, self.load_in_8bit, self.dtype,
            ):
                self._log_phase("Reusing running model server.")
                return
            self._log_phase("Server config mismatch (model/adapter/quant/dtype). Stopping old server...")
            server_client.send_shutdown()
            time.sleep(1)

        self._log_phase("Starting persistent model server...")
        server_script = self._get_server_script()
        socket_path = server_client.get_socket_path()
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, server_script,
               "--model", self.model_name,
               "--socket-path", str(socket_path)]
        if self.adapter_path:
            cmd.extend(["--adapter-path", str(self.adapter_path)])
        if self.load_in_4bit:
            cmd.append("--load-in-4bit")
        elif self.load_in_8bit:
            cmd.append("--load-in-8bit")
        if self.dtype:
            cmd.extend(["--dtype", self.dtype])
        if self.debug:
            cmd.append("--debug")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
            text=True,
        )

        self._log_phase("Waiting for model server to become ready...")
        deadline = time.time() + 120
        while time.time() < deadline:
            if server_client.is_server_running():
                self._log_phase("Persistent model server ready.")
                return
            time.sleep(1)

        # Server failed to start — collect stderr for diagnostic
        stderr_text = ""
        try:
            proc.kill()
            _, stderr_text = proc.communicate(timeout=5)
        except Exception:
            try:
                stderr_text = proc.stderr.read() if proc.stderr else ""
            except Exception:
                stderr_text = "(could not read server stderr)"

        msg = "Persistent model server failed to start within 120s"
        if stderr_text and stderr_text.strip():
            lines = stderr_text.strip().split("\n")
            summary = "\n".join(lines[-20:])
            if len(summary) > 500:
                summary = "..." + summary[-497:]
            msg += f"\nServer stderr (last lines):\n{summary}"
        raise RuntimeError(msg)

    def _generate_via_server(self, prompt: str, gen_kwargs: dict) -> dict:
        """Send generate request to persistent server."""
        return server_client.send_generate(prompt, gen_kwargs, timeout=self.timeout)

    def _kill_worker(self):
        if self._worker_process is None:
            return
        try:
            try:
                self._send_to_worker({"command": "shutdown"})
                self._worker_process.wait(timeout=5)
            except Exception:
                self._worker_process.kill()
                self._worker_process.wait(timeout=5)
        except Exception:
            pass
        self._worker_process = None
        self._worker_loaded = False

    def _send_to_worker(self, data: dict):
        if self._worker_process is None or self._worker_process.stdin is None:
            raise RuntimeError("Worker not running")
        line = json.dumps(data) + "\n"
        self._worker_process.stdin.write(line)
        self._worker_process.stdin.flush()

    def _recv_from_worker(self, timeout: float = 30) -> dict:
        """Read one JSON line from worker stdout with timeout."""
        if self._worker_process is None or self._worker_process.stdout is None:
            raise RuntimeError("Worker not running")

        fd = self._worker_process.stdout.fileno()
        start = time.time()
        while time.time() - start < timeout:
            r, _, _ = select.select([fd], [], [], 0.5)
            if r:
                line = self._worker_process.stdout.readline()
                if not line:
                    poll = self._worker_process.poll()
                    if poll is not None:
                        raise RuntimeError(f"Worker process died (exit code {poll})")
                    continue
                return json.loads(line.strip())
            else:
                poll = self._worker_process.poll()
                if poll is not None:
                    raise RuntimeError(f"Worker process died (exit code {poll})")

        raise TimeoutError(f"Worker did not respond within {timeout}s")

    # ── generation via worker ─────────────────────────────────────────────

    def _generate_via_worker(
        self, prompt: str, gen_kwargs: dict
    ) -> dict:
        """Send a generate request to the worker and wait for the response.

        Returns a dict with keys ``output``, ``prompt_tokens``,
        ``generated_tokens``.

        When ``self.reuse_worker`` is True, uses the persistent server
        instead of spawning a fresh subprocess worker.
        """
        if self.reuse_worker:
            self._ensure_server()
            return self._generate_via_server(prompt, gen_kwargs)

        self._ensure_worker()
        self._send_to_worker({
            "command": "generate",
            "prompt": prompt,
            "gen_kwargs": gen_kwargs,
        })

        response = self._recv_from_worker(timeout=self.timeout)
        if response.get("status") == "error":
            raise RuntimeError(response.get("error", "Unknown worker error"))
        if response.get("status") != "ok":
            raise RuntimeError(f"Unexpected worker response: {response}")

        return {
            "output": response["output"],
            "prompt_tokens": response["prompt_tokens"],
            "generated_tokens": response["generated_tokens"],
        }

    # ── prompt formatting ─────────────────────────────────────────────────

    def _build_safe_gen_kwargs(self, **overrides) -> dict:
        eos_id = self._tokenizer.eos_token_id if self._tokenizer else None
        pad_id = eos_id
        if pad_id is None and self._tokenizer:
            pad_id = getattr(self._tokenizer, "pad_token_id", None)

        kwargs: Dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.do_sample,
            "use_cache": True,
        }
        if eos_id is not None:
            kwargs["eos_token_id"] = eos_id
        if pad_id is not None:
            kwargs["pad_token_id"] = pad_id
        if self.do_sample:
            kwargs["temperature"] = self.temperature
            kwargs["top_p"] = self.top_p

        kwargs.update(overrides)
        return kwargs

    def _format_prompt(self, prompt: str) -> str:
        chat_template = getattr(self._tokenizer, "chat_template", None)
        if chat_template:
            messages = [{"role": "user", "content": prompt}]
            return self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        name = self.model_name.lower()
        if "deepseek" in name:
            return f"You are Lyme, a local coding assistant.\n\nUser: {prompt}\nAssistant:"
        if "llama-3" in name or "llama3" in name:
            return f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>"
        return f"### Instruction: {prompt}\n\n### Response:"

    # ── output cleanup ────────────────────────────────────────────────────

    @staticmethod
    def _clean_output(output: str) -> str:
        """Strip trailing structural markers and template artifacts.

        Delegates to the shared ``clean_generated_output`` function so that
        both the subprocess worker and persistent server paths use the same
        cleanup logic.
        """
        return clean_generated_output(output)

    # ── public API ────────────────────────────────────────────────────────

    def generate(self, prompt: str, save_run: bool = True, raw_prompt: bool = False, **gen_kwargs) -> InferenceResult:
        """Generate text using the local model via subprocess worker.

        Safe generation defaults are enforced (max_new_tokens=32,
        do_sample=False, use_cache=True, eos/pad from tokenizer).
        Timeout kills the worker subprocess, freeing all resources.
        """
        run_id = uuid.uuid4().hex[:12]
        result = InferenceResult(
            model_name=self.model_name,
            task=prompt[:100],
            output="",
            run_id=run_id,
        )

        gpu_before = self.monitor.sample_gpu()

        try:
            self._load_tokenizer()
        except Exception as exc:
            result.error = str(exc)
            return result

        if not raw_prompt:
            prompt = self._format_prompt(prompt)

        safe_kwargs = self._build_safe_gen_kwargs(**gen_kwargs)

        self._log_phase("Generating tokens...")
        start = time.time()

        try:
            gen_result = self._generate_via_worker(prompt, safe_kwargs)
        except TimeoutError:
            if not self.reuse_worker:
                self._kill_worker()
            self._log_phase(f"Timed out after {self.timeout}s.")
            elapsed = time.time() - start
            result.error = f"Generation timed out after {self.timeout}s"
            result.time_s = round(elapsed, 2)
            method = "transformers_peft_server" if self.reuse_worker else "transformers_peft_worker"
            if save_run:
                save_run_metadata(result, {"method": method, "timeout": True})
            return result
        except Exception as exc:
            if not self.reuse_worker:
                self._kill_worker()
            result.error = str(exc)
            if self.debug and self._last_worker_error_response:
                result.error_traceback = self._last_worker_error_response.get("traceback")
            return result

        elapsed = time.time() - start

        result.output = self._clean_output(gen_result["output"])
        result.success = True
        result.prompt_tokens = gen_result["prompt_tokens"]
        result.generated_tokens = gen_result["generated_tokens"]
        result.time_s = round(elapsed, 2)
        result.tokens_per_second = (
            round(gen_result["generated_tokens"] / elapsed, 1)
            if elapsed > 0 and gen_result["generated_tokens"] > 0
            else 0.0
        )

        gpu_after = self.monitor.sample_gpu()
        result.gpu_utilization = gpu_after.utilization_percent
        result.vram_used_mb = gpu_after.vram_used_mb

        if save_run:
            method = "transformers_peft_server" if self.reuse_worker else "transformers_peft_worker"
            save_run_metadata(result, {"method": method})

        return result


class AgentRuntime:
    """Full agent runtime that orchestrates the inference loop."""

    def __init__(
        self,
        model_name: str = "deepseek-ai/deepseek-coder-6.7b-instruct",
        adapter_path: Optional[str] = None,
        repo_path: Optional[str] = None,
        **engine_kwargs,
    ):
        self.engine = LocalInferenceEngine(
            model_name, adapter_path=adapter_path, **engine_kwargs
        )
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self.history: List[InferenceResult] = []

    def run_task(
        self, task: str, context: Optional[str] = None, raw_prompt: bool = False
    ) -> InferenceResult:
        """Execute a coding task with optional compressed context.

        Context is only included when explicitly provided.  When
        ``context`` is ``None``, the raw task is passed directly without
        any repository-context preamble.
        """
        if context:
            prompt = (
                f"Repository context:\n{context}\n\n"
                f"Task:\n{task}\n\n"
                "Complete the task. Return only the necessary code or analysis."
            )
        else:
            prompt = task

        result = self.engine.generate(prompt, raw_prompt=raw_prompt)
        self.history.append(result)
        return result

    def get_history(self) -> List[Dict]:
        return [r.to_dict() for r in self.history]
