"""AgentOrchestrator — multi-agent coordination and delegation."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentRole


class DelegationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class AgentDelegation:
    agent_name: str
    task: str
    status: DelegationStatus = DelegationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "task": self.task,
            "status": self.status.value,
            "error": self.error,
        }


@dataclass
class OrchestrationPlan:
    id: str
    goal: str
    delegations: List[AgentDelegation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"

    def add_delegation(self, delegation: AgentDelegation) -> None:
        self.delegations.append(delegation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "delegation_count": len(self.delegations),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


class AgentOrchestrator:
    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}
        self._plans: Dict[str, OrchestrationPlan] = {}

    def register_agent(self, config: AgentConfig) -> None:
        self._agents[config.name] = config

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        return self._agents.get(name)

    def list_agents(self, role: Optional[AgentRole] = None) -> List[AgentConfig]:
        agents = list(self._agents.values())
        if role:
            agents = [a for a in agents if a.role == role]
        return agents

    def create_plan(self, goal: str, plan_id: str = "") -> OrchestrationPlan:
        plan = OrchestrationPlan(
            id=plan_id or f"plan_{datetime.now().timestamp():.0f}",
            goal=goal,
        )
        self._plans[plan.id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[OrchestrationPlan]:
        return self._plans.get(plan_id)

    def route_task(self, task: str, required_capability: str) -> Optional[str]:
        for name, agent in self._agents.items():
            for cap in agent.capabilities:
                if cap.name == required_capability and cap.score >= 0.5:
                    return name
        return None
