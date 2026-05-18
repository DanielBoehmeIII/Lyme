"""HardeningSuite — runs hardening checks to ensure system reliability."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CheckResult:
    name: str = ""
    passed: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message[:100],
        }


@dataclass
class HardeningCheck:
    name: str
    description: str
    fn: Callable[[], bool]
    severity: str = "medium"


class HardeningSuite:
    def __init__(self):
        self._checks: List[HardeningCheck] = []

    def add_check(self, check: HardeningCheck) -> None:
        self._checks.append(check)

    def run_all(self) -> List[CheckResult]:
        results: List[CheckResult] = []
        for check in self._checks:
            try:
                passed = check.fn()
                results.append(CheckResult(
                    name=check.name,
                    passed=passed,
                    message="Passed" if passed else "Failed",
                ))
            except Exception as e:
                results.append(CheckResult(
                    name=check.name,
                    passed=False,
                    message=str(e),
                ))
        return results

    def run_category(self, severity: str) -> List[CheckResult]:
        checks = [c for c in self._checks if c.severity == severity]
        results = []
        for check in checks:
            try:
                passed = check.fn()
                results.append(CheckResult(name=check.name, passed=passed))
            except Exception as e:
                results.append(CheckResult(name=check.name, passed=False, message=str(e)))
        return results

    def summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "pass_rate": sum(1 for r in results if r.passed) / max(len(results), 1),
        }
