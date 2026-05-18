"""RegressionGate — threshold gates that arena runs must pass.

Each gate defines a minimum acceptable score in a dimension.
A run that fails a gate triggers a regression alert.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegressionGate:
    name: str
    dimension: str
    min_score: float
    description: str
    critical: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dimension": self.dimension,
            "min_score": self.min_score,
            "description": self.description,
            "critical": self.critical,
        }


DEFAULT_GATES = [
    RegressionGate("correctness_min", "correctness", 0.5,
                   "Correctness score must be >= 0.5", critical=True),
    RegressionGate("test_pass_min", "test_pass_rate", 0.5,
                   "Test pass rate must be >= 0.5", critical=True),
    RegressionGate("autonomy_min", "autonomy", 0.3,
                   "Autonomy score must be >= 0.3"),
    RegressionGate("time_max", "time_efficiency", 0.2,
                   "Time efficiency must be >= 0.2"),
    RegressionGate("cost_max", "cost_efficiency", 0.1,
                   "Cost efficiency must be >= 0.1"),
]


class RegressionChecker:
    """Check arena scores against regression gates."""

    def __init__(self, gates: Optional[list[RegressionGate]] = None):
        self.gates = gates or DEFAULT_GATES

    def check(self, scores: dict) -> dict:
        tool_results: dict[str, list[dict]] = {}
        for tool_key, score_data in scores.items():
            dims = score_data.get("dimensions", {})
            tool_results[tool_key] = []
            for gate in self.gates:
                actual = dims.get(gate.dimension, 0.0)
                passed = actual >= gate.min_score
                tool_results[tool_key].append({
                    "gate": gate.name,
                    "dimension": gate.dimension,
                    "min_score": gate.min_score,
                    "actual": actual,
                    "passed": passed,
                    "critical": gate.critical,
                    "description": gate.description,
                })

        overall = self._compute_overall(tool_results)
        return {
            "tool_results": tool_results,
            "overall": overall,
            "gates": [g.to_dict() for g in self.gates],
        }

    def _compute_overall(self, tool_results: dict) -> dict:
        all_passed = True
        any_critical_failed = False
        critical_failures = []
        total_checks = 0
        passed_checks = 0

        for tool, results in tool_results.items():
            for r in results:
                total_checks += 1
                if r["passed"]:
                    passed_checks += 1
                else:
                    all_passed = False
                    if r["critical"]:
                        any_critical_failed = True
                        critical_failures.append(f"{tool}: {r['gate']} ({r['dimension']})")

        return {
            "all_passed": all_passed,
            "any_critical_failed": any_critical_failed,
            "critical_failures": critical_failures,
            "passed_fraction": round(passed_checks / max(total_checks, 1), 4),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
        }

    def regression_report(self, check_result: dict) -> str:
        lines = []
        overall = check_result["overall"]

        lines.append("=" * 60)
        lines.append("REGRESSION GATE REPORT")
        lines.append("=" * 60)

        if overall["all_passed"]:
            lines.append("\n  ✓ ALL GATES PASSED")
        else:
            lines.append(f"\n  ✗ {overall['passed_checks']}/{overall['total_checks']} GATES PASSED")
            if overall["any_critical_failed"]:
                lines.append("\n  ⚠ CRITICAL FAILURES:")
                for cf in overall["critical_failures"]:
                    lines.append(f"    ✗ {cf}")

        for tool, results in check_result["tool_results"].items():
            lines.append(f"\n── {tool} ──")
            for r in results:
                icon = "✓" if r["passed"] else "✗"
                lines.append(f"  {icon} {r['gate']}: {r['actual']:.3f} >= {r['min_score']} "
                             f"({'critical' if r['critical'] else 'warning'})")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
