import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WorkflowSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    commands: list = field(default_factory=list)
    current_workflow: Optional[str] = None
    workflow_steps: list = field(default_factory=list)
    abandoned: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": round(self.end_time - self.start_time, 1) if self.end_time else None,
            "commands": self.commands,
            "current_workflow": self.current_workflow,
            "workflow_steps": self.workflow_steps,
            "abandoned": self.abandoned,
            "metadata": self.metadata,
        }


@dataclass
class CommandUsage:
    command: str
    count: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_ms: float = 0
    last_used: float = 0
    unique_users: set = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "count": self.count,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.successes / self.count * 100, 1) if self.count else 0,
            "avg_duration_ms": round(self.total_duration_ms / self.count, 1) if self.count else 0,
            "last_used": self.last_used,
            "unique_users": len(self.unique_users),
        }


class CommandUsageTracker:
    def __init__(self, storage_dir: str = ".lyme/analytics/commands"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._usage: dict[str, CommandUsage] = {}
        self._sessions: dict[str, WorkflowSession] = {}
        self._history: list = []
        self._pipeline_dir = self._storage_dir / "pipeline"
        self._pipeline_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _path(self) -> Path:
        return self._storage_dir / "command_usage.json"

    def _load(self):
        path = self._path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for cmd, d in data.items():
                    usage = CommandUsage(command=cmd)
                    usage.count = d.get("count", 0)
                    usage.successes = d.get("successes", 0)
                    usage.failures = d.get("failures", 0)
                    usage.total_duration_ms = d.get("total_duration_ms", 0)
                    usage.last_used = d.get("last_used", 0)
                    usage.unique_users = set(d.get("unique_users", []))
                    self._usage[cmd] = usage
            except Exception:
                pass

    def _save(self):
        data = {cmd: u.to_dict() for cmd, u in self._usage.items()}
        self._path().write_text(json.dumps(data, indent=2))

    def record_command(
        self,
        command: str,
        duration_ms: float = 0,
        success: bool = True,
        error: Optional[str] = None,
        user_id: str = "",
        session_id: str = "",
        workflow: Optional[str] = None,
    ):
        if command not in self._usage:
            self._usage[command] = CommandUsage(command=command)
        usage = self._usage[command]
        usage.count += 1
        usage.total_duration_ms += duration_ms
        usage.last_used = time.time()
        if user_id:
            usage.unique_users.add(user_id)
        if success:
            usage.successes += 1
        else:
            usage.failures += 1

        entry = {
            "command": command,
            "timestamp": time.time(),
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "user_id": user_id,
            "session_id": session_id or "",
            "workflow": workflow or "",
        }
        self._history.append(entry)
        self._save()

        if session_id:
            self._track_session_step(command, session_id, workflow, success)

    def _track_session_step(self, command: str, session_id: str, workflow: Optional[str], success: bool):
        if session_id not in self._sessions:
            self._sessions[session_id] = WorkflowSession(
                session_id=session_id, current_workflow=workflow
            )
        session = self._sessions[session_id]
        session.commands.append(command)
        if workflow:
            session.current_workflow = workflow
            session.workflow_steps.append({"command": command, "timestamp": time.time(), "success": success})

    def end_session(self, session_id: str, abandoned: bool = False):
        session = self._sessions.get(session_id)
        if session:
            session.end_time = time.time()
            session.abandoned = abandoned
            self._persist_session(session)
            if abandoned:
                del self._sessions[session_id]

    def _persist_session(self, session: WorkflowSession):
        path = self._pipeline_dir / f"{session.session_id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2))

    def get_usage_stats(self) -> dict:
        return {
            "total_commands": sum(u.count for u in self._usage.values()),
            "unique_commands": len(self._usage),
            "commands": sorted(
                [u.to_dict() for u in self._usage.values()],
                key=lambda x: x["count"],
                reverse=True,
            ),
            "abandoned_workflows": sum(
                1 for s in self._sessions.values() if s.abandoned
            ),
            "active_workflows": len(self._sessions),
        }

    def get_abandoned_workflows(self) -> list[dict]:
        abandoned = [s.to_dict() for s in self._sessions.values() if s.abandoned]
        abandoned.sort(key=lambda s: s.get("start_time", 0), reverse=True)
        pipeline_abandoned = []
        for path in sorted(self._pipeline_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text())
                if data.get("abandoned"):
                    pipeline_abandoned.append(data)
            except Exception:
                pass
        return abandoned + pipeline_abandoned

    def get_command_heatmap(self) -> list[dict]:
        now = time.time()
        day = 86400
        intervals = [
            ("last_hour", 3600),
            ("today", day),
            ("this_week", day * 7),
            ("this_month", day * 30),
        ]
        result = []
        for label, seconds in intervals:
            cutoff = now - seconds
            commands = [e for e in self._history if e["timestamp"] >= cutoff]
            count = len(commands)
            unique = len(set(e["command"] for e in commands))
            failed = sum(1 for e in commands if not e["success"])
            result.append({
                "period": label,
                "commands": count,
                "unique_commands": unique,
                "failures": failed,
                "failure_rate": round(failed / count * 100, 1) if count else 0,
            })
        return result


command_tracker = CommandUsageTracker()
