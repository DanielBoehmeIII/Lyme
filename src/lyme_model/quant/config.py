"""QuantConfig — quantization configuration for model compression."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QuantMethod(Enum):
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    NF4 = "nf4"
    FP4 = "fp4"
    Q4_K_M = "q4_k_m"
    Q5_K_M = "q5_k_m"
    Q8_0 = "q8_0"


@dataclass
class BitsAndBytesConfig:
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True


@dataclass
class QuantConfig:
    method: QuantMethod = QuantMethod.Q4_K_M
    bits: int = 4
    backend: str = "auto"
    bnb: BitsAndBytesConfig = field(default_factory=BitsAndBytesConfig)
    calibrate: bool = False
    dataset: str = ""

    def estimated_vram_gb(self, model_params_b: float) -> float:
        factor = {
            QuantMethod.NONE: 2.0,
            QuantMethod.INT8: 1.0,
            QuantMethod.INT4: 0.6,
            QuantMethod.NF4: 0.6,
            QuantMethod.FP4: 0.6,
            QuantMethod.Q4_K_M: 0.55,
            QuantMethod.Q5_K_M: 0.65,
            QuantMethod.Q8_0: 0.85,
        }.get(self.method, 1.0)
        return model_params_b * factor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "bits": self.bits,
            "backend": self.backend,
            "bnb": self.bnb.__dict__,
            "calibrate": self.calibrate,
        }
