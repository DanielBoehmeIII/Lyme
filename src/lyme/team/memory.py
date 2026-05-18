"""SharedMemory — team-shared memory across repos and agents."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SharedEntry:
    key: str = ""
    content: str = ""
    team: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "team": self.team,
            "author": self.author,
            "tags": self.tags,
            "importance": self.importance,
        }


class SharedMemory:
    def __init__(self, storage_path: str = ".lyme/team_memory"):
        self._path = Path(storage_path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, SharedEntry] = {}
        self._load()

    def share(self, entry: SharedEntry) -> None:
        self._entries[entry.key] = entry
        self._save()

    def search(self, query: str, team: Optional[str] = None) -> List[SharedEntry]:
        q = query.lower()
        results = []
        for entry in self._entries.values():
            if team and entry.team != team:
                continue
            if q in entry.content.lower() or q in entry.key.lower():
                results.append(entry)
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:20]

    def list_by_team(self, team: str) -> List[SharedEntry]:
        return [e for e in self._entries.values() if e.team == team]

    def stats(self) -> Dict[str, Any]:
        teams = set(e.team for e in self._entries.values())
        return {
            "total": len(self._entries),
            "teams": len(teams),
            "team_list": list(teams),
        }

    def _save(self) -> None:
        data = [e.to_dict() for e in self._entries.values()]
        (self._path / "shared_memory.json").write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self._path / "shared_memory.json"
        if path.exists():
            try:
                for d in json.loads(path.read_text()):
                    e = SharedEntry(**d)
                    self._entries[e.key] = e
            except Exception:
                pass
