"""BaseAgent — abstract base for all Lyme agent implementations."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class AgentRole(Enum):
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    REPAIR = "repair"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentCapability:
    name: str
    description: str
    score: float = 0.5
    requires: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    name: str
    role: AgentRole = AgentRole.CODER
    model: str = ""
    max_tokens: int = 128000
    timeout_s: int = 300
    capabilities: List[AgentCapability] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "timeout_s": self.timeout_s,
            "capabilities": [{"name": c.name, "description": c.description, "score": c.score}
                             for c in self.capabilities],
        }


@runtime_checkable
class BaseAgent(Protocol):
    config: AgentConfig

    async def plan(self, task: str, context: Dict[str, Any]) -> List[Dict[str, Any]]: ...
    async def execute(self, plan_step: Dict[str, Any]) -> Dict[str, Any]: ...
    async def review(self, result: Dict[str, Any]) -> Dict[str, Any]: ...
    async def repair(self, error: Dict[str, Any]) -> Dict[str, Any]: ...
    def get_metrics(self) -> Dict[str, float]: ...
