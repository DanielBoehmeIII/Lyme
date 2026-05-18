"""ReliabilityDashboard — aggregates trust metrics from all systems into one view."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TrustMetric(str, Enum):
    REPRODUCIBILITY = "reproducibility"
    EXPLAINABILITY = "explainability"
    ROLLBACK_SAFETY = "rollback_safety"
    ARCHITECTURAL_REASONING = "architectural_reasoning"
    VERIFICATION_COVERAGE = "verification_coverage"
    EXECUTION_SUPERVISION = "execution_supervision"
    GOAL_COMPLETION = "goal_completion"
    WORKFLOW_INTELLIGENCE = "workflow_intelligence"


class HealthLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class MetricScore:
    metric: TrustMetric
    score: float
    status: str
    details: str

    def to_dict(self) -> Dict:
        return {
            "metric": self.metric.value,
            "score": round(self.score, 3),
            "status": self.status,
            "details": self.details[:60],
        }


@dataclass
class DashboardReport:
    overall_health: HealthLevel
    overall_score: float
    metrics: List[MetricScore]
    total_systems_reporting: int
    critical_issues: List[str]
    recommendations: List[str]

    def render_cli(self) -> str:
        icons = {HealthLevel.EXCELLENT: "🟢", HealthLevel.GOOD: "💚",
                 HealthLevel.FAIR: "🟡", HealthLevel.POOR: "🟠",
                 HealthLevel.CRITICAL: "🔴"}
        lines = []
        lines.append("=" * 70)
        lines.append("  RELIABILITY DASHBOARD")
        lines.append("=" * 70)
        lines.append(f"  Overall Health: {icons.get(self.overall_health, '•')} "
                     f"{self.overall_health.value.upper()} ({self.overall_score:.1%})")
        lines.append(f"  Systems Reporting: {self.total_systems_reporting}")
        lines.append("")
        for m in self.metrics:
            bar = "█" * int(m.score * 20)
            dot = "🟢" if m.score >= 0.7 else ("🟡" if m.score >= 0.4 else "🔴")
            lines.append(f"  {dot} {m.metric.value}: {m.score:.0%} {bar}")
            lines.append(f"     {m.details[:60]}")
        if self.critical_issues:
            lines.append("-" * 70)
            lines.append("  CRITICAL ISSUES:")
            for issue in self.critical_issues:
                lines.append(f"    🔴 {issue}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ReliabilityDashboard:
    def __init__(self):
        self._sources: Dict[TrustMetric, float] = {}

    def report_metric(self, metric: TrustMetric, score: float, details: str = "") -> None:
        self._sources[metric] = score

    def load_from_modules(self, modules: Dict[TrustMetric, Any]) -> None:
        for metric, module in modules.items():
            try:
                if hasattr(module, "report") and callable(module.report):
                    report = module.report()
                    score = self._extract_score(report)
                    self._sources[metric] = score
            except Exception:
                self._sources[metric] = 0.0

    def _extract_score(self, report: Any) -> float:
        if hasattr(report, "overall_score") and isinstance(report.overall_score, (int, float)):
            return report.overall_score
        if hasattr(report, "overall_success_rate"):
            return report.overall_success_rate
        if hasattr(report, "determinism_rate"):
            return report.determinism_rate
        if hasattr(report, "total_rollbacks"):
            return min(1.0, report.verified_count / max(report.total_rollbacks, 1)) if hasattr(report, "verified_count") else 0.5
        return 0.5

    def generate(self) -> DashboardReport:
        if not self._sources:
            return DashboardReport(
                overall_health=HealthLevel.CRITICAL,
                overall_score=0.0,
                metrics=[],
                total_systems_reporting=0,
                critical_issues=["No systems reporting — trust metrics unavailable"],
                recommendations=["Connect trust modules to the dashboard"],
            )

        metrics: List[MetricScore] = []
        for metric in TrustMetric:
            score = self._sources.get(metric, 0.0)
            if score >= 0.8:
                status = "excellent"
            elif score >= 0.6:
                status = "good"
            elif score >= 0.4:
                status = "fair"
            elif score >= 0.2:
                status = "poor"
            else:
                status = "critical"

            details_map = {
                TrustMetric.REPRODUCIBILITY: f"{score:.0%} executions deterministic",
                TrustMetric.EXPLAINABILITY: f"Decisions explained with reasoning chains",
                TrustMetric.ROLLBACK_SAFETY: f"{score:.0%} recovery procedures verified",
                TrustMetric.ARCHITECTURAL_REASONING: f"{score:.0%} decisions validated",
                TrustMetric.VERIFICATION_COVERAGE: f"{score:.0%} verification coverage",
                TrustMetric.EXECUTION_SUPERVISION: f"{score:.0%} task supervision rate",
                TrustMetric.GOAL_COMPLETION: f"{score:.0%} goal completion rate",
                TrustMetric.WORKFLOW_INTELLIGENCE: f"{score:.0%} workflow patterns learned",
            }
            details = details_map.get(metric, f"Score: {score:.0%}")

            metrics.append(MetricScore(
                metric=metric,
                score=score,
                status=status,
                details=details,
            ))

        overall_score = sum(m.score for m in metrics) / max(len(metrics), 1)

        if overall_score >= 0.8:
            health = HealthLevel.EXCELLENT
        elif overall_score >= 0.6:
            health = HealthLevel.GOOD
        elif overall_score >= 0.4:
            health = HealthLevel.FAIR
        elif overall_score >= 0.2:
            health = HealthLevel.POOR
        else:
            health = HealthLevel.CRITICAL

        critical = [m for m in metrics if m.score < 0.3]
        critical_issues = [f"{m.metric.value}: {m.details}" for m in critical]

        recommendations: List[str] = []
        if critical:
            recommendations.append(f"Address {len(critical)} critical trust metrics immediately")
        low = [m for m in metrics if m.score < 0.6 and m.score >= 0.3]
        if low:
            recommendations.append(f"Improve {len(low)} below-target trust metrics")
        if not recommendations:
            recommendations.append("All trust metrics are healthy")

        return DashboardReport(
            overall_health=health,
            overall_score=overall_score,
            metrics=metrics,
            total_systems_reporting=len(self._sources),
            critical_issues=critical_issues,
            recommendations=recommendations,
        )
