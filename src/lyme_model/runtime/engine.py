"""Runtime engine for Lyme Model — the core inference orchestrator.

Loads models, manages inference, and coordinates the agent loop.
Uses the Ollama REST API for local model execution.
"""

import json
import time
import uuid
import urllib.request
import urllib.error
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pathlib import Path

from ..hardware.detector import detect_all
from ..hardware.monitor import HardwareMonitor


OLLAMA_API_BASE = "http://localhost:11434"


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
    gpu_utilization: float = 0.0
    vram_used_mb: int = 0
    run_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def check_ollama() -> bool:
    """Check if Ollama is available and running."""
    if not shutil.which("ollama"):
        return False
    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def list_ollama_models() -> List[str]:
    """List available models from Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def check_model_available(model_name: str) -> bool:
    """Check if a specific model is available in Ollama."""
    return model_name in list_ollama_models()


def save_run_metadata(result: InferenceResult, metadata: dict = None):
    """Save run metadata to .lyme/model-runs/."""
    run_dir = Path.cwd() / ".lyme" / "model-runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / f"{result.run_id}.json"
    data = result.to_dict()
    if metadata:
        data["metadata"] = metadata
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    run_file.write_text(json.dumps(data, indent=2))


class LocalInferenceEngine:
    """Core inference engine using Ollama REST API."""

    def __init__(self, model_name: str = "deepseek-coder:6.7b",
                 timeout: int = 120):
        self.model_name = model_name
        self.timeout = timeout
        self.monitor = HardwareMonitor()

    def generate(self, prompt: str, save_run: bool = True) -> InferenceResult:
        """Generate text from the model using the Ollama REST API."""
        run_id = uuid.uuid4().hex[:12]
        result = InferenceResult(
            model_name=self.model_name,
            task=prompt[:100],
            output="",
            run_id=run_id,
        )

        gpu_before = self.monitor.sample_gpu()

        if not check_ollama():
            result.error = "Ollama is not available or not running"
            return result

        if not check_model_available(self.model_name):
            result.error = (
                f"Model '{self.model_name}' not found in Ollama. "
                f"Install with: ollama pull {self.model_name}"
            )
            return result

        try:
            payload = json.dumps({
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 2048,
                    "temperature": 0.2,
                }
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_API_BASE}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            start = time.time()
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode()
                data = json.loads(body)
            elapsed = time.time() - start

            result.output = data.get("response", "").strip()
            result.time_s = round(elapsed, 2)
            result.success = True

            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            result.generated_tokens = eval_count
            result.prompt_tokens = prompt_eval_count
            result.tokens_per_second = round(
                eval_count / elapsed, 1
            ) if elapsed > 0 and eval_count > 0 else 0.0

        except urllib.error.HTTPError as e:
            result.error = f"Ollama API error: {e.code} {e.reason}"
        except urllib.error.URLError as e:
            result.error = f"Ollama connection error: {e.reason}"
        except Exception as e:
            result.error = str(e)

        gpu_after = self.monitor.sample_gpu()
        result.gpu_utilization = gpu_after.utilization_percent
        result.vram_used_mb = gpu_after.vram_used_mb

        if save_run:
            save_run_metadata(result, {"method": "ollama_api"})

        return result


class AgentRuntime:
    """Full agent runtime that orchestrates the inference loop."""

    def __init__(self, model_name: str = "deepseek-coder:6.7b",
                 repo_path: Optional[str] = None):
        self.engine = LocalInferenceEngine(model_name)
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self.history: List[InferenceResult] = []

    def run_task(self, task: str, context: Optional[str] = None) -> InferenceResult:
        """Execute a coding task with optional compressed context."""
        if context:
            prompt = (
                f"Repository context:\n{context}\n\n"
                f"Task:\n{task}\n\n"
                "Complete the task. Return only the necessary code or analysis."
            )
        else:
            prompt = task

        result = self.engine.generate(prompt)
        self.history.append(result)
        return result

    def get_history(self) -> List[Dict]:
        return [r.to_dict() for r in self.history]
