"""EditSession — tracks agent edit operations with rollback support."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionState(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    CONFLICTED = "conflicted"


class OperationType(Enum):
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class EditOperation:
    operation_id: str = ""
    operation_type: OperationType = OperationType.EDIT
    file_path: str = ""
    original_content: str = ""
    new_content: str = ""
    timestamp: float = field(default_factory=time.time)
    agent: str = "lyme"
    status: str = "pending"

    @property
    def has_changes(self) -> bool:
        return self.original_content != self.new_content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "type": self.operation_type.value,
            "file_path": self.file_path,
            "agent": self.agent,
            "status": self.status,
            "has_changes": self.has_changes,
        }


@dataclass
class EditSession:
    session_id: str = ""
    task: str = ""
    state: SessionState = SessionState.ACTIVE
    operations: List[EditOperation] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    agent: str = "lyme"

    def add_operation(self, op: EditOperation) -> None:
        op.operation_id = op.operation_id or str(uuid.uuid4())[:12]
        self.operations.append(op)

    def rollback(self) -> List[str]:
        rolled = []
        for op in reversed(self.operations):
            if op.status == "applied":
                path = Path(op.file_path)
                if path.exists() and op.original_content:
                    path.write_text(op.original_content)
                    op.status = "rolled_back"
                    rolled.append(op.file_path)
        self.state = SessionState.ROLLED_BACK
        self.completed_at = time.time()
        return rolled

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task[:80],
            "state": self.state.value,
            "operations": len(self.operations),
            "files_changed": len(set(op.file_path for op in self.operations if op.status == "applied")),
            "duration_s": round((self.completed_at or time.time()) - self.started_at, 2),
            "agent": self.agent,
        }


class SessionTracker:
    def __init__(self):
        self._sessions: Dict[str, EditSession] = {}

    def create_session(self, task: str, agent: str = "lyme") -> EditSession:
        session = EditSession(
            session_id=str(uuid.uuid4())[:12],
            task=task,
            agent=agent,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[EditSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        sessions = sorted(self._sessions.values(), key=lambda s: s.started_at, reverse=True)
        return [s.summary() for s in sessions[:limit]]

    def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.COMPLETED
            session.completed_at = time.time()
