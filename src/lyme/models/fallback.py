"""Fallback — model-level fallback chains for graceful degradation."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class FallbackReason(Enum):
    OOM = "out_of_memory"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    LOW_QUALITY = "low_quality"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


@dataclass
class FallbackStep:
    backend: str
    model: str
    quantization: str = "Q4_K_M"
    min_vram_gb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"backend": self.backend, "model": self.model, "quantization": self.quantization}


@dataclass
class FallbackResult:
    success: bool
    text: str = ""
    backend: str = ""
    model: str = ""
    steps_tried: int = 0
    reason: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "steps_tried": self.steps_tried,
            "backend": self.backend,
            "model": self.model,
            "reason": self.reason,
            "metrics": self.metrics,
        }


InferenceCallable = Callable[[str, str, str], Tuple[bool, str, float]]


class FallbackChain:
    def __init__(self, name: str, steps: List[FallbackStep]):
        self.name = name
        self.steps = steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }


PRESET_FALLBACK_CHAINS = {
    "default": FallbackChain(
        name="default",
        steps=[
            FallbackStep(backend="llama.cpp", model="qwen2.5-coder-7b", quantization="Q4_K_M", min_vram_gb=6),
            FallbackStep(backend="ollama", model="qwen2.5-coder:7b", min_vram_gb=6),
            FallbackStep(backend="llama.cpp", model="deepseek-coder-1.3b", quantization="Q4_K_M", min_vram_gb=2),
            FallbackStep(backend="ollama", model="deepseek-coder:1.3b", min_vram_gb=2),
        ],
    ),
    "fast": FallbackChain(
        name="fast",
        steps=[
            FallbackStep(backend="ollama", model="qwen2.5-coder:1.5b", min_vram_gb=2),
            FallbackStep(backend="llama.cpp", model="phi-3-mini-4k", quantization="Q4_K_M", min_vram_gb=3),
        ],
    ),
    "high_quality": FallbackChain(
        name="high_quality",
        steps=[
            FallbackStep(backend="llama.cpp", model="deepseek-coder-33b", quantization="Q4_K_M", min_vram_gb=20),
            FallbackStep(backend="ollama", model="deepseek-coder-v2:16b", min_vram_gb=12),
            FallbackStep(backend="llama.cpp", model="deepseek-coder-6.7b", quantization="Q4_K_M", min_vram_gb=8),
        ],
    ),
}


class ModelFallbackOrchestrator:
    def __init__(self, infer: InferenceCallable):
        self.infer = infer
        self.chains = dict(PRESET_FALLBACK_CHAINS)
        self._logger = logging.getLogger("lyme.models.fallback")

    def execute(self, prompt: str, chain_name: str = "default") -> FallbackResult:
        chain = self.chains.get(chain_name, self.chains["default"])
        errors: List[str] = []

        for i, step in enumerate(chain.steps):
            self._logger.info(f"Fallback step {i+1}/{len(chain.steps)}: {step.backend}/{step.model}")
            try:
                success, text, duration = self.infer(prompt, step.backend, step.model)
                if success:
                    return FallbackResult(
                        success=True,
                        text=text,
                        backend=step.backend,
                        model=step.model,
                        steps_tried=i + 1,
                        metrics={"duration_ms": duration},
                    )
                errors.append(f"Step {i+1} ({step.backend}/{step.model}): inference returned failure")
            except Exception as e:
                errors.append(f"Step {i+1} ({step.backend}/{step.model}): {e}")

        return FallbackResult(
            success=False,
            steps_tried=len(chain.steps),
            reason="; ".join(errors),
        )

    def add_chain(self, chain: FallbackChain) -> None:
        self.chains[chain.name] = chain

    def list_chains(self) -> List[Dict[str, Any]]:
        return [{"name": k, "steps": len(v.steps)} for k, v in self.chains.items()]
