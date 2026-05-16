"""Week 118 — Local-First Fallback Strategy.

Lyme Model tries local paths first, but knows when local is insufficient.

Fallback options:
- ask user for narrower task
- retrieve more context
- switch to careful mode
- use stronger local critic
- use external model if explicitly configured
- refuse unsupported claim

Do NOT silently call cloud models.
All fallback must be explicit and auditable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import time


class FallbackReason(Enum):
    LOW_CONFIDENCE = "low_confidence"
    HIGH_RISK = "high_risk"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    MODEL_TIMEOUT = "model_timeout"
    MODEL_ERROR = "model_error"
    TASK_TOO_LARGE = "task_too_large"
    AMBIGUOUS_TASK = "ambiguous_task"
    MISSING_TOOLS = "missing_tools"
    HARDWARE_LIMITATION = "hardware_limitation"
    USER_CANCELLED = "user_cancelled"


class FallbackAction(Enum):
    ASK_NARROWER = "ask_narrower"
    RETRIEVE_MORE = "retrieve_more"
    SWITCH_CAREFUL = "switch_careful"
    USE_CRITIC = "use_critic"
    USE_EXTERNAL_MODEL = "use_external_model"
    REFUSE = "refuse"
    RETRY = "retry"


FALLBACK_DESCRIPTIONS = {
    FallbackAction.ASK_NARROWER: "Ask the user to provide a narrower, more specific task. The current task is too broad or ambiguous for reliable local execution.",
    FallbackAction.RETRIEVE_MORE: "Retrieve additional context files. Current context may not contain enough information for a reliable answer.",
    FallbackAction.SWITCH_CAREFUL: "Switch from fast to careful mode with self-verification. Slow but more reliable.",
    FallbackAction.USE_CRITIC: "Use a critic model to review and validate the output before presenting it. Catches hallucinations and errors.",
    FallbackAction.USE_EXTERNAL_MODEL: "Use an externally configured model (only if explicitly configured by user). Lyme Model never silently calls cloud APIs.",
    FallbackAction.REFUSE: "Refuse the task with an explicit explanation of why it cannot be completed. No action will be taken.",
    FallbackAction.RETRY: "Retry the same approach with different parameters. Useful after transient errors.",
}


@dataclass
class FallbackDecision:
    reason: FallbackReason
    action: FallbackAction
    explanation: str
    confidence_before: float
    confidence_after: Optional[float]
    auditable: bool
    external_model_used: bool
    user_notified: bool
    action_taken: bool
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "reason": self.reason.value,
            "action": self.action.value,
            "explanation": self.explanation,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "auditable": self.auditable,
            "external_model_used": self.external_model_used,
            "user_notified": self.user_notified,
            "action_taken": self.action_taken,
            "details": self.details,
            "action_description": FALLBACK_DESCRIPTIONS.get(self.action, ""),
        }


FALLBACK_CHAINS: Dict[FallbackReason, List[FallbackAction]] = {
    FallbackReason.LOW_CONFIDENCE: [
        FallbackAction.RETRIEVE_MORE,
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.USE_CRITIC,
        FallbackAction.ASK_NARROWER,
        FallbackAction.USE_EXTERNAL_MODEL,
        FallbackAction.REFUSE,
    ],
    FallbackReason.HIGH_RISK: [
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.USE_CRITIC,
        FallbackAction.ASK_NARROWER,
        FallbackAction.REFUSE,
    ],
    FallbackReason.INSUFFICIENT_CONTEXT: [
        FallbackAction.RETRIEVE_MORE,
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.ASK_NARROWER,
        FallbackAction.REFUSE,
    ],
    FallbackReason.UNSUPPORTED_CLAIM: [
        FallbackAction.REFUSE,
        FallbackAction.ASK_NARROWER,
    ],
    FallbackReason.MODEL_TIMEOUT: [
        FallbackAction.RETRY,
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.USE_CRITIC,
        FallbackAction.REFUSE,
    ],
    FallbackReason.MODEL_ERROR: [
        FallbackAction.RETRY,
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.REFUSE,
    ],
    FallbackReason.TASK_TOO_LARGE: [
        FallbackAction.ASK_NARROWER,
        FallbackAction.RETRIEVE_MORE,
        FallbackAction.REFUSE,
    ],
    FallbackReason.AMBIGUOUS_TASK: [
        FallbackAction.ASK_NARROWER,
        FallbackAction.RETRIEVE_MORE,
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.REFUSE,
    ],
    FallbackReason.MISSING_TOOLS: [
        FallbackAction.ASK_NARROWER,
        FallbackAction.REFUSE,
    ],
    FallbackReason.HARDWARE_LIMITATION: [
        FallbackAction.SWITCH_CAREFUL,
        FallbackAction.ASK_NARROWER,
        FallbackAction.RETRIEVE_MORE,
        FallbackAction.REFUSE,
    ],
    FallbackReason.USER_CANCELLED: [
        FallbackAction.REFUSE,
    ],
}


class FallbackStrategy:
    """Local-first fallback strategy for Lyme Model."""

    def __init__(self, external_model_configured: bool = False):
        self._external_configured = external_model_configured
        self._decisions: List[FallbackDecision] = []
        self._chain_position: Dict[FallbackReason, int] = {}

    def configure_external_model(self, configured: bool):
        self._external_configured = configured

    def decide(self, reason: FallbackReason, current_confidence: float,
               current_mode: str = "local_fast", additional_context: Optional[Dict] = None) -> FallbackDecision:
        chain = FALLBACK_CHAINS.get(reason, [FallbackAction.REFUSE])
        pos = self._chain_position.get(reason, 0)
        action = chain[pos] if pos < len(chain) else FallbackAction.REFUSE

        if action == FallbackAction.USE_EXTERNAL_MODEL and not self._external_configured:
            pos += 1
            action = chain[pos] if pos < len(chain) else FallbackAction.REFUSE

        self._chain_position[reason] = pos + 1

        external_used = action == FallbackAction.USE_EXTERNAL_MODEL
        user_notified = action in (FallbackAction.ASK_NARROWER, FallbackAction.REFUSE, FallbackAction.USE_EXTERNAL_MODEL)

        explanations = {
            FallbackAction.ASK_NARROWER: f"Confidence too low ({current_confidence:.0%}) and task is ambiguous. Asking user for a narrower task.",
            FallbackAction.RETRIEVE_MORE: f"Insufficient context to proceed reliably. Retrieving more files for analysis.",
            FallbackAction.SWITCH_CAREFUL: f"Switching from {current_mode} to careful mode with verification.",
            FallbackAction.USE_CRITIC: f"Confidence is marginal ({current_confidence:.0%}). Using critic model to validate output.",
            FallbackAction.USE_EXTERNAL_MODEL: f"Local model confidence too low ({current_confidence:.0%}). Using external model (explicitly configured).",
            FallbackAction.REFUSE: f"Task cannot be completed: {reason.value}. No action taken.",
            FallbackAction.RETRY: f"Transient error. Retrying with same parameters.",
        }

        action_taken = action not in (FallbackAction.ASK_NARROWER, FallbackAction.REFUSE)
        if action == FallbackAction.USE_EXTERNAL_MODEL:
            action_taken = self._external_configured

        decision = FallbackDecision(
            reason=reason,
            action=action,
            explanation=explanations.get(action, f"Fallback triggered: {reason.value}"),
            confidence_before=current_confidence,
            confidence_after=None,
            auditable=True,
            external_model_used=external_used,
            user_notified=user_notified,
            action_taken=action_taken,
            details={
                "previous_mode": current_mode,
                "chain_position": pos,
                "total_chain_length": len(chain),
                "timestamp": time.time(),
            },
        )

        if additional_context:
            decision.details.update(additional_context)

        self._decisions.append(decision)
        return decision

    def reset_chain(self, reason: FallbackReason):
        """Reset the fallback chain position for a reason."""
        self._chain_position[reason] = 0

    def get_decision_history(self) -> List[dict]:
        return [d.to_dict() for d in self._decisions]

    def check_before_action(self, task: str, confidence: float, risk: str,
                            current_mode: str, external_configured: bool) -> Optional[FallbackDecision]:
        self._external_configured = external_configured

        if confidence < 0.2:
            return self.decide(FallbackReason.LOW_CONFIDENCE, confidence, current_mode)
        if risk in ("high", "critical") and current_mode not in ("local_careful", "local_with_critic", "local_with_human_checkpoint"):
            return self.decide(FallbackReason.HIGH_RISK, confidence, current_mode)
        if confidence < 0.4:
            decision = self.decide(FallbackReason.LOW_CONFIDENCE, confidence, current_mode)
            if decision.action == FallbackAction.REFUSE:
                return decision
        return None

    def should_refuse(self, task_type: str, difficulty: float, hardware_tier: str) -> Optional[str]:
        if hardware_tier == "minimal" and difficulty > 0.3:
            return f"Hardware too limited (minimal) for difficulty {difficulty:.2f} task. Need at least 4GB RAM."
        if difficulty > 0.9:
            return f"Task difficulty ({difficulty:.2f}) exceeds maximum supported by Lyme Model. Consider using a stronger tool."
        if task_type == "cross_repo" and difficulty > 0.5:
            return "Cross-repo tasks with difficulty > 0.5 are not supported locally. Needs external model."
        return None


fallback = FallbackStrategy()
