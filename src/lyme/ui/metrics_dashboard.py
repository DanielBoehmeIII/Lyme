import json
from pathlib import Path
from typing import Dict, Any, List


def render_dashboard(runs: List[dict], output_path: str = "") -> str:
    cards = []
    all_agents = set()

    for run in runs:
        agent = run.get("agent_name", "unknown")
        all_agents.add(agent)
        scenario = run.get("scenario_name", "")
        metrics = run.get("metrics", {})

        card_metrics = []
        for name, value in list(metrics.items())[:6]:
            if isinstance(value, float):
                card_metrics.append({
                    "name": name.replace("_", " ").title(),
                    "value": f"{value:.2f}" if value < 1000 else f"{value:.0f}",
                })
            else:
                card_metrics.append({
                    "name": name.replace("_", " ").title(),
                    "value": str(value),
                })

        cards.append({
            "title": f"{agent} / {scenario}",
            "metrics": card_metrics,
        })

    data = {
        "cards": cards,
        "agents": list(all_agents),
        "comparison": _build_comparison_table(runs, list(all_agents)),
    }

    data_json = json.dumps(data)
    html = _DASHBOARD_TEMPLATE.replace("__DATA__", data_json)

    if output_path:
        Path(output_path).write_text(html)
    return html


def _build_comparison_table(runs: List[dict], agents: List[str]) -> list:
    if len(agents) < 2:
        return []

    pivot = {}
    for run in runs:
        agent = run.get("agent_name", "")
        scenario = run.get("scenario_name", "")
        key = f"{scenario}"
        if key not in pivot:
            pivot[key] = {}
        pivot[key][agent] = run.get("metrics", {})

    table = []
    for scenario, agent_metrics in pivot.items():
        for metric in ["duration_ms", "tool_calls_count", "errors_count", "hallucinations_detected"]:
            values = []
            for agent in agents:
                m = agent_metrics.get(agent, {})
                v = m.get(metric, "N/A")
                if isinstance(v, float):
                    values.append(f"{v:.1f}")
                else:
                    values.append(str(v))
            table.append({"name": f"{scenario} / {metric}", "values": values})

    return table


_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lyme Metrics Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; margin-bottom: 16px; font-size: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 12px; margin-bottom: 20px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .card h3 { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
             margin-bottom: 8px; }
  .card .metric { display: flex; justify-content: space-between; padding: 4px 0;
                  border-bottom: 1px solid #21262d; font-size: 13px; }
  .card .metric:last-child { border-bottom: none; }
  .card .value { color: #58a6ff; font-weight: 600; }
  .comparison { margin-top: 20px; }
  .comparison table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .comparison th { background: #21262d; color: #8b949e; padding: 8px 12px;
                   text-align: left; font-weight: 500; border-bottom: 1px solid #30363d; }
  .comparison td { padding: 8px 12px; border-bottom: 1px solid #21262d; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
           font-size: 10px; font-weight: 600; }
  .badge.pass { background: #23863633; color: #3fb950; }
  .badge.fail { background: #da363333; color: #f85149; }
</style>
</head>
<body>
<h1>Lyme Metrics Dashboard</h1>
<div class="grid" id="cards"></div>
<div class="comparison" id="comparison"></div>
<script>
const DATA = __DATA__;
const cardsContainer = document.getElementById('cards');
DATA.cards.forEach(card => {
  const el = document.createElement('div');
  el.className = 'card';
  el.innerHTML = '<h3>' + card.title + '</h3>' +
    card.metrics.map(m => '<div class="metric"><span>' + m.name + '</span><span class="value">' + m.value + '</span></div>').join('');
  cardsContainer.appendChild(el);
});
if (DATA.comparison && DATA.comparison.length) {
  let html = '<h2 style="color:#58a6ff;font-size:14px;margin-bottom:8px;">Agent Comparison</h2><table><tr><th>Metric</th>';
  DATA.agents.forEach(a => { html += '<th>' + a + '</th>'; });
  html += '</tr>';
  DATA.comparison.forEach(row => {
    html += '<tr><td>' + row.name + '</td>';
    row.values.forEach(v => { html += '<td>' + v + '</td>'; });
    html += '</tr>';
  });
  html += '</table>';
  document.getElementById('comparison').innerHTML = html;
}
</script>
</body>
</html>"""
