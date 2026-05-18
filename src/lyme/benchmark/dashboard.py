"""ScoringDashboard — generates HTML/JSON benchmark dashboards."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DashboardConfig:
    title: str = "Lyme Benchmark Dashboard"
    output_dir: str = "."


class ScoringDashboard:
    def __init__(self, config: DashboardConfig = None):
        self.config = config or DashboardConfig()
        self._runs: List[Dict[str, Any]] = []
        self._scores: Dict[str, Dict[str, float]] = {}

    def add_run(self, agent: str, scenario: str, metrics: Dict[str, float]) -> None:
        self._runs.append({
            "agent": agent,
            "scenario": scenario,
            "metrics": metrics,
            "timestamp": time.time(),
        })
        if agent not in self._scores:
            self._scores[agent] = {}
        if scenario not in self._scores[agent]:
            self._scores[agent][scenario] = {}
        self._scores[agent][scenario] = metrics

    def _leaderboard(self) -> List[Dict[str, Any]]:
        agent_scores: Dict[str, List[float]] = {}
        for run in self._runs:
            agent = run["agent"]
            if agent not in agent_scores:
                agent_scores[agent] = []
            metrics = run["metrics"]
            avg = sum(metrics.values()) / max(len(metrics), 1)
            agent_scores[agent].append(avg)

        return [
            {
                "rank": i + 1,
                "agent": agent,
                "avg_score": round(sum(scores) / len(scores), 4),
                "runs": len(scores),
            }
            for i, (agent, scores) in enumerate(
                sorted(agent_scores.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)
            )
        ]

    def to_html(self) -> str:
        leaderboard = self._leaderboard()
        lines = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8">',
            f"<title>{self.config.title}</title>",
            "<style>",
            "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px;background:#0d1117;color:#c9d1d9}",
            "h1{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px}",
            "h2{color:#58a6ff;margin-top:30px}",
            "table{border-collapse:collapse;width:100%;margin:10px 0}",
            "th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}",
            "th{background:#161b22;color:#8b949e}",
            "tr:hover{background:#161b22}",
            ".rank1{color:#ffd700;font-weight:bold}",
            ".rank2{color:#c0c0c0;font-weight:bold}",
            ".rank3{color:#cd7f32;font-weight:bold}",
            "</style></head><body>",
            f"<h1>{self.config.title}</h1>",
            f"<p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>",
            "<h2>Leaderboard</h2>",
            "<table><tr><th>Rank</th><th>Agent</th><th>Avg Score</th><th>Runs</th></tr>",
        ]
        for entry in leaderboard:
            rank_cls = f"rank{entry['rank']}" if entry["rank"] <= 3 else ""
            lines.append(
                f"<tr><td class='{rank_cls}'>#{entry['rank']}</td>"
                f"<td>{entry['agent']}</td>"
                f"<td>{entry['avg_score']:.4f}</td>"
                f"<td>{entry['runs']}</td></tr>"
            )
        lines.append("</table>")

        lines.append("<h2>Per-Scenario Scores</h2>")
        agents = sorted(self._scores.keys())
        scenarios = sorted(set(
            s for agent_data in self._scores.values() for s in agent_data
        ))
        lines.append("<table><tr><th>Scenario</th>" + "".join(f"<th>{a}</th>" for a in agents) + "</tr>")
        for sc in scenarios:
            lines.append(f"<tr><td>{sc}</td>")
            for agent in agents:
                metrics = self._scores.get(agent, {}).get(sc, {})
                avg = sum(metrics.values()) / max(len(metrics), 1) if metrics else 0
                lines.append(f"<td>{avg:.3f}</td>")
            lines.append("</tr>")
        lines.append("</table></body></html>")

        return "\n".join(lines)

    def save(self, name: str = "dashboard") -> Dict[str, str]:
        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        html_path = out / f"{name}.html"
        html_path.write_text(self.to_html())

        json_path = out / f"{name}.json"
        json_path.write_text(json.dumps({
            "title": self.config.title,
            "leaderboard": self._leaderboard(),
            "runs": self._runs,
        }, indent=2))

        return {"html": str(html_path), "json": str(json_path)}

    def __len__(self) -> int:
        return len(self._runs)
