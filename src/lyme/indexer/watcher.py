"""FileWatcher — monitors file system for changes to trigger re-indexing."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileChangeEvent:
    file_path: str
    change_type: ChangeType
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp,
        }


class FileWatcher:
    def __init__(self, watch_dir: str, poll_interval: float = 2.0):
        self.watch_dir = Path(watch_dir).resolve()
        self.poll_interval = poll_interval
        self._mtimes: Dict[str, float] = {}
        self._handlers: List[Callable[[FileChangeEvent], None]] = []
        self._running = False

    def on_change(self, handler: Callable[[FileChangeEvent], None]) -> None:
        self._handlers.append(handler)

    def start(self) -> None:
        self._running = True
        self._mtimes = self._snapshot()

    def stop(self) -> None:
        self._running = False

    def poll(self) -> List[FileChangeEvent]:
        events: List[FileChangeEvent] = []
        current = self._snapshot()

        for path, mtime in current.items():
            if path not in self._mtimes:
                events.append(FileChangeEvent(
                    file_path=path, change_type=ChangeType.ADDED, timestamp=time.time(),
                ))
            elif mtime != self._mtimes[path]:
                events.append(FileChangeEvent(
                    file_path=path, change_type=ChangeType.MODIFIED, timestamp=time.time(),
                ))

        for path in self._mtimes:
            if path not in current:
                events.append(FileChangeEvent(
                    file_path=path, change_type=ChangeType.DELETED, timestamp=time.time(),
                ))

        self._mtimes = current

        for event in events:
            for handler in self._handlers:
                try:
                    handler(event)
                except Exception:
                    pass

        return events

    def poll_loop(self, callback: Callable[[List[FileChangeEvent]], None]) -> None:
        self.start()
        try:
            while self._running:
                events = self.poll()
                if events:
                    callback(events)
                time.sleep(self.poll_interval)
        finally:
            self.stop()

    def _snapshot(self) -> Dict[str, float]:
        mtimes: Dict[str, float] = {}
        if not self.watch_dir.exists():
            return mtimes
        for f in self.watch_dir.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                try:
                    mtimes[str(f)] = os.path.getmtime(f)
                except OSError:
                    continue
        return mtimes
