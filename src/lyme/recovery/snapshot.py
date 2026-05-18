"""SnapshotManager — pre-edit file snapshots for rollback."""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FileSnapshot:
    file_path: str
    content: str
    hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "hash": self.hash,
            "timestamp": self.timestamp,
        }


class SnapshotManager:
    def __init__(self, repo_path: str = ".lyme/snapshots"):
        self._snap_dir = Path(repo_path)
        self._snap_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[str, FileSnapshot] = {}
        self._active_snapshot_id: Optional[str] = None

    def snapshot(self, file_paths: List[str]) -> str:
        snapshot_id = f"snap_{int(time.time() * 1000)}"
        for fp in file_paths:
            path = Path(fp)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                    snap = FileSnapshot(file_path=str(path.resolve()), content=content)
                    self._snapshots[snap.file_path] = snap
                except Exception:
                    continue

        self._active_snapshot_id = snapshot_id
        self._save(snapshot_id)
        return snapshot_id

    def restore(self, snapshot_id: Optional[str] = None) -> int:
        if snapshot_id:
            self._load(snapshot_id)

        restored = 0
        for fp, snap in list(self._snapshots.items()):
            try:
                path = Path(fp)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(snap.content)
                restored += 1
            except Exception:
                continue

        return restored

    def list_snapshots(self) -> List[Dict[str, Any]]:
        snapshots = []
        for path in sorted(self._snap_dir.glob("snapshot_*.json"), reverse=True):
            try:
                data = json.loads(path.read_text())
                snapshots.append({
                    "id": path.stem,
                    "timestamp": data.get("timestamp", 0),
                    "files": len(data.get("files", {})),
                })
            except Exception:
                continue
        return snapshots

    def _save(self, snapshot_id: str) -> None:
        path = self._snap_dir / f"{snapshot_id}.json"
        data = {
            "timestamp": time.time(),
            "files": {fp: s.to_dict() for fp, s in self._snapshots.items()},
        }
        path.write_text(json.dumps(data, indent=2))

    def _load(self, snapshot_id: str) -> None:
        path = self._snap_dir / f"{snapshot_id}.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for fp, sdata in data.get("files", {}).items():
                self._snapshots[fp] = FileSnapshot(
                    file_path=sdata["file_path"],
                    content=sdata.get("content", ""),
                    hash=sdata.get("hash", ""),
                    timestamp=sdata.get("timestamp", 0),
                )
        except Exception:
            pass
