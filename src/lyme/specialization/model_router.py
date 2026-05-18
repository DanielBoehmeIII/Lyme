"""ModelRouter — selects models based on task requirements + hardware profile."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class HardwareTier(str, Enum):
    LOW = "4gb"
    MEDIUM = "8gb"
    HIGH = "12gb"
    ULTRA = "24gb"


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class ModelProfile:
    name: str
    path: str
    parameter_size_b: float
    hardware_minimum: str
    context_window: int
    speed_rating: float
    quality_rating: float
    supported_tasks: List[str]
    quantization_options: List[str]
    is_local: bool = True
    requires_gpu: bool = False
    vram_usage_gb: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "parameter_size": f"{self.parameter_size_b}B",
            "hardware_min": self.hardware_minimum,
            "context_window": self.context_window,
            "quality": self.quality_rating,
            "speed": self.speed_rating,
        }


@dataclass
class ModelSelection:
    model: ModelProfile
    quantization: str
    estimated_vram_gb: float
    estimated_speed: str
    confidence: float
    rationale: str
    alternatives: List[str]

    def to_dict(self) -> Dict:
        return {
            "model": self.model.name,
            "quantization": self.quantization,
            "estimated_vram": round(self.estimated_vram_gb, 1),
            "estimated_speed": self.estimated_speed,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale[:80],
        }


@dataclass
class RouterProfileReport:
    available_models: List[Dict]
    recommended_for_hardware: List[Dict]
    task_coverage: Dict[str, List[str]]
    insights: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  MODEL ROUTER PROFILE")
        lines.append("=" * 70)
        lines.append(f"  Available Models: {len(self.available_models)}")
        lines.append("")
        lines.append("  Recommended:")
        for r in self.recommended_for_hardware[:3]:
            lines.append(f"    {r['model']} ({r['quantization']}) — {r['rationale'][:50]}")
        lines.append("")
        lines.append("  Task Coverage:")
        for task, models in sorted(self.task_coverage.items(), key=lambda x: -len(x[1]))[:5]:
            lines.append(f"    {task}: {len(models)} models ({', '.join(models[:3])})")
        if self.insights:
            lines.append("-" * 70)
            for ins in self.insights:
                lines.append(f"  • {ins}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ModelRouter:
    def __init__(self):
        self._models: Dict[str, ModelProfile] = {}
        self._build_default_models()

    def _build_default_models(self) -> None:
        defaults = [
            ModelProfile("Qwen2.5-Coder-0.5B", "qwen2.5-coder:0.5b", 0.5,
                        "4gb", 32768, 0.95, 0.3, ["simple_edit", "doc", "format"],
                        ["Q8_0", "Q4_K_M"], vram_usage_gb=0.5),
            ModelProfile("Qwen2.5-Coder-1.5B", "qwen2.5-coder:1.5b", 1.5,
                        "4gb", 32768, 0.85, 0.45, ["simple_edit", "qa", "doc", "review"],
                        ["Q8_0", "Q4_K_M", "Q3_K_S"], vram_usage_gb=1.2),
            ModelProfile("Qwen2.5-Coder-7B", "qwen2.5-coder:7b", 7,
                        "8gb", 32768, 0.6, 0.75, ["planning", "editing", "review", "debug", "refactor"],
                        ["Q8_0", "Q5_K_M", "Q4_K_M", "Q3_K_S"], vram_usage_gb=5.5),
            ModelProfile("DeepSeek-Coder-6.7B", "deepseek-coder:6.7b", 6.7,
                        "8gb", 16384, 0.55, 0.78, ["planning", "editing", "debug", "test_repair"],
                        ["Q8_0", "Q5_K_M", "Q4_K_M"], vram_usage_gb=5.0),
            ModelProfile("CodeLlama-7B", "codellama:7b", 7,
                        "8gb", 16384, 0.5, 0.65, ["editing", "review", "doc"],
                        ["Q8_0", "Q4_K_M"], vram_usage_gb=5.2),
            ModelProfile("Qwen2.5-Coder-14B", "qwen2.5-coder:14b", 14,
                        "12gb", 32768, 0.4, 0.85, ["planning", "complex_edit", "architecture", "review"],
                        ["Q5_K_M", "Q4_K_M", "Q3_K_S"], vram_usage_gb=10.0),
            ModelProfile("DeepSeek-Coder-33B", "deepseek-coder:33b", 33,
                        "24gb", 16384, 0.25, 0.9, ["architecture", "complex_planning", "code_review"],
                        ["Q4_K_M", "Q3_K_S"], vram_usage_gb=20.0),
            ModelProfile("Llama-3-70B", "llama3:70b", 70,
                        "48gb", 8192, 0.15, 0.92, ["architecture", "design", "complex_reasoning"],
                        ["Q4_K_M", "Q3_K_S"], vram_usage_gb=40.0, requires_gpu=True),
        ]
        for m in defaults:
            self._models[m.name] = m

    def register_model(self, profile: ModelProfile) -> None:
        self._models[profile.name] = profile

    def select(self, task_type: str, task_complexity: TaskComplexity,
               hardware_tier: HardwareTier,
               priority: str = "quality") -> ModelSelection:
        eligible = []
        for name, model in self._models.items():
            if task_type not in model.supported_tasks:
                continue
            if not self._hardware_compatible(model, hardware_tier):
                continue
            eligible.append(model)

        if not eligible:
            eligible = [m for m in self._models.values()
                       if self._hardware_compatible(m, hardware_tier)]

        if not eligible:
            fallback = list(self._models.values())[0]
            return ModelSelection(
                model=fallback, quantization="Q4_K_M",
                estimated_vram_gb=fallback.vram_usage_gb,
                estimated_speed="unknown",
                confidence=0.2,
                rationale=f"No model supports '{task_type}' on {hardware_tier.value}",
                alternatives=[],
            )

        if priority == "quality":
            eligible.sort(key=lambda m: -m.quality_rating)
        else:
            eligible.sort(key=lambda m: -m.speed_rating)

        selected = eligible[0]
        quantization = self._pick_quantization(selected, hardware_tier)

        alternatives = [m.name for m in eligible[1:4]]

        speed_labels = {0.9: "very fast", 0.7: "fast", 0.5: "moderate",
                       0.3: "slow", 0.1: "very slow"}
        speed_label = "moderate"
        for threshold, label in sorted(speed_labels.items(), reverse=True):
            if selected.speed_rating >= threshold:
                speed_label = label
                break

        return ModelSelection(
            model=selected,
            quantization=quantization,
            estimated_vram_gb=selected.vram_usage_gb,
            estimated_speed=speed_label,
            confidence=selected.quality_rating * 0.7 + selected.speed_rating * 0.3,
            rationale=f"{selected.name} ({quantization}) on {hardware_tier.value} hardware",
            alternatives=alternatives,
        )

    def _hardware_compatible(self, model: ModelProfile, tier: HardwareTier) -> bool:
        tiers = {"4gb": 0, "8gb": 1, "12gb": 2, "24gb": 3, "48gb": 4}
        model_idx = tiers.get(model.hardware_minimum, 99)
        hw_idx = tiers.get(tier.value, 0)
        return hw_idx >= model_idx

    def _pick_quantization(self, model: ModelProfile, tier: HardwareTier) -> str:
        if not model.quantization_options:
            return "Q4_K_M"
        vram_map = {"4gb": 3, "8gb": 6, "12gb": 10, "24gb": 18, "48gb": 40}
        available = model.vram_usage_gb
        hw_vram = vram_map.get(tier.value, 8)

        for q in model.quantization_options:
            if "Q8" in q and hw_vram >= available * 2:
                return q
        for q in model.quantization_options:
            if "Q5" in q and hw_vram >= available * 1.5:
                return q
        for q in model.quantization_options:
            if "Q4" in q and hw_vram >= available:
                return q
        return model.quantization_options[-1]

    def profile(self, hardware_tier: HardwareTier) -> RouterProfileReport:
        compatible = [m for m in self._models.values()
                     if self._hardware_compatible(m, hardware_tier)]
        recs = [self.select("planning", TaskComplexity.MODERATE, hardware_tier).to_dict()]

        task_coverage: Dict[str, List[str]] = {}
        for m in compatible:
            for task in m.supported_tasks:
                if task not in task_coverage:
                    task_coverage[task] = []
                task_coverage[task].append(m.name)

        insights: List[str] = []
        uncovered = [task for task, models in task_coverage.items() if not models]
        if uncovered:
            insights.append(f"No model covers: {', '.join(uncovered[:3])}")
        insights.append(f"{len(compatible)}/{len(self._models)} models compatible with {hardware_tier.value}")

        return RouterProfileReport(
            available_models=[m.to_dict() for m in self._models.values()],
            recommended_for_hardware=recs,
            task_coverage=task_coverage,
            insights=insights,
        )
