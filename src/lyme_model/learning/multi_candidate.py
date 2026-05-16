"""Week 104 — Multi-Candidate Local Decoding.

Generate N candidates, rank with critic/static checks/test selection/risk score.
Measure quality improvement, latency increase, hardware cost, best-of-N benefits.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import time
import json
import uuid


@dataclass
class Candidate:
    index: int = 0
    content: str = ""
    score: float = 0.0
    static_check_passed: bool = False
    risk_score: float = 0.0
    latency_ms: float = 0.0
    selected: bool = False

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "content": self.content[:100],
            "score": round(self.score, 4),
            "static_check_passed": self.static_check_passed,
            "risk_score": round(self.risk_score, 4),
            "latency_ms": round(self.latency_ms, 1),
            "selected": self.selected,
        }


@dataclass
class MultiCandidateResult:
    task: str = ""
    num_candidates: int = 0
    candidates: List[Candidate] = field(default_factory=list)
    best_score: float = 0.0
    best_improvement_over_first: float = 0.0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    selection_method: str = "critic_ranked"

    def to_dict(self) -> dict:
        return {
            "task": self.task[:100],
            "num_candidates": self.num_candidates,
            "candidates": [c.to_dict() for c in self.candidates],
            "best_score": round(self.best_score, 4),
            "best_improvement_over_first": round(self.best_improvement_over_first, 4),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "selection_method": self.selection_method,
        }


class MultiCandidateDecoder:
    """Generates N candidates and ranks them."""

    def __init__(self, num_candidates: int = 3):
        self.num_candidates = num_candidates

    def generate_and_rank(self, task: str, generate_fn: Optional[Callable] = None) -> MultiCandidateResult:
        result = MultiCandidateResult(task=task, num_candidates=self.num_candidates)

        total_latency = 0.0
        candidates = []

        for i in range(self.num_candidates):
            c_start = time.time()
            content = self._generate_candidate(task, i, generate_fn)
            c_latency = (time.time() - c_start) * 1000
            total_latency += c_latency

            score = self._score_candidate(content, task)
            static_pass = self._static_check(content)
            risk = self._risk_score(content)

            candidates.append(Candidate(
                index=i,
                content=content,
                score=score,
                static_check_passed=static_pass,
                risk_score=risk,
                latency_ms=c_latency,
            ))

        # Rank by score (higher = better), break ties by risk (lower = better)
        candidates.sort(key=lambda c: (-c.score, c.risk_score))
        if candidates:
            candidates[0].selected = True

        result.candidates = candidates
        result.best_score = candidates[0].score if candidates else 0.0
        result.best_improvement_over_first = (
            candidates[0].score - candidates[-1].score
        ) / max(abs(candidates[-1].score), 0.01) if candidates else 0.0
        result.total_latency_ms = total_latency
        result.avg_latency_ms = total_latency / max(self.num_candidates, 1)
        return result

    def _generate_candidate(self, task: str, idx: int, fn: Optional[Callable] = None) -> str:
        if fn:
            return fn(task, idx)
        task_l = task.lower()
        variations = [
            f"Fix: {task}",
            f"Solution: Address {task}",
            f"Patch: Resolve {task}",
        ]
        return variations[idx % len(variations)]

    def _score_candidate(self, content: str, task: str) -> float:
        score = 0.5
        task_words = set(task.lower().split())
        content_words = set(content.lower().split())
        overlap = task_words & content_words
        if overlap:
            score += min(len(overlap) / max(len(task_words), 1), 0.3)
        if len(content) > 20:
            score += 0.1
        if any(w in content.lower() for w in ["fix", "resolve", "address", "change"]):
            score += 0.1
        return min(score, 1.0)

    def _static_check(self, content: str) -> bool:
        return len(content) > 10

    def _risk_score(self, content: str) -> float:
        risk = 0.1
        high_risk = ["delete", "remove", "drop", "truncate", "exec", "eval"]
        for w in high_risk:
            if w in content.lower():
                risk += 0.15
        return min(risk, 1.0)

    def benchmark(self) -> Dict:
        tasks = [
            "Fix division by zero in calculator.py",
            "Fix null dropping in transform.py",
            "Fix ID mismatch in todo-api delete endpoint",
            "Refactor payment processing to use strategy pattern",
            "Add input validation to todo creation endpoint",
        ]
        results = []
        for t in tasks:
            r = self.generate_and_rank(t)
            results.append(r.to_dict())

        avg_improvement = sum(
            r["best_improvement_over_first"] for r in results
        ) / max(len(results), 1)

        return {
            "num_tasks": len(tasks),
            "candidates_per_task": self.num_candidates,
            "avg_improvement_over_first": round(avg_improvement, 4),
            "avg_latency_ms": round(
                sum(r["total_latency_ms"] for r in results) / max(len(results), 1), 1
            ),
            "avg_best_score": round(
                sum(r["best_score"] for r in results) / max(len(results), 1), 4
            ),
            "results": results,
        }

    @staticmethod
    def best_of_n_gains() -> Dict:
        return {
            "n=1": {"quality": 1.0, "latency": 1.0, "cost": "baseline"},
            "n=2": {"quality": 1.15, "latency": 2.0, "cost": "2x generation, 1x critic"},
            "n=3": {"quality": 1.25, "latency": 3.0, "cost": "3x generation, 1x critic + ranking"},
            "n=5": {"quality": 1.35, "latency": 5.0, "cost": "5x generation, diminishing returns"},
            "note": "Estimated gains. Actual depends on task difficulty and model quality.",
        }
