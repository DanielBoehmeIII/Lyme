from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .layer1_tree import FileTreeLayer
from .layer2_apis import APILayer
from .layer3_subsystems import SubsystemLayer
from .layer4_invariants import InvariantLayer
from .layer5_rehydration import RehydrationLayer
from .context_budget import ContextBudgetOptimizer
from .summarizer import RepoSummarizer


@dataclass
class CompressionResult:
    layer1_tree: Dict[str, Any]
    layer2_apis: Dict[str, Any]
    layer3_subsystems: Dict[str, Any]
    layer4_invariants: Dict[str, Any]
    layer5_rehydration: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer1_tree": self.layer1_tree,
            "layer2_apis": self.layer2_apis,
            "layer3_subsystems": self.layer3_subsystems,
            "layer4_invariants": self.layer4_invariants,
            "layer5_rehydration": self.layer5_rehydration,
        }


@dataclass
class CompressionPipeline:
    layers: List[Any] = field(default_factory=list)

    def add_layer(self, layer: Any) -> CompressionPipeline:
        self.layers.append(layer)
        return self

    def run(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for layer in self.layers:
            layer_name = layer.__class__.__name__.lower()
            results[layer_name] = layer.extract(repo_path, **kwargs)
        return results


class CodebaseCompressor:
    def __init__(
        self,
        repo_path: Optional[str] = None,
        pipeline: Optional[CompressionPipeline] = None,
    ):
        self.repo_path = Path(repo_path).resolve() if repo_path else None
        self._result: Optional[CompressionResult] = None
        self._pipeline = pipeline or self._default_pipeline()

    def _default_pipeline(self) -> CompressionPipeline:
        return CompressionPipeline().add_layer(FileTreeLayer()).add_layer(
            APILayer()
        ).add_layer(SubsystemLayer()).add_layer(InvariantLayer())

    def compress(self, repo_path: Optional[str] = None) -> CompressionResult:
        path = Path(repo_path or self.repo_path).resolve()
        raw = self._pipeline.run(path)
        self._result = CompressionResult(
            layer1_tree=raw.get("filetreelayer", {}),
            layer2_apis=raw.get("apilayer", {}),
            layer3_subsystems=raw.get("subsystemlayer", {}),
            layer4_invariants=raw.get("invariantlayer", {}),
        )
        return self._result

    def get_layer(self, n: int) -> Dict[str, Any]:
        if not self._result:
            raise ValueError("No compression result. Call compress() first.")
        layers = [
            self._result.layer1_tree,
            self._result.layer2_apis,
            self._result.layer3_subsystems,
            self._result.layer4_invariants,
        ]
        if n < 1 or n > len(layers):
            raise IndexError(f"Layer index {n} out of range [1, {len(layers)}]")
        return layers[n - 1]

    def get_rehydration_packet(self, task: str) -> Dict[str, Any]:
        if not self._result:
            raise ValueError("No compression result. Call compress() first.")
        rehydrator = RehydrationLayer()
        self._result.layer5_rehydration = rehydrator.rehydrate(
            task=task,
            layer1_tree=self._result.layer1_tree,
            layer2_apis=self._result.layer2_apis,
            layer3_subsystems=self._result.layer3_subsystems,
            layer4_invariants=self._result.layer4_invariants,
            repo_path=self.repo_path,
        )
        return self._result.layer5_rehydration

    def get_summary(self, model_context_limit: int = 128_000) -> str:
        if not self._result:
            raise ValueError("No compression result. Call compress() first.")
        summarizer = RepoSummarizer()
        return summarizer.summarize(
            layers=self._result.to_dict(),
            context_limit=model_context_limit,
        )

    def to_json(self, indent: int = 2) -> str:
        if not self._result:
            raise ValueError("No compression result. Call compress() first.")
        return json.dumps(self._result.to_dict(), indent=indent, default=str)

    @classmethod
    def from_pipeline(cls, pipeline: CompressionPipeline) -> CodebaseCompressor:
        return cls(pipeline=pipeline)
