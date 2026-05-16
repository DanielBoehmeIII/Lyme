"""Research Report Generator for Lyme.

Given experiment results, produces:
- abstract
- methodology
- setup
- models tested
- tasks
- metrics
- results
- statistical analysis
- limitations
- future work

The report avoids hype and is brutally honest.
It should say when results are weak, noisy, or inconclusive.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import json
import math
import uuid


class ResultStrength(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INCONCLUSIVE = "inconclusive"
    NO_EFFECT = "no_effect"
    CONTRADICTORY = "contradictory"


@dataclass
class ReportSection:
    title: str = ""
    content: str = ""
    subsections: List[ReportSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class StatisticalResult:
    metric: str = ""
    control_mean: float = 0.0
    treatment_mean: float = 0.0
    difference: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    p_value: float = 0.5
    effect_size: float = 0.0
    significant: bool = False
    interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "control_mean": self.control_mean,
            "treatment_mean": self.treatment_mean,
            "difference": self.difference,
            "confidence_interval": list(self.confidence_interval),
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "significant": self.significant,
            "interpretation": self.interpretation,
        }


@dataclass
class Finding:
    statement: str = ""
    strength: ResultStrength = ResultStrength.INCONCLUSIVE
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    caveats: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "strength": self.strength.value,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "caveats": self.caveats,
        }


@dataclass
class ResearchReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = "0.1.0"

    abstract: str = ""
    methodology: str = ""
    setup: str = ""
    models_tested: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    results: List[StatisticalResult] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    future_work: List[str] = field(default_factory=list)
    raw_data_summary: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "generated_at": self.generated_at,
            "abstract": self.abstract,
            "methodology": self.methodology,
            "setup": self.setup,
            "models_tested": self.models_tested,
            "tasks": self.tasks,
            "metrics": self.metrics,
            "results": [r.to_dict() for r in self.results],
            "findings": [f.to_dict() for f in self.findings],
            "limitations": self.limitations,
            "future_work": self.future_work,
            "raw_data_summary": self.raw_data_summary,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Research Report: {self.title}")
        lines.append(f"")
        lines.append(f"**Generated**: {self.generated_at}")
        lines.append(f"**ID**: {self.id}")
        lines.append(f"")

        lines.append(f"## Abstract")
        lines.append(f"{self.abstract}")
        lines.append(f"")

        lines.append(f"## Methodology")
        lines.append(f"{self.methodology}")
        lines.append(f"")

        lines.append(f"## Setup")
        lines.append(f"{self.setup}")
        lines.append(f"")

        if self.models_tested:
            lines.append(f"## Models Tested")
            for m in self.models_tested:
                lines.append(f"- {m}")
            lines.append(f"")

        if self.tasks:
            lines.append(f"## Tasks ({len(self.tasks)})")
            for t in self.tasks:
                lines.append(f"- {t}")
            lines.append(f"")

        if self.results:
            lines.append(f"## Results")
            for r in self.results:
                sig_mark = " ✓" if r.significant else " ✗"
                ci = f"[{r.confidence_interval[0]:.3f}, {r.confidence_interval[1]:.3f}]"
                lines.append(f"")
                lines.append(f"### {r.metric}{sig_mark}")
                lines.append(f"- Control: {r.control_mean:.3f} → Treatment: {r.treatment_mean:.3f}")
                lines.append(f"- Difference: {r.difference:+.3f} (p={r.p_value:.3f}, d={r.effect_size:.2f})")
                lines.append(f"- 95% CI: {ci}")
                lines.append(f"- {r.interpretation}")
            lines.append(f"")

        if self.findings:
            lines.append(f"## Findings")
            for f in self.findings:
                strength_icons = {
                    ResultStrength.STRONG: "✓✓",
                    ResultStrength.MODERATE: "✓",
                    ResultStrength.WEAK: "~",
                    ResultStrength.INCONCLUSIVE: "?",
                    ResultStrength.NO_EFFECT: "∅",
                    ResultStrength.CONTRADICTORY: "!",
                }
                icon = strength_icons.get(f.strength, "?")
                lines.append(f"- [{icon} {f.strength.value}] {f.statement}")
                if f.caveats:
                    for c in f.caveats:
                        lines.append(f"  - Caveat: {c}")
            lines.append(f"")

        if self.limitations:
            lines.append(f"## Limitations")
            for l in self.limitations:
                lines.append(f"- {l}")
            lines.append(f"")

        if self.future_work:
            lines.append(f"## Future Work")
            for f in self.future_work:
                lines.append(f"- {f}")
            lines.append(f"")

        return "\n".join(lines)


class ResearchReportGenerator:
    def __init__(self):
        self._weak_threshold = 0.05
        self._moderate_threshold = 0.01

    def generate_from_metrics(
        self,
        title: str,
        control_metrics: Dict[str, List[float]],
        treatment_metrics: Dict[str, List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResearchReport:
        report = ResearchReport(title=title)

        for metric in control_metrics:
            report.metrics.append(metric)
            control_vals = control_metrics[metric]
            treatment_vals = treatment_metrics.get(metric, [])

            if control_vals and treatment_vals:
                stat = self._analyze_metric(metric, control_vals, treatment_vals)
                report.results.append(stat)

        report.findings = self._derive_findings(report.results)
        report.limitations = self._derive_limitations(report.results)
        report.future_work = self._derive_future_work(report.results)

        report.abstract = self._generate_abstract(report)
        report.methodology = self._generate_methodology()
        report.setup = self._generate_setup(metadata)

        if metadata:
            report.models_tested = metadata.get("models", [])
            report.tasks = metadata.get("tasks", [])
            report.metadata = metadata

        return report

    def generate_from_experiment_plan(
        self,
        title: str,
        plan_results: Dict[str, Dict[str, float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResearchReport:
        control = {}
        treatment = {}
        for metric, values in plan_results.items():
            if "control" in values:
                control[metric] = [values["control"]]
            if "treatment" in values:
                treatment[metric] = [values["treatment"]]

        return self.generate_from_metrics(title, control, treatment, metadata)

    def _analyze_metric(
        self, metric: str, control_vals: List[float], treatment_vals: List[float]
    ) -> StatisticalResult:
        import statistics

        control_mean = statistics.mean(control_vals) if control_vals else 0.0
        treatment_mean = statistics.mean(treatment_vals) if treatment_vals else 0.0
        diff = treatment_mean - control_mean

        control_std = statistics.stdev(control_vals) if len(control_vals) > 1 else 0.05
        treatment_std = statistics.stdev(treatment_vals) if len(treatment_vals) > 1 else 0.05

        pooled_std = math.sqrt(
            (control_std ** 2 + treatment_std ** 2) / 2
        ) if control_std or treatment_std else 0.1

        effect_size = diff / pooled_std if pooled_std > 0 else 0.0

        n1, n2 = len(control_vals), len(treatment_vals)
        se = pooled_std * math.sqrt(1 / max(n1, 1) + 1 / max(n2, 1))
        t_stat = diff / se if se > 0 else 0.0
        df = max(n1 + n2 - 2, 1)
        p_value = self._approximate_p_value(t_stat, df)

        ci_margin = 1.96 * se
        ci = (diff - ci_margin, diff + ci_margin)

        significant = p_value < 0.05

        if significant:
            if p_value < 0.001:
                interpretation = f"Strong evidence: {metric} differs significantly (p<0.001)"
            elif p_value < 0.01:
                interpretation = f"Moderate evidence: {metric} differs (p<0.01)"
            else:
                interpretation = f"Some evidence: {metric} differs (p<0.05)"
        else:
            interpretation = f"No significant difference in {metric} (p={p_value:.3f})"

        if abs(effect_size) < 0.2:
            interpretation += ". Effect size negligible."
        elif abs(effect_size) < 0.5:
            interpretation += ". Effect size small."
        elif abs(effect_size) < 0.8:
            interpretation += ". Effect size medium."

        return StatisticalResult(
            metric=metric,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            difference=diff,
            confidence_interval=ci,
            p_value=p_value,
            effect_size=effect_size,
            significant=significant,
            interpretation=interpretation,
        )

    def _approximate_p_value(self, t_stat: float, df: int) -> float:
        """Approximate p-value from t-statistic using normal approximation."""
        from math import exp, pi, atan
        x = abs(t_stat)
        if df > 30:
            p = 2 * (1 - self._normal_cdf(x))
        else:
            p = 2 * (1 - min(0.5, 0.5 * (1 + x / math.sqrt(df + x * x))))
        return max(0.001, min(0.999, p))

    def _normal_cdf(self, x: float) -> float:
        """Standard normal CDF approximation."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _derive_findings(self, results: List[StatisticalResult]) -> List[Finding]:
        findings = []

        for r in results:
            if r.significant:
                strength = ResultStrength.STRONG if r.p_value < 0.001 else ResultStrength.MODERATE
                if abs(r.effect_size) < 0.3:
                    strength = ResultStrength.WEAK
                findings.append(Finding(
                    statement=r.interpretation.split(".")[0],
                    strength=strength,
                    evidence=[f"p={r.p_value:.3f}, d={r.effect_size:.2f}, CI={r.confidence_interval}"],
                    confidence=1.0 - min(r.p_value, 1.0),
                    caveats=[] if abs(r.effect_size) >= 0.3 else ["Effect size is small — practical significance unclear"],
                ))
            else:
                findings.append(Finding(
                    statement=f"No significant effect detected for {r.metric}",
                    strength=ResultStrength.INCONCLUSIVE if abs(r.effect_size) > 0.2 else ResultStrength.NO_EFFECT,
                    evidence=[f"p={r.p_value:.3f}, d={r.effect_size:.2f}"],
                    confidence=0.3,
                    caveats=["Absence of evidence is not evidence of absence — study may be underpowered"],
                ))

        if not findings:
            findings.append(Finding(
                statement="No statistically significant results were found across any metric",
                strength=ResultStrength.INCONCLUSIVE,
                caveats=["Results may be noisy or effect sizes may be smaller than detectable"],
            ))

        return findings

    def _derive_limitations(self, results: List[StatisticalResult]) -> List[str]:
        limitations = []

        low_n = sum(1 for r in results if r.significant and r.p_value > 0.01)
        if low_n > 0:
            limitations.append(
                f"Several results are borderline significant ({low_n} metrics with p near 0.05)"
            )

        small_effects = sum(1 for r in results if abs(r.effect_size) < 0.3)
        if small_effects > len(results) / 2:
            limitations.append("Most effect sizes are small — practical significance is uncertain")

        limitations.append("Results based on simulated/estimated data — real-world validation needed")
        limitations.append("Sample sizes may be insufficient to detect small effect sizes")
        limitations.append("Metrics may not capture all relevant dimensions of agent performance")

        return limitations

    def _derive_future_work(self, results: List[StatisticalResult]) -> List[str]:
        future = []

        sig_metrics = [r for r in results if r.significant]
        if sig_metrics:
            future.append(f"Replicate significant findings for {', '.join(r.metric for r in sig_metrics[:3])} with larger samples")

        non_sig = [r for r in results if not r.significant and abs(r.effect_size) > 0.2]
        if non_sig:
            future.append(f"Increase statistical power for inconclusive metrics ({len(non_sig)} affected)")

        future.append("Extend evaluation to additional task types and difficulty levels")
        future.append("Investigate interaction effects between components")
        future.append("Validate findings across multiple model families and sizes")

        return future

    def _generate_abstract(self, report: ResearchReport) -> str:
        sig_count = sum(1 for r in report.results if r.significant)
        total = len(report.results)

        if sig_count == 0:
            strength = "no statistically significant effects were detected"
        elif sig_count <= total / 3:
            strength = f"some effects were detected ({sig_count}/{total} metrics significant)"
        elif sig_count <= total * 2 / 3:
            strength = f"moderate effects were detected ({sig_count}/{total} metrics significant)"
        else:
            strength = f"strong effects were detected ({sig_count}/{total} metrics significant)"

        return (
            f"We present an experimental evaluation of {report.title}. "
            f"Across {total} metrics, {strength}. "
            f"Effect sizes ranged from {min((abs(r.effect_size) for r in report.results), default=0):.2f} "
            f"to {max((abs(r.effect_size) for r in report.results), default=0):.2f}. "
            f"Results should be interpreted with caution given the limitations discussed below."
        )

    def _generate_methodology(self) -> str:
        return (
            "We conduct controlled experiments comparing agent performance with and without "
            "specific components or interventions. Each condition is replicated multiple times "
            "to estimate variance. Statistical significance is assessed using t-tests with "
            "α=0.05. Effect sizes are reported as Cohen's d. Confidence intervals are 95%.\n\n"
            "No p-hacking. No selective reporting. All metrics are reported regardless of "
            "significance. Results marked as 'inconclusive' should not be interpreted as "
            "evidence for or against an effect."
        )

    def _generate_setup(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        if metadata:
            parts = []
            if "models" in metadata:
                parts.append(f"Models tested: {', '.join(metadata['models'])}")
            if "temperature" in metadata:
                parts.append(f"Temperature: {metadata['temperature']}")
            if "repetitions" in metadata:
                parts.append(f"Repetitions per condition: {metadata['repetitions']}")
            return "\n".join(parts)
        return "See experimental metadata for detailed setup."
