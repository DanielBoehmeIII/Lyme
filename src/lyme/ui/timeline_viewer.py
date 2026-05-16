import json
from pathlib import Path


def render_timeline(timeline, title: str = "Agent Timeline",
                    output_path: str = "") -> str:
    data_json = json.dumps(timeline.to_dict())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lyme Timeline Viewer</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; margin-bottom: 20px; font-size: 18px; font-weight: 600; }}
.timeline {{ position: relative; padding-left: 30px; }}
.timeline::before {{ content: ''; position: absolute; left: 12px; top: 0; bottom: 0;
                    width: 2px; background: #30363d; }}
.event {{ position: relative; margin-bottom: 6px; padding: 8px 12px;
         border-radius: 6px; background: #161b22; border: 1px solid #30363d;
         font-size: 12px; cursor: pointer; transition: background 0.15s; }}
.event:hover {{ background: #1c2128; }}
.event::before {{ content: ''; position: absolute; left: -22px; top: 12px;
                 width: 8px; height: 8px; border-radius: 50%; background: #30363d; }}
.event.success::before {{ background: #3fb950; }}
.event.error::before {{ background: #f85149; }}
.event.warning::before {{ background: #d29922; }}
.event .time {{ color: #8b949e; font-size: 11px; display: inline-block; width: 80px; }}
.event .label {{ color: #c9d1d9; font-weight: 500; }}
.event .detail {{ color: #8b949e; font-size: 11px; margin-top: 2px; }}
.event .duration {{ color: #58a6ff; font-size: 11px; margin-left: 8px; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
         gap: 8px; margin-bottom: 20px; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px;
        padding: 12px; text-align: center; }}
.stat .value {{ color: #58a6ff; font-size: 20px; font-weight: 600; }}
.stat .name {{ color: #8b949e; font-size: 11px; margin-top: 2px; }}
.depth-1 {{ margin-left: 20px; }}
.depth-2 {{ margin-left: 40px; }}
.depth-3 {{ margin-left: 60px; }}
</style>
</head>
<body>
<h1>Timeline: {title}</h1>
<div class="stats" id="stats"></div>
<div class="timeline" id="timeline"></div>
<script>
const DATA = {data_json};
const stats = DATA.reduce((acc, e) => {{
  acc[e.status] = (acc[e.status] || 0) + 1;
  return acc;
}}, {{}});
const total = DATA.length;
document.getElementById('stats').innerHTML = Object.entries({{
  'Total': total, 'Success': stats.success || 0,
  'Error': stats.error || 0, 'Warning': stats.warning || 0,
}}).map(([k,v]) => `<div class="stat"><div class="value">${{v}}</div><div class="name">${{k}}</div></div>`).join('');
document.getElementById('timeline').innerHTML = DATA.map(e =>
  `<div class="event ${{e.status}} depth-${{e.depth||0}}">
    <span class="time">${{new Date(e.timestamp*1000).toISOString().substr(11,8)}}</span>
    <span class="label">${{e.label}}</span>
    ${{e.duration_ms ? `<span class="duration">${{e.duration_ms.toFixed(0)}}ms</span>` : ''}}
    ${{e.detail ? `<div class="detail">${{e.detail}}</div>` : ''}}
  </div>`
).join('');
</script>
</body>
</html>"""

    if output_path:
        Path(output_path).write_text(html)
    return html
