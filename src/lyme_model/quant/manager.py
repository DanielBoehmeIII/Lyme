"""QuantizationManager — manages model quantization lifecycle."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import QuantConfig, QuantMethod


@dataclass
class QuantizedModel:
    original_name: str
    method: QuantMethod
    path: str = ""
    vram_gb: float = 0.0
    quality_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_name": self.original_name,
            "method": self.method.value,
            "path": self.path,
            "vram_gb": self.vram_gb,
            "quality_score": self.quality_score,
        }


class QuantizationManager:
    def __init__(self):
        self._quantized: Dict[str, QuantizedModel] = {}

    def quantize(self, model_name: str, config: QuantConfig) -> Optional[QuantizedModel]:
        vram = config.estimated_vram_gb(7.0)
        quality_drop = {
            QuantMethod.Q4_K_M: 0.05,
            QuantMethod.Q5_K_M: 0.03,
            QuantMethod.Q8_0: 0.01,
            QuantMethod.NF4: 0.08,
            QuantMethod.INT4: 0.10,
            QuantMethod.INT8: 0.02,
        }.get(config.method, 0.0)

        qm = QuantizedModel(
            original_name=model_name,
            method=config.method,
            path=f"models/{model_name}/{config.method.value}",
            vram_gb=vram,
            quality_score=max(0.0, 1.0 - quality_drop),
        )
        self._quantized[model_name] = qm
        return qm

    def get(self, model_name: str) -> Optional[QuantizedModel]:
        return self._quantized.get(model_name)

    def list_quantized(self) -> List[QuantizedModel]:
        return list(self._quantized.values())

    def best_for_vram(self, model_name: str, vram_gb: float) -> Optional[QuantizedModel]:
        for method in [QuantMethod.Q8_0, QuantMethod.Q5_K_M, QuantMethod.Q4_K_M, QuantMethod.INT4]:
            config = QuantConfig(method=method)
            estimated = config.estimated_vram_gb(7.0)
            if estimated <= vram_gb:
                return self.quantize(model_name, config)
        return None
