import os
import sys
import time
import json
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

from ..config import AgentConfig
from ..telemetry import Tracer, EventLog, MetricsStore, Event, EventType


class AgentRunnerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class AgentResult:
    status: AgentRunnerStatus = AgentRunnerStatus.IDLE
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    exit_code: Optional[int] = None
    error: Optional[str] = None
    tool_calls: List[dict] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    events: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "error": self.error,
            "tool_calls_count": len(self.tool_calls),
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "events_count": len(self.events),
        }


class AgentRunner:
    def __init__(self, config: AgentConfig, tracer: Tracer = None,
                 event_log: EventLog = None, metrics: MetricsStore = None):
        self.config = config
        self.tracer = tracer or Tracer()
        self.event_log = event_log or EventLog()
        self.metrics = metrics or MetricsStore()
        self._process: Optional[subprocess.Popen] = None
        self._stdout_buf: List[str] = []
        self._stderr_buf: List[str] = []
        self._lock = threading.Lock()

    def run(self, prompt: str, work_dir: Path, timeout_s: int = 120,
            env: dict = None) -> AgentResult:
        result = AgentResult()
        start = time.time()

        cmd = self._build_command()
        full_env = {**os.environ, **self.config.env, **(env or {})}

        self.event_log.emit(
            EventType.SYSTEM,
            {"description": f"Starting agent: {self.config.name}",
             "command": " ".join(cmd), "work_dir": str(work_dir)},
            source="runner",
        )

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
                env=full_env,
                text=True,
            )

            stdout_thread = threading.Thread(
                target=self._capture_stdout, daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._capture_stderr, daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            self._process.stdin.write(prompt)
            self._process.stdin.flush()
            self._process.stdin.close()

            try:
                self._process.wait(timeout=timeout_s)
                result.exit_code = self._process.returncode
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
                result.status = AgentRunnerStatus.TIMEOUT
                result.error = f"Timed out after {timeout_s}s"
                self.event_log.emit(
                    EventType.ERROR,
                    {"description": result.error, "timeout_s": timeout_s},
                    severity="error", source="runner",
                )

            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            result.stdout = "".join(self._stdout_buf)
            result.stderr = "".join(self._stderr_buf)
            result.duration_ms = (time.time() - start) * 1000

            if result.status != AgentRunnerStatus.TIMEOUT:
                result.status = AgentRunnerStatus.SUCCESS if result.exit_code == 0 else AgentRunnerStatus.FAILURE

            self.metrics.record("agent.duration_ms", result.duration_ms,
                                tags={"agent": self.config.name})
            self.metrics.record("agent.exit_code", float(result.exit_code or -1),
                                tags={"agent": self.config.name})

            self.event_log.emit(
                EventType.SYSTEM,
                {"description": f"Agent finished: {result.status.value}",
                 "duration_ms": result.duration_ms,
                 "exit_code": result.exit_code},
                source="runner",
            )

        except Exception as e:
            result.status = AgentRunnerStatus.ERROR
            result.error = str(e)
            self.event_log.emit(
                EventType.ERROR,
                {"description": f"Runner error: {e}"},
                severity="error", source="runner",
            )
        finally:
            self._process = None

        return result

    def _build_command(self) -> list:
        cmd = self.config.command.split()
        return cmd

    def _capture_stdout(self):
        if self._process and self._process.stdout:
            for line in iter(self._process.stdout.readline, ""):
                with self._lock:
                    self._stdout_buf.append(line)

    def _capture_stderr(self):
        if self._process and self._process.stderr:
            for line in iter(self._process.stderr.readline, ""):
                with self._lock:
                    self._stderr_buf.append(line)

    def cancel(self):
        if self._process:
            self._process.kill()
