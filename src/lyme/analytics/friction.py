import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FrictionPoint:
    point_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    command: str = ""
    workflow: str = ""
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    retry_count: int = 0
    error_type: str = ""
    error_message: str = ""
    user_id: str = ""
    session_id: str = ""
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "point_id": self.point_id,
            "command": self.command,
            "workflow": self.workflow,
            "description": self.description,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tags": self.tags,
        }


@dataclass
class WorkflowAbandonment:
    abandonment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow: str = ""
    user_id: str = ""
    session_id: str = ""
    start_time: float = field(default_factory=time.time)
    abort_time: Optional[float] = None
    steps_completed: int = 0
    total_steps: int = 0
    last_command: str = ""
    last_error: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "abandonment_id": self.abandonment_id,
            "workflow": self.workflow,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "abort_time": self.abort_time,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "last_command": self.last_command,
            "last_error": self.last_error,
            "reason": self.reason,
        }


class FrictionHeatmap:
    def __init__(self, storage_dir: str = ".lyme/analytics/friction"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._friction_points: list[FrictionPoint] = []
        self._abandonments: list[WorkflowAbandonment] = []
        self._load()

    def _friction_path(self) -> Path:
        return self._storage_dir / "friction_points.json"

    def _abandonment_path(self) -> Path:
        return self._storage_dir / "abandonments.json"

    def _load(self):
        for path, target in [(self._friction_path(), self._friction_points),
                              (self._abandonment_path(), self._abandonments)]:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    for d in data:
                        if "error_type" in d:
                            fp = FrictionPoint(
                                point_id=d.get("point_id"),
                                command=d.get("command", ""),
                                workflow=d.get("workflow", ""),
                                description=d.get("description", ""),
                                timestamp=d.get("timestamp", time.time()),
                                duration_ms=d.get("duration_ms", 0),
                                retry_count=d.get("retry_count", 0),
                                error_type=d.get("error_type", ""),
                                error_message=d.get("error_message", ""),
                                user_id=d.get("user_id", ""),
                                session_id=d.get("session_id", ""),
                                tags=d.get("tags", []),
                            )
                            target.append(fp)
                        else:
                            wa = WorkflowAbandonment(
                                abandonment_id=d.get("abandonment_id"),
                                workflow=d.get("workflow", ""),
                                user_id=d.get("user_id", ""),
                                session_id=d.get("session_id", ""),
                                start_time=d.get("start_time", time.time()),
                                abort_time=d.get("abort_time"),
                                steps_completed=d.get("steps_completed", 0),
                                total_steps=d.get("total_steps", 0),
                                last_command=d.get("last_command", ""),
                                last_error=d.get("last_error", ""),
                                reason=d.get("reason", ""),
                            )
                            target.append(wa)
                except Exception:
                    pass

    def _save_friction(self):
        data = [fp.to_dict() for fp in self._friction_points]
        self._friction_path().write_text(json.dumps(data, indent=2))

    def _save_abandonments(self):
        data = [wa.to_dict() for wa in self._abandonments]
        self._abandonment_path().write_text(json.dumps(data, indent=2))

    def record_friction(
        self,
        command: str = "",
        workflow: str = "",
        description: str = "",
        duration_ms: float = 0,
        retry_count: int = 0,
        error_type: str = "",
        error_message: str = "",
        user_id: str = "",
        session_id: str = "",
    ):
        point = FrictionPoint(
            command=command,
            workflow=workflow,
            description=description,
            duration_ms=duration_ms,
            retry_count=retry_count,
            error_type=error_type,
            error_message=error_message,
            user_id=user_id,
            session_id=session_id,
        )
        self._friction_points.append(point)
        self._save_friction()
        return point

    def record_abandonment(
        self,
        workflow: str = "",
        user_id: str = "",
        session_id: str = "",
        steps_completed: int = 0,
        total_steps: int = 0,
        last_command: str = "",
        last_error: str = "",
        reason: str = "",
    ):
        abandonment = WorkflowAbandonment(
            workflow=workflow,
            user_id=user_id,
            session_id=session_id,
            abort_time=time.time(),
            steps_completed=steps_completed,
            total_steps=total_steps,
            last_command=last_command,
            last_error=last_error,
            reason=reason,
        )
        self._abandonments.append(abandonment)
        self._save_abandonments()
        return abandonment

    def get_heatmap(self) -> dict:
        if not self._friction_points:
            return {"total_friction_points": 0, "total_abandonments": 0, "total_friction_duration_ms": 0, "total_retries": 0, "by_command": {}, "by_workflow": {}, "by_error_type": {}, "abandonment_rate": 0.0}

        by_command = defaultdict(int)
        by_workflow = defaultdict(int)
        by_error = defaultdict(int)
        total_duration = 0
        total_retries = 0

        for fp in self._friction_points:
            by_command[fp.command or "unknown"] += 1
            by_workflow[fp.workflow or "unknown"] += 1
            by_error[fp.error_type or "unknown"] += 1
            total_duration += fp.duration_ms
            total_retries += fp.retry_count

        return {
            "total_friction_points": len(self._friction_points),
            "total_abandonments": len(self._abandonments),
            "total_friction_duration_ms": total_duration,
            "total_retries": total_retries,
            "by_command": dict(sorted(by_command.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_workflow": dict(sorted(by_workflow.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_error_type": dict(sorted(by_error.items(), key=lambda x: x[1], reverse=True)[:10]),
            "abandonment_rate": round(
                len(self._abandonments) / max(len(self._friction_points), 1) * 100, 1
            ),
        }


friction_heatmap = FrictionHeatmap()
