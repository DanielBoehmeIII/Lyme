"""Runtime engine for Lyme Model — the core inference orchestrator.

Loads models, manages inference, and coordinates the agent loop.
Wraps Ollama for local model execution.
"""

import subprocess
import time
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from pathlib import Path

from ..hardware.detector import detect_all, HardwareProfile
from ..hardware.monitor import HardwareMonitor


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

    def to_dict(self) -> dict:
        return asdict(self)


class LocalInferenceEngine:
    """Core inference engine using Ollama as the backend."""

    def __init__(self, model_name: str = "deepseek-coder:6.7b",
                 timeout: int = 120):
        self.model_name = model_name
        self.timeout = timeout
        self.monitor = HardwareMonitor()

    def generate(self, prompt: str) -> InferenceResult:
        """Generate text from the model."""
        result = InferenceResult(
            model_name=self.model_name,
            task=prompt[:100],
            output="",
        )

        gpu_before = self.monitor.sample_gpu()

        try:
            start = time.time()
            proc = subprocess.run(
                ["ollama", "run", self.model_name, prompt],
                capture_output=True, text=True, timeout=self.timeout
            )
            elapsed = time.time() - start
            output = proc.stdout.strip()

            result.output = output
            result.time_s = round(elapsed, 2)
            result.success = proc.returncode == 0

            # Estimate tokens
            result.generated_tokens = len(output.split())
            result.tokens_per_second = round(
                result.generated_tokens / elapsed, 1
            ) if elapsed > 0 else 0.0

        except subprocess.TimeoutExpired:
            result.error = f"Timeout ({self.timeout}s)"
            result.time_s = self.timeout
        except Exception as e:
            result.error = str(e)

        gpu_after = self.monitor.sample_gpu()
        result.gpu_utilization = gpu_after.utilization_percent
        result.vram_used_mb = gpu_after.vram_used_mb

        return result

    def profile(self, warmup: str = "hello", samples: int = 3) -> Dict:
        """Profile model performance."""
        times = []
        for i in range(samples):
            r = self.generate(warmup)
            if r.success:
                times.append(r.time_s)

        avg_time = sum(times) / len(times) if times else 0
        return {
            "model": self.model_name,
            "samples": samples,
            "avg_time_s": round(avg_time, 2),
            "hardware": detect_all().to_dict(),
        }


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
