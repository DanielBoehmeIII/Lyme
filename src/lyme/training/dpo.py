"""DPOTrainer — Direct Preference Optimization training loop for Lyme."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class DPOConfig:
    model_name: str = ""
    beta: float = 0.1
    learning_rate: float = 5e-6
    batch_size: int = 4
    num_epochs: int = 3
    max_length: int = 2048
    output_dir: str = "./checkpoints/dpo"
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05


@dataclass
class DPOResult:
    loss_history: List[float] = field(default_factory=list)
    avg_reward_chosen: float = 0.0
    avg_reward_rejected: float = 0.0
    accuracy: float = 0.0
    total_steps: int = 0
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_reward_chosen": round(self.avg_reward_chosen, 4),
            "avg_reward_rejected": round(self.avg_reward_rejected, 4),
            "accuracy": round(self.accuracy, 4),
            "total_steps": self.total_steps,
            "duration_s": round(self.duration_s, 2),
        }


class DPOTrainer:
    def __init__(self, config: DPOConfig = None):
        self.config = config or DPOConfig()
        self._model_fn: Optional[Callable] = None
        self._ref_fn: Optional[Callable] = None

    def set_model(self, fn: Callable) -> None:
        self._model_fn = fn

    def set_ref_model(self, fn: Callable) -> None:
        self._ref_fn = fn

    def train(self, preferences: List[Dict[str, Any]]) -> DPOResult:
        result = DPOResult()
        start = time.time()
        correct = 0
        total = 0

        for epoch in range(self.config.num_epochs):
            epoch_loss = 0.0
            for i in range(0, len(preferences), self.config.batch_size):
                batch = preferences[i:i + self.config.batch_size]
                for pair in batch:
                    chosen = pair.get("chosen", "")
                    rejected = pair.get("rejected", "")
                    prompt = pair.get("prompt", "")

                    if self._model_fn and self._ref_fn:
                        chosen_score = self._model_fn(prompt + chosen)
                        rejected_score = self._model_fn(prompt + rejected)
                        if chosen_score > rejected_score:
                            correct += 1
                        total += 1
                        loss = -self._compute_dpo_loss(chosen_score, rejected_score)
                        epoch_loss += loss
                    else:
                        result.loss_history.append(0.0)

            if epoch_loss > 0:
                result.loss_history.append(epoch_loss / max(len(preferences), 1))

        result.accuracy = correct / max(total, 1)
        result.total_steps = len(preferences) * self.config.num_epochs
        result.duration_s = time.time() - start
        return result

    def _compute_dpo_loss(self, chosen_score: float, rejected_score: float) -> float:
        import math
        logits = chosen_score - rejected_score
        return -math.log(1.0 / (1.0 + math.exp(-self.config.beta * logits)))
