"""Runtime hardware monitoring for Lyme Model.

Tracks GPU utilization, VRAM usage, temperature, and performance
metrics during model inference.
"""

import time
import subprocess
import shutil
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from .detector import HardwareProfile


@dataclass
class GPUMetrics:
    utilization_percent: float = 0.0
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    temperature_c: Optional[float] = None
    power_watts: Optional[float] = None


@dataclass
class InferenceMetrics:
    model_name: str = ""
    prompt_tokens: int = 0
    generated_tokens: int = 0
    prompt_time_s: float = 0.0
    generation_time_s: float = 0.0
    tokens_per_second: float = 0.0
    time_to_first_token_s: float = 0.0
    vram_used_mb: int = 0
    gpu_utilization: float = 0.0

    def to_dict(self):
        return asdict(self)


class HardwareMonitor:
    """Monitors hardware during model inference."""

    def __init__(self):
        self._has_nvidia = shutil.which("nvidia-smi") is not None

    def sample_gpu(self) -> GPUMetrics:
        """Sample current GPU metrics."""
        metrics = GPUMetrics()
        if not self._has_nvidia:
            return metrics
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = [p.strip() for p in result.stdout.strip().split(", ")]
                metrics.utilization_percent = float(parts[0]) if len(parts) > 0 else 0.0
                metrics.vram_used_mb = int(float(parts[1])) if len(parts) > 1 else 0
                metrics.vram_total_mb = int(float(parts[2])) if len(parts) > 2 else 0
                metrics.temperature_c = float(parts[3]) if len(parts) > 3 else None
                metrics.power_watts = float(parts[4]) if len(parts) > 4 else None
        except Exception:
            pass
        return metrics

    def measure_inference(
        self,
        model_name: str,
        prompt: str,
        generate_func,
        warmup: bool = True,
    ) -> InferenceMetrics:
        """Measure inference performance for a given model and prompt.

        Args:
            model_name: Name of the model being tested
            prompt: Input prompt
            generate_func: Callable that takes a prompt and returns
                          (generated_text, prompt_tokens, generated_tokens)
            warmup: Whether to do a warmup run first

        Returns:
            InferenceMetrics with timing data
        """
        if warmup:
            generate_func("warmup prompt (ignored)")
            time.sleep(0.5)

        gpu_before = self.sample_gpu()

        start = time.time()
        result, prompt_tokens, generated_tokens = generate_func(prompt)
        total_time = time.time() - start

        gpu_after = self.sample_gpu()

        metrics = InferenceMetrics(
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            prompt_time_s=0.0,
            generation_time_s=total_time,
            tokens_per_second=round(generated_tokens / total_time, 1) if total_time > 0 else 0.0,
            time_to_first_token_s=0.0,
            vram_used_mb=gpu_after.vram_used_mb,
            gpu_utilization=gpu_after.utilization_percent,
        )
        return metrics
