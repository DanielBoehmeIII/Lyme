"""AuditTrail — immutable audit trail for compliance."""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    action: str = ""
    actor: str = ""
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    previous_hash: str = ""
    hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = f"{self.action}{self.actor}{self.resource}{json.dumps(self.details, sort_keys=True)}{self.timestamp}{self.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "actor": self.actor,
            "resource": self.resource,
            "timestamp": self.timestamp,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
        }


@dataclass
class ComplianceReport:
    total_entries: int = 0
    unique_actors: int = 0
    date_range: str = ""
    verified: bool = False
    tampered_entries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "unique_actors": self.unique_actors,
            "date_range": self.date_range,
            "verified": self.verified,
            "tampered": self.tampered_entries,
        }


class AuditTrail:
    def __init__(self, storage_path: str = ".lyme/audit_trail"):
        self._path = Path(storage_path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._load()

    def record(self, action: str, actor: str, resource: str = "",
               details: Dict = None) -> AuditEntry:
        prev_hash = self._entries[-1].hash if self._entries else "0" * 16
        entry = AuditEntry(
            action=action, actor=actor, resource=resource,
            details=details or {}, previous_hash=prev_hash,
        )
        self._entries.append(entry)
        self._save()
        return entry

    def verify(self) -> ComplianceReport:
        report = ComplianceReport(total_entries=len(self._entries))
        actors = set()
        for i, entry in enumerate(self._entries):
            actors.add(entry.actor)
            expected_hash = entry._compute_hash()
            if entry.hash != expected_hash:
                report.tampered_entries += 1
            if i > 0:
                if entry.previous_hash != self._entries[i - 1].hash:
                    report.tampered_entries += 1
        report.unique_actors = len(actors)
        report.verified = report.tampered_entries == 0
        if self._entries:
            first = time.strftime("%Y-%m-%d", time.localtime(self._entries[0].timestamp))
            last = time.strftime("%Y-%m-%d", time.localtime(self._entries[-1].timestamp))
            report.date_range = f"{first} to {last}"
        return report

    def export(self, path: str) -> None:
        data = [e.to_dict() for e in self._entries]
        Path(path).write_text(json.dumps(data, indent=2))

    def _save(self) -> None:
        data = [e.to_dict() for e in self._entries]
        (self._path / "audit.json").write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self._path / "audit.json"
        if path.exists():
            try:
                for d in json.loads(path.read_text()):
                    self._entries.append(AuditEntry(**d))
            except Exception:
                pass
