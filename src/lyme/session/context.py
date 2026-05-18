from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class Goal:
    id: str = ""
    description: str = ""
    status: str = "open"
    steps: List[str] = field(default_factory=list)
    completed_steps: List[str] = field(default_factory=list)
    branch: str = ""
    files_touched: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "steps": self.steps,
            "completed_steps": self.completed_steps,
            "branch": self.branch,
            "files_touched": self.files_touched,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Goal:
        return cls(**d)

    def progress_pct(self) -> float:
        if not self.steps:
            return 0.0
        return len(self.completed_steps) / len(self.steps) * 100

    def is_stale(self, max_idle_hours: float = 24) -> bool:
        return (time.time() - self.updated_at) > (max_idle_hours * 3600)

    def is_unfinished(self) -> bool:
        return self.status in ("open", "in_progress") and (
            len(self.completed_steps) < len(self.steps)
        )


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    branch: str = ""
    active_goal_id: Optional[str] = None
    goals: List[Goal] = field(default_factory=list)
    commands_run: List[Dict[str, Any]] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "branch": self.branch,
            "active_goal_id": self.active_goal_id,
            "goals": [g.to_dict() for g in self.goals],
            "commands_run": self.commands_run[-100:],
            "files_modified": self.files_modified,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Session:
        s = cls(
            session_id=d.get("session_id", ""),
            start_time=d.get("start_time", 0.0),
            end_time=d.get("end_time"),
            branch=d.get("branch", ""),
            active_goal_id=d.get("active_goal_id"),
            tags=d.get("tags", []),
        )
        s.goals = [Goal.from_dict(g) for g in d.get("goals", [])]
        s.commands_run = d.get("commands_run", [])
        s.files_modified = d.get("files_modified", [])
        return s


