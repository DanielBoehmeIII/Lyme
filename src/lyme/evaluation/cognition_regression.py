from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import time
import uuid


class CognitionDimension(str, Enum):
    PLANNING = "planning"
    EVIDENCE_GROUNDING = "evidence_grounding"
    TOOL_USE = "tool_use"
    MEMORY_RETRIEVAL = "memory_retrieval"
    VERIFICATION = "verification"
    SAFE_EDITING = "safe_editing"
    UNCERTAINTY_COMMUNICATION = "uncertainty_communication"
    CROSS_REPO_TRANSFER = "cross_repo_transfer"


@dataclass
class RegressionAlert:
    dimension: CognitionDimension
    baseline_score: float
    current_score: float
    delta: float
    severity: str
    timestamp: float
    suspected_cause: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "baseline_score": self.baseline_score,
            "current_score": self.current_score,
            "delta": self.delta,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "suspected_cause": self.suspected_cause,
            "recommendation": self.recommendation,
        }

    def to_markdown(self) -> str:
        icons = {"critical": "🔴", "major": "🟠", "minor": "🟡", "none": "🟢"}
        icon = icons.get(self.severity, "⚪")
        return (
            f"{icon} **{self.dimension.value}**: {self.baseline_score:.3f} → {self.current_score:.3f} "
            f"({self.delta:+.3f}) — {self.severity.upper()}\n"
            f"   Cause: {self.suspected_cause or 'Unknown'}\n"
            f"   → {self.recommendation}"
        )


@dataclass
class RegressionRun:
    id: str
    timestamp: float
    dimension: CognitionDimension
    score: float
    baseline: float
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "dimension": self.dimension.value,
            "score": self.score,
            "baseline": self.baseline,
            "metadata": self.metadata,
        }


@dataclass
class RegressionResult:
    runs: List[RegressionRun] = field(default_factory=list)
    alerts: List[RegressionAlert] = field(default_factory=list)
    overall_status: str = "passed"
    dimension_summary: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "runs": [r.to_dict() for r in self.runs],
            "alerts": [a.to_dict() for a in self.alerts],
            "overall_status": self.overall_status,
            "dimension_summary": self.dimension_summary,
        }

    def to_markdown(self) -> str:
        icons = {"passed": "✅", "regression": "🔴", "warning": "🟡", "error": "❌"}
        lines = []
        lines.append("# Cognition Regression Detection Report")
        lines.append(f"")
        lines.append(f"**Status**: {icons.get(self.overall_status, '❓')} {self.overall_status.upper()}")
        lines.append(f"")
        lines.append(f"## Dimension Status")
        for dim, status in self.dimension_summary.items():
            s_icon = {"passed": "✅", "regression": "🔴", "warning": "🟡"}.get(status, "⚪")
            lines.append(f"- {s_icon} **{dim}**: {status}")
        lines.append(f"")
        if self.alerts:
            lines.append(f"## Regressions Detected ({len(self.alerts)})")
            for alert in self.alerts:
                lines.append("")
                lines.append(alert.to_markdown())
        return "\n".join(lines)

    def render_cli(self) -> str:
        icons = {"passed": "✅", "regression": "🔴", "warning": "🟡", "error": "❌"}
        lines = []
        lines.append("=" * 70)
        lines.append("  COGNITION REGRESSION DETECTION")
        lines.append("=" * 70)
        lines.append(f"  Status: {icons.get(self.overall_status, '?')} {self.overall_status.upper()}")
        lines.append("-" * 70)
        lines.append("  Dimensions:")
        for dim, status in self.dimension_summary.items():
            s_icon = {"passed": "✅", "regression": "🔴", "warning": "🟡"}.get(status, "⚪")
            lines.append(f"    {s_icon} {dim}: {status}")
        if self.alerts:
            lines.append("")
            lines.append(f"  Alerts ({len(self.alerts)}):")
            for a in self.alerts:
                lines.append(f"    🔴 {a.dimension.value}: {a.baseline_score:.3f} -> {a.current_score:.3f} ({a.delta:+.3f})")
                lines.append(f"       {a.recommendation}")
        lines.append("=" * 70)
        return "\n".join(lines)


