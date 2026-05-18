"""SubscriptionManager — tiered subscription plans."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanTier(Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


@dataclass
class Plan:
    tier: PlanTier = PlanTier.FREE
    price_monthly: float = 0.0
    max_agents: int = 1
    max_tasks_per_day: int = 50
    team_members: int = 1
    audit_trail: bool = False
    airgap: bool = False
    priority_support: bool = False
    hosted_evals: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "price_monthly": self.price_monthly,
            "max_agents": self.max_agents,
            "max_tasks_per_day": self.max_tasks_per_day,
            "team_members": self.team_members,
            "features": {
                "audit_trail": self.audit_trail,
                "airgap": self.airgap,
                "priority_support": self.priority_support,
                "hosted_evals": self.hosted_evals,
            },
        }


PLANS = {
    PlanTier.FREE: Plan(tier=PlanTier.FREE, max_agents=1, max_tasks_per_day=50),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO, price_monthly=29.0,
        max_agents=3, max_tasks_per_day=500,
    ),
    PlanTier.TEAM: Plan(
        tier=PlanTier.TEAM, price_monthly=99.0,
        max_agents=10, max_tasks_per_day=2000,
        team_members=10, audit_trail=True,
    ),
    PlanTier.ENTERPRISE: Plan(
        tier=PlanTier.ENTERPRISE, price_monthly=499.0,
        max_agents=100, max_tasks_per_day=10000,
        team_members=100, audit_trail=True,
        airgap=True, priority_support=True, hosted_evals=True,
    ),
}


@dataclass
class Subscription:
    user_id: str = ""
    tier: PlanTier = PlanTier.FREE
    active: bool = True

    def plan(self) -> Plan:
        return PLANS.get(self.tier, PLANS[PlanTier.FREE])


class SubscriptionManager:
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}

    def subscribe(self, user_id: str, tier: PlanTier) -> Subscription:
        sub = Subscription(user_id=user_id, tier=tier, active=True)
        self._subscriptions[user_id] = sub
        return sub

    def get(self, user_id: str) -> Subscription:
        return self._subscriptions.get(user_id, Subscription(user_id=user_id))

    def check_limit(self, user_id: str, task_count: int) -> bool:
        sub = self.get(user_id)
        plan = sub.plan()
        return task_count <= plan.max_tasks_per_day

    def list_plans(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in PLANS.values()]
