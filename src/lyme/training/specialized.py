"""SpecializedSubmodels — training profiles for planner, patch, review, and summarizer models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubmodelProfile:
    name: str
    role: str
    base_model: str = ""
    dataset_path: str = ""
    training_config: Dict[str, Any] = field(default_factory=dict)
    eval_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "base_model": self.base_model,
            "dataset_path": self.dataset_path,
            "eval_metrics": self.eval_metrics,
        }


PLANNER_MODEL = SubmodelProfile(
    name="lyme-planner", role="planner",
    base_model="Qwen2.5-7B",
    dataset_path="datasets/v2/sft/planning",
    training_config={"lora_r": 16, "num_epochs": 3, "learning_rate": 2e-4},
)

PATCH_MODEL = SubmodelProfile(
    name="lyme-patcher", role="patch",
    base_model="DeepSeek-Coder-6.7B",
    dataset_path="datasets/v2/sft/patch",
    training_config={"lora_r": 16, "num_epochs": 5, "learning_rate": 1e-4},
)

REVIEW_MODEL = SubmodelProfile(
    name="lyme-reviewer", role="review",
    base_model="Qwen2.5-7B",
    dataset_path="datasets/v2/preference",
    training_config={"lora_r": 8, "num_epochs": 2, "learning_rate": 3e-5},
)

SUMMARIZER_MODEL = SubmodelProfile(
    name="lyme-summarizer", role="summarizer",
    base_model="Phi-3-Mini-4K",
    dataset_path="datasets/v2/sft/summary",
    training_config={"lora_r": 8, "num_epochs": 2, "learning_rate": 3e-4},
)

ALL_SUBMODELS = [PLANNER_MODEL, PATCH_MODEL, REVIEW_MODEL, SUMMARIZER_MODEL]


class SpecializedModelManager:
    def __init__(self):
        self._models: Dict[str, SubmodelProfile] = {
            m.name: m for m in ALL_SUBMODELS
        }

    def get(self, name: str) -> Optional[SubmodelProfile]:
        return self._models.get(name)

    def list_models(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in ALL_SUBMODELS]

    def routing_map(self, task_type: str) -> Optional[str]:
        routing = {
            "planning": "lyme-planner",
            "coding": "lyme-patcher",
            "review": "lyme-reviewer",
            "summarization": "lyme-summarizer",
        }
        name = routing.get(task_type)
        return name if name in self._models else None
