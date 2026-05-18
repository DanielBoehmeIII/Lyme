"""DecodeStrategy — different decoding strategies for text generation."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


LogitsFn = Callable[[str], List[float]]


class DecodeStrategy:
    def __init__(self, name: str = "greedy"):
        self.name = name

    def decode(self, logits: List[float]) -> int:
        raise NotImplementedError


class GreedyDecode(DecodeStrategy):
    def __init__(self):
        super().__init__("greedy")

    def decode(self, logits: List[float]) -> int:
        return logits.index(max(logits))


class SamplingDecode(DecodeStrategy):
    def __init__(self, temperature: float = 0.7, top_k: int = 40, top_p: float = 0.9):
        super().__init__("sampling")
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p

    def decode(self, logits: List[float]) -> int:
        import math
        scaled = [l / max(self.temperature, 0.001) for l in logits]
        exp_vals = [math.exp(l) for l in scaled]
        total = sum(exp_vals)
        probs = [e / total for e in exp_vals]
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return len(probs) - 1


class BeamSearchDecode(DecodeStrategy):
    def __init__(self, beam_width: int = 3):
        super().__init__("beam_search")
        self.beam_width = beam_width

    def decode(self, logits: List[float]) -> int:
        return logits.index(max(logits))
