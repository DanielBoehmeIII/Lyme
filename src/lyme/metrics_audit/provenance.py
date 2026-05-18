from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import time
import json
from pathlib import Path


class VerdictStatus(Enum):
    REAL = "real"
    SIMULATED = "simulated"
    UNVERIFIED = "unverified"
    STALE = "stale"
    FAKE = "fake"


class MetricSource(Enum):
    COMMAND_EXECUTION = "command_execution"
    TEST_RESULT = "test_result"
    GIT_DIFF = "git_diff"
    HUMAN_VERIFIED = "human_verified"
    CI_PIPELINE = "ci_pipeline"
    SIMULATED = "simulated"
    HARDCODED = "hardcoded"
    UNKNOWN = "unknown"


@dataclass
class ProvenanceEntry:
    metric_name: str
    value: float
    unit: str
    source: MetricSource
    verdict: VerdictStatus
    timestamp: float
    command_used: Optional[str] = None
    evidence_file: Optional[str] = None
    human_verified: bool = False
    reproduces: Optional[bool] = None
    staleness_days: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "source": self.source.value,
            "verdict": self.verdict.value,
            "command_used": self.command_used,
            "evidence_file": self.evidence_file,
            "human_verified": self.human_verified,
            "reproduces": self.reproduces,
            "staleness_days": self.staleness_days,
            "notes": self.notes,
        }


class MetricProvenanceTracker:
    def __init__(self):
        self.entries: List[ProvenanceEntry] = []

    def record(
        self, name: str, value: float, unit: str = "",
        source: MetricSource = MetricSource.UNKNOWN,
        verdict: VerdictStatus = VerdictStatus.UNVERIFIED,
        command: Optional[str] = None,
        evidence: Optional[str] = None,
        human_verified: bool = False,
        notes: str = "",
    ):
        self.entries.append(ProvenanceEntry(
            metric_name=name, value=value, unit=unit,
            source=source, verdict=verdict,
            timestamp=time.time(),
            command_used=command, evidence_file=evidence,
            human_verified=human_verified, notes=notes,
        ))

    def audit(self) -> Dict[str, List[ProvenanceEntry]]:
        real = [e for e in self.entries if e.verdict == VerdictStatus.REAL]
        fake = [e for e in self.entries if e.verdict == VerdictStatus.FAKE]
        simulated = [e for e in self.entries if e.verdict == VerdictStatus.SIMULATED]
        unverified = [e for e in self.entries if e.verdict == VerdictStatus.UNVERIFIED]
        stale = [e for e in self.entries if e.verdict == VerdictStatus.STALE]
        return {
            "real": real,
            "fake": fake,
            "simulated": simulated,
            "unverified": unverified,
            "stale": stale,
        }

    def trust_ratio(self) -> float:
        if not self.entries:
            return 0.0
        real = sum(1 for e in self.entries if e.verdict == VerdictStatus.REAL)
        fake = sum(1 for e in self.entries if e.verdict in (VerdictStatus.FAKE, VerdictStatus.SIMULATED))
        total = len(self.entries)
        return round((total - fake) / total, 3)

    def print_audit(self):
        audit = self.audit()
        print(f"{'='*60}")
        print(f"  METRIC PROVENANCE AUDIT")
        print(f"{'='*60}")
        print(f"  Total metrics: {len(self.entries)}")
        print(f"  {'Real':>12s}: {len(audit['real'])}")
        print(f"  {'Simulated':>12s}: {len(audit['simulated'])}")
        print(f"  {'Fake':>12s}: {len(audit['fake'])}")
        print(f"  {'Unverified':>12s}: {len(audit['unverified'])}")
        print(f"  {'Stale':>12s}: {len(audit['stale'])}")
        print(f"  Trust ratio: {self.trust_ratio():.0%}")
        if audit['fake']:
            print(f"\n  FAKE METRICS DETECTED:")
            for e in audit['fake']:
                print(f"    ✗ {e.metric_name} = {e.value} {e.unit} — {e.notes}")
        if audit['simulated']:
            print(f"\n  SIMULATED METRICS:")
            for e in audit['simulated']:
                print(f"    ~ {e.metric_name} = {e.value} {e.unit} — {e.notes}")
        print(f"{'='*60}")

    def export_json(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "trust_ratio": self.trust_ratio(),
            "total_entries": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }
        path.write_text(json.dumps(data, indent=2))


provenance_tracker = MetricProvenanceTracker()
