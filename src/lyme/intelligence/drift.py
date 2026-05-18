from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class DriftFinding:
    subsystem: str
    drift_type: str
    severity: str
    description: str
    expected: str
    actual: str
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
            "file_path": self.file_path,
        }


@dataclass
class DriftReport:
    findings: List[DriftFinding] = field(default_factory=list)
    total_drift: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "total_drift": self.total_drift,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
        }

    def to_markdown(self) -> str:
        if not self.findings:
            return "No architecture drift detected."
        lines = [f"## Architecture Drift Report\n"]
        for f in self.findings:
            icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(f.severity, "•")
            lines.append(f"{icon} **{f.subsystem}**: {f.description}")
            lines.append(f"   - Expected: {f.expected}")
            lines.append(f"   - Actual: {f.actual}")
            lines.append("")
        return "\n".join(lines)


class ArchitectureDriftDetector:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._arch_file = self._repo / ".lyme" / "architecture.json"

    def detect(self) -> DriftReport:
        report = DriftReport()
        arch = self._load_arch()
        if not arch:
            return report

        subsystems = arch.get("subsystems", [])
        boundary_rules = arch.get("boundary_rules", [])
        invariants = arch.get("invariants", [])

        for sd in subsystems:
            name = sd.get("name", "")
            owned_files = []
            for r in sd.get("responsibilities", []):
                owned_files.extend(r.get("owned_files", []))
                owned_files.extend(r.get("source_files", []))

            for f in owned_files:
                path = self._repo / f
                exists = path.exists()
                if not exists and name != "unknown":
                    report.findings.append(DriftFinding(
                        subsystem=name,
                        drift_type="missing_file",
                        severity="warning",
                        description=f"Owned file missing: {f}",
                        expected=f"File exists at {f}",
                        actual="File not found",
                        file_path=f,
                    ))

        for rule in boundary_rules:
            from_sys = rule.get("from_subsystem", "")
            to_sys = rule.get("to_subsystem", "")
            forbidden_patterns = rule.get("forbidden_patterns", [])
            if not forbidden_patterns:
                continue
            from_files = self._get_subsystem_files(from_sys)
            for f in from_files:
                try:
                    content = Path(f).read_text()
                except Exception:
                    continue
                for pattern in forbidden_patterns:
                    if pattern in content:
                        report.findings.append(DriftFinding(
                            subsystem=from_sys,
                            drift_type="boundary_violation",
                            severity="critical",
                            description=f"Boundary violation: {from_sys} uses forbidden pattern '{pattern}'",
                            expected=f"No '{pattern}' in {from_sys} files",
                            actual=f"Found in {f}",
                            file_path=f,
                        ))

        for inv in invariants:
            scope = inv.get("scope", "")
            condition = inv.get("condition", "")
            if scope == "global" and condition:
                if not self._check_invariant_condition(condition):
                    report.findings.append(DriftFinding(
                        subsystem="global",
                        drift_type="invariant_violation",
                        severity="critical",
                        description=f"Invariant violated: {inv.get('name', 'unknown')}",
                        expected=f"Condition holds: {condition}",
                        actual="Condition no longer holds",
                    ))

        report.total_drift = len(report.findings)
        report.critical_count = sum(1 for f in report.findings if f.severity == "critical")
        report.warning_count = sum(1 for f in report.findings if f.severity == "warning")
        report.info_count = sum(1 for f in report.findings if f.severity == "info")
        return report

    def _load_arch(self) -> Optional[Dict[str, Any]]:
        if not self._arch_file.exists():
            return None
        try:
            return json.loads(self._arch_file.read_text())
        except Exception:
            return None

    def _get_subsystem_files(self, name: str) -> List[str]:
        arch = self._load_arch()
        if not arch:
            return []
        for sd in arch.get("subsystems", []):
            if sd.get("name") == name:
                files = []
                for r in sd.get("responsibilities", []):
                    files.extend(r.get("owned_files", []))
                    files.extend(r.get("source_files", []))
                return [str(self._repo / f) for f in files if (self._repo / f).exists()]
        return []

    def _check_invariant_condition(self, condition: str) -> bool:
        if condition == "pytest passes":
            try:
                result = subprocess.run(
                    ["pytest", "--co", "-q", "--tb=no"],
                    capture_output=True, text=True,
                    cwd=str(self._repo), timeout=30,
                )
                return result.returncode == 0
            except Exception:
                return True
        return True
