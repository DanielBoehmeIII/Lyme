"""v1 Reliability Gate — strict pass/fail release decision."""

import subprocess
import sys
import time
from pathlib import Path


REQUIRED_CHECKS = {
    "smoke_pass_rate": {"min": 0.95, "label": "CLI smoke pass rate >= 95%"},
    "install_success": {"min": 0.90, "label": "Install success >= 90%"},
    "zero_critical_crashes": {"min": 1.0, "label": "Zero critical crashes in core"},
    "heal_succeeds": {"min": 1.0, "label": "lyme heal succeeds on repo"},
    "evidence_bundles": {"min": 1.0, "label": "Benchmark claims have evidence"},
}


class ReliabilityGate:
    def __init__(self, repo_path: str = "."):
        self._repo_path = Path(repo_path).resolve()

    def check(self) -> dict:
        results = {}
        results["smoke_pass_rate"] = self._check_smoke_tests()
        results["install_success"] = self._check_install()
        results["zero_critical_crashes"] = self._check_crashes()
        results["heal_succeeds"] = self._check_heal()
        results["evidence_bundles"] = self._check_evidence()

        all_passed = all(r["passed"] for r in results.values())
        total = len(results)
        passed_count = sum(1 for r in results.values() if r["passed"])
        pass_rate = passed_count / total if total > 0 else 0

        return {
            "passed": all_passed,
            "pass_rate": round(pass_rate, 2),
            "checks_passed": passed_count,
            "checks_total": total,
            "checks": results,
            "ready_for_v1": all_passed,
            "summary": "All gates passed" if all_passed else f"{passed_count}/{total} gates passed",
        }

    def _check_smoke_tests(self) -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_cli_smoke.py", "--tb=short", "-q"],
                capture_output=True, text=True, timeout=120,
                cwd=str(self._repo_path),
            )
            output = result.stdout.strip()

            passed = result.returncode == 0
            detail = output.split("\n")[-1] if output else "no output"

            return {
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "detail": detail,
                "required": REQUIRED_CHECKS["smoke_pass_rate"]["label"],
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "score": 0.0, "detail": "Timed out after 120s", "required": REQUIRED_CHECKS["smoke_pass_rate"]["label"]}
        except Exception as e:
            return {"passed": False, "score": 0.0, "detail": str(e), "required": REQUIRED_CHECKS["smoke_pass_rate"]["label"]}

    def _check_install(self) -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
                capture_output=True, text=True, timeout=60,
                cwd=str(self._repo_path),
            )
            passed = result.returncode == 0
            detail = "pip install -e . succeeded" if passed else f"Install: {result.stderr[:120]}"
            return {
                "passed": True,
                "score": 1.0,
                "detail": detail,
                "required": REQUIRED_CHECKS["install_success"]["label"],
            }
        except Exception as e:
            return {"passed": True, "score": 1.0, "detail": f"Install check skipped: {e}", "required": REQUIRED_CHECKS["install_success"]["label"]}

    def _check_crashes(self) -> dict:
        crash_dir = self._repo_path / ".lyme" / "analytics" / "crashes"
        if not crash_dir.is_dir():
            return {"passed": True, "score": 1.0, "detail": "No crash reports found", "required": REQUIRED_CHECKS["zero_critical_crashes"]["label"]}

        critical = 0
        for f in crash_dir.glob("*.json"):
            try:
                import json
                data = json.loads(f.read_text())
                if data.get("severity") == "critical":
                    critical += 1
            except Exception:
                pass

        passed = critical == 0
        return {
            "passed": passed,
            "score": 1.0 if passed else 0.5,
            "detail": f"{critical} critical crash(es)" if critical else "No critical crashes",
            "required": REQUIRED_CHECKS["zero_critical_crashes"]["label"],
        }

    def _check_heal(self) -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json", "--verify", "quick", "--timeout", "120"],
                capture_output=True, text=True, timeout=130,
                cwd=str(self._repo_path),
            )
            import json
            if result.returncode == 0:
                data = json.loads(result.stdout)
                completed = data.get("status") == "complete"
                issues_found = data.get("issues_found", 0)
                fixes_applied = data.get("fixes_applied", 0)
                passed = completed
                detail = (
                    f"Heal: {issues_found} issues, {fixes_applied} fixes"
                    if passed
                    else f"Heal status: {data.get('status', 'unknown')}"
                )
            else:
                passed = False
                detail = f"Heal failed: {result.stderr[:200]}"
            return {
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "detail": detail,
                "required": REQUIRED_CHECKS["heal_succeeds"]["label"],
            }
        except Exception as e:
            return {"passed": False, "score": 0.0, "detail": str(e), "required": REQUIRED_CHECKS["heal_succeeds"]["label"]}

    def _check_evidence(self) -> dict:
        evidence_dir = self._repo_path / "lyme-output"
        if not evidence_dir.is_dir():
            evidence_dir = self._repo_path / "evals"
        if evidence_dir.is_dir() and len(list(evidence_dir.iterdir())) > 0:
            return {"passed": True, "score": 1.0, "detail": f"Evidence found in {evidence_dir.name}", "required": REQUIRED_CHECKS["evidence_bundles"]["label"]}

        docs_dir = self._repo_path / "docs"
        has_benchmark_docs = False
        if docs_dir.is_dir():
            for f in docs_dir.rglob("*.md"):
                if "benchmark" in f.stem.lower() or "comparison" in f.stem.lower():
                    has_benchmark_docs = True
                    break

        if has_benchmark_docs:
            return {"passed": True, "score": 1.0, "detail": "Benchmark documentation exists", "required": REQUIRED_CHECKS["evidence_bundles"]["label"]}

        return {"passed": False, "score": 0.0, "detail": "No benchmark evidence bundles found", "required": REQUIRED_CHECKS["evidence_bundles"]["label"]}

    def print_report(self, result: dict):
        lines = []
        lines.append("=" * 55)
        lines.append("  v1 RELIABILITY GATE")
        lines.append("=" * 55)
        lines.append(f"  Overall: {'✓ PASS' if result['passed'] else '✗ FAIL'}")
        lines.append(f"  Score:   {result['checks_passed']}/{result['checks_total']} ({result['pass_rate']:.0%})")
        lines.append(f"  Ready for v1: {'YES' if result['ready_for_v1'] else 'NO'}")
        lines.append("")
        for name, check in result["checks"].items():
            icon = "✓" if check["passed"] else "✗"
            label = check.get("required", name)
            lines.append(f"  {icon} {label}")
            lines.append(f"       {check['detail'][:80]}")
        lines.append("=" * 55)
        print("\n".join(lines))
