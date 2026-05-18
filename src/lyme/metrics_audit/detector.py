from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re
import json
import time


FAKE_METRIC_PATTERNS = [
    r"100\.0%\s+pass",
    r"pass_rate.*100",
    r"perfect\s+score",
    r"100%\s+accuracy",
    r"zero\s+errors",
    r"no\s+failures",
    r"all\s+tests\s+pass",
    r"avg_score.*[0-9]\.[9][0-9]",
    r"score.*1\.0",
    r"0\.9[5-9]\s+confidence",
]

SIMULATION_SIGNALS = [
    "simulated",
    "mock",
    "fake",
    "placeholder",
    "TODO",
    "estimated",
    "assumed",
    "hypothetical",
    "projected",
    "expected",
]

NO_EVIDENCE_SIGNALS = [
    "no evidence",
    "no source",
    "generated",
    "synthetic",
]


@dataclass
class SuspiciousMetric:
    name: str
    value: float
    reason: str
    severity: str

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "reason": self.reason, "severity": self.severity}


@dataclass
class FakeMetricReport:
    total_metrics_audited: int
    suspicious_count: int
    fake_count: int
    simulated_count: int
    suspicious_metrics: List[SuspiciousMetric]
    fake_metrics: List[SuspiciousMetric]
    simulated_metrics: List[SuspiciousMetric]
    credibility_score: float
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "total_metrics_audited": self.total_metrics_audited,
            "suspicious_count": self.suspicious_count,
            "fake_count": self.fake_count,
            "simulated_count": self.simulated_count,
            "suspicious_metrics": [m.to_dict() for m in self.suspicious_metrics],
            "fake_metrics": [m.to_dict() for m in self.fake_metrics],
            "simulated_metrics": [m.to_dict() for m in self.simulated_metrics],
            "credibility_score": round(self.credibility_score, 3),
            "recommendations": self.recommendations,
        }


class FakeMetricDetector:
    def __init__(self):
        self.fake_patterns = [re.compile(p, re.IGNORECASE) for p in FAKE_METRIC_PATTERNS]
        self.simulation_signals = SIMULATION_SIGNALS
        self.no_evidence_signals = NO_EVIDENCE_SIGNALS

    def scan_text(self, text: str, source_name: str = "unknown") -> List[SuspiciousMetric]:
        hits = []
        for pattern in self.fake_patterns:
            matches = pattern.findall(text)
            for m in matches:
                hits.append(SuspiciousMetric(
                    name=f"pattern match in {source_name}",
                    value=0.0,
                    reason=f"Fake metric pattern detected: '{m[:80]}'",
                    severity="high",
                ))
        for signal in self.simulation_signals:
            if signal.lower() in text.lower():
                hits.append(SuspiciousMetric(
                    name=f"simulation signal in {source_name}",
                    value=0.0,
                    reason=f"Contains simulation signal: '{signal}'",
                    severity="medium",
                ))
        return hits

    def scan_metrics_dict(self, metrics: Dict[str, Any], path: str = "root") -> List[SuspiciousMetric]:
        hits = []
        suspicious_thresholds = {
            "pass_rate": (0.99, 1.01, "Pass rate at 100% suggests no real testing"),
            "avg_score": (0.95, 1.01, "Avg score near perfect suggests cherry-picking"),
            "accuracy": (0.99, 1.01, "Perfect accuracy suggests no real test"),
            "confidence": (0.98, 1.01, "Perfect confidence suggests overconfidence"),
            "success_rate": (0.99, 1.01, "Perfect success rate is suspicious"),
        }
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                for sus_key, (low, high, reason) in suspicious_thresholds.items():
                    if sus_key in key.lower() and low <= value <= high:
                        hits.append(SuspiciousMetric(
                            name=f"{path}.{key}",
                            value=float(value),
                            reason=reason,
                            severity="high",
                        ))
            elif isinstance(value, dict):
                hits.extend(self.scan_metrics_dict(value, f"{path}.{key}"))
            elif isinstance(value, str):
                for pattern in self.fake_patterns:
                    if pattern.search(value):
                        hits.append(SuspiciousMetric(
                            name=f"{path}.{key}",
                            value=0.0,
                            reason=f"Fake metric pattern in string: '{value[:80]}'",
                            severity="high",
                        ))
        return hits

    def detect_fakes(self, metrics: Dict[str, Any], text_sources: Optional[List[str]] = None) -> FakeMetricReport:
        text_sources = text_sources or []
        all_suspicious = self.scan_metrics_dict(metrics)

        for src in text_sources:
            all_suspicious.extend(self.scan_text(src))

        total = len(metrics) + len(text_sources)
        fake = [m for m in all_suspicious if m.severity == "high"]
        simulated = [m for m in all_suspicious if m.severity == "medium"]
        suspicious = [m for m in all_suspicious if m.severity == "low"]

        credibility = 1.0 - (len(fake) * 0.15 + len(simulated) * 0.08) / max(total, 1)

        recs = []
        if fake:
            recs.append(f"Kill {len(fake)} fake/suspicious metrics — replace with real command execution")
        if simulated:
            recs.append(f"Tag {len(simulated)} simulated metrics as experimental")
        if credibility < 0.7:
            recs.append("Overall credibility low — audit all metric sources")
        recs.append("Add provenance metadata to every metric")
        recs.append("Pin commit hash for reproducibility")

        return FakeMetricReport(
            total_metrics_audited=max(total, 1),
            suspicious_count=len(suspicious),
            fake_count=len(fake),
            simulated_count=len(simulated),
            suspicious_metrics=suspicious,
            fake_metrics=fake,
            simulated_metrics=simulated,
            credibility_score=credibility,
            recommendations=recs,
        )

    def audit_benchmark_file(self, path: str) -> FakeMetricReport:
        with open(path) as f:
            data = json.load(f)
        return self.detect_fakes(data, text_sources=[path])

    def print_report(self, report: FakeMetricReport):
        print(f"{'='*60}")
        print(f"  FAKE METRIC DETECTION REPORT")
        print(f"{'='*60}")
        print(f"  Metrics audited: {report.total_metrics_audited}")
        print(f"  Suspicious:      {report.suspicious_count}")
        print(f"  Fake:            {report.fake_count}")
        print(f"  Simulated:       {report.simulated_count}")
        print(f"  Credibility:     {report.credibility_score:.0%}")
        if report.fake_metrics:
            print(f"\n  ✗ FAKE METRICS:")
            for m in report.fake_metrics:
                print(f"    {m.name:40s} {m.reason}")
        if report.simulated_metrics:
            print(f"\n  ~ SIMULATED METRICS:")
            for m in report.simulated_metrics:
                print(f"    {m.name:40s} {m.reason}")
        print(f"\n  Recommendations:")
        for r in report.recommendations:
            print(f"    → {r}")
        print(f"{'='*60}")


fake_detector = FakeMetricDetector()
