"""SpeculativeDecoder — draft-then-verify speculative decoding."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SpeculativeConfig:
    draft_model: str = ""
    verifier_model: str = ""
    max_draft_tokens: int = 5
    temperature: float = 0.7
    top_k: int = 40
    top_p: float = 0.9
    use_greedy_draft: bool = True


@dataclass
class SpeculativeResult:
    text: str
    draft_tokens: int = 0
    accepted_tokens: int = 0
    rejected_tokens: int = 0
    acceptance_rate: float = 0.0
    speedup_vs_standard: float = 1.0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_tokens": self.draft_tokens,
            "accepted_tokens": self.accepted_tokens,
            "rejected_tokens": self.rejected_tokens,
            "acceptance_rate": round(self.acceptance_rate, 4),
            "speedup_vs_standard": round(self.speedup_vs_standard, 4),
            "duration_ms": round(self.duration_ms, 2),
        }


DraftFn = Callable[[str, int], str]
VerifyFn = Callable[[str], str]


class SpeculativeDecoder:
    def __init__(self, config: SpeculativeConfig = None):
        self.config = config or SpeculativeConfig()
        self._draft_fn: Optional[DraftFn] = None
        self._verify_fn: Optional[VerifyFn] = None

    def set_draft(self, fn: DraftFn) -> None:
        self._draft_fn = fn

    def set_verifier(self, fn: VerifyFn) -> None:
        self._verify_fn = fn

    def generate(self, prompt: str) -> SpeculativeResult:
        start = time.time()
        if not self._draft_fn or not self._verify_fn:
            return SpeculativeResult(text="Draft or verifier not configured", duration_ms=(time.time() - start) * 1000)

        draft_tokens_total = 0
        accepted = 0
        rejected = 0
        output_parts: List[str] = []

        while draft_tokens_total < self.config.max_draft_tokens:
            current_prompt = prompt + "".join(output_parts)
            draft_text = self._draft_fn(current_prompt, self.config.max_draft_tokens)
            draft_tokens = draft_text.split()
            draft_tokens_total += len(draft_tokens)

            for token in draft_tokens:
                verify_prompt = current_prompt + "".join(output_parts) + token
                verified = self._verify_fn(verify_prompt)
                if verified.strip().startswith(token.strip()):
                    output_parts.append(token + " ")
                    accepted += 1
                else:
                    output_parts.append(verified.strip().split()[0] + " " if verified.strip().split() else "")
                    rejected += 1
                    break

            if not draft_tokens:
                break

        total = accepted + rejected
        return SpeculativeResult(
            text="".join(output_parts),
            draft_tokens=draft_tokens_total,
            accepted_tokens=accepted,
            rejected_tokens=rejected,
            acceptance_rate=accepted / max(total, 1),
            duration_ms=(time.time() - start) * 1000,
        )
