"""SocietyRuntime — live multi-agent society that wires orchestrator → agents → collective memory."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..agents.orchestrator import AgentOrchestrator, AgentDelegation, DelegationStatus
from ..agents.base import AgentConfig, AgentRole
from ..collective import AdaptiveTrustSystem


class SocietyState(Enum):
    IDLE = "idle"
    DELEGATING = "delegating"
    EXECUTING = "executing"
    DEBATING = "debating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SocietyResult:
    task: str
    state: SocietyState = SocietyState.IDLE
    delegations: List[AgentDelegation] = field(default_factory=list)
    debate_summary: str = ""
    collective_verdict: str = ""
    duration_ms: float = 0.0
    society_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "state": self.state.value,
            "delegations": [d.to_dict() for d in self.delegations],
            "debate_summary": self.debate_summary[:200],
            "collective_verdict": self.collective_verdict,
            "duration_ms": round(self.duration_ms, 2),
        }


class SocietyRuntime:
    def __init__(self, name: str = "default"):
        self.name = name
        self.state = SocietyState.IDLE
        self.orchestrator = AgentOrchestrator()
        self.trust_system = AdaptiveTrustSystem()
        self._delegates: Dict[str, Callable] = {}

    def register_agent(self, config: AgentConfig, executor: Callable) -> None:
        self.orchestrator.register_agent(config)
        self._delegates[config.name] = executor

    def run(self, task: str) -> SocietyResult:
        start = time.time()
        sid = str(uuid.uuid4())[:8]
        result = SocietyResult(task=task, society_id=sid)

        self.state = SocietyState.DELEGATING

        # 1. Decompose and delegate
        plan = self.orchestrator.create_plan(task, sid)
        for role in [AgentRole.PLANNER, AgentRole.CODER, AgentRole.REVIEWER, AgentRole.TESTER]:
            agent = self.orchestrator.route_task(f"{role.value}: {task}", role.value)
            if agent:
                delegation = AgentDelegation(agent_name=agent, task=task)
                plan.add_delegation(delegation)
                result.delegations.append(delegation)

        # 2. Execute delegations
        self.state = SocietyState.EXECUTING
        for delegation in plan.delegations:
            executor = self._delegates.get(delegation.agent_name)
            if executor:
                delegation.status = DelegationStatus.IN_PROGRESS
                try:
                    output = executor(task)
                    delegation.result = {"output": str(output)[:500]}
                    delegation.status = DelegationStatus.COMPLETED
                except Exception as e:
                    delegation.result = {"error": str(e)}
                    delegation.status = DelegationStatus.FAILED

        # 3. Collective verification
        self.state = SocietyState.DEBATING
        trust_scores = []
        for delegation in plan.delegations:
            if delegation.result and "error" not in delegation.result:
                score = self.trust_system.compute_trust(delegation.agent_name)
                trust_scores.append(score)

        avg_trust = sum(trust_scores) / max(len(trust_scores), 1)
        result.collective_verdict = "approved" if avg_trust > 0.5 else "needs_review"
        result.debate_summary = f"Trust-weighted verdict from {len(trust_scores)} agents (avg trust: {avg_trust:.2f})"

        # 4. Store in trust system
        try:
            self.trust_system.record_escalation(sid, task)
        except Exception:
            pass

        result.duration_ms = (time.time() - start) * 1000
        result.state = SocietyState.COMPLETED
        return result
