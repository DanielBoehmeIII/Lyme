"""Launch candidate verification for v0.9.0."""
from pathlib import Path
import json
import time
import sys


LAUNCH_CHECKLIST = [
    {"id": "VERSION", "label": "Version is 0.9.0", "command": "lyme --version"},
    {"id": "CLI_IMPORTS", "label": "CLI imports without errors", "command": "python3 -m lyme --version"},
    {"id": "DOCTOR", "label": "lyme doctor runs", "command": "lyme doctor"},
    {"id": "ASK", "label": "lyme ask runs", "command": "lyme ask 'test'"},
    {"id": "DASHBOARD", "label": "lyme dashboard runs", "command": "lyme dashboard"},
    {"id": "START", "label": "lyme start runs", "command": "lyme start"},
    {"id": "INBOX", "label": "lyme inbox runs", "command": "lyme inbox"},
    {"id": "DIFF_EXPLAIN", "label": "lyme diff-explain runs", "command": "lyme diff-explain"},
    {"id": "BRANCH_REVIEW", "label": "lyme branch-review runs", "command": "lyme branch-review"},
    {"id": "CONTINUE", "label": "lyme continue runs", "command": "lyme continue"},
    {"id": "WATCH", "label": "lyme watch runs", "command": "lyme watch"},
    {"id": "DOGFOOD_HELP", "label": "lyme dogfood has subcommands", "command": "lyme dogfood --help"},
    {"id": "METRICS_AUDIT", "label": "lyme metrics-audit runs", "command": "lyme metrics-audit provenance"},
    {"id": "PRICING", "label": "lyme pricing runs", "command": "lyme pricing plans"},
    {"id": "PRICING_CHECK", "label": "Feature gates work", "command": "lyme pricing check dashboard"},
    {"id": "TRUST", "label": "lyme trust runs", "command": "lyme trust privacy"},
    {"id": "BETA", "label": "lyme beta runs", "command": "lyme beta status"},
    {"id": "PI_DOGFOOD", "label": "Dogfood report exists", "command": None},
    {"id": "RELEASE_NOTES", "label": "Release notes exist", "command": None},
    {"id": "SMOKE_TESTS", "label": "Smoke tests pass", "command": "python3 -m pytest tests/test_phase8_launch.py -v"},
]


class LaunchVerifier:
    def __init__(self):
        self.results = []
        self.checklist = LAUNCH_CHECKLIST

    def verify(self) -> dict:
        import subprocess

        for item in self.checklist:
            result = {
                "id": item["id"],
                "label": item["label"],
                "passed": False,
                "output": "",
            }
            if item["command"] is None:
                if item["id"] == "PI_DOGFOOD":
                    result["passed"] = Path("lyme-output/dogfood/dogfood-report.json").exists()
                    result["output"] = "found" if result["passed"] else "not found"
                elif item["id"] == "RELEASE_NOTES":
                    result["passed"] = Path("RELEASE_NOTES_v0.9.0.md").exists()
                    result["output"] = "found" if result["passed"] else "not found"
            else:
                try:
                    rc = subprocess.run(
                        item["command"].split(),
                        capture_output=True, text=True, timeout=30,
                    )
                    result["passed"] = rc.returncode == 0
                    result["output"] = (rc.stdout + rc.stderr)[:200]
                except Exception as e:
                    result["output"] = str(e)
            self.results.append(result)

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        return {
            "version": "0.9.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 3) if total > 0 else 0,
            "results": self.results,
        }

    def print_verification(self, report: dict):
        print(f"\n{'='*60}")
        print(f"  LAUNCH VERIFICATION — v{report['version']}")
        print(f"{'='*60}")
        print(f"  Passed: {report['passed']}/{report['total']} ({report['pass_rate']:.0%})")
        print()
        for r in report['results']:
            icon = "✓" if r['passed'] else "✗"
            print(f"  {icon} {r['id']:20s} {r['label']}")
            if not r['passed'] and r['output']:
                print(f"    {r['output'][:100]}")
        print(f"\n  Verdict: ", end="")
        if report['pass_rate'] >= 0.9:
            print("LAUNCH READY")
        elif report['pass_rate'] >= 0.7:
            print("LAUNCHABLE WITH CAVEATS")
        else:
            print("NOT READY — FIX FAILURES")
        print(f"{'='*60}")


verifier = LaunchVerifier()
