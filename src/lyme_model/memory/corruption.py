"""Week 82 — Memory Corruption Detection.

Detects when memory is:
- stale
- contradicted by code
- overgeneralized
- repo-specific but applied globally
- based on failed run
- too vague
- harmful to retrieval
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re

from .coding_memory import MemoryEntry, MemoryType, MemoryStore


@dataclass
class CorruptionFlag:
    memory_id: str
    issue: str
    severity: str  # info, warning, critical
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "issue": self.issue,
            "severity": self.severity,
            "details": self.details[:200],
        }


@dataclass
class MemoryAuditReport:
    total_entries: int = 0
    corrupt_entries: int = 0
    stale_entries: int = 0
    contradicted_entries: int = 0
    overgeneralized_entries: int = 0
    repo_mismatch_entries: int = 0
    failed_run_entries: int = 0
    vague_entries: int = 0
    flags: List[CorruptionFlag] = field(default_factory=list)
    healthy_ratio: float = 1.0

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "corrupt_entries": self.corrupt_entries,
            "stale_entries": self.stale_entries,
            "contradicted_entries": self.contradicted_entries,
            "overgeneralized_entries": self.overgeneralized_entries,
            "repo_mismatch_entries": self.repo_mismatch_entries,
            "failed_run_entries": self.failed_run_entries,
            "vague_entries": self.vague_entries,
            "healthy_ratio": round(self.healthy_ratio, 4),
            "flags": [f.to_dict() for f in self.flags],
        }


class CorruptionDetector:
    """Detects corruption in coding memory entries."""

    def __init__(self, store: MemoryStore, repo_path: str = "."):
        self.store = store
        self.repo_path = Path(repo_path)

    def audit(self) -> MemoryAuditReport:
        report = MemoryAuditReport()
        all_entries = self.store._entries.values()
        report.total_entries = len(all_entries)

        for entry in all_entries:
            # Check staleness
            if entry.is_expired():
                report.stale_entries += 1
                report.corrupt_entries += 1
                report.flags.append(CorruptionFlag(
                    memory_id=entry.memory_id,
                    issue="stale",
                    severity="warning",
                    details=f"Entry expired at {entry.expires_at}",
                ))
                continue

            # Check age (older than 60 days without access)
            try:
                created = datetime.fromisoformat(entry.created_at)
                age = datetime.now(timezone.utc) - created
                if age > timedelta(days=60) and entry.access_count == 0:
                    report.stale_entries += 1
                    report.corrupt_entries += 1
                    report.flags.append(CorruptionFlag(
                        memory_id=entry.memory_id,
                        issue="stale (unaccessed, >60 days old)",
                        severity="info",
                    ))
            except Exception:
                pass

            # Check for vagueness
            if self._is_vague(entry.content):
                report.vague_entries += 1
                report.corrupt_entries += 1
                report.flags.append(CorruptionFlag(
                    memory_id=entry.memory_id,
                    issue="too vague",
                    severity="warning",
                    details=f"Content too vague to be useful: {entry.content[:80]}",
                ))

            # Check for overgeneralization
            if self._is_overgeneralized(entry):
                report.overgeneralized_entries += 1
                report.corrupt_entries += 1
                report.flags.append(CorruptionFlag(
                    memory_id=entry.memory_id,
                    issue="overgeneralized",
                    severity="warning",
                    details="Memory uses non-specific language without repo context",
                ))

            # Check for failed-run source
            if entry.source == "verification_fail" and entry.confidence > 0.5:
                report.failed_run_entries += 1
                report.flags.append(CorruptionFlag(
                    memory_id=entry.memory_id,
                    issue="based on failed run",
                    severity="info",
                    details="High confidence memory from a failed run",
                ))

        total = report.total_entries
        report.healthy_ratio = (total - report.corrupt_entries) / total if total > 0 else 1.0
        return report

    def quarantine(self, entry: MemoryEntry) -> bool:
        """Remove a corrupt entry from the store."""
        if entry.memory_id in self.store._entries:
            del self.store._entries[entry.memory_id]
            return True
        return False

    def _is_vague(self, content: str) -> bool:
        vague_patterns = [
            r"^(something|thing|stuff|code|it|that)$",
            r"^.{0,10}$",  # Too short
        ]
        for p in vague_patterns:
            if re.match(p, content.strip()):
                return True
        return False

    def _is_overgeneralized(self, entry: MemoryEntry) -> bool:
        vague_words = ["always", "never", "everyone", "nobody", "everything", "nothing"]
        content_lower = entry.content.lower()
        return any(w in content_lower for w in vague_words) and not entry.repo
