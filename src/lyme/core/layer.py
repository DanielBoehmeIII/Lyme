"""Architecture layers — typed definitions for Lyme's 8-layer architecture."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LayerStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"


@dataclass
class ArchitectureLayer:
    name: str
    description: str
    status: LayerStatus = LayerStatus.ACTIVE
    dependencies: List[str] = field(default_factory=list)
    module_path: str = ""
    version: str = "0.1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "module_path": self.module_path,
            "version": self.version,
        }


ORCHESTRATION_LAYER = ArchitectureLayer(
    name="orchestration",
    description="Multi-agent orchestration, task routing, lifecycle management",
    dependencies=["planning", "execution", "validation"],
    module_path="src/lyme/core/",
)

INFERENCE_LAYER = ArchitectureLayer(
    name="inference",
    description="Local model runtime, streaming, batching, speculative decoding",
    dependencies=[],
    module_path="src/lyme/models/",
)

PLANNING_LAYER = ArchitectureLayer(
    name="planning",
    description="Multi-step planning, dependency reasoning, task decomposition",
    dependencies=["inference", "repo_memory"],
    module_path="src/lyme/planning/",
)

REPO_MEMORY_LAYER = ArchitectureLayer(
    name="repo_memory",
    description="Repository understanding, AST parsing, dependency graphing, semantic indexing",
    dependencies=[],
    module_path="src/lyme/memory/",
)

VALIDATION_LAYER = ArchitectureLayer(
    name="validation",
    description="Test intelligence, diff validation, hallucination detection, rollback",
    dependencies=["execution"],
    module_path="src/lyme/verification/",
)

EXECUTION_LAYER = ArchitectureLayer(
    name="execution",
    description="Safe diff application, sandboxed execution, tool use, CI integration",
    dependencies=["planning"],
    module_path="src/lyme/runtime/",
)

TRAINING_LAYER = ArchitectureLayer(
    name="training",
    description="Fine-tuning, dataset pipelines, synthetic data, human preference",
    status=LayerStatus.EXPERIMENTAL,
    dependencies=["inference", "repo_memory"],
    module_path="src/lyme/training/",
)

UI_LAYER = ArchitectureLayer(
    name="ui",
    description="Terminal UI, dashboards, visualizations, IDE bridge",
    dependencies=[],
    module_path="src/lyme/ui/",
)


@dataclass
class ArchitectureLayers:
    orchestration: ArchitectureLayer = field(default_factory=lambda: ORCHESTRATION_LAYER)
    inference: ArchitectureLayer = field(default_factory=lambda: INFERENCE_LAYER)
    planning: ArchitectureLayer = field(default_factory=lambda: PLANNING_LAYER)
    repo_memory: ArchitectureLayer = field(default_factory=lambda: REPO_MEMORY_LAYER)
    validation: ArchitectureLayer = field(default_factory=lambda: VALIDATION_LAYER)
    execution: ArchitectureLayer = field(default_factory=lambda: EXECUTION_LAYER)
    training: ArchitectureLayer = field(default_factory=lambda: TRAINING_LAYER)
    ui: ArchitectureLayer = field(default_factory=lambda: UI_LAYER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "architecture": "8-layer separation with shared event bus",
            "layers": {k: v.to_dict() for k, v in self.__dict__.items()},
        }

    def all(self) -> List[ArchitectureLayer]:
        return [
            self.orchestration, self.inference, self.planning,
            self.repo_memory, self.validation, self.execution,
            self.training, self.ui,
        ]
