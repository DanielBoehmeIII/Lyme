from __future__ import annotations
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from ..analytics.command_tracker import command_tracker
from ..session.context import session_context


@dataclass
class Prediction:
    command: str
    confidence: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"command": self.command, "confidence": round(self.confidence, 3), "reason": self.reason}


class CommandPredictor:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "rhythm" / "predictor.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._transition_counts: Dict[str, Counter] = defaultdict(Counter)
        self._last_command: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text())
                self._last_command = data.get("last_command")
                for cmd, transitions in data.get("transitions", {}).items():
                    self._transition_counts[cmd] = Counter(transitions)
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "last_command": self._last_command,
            "transitions": {
                cmd: dict(trans) for cmd, trans in self._transition_counts.items()
            },
        }
        self._db_path.write_text(json.dumps(data, indent=2))

    def record_command(self, command: str) -> None:
        if self._last_command and self._last_command != command:
            self._transition_counts[self._last_command][command] += 1
        self._last_command = command
        self._save()

    def predict_next(self, top_n: int = 3) -> List[Prediction]:
        predictions = []

        if self._last_command and self._last_command in self._transition_counts:
            transitions = self._transition_counts[self._last_command]
            total = sum(transitions.values())
            if total > 0:
                for cmd, count in transitions.most_common(top_n):
                    predictions.append(Prediction(
                        command=cmd,
                        confidence=count / total,
                        reason=f"Follows '{self._last_command}' ({count}/{total} times)",
                    ))

        usage_stats = command_tracker.get_usage_stats()
        commands = usage_stats.get("commands", [])
        freq_commands = sorted(commands, key=lambda c: c["count"], reverse=True)

        existing = {p.command for p in predictions}
        for cmd in freq_commands[:top_n]:
            if cmd["command"] not in existing:
                predictions.append(Prediction(
                    command=cmd["command"],
                    confidence=0.1,
                    reason=f"Most used command ({cmd['count']}x)",
                ))
                if len(predictions) >= top_n:
                    break

        return predictions[:top_n]

    def predict_for_context(self, context_hint: str = "", top_n: int = 3) -> List[Prediction]:
        """Predict next command based on context."""
        hint_lower = context_hint.lower()

        if "test" in hint_lower or "fail" in hint_lower:
            return [
                Prediction("lyme fix-latest", 0.7, "Test failure detected"),
                Prediction("lyme heal", 0.5, "General repair"),
            ][:top_n]

        if "commit" in hint_lower or "push" in hint_lower:
            return [
                Prediction("lyme branch-review", 0.6, "Before committing"),
                Prediction("lyme diff-explain", 0.5, "Review changes"),
            ][:top_n]

        if "start" in hint_lower or "morning" in hint_lower:
            return [
                Prediction("lyme start", 0.8, "Daily startup"),
                Prediction("lyme inbox", 0.5, "Check pending tasks"),
            ][:top_n]

        return self.predict_next(top_n)

    def state_dict(self) -> Dict[str, Any]:
        return {
            "last_command": self._last_command,
            "known_transitions": dict(self._transition_counts),
        }
