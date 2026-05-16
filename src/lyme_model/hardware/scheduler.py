"""Week 91 — Hardware-Aware Scheduling for Lyme Model.

Decides:
- which model to load
- when to unload
- CPU vs GPU route
- quantization level
- context size
- parallel vs sequential tools
- fallback mode
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone


class ComputeBackend(str, Enum):
    GPU = "gpu"
    CPU = "cpu"
    HYBRID = "hybrid"


class TaskDifficulty(str, Enum):
    EASY = "easy"       # lint fix, import sort
    MEDIUM = "medium"   # single-file edit, test addition
    HARD = "hard"       # multi-file edit, refactor
    COMPLEX = "complex" # architecture change, cross-cutting concern


@dataclass
class SchedulingDecision:
    model: str = ""
    quantization: str = "Q4"
    backend: ComputeBackend = ComputeBackend.GPU
    max_context: int = 4096
    parallel_tools: bool = False
    fallback_enabled: bool = True
    unload_after_idle_s: int = 300
    reasoning: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "quantization": self.quantization,
            "backend": self.backend.value,
            "max_context": self.max_context,
            "parallel_tools": self.parallel_tools,
            "fallback_enabled": self.fallback_enabled,
            "unload_after_idle_s": self.unload_after_idle_s,
            "reasoning": self.reasoning[:5],
            "confidence": round(self.confidence, 2),
        }

    def summary(self) -> str:
        lines = [
            f"**Model:** {self.model} ({self.quantization})",
            f"**Backend:** {self.backend.value}",
            f"**Context:** {self.max_context} tokens",
            f"**Parallel tools:** {self.parallel_tools}",
            f"**Fallback:** {self.fallback_enabled}",
            "",
            "**Reasoning:**",
        ]
        for r in self.reasoning:
            lines.append(f"- {r}")
        return "\n".join(lines)


@dataclass
class HardwareState:
    vram_total_mb: int = 0
    vram_available_mb: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    gpu_present: bool = False
    gpu_name: str = ""
    cpu_cores: int = 0
    current_load: float = 0.0
    model_loaded: bool = False
    loaded_model: str = ""

    @property
    def can_use_gpu(self) -> bool:
        return self.gpu_present and self.vram_available_mb > 2000


@dataclass
class TaskRequirements:
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    estimated_context: int = 4096
    needs_code_generation: bool = True
    needs_test_execution: bool = False
    needs_retrieval: bool = True
    latency_target_s: float = 30.0
    quality_target: float = 0.8


MODEL_CATALOG = [
    {"name": "qwen2.5-coder:1.5b", "params_b": 1.5, "vram_q4": 1200, "vram_q8": 2200, "quality": 0.5, "speed": 40, "context": 4096},
    {"name": "qwen2.5-coder:3b",   "params_b": 3.0, "vram_q4": 2200, "vram_q8": 4000, "quality": 0.65, "speed": 25, "context": 8192},
    {"name": "qwen2.5-coder:7b",   "params_b": 7.0, "vram_q4": 4500, "vram_q8": 8000, "quality": 0.8, "speed": 15, "context": 8192},
    {"name": "deepseek-coder:6.7b", "params_b": 6.7, "vram_q4": 4200, "vram_q8": 7500, "quality": 0.82, "speed": 14, "context": 16384},
    {"name": "codegemma:7b",        "params_b": 7.0, "vram_q4": 4500, "vram_q8": 8000, "quality": 0.78, "speed": 16, "context": 8192},
    {"name": "codellama:7b",        "params_b": 7.0, "vram_q4": 4500, "vram_q8": 8000, "quality": 0.75, "speed": 15, "context": 16384},
    {"name": "llama3:8b",           "params_b": 8.0, "vram_q4": 5000, "vram_q8": 9000, "quality": 0.76, "speed": 14, "context": 8192},
]


class HardwareScheduler:
    """Makes hardware-aware scheduling decisions for Lyme Model."""

    def __init__(self):
        self.decisions: List[SchedulingDecision] = []

    def decide(
        self,
        state: HardwareState,
        task: Optional[TaskRequirements] = None,
    ) -> SchedulingDecision:
        task = task or TaskRequirements()
        reasoning = []
        now = datetime.now(timezone.utc).isoformat()

        # 1. Determine backend
        if state.can_use_gpu:
            backend = ComputeBackend.GPU
            reasoning.append(f"GPU available: {state.gpu_name} ({state.vram_available_mb}MB free)")
        else:
            backend = ComputeBackend.CPU
            reasoning.append("No GPU available, using CPU")

        # 2. Select quantization
        if state.vram_total_mb < 4000:
            quant = "Q4"
            reasoning.append("Low VRAM: using Q4 quantization")
        elif state.vram_total_mb < 8000:
            quant = "Q4"
            reasoning.append("Moderate VRAM: Q4 to leave room for context")
        else:
            quant = "Q8"
            reasoning.append("Sufficient VRAM: using Q8 for quality")

        # 3. Select best model
        selected_model = self._select_model(state, task, quant)
        reasoning.append(f"Selected model: {selected_model['name']} ({quant}, quality={selected_model['quality']})")

        # 4. Determine context size
        if state.vram_total_mb > 0 and selected_model["vram_q4"] > 0:
            vram_after_model = state.vram_total_mb - selected_model.get(f"vram_{quant.lower()}", selected_model["vram_q4"])
            kv_context_per_token = 0.002 * 1024  # MB per token
            est_context = int((vram_after_model - 512) / kv_context_per_token) if vram_after_model > 512 else 2048
            max_context = min(est_context, task.estimated_context, selected_model["context"])
        else:
            max_context = min(task.estimated_context, 4096)

        reasoning.append(f"Context budget: {max_context} tokens")

        # 5. Parallel vs sequential tools
        parallel = task.difficulty in (TaskDifficulty.EASY, TaskDifficulty.MEDIUM) and backend == ComputeBackend.GPU
        reasoning.append(f"Parallel tools: {'enabled' if parallel else 'disabled'}")

        # 6. Fallback mode
        fallback = state.vram_total_mb < 4000 or not state.gpu_present
        if fallback:
            reasoning.append("Fallback enabled: limited hardware detected")

        # 7. Unload timeout
        unload_s = 120 if state.vram_total_mb < 4000 else 300

        decision = SchedulingDecision(
            model=selected_model["name"],
            quantization=quant,
            backend=backend,
            max_context=max_context,
            parallel_tools=parallel,
            fallback_enabled=fallback,
            unload_after_idle_s=unload_s,
            reasoning=reasoning,
            confidence=0.85 if state.gpu_present else 0.7,
            timestamp=now,
        )
        self.decisions.append(decision)
        return decision

    def _select_model(self, state: HardwareState, task: TaskRequirements,
                      quant: str) -> dict:
        """Select the best model for the given hardware and task."""
        difficulty_map = {
            TaskDifficulty.EASY: 0.4,
            TaskDifficulty.MEDIUM: 0.6,
            TaskDifficulty.HARD: 0.75,
            TaskDifficulty.COMPLEX: 0.85,
        }
        min_quality = difficulty_map.get(task.difficulty, 0.5)

        feasible = []
        for model in MODEL_CATALOG:
            vram_needed = model.get(f"vram_{quant.lower()}", model["vram_q4"])
            vram_ok = vram_needed <= state.vram_total_mb if state.vram_total_mb > 0 else True
            quality_ok = model["quality"] >= min_quality
            if vram_ok and quality_ok:
                feasible.append(model)

        if not feasible:
            feasible = sorted(MODEL_CATALOG, key=lambda m: m["vram_q4"])

        return feasible[0]

    def should_unload(self, state: HardwareState, idle_seconds: int) -> bool:
        """Decide whether to unload the current model."""
        if not state.model_loaded:
            return False
        threshold = 120 if state.vram_total_mb < 4000 else 300
        return idle_seconds > threshold

    def select_quantization(self, state: HardwareState) -> str:
        if state.vram_total_mb < 3000:
            return "Q4"
        elif state.vram_total_mb < 8000:
            return "Q4"
        return "Q8"
