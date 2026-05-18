"""IntelligenceEngine — unified background analysis engine.

Runs all passive intelligence detectors on a schedule and surfaces
actionable warnings. Designed to feel like a senior engineer quietly
watching the repo.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .drift import ArchitectureDriftDetector, DriftReport
from .flaky import FlakyTestDetector, FlakyReport
from .suspicious import SuspiciousCommitDetector, SuspiciousReport
from .debt import TechnicalDebtAnalyzer, DebtReport


@dataclass
class IntelligenceReport:
    timestamp: float = field(default_factory=time.time)
    drift: Optional[DriftReport] = None
    flaky: Optional[FlakyReport] = None
    suspicious: Optional[SuspiciousReport] = None
    debt: Optional[DebtReport] = None
    summary: str = ""
    warning_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "drift": self.drift.to_dict() if self.drift else None,
            "flaky": self.flaky.to_dict() if self.flaky else None,
            "suspicious": self.suspicious.to_dict() if self.suspicious else None,
            "debt": self.debt.to_dict() if self.debt else None,
            "summary": self.summary,
            "warning_count": self.warning_count,
        }

    def to_markdown(self) -> str:
        parts = [f"## Intelligence Report\n"]
        if self.drift and self.drift.total_drift > 0:
            parts.append(f"- Architecture drift: {self.drift.critical_count} critical, {self.drift.warning_count} warning")
        if self.flaky and self.flaky.flaky_count > 0:
            parts.append(f"- Flaky tests: {self.flaky.flaky_count}")
        if self.suspicious and self.suspicious.suspicious_count > 0:
            parts.append(f"- Suspicious commits: {self.suspicious.suspicious_count}")
        if self.debt and self.debt.total_debt > 0:
            parts.append(f"- Technical debt: {self.debt.critical_count} critical, {self.debt.warning_count} warning")
        if len(parts) == 1:
            parts.append("All clear — no issues detected.")
        parts.append("")
        parts.append(f"### Warnings ({self.warning_count})")
        parts.append(self.summary)
        return "\n".join(parts)


class IntelligenceEngine:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "intel" / "reports"
        self._db_path.mkdir(parents=True, exist_ok=True)
        self.drift = ArchitectureDriftDetector(str(self._repo))
        self.flaky = FlakyTestDetector(str(self._repo))
        self.suspicious = SuspiciousCommitDetector(str(self._repo))
        self.debt = TechnicalDebtAnalyzer(str(self._repo))

    def run_all(self) -> IntelligenceReport:
        report = IntelligenceReport()
        warnings = []

        try:
            report.drift = self.drift.detect()
            if report.drift.critical_count > 0:
                warnings.append(f"Architecture drift: {report.drift.critical_count} critical violations")
            if report.drift.warning_count > 0:
                warnings.append(f"Architecture drift: {report.drift.warning_count} warnings")
        except Exception:
            pass

        try:
            report.flaky = self.flaky.analyze_existing()
            if report.flaky.flaky_count > 0:
                warnings.append(f"Flaky tests: {report.flaky.flaky_count} tests may be unreliable")
        except Exception:
            pass

        try:
            report.suspicious = self.suspicious.analyze(since_commits=30)
            if report.suspicious.suspicious_count > 0:
                report.suspicious.blocked > 0,
                type_count = (
                    f"{report.suspicious.blocked} blocked patterns, " if report.suspicious.blocked else ""
                )
                warnings.append(f"Suspicious commits: {report.suspicious.suspicious_count} findings ({type_count}{report.suspicious.large} large, {report.suspicious.untested} untested)")
        except Exception:
            pass

        try:
            report.debt = self.debt.analyze()
            if report.debt.critical_count > 0:
                warnings.append(f"Technical debt: {report.debt.critical_count} critical items")
            if report.debt.warning_count > 0:
                warnings.append(f"Technical debt: {report.debt.warning_count} warnings")
        except Exception:
            pass

        report.warning_count = len(warnings)
        report.summary = "\n".join(f"- {w}" for w in warnings) if warnings else "All clear."
        self._save_report(report)
        return report

    def run_fast(self) -> IntelligenceReport:
        report = IntelligenceReport()
        warnings = []

        try:
            report.drift = self.drift.detect()
            if report.drift.critical_count > 0:
                warnings.append(f"Architecture drift: {report.drift.critical_count} critical")
        except Exception:
            pass

        try:
            report.suspicious = self.suspicious.analyze(since_commits=10)
            if report.suspicious.suspicious_count > 0:
                warnings.append(f"Suspicious commits: {report.suspicious.suspicious_count}")
        except Exception:
            pass

        report.warning_count = len(warnings)
        report.summary = "\n".join(f"- {w}" for w in warnings) if warnings else "All clear."
        return report

    def latest_report(self) -> Optional[IntelligenceReport]:
        reports = sorted(self._db_path.glob("report_*.json"), reverse=True)
        if not reports:
            return None
        try:
            data = json.loads(reports[0].read_text())
            r = IntelligenceReport(timestamp=data.get("timestamp", 0))
            r.summary = data.get("summary", "")
            r.warning_count = data.get("warning_count", 0)
            return r
        except Exception:
            return None

    def _save_report(self, report: IntelligenceReport) -> None:
        path = self._db_path / f"report_{int(time.time())}.json"
        path.write_text(json.dumps(report.to_dict(), indent=2))

    def print_warnings(self) -> None:
        report = self.latest_report()
        if not report or report.warning_count == 0:
            return
        print(f"\n  ⚠ Passive intelligence ({report.warning_count} warnings):")
        for line in report.summary.split("\n"):
            if line.strip():
                print(f"    {line}")
        print(f"    Run `lyme intel` for full report.")