class SessionContext:
    def __init__(self, repo_path: str = "."):
        self._path = Path(repo_path) / ".lyme" / "session"
        self._path.mkdir(parents=True, exist_ok=True)
        self._session: Optional[Session] = None
        self._load()

    def _session_file(self) -> Path:
        return self._path / "current.json"

    def _goals_dir(self) -> Path:
        return self._path / "goals"

    def _load(self) -> None:
        path = self._session_file()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._session = Session.from_dict(data)
            except Exception:
                self._session = None
        if self._session is None:
            self._session = Session()

    def _save(self) -> None:
        if self._session:
            self._session_file().write_text(
                json.dumps(self._session.to_dict(), indent=2)
            )

    def _save_goal(self, goal: Goal) -> None:
        self._goals_dir().mkdir(parents=True, exist_ok=True)
        path = self._goals_dir() / f"{goal.id}.json"
        path.write_text(json.dumps(goal.to_dict(), indent=2))

    # --- Session lifecycle ---

    def start(self, branch: str = "") -> str:
        self._session = Session(branch=branch)
        self._save()
        return self._session.session_id

    def end(self) -> None:
        if self._session:
            self._session.end_time = time.time()
            self._save()

    def current(self) -> Optional[Session]:
        return self._session

    def is_active(self) -> bool:
        return self._session is not None and self._session.end_time is None

    # --- Branch tracking ---

    def set_branch(self, branch: str) -> None:
        if self._session:
            self._session.branch = branch
            self._save()

    def current_branch(self) -> str:
        if self._session:
            return self._session.branch
        return ""

    # --- Command tracking ---

    def record_command(self, command: str, duration_ms: float = 0, success: bool = True) -> None:
        if not self._session:
            return
        self._session.commands_run.append({
            "command": command,
            "timestamp": time.time(),
            "duration_ms": duration_ms,
            "success": success,
        })
        self._save()

    def recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._session:
            return []
        return self._session.commands_run[-limit:]

    # --- File tracking ---

    def record_file_modification(self, file_path: str) -> None:
        if not self._session:
            return
        if file_path not in self._session.files_modified:
            self._session.files_modified.append(file_path)
        self._save()

    def modified_files(self) -> List[str]:
        if not self._session:
            return []
        return list(self._session.files_modified)

    # --- Goal management ---

    def create_goal(
        self,
        description: str,
        steps: Optional[List[str]] = None,
        branch: str = "",
        tags: Optional[List[str]] = None,
    ) -> Goal:
        goal = Goal(
            id=uuid.uuid4().hex[:12],
            description=description,
            steps=steps or [],
            branch=branch or self.current_branch(),
            tags=tags or [],
        )
        if self._session:
            self._session.goals.append(goal)
            self._session.active_goal_id = goal.id
            self._save()
            self._save_goal(goal)
        return goal

    def active_goal(self) -> Optional[Goal]:
        if not self._session or not self._session.active_goal_id:
            return None
        for g in self._session.goals:
            if g.id == self._session.active_goal_id:
                return g
        return None

    def complete_step(self, step_description: str) -> None:
        goal = self.active_goal()
        if not goal:
            return
        if step_description not in goal.completed_steps:
            goal.completed_steps.append(step_description)
            goal.updated_at = time.time()
            if goal.completed_steps == goal.steps:
                goal.status = "completed"
            self._save()
            self._save_goal(goal)

    def complete_goal(self, goal_id: str) -> None:
        for g in self._session.goals:
            if g.id == goal_id:
                g.status = "completed"
                g.updated_at = time.time()
                self._save()
                self._save_goal(g)
                break

    def fail_goal(self, goal_id: str) -> None:
        for g in self._session.goals:
            if g.id == goal_id:
                g.status = "failed"
                g.updated_at = time.time()
                self._save()
                self._save_goal(g)
                break

    def unfinished_goals(self) -> List[Goal]:
        if not self._session:
            return []
        return [g for g in self._session.goals if g.is_unfinished()]

    def goals_for_branch(self, branch: str) -> List[Goal]:
        if not self._session:
            return []
        return [g for g in self._session.goals if g.branch == branch]

    def all_goals(self) -> List[Goal]:
        if not self._session:
            return []
        return list(self._session.goals)

    def find_goal_by_id(self, goal_id: str) -> Optional[Goal]:
        if not self._session:
            return None
        for g in self._session.goals:
            if g.id == goal_id:
                return g
        return None

    # --- Continuity / where-we-left-off ---

    def continuity_summary(self) -> Dict[str, Any]:
        if not self._session:
            return {"has_session": False}

        goal = self.active_goal()
        unfinished = self.unfinished_goals()
        recent_cmds = self.recent_commands(5)

        return {
            "has_session": True,
            "session_id": self._session.session_id,
            "branch": self._session.branch,
            "duration_hours": round(
                (time.time() - self._session.start_time) / 3600, 2
            ),
            "active_goal": goal.to_dict() if goal else None,
            "unfinished_goals": [g.to_dict() for g in unfinished],
            "commands_run_count": len(self._session.commands_run),
            "recent_commands": recent_cmds,
            "files_modified_count": len(self._session.files_modified),
            "goals_completed": sum(
                1 for g in self._session.goals if g.status == "completed"
            ),
            "goals_total": len(self._session.goals),
        }

    def resume_context(self) -> Dict[str, Any]:
        summary = self.continuity_summary()
        if not summary.get("has_session"):
            return {"action": "start_fresh"}

        goal = self.active_goal()
        if not goal:
            unfinished = self.unfinished_goals()
            if unfinished:
                return {
                    "action": "resume_unfinished_goal",
                    "goal": unfinished[0].to_dict(),
                    "next_step": self._next_unfinished_step(unfinished[0]),
                }
            return {"action": "no_active_goal"}

        return {
            "action": "resume_active_goal",
            "goal": goal.to_dict(),
            "progress_pct": goal.progress_pct(),
            "next_step": self._next_unfinished_step(goal),
        }

    def _next_unfinished_step(self, goal: Goal) -> Optional[str]:
        for step in goal.steps:
            if step not in goal.completed_steps:
                return step
        return None

    # --- Session history ---

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        sessions = []
        for path in sorted(self._path.glob("archive_*.json"), reverse=True):
            try:
                data = json.loads(path.read_text())
                sessions.append({
                    "session_id": data.get("session_id", ""),
                    "start_time": data.get("start_time", 0),
                    "end_time": data.get("end_time"),
                    "branch": data.get("branch", ""),
                    "commands": len(data.get("commands_run", [])),
                    "goals": len(data.get("goals", [])),
                })
            except Exception:
                continue
        return sessions[:limit]

    def archive_current(self) -> None:
        if not self._session:
            return
        self._session.end_time = time.time()
        path = self._path / f"archive_{self._session.session_id}.json"
        path.write_text(json.dumps(self._session.to_dict(), indent=2))
        self._session = Session()
        self._save()


session_context = SessionContext()
