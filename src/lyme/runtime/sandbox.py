import os
import io
import time
import signal
import difflib
import logging
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path
from glob import glob as glob_glob


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: float = 0.0
    timed_out: bool = False

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout[:2000],
            "stderr": self.stderr[:1000],
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
        }


class Sandbox:
    def __init__(self, work_dir: str = "./lyme-sandbox", memory_limit_mb: int = 1024):
        self.work_dir = Path(work_dir).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.memory_limit_mb = memory_limit_mb
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._logger = logging.getLogger("lyme.sandbox")

    def run(self, command: str, timeout: float = 30.0,
            env: Optional[dict] = None) -> ExecutionResult:
        self._cancelled.clear()
        result = ExecutionResult()
        start = time.time()

        full_env = {**os.environ, **(env or {})}
        if "PATH" not in full_env:
            full_env["PATH"] = "/usr/local/bin:/usr/bin:/bin"

        try:
            self._process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.work_dir),
                env=full_env,
                text=True,
                preexec_fn=self._set_resource_limits,
            )

            monitor = threading.Thread(target=self._memory_monitor, daemon=True)
            monitor.start()

            try:
                stdout_bytes, stderr_bytes = self._process.communicate(timeout=timeout)
                result.stdout = stdout_bytes or ""
                result.stderr = stderr_bytes or ""
                result.exit_code = self._process.returncode
            except subprocess.TimeoutExpired:
                self._kill_process()
                stdout_remaining, stderr_remaining = self._process.communicate()
                result.stdout = stdout_remaining or ""
                result.stderr = stderr_remaining or ""
                result.exit_code = -1
                result.timed_out = True
                self._logger.warning(f"Command timed out after {timeout}s: {command[:120]}")

        except FileNotFoundError as e:
            result.stderr = f"Command not found: {e}"
            result.exit_code = 127
        except PermissionError as e:
            result.stderr = f"Permission denied: {e}"
            result.exit_code = 126
        except Exception as e:
            result.stderr = f"Execution error: {e}"
            result.exit_code = 1
            self._logger.error(f"Sandbox execution error: {e}")
        finally:
            result.duration_ms = (time.time() - start) * 1000
            self._process = None

        return result

    def read_file(self, path: str) -> str:
        full_path = self._resolve_path(path)
        self._validate_path(full_path)
        try:
            return full_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {full_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {full_path}")

    def write_file(self, path: str, content: str) -> None:
        full_path = self._resolve_path(path)
        self._validate_path(full_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            full_path.write_text(content, encoding="utf-8")
        except PermissionError:
            raise PermissionError(f"Permission denied: {full_path}")

    def diff_files(self, old_path: str, new_path: str,
                   context_lines: int = 3) -> str:
        old_full = self._resolve_path(old_path)
        new_full = self._resolve_path(new_path)
        self._validate_path(old_full)
        self._validate_path(new_full)

        try:
            old_content = old_full.read_text(encoding="utf-8").splitlines(keepends=True)
        except FileNotFoundError:
            old_content = []

        try:
            new_content = new_full.read_text(encoding="utf-8").splitlines(keepends=True)
        except FileNotFoundError:
            new_content = []

        diff = difflib.unified_diff(
            old_content,
            new_content,
            fromfile=str(old_path),
            tofile=str(new_path),
            n=context_lines,
        )
        return "".join(diff)

    def diff_strings(self, old_text: str, new_text: str,
                     context_lines: int = 3) -> str:
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="original",
            tofile="modified",
            n=context_lines,
        )
        return "".join(diff)

    def run_tests(self, test_pattern: str = "test_*.py",
                  timeout: float = 60.0) -> ExecutionResult:
        matches = list(self.work_dir.rglob(test_pattern))
        if not matches:
            return ExecutionResult(
                stdout="",
                stderr=f"No test files matched pattern: {test_pattern}",
                exit_code=0,
                duration_ms=0.0,
            )

        test_files = [str(m.relative_to(self.work_dir)) for m in matches]
        command = f"python -m pytest {' '.join(test_files)} -v"
        return self.run(command, timeout=timeout)

    def cancel(self) -> None:
        self._cancelled.set()
        self._kill_process()

    def cleanup(self) -> None:
        self.cancel()
        if self.work_dir.exists():
            import shutil
            shutil.rmtree(str(self.work_dir), ignore_errors=True)

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.work_dir / p
        return p.resolve()

    def _validate_path(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self.work_dir.resolve())
        except ValueError:
            raise PermissionError(
                f"Access denied: {path} is outside sandbox directory {self.work_dir}"
            )

    def _kill_process(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._process.send_signal(signal.SIGTERM)
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait()
                except ProcessLookupError:
                    pass

    def _set_resource_limits(self) -> None:
        try:
            import resource
            memory_bytes = self.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            resource.setrlimit(resource.RLIMIT_RSS, (memory_bytes, memory_bytes))
        except (ImportError, ResourceWarning):
            pass

    def _memory_monitor(self) -> None:
        proc_obj = getattr(self, '_process', None)
        if proc_obj is None or proc_obj.pid is None:
            return
        try:
            import psutil
            try:
                proc = psutil.Process(proc_obj.pid)
            except (psutil.NoSuchProcess, ProcessLookupError):
                return
                while self._process and self._process.poll() is None:
                    if self._cancelled.is_set():
                        self._kill_process()
                        break
                    try:
                        mem = proc.memory_info().rss / (1024 * 1024)
                        if mem > self.memory_limit_mb:
                            self._kill_process()
                            break
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        break
                    time.sleep(0.5)
        except ImportError:
            pass
        except Exception:
            pass  # Daemon thread - don't crash on cleanup race

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
