import json
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class CrashSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CrashReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    command: str = ""
    error_type: str = ""
    error_message: str = ""
    traceback: str = ""
    severity: CrashSeverity = CrashSeverity.MEDIUM
    user_id: str = ""
    session_id: str = ""
    context: dict = field(default_factory=dict)
    frequency_count: int = 1
    resolved: bool = False
    resolved_at: Optional[float] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "command": self.command,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "context": self.context,
            "frequency_count": self.frequency_count,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "tags": self.tags,
        }


class CrashReporter:
    def __init__(self, storage_dir: str = ".lyme/analytics/crashes"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._reports: dict[str, CrashReport] = {}
        self._load()

    def _reports_path(self) -> Path:
        return self._storage_dir / "crash_index.json"

    def _load(self):
        path = self._reports_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for d in data:
                    report = CrashReport(
                        report_id=d.get("report_id"),
                        timestamp=d.get("timestamp", time.time()),
                        command=d.get("command", ""),
                        error_type=d.get("error_type", ""),
                        error_message=d.get("error_message", ""),
                        traceback=d.get("traceback", ""),
                        severity=CrashSeverity(d.get("severity", "medium")),
                        user_id=d.get("user_id", ""),
                        session_id=d.get("session_id", ""),
                        context=d.get("context", {}),
                        frequency_count=d.get("frequency_count", 1),
                        resolved=d.get("resolved", False),
                        resolved_at=d.get("resolved_at"),
                        tags=d.get("tags", []),
                    )
                    self._reports[report.report_id] = report
            except Exception:
                pass

    def _save(self):
        data = [r.to_dict() for r in self._reports.values()]
        self._reports_path().write_text(json.dumps(data, indent=2))

    def record(
        self,
        command: str = "",
        error: Optional[Exception] = None,
        error_type: str = "",
        error_message: str = "",
        severity: CrashSeverity = CrashSeverity.MEDIUM,
        user_id: str = "",
        session_id: str = "",
        context: dict = None,
    ) -> CrashReport:
        if error:
            error_type = error_type or type(error).__name__
            error_message = error_message or str(error)
            tb = traceback.format_exc()
        else:
            tb = ""

        dedup_key = f"{command}:{error_type}:{error_message[:100]}"
        for existing in self._reports.values():
            if (existing.command == command
                    and existing.error_type == error_type
                    and existing.error_message[:100] == error_message[:100]):
                existing.frequency_count += 1
                existing.timestamp = time.time()
                existing.severity = self._escalate_severity(existing.severity, frequency=existing.frequency_count)
                self._save()
                return existing

        report = CrashReport(
            command=command,
            error_type=error_type,
            error_message=error_message,
            traceback=tb,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            context=context or {},
        )
        self._reports[report.report_id] = report
        self._save()
        return report

    def _escalate_severity(self, current: CrashSeverity, frequency: int) -> CrashSeverity:
        if frequency >= 10:
            return CrashSeverity.CRITICAL
        if frequency >= 5:
            return CrashSeverity.HIGH
        return current

    def mark_resolved(self, report_id: str):
        report = self._reports.get(report_id)
        if report:
            report.resolved = True
            report.resolved_at = time.time()
            self._save()

    def get_summary(self) -> dict:
        if not self._reports:
            return {"total_reports": 0, "unresolved": 0, "resolved": 0, "by_severity": {}, "by_command": {}, "most_frequent": []}
        by_severity = {}
        for r in self._reports.values():
            sev = r.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
        by_command = {}
        for r in self._reports.values():
            cmd = r.command or "unknown"
            by_command[cmd] = by_command.get(cmd, 0) + 1
        return {
            "total_reports": len(self._reports),
            "unresolved": sum(1 for r in self._reports.values() if not r.resolved),
            "resolved": sum(1 for r in self._reports.values() if r.resolved),
            "by_severity": by_severity,
            "by_command": dict(sorted(by_command.items(), key=lambda x: x[1], reverse=True)[:10]),
            "most_frequent": sorted(
                [r.to_dict() for r in self._reports.values()],
                key=lambda x: x["frequency_count"],
                reverse=True,
            )[:5],
        }

    def get_unresolved(self, severity: Optional[CrashSeverity] = None) -> list[CrashReport]:
        reports = [r for r in self._reports.values() if not r.resolved]
        if severity:
            reports = [r for r in reports if r.severity == severity]
        return sorted(reports, key=lambda r: r.timestamp, reverse=True)


crash_reporter = CrashReporter()
