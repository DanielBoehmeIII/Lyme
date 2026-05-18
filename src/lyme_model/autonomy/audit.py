"""AuditTrail — persistent record of every autonomy decision."""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import AutonomyLevel, Action, AuditEntry


class AuditTrail:
    """Record every action decision for auditability."""

    def __init__(self, log_path: str = ".lyme/autonomy/audit.json"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[AuditEntry] = []
        self._load()

    def record(self, level: AutonomyLevel, action: Action, description: str,
               confidence: float, risk_score: float, approved: bool, result: str,
               duration_ms: float = 0.0, files_changed: list[str] = None,
               commands_run: list[str] = None, approval_id: Optional[str] = None,
               error: Optional[str] = None) -> AuditEntry:
        entry = AuditEntry(
            id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            autonomy_level=level,
            action=action,
            description=description,
            confidence=confidence,
            risk_score=risk_score,
            approved=approved,
            result=result,
            duration_ms=duration_ms,
            files_changed=files_changed or [],
            commands_run=commands_run or [],
            approval_id=approval_id,
            error=error,
        )
        self._entries.append(entry)
        self._save()
        return entry

    def get_entries(self, limit: int = 100, level: Optional[AutonomyLevel] = None,
                    action: Optional[Action] = None, approved_only: Optional[bool] = None) -> list[AuditEntry]:
        entries = self._entries
        if level:
            entries = [e for e in entries if e.autonomy_level == level]
        if action:
            entries = [e for e in entries if e.action == action]
        if approved_only is not None:
            entries = [e for e in entries if e.approved == approved_only]
        return entries[-limit:]

    def summary(self) -> dict:
        total = len(self._entries)
        approved = sum(1 for e in self._entries if e.approved)
        denied = total - approved
        by_level: dict[str, int] = {}
        by_action: dict[str, int] = {}
        errors = sum(1 for e in self._entries if e.error)
        for e in self._entries:
            by_level[e.autonomy_level.value] = by_level.get(e.autonomy_level.value, 0) + 1
            by_action[e.action.value] = by_action.get(e.action.value, 0) + 1
        return {
            "total_entries": total,
            "approved": approved,
            "denied": denied,
            "approval_rate": round(approved / max(total, 1), 3),
            "errors": errors,
            "by_level": by_level,
            "by_action": by_action,
        }

    def export(self, path: str) -> Path:
        out = Path(path)
        out.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))
        return out

    def _save(self) -> None:
        self.log_path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    def _load(self) -> None:
        if self.log_path.exists():
            try:
                data = json.loads(self.log_path.read_text())
                self._entries = [AuditEntry(**e) for e in data]
            except Exception:
                self._entries = []
