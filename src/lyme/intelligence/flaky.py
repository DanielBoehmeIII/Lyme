from __future__ import annotations
import json
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FlakyTestResult:
    test_name: str
    file_path: str
    runs: int = 0
    passes: int = 0
    failures: int = 0
    flake_rate: float = 0.0
    last_seen: float = 0.0
    error_messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "file_path": self.file_path,
            "runs": self.runs,
            "passes": self.passes,
            "failures": self.failures,
            "flake_rate": round(self.flake_rate, 3),
            "last_seen": self.last_seen,
            "error_messages": self.error_messages[:3],
        }

    def is_flaky(self, threshold: float = 0.3) -> bool:
        return self.runs >= 3 and self.flake_rate > 0 and self.flake_rate < 1.0


@dataclass
class FlakyReport:
    results: List[FlakyTestResult] = field(default_factory=list)
    total_tests: int = 0
    flaky_count: int = 0
    consistent_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "total_tests": self.total_tests,
            "flaky_count": self.flaky_count,
            "consistent_count": self.consistent_count,
        }

    def to_markdown(self) -> str:
        if not self.results:
            return "No flaky tests detected."
        lines = [f"## Flaky Test Report\n"]
        flaky = [r for r in self.results if r.is_flaky()]
        if not flaky:
            lines.append("No flaky tests detected.\n")
            return "\n".join(lines)
        lines.append(f"Found {len(flaky)} potentially flaky test(s):\n")
        for r in sorted(flaky, key=lambda x: x.flake_rate, reverse=True)[:10]:
            rate_pct = r.flake_rate * 100
            lines.append(f"- **{r.test_name}** ({rate_pct:.0f}% flaky, {r.passes}/{r.runs} passes)")
            if r.error_messages:
                lines.append(f"  - Last error: {r.error_messages[-1][:120]}")
            lines.append("")
        return "\n".join(lines)


class FlakyTestDetector:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "intel" / "flaky_db.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._history: Dict[str, FlakyTestResult] = {}
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text())
                for name, d in data.items():
                    self._history[name] = FlakyTestResult(**d)
            except Exception:
                pass

    def _save(self) -> None:
        data = {name: r.to_dict() for name, r in self._history.items()}
        self._db_path.write_text(json.dumps(data, indent=2))

    def run_detection(self, runs: int = 3) -> FlakyReport:
        tests = self._discover_tests()
        report = FlakyReport()
        report.total_tests = len(tests)

        for test_path in tests:
            outcomes = []
            for _ in range(runs):
                try:
                    result = subprocess.run(
                        ["pytest", test_path, "--tb=short", "-q"],
                        capture_output=True, text=True,
                        cwd=str(self._repo), timeout=120,
                    )
                    outcomes.append(result.returncode == 0)
                except Exception:
                    outcomes.append(False)

            passes = sum(1 for o in outcomes if o)
            failures = len(outcomes) - passes
            flake = 0.0
            if len(outcomes) > 0:
                flake = 1.0 - (passes / len(outcomes))
                if passes == 0 or passes == len(outcomes):
                    flake = 0.0

            test_name = self._test_name_from_path(test_path)
            entry = self._history.get(test_name, FlakyTestResult(
                test_name=test_name, file_path=test_path,
            ))
            entry.runs += len(outcomes)
            entry.passes += passes
            entry.failures += failures
            entry.flake_rate = 1.0 - (entry.passes / max(entry.runs, 1))
            if entry.passes == 0 or entry.passes == entry.runs:
                entry.flake_rate = 0.0
            entry.last_seen = time.time()
            if failures > 0:
                try:
                    error_text = subprocess.run(
                        ["pytest", test_path, "--tb=line", "-q"],
                        capture_output=True, text=True,
                        cwd=str(self._repo), timeout=60,
                    ).stderr
                    if error_text:
                        entry.error_messages.append(error_text[:200])
                        entry.error_messages = entry.error_messages[-5:]
                except Exception:
                    pass
            self._history[test_name] = entry
            report.results.append(entry)

        report.flaky_count = sum(1 for r in report.results if r.is_flaky())
        report.consistent_count = report.total_tests - report.flaky_count
        self._save()
        return report

    def analyze_existing(self) -> FlakyReport:
        tests = self._discover_tests()
        report = FlakyReport()
        report.total_tests = len(tests)

        for test_path in tests:
            test_name = self._test_name_from_path(test_path)
            entry = self._history.get(test_name, FlakyTestResult(
                test_name=test_name, file_path=test_path,
            ))
            if entry.runs == 0:
                continue
            report.results.append(entry)

        report.flaky_count = sum(1 for r in report.results if r.is_flaky())
        report.consistent_count = report.total_tests - report.flaky_count
        return report

    def _discover_tests(self) -> List[str]:
        try:
            result = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                capture_output=True, text=True,
                cwd=str(self._repo), timeout=30,
            )
            tests = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.endswith(".py") and "test_" in line:
                    tests.append(line)
                elif "::" in line:
                    parts = line.split("::")
                    if len(parts) >= 2 and ".py" in parts[0]:
                        tests.append(line)
            return tests[:20]
        except Exception:
            return []

    def _test_name_from_path(self, path: str) -> str:
        return path.replace("/", ".").replace("::", ".").replace(".py", "")
