"""Lyme Audit System — Every action replayable, inspectable, reversible.

Commands:
  lyme history       — View action history
  lyme replay <id>   — Replay a previous run
  lyme undo <id>     — Reverse a previous action
  lyme audit <id>    — Full audit trail for an action
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import uuid
import subprocess
import difflib


class ActionKind:
    BENCHMARK = "benchmark"
    EDIT = "edit"
    QUERY = "query"
    DIAGNOSE = "diagnose"
    DIFF = "diff"
    DISCOVER = "discover"
    LEARN = "learn"
    REPLAY = "replay"
    UNDO = "undo"


@dataclass
class AuditEntry:
    audit_id: str
    kind: str
    description: str
    timestamp: str
    author: str = "lyme"
    status: str = "completed"
    trace_id: Optional[str] = None
    patch_ids: List[str] = field(default_factory=list)
    files_affected: List[str] = field(default_factory=list)
    git_state_before: Optional[str] = None
    git_state_after: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    reversible: bool = False
    parent_audit_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "kind": self.kind,
            "description": self.description,
            "timestamp": self.timestamp,
            "author": self.author,
            "status": self.status,
            "trace_id": self.trace_id,
            "patch_ids": self.patch_ids,
            "files_affected": self.files_affected,
            "git_state_before": self.git_state_before,
            "git_state_after": self.git_state_after,
            "metadata": self.metadata,
            "reversible": self.reversible,
            "parent_audit_id": self.parent_audit_id,
        }


@dataclass
class AuditTrail:
    entries: List[AuditEntry] = field(default_factory=list)
    repo_path: str = ""

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "total_entries": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }

    def to_markdown(self, limit: int = 20) -> str:
        lines = []
        lines.append("# Lyme Audit Trail")
        lines.append(f"**Repository**: {self.repo_path}")
        lines.append(f"**Total actions**: {len(self.entries)}")
        lines.append("")
        lines.append("| ID | Kind | Description | Status | Reversible | Timestamp |")
        lines.append("|---|---|---|---|---|---|")
        for entry in self.entries[-limit:]:
            rev = "✓" if entry.reversible else "✗"
            desc = entry.description[:50].replace("|", "/")
            lines.append(
                f"| {entry.audit_id[:8]} | {entry.kind} | {desc} "
                f"| {entry.status} | {rev} | {entry.timestamp[:19]} |"
            )
        return "\n".join(lines)


@dataclass
class AuditReport:
    audit_id: str
    entry: AuditEntry
    trace: Optional[dict] = None
    patches: List[dict] = field(default_factory=list)
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    diff: Optional[str] = None
    can_undo: bool = False
    related_entries: List[AuditEntry] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Audit Report: {self.audit_id[:12]}")
        lines.append("")
        lines.append(f"**Action**: {self.entry.description}")
        lines.append(f"**Kind**: {self.entry.kind}")
        lines.append(f"**Time**: {self.entry.timestamp}")
        lines.append(f"**Status**: {self.entry.status}")
        lines.append(f"**Can undo**: {'Yes' if self.can_undo else 'No'}")
        lines.append("")
        lines.append("## Files Affected")
        for f in self.entry.files_affected:
            lines.append(f"- `{f}`")
        lines.append("")
        if self.diff:
            lines.append("## Diff")
            lines.append("```diff")
            lines.append(self.diff[:2000])
            lines.append("```")
            lines.append("")
        if self.related_entries:
            lines.append("## Related Actions")
            for rel in self.related_entries:
                lines.append(f"- {rel.audit_id[:8]} {rel.kind}: {rel.description[:60]}")
            lines.append("")
        if self.trace:
            lines.append("## Trace Summary")
            steps = self.trace.get("steps", [])
            lines.append(f"- Steps: {len(steps)}")
            decisions = self.trace.get("decisions", [])
            lines.append(f"- Decisions: {len(decisions)}")
            tool_calls = self.trace.get("tool_calls", [])
            lines.append(f"- Tool calls: {len(tool_calls)}")
        return "\n".join(lines)


class AuditSystem:
    """Complete audit trail for every Lyme action."""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self._entries: List[AuditEntry] = []
        self._load()

    @property
    def _audit_dir(self) -> Path:
        return self.repo_path / ".lyme" / "audit"

    def _load(self):
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(self._audit_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                entry = AuditEntry(**{k: v for k, v in data.items()
                                      if k in AuditEntry.__dataclass_fields__})
                self._entries.append(entry)
            except Exception:
                pass

    def record(self, kind: str, description: str,
               files_affected: Optional[List[str]] = None,
               trace_id: Optional[str] = None,
               metadata: Optional[dict] = None,
               reversible: bool = False,
               parent_audit_id: Optional[str] = None) -> AuditEntry:

        git_before = self._capture_git_state()

        entry = AuditEntry(
            audit_id=str(uuid.uuid4()),
            kind=kind,
            description=description,
            timestamp=datetime.now(timezone.utc).isoformat(),
            files_affected=files_affected or [],
            trace_id=trace_id,
            metadata=metadata or {},
            reversible=reversible,
            git_state_before=git_before,
            parent_audit_id=parent_audit_id,
        )

        entry.git_state_after = self._capture_git_state()

        self._entries.append(entry)
        self._save(entry)

        return entry

    def _save(self, entry: AuditEntry):
        path = self._audit_dir / f"{entry.audit_id}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2, default=str))

    def _capture_git_state(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            return result.stdout.strip()[:16] if result.returncode == 0 else None
        except Exception:
            return None

    def get_history(self, limit: int = 50,
                    kind_filter: Optional[str] = None) -> AuditTrail:
        entries = self._entries
        if kind_filter:
            entries = [e for e in entries if e.kind == kind_filter]
        entries = entries[-limit:]
        return AuditTrail(entries=entries, repo_path=str(self.repo_path))

    def get_entry(self, audit_id: str) -> Optional[AuditEntry]:
        for entry in self._entries:
            if entry.audit_id == audit_id or entry.audit_id.startswith(audit_id):
                return entry
        return None

    def get_report(self, audit_id: str) -> Optional[AuditReport]:
        entry = self.get_entry(audit_id)
        if not entry:
            return None

        trace = None
        if entry.trace_id:
            trace_path = self.repo_path / ".lyme" / "traces" / f"{entry.trace_id}.json"
            if trace_path.exists():
                try:
                    trace = json.loads(trace_path.read_text())
                except Exception:
                    pass

        patches = []
        for pid in entry.patch_ids:
            patch_path = self.repo_path / ".lyme" / "patches" / f"{pid}.json"
            if patch_path.exists():
                try:
                    patches.append(json.loads(patch_path.read_text()))
                except Exception:
                    pass

        diff = None
        if entry.files_affected and len(entry.files_affected) == 1:
            file_path = self.repo_path / entry.files_affected[0]
            if file_path.exists():
                if entry.git_state_before and entry.git_state_after:
                    try:
                        result = subprocess.run(
                            ["git", "diff", entry.git_state_before[:16],
                             entry.git_state_after[:16], "--", entry.files_affected[0]],
                            capture_output=True, text=True, cwd=self.repo_path, timeout=10,
                        )
                        diff = result.stdout
                    except Exception:
                        pass

        related = [
            e for e in self._entries
            if e.parent_audit_id == entry.audit_id
            or e.audit_id == entry.parent_audit_id
        ]

        return AuditReport(
            audit_id=entry.audit_id,
            entry=entry,
            trace=trace,
            patches=patches,
            diff=diff,
            can_undo=entry.reversible,
            related_entries=related,
        )

    def can_undo(self, audit_id: str) -> bool:
        entry = self.get_entry(audit_id)
        if not entry:
            return False
        return entry.reversible

    def undo(self, audit_id: str) -> bool:
        entry = self.get_entry(audit_id)
        if not entry or not entry.reversible:
            return False

        success = True
        for file_path in reversed(entry.files_affected):
            try:
                full_path = self.repo_path / file_path
                if entry.git_state_before:
                    result = subprocess.run(
                        ["git", "checkout", entry.git_state_before[:16], "--", file_path],
                        capture_output=True, text=True, cwd=self.repo_path, timeout=10,
                    )
                    if result.returncode != 0:
                        success = False
            except Exception:
                success = False

        if success:
            self.record(
                kind=ActionKind.UNDO,
                description=f"Undo: {entry.description}",
                files_affected=entry.files_affected,
                reversible=False,
                parent_audit_id=entry.audit_id,
                metadata={"undo_target": audit_id, "success": True},
            )

        return success

    def get_trail_for_action(self, audit_id: str) -> List[AuditEntry]:
        chain = []
        current = self.get_entry(audit_id)
        while current:
            chain.insert(0, current)
            if current.parent_audit_id:
                current = self.get_entry(current.parent_audit_id)
            else:
                break
        return chain
