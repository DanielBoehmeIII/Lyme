"""LiveMonitor — real-time agent monitoring."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentSnapshot:
    agent_id: str = ""
    status: str = "idle"
    current_task: str = ""
    duration_s: float = 0.0
    memory_mb: float = 0.0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "task": self.current_task[:60],
            "duration_s": round(self.duration_s, 2),
            "memory_mb": round(self.memory_mb, 2),
            "errors": self.error_count,
        }


class LiveMonitor:
    def __init__(self):
        self._snapshots: Dict[str, AgentSnapshot] = {}
        self._history: List[Dict[str, Any]] = []

    def update(self, snapshot: AgentSnapshot) -> None:
        self._snapshots[snapshot.agent_id] = snapshot
        self._history.append({
            "agent_id": snapshot.agent_id,
            "status": snapshot.status,
            "timestamp": time.time(),
        })
        if len(self._history) > 1000:
            self._history = self._history[-500:]

    def get_agents(self) -> List[AgentSnapshot]:
        return list(self._snapshots.values())

    def get_agent(self, agent_id: str) -> Optional[AgentSnapshot]:
        return self._snapshots.get(agent_id)

    def get_history(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return [h for h in self._history if h["agent_id"] == agent_id][-limit:]
