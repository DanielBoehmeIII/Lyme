from __future__ import annotations
import json
import time
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TimelineEvent:
    event_type: str
    description: str
    timestamp: float = field(default_factory=time.time)
    branch: str = ""
    commit_hash: str = ""
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "author": self.author,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TimelineEvent:
        return cls(**d)


class RepoTimeline:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._path = self._repo / ".lyme" / "session" / "timeline.json"
        self._events: List[TimelineEvent] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._events = [TimelineEvent.from_dict(e) for e in data]
            except Exception:
                self._events = []

    def _save(self) -> None:
        data = [e.to_dict() for e in self._events]
        self._path.write_text(json.dumps(data, indent=2))

    def record(
        self,
        event_type: str,
        description: str,
        branch: str = "",
        commit_hash: str = "",
        author: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = TimelineEvent(
            event_type=event_type,
            description=description,
            branch=branch,
            commit_hash=commit_hash,
            author=author,
            metadata=metadata or {},
        )
        self._events.append(event)
        self._save()

    def record_session_start(self, branch: str = "") -> None:
        self.record("session_start", f"Session started on branch {branch}", branch=branch)

    def record_session_end(self, branch: str = "") -> None:
        self.record("session_end", f"Session ended on branch {branch}", branch=branch)

    def record_goal_created(self, description: str, branch: str = "") -> None:
        self.record("goal_created", f"Goal: {description}", branch=branch)

    def record_goal_completed(self, description: str, branch: str = "") -> None:
        self.record("goal_completed", f"Goal completed: {description}", branch=branch)

    def record_goal_failed(self, description: str, branch: str = "") -> None:
        self.record("goal_failed", f"Goal failed: {description}", branch=branch)

    def record_command(self, command: str, branch: str = "") -> None:
        self.record("command", f"Command: {command}", branch=branch)

    def record_branch_switch(self, from_branch: str, to_branch: str) -> None:
        self.record(
            "branch_switch",
            f"Switched from {from_branch} to {to_branch}",
            branch=to_branch,
        )

    def record_commit(self, commit_hash: str, message: str, branch: str = "", author: str = "") -> None:
        self.record(
            "commit", message,
            branch=branch, commit_hash=commit_hash, author=author,
        )

    def record_interruption(self, description: str, branch: str = "") -> None:
        self.record("interruption", description, branch=branch)

    # --- Git-aware sync ---

    def sync_from_git(self) -> int:
        count = 0
        try:
            log = subprocess.run(
                ["git", "log", "--oneline", "-50", "--format=%H|%s|%an|%D"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            known_hashes = {e.commit_hash for e in self._events if e.commit_hash}
            for line in log.stdout.splitlines():
                parts = line.split("|", 3)
                if len(parts) >= 3:
                    h, msg, author = parts[0], parts[1], parts[2]
                    refs = parts[3] if len(parts) > 3 else ""
                    if h not in known_hashes:
                        branch = ""
                        if "HEAD ->" in refs:
                            branch = refs.split("HEAD ->")[1].split(",")[0].strip()
                        self.record_commit(h, msg, branch=branch, author=author)
                        known_hashes.add(h)
                        count += 1
        except Exception:
            pass
        if count:
            self._save()
        return count

    # --- Query ---

    def events_since(self, since_timestamp: float) -> List[TimelineEvent]:
        return [e for e in self._events if e.timestamp >= since_timestamp]

    def events_of_type(self, event_type: str, limit: int = 20) -> List[TimelineEvent]:
        filtered = [e for e in self._events if e.event_type == event_type]
        return filtered[-limit:]

    def events_on_branch(self, branch: str, limit: int = 20) -> List[TimelineEvent]:
        filtered = [e for e in self._events if e.branch == branch]
        return filtered[-limit:]

    def recent(self, limit: int = 20) -> List[TimelineEvent]:
        return self._events[-limit:]

    def all_events(self) -> List[TimelineEvent]:
        return list(self._events)

    def summary(self) -> Dict[str, Any]:
        today = time.time() - 86400
        this_week = time.time() - 86400 * 7
        return {
            "total_events": len(self._events),
            "today": len(self.events_since(today)),
            "this_week": len(self.events_since(this_week)),
            "commits": len(self.events_of_type("commit")),
            "goals_completed": len(self.events_of_type("goal_completed")),
            "goals_created": len(self.events_of_type("goal_created")),
            "sessions": len(self.events_of_type("session_start")),
            "branches": list({e.branch for e in self._events if e.branch}),
        }

    def current_branch_work(self) -> Dict[str, Any]:
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self._repo),
            ).stdout.strip()
        except Exception:
            branch = "unknown"
        return {
            "branch": branch,
            "events": [e.to_dict() for e in self.events_on_branch(branch, limit=10)],
        }
