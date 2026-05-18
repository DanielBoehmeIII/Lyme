"""ModelProfiles — task-specific model profiles for coding, planning, repair, summarization."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskProfile(Enum):
    CODING = "coding"
    PLANNING = "planning"
    REPAIR = "repair"
    SUMMARIZATION = "summarization"
    REVIEW = "review"
    GENERAL = "general"


@dataclass
class ProfileRecommendation:
    tier: str  # low, medium, high
    model_name: str
    min_vram_gb: float
    context_window: int
    quantization: str = "Q4_K_M"
    backend: str = "llama.cpp"
    expected_quality: float = 0.5  # 0-1
    expected_speed_tok_s: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "model_name": self.model_name,
            "min_vram_gb": self.min_vram_gb,
            "context_window": self.context_window,
            "quantization": self.quantization,
            "backend": self.backend,
            "expected_quality": self.expected_quality,
            "expected_speed_tok_s": self.expected_speed_tok_s,
        }


@dataclass
class ModelProfile:
    task: TaskProfile
    recommendations: Dict[str, ProfileRecommendation] = field(default_factory=dict)

    def get(self, vram_gb: float) -> Optional[ProfileRecommendation]:
        tiers = [
            ("high", 16.0),
            ("medium", 8.0),
            ("low", 4.0),
        ]
        for tier_name, tier_vram in tiers:
            if vram_gb >= tier_vram and tier_name in self.recommendations:
                return self.recommendations[tier_name]
        return self.recommendations.get("low")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task.value,
            "recommendations": {k: v.to_dict() for k, v in self.recommendations.items()},
        }


CODING_PROFILE = ModelProfile(
    task=TaskProfile.CODING,
    recommendations={
        "high": ProfileRecommendation(
            tier="high", model_name="deepseek-coder-33b",
            min_vram_gb=20, context_window=16384,
            expected_quality=0.9, expected_speed_tok_s=8,
        ),
        "medium": ProfileRecommendation(
            tier="medium", model_name="deepseek-coder-6.7b",
            min_vram_gb=8, context_window=16384,
            expected_quality=0.75, expected_speed_tok_s=20,
        ),
        "low": ProfileRecommendation(
            tier="low", model_name="qwen2.5-coder-1.5b",
            min_vram_gb=2, context_window=32768,
            expected_quality=0.5, expected_speed_tok_s=40,
        ),
    },
)

PLANNING_PROFILE = ModelProfile(
    task=TaskProfile.PLANNING,
    recommendations={
        "high": ProfileRecommendation(
            tier="high", model_name="deepseek-r1-distill-qwen-32b",
            min_vram_gb=24, context_window=32768,
            expected_quality=0.85, expected_speed_tok_s=5,
        ),
        "medium": ProfileRecommendation(
            tier="medium", model_name="qwen2.5-14b",
            min_vram_gb=12, context_window=32768,
            expected_quality=0.7, expected_speed_tok_s=15,
        ),
        "low": ProfileRecommendation(
            tier="low", model_name="qwen2.5-7b",
            min_vram_gb=6, context_window=32768,
            expected_quality=0.55, expected_speed_tok_s=25,
        ),
    },
)

REPAIR_PROFILE = ModelProfile(
    task=TaskProfile.REPAIR,
    recommendations={
        "high": ProfileRecommendation(
            tier="high", model_name="deepseek-coder-33b",
            min_vram_gb=20, context_window=16384,
            expected_quality=0.85, expected_speed_tok_s=8, backend="llama.cpp",
        ),
        "medium": ProfileRecommendation(
            tier="medium", model_name="codellama-13b",
            min_vram_gb=10, context_window=16384,
            expected_quality=0.7, expected_speed_tok_s=15, backend="llama.cpp",
        ),
        "low": ProfileRecommendation(
            tier="low", model_name="deepseek-coder-1.3b",
            min_vram_gb=2, context_window=8192,
            expected_quality=0.5, expected_speed_tok_s=35, backend="ollama",
        ),
    },
)

SUMMARIZATION_PROFILE = ModelProfile(
    task=TaskProfile.SUMMARIZATION,
    recommendations={
        "high": ProfileRecommendation(
            tier="high", model_name="qwen2.5-14b",
            min_vram_gb=12, context_window=32768,
            expected_quality=0.85, expected_speed_tok_s=20, backend="ollama",
        ),
        "medium": ProfileRecommendation(
            tier="medium", model_name="qwen2.5-7b",
            min_vram_gb=6, context_window=32768,
            expected_quality=0.75, expected_speed_tok_s=30, backend="ollama",
        ),
        "low": ProfileRecommendation(
            tier="low", model_name="phi-3-mini-4k",
            min_vram_gb=3, context_window=4096,
            expected_quality=0.6, expected_speed_tok_s=40, backend="ollama",
        ),
    },
)

ALL_PROFILES: Dict[TaskProfile, ModelProfile] = {
    TaskProfile.CODING: CODING_PROFILE,
    TaskProfile.PLANNING: PLANNING_PROFILE,
    TaskProfile.REPAIR: REPAIR_PROFILE,
    TaskProfile.SUMMARIZATION: SUMMARIZATION_PROFILE,
}


def get_profile(task: TaskProfile) -> ModelProfile:
    return ALL_PROFILES.get(task, CODING_PROFILE)


def recommend_model(task: TaskProfile, vram_gb: float) -> Optional[ProfileRecommendation]:
    profile = get_profile(task)
    return profile.get(vram_gb)
