"""FlakyDetector — identifies flaky tests from historical run data."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FlakyTest:
    test_name: str
    flake_count: int = 0
    total_runs: int = 0
    flake_rate: float = 0.0
    last_flake: float = 0.0

    @property
    def is_flaky(self) -> bool:
        return self.flake_rate > 0.1 and self.total_runs >= 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "flake_count": self.flake_count,
            "total_runs": self.total_runs,
            "flake_rate": round(self.flake_rate, 4),
            "is_flaky": self.is_flaky,
        }


class FlakyDetector:
    def __init__(self):
        self._tests: Dict[str, FlakyTest] = {}

    def record_run(self, test_name: str, passed: bool) -> None:
        if test_name not in self._tests:
            self._tests[test_name] = FlakyTest(test_name=test_name)
        test = self._tests[test_name]
        test.total_runs += 1
        if not passed:
            test.flake_count += 1
            import time
            test.last_flake = time.time()
        test.flake_rate = test.flake_count / max(test.total_runs, 1)

    def get_flaky(self, threshold: float = 0.1) -> List[FlakyTest]:
        return [
            t for t in self._tests.values()
            if t.flake_rate > threshold and t.total_runs >= 3
        ]

    def get_stable(self) -> List[FlakyTest]:
        return [
            t for t in self._tests.values()
            if t.flake_rate <= 0.05 and t.total_runs >= 3
        ]

    def quarantine(self, test_name: str) -> bool:
        test = self._tests.get(test_name)
        return test.is_flaky if test else False

    def stats(self) -> Dict[str, Any]:
        all_tests = list(self._tests.values())
        return {
            "total_tracked": len(all_tests),
            "flaky": len(self.get_flaky()),
            "stable": len(self.get_stable()),
        }
