"""TeamAnalytics — team-level usage metrics and reporting."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TeamStats:
    total_agents: int = 0
    total_tasks: int = 0
    total_edits: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_task_duration_s: float = 0.0
    active_since: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.total_successes / max(self.total_tasks, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": self.total_agents,
            "tasks": self.total_tasks,
            "edits": self.total_edits,
            "successes": self.total_successes,
            "failures": self.total_failures,
            "success_rate": round(self.success_rate, 4),
            "avg_duration_s": round(self.avg_task_duration_s, 2),
        }


class TeamAnalytics:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def record(self, event: str, agent: str, duration_s: float = 0.0,
               success: bool = True, metadata: Dict = None) -> None:
        self._events.append({
            "event": event, "agent": agent,
            "duration_s": duration_s, "success": success,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

    def get_stats(self, since: float = 0) -> TeamStats:
        events = [e for e in self._events if e["timestamp"] >= since]
        stats = TeamStats()
        agents = set()
        for e in events:
            agents.add(e["agent"])
            stats.total_tasks += 1
            if e["success"]:
                stats.total_successes += 1
            else:
                stats.total_failures += 1
            stats.total_edits += 1 if e.get("event") == "edit" else 0
            stats.avg_task_duration_s += e.get("duration_s", 0)
        stats.total_agents = len(agents)
        stats.avg_task_duration_s /= max(len(events), 1)
        if events:
            stats.active_since = min(e["timestamp"] for e in events)
        return stats

    def top_agents(self, limit: int = 5) -> List[Dict[str, Any]]:
        agent_stats: Dict[str, Dict] = {}
        for e in self._events:
            a = e["agent"]
            if a not in agent_stats:
                agent_stats[a] = {"tasks": 0, "successes": 0}
            agent_stats[a]["tasks"] += 1
            if e["success"]:
                agent_stats[a]["successes"] += 1
        sorted_agents = sorted(agent_stats.items(), key=lambda x: x[1]["successes"], reverse=True)
        return [
            {"agent": a, **s}
            for a, s in sorted_agents[:limit]
        ]
