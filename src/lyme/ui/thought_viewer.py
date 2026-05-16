import json
from pathlib import Path


def render_cognitive_trace(trace_data: dict, output_path: str = "") -> str:
    title = trace_data.get("scenario_name", "Cognitive Trace")
    agent = trace_data.get("agent_name", "unknown")
    scenario = trace_data.get("scenario_name", "unknown")
    trace_id = trace_data.get("trace_id", "")
    steps_json = json.dumps(trace_data.get("steps", []))

    html = _THOUGHT_TEMPLATE.replace("__TITLE__", title)
    html = html.replace("__AGENT__", agent)
    html = html.replace("__SCENARIO__", scenario)
    html = html.replace("__TRACE_ID__", trace_id)
    html = html.replace("__DATA__", steps_json)

    if output_path:
        Path(output_path).write_text(html)
    return html


def render_branch_view(trace_data: dict, output_path: str = "") -> str:
    branches = {}
    for step in trace_data.get("steps", []):
        branch = step.get("branch", "main")
        branches.setdefault(branch, []).append(step)

    html = "<html><body style='background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:20px;'>"
    html += f"<h1>Branch View: {trace_data.get('scenario_name', '')}</h1>"
    for branch, steps in branches.items():
        html += f"<div class='branch'><h3>{branch} ({len(steps)} steps)</h3>"
        for s in steps:
            html += f"<div class='thought'><span class='type-badge type-{s['type']}'>{s['type']}</span>{s['content'][:100]}</div>"
        html += "</div>"
    html += "</body></html>"

    if output_path:
        Path(output_path).write_text(html)
    return html


_THOUGHT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lyme Cognitive Trace Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; margin-bottom: 4px; font-size: 18px; }
  .meta { color: #8b949e; font-size: 12px; margin-bottom: 16px; }
  .controls { margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .controls button, .controls select { background: #21262d; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; }
  .controls button:hover { background: #30363d; }
  .thought-chain { position: relative; padding-left: 24px; }
  .thought-chain::before { content: ''; position: absolute; left: 10px; top: 0; bottom: 0;
    width: 2px; background: #30363d; }
  .thought { position: relative; margin-bottom: 4px; padding: 8px 12px;
    border-radius: 6px; background: #161b22; border: 1px solid #30363d;
    font-size: 13px; line-height: 1.4; }
  .thought::before { content: ''; position: absolute; left: -18px; top: 12px;
    width: 6px; height: 6px; border-radius: 50%; background: #30363d; }
  .thought .type-badge { display: inline-block; padding: 1px 6px; border-radius: 10px;
    font-size: 10px; font-weight: 600; margin-right: 6px; }
  .type-plan { background: #1f6feb33; color: #58a6ff; }
  .type-decision { background: #23863633; color: #3fb950; }
  .type-error { background: #da363333; color: #f85149; }
  .type-uncertainty { background: #d2992233; color: #d29922; }
  .type-exploration { background: #8957e533; color: #a371f7; }
  .type-retry { background: #f0883e33; color: #f0883e; }
  .type-hallucination { background: #ff7b7233; color: #ff7b72; }
  .type-insight { background: #23863633; color: #3fb950; }
  .thought .confidence { color: #8b949e; font-size: 11px; margin-left: 6px; }
  .thought .content { margin-top: 3px; color: #e6edf3; }
  .thought .time { color: #484f58; font-size: 10px; margin-left: 4px; }
  .summary { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 6px; margin-bottom: 16px; }
  .summary-item { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
    padding: 10px; text-align: center; }
  .summary-item .value { color: #58a6ff; font-size: 18px; font-weight: 600; }
  .summary-item .label { color: #8b949e; font-size: 10px; margin-top: 2px; }
  .conf-chart { margin: 12px 0; padding: 8px; background: #161b22; border-radius: 6px; }
  .conf-bar { display: inline-block; height: 12px; border-radius: 2px;
    margin-right: 1px; transition: background 0.2s; }
  .branch { border-left: 2px solid #30363d; margin-left: 12px; padding-left: 12px; }
</style>
</head>
<body>
<h1>Cognitive Trace: __TITLE__</h1>
<div class="meta">__AGENT__ / __SCENARIO__ / __TRACE_ID__</div>
<div class="summary" id="summary"></div>
<div class="controls">
  <select id="typeFilter"><option value="">All Types</option></select>
  <select id="confidenceFilter"><option value="">All Confidence</option>
    <option value="high">High (>0.8)</option><option value="medium">Medium (0.4-0.8)</option>
    <option value="low">Low (<0.4)</option></select>
  <button onclick="resetFilter()">Reset</button>
</div>
<div class="conf-chart" id="confChart"></div>
<div class="thought-chain" id="chain"></div>
<script>
const DATA = __DATA__;
function render(steps) {
  document.getElementById('chain').innerHTML = steps.map(s => `
    <div class="thought">
      <span class="type-badge type-${s.type.replace(/_/g,'-')}">${s.type.replace(/_/g,' ')}</span>
      <span class="confidence">[${(s.confidence*100).toFixed(0)}%]</span>
      <span class="time">${new Date(s.timestamp*1000).toISOString().substr(11,8)}</span>
      <div class="content">${s.content}</div>
    </div>
  `).join('');

  const confData = steps.map((s,i) => s.confidence);
  document.getElementById('confChart').innerHTML = confData.map((c,i) =>
    `<div class="conf-bar" style="width:${100/confData.length}%;background:hsl(${c*120},70%,50%)" title="step ${i}: ${(c*100).toFixed(0)}%"></div>`
  ).join('');
}
render(DATA);
const types = [...new Set(DATA.map(s => s.type))];
const sel = document.getElementById('typeFilter');
types.forEach(t => { const opt = document.createElement('option'); opt.value = t; opt.textContent = t.replace(/_/g,' '); sel.appendChild(opt); });
document.getElementById('typeFilter').onchange = applyFilter;
document.getElementById('confidenceFilter').onchange = applyFilter;
function applyFilter() {
  let steps = DATA;
  const type = document.getElementById('typeFilter').value;
  const conf = document.getElementById('confidenceFilter').value;
  if (type) steps = steps.filter(s => s.type === type);
  if (conf === 'high') steps = steps.filter(s => s.confidence > 0.8);
  else if (conf === 'medium') steps = steps.filter(s => s.confidence >= 0.4 && s.confidence <= 0.8);
  else if (conf === 'low') steps = steps.filter(s => s.confidence < 0.4);
  render(steps);
}
function resetFilter() {
  document.getElementById('typeFilter').value = '';
  document.getElementById('confidenceFilter').value = '';
  render(DATA);
}
const summary = DATA.reduce((acc, s) => { acc[s.type] = (acc[s.type] || 0) + 1; return acc; }, {});
summary.total = DATA.length;
summary.avg_conf = (DATA.reduce((a,s) => a+s.confidence, 0) / DATA.length * 100).toFixed(0);
document.getElementById('summary').innerHTML = Object.entries(summary).map(([k,v]) =>
  `<div class="summary-item"><div class="value">${v}</div><div class="label">${k.replace(/_/g,' ')}</div></div>`
).join('');
</script>
</body>
</html>"""
