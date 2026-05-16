"""Week 117 — Lyme Model Mode Selection.

Modes:
- local fast
- local careful
- local multi-candidate
- local with critic
- local with human checkpoint
- fallback to stronger model if configured
- audit-only

Mode chosen by:
- task difficulty
- hardware
- risk
- repo size
- user preference
- previous success rate

Every mode choice is explained.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import time


class Mode(Enum):
    LOCAL_FAST = "local_fast"
    LOCAL_CAREFUL = "local_careful"
    LOCAL_MULTI_CANDIDATE = "local_multi_candidate"
    LOCAL_WITH_CRITIC = "local_with_critic"
    LOCAL_WITH_HUMAN_CHECKPOINT = "local_with_human_checkpoint"
    FALLBACK_STRONGER = "fallback_stronger"
    AUDIT_ONLY = "audit_only"


MODE_DESCRIPTIONS = {
    Mode.LOCAL_FAST: "Fastest local inference. Single pass, no verification loop. Best for trivial Repo Q&A, simple lookups, well-defined factual queries. Uses small model or static analysis only.",
    Mode.LOCAL_CAREFUL: "Slower local inference with self-verification. Re-checks output against source. Best for bug location, failure explanation, and medium-difficulty tasks where correctness matters but risk is low.",
    Mode.LOCAL_MULTI_CANDIDATE: "Generate N candidate answers, score, pick best. Uses multi-candidate decoding with similarity clustering. Best for ambiguous tasks, code generation, or when single-pass quality is uncertain.",
    Mode.LOCAL_WITH_CRITIC: "Generate answer, then run critic model to check for errors. Iterate if critic flags issues. Best for patch planning and application where correctness is critical and local models may hallucinate.",
    Mode.LOCAL_WITH_HUMAN_CHECKPOINT: "Same as careful or critic mode, but pauses before each edit or high-risk action. Asks user to confirm. Best for destructive operations, dependency changes, or when user lacks full trust in automation.",
    Mode.FALLBACK_STRONGER: "Explicitly fall back to a stronger (possibly cloud) model. Must be explicitly configured by user. Lyme Model never silently calls cloud APIs. Best for very hard tasks, cross-repo analysis, or when local model confidence is too low.",
    Mode.AUDIT_ONLY: "Do not run any model. Only perform audit-safe actions: index repo, measure structure, record observations, check invariants. Best for unfamiliar repos, first-time analysis, or when user wants to understand state before acting.",
}


@dataclass
class ModeSelection:
    selected_mode: Mode
    alternatives: List[Mode]
    selection_reasoning: List[str]
    selection_factors: Dict[str, float]
    user_override: Optional[Mode] = None
    previous_success_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "selected_mode": self.selected_mode.value,
            "alternatives": [m.value for m in self.alternatives],
            "selection_reasoning": self.selection_reasoning,
            "selection_factors": self.selection_factors,
            "user_override": self.user_override.value if self.user_override else None,
            "previous_success_rate": self.previous_success_rate,
            "mode_description": MODE_DESCRIPTIONS.get(self.selected_mode, ""),
        }


@dataclass
class ModeConfig:
    """Configuration for how each mode behaves."""
    model_tier: str  # "small", "medium", "large", "external"
    num_candidates: int
    use_critic: bool
    use_verification: bool
    human_checkpoint: bool
    max_retries: int
    timeout_s: int
    estimated_cost_multiplier: float

    def to_dict(self) -> dict:
        return {
            "model_tier": self.model_tier,
            "num_candidates": self.num_candidates,
            "use_critic": self.use_critic,
            "use_verification": self.use_verification,
            "human_checkpoint": self.human_checkpoint,
            "max_retries": self.max_retries,
            "timeout_s": self.timeout_s,
            "estimated_cost_multiplier": self.estimated_cost_multiplier,
        }


MODE_CONFIGS = {
    Mode.LOCAL_FAST: ModeConfig("small", 1, False, False, False, 1, 30, 1.0),
    Mode.LOCAL_CAREFUL: ModeConfig("medium", 1, False, True, False, 2, 60, 2.0),
    Mode.LOCAL_MULTI_CANDIDATE: ModeConfig("medium", 3, False, True, False, 3, 120, 4.0),
    Mode.LOCAL_WITH_CRITIC: ModeConfig("medium", 1, True, True, False, 3, 180, 3.0),
    Mode.LOCAL_WITH_HUMAN_CHECKPOINT: ModeConfig("medium", 1, True, True, True, 3, 300, 2.5),
    Mode.FALLBACK_STRONGER: ModeConfig("external", 1, True, True, False, 3, 120, 10.0),
    Mode.AUDIT_ONLY: ModeConfig("none", 0, False, False, False, 0, 10, 0.0),
}


# Hardware constraints per mode
HARDWARE_COMPATIBILITY: Dict[str, List[Mode]] = {
    "minimal": [Mode.LOCAL_FAST, Mode.AUDIT_ONLY],
    "cpu_only": [Mode.LOCAL_FAST, Mode.LOCAL_CAREFUL, Mode.AUDIT_ONLY],
    "budget_gpu": [Mode.LOCAL_FAST, Mode.LOCAL_CAREFUL, Mode.LOCAL_WITH_CRITIC, Mode.AUDIT_ONLY],
    "standard_gpu": [Mode.LOCAL_FAST, Mode.LOCAL_CAREFUL, Mode.LOCAL_MULTI_CANDIDATE, Mode.LOCAL_WITH_CRITIC, Mode.LOCAL_WITH_HUMAN_CHECKPOINT, Mode.AUDIT_ONLY],
    "high_end": [Mode.LOCAL_FAST, Mode.LOCAL_CAREFUL, Mode.LOCAL_MULTI_CANDIDATE, Mode.LOCAL_WITH_CRITIC, Mode.LOCAL_WITH_HUMAN_CHECKPOINT, Mode.FALLBACK_STRONGER, Mode.AUDIT_ONLY],
    "unknown": [Mode.LOCAL_FAST, Mode.AUDIT_ONLY],
}


class ModeSelector:
    """Selects Lyme Model mode based on task, hardware, and history."""

    def __init__(self):
        self._success_history: Dict[Mode, List[bool]] = {m: [] for m in Mode}
        self._user_preferences: Dict[str, Mode] = {}

    def set_user_preference(self, task_pattern: str, mode: Mode):
        self._user_preferences[task_pattern] = mode

    def record_outcome(self, mode: Mode, success: bool):
        self._success_history.setdefault(mode, []).append(success)

    def get_success_rate(self, mode: Mode) -> float:
        history = self._success_history.get(mode, [])
        if not history:
            return 0.5
        return sum(history) / len(history)

    def select_mode(self, difficulty_score: float, risk_level: str,
                    hardware_tier: str, repo_file_count: int,
                    user_preference: Optional[Mode] = None,
                    task_type: str = "unknown") -> ModeSelection:
        factors = {
            "difficulty_score": difficulty_score,
            "risk": {"none": 0.0, "low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}.get(risk_level, 0.5),
            "repo_size": min(1.0, repo_file_count / 10000),
            "hardware_capability": {"minimal": 0.2, "cpu_only": 0.3, "budget_gpu": 0.5, "standard_gpu": 0.7, "high_end": 1.0, "unknown": 0.2}.get(hardware_tier, 0.3),
        }

        available = HARDWARE_COMPATIBILITY.get(hardware_tier, HARDWARE_COMPATIBILITY["unknown"])
        scoring: Dict[Mode, float] = {m: 0.0 for m in available}

        for mode in available:
            score = 0.0
            config = MODE_CONFIGS[mode]

            if mode == Mode.AUDIT_ONLY:
                score = 0.1
            elif mode == Mode.LOCAL_FAST:
                score = 0.9 - factors["difficulty_score"] * 0.5 - factors["risk"] * 0.3
            elif mode == Mode.LOCAL_CAREFUL:
                score = 0.3 + factors["difficulty_score"] * 0.3 + factors["risk"] * 0.2
            elif mode == Mode.LOCAL_MULTI_CANDIDATE:
                score = 0.1 + factors["difficulty_score"] * 0.5 - factors["hardware_capability"] * 0.2
            elif mode == Mode.LOCAL_WITH_CRITIC:
                score = 0.2 + factors["difficulty_score"] * 0.4 + factors["risk"] * 0.3
            elif mode == Mode.LOCAL_WITH_HUMAN_CHECKPOINT:
                score = 0.1 + factors["risk"] * 0.5 + (1 - factors["hardware_capability"]) * 0.2
            elif mode == Mode.FALLBACK_STRONGER:
                score = (factors["difficulty_score"] - 0.5) * 0.5 + factors["risk"] * 0.3

            success_rate = self.get_success_rate(mode)
            score += (success_rate - 0.5) * 0.2

            scoring[mode] = max(0, score)

        if not scoring:
            return ModeSelection(
                selected_mode=Mode.AUDIT_ONLY,
                alternatives=[],
                selection_reasoning=["No modes available for hardware tier"],
                selection_factors=factors,
            )

        if user_preference and user_preference in available:
            selected = user_preference
            scoring[selected] += 1.0
        else:
            selected = max(scoring, key=scoring.get)

        alternatives = sorted([m for m in scoring if m != selected], key=lambda m: scoring[m], reverse=True)[:3]

        reasoning = self._build_reasoning(selected, factors, scoring, user_preference, task_type)

        return ModeSelection(
            selected_mode=selected,
            alternatives=alternatives,
            selection_reasoning=reasoning,
            selection_factors=factors,
            user_override=user_preference,
            previous_success_rate=self.get_success_rate(selected),
        )

    def _build_reasoning(self, mode: Mode, factors: Dict[str, float],
                         scoring: Dict[Mode, float], user_pref: Optional[Mode],
                         task_type: str) -> List[str]:
        reasons = [f"Selected mode: {mode.value}"]
        reasons.append(f"Mode description: {MODE_DESCRIPTIONS[mode]}")

        if user_pref:
            reasons.append(f"User preference override: {user_pref.value}")

        if factors["difficulty_score"] < 0.3:
            reasons.append(f"Task is easy (difficulty={factors['difficulty_score']:.2f}) — fast mode is sufficient")
        elif factors["difficulty_score"] < 0.5:
            reasons.append(f"Task is moderate (difficulty={factors['difficulty_score']:.2f}) — careful mode appropriate")
        elif factors["difficulty_score"] < 0.7:
            reasons.append(f"Task is hard (difficulty={factors['difficulty_score']:.2f}) — multi-candidate or critic mode recommended")
        else:
            reasons.append(f"Task is very hard (difficulty={factors['difficulty_score']:.2f}) — consider human checkpoint or fallback")

        if factors["risk"] > 0.5:
            reasons.append(f"Risk is high ({factors['risk']:.2f}) — using safer mode with verification")

        if mode == Mode.FALLBACK_STRONGER:
            reasons.append("Local model insufficient — explicit fallback to stronger model (only if configured)")
        elif mode == Mode.AUDIT_ONLY:
            reasons.append("Audit-only mode — no model inference, static analysis only")

        reasons.append(f"Previous success rate for {mode.value}: {self.get_success_rate(mode):.1%}")
        return reasons

    def get_mode_config(self, mode: Mode) -> ModeConfig:
        return MODE_CONFIGS.get(mode, MODE_CONFIGS[Mode.LOCAL_FAST])

    def available_modes(self, hardware_tier: str) -> List[dict]:
        modes = HARDWARE_COMPATIBILITY.get(hardware_tier, HARDWARE_COMPATIBILITY["unknown"])
        return [{"mode": m.value, "description": MODE_DESCRIPTIONS[m], "config": MODE_CONFIGS[m].to_dict()} for m in modes]


selector = ModeSelector()
