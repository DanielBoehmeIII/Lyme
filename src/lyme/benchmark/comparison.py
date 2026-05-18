"""ComparisonEngine — multi-agent benchmark comparison and dashboard generation."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine import BenchmarkEngine, BenchmarkRun
from .runner import AgentRunnerStatus
from .agents import AGENT_REGISTRY, SUPPORTED_AGENTS
from ..config import AgentConfig, Settings


@dataclass
class ComparisonMetric:
    name: str
    lyme_value: float = 0.0
    competitor_value: float = 0.0
    lyme_wins: bool = False
    unit: str = ""

    @property
    def delta(self) -> float:
        return self.lyme_value - self.competitor_value

    @property
    def delta_pct(self) -> float:
        if self.competitor_value == 0:
            return 0.0
        return (self.delta / self.competitor_value) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lyme": round(self.lyme_value, 4),
            "competitor": round(self.competitor_value, 4),
            "delta": round(self.delta, 4),
            "delta_pct": round(self.delta_pct, 2),
            "lyme_wins": self.lyme_wins,
            "unit": self.unit,
        }


@dataclass
class AgentComparison:
    competitor_name: str
    scenario: str
    metrics: List[ComparisonMetric] = field(default_factory=list)
    lyme_score: float = 0.0
    competitor_score: float = 0.0
    lyme_wins: bool = False
    total_metrics: int = 0
    metrics_won: int = 0

    @property
    def win_rate(self) -> float:
        return self.metrics_won / max(self.total_metrics, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor_name,
            "scenario": self.scenario,
            "lyme_score": round(self.lyme_score, 4),
            "competitor_score": round(self.competitor_score, 4),
            "lyme_wins": self.lyme_wins,
            "win_rate": round(self.win_rate, 4),
            "total_metrics": self.total_metrics,
            "metrics_won": self.metrics_won,
            "metrics": [m.to_dict() for m in self.metrics],
        }


@dataclass
class ComparisonReport:
    timestamp: float = field(default_factory=time.time)
    comparisons: List[AgentComparison] = field(default_factory=list)
    lyme_overall_wins: int = 0
    lyme_overall_losses: int = 0
    total_comparisons: int = 0
    overall_win_rate: float = 0.0

    def add_comparison(self, comp: AgentComparison) -> None:
        self.comparisons.append(comp)
        self.total_comparisons += 1
        if comp.lyme_wins:
            self.lyme_overall_wins += 1
        else:
            self.lyme_overall_losses += 1
        self.overall_win_rate = self.lyme_overall_wins / max(self.total_comparisons, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_comparisons": self.total_comparisons,
            "lyme_wins": self.lyme_overall_wins,
            "lyme_losses": self.lyme_overall_losses,
            "overall_win_rate": round(self.overall_win_rate, 4),
            "comparisons": [c.to_dict() for c in self.comparisons],
        }

    def to_html(self) -> str:
        lines = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8"><title>Lyme Benchmark Comparison</title>',
            "<style>",
            "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px;background:#0d1117;color:#c9d1d9}",
            "h1{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px}",
            "h2{color:#58a6ff;margin-top:30px}",
            "table{border-collapse:collapse;width:100%;margin:10px 0 20px}",
            "th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}",
            "th{background:#161b22;color:#8b949e;font-weight:600}",
            "tr:hover{background:#161b22}",
            ".win{color:#3fb950;font-weight:bold}",
            ".loss{color:#f85149;font-weight:bold}",
            ".tie{color:#d29922}",
            ".score{font-size:24px;font-weight:bold;margin:10px 0}",
            ".summary{display:flex;gap:20px;margin:20px 0}",
            ".card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;flex:1}",
            ".card h3{margin:0 0 8px;color:#8b949e;font-size:14px}",
            ".card .value{font-size:28px;font-weight:bold}",
            "</style></head><body>",
            f"<h1>Lyme Benchmark Comparison</h1>",
            f"<p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>",
            '<div class="summary">',
            f'<div class="card"><h3>Total Comparisons</h3><div class="value" style="color:#58a6ff">{self.total_comparisons}</div></div>',
            f'<div class="card"><h3>Lyme Wins</h3><div class="value win">{self.lyme_overall_wins}</div></div>',
            f'<div class="card"><h3>Win Rate</h3><div class="value" style="color:{'#3fb950' if self.overall_win_rate > 0.5 else '#f85149'}">{self.overall_win_rate:.0%}</div></div>',
            "</div>",
        ]

        for comp in self.comparisons:
            lines.append(f"<h2>{comp.competitor_name} — {comp.scenario}</h2>")
            lines.append(f'<div class="score {("win" if comp.lyme_wins else "loss")}">Lyme: {comp.lyme_score:.1f} vs {comp.competitor_name}: {comp.competitor_score:.1f}</div>')
            lines.append('<table><tr><th>Metric</th><th>Lyme</th><th>' + comp.competitor_name + '</th><th>Delta</th><th>Result</th></tr>')
            for m in comp.metrics:
                cls = "win" if m.lyme_wins else "loss"
                lines.append(f"<tr><td>{m.name}</td><td>{m.lyme_value:.2f}</td><td>{m.competitor_value:.2f}</td><td>{m.delta_pct:+.1f}%</td><td class='{cls}'>Lyme {'wins' if m.lyme_wins else 'loses'}</td></tr>")
            lines.append("</table>")

        lines.append("</body></html>")
        return "\n".join(lines)


class ComparisonEngine:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.engine = BenchmarkEngine(self.settings)
        self.report = ComparisonReport()

    def compare(self, scenario_name: str, competitors: List[str]) -> ComparisonReport:
        agent_configs = [self.engine.settings.agents[0] if self.engine.settings.agents else None]
        for name in competitors:
            try:
                from .agents import get_agent
                agent_configs.append(get_agent(name))
            except KeyError:
                continue

        if not agent_configs:
            return self.report

        runs = self.engine.run_scenarios([scenario_name], agent_configs)
        lyme_run = next((r for r in runs if r.agent_name in ("lyme", "opencode")), None)
        competitor_map: Dict[str, BenchmarkRun] = {}
        for run in runs:
            if run.agent_name not in ("lyme", "opencode"):
                competitor_map[run.agent_name] = run

        if not lyme_run:
            return self.report

        for comp_name, comp_run in competitor_map.items():
            comp = AgentComparison(
                competitor_name=comp_name,
                scenario=scenario_name,
            )
            metrics = self._extract_metrics(lyme_run, comp_run)
            comp.metrics = metrics
            comp.total_metrics = len(metrics)
            comp.metrics_won = sum(1 for m in metrics if m.lyme_wins)
            comp.lyme_score = sum(m.lyme_value for m in metrics) / max(len(metrics), 1)
            comp.competitor_score = sum(m.competitor_value for m in metrics) / max(len(metrics), 1)
            comp.lyme_wins = comp.lyme_score >= comp.competitor_score
            self.report.add_comparison(comp)

        return self.report

    def compare_all(self, scenario_name: str) -> ComparisonReport:
        return self.compare(scenario_name, SUPPORTED_AGENTS)

    def _extract_metrics(self, lyme_run: BenchmarkRun, comp_run: BenchmarkRun) -> List[ComparisonMetric]:
        metrics = []

        lr = lyme_run.agent_result
        cr = comp_run.agent_result

        if lr and cr:
            metrics.append(ComparisonMetric(
                name="task_success",
                lyme_value=1.0 if lr.status == AgentRunnerStatus.SUCCESS else 0.0,
                competitor_value=1.0 if cr.status == AgentRunnerStatus.SUCCESS else 0.0,
                lyme_wins=(lr.status == AgentRunnerStatus.SUCCESS) and (cr.status != AgentRunnerStatus.SUCCESS),
                unit="bool",
            ))
            metrics.append(ComparisonMetric(
                name="latency_ms",
                lyme_value=lr.duration_ms,
                competitor_value=cr.duration_ms,
                lyme_wins=lr.duration_ms < cr.duration_ms,
                unit="ms",
            ))

        lr_metrics = lyme_run.scenario_result.metrics if lyme_run.scenario_result else {}
        cr_metrics = comp_run.scenario_result.metrics if comp_run.scenario_result else {}

        for key in set(list(lr_metrics.keys()) + list(cr_metrics.keys())):
            lv = lr_metrics.get(key, 0.0)
            cv = cr_metrics.get(key, 0.0)
            higher_is_better = key not in ("latency", "duration_ms", "tokens", "cost")
            metrics.append(ComparisonMetric(
                name=key,
                lyme_value=lv,
                competitor_value=cv,
                lyme_wins=lv > cv if higher_is_better else lv < cv,
                unit="",
            ))

        return metrics

    def generate_report(self, output_dir: str = ".") -> Dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        html_path = out / "benchmark-comparison.html"
        html_path.write_text(self.report.to_html())

        json_path = out / "benchmark-comparison.json"
        json_path.write_text(json.dumps(self.report.to_dict(), indent=2))

        return {
            "html": str(html_path),
            "json": str(json_path),
        }
