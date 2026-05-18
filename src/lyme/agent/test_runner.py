"""TestRunner — runs tests and parses output for retry guidance."""
from __future__ import annotations
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TestSummary:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0

    @property
    def success_rate(self) -> float:
        return self.passed / max(self.total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "total": self.total,
            "success_rate": round(self.success_rate, 4),
        }


@dataclass
class TestResult:
    test_name: str
    status: str  # passed, failed, error, skipped
    duration_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "error_message": self.error_message[:200] if self.error_message else "",
        }


@dataclass
class TestRun:
    summary: TestSummary = field(default_factory=TestSummary)
    results: List[TestResult] = field(default_factory=list)
    stdout: str = ""
    duration_ms: float = 0.0
    command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results[:20]],
            "duration_ms": round(self.duration_ms, 2),
            "command": self.command,
        }


class TestRunner:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    def run(self, test_files: List[str] = None) -> TestRun:
        run = TestRun()

        # Auto-detect test command
        cmd = self._detect_test_command()
        if not cmd:
            run.summary.failed = 1
            run.summary.total = 1
            run.stdout = "No test command detected"
            return run

        run.command = cmd
        start = time.time()

        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=120,
            )
            run.stdout = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            run.stdout = "Test execution timed out (120s)"
            run.summary.failed = 1
            run.summary.total = 1
            run.duration_ms = (time.time() - start) * 1000
            return run
        except FileNotFoundError:
            run.stdout = "Test command not found"
            run.summary.failed = 1
            run.summary.total = 1
            run.duration_ms = (time.time() - start) * 1000
            return run

        run.duration_ms = (time.time() - start) * 1000

        # Parse pytest output
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("==") and "passed" in line and "failed" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        try:
                            run.summary.passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif "failed" in part:
                        try:
                            run.summary.failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass

            # Parse individual test results
            if line.startswith("FAILED") or line.startswith("PASSED") or line.startswith("ERROR"):
                parts = line.split()
                if len(parts) >= 2:
                    status = parts[0].lower()
                    test_name = parts[-1]
                    run.results.append(TestResult(
                        test_name=test_name,
                        status=status,
                    ))

            if line.startswith("ERRORS") or line.startswith("FAILURES"):
                run.summary.errors += 1

        run.summary.total = run.summary.passed + run.summary.failed + run.summary.skipped
        if run.summary.total == 0:
            run.summary.total = 1
            if result.returncode == 0:
                run.summary.passed = 1
            else:
                run.summary.failed = 1

        return run

    def _detect_test_command(self) -> Optional[str]:
        markers = [
            ("pyproject.toml", "pytest"),
            ("setup.cfg", "pytest"),
            ("pytest.ini", "pytest"),
            ("Makefile", "make test"),
            ("package.json", "npm test"),
        ]
        for marker, cmd in markers:
            if (self.repo_path / marker).exists():
                return cmd
        # Default
        if list(self.repo_path.rglob("test_*.py")):
            return "pytest"
        return None
