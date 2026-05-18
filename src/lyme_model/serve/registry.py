"""ServerRegistry — registry of available model servers and endpoints."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegisteredModel:
    name: str
    backend: str
    endpoint: str = ""
    status: str = "registered"
    vram_gb: float = 0.0
    context_window: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "backend": self.backend,
            "endpoint": self.endpoint,
            "status": self.status,
            "vram_gb": self.vram_gb,
            "context_window": self.context_window,
        }


class ServerRegistry:
    def __init__(self):
        self._models: Dict[str, RegisteredModel] = {}

    def register(self, model: RegisteredModel) -> None:
        self._models[model.name] = model

    def unregister(self, name: str) -> None:
        self._models.pop(name, None)

    def get(self, name: str) -> Optional[RegisteredModel]:
        return self._models.get(name)

    def list(self, backend: Optional[str] = None) -> List[RegisteredModel]:
        models = list(self._models.values())
        if backend:
            models = [m for m in models if m.backend == backend]
        return models

    def available(self) -> List[RegisteredModel]:
        return [m for m in self._models.values() if m.status == "running"]

    def count(self) -> int:
        return len(self._models)
