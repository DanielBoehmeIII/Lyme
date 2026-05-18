"""HostedEval — managed benchmark evaluation service."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalSession:
    session_id: str = ""
    agent_name: str = ""
    scenario: str = ""
    status: str = "pending"
    score: float = 0.0
    duration_s: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent": self.agent_name,
            "scenario": self.scenario,
            "status": self.status,
            "score": round(self.score, 4),
            "duration_s": round(self.duration_s, 2),
        }


class HostedEval:
    def __init__(self):
        self._sessions: List[EvalSession] = []

    def create_session(self, agent_name: str, scenario: str) -> EvalSession:
        import uuid
        session = EvalSession(
            session_id=str(uuid.uuid4())[:12],
            agent_name=agent_name, scenario=scenario,
        )
        self._sessions.append(session)
        return session

    def get_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        sorted_sessions = sorted(self._sessions, key=lambda s: s.created_at, reverse=True)
        return [s.to_dict() for s in sorted_sessions[:limit]]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "unique_agents": len(set(s.agent_name for s in self._sessions)),
            "unique_scenarios": len(set(s.scenario for s in self._sessions)),
            "avg_score": sum(s.score for s in self._sessions if s.score) / max(len(self._sessions), 1),
        }
