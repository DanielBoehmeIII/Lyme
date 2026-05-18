"""HumanPreferenceLoop — collects human feedback and trains on preferences."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PreferencePair:
    prompt: str
    response_a: str
    response_b: str
    winner: str = ""  # "a", "b", or "tie"
    annotator: str = "human"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt[:200],
            "winner": self.winner,
            "annotator": self.annotator,
        }


@dataclass
class PreferenceStats:
    total_pairs: int = 0
    a_wins: int = 0
    b_wins: int = 0
    ties: int = 0
    agreement_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total_pairs,
            "a_wins": self.a_wins,
            "b_wins": self.b_wins,
            "ties": self.ties,
            "agreement_rate": round(self.agreement_rate, 4),
        }


class HumanPreferenceLoop:
    def __init__(self, storage_path: str = ".lyme/preferences"):
        self._path = Path(storage_path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._pairs: List[PreferencePair] = []
        self._load()

    def add_pair(self, pair: PreferencePair) -> None:
        self._pairs.append(pair)
        self._save()

    def record_choice(self, prompt: str, response_a: str, response_b: str,
                      winner: str, annotator: str = "human") -> PreferencePair:
        pair = PreferencePair(
            prompt=prompt, response_a=response_a,
            response_b=response_b, winner=winner, annotator=annotator,
        )
        self.add_pair(pair)
        return pair

    def get_pairs(self, limit: int = 100) -> List[PreferencePair]:
        sorted_pairs = sorted(self._pairs, key=lambda p: p.timestamp, reverse=True)
        return sorted_pairs[:limit]

    def stats(self) -> PreferenceStats:
        stats = PreferenceStats(total_pairs=len(self._pairs))
        for p in self._pairs:
            if p.winner == "a":
                stats.a_wins += 1
            elif p.winner == "b":
                stats.b_wins += 1
            else:
                stats.ties += 1
        return stats

    def export_dpo(self, path: str) -> int:
        data = []
        for p in self._pairs:
            if p.winner == "a":
                chosen, rejected = p.response_a, p.response_b
            elif p.winner == "b":
                chosen, rejected = p.response_b, p.response_a
            else:
                continue
            data.append({
                "prompt": p.prompt,
                "chosen": chosen,
                "rejected": rejected,
            })
        Path(path).write_text(json.dumps(data, indent=2))
        return len(data)

    def _save(self) -> None:
        data = [p.to_dict() for p in self._pairs]
        (self._path / "preferences.json").write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self._path / "preferences.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for d in data:
                    self._pairs.append(PreferencePair(**d))
            except Exception:
                pass
