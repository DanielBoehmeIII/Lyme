"""Week 86 — Tool-Use Policy Model.

A small policy model that decides the next action:
search, read, inspect AST, run command, generate patch, verify, stop.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class Action(str, Enum):
    SEARCH = "search"
    READ = "read"
    INSPECT_AST = "inspect_ast"
    RUN_COMMAND = "run_command"
    GENERATE_PATCH = "generate_patch"
    VERIFY = "verify"
    STOP = "stop"


@dataclass
class PolicyDecision:
    action: Action
    confidence: float
    reasoning: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning[:100],
            "latency_ms": round(self.latency_ms, 1),
        }


class HeuristicRouter:
    """Rule-based action router — baseline for comparison."""

    def decide(self, context: dict) -> PolicyDecision:
        state = context.get("state", "")
        has_task = bool(context.get("task", ""))
        has_patch = bool(context.get("patch_content", ""))
        test_failed = context.get("test_failed", False)
        files_read = context.get("files_read", [])
        loop_count = context.get("loop_count", 0)

        if loop_count > 5:
            return PolicyDecision(action=Action.STOP, confidence=0.9,
                                  reasoning="Too many iterations")
        if not files_read and has_task:
            return PolicyDecision(action=Action.READ, confidence=0.8,
                                  reasoning="Need to read before acting")
        if has_patch and not test_failed:
            return PolicyDecision(action=Action.VERIFY, confidence=0.9,
                                  reasoning="Patch ready, verify it")
        if test_failed:
            needs_symbols = bool(context.get("unknown_symbols", False))
            if needs_symbols:
                return PolicyDecision(action=Action.INSPECT_AST, confidence=0.75,
                                      reasoning="Test failed, check symbols via AST")
            return PolicyDecision(action=Action.SEARCH, confidence=0.7,
                                  reasoning="Test failed, find the issue")
        if has_task:
            return PolicyDecision(action=Action.GENERATE_PATCH, confidence=0.6,
                                  reasoning="Ready to generate patch")
        return PolicyDecision(action=Action.STOP, confidence=0.5,
                              reasoning="No task or changes pending")


class ToolPolicyModel:
    """Small tool-use policy model with learned weights.

    Can be:
    - Rule-based (heuristic router)
    - Tiny classifier with learned weights
    - LoRA fine-tuned from audit traces
    - Imitation learning from traces
    """

    def __init__(self, mode: str = "heuristic"):
        self.mode = mode
        self.router = HeuristicRouter()
        self.weights: Dict[str, float] = {
            "search": 1.0,
            "read": 1.0,
            "inspect_ast": 0.8,
            "run_command": 1.0,
            "generate_patch": 1.2,
            "verify": 1.1,
            "stop": 0.9,
        }
        self.decisions: List[PolicyDecision] = []

    def decide(self, context: dict) -> PolicyDecision:
        if self.mode == "heuristic":
            decision = self.router.decide(context)
        elif self.mode == "weighted":
            decision = self._weighted_decide(context)
        else:
            decision = self.router.decide(context)

        self.decisions.append(decision)
        return decision

    def _weighted_decide(self, context: dict) -> PolicyDecision:
        base = self.router.decide(context)
        score = base.confidence * self.weights.get(base.action.value, 1.0)
        base.confidence = min(score, 1.0)
        return base

    def train_step(self, examples: List[tuple]) -> Dict:
        """Simulate a training step (updates weights based on correct actions)."""
        correct = 0
        for context, correct_action in examples:
            decision = self.decide(context)
            if decision.action.value == correct_action:
                correct += 1
                self.weights[decision.action.value] = min(
                    self.weights.get(decision.action.value, 1.0) * 1.01, 2.0
                )
            else:
                self.weights[decision.action.value] = max(
                    self.weights.get(decision.action.value, 1.0) * 0.99, 0.1
                )

        accuracy = correct / len(examples) if examples else 0
        return {
            "mode": self.mode,
            "examples": len(examples),
            "accuracy": round(accuracy, 4),
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
        }

    def benchmark(self, test_examples: List[tuple]) -> Dict:
        """Benchmark against test examples."""
        if not test_examples:
            return {"accuracy": 0.0, "total": 0}
        correct = 0
        action_counts: Dict[str, int] = {}
        for context, correct_action in test_examples:
            decision = self.decide(context)
            action_counts[decision.action.value] = action_counts.get(
                decision.action.value, 0) + 1
            if decision.action.value == correct_action:
                correct += 1
        return {
            "accuracy": round(correct / len(test_examples), 4),
            "total": len(test_examples),
            "correct": correct,
            "action_distribution": action_counts,
        }
