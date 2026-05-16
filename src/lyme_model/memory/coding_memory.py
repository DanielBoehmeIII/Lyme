"""Week 81 — Local Agent Memory for Coding.

Memory types for Lyme Model:
- repo conventions
- successful patches
- failed patches
- test commands
- fragile files
- tool sequences
- recurring errors
- user preferences
- model-specific weaknesses

Does NOT let memory override fresh evidence.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import uuid


class MemoryType(str, Enum):
    REPO_CONVENTION = "repo_convention"
    SUCCESSFUL_PATCH = "successful_patch"
    FAILED_PATCH = "failed_patch"
    TEST_COMMAND = "test_command"
    FRAGILE_FILE = "fragile_file"
    TOOL_SEQUENCE = "tool_sequence"
    RECURRING_ERROR = "recurring_error"
    USER_PREFERENCE = "user_preference"
    MODEL_WEAKNESS = "model_weakness"


@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: MemoryType
    content: str
    confidence: float = 1.0
    source: str = ""
    repo: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[str] = None

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > expiry
        except Exception:
            return False

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content[:200],
            "confidence": self.confidence,
            "source": self.source,
            "repo": self.repo,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }


class MemoryStore:
    """Persistent memory store for Lyme Model."""

    def __init__(self, storage_path: str = ""):
        self.storage_path = storage_path
        self._entries: Dict[str, MemoryEntry] = {}

    def add(self, entry: MemoryEntry):
        self._entries[entry.memory_id] = entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now(timezone.utc).isoformat()
        return entry

    def query(self, memory_type: Optional[MemoryType] = None,
              repo: Optional[str] = None,
              min_confidence: float = 0.0,
              limit: int = 20) -> List[MemoryEntry]:
        results = []
        for e in self._entries.values():
            if e.is_expired():
                continue
            if memory_type and e.memory_type != memory_type:
                continue
            if repo and e.repo != repo:
                continue
            if e.confidence < min_confidence:
                continue
            results.append(e)
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]

    def count(self) -> int:
        return len(self._entries)

    def clear_expired(self):
        self._entries = {
            k: v for k, v in self._entries.items() if not v.is_expired()
        }


class CodingMemory:
    """Coding-specific memory for Lyme Model.

    Memory types cover all aspects of local coding agent experience.
    Fresh evidence always overrides memory.
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

    def remember_convention(self, convention: str, repo: str = "",
                             confidence: float = 0.8):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.REPO_CONVENTION,
            content=convention,
            confidence=confidence,
            repo=repo,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        ))

    def remember_successful_patch(self, file: str, change: str, repo: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.SUCCESSFUL_PATCH,
            content=f"{file}: {change}",
            confidence=0.9,
            source="verification_pass",
            repo=repo,
        ))

    def remember_failed_patch(self, file: str, error: str, repo: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.FAILED_PATCH,
            content=f"{file}: {error}",
            confidence=0.7,
            source="verification_fail",
            repo=repo,
        ))

    def remember_test_command(self, command: str, project: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.TEST_COMMAND,
            content=command,
            confidence=1.0,
            source="user",
            repo=project,
        ))

    def remember_fragile_file(self, path: str, reason: str, repo: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.FRAGILE_FILE,
            content=f"{path}: {reason}",
            confidence=0.8,
            repo=repo,
        ))

    def remember_recurring_error(self, error: str, pattern: str, repo: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.RECURRING_ERROR,
            content=f"{error} (pattern: {pattern})",
            confidence=0.75,
            repo=repo,
        ))

    def remember_user_preference(self, preference: str, repo: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.USER_PREFERENCE,
            content=preference,
            confidence=0.9,
            source="user",
            repo=repo,
        ))

    def remember_model_weakness(self, weakness: str, model: str = ""):
        self.store.add(MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=MemoryType.MODEL_WEAKNESS,
            content=f"{model}: {weakness}",
            confidence=0.85,
            source="self_observed",
        ))

    def get_conventions(self, repo: str = "") -> List[str]:
        entries = self.store.query(MemoryType.REPO_CONVENTION, repo=repo)
        return [e.content for e in entries]

    def get_test_commands(self, project: str = "") -> List[str]:
        entries = self.store.query(MemoryType.TEST_COMMAND, repo=project)
        return [e.content for e in entries]

    def get_fragile_files(self, repo: str = "") -> List[str]:
        entries = self.store.query(MemoryType.FRAGILE_FILE, repo=repo)
        return [e.content for e in entries]

    def get_recurring_errors(self, repo: str = "") -> List[str]:
        entries = self.store.query(MemoryType.RECURRING_ERROR, repo=repo)
        return [e.content for e in entries]

    def summary(self) -> Dict:
        by_type = {}
        for mt in MemoryType:
            count = len(self.store.query(memory_type=mt))
            if count > 0:
                by_type[mt.value] = count
        return {
            "total_entries": self.store.count(),
            "by_type": by_type,
        }
