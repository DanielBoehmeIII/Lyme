"""PrivateInference — on-premises inference for airgapped environments."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class InferenceEndpoint:
    name: str = ""
    url: str = ""
    model: str = ""
    backend: str = "llama.cpp"
    status: str = "unknown"


class PrivateInference:
    def __init__(self):
        self._endpoints: Dict[str, InferenceEndpoint] = {}
        self._local_fn: Optional[Callable] = None

    def set_local_fn(self, fn: Callable) -> None:
        self._local_fn = fn

    def add_endpoint(self, ep: InferenceEndpoint) -> None:
        self._endpoints[ep.name] = ep

    def infer(self, prompt: str, endpoint: str = "local") -> str:
        if endpoint == "local" and self._local_fn:
            return self._local_fn(prompt)
        ep = self._endpoints.get(endpoint)
        if ep:
            return f"[{ep.name}] simulated: {prompt[:50]}..."
        return "No inference endpoint available"

    def list_endpoints(self) -> List[Dict[str, Any]]:
        return [{"name": n, "model": e.model, "backend": e.backend, "status": e.status}
                for n, e in self._endpoints.items()]
