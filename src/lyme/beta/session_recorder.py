import json
import time
import uuid
from pathlib import Path
from typing import Optional


class SessionRecorder:
    def __init__(self, storage_dir: str = ".lyme/beta/sessions"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._current: Optional[dict] = None

    def start_session(self, user_id: str = "", metadata: dict = None):
        self._current = {
            "session_id": uuid.uuid4().hex[:12],
            "user_id": user_id,
            "start_time": time.time(),
            "end_time": None,
            "commands": [],
            "errors": [],
            "confusion_points": [],
            "metadata": metadata or {},
            "duration_s": None,
        }

    def record_command(self, command: str, args: str = "", duration_ms: float = 0, success: bool = True):
        if self._current:
            self._current["commands"].append({
                "command": command,
                "args": args,
                "timestamp": time.time(),
                "duration_ms": duration_ms,
                "success": success,
            })

    def record_confusion(self, command: str, reason: str = "", duration_ms: float = 0):
        if self._current:
            self._current["confusion_points"].append({
                "command": command,
                "reason": reason,
                "timestamp": time.time(),
                "duration_ms": duration_ms,
            })

    def record_error(self, command: str, error: str, traceback: str = ""):
        if self._current:
            self._current["errors"].append({
                "command": command,
                "error": error,
                "traceback": traceback[:500],
                "timestamp": time.time(),
            })

    def end_session(self) -> Optional[dict]:
        if self._current:
            self._current["end_time"] = time.time()
            self._current["duration_s"] = round(self._current["end_time"] - self._current["start_time"], 1)
            session = dict(self._current)
            self._save(session)
            self._current = None
            return session
        return None

    def _save(self, session: dict):
        path = self._storage_dir / f"{session['session_id']}.json"
        path.write_text(json.dumps(session, indent=2))

    def get_sessions(self, limit: int = 20) -> list[dict]:
        sessions = []
        for path in sorted(self._storage_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                sessions.append(json.loads(path.read_text()))
            except Exception:
                pass
        return sessions

    def get_summary(self) -> dict:
        sessions = self.get_sessions(100)
        if not sessions:
            return {"total_sessions": 0}
        total_commands = sum(len(s.get("commands", [])) for s in sessions)
        total_errors = sum(len(s.get("errors", [])) for s in sessions)
        total_confusion = sum(len(s.get("confusion_points", [])) for s in sessions)
        avg_duration = sum(s.get("duration_s", 0) for s in sessions) / len(sessions)
        return {
            "total_sessions": len(sessions),
            "total_commands": total_commands,
            "total_errors": total_errors,
            "total_confusion_points": total_confusion,
            "avg_duration_s": round(avg_duration, 1),
            "error_rate": round(total_errors / max(total_commands, 1) * 100, 1),
            "confusion_rate": round(total_confusion / max(total_commands, 1) * 100, 1),
        }


session_recorder = SessionRecorder()
