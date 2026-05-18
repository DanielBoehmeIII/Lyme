"""CostTracker — tracks usage costs and savings vs cloud alternatives."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UsageMetrics:
    total_tasks: int = 0
    total_tokens: int = 0
    total_duration_s: float = 0.0
    estimated_cost_usd: float = 0.0
    cloud_equivalent_cost: float = 0.0

    @property
    def savings(self) -> float:
        return self.cloud_equivalent_cost - self.estimated_cost_usd

    @property
    def savings_pct(self) -> float:
        if self.cloud_equivalent_cost == 0:
            return 0.0
        return (self.savings / self.cloud_equivalent_cost) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": self.total_tasks,
            "tokens": self.total_tokens,
            "duration_s": round(self.total_duration_s, 2),
            "cost_usd": round(self.estimated_cost_usd, 4),
            "cloud_cost_usd": round(self.cloud_equivalent_cost, 4),
            "savings_usd": round(self.savings, 4),
            "savings_pct": round(self.savings_pct, 2),
        }


class CostTracker:
    COST_PER_TOKEN_LOCAL = 0.0000001  # $0.10 per 1M tokens local
    COST_PER_TOKEN_CLOUD = 0.000015   # $15 per 1M tokens cloud

    def __init__(self):
        self._sessions: List[UsageMetrics] = []

    def record(self, tokens: int, duration_s: float = 0.0) -> UsageMetrics:
        m = UsageMetrics(
            total_tasks=1,
            total_tokens=tokens,
            total_duration_s=duration_s,
            estimated_cost_usd=tokens * self.COST_PER_TOKEN_LOCAL,
            cloud_equivalent_cost=tokens * self.COST_PER_TOKEN_CLOUD,
        )
        self._sessions.append(m)
        return m

    def total(self) -> UsageMetrics:
        total = UsageMetrics()
        for s in self._sessions:
            total.total_tasks += s.total_tasks
            total.total_tokens += s.total_tokens
            total.total_duration_s += s.total_duration_s
            total.estimated_cost_usd += s.estimated_cost_usd
            total.cloud_equivalent_cost += s.cloud_equivalent_cost
        return total
