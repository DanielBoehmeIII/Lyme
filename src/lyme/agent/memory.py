"""ExecutionMemory — persistent cross-session execution memory."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionRecord:
    task: str
    status: str = "unknown"
    patches: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "status": self.status,
            "patch_count": len(self.patches),
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


class ExecutionMemory:
    def __init__(self, repo_path: str = "."):
        self._path = Path(repo_path) / ".lyme" / "agent_memory"
        self._path.mkdir(parents=True, exist_ok=True)
        self._records: List[ExecutionRecord] = []
        self._load()

    def store(self, record: ExecutionRecord) -> None:
        self._records.append(record)
        self._save()

    def search(self, query: str, limit: int = 10) -> List[ExecutionRecord]:
        query_lower = query.lower()
        words = query_lower.split()
        scored: List[tuple[float, ExecutionRecord]] = []

        for rec in self._records:
            score = 0.0
            task_lower = rec.task.lower()
            for word in words:
                if word in task_lower:
                    score += 1.0
            if rec.status == "failed":
                score *= 0.5
            if score > 0:
                scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    def recent(self, limit: int = 10) -> List[ExecutionRecord]:
        sorted_records = sorted(self._records, key=lambda r: r.timestamp, reverse=True)
        return sorted_records[:limit]

    def stats(self) -> Dict[str, Any]:
        total = len(self._records)
        success = sum(1 for r in self._records if r.status == "success")
        failed = sum(1 for r in self._records if r.status in ("failed", "partial"))
        return {
            "total_executions": total,
            "successful": success,
            "failed": failed,
            "success_rate": success / max(total, 1),
        }

    def clear(self) -> None:
        self._records.clear()
        self._save()

    def _save(self) -> None:
        path = self._path / "memory.json"
        data = [r.to_dict() for r in self._records]
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self._path / "memory.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._records = [ExecutionRecord(**r) for r in data]
            except Exception:
                self._records = []
