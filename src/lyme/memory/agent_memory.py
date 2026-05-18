"""AgentMemory — integrated agent memory system with cross-session retrieval."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    key: str
    content: str
    entry_type: str  # convention, pattern, edit, failure, success
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "entry_type": self.entry_type,
            "tags": self.tags,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at,
        }


@dataclass
class Suggestion:
    pattern: str
    description: str
    confidence: float
    source: str  # repo_convention, past_edit, failure_pattern
    applicable_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "description": self.description[:100],
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "files": self.applicable_files[:5],
        }


class AgentMemory:
    def __init__(self, repo_path: str = "."):
        self._path = Path(repo_path) / ".lyme" / "agent_memory"
        self._path.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, MemoryEntry] = {}
        self._patterns: Dict[str, List[str]] = {}  # pattern -> file_keys
        self._load()

    def remember(self, entry: MemoryEntry) -> None:
        self._entries[entry.key] = entry
        for tag in entry.tags:
            if tag not in self._patterns:
                self._patterns[tag] = []
            self._patterns[tag].append(entry.key)
        self._save()

    def recall(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        query_lower = query.lower()
        scored: List[tuple[float, MemoryEntry]] = []

        for entry in self._entries.values():
            score = 0.0
            if query_lower in entry.content.lower():
                score += 2.0
            if query_lower in entry.key.lower():
                score += 3.0
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 1.0
            score *= (0.5 + entry.importance * 0.5)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        for _, entry in scored[:limit]:
            entry.access_count += 1
            entry.last_accessed = time.time()
        self._save()

        return [e for _, e in scored[:limit]]

    def suggest(self, file_path: str, task: str = "") -> List[Suggestion]:
        suggestions: List[Suggestion] = []
        path_lower = file_path.lower()

        for entry in self._entries.values():
            relevance = 0.0
            if path_lower in entry.key.lower() or any(
                tag.lower() in path_lower for tag in entry.tags
            ):
                relevance += 0.5
            if task and task.lower() in entry.content.lower():
                relevance += 0.3

            if relevance > 0:
                suggestions.append(Suggestion(
                    pattern=entry.key,
                    description=entry.content[:200],
                    confidence=entry.importance * relevance,
                    source=entry.entry_type,
                    applicable_files=[file_path],
                ))

        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:5]

    def remember_edit(self, file_path: str, description: str, success: bool) -> None:
        self.remember(MemoryEntry(
            key=f"edit:{file_path}:{int(time.time())}",
            content=f"{'Successful' if success else 'Failed'} edit on {file_path}: {description}",
            entry_type="success" if success else "failure",
            tags=[file_path.split("/")[-1].split(".")[0], "edit"],
            importance=0.7 if success else 0.3,
        ))

    def remember_convention(self, file_path: str, convention: str) -> None:
        self.remember(MemoryEntry(
            key=f"convention:{file_path}",
            content=convention,
            entry_type="convention",
            tags=[file_path.split("/")[-1].split(".")[0], "convention"],
            importance=0.8,
        ))

    def stats(self) -> Dict[str, Any]:
        types: Dict[str, int] = {}
        for entry in self._entries.values():
            types[entry.entry_type] = types.get(entry.entry_type, 0) + 1
        return {
            "total_entries": len(self._entries),
            "by_type": types,
            "avg_importance": sum(e.importance for e in self._entries.values()) / max(len(self._entries), 1),
            "patterns": len(self._patterns),
        }

    def get_fragile_files(self) -> List[str]:
        fragile = []
        for entry in self._entries.values():
            if entry.entry_type == "failure" and entry.importance > 0.5:
                for tag in entry.tags:
                    if tag not in ("edit", "failure"):
                        fragile.append(tag)
        return list(set(fragile))

    def clear(self) -> None:
        self._entries.clear()
        self._patterns.clear()
        self._save()

    def _save(self) -> None:
        data = {
            "entries": {k: v.to_dict() for k, v in self._entries.items()},
            "patterns": self._patterns,
        }
        (self._path / "memory.json").write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self._path / "memory.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for k, v in data.get("entries", {}).items():
                    entry = MemoryEntry(
                        key=v["key"],
                        content=v.get("content", ""),
                        entry_type=v["entry_type"],
                        tags=v.get("tags", []),
                        importance=v.get("importance", 0.5),
                        access_count=v.get("access_count", 0),
                        created_at=v.get("created_at", 0),
                        last_accessed=v.get("last_accessed", 0),
                    )
                    self._entries[k] = entry
                self._patterns = data.get("patterns", {})
            except Exception:
                pass
