"""EvalMetrics — standard evaluation metrics."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SuccessRate:
    total: int = 0
    passed: int = 0
    failed: int = 0

    @property
    def rate(self) -> float:
        return self.passed / max(self.total, 1)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "rate": round(self.rate, 4),
        }


@dataclass
class LatencyMetric:
    values: List[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        return sum(self.values) / max(len(self.values), 1)

    @property
    def p50_ms(self) -> float:
        if not self.values:
            return 0.0
        return sorted(self.values)[len(self.values) // 2]

    @property
    def p95_ms(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        return sorted_vals[int(len(sorted_vals) * 0.95)]

    @property
    def p99_ms(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        return sorted_vals[int(len(sorted_vals) * 0.99)]

    def to_dict(self) -> dict:
        return {
            "mean_ms": round(self.mean_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "count": len(self.values),
        }


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class EditPrecision:
    correct_edits: int = 0
    incorrect_edits: int = 0
    total_edits: int = 0

    @property
    def precision(self) -> float:
        return self.correct_edits / max(self.total_edits, 1)

    @property
    def accuracy(self) -> float:
        return self.correct_edits / max(self.correct_edits + self.incorrect_edits, 1)

    def to_dict(self) -> dict:
        return {
            "correct_edits": self.correct_edits,
            "incorrect_edits": self.incorrect_edits,
            "total_edits": self.total_edits,
            "precision": round(self.precision, 4),
            "accuracy": round(self.accuracy, 4),
        }


@dataclass
class EvalMetrics:
    success_rate: SuccessRate = field(default_factory=SuccessRate)
    latency: LatencyMetric = field(default_factory=LatencyMetric)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    edit_precision: EditPrecision = field(default_factory=EditPrecision)
    custom: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success_rate": self.success_rate.to_dict(),
            "latency": self.latency.to_dict(),
            "token_usage": self.token_usage.to_dict(),
            "edit_precision": self.edit_precision.to_dict(),
            "custom": self.custom,
        }