class CognitionRegressionDetector:
    def __init__(self):
        self._baselines: Dict[CognitionDimension, float] = {}
        self._history: Dict[CognitionDimension, List[float]] = {
            d: [] for d in CognitionDimension
        }
        self._alerts: List[RegressionAlert] = []

    def set_baseline(self, dimension: CognitionDimension, score: float) -> None:
        self._baselines[dimension] = score

    def set_all_baselines(self, scores: Dict[CognitionDimension, float]) -> None:
        self._baselines.update(scores)

    def record_run(self, dimension: CognitionDimension, score: float,
                   metadata: Optional[Dict] = None) -> RegressionRun:
        run = RegressionRun(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            dimension=dimension,
            score=score,
            baseline=self._baselines.get(dimension, 0.5),
            metadata=metadata or {},
        )
        self._history[dimension].append(score)
        self._check_regression(dimension, score)
        return run

    def _check_regression(self, dimension: CognitionDimension, score: float) -> None:
        baseline = self._baselines.get(dimension)
        if baseline is None:
            return

        delta = score - baseline
        threshold = 0.1

        if delta < -threshold:
            if abs(delta) > 0.3:
                severity = "critical"
                rec = f"Critical regression in {dimension.value}. Roll back recent changes to this capability."
            elif abs(delta) > 0.2:
                severity = "major"
                rec = f"Major regression in {dimension.value}. Investigate and fix."
            else:
                severity = "minor"
                rec = f"Minor regression in {dimension.value}. Monitor closely."

            alert = RegressionAlert(
                dimension=dimension,
                baseline_score=baseline,
                current_score=score,
                delta=delta,
                severity=severity,
                timestamp=time.time(),
                suspected_cause=f"Score dropped from {baseline:.3f} to {score:.3f}",
                recommendation=rec,
            )
            self._alerts.append(alert)

    def evaluate(self, scores: Dict[CognitionDimension, float]) -> RegressionResult:
        runs = []
        for dim, score in scores.items():
            run = self.record_run(dim, score)
            runs.append(run)

        dimension_summary: Dict[str, str] = {}
        for dim in CognitionDimension:
            baseline = self._baselines.get(dim)
            history = self._history.get(dim, [])
            if not history:
                dimension_summary[dim.value] = "no_data"
            elif baseline is None:
                dimension_summary[dim.value] = "no_baseline"
            else:
                current = history[-1]
                if current < baseline - 0.15:
                    dimension_summary[dim.value] = "regression"
                elif current < baseline - 0.05:
                    dimension_summary[dim.value] = "warning"
                else:
                    dimension_summary[dim.value] = "passed"

        num_regressions = sum(1 for s in dimension_summary.values() if s == "regression")
        num_warnings = sum(1 for s in dimension_summary.values() if s == "warning")
        critical_alerts = sum(1 for a in self._alerts if a.severity == "critical")

        if critical_alerts > 0 or num_regressions >= 3:
            overall = "regression"
        elif num_regressions > 0 or num_warnings >= 3:
            overall = "warning"
        else:
            overall = "passed"

        return RegressionResult(
            runs=runs,
            alerts=self._alerts[-10:],
            overall_status=overall,
            dimension_summary=dimension_summary,
        )

    def evaluate_all_dims(self, score_map: Dict[str, float]) -> RegressionResult:
        mapped = {}
        for dim in CognitionDimension:
            if dim.value in score_map:
                mapped[dim] = score_map[dim.value]
            else:
                mapped[dim] = 0.5
        return self.evaluate(mapped)

    def get_history(self) -> Dict[str, List[float]]:
        return {k.value: v for k, v in self._history.items()}

    def get_alerts(self) -> List[RegressionAlert]:
        return self._alerts
