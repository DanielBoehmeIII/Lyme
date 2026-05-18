"""RepoWatcher — watches for commits, test failures, architecture drift, debt."""
from __future__ import annotations
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class WatchEvent:
    COMMIT = "commit"
    TEST_FAILURE = "test_failure"
    ARCH_DRIFT = "architecture_drift"
    TECH_DEBT = "technical_debt"
    DEP_UPDATE = "dependency_update"


@dataclass
class WatchConfig:
    repo_path: str = "."
    poll_interval_s: int = 60
    watch_commits: bool = True
    watch_tests: bool = True
    watch_arch: bool = True
    max_events: int = 100


class RepoWatcher:
    def __init__(self, config: WatchConfig = None):
        self.config = config or WatchConfig()
        self._handlers: Dict[str, List[Callable]] = {}
        self._last_commit = ""
        self._events: List[Dict[str, Any]] = []
        self._intel_engine = None

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def poll(self) -> List[Dict[str, Any]]:
        events = []

        if self.config.watch_commits:
            events.extend(self._check_commits())

        if self.config.watch_tests:
            events.extend(self._check_tests())

        if self.config.watch_arch:
            events.extend(self._check_architecture())

        # Run passive intelligence every poll
        try:
            intel_events = self._run_intelligence()
            events.extend(intel_events)
        except Exception:
            pass

        for event in events:
            self._events.append(event)
            for handler in self._handlers.get(event["type"], []):
                try:
                    handler(event)
                except Exception:
                    pass

        if len(self._events) > self.config.max_events:
            self._events = self._events[-self.config.max_events:]

        return events

    def _run_intelligence(self) -> List[Dict[str, Any]]:
        events = []
        try:
            from ..intelligence.engine import IntelligenceEngine
            if self._intel_engine is None:
                self._intel_engine = IntelligenceEngine(str(self.config.repo_path))
            report = self._intel_engine.run_fast()
            if report.warning_count > 0:
                events.append({
                    "type": WatchEvent.ARCH_DRIFT if report.drift and report.drift.total_drift > 0 else WatchEvent.TECH_DEBT,
                    "summary": report.summary,
                    "warnings": report.warning_count,
                    "timestamp": report.timestamp,
                })
        except Exception:
            pass
        return events

    def _check_commits(self) -> List[Dict[str, Any]]:
        events = []
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True,
                cwd=self.config.repo_path, timeout=5,
            )
            current = result.stdout.strip()
            if current and current != self._last_commit:
                if self._last_commit:
                    events.append({
                        "type": WatchEvent.COMMIT,
                        "hash": current.split()[0],
                        "message": " ".join(current.split()[1:]),
                        "timestamp": time.time(),
                    })
                self._last_commit = current
        except Exception:
            pass
        return events

    def _check_tests(self) -> List[Dict[str, Any]]:
        events = []
        try:
            result = subprocess.run(
                ["pytest", "--tb=no", "--summary", "-q"],
                capture_output=True, text=True,
                cwd=self.config.repo_path, timeout=30,
            )
            if result.returncode != 0:
                events.append({
                    "type": WatchEvent.TEST_FAILURE,
                    "output": result.stdout[-200:],
                    "timestamp": time.time(),
                })
        except Exception:
            pass
        return events

    def _check_architecture(self) -> List[Dict[str, Any]]:
        return []

    def get_events(self, since: float = 0) -> List[Dict[str, Any]]:
        return [e for e in self._events if e.get("timestamp", 0) >= since]

    def run_forever(self) -> None:
        while True:
            self.poll()
            time.sleep(self.config.poll_interval_s)
