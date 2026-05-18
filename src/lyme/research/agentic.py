"""AgenticResearch — persistent agents, long-horizon planning, continuous improvement."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PersistentAgent:
    agent_id: str = ""
    goal: str = ""
    status: str = "idle"
    lifetime_s: float = 0.0
    tasks_completed: int = 0
    last_active: float = field(default_factory=time.time)
    checkpoints: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "goal": self.goal[:60],
            "status": self.status,
            "uptime_s": round(self.lifetime_s, 2),
            "tasks_completed": self.tasks_completed,
            "checkpoints": self.checkpoints,
        }


@dataclass
class LongHorizonPlan:
    goal: str = ""
    phases: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration_s: float = 0.0
    progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal[:60],
            "phases": len(self.phases),
            "duration_s": round(self.estimated_duration_s, 2),
            "progress": round(self.progress, 4),
        }


class AgenticResearch:
    def __init__(self):
        self._agents: Dict[str, PersistentAgent] = {}
        self._plans: List[LongHorizonPlan] = []

    def spawn_agent(self, goal: str) -> PersistentAgent:
        import uuid
        agent = PersistentAgent(
            agent_id=str(uuid.uuid4())[:12], goal=goal,
        )
        self._agents[agent.agent_id] = agent
        return agent

    def create_plan(self, goal: str, phases: List[str]) -> LongHorizonPlan:
        plan = LongHorizonPlan(
            goal=goal,
            phases=[{"name": p, "status": "pending"} for p in phases],
            estimated_duration_s=len(phases) * 300,
        )
        self._plans.append(plan)
        return plan

    def get_agents(self) -> List[PersistentAgent]:
        return list(self._agents.values())

    def get_plans(self) -> List[LongHorizonPlan]:
        return self._plans

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_agents": len(self._agents),
            "total_plans": len(self._plans),
            "total_tasks_completed": sum(a.tasks_completed for a in self._agents.values()),
        }
