"""ModelRuntime — unified multi-backend inference runtime with streaming, fallback, VRAM awareness."""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

from .profiles import (
    ModelProfile, TaskProfile, ProfileRecommendation,
    recommend_model, get_profile, ALL_PROFILES,
)
from .streaming import StreamConfig, TokenStream, StreamStats
from .batching import BatchRequest, BatchResult, BatchProcessor, BatchStats
from .fallback import ModelFallbackOrchestrator, FallbackChain, FallbackStep, FallbackResult


@dataclass
class ModelRuntimeConfig:
    preferred_backend: str = "auto"
    vram_gb: float = 0.0
    fallback_chain: str = "default"
    stream: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    verbose: bool = False


@dataclass
class InferenceResponse:
    text: str
    model: str = ""
    backend: str = ""
    tokens: int = 0
    duration_ms: float = 0.0
    tokens_per_second: float = 0.0
    stream_stats: Optional[StreamStats] = None
    fallback_result: Optional[FallbackResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "backend": self.backend,
            "tokens": self.tokens,
            "duration_ms": round(self.duration_ms, 2),
            "tokens_per_second": round(self.tokens_per_second, 2),
            "stream_stats": self.stream_stats.to_dict() if self.stream_stats else None,
            "fallback_result": self.fallback_result.to_dict() if self.fallback_result else None,
        }


class ModelRuntime:
    def __init__(self, config: ModelRuntimeConfig = None):
        self.config = config or ModelRuntimeConfig()
        self._logger = logging.getLogger("lyme.models.runtime")
        self._inference_fn = None
        self._fallback: Optional[ModelFallbackOrchestrator] = None

    def set_inference_fn(self, fn) -> None:
        self._inference_fn = fn

    def set_fallback(self, fallback: ModelFallbackOrchestrator) -> None:
        self._fallback = fallback

    def infer(self, prompt: str, task: TaskProfile = TaskProfile.GENERAL) -> InferenceResponse:
        if self._fallback and self.config.fallback_chain:
            result = self._fallback.execute(prompt, self.config.fallback_chain)
            return InferenceResponse(
                text=result.text,
                model=result.model,
                backend=result.backend,
                fallback_result=result,
                tokens=len(result.text.split()),
                duration_ms=result.metrics.get("duration_ms", 0),
            )

        if self._inference_fn:
            start = time.time()
            try:
                text = self._inference_fn(prompt)
                duration = (time.time() - start) * 1000
                return InferenceResponse(
                    text=text,
                    tokens=len(text.split()),
                    duration_ms=duration,
                    tokens_per_second=(len(text.split()) / (duration / 1000)) if duration > 0 else 0,
                )
            except Exception as e:
                return InferenceResponse(text=f"Error: {e}")

        return InferenceResponse(text="No inference backend configured")

    def infer_stream(self, prompt: str) -> Generator[str, None, InferenceResponse]:
        config = StreamConfig(max_tokens=self.config.max_tokens, temperature=self.config.temperature)
        stream = TokenStream(config)
        stream.start()
        start = time.time()

        if self._inference_fn:
            try:
                text = self._inference_fn(prompt)
                for token in text.split():
                    stream.feed(token + " ")
                    yield token + " "
            except Exception as e:
                yield f"Error: {e}"
        else:
            yield "No inference backend configured"

        result = stream.complete()
        duration = (time.time() - start) * 1000
        yield InferenceResponse(
            text=result,
            tokens=stream.stats.total_tokens,
            duration_ms=duration,
            stream_stats=stream.stats,
        )

    def batch_infer(self, prompts: List[str], task: TaskProfile = TaskProfile.GENERAL) -> List[InferenceResponse]:
        responses: List[InferenceResponse] = []
        for prompt in prompts:
            responses.append(self.infer(prompt, task))
        return responses

    def recommend(self, task: TaskProfile) -> Optional[ProfileRecommendation]:
        vram = self.config.vram_gb or 8.0
        return recommend_model(task, vram)

    def auto_configure(self, vram_gb: float) -> None:
        self.config.vram_gb = vram_gb
        if vram_gb >= 20:
            self.config.fallback_chain = "high_quality"
        elif vram_gb >= 8:
            self.config.fallback_chain = "default"
        else:
            self.config.fallback_chain = "fast"

    def get_profiles(self) -> Dict[str, Any]:
        return {p.name: p.to_dict() for p in ALL_PROFILES.values()}

    def get_config(self) -> Dict[str, Any]:
        return {
            "preferred_backend": self.config.preferred_backend,
            "vram_gb": self.config.vram_gb,
            "fallback_chain": self.config.fallback_chain,
            "stream": self.config.stream,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
