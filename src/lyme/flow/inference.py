from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class InferredIntent:
    command: str
    confidence: float
    args: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    is_natural_language: bool = False
    original_input: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "confidence": round(self.confidence, 3),
            "args": self.args,
            "explanation": self.explanation,
            "original_input": self.original_input,
        }


class IntentInferrer:
    INTENT_MAP = {
        "fix": ["lyme heal", "lyme fix", "lyme v1-fix"],
        "repair": ["lyme heal", "lyme fix"],
        "heal": ["lyme heal"],
        "test": ["lyme fix-latest", "lyme test"],
        "check": ["lyme doctor", "lyme gate", "lyme intel all"],
        "audit": ["lyme v1-audit", "lyme metrics-audit"],
        "continue": ["lyme continue"],
        "resume": ["lyme continue --resume"],
        "start": ["lyme start"],
        "inbox": ["lyme inbox"],
        "dashboard": ["lyme dashboard"],
        "status": ["lyme session status", "lyme intel status"],
        "what": ["lyme ask"],
        "why": ["lyme ask"],
        "how": ["lyme ask"],
        "explain": ["lyme diff-explain", "lyme ask"],
        "review": ["lyme branch-review"],
        "pr": ["lyme branch-review"],
        "commit": ["lyme diff-explain"],
        "session": ["lyme session"],
        "goal": ["lyme session goal"],
        "timeline": ["lyme session timeline"],
        "profile": ["lyme rhythm profile"],
        "intel": ["lyme intel"],
        "drift": ["lyme intel drift"],
        "debt": ["lyme intel debt"],
        "predict": ["lyme rhythm predict"],
        "rhythm": ["lyme rhythm report"],
        "learn": ["lyme rhythm report"],
        "help": ["lyme --help"],
    }

    # Context-aware: when User types a partial, we can map it
    SHORT_ALIASES = {
        "h": "lyme heal",
        "he": "lyme heal",
        "fix": "lyme fix",
        "fi": "lyme fix",
        "st": "lyme start",
        "go": "lyme continue",
        "co": "lyme continue",
        "in": "lyme inbox",
        "d": "lyme dashboard",
        "da": "lyme dashboard",
        "w": "lyme watch",
        "wa": "lyme watch",
        "pr": "lyme branch-review",
        "br": "lyme branch-review",
        "s": "lyme session status",
        "se": "lyme session",
        "i": "lyme intel status",
        "in": "lyme intel",
    }

    def infer(self, input_text: str) -> InferredIntent:
        text = input_text.strip().lower()

        # Check short aliases
        if text in self.SHORT_ALIASES:
            return InferredIntent(
                command=self.SHORT_ALIASES[text],
                confidence=0.95,
                explanation=f"Alias '{text}' → {self.SHORT_ALIASES[text]}",
                original_input=input_text,
            )

        # Check exact command match
        if text.startswith("lyme "):
            return InferredIntent(
                command=text,
                confidence=1.0,
                explanation="Explicit command",
                original_input=input_text,
            )

        # Check intent keywords
        words = text.split()
        for word in words:
            if word in self.INTENT_MAP:
                candidates = self.INTENT_MAP[word]
                return InferredIntent(
                    command=candidates[0],
                    confidence=0.85 if len(words) <= 3 else 0.7,
                    explanation=f"Intent '{word}' → {candidates[0]}",
                    original_input=input_text,
                )

        # Multi-keyword match
        matched_intents = []
        for word in words:
            if word in self.INTENT_MAP:
                for cmd in self.INTENT_MAP[word]:
                    matched_intents.append((cmd, word))
        if matched_intents:
            best = max(set(matched_intents), key=matched_intents.count)
            return InferredIntent(
                command=best[0],
                confidence=0.6,
                explanation=f"Keywords matched: {best[0]}",
                original_input=input_text,
            )

        # Default: try as a lyme command subcommand
        for candidate in ["lyme " + text, "lyme " + text.split()[0]]:
            return InferredIntent(
                command=candidate,
                confidence=0.4,
                explanation=f"Best guess: {candidate}",
                is_natural_language=True,
                original_input=input_text,
            )

        return InferredIntent(
            command="lyme --help",
            confidence=0.2,
            explanation="Could not determine intent",
            original_input=input_text,
        )
