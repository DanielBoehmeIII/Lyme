"""InferenceOptimization — KV cache, speculative decoding, quantization experiments."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class QuantLevel(Enum):
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    NF4 = "nf4"
    FP8 = "fp8"


@dataclass
class KVCacheConfig:
    enabled: bool = True
    max_cache_size: int = 4096
    reuse_across_calls: bool = True
    compression: str = "none"


@dataclass
class SpecDecodeConfig:
    enabled: bool = False
    draft_model: str = ""
    max_draft_tokens: int = 5
    accept_threshold: float = 0.9


@dataclass
class InferenceOptConfig:
    kv_cache: KVCacheConfig = field(default_factory=KVCacheConfig)
    spec_decode: SpecDecodeConfig = field(default_factory=SpecDecodeConfig)
    quant_level: QuantLevel = QuantLevel.NF4
    flash_attention: bool = True
    continuous_batch: bool = False
    max_batch_size: int = 1


@dataclass
class SpeedBenchmark:
    tokens_per_second: float = 0.0
    time_to_first_token_ms: float = 0.0
    memory_peak_gb: float = 0.0
    speedup_vs_baseline: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens_per_second": round(self.tokens_per_second, 2),
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
            "memory_peak_gb": round(self.memory_peak_gb, 2),
            "speedup": round(self.speedup_vs_baseline, 2),
        }


class InferenceOptimizer:
    def __init__(self, config: InferenceOptConfig = None):
        self.config = config or InferenceOptConfig()
        self._infer_fn: Optional[Callable] = None

    def set_inference_fn(self, fn: Callable) -> None:
        self._infer_fn = fn

    def benchmark(self, prompts: List[str]) -> SpeedBenchmark:
        import time
        result = SpeedBenchmark()
        start = time.time()
        total_tokens = 0
        first = True

        for prompt in prompts:
            if self._infer_fn:
                output = self._infer_fn(prompt)
                tokens = len(output.split())
                total_tokens += tokens
                if first:
                    result.time_to_first_token_ms = (time.time() - start) * 1000
                    first = False

        elapsed = time.time() - start
        result.tokens_per_second = total_tokens / max(elapsed, 0.001)
        return result

    def estimate_speedup(self) -> Dict[str, float]:
        speedups = {}
        if self.config.kv_cache.enabled and self.config.kv_cache.reuse_across_calls:
            speedups["kv_cache"] = 1.5
        if self.config.spec_decode.enabled:
            speedups["spec_decode"] = 2.0
        if self.config.quant_level in (QuantLevel.INT8, QuantLevel.INT4, QuantLevel.NF4):
            speedups["quantization"] = 1.3
        if self.config.flash_attention:
            speedups["flash_attention"] = 1.2
        if self.config.continuous_batch:
            speedups["continuous_batch"] = 3.0
        return speedups
