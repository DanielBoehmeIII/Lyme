"""Demos — viral developer experience demos and showcases."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DemoStep:
    name: str = ""
    description: str = ""
    duration_s: float = 0.0
    status: str = "ready"

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "status": self.status}


DEMOS: Dict[str, List[DemoStep]] = {
    "autonomous_repair": [
        DemoStep("Bug detection", "Lyme scans the repo and finds a failing test", 1.0),
        DemoStep("Root cause analysis", "Lyme traces the failure to its source", 2.0),
        DemoStep("Fix generation", "Lyme generates and applies a patch", 3.0),
        DemoStep("Verification", "Lyme re-runs tests to confirm the fix", 1.5),
    ],
    "multi_file_refactor": [
        DemoStep("Architecture analysis", "Lyme builds the dependency graph", 2.0),
        DemoStep("Impact assessment", "Lyme identifies all affected files", 1.0),
        DemoStep("Safe refactor", "Lyme applies changes across 5 files", 4.0),
        DemoStep("Regression check", "Lyme runs the full test suite", 3.0),
    ],
    "issue_to_pr": [
        DemoStep("Issue parsing", "Lyme reads the GitHub issue", 0.5),
        DemoStep("Code understanding", "Lyme navigates to the relevant code", 1.0),
        DemoStep("Implementation", "Lyme writes the fix", 3.0),
        DemoStep("PR creation", "Lyme creates a PR with description and tests", 1.5),
    ],
}


def list_demos() -> List[str]:
    return list(DEMOS.keys())


def run_demo(name: str, ui=None) -> List[Dict[str, Any]]:
    steps = DEMOS.get(name)
    if not steps:
        return []
    results = []
    for step in steps:
        start = time.time()
        if ui:
            ui.info(f"  {step.name}...")
        time.sleep(min(step.duration_s * 0.1, 0.5))  # Simulate
        results.append({"step": step.name, "duration_s": time.time() - start, "status": "passed"})
        if ui:
            ui.ok(f"  {step.name} ({time.time() - start:.1f}s)")
    return results
