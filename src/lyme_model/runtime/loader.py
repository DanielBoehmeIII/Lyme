"""Model loader — manages model discovery and selection for Lyme Model."""

from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class ModelInfo:
    name: str
    size: str  # "3B", "7B", "8B", etc.
    quantization: str = "Q4"
    backend: str = "transformers"
    local: bool = True

    def to_dict(self) -> dict:
        return {"name": self.name, "size": self.size,
                "quantization": self.quantization, "backend": self.backend,
                "local": self.local}


class ModelLoader:
    """Manages model discovery and selection."""

    AVAILABLE_MODELS = {
        "deepseek-ai/deepseek-coder-6.7b-instruct": ModelInfo("deepseek-ai/deepseek-coder-6.7b-instruct", "6.7B", "Q4"),
        "deepseek-ai/deepseek-coder-1.3b-instruct": ModelInfo("deepseek-ai/deepseek-coder-1.3b-instruct", "1.3B", "fp16"),
    }

    @classmethod
    def list_models(cls) -> List[ModelInfo]:
        return list(cls.AVAILABLE_MODELS.values())

    @classmethod
    def get_model(cls, name: str) -> Optional[ModelInfo]:
        return cls.AVAILABLE_MODELS.get(name)

    @classmethod
    def recommend_for_hardware(cls, vram_mb: int) -> List[ModelInfo]:
        """Recommend models based on available VRAM."""
        if vram_mb >= 12000:
            return [cls.AVAILABLE_MODELS["deepseek-ai/deepseek-coder-6.7b-instruct"]]
        elif vram_mb >= 6000:
            return [cls.AVAILABLE_MODELS["deepseek-ai/deepseek-coder-6.7b-instruct"]]
        else:
            return []
