"""Week 73 — Failure metrics for local coding agent error taxonomy.

Tracks rates, distributions, and trends of failure categories.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .taxonomy import LocalCodingFailureRecord


@dataclass
class FailureMetrics:
    total_runs: int = 0
    total_failures: int = 0
    failure_rate: float = 0.0
    by_category_rate: Dict[str, float] = field(default_factory=dict)
    by_severity_rate: Dict[str, float] = field(default_factory=dict)
    top_failures: List[Dict] = field(default_factory=list)
    mitigation_success_rate: float = 0.0
    trend_direction: str = "stable"
    window_label: str = ""

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_failures": self.total_failures,
            "failure_rate": round(self.failure_rate, 4),
            "by_category_rate": {k: round(v, 4) for k, v in self.by_category_rate.items()},
            "by_severity_rate": {k: round(v, 4) for k, v in self.by_severity_rate.items()},
            "top_failures": self.top_failures[:5],
            "mitigation_success_rate": round(self.mitigation_success_rate, 4),
            "trend_direction": self.trend_direction,
            "window_label": self.window_label,
        }


def compute_failure_metrics(
    records: List[LocalCodingFailureRecord],
    total_runs: int = 0,
    window_label: str = "latest",
) -> FailureMetrics:
    """Compute metrics from a list of failure records."""
    total = len(records)
    runs = total_runs if total_runs > 0 else total

    by_category: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    mitigated = 0

    for r in records:
        cat = r.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
        sev = r.severity
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if r.mitigated_by:
            mitigated += 1

    top_failures = sorted(
        [{"category": cat, "count": cnt, "rate": round(cnt / runs, 4)}
         for cat, cnt in by_category.items()],
        key=lambda x: -x["count"],
    )

    return FailureMetrics(
        total_runs=runs,
        total_failures=total,
        failure_rate=total / runs if runs > 0 else 0.0,
        by_category_rate={k: v / runs for k, v in by_category.items()},
        by_severity_rate={k: v / runs for k, v in by_severity.items()},
        top_failures=top_failures,
        mitigation_success_rate=mitigated / total if total > 0 else 0.0,
        window_label=window_label,
    )
