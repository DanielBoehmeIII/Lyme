"""ModelPack — distributable model configuration packs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelPackConfig:
    name: str = ""
    models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    default_profile: str = "coding"
    min_vram_gb: float = 8.0


class ModelPack:
    def __init__(self, config: ModelPackConfig):
        self.config = config

    def get_model(self, role: str) -> Optional[Dict[str, Any]]:
        return self.config.models.get(role)

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"role": role, **cfg}
            for role, cfg in self.config.models.items()
        ]

    @classmethod
    def default_coding(cls) -> "ModelPack":
        return cls(ModelPackConfig(
            name="default-coding",
            models={
                "planning": {"model": "qwen2.5-7b", "backend": "ollama"},
                "coding": {"model": "deepseek-coder-6.7b", "backend": "llama.cpp"},
                "review": {"model": "qwen2.5-7b", "backend": "ollama"},
                "repair": {"model": "deepseek-coder-1.3b", "backend": "llama.cpp"},
            },
        ))

    @classmethod
    def light(cls) -> "ModelPack":
        return cls(ModelPackConfig(
            name="light",
            models={
                "coding": {"model": "qwen2.5-coder-1.5b", "backend": "ollama"},
                "planning": {"model": "phi-3-mini-4k", "backend": "llama.cpp"},
            },
            min_vram_gb=4.0,
        ))
