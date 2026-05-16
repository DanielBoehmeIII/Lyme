from __future__ import annotations
from typing import Dict, List, Optional, Any, Set
import json


class EcosystemVisualization:
    def __init__(self, dependency_graph, stability_analyzer=None):
        self._graph = dependency_graph
        self._stability = stability_analyzer

    def to_dependency_graph_html(self, title: str = "Ecosystem Dependency Graph") -> str:
        nodes, edges = self._build_vis_data()
        return self._render_vis_html(title, nodes, edges)

    def to_d3_json(self) -> Dict:
        nodes, edges = self._build_vis_data()
        return {"nodes": nodes, "edges": edges}

    def _build_vis_data(self) -> tuple:
        nodes = []
        edges = []
        libs = self._graph.libraries if hasattr(self._graph, 'libraries') else []
        added_ids = set()

        for lib in libs:
            node_id = lib.id
            if node_id in added_ids:
                continue
            added_ids.add(node_id)
            phase_color = {
                "emerging": "#4CAF50",
                "growing": "#2196F3",
                "dominant": "#FF9800",
                "declining": "#f44336",
                "fragmenting": "#9C27B0",
                "niche": "#607D8B",
            }
            color = phase_color.get(getattr(lib, 'phase', None).value if hasattr(lib, 'phase') else "emerging", "#999")
            size = 10 + (getattr(lib, 'centrality', 0) * 20)

            nodes.append({
                "id": node_id,
                "label": getattr(lib, 'name', node_id),
                "group": getattr(lib, 'ecosystem', 'unknown'),
                "value": size,
                "color": color,
                "title": (f"{getattr(lib, 'name', '')}\n"
                          f"Version: {getattr(lib, 'version', '')}\n"
                          f"Phase: {getattr(lib, 'phase', None).value if hasattr(lib, 'phase') else 'unknown'}\n"
                          f"Centrality: {getattr(lib, 'centrality', 0):.2f}\n"
                          f"Adoption: {getattr(lib, 'adoption_rate', 0):.0%}"),
            })

        for e in (self._graph._edges.values() if hasattr(self._graph, '_edges') else []):
            if e.source_id in added_ids and e.target_id in added_ids:
                color = "#f44336" if getattr(e, 'is_conflicting', False) else "#4CAF50"
                edges.append({
                    "from": e.source_id,
                    "to": e.target_id,
                    "label": getattr(e, 'dep_type', None).value if hasattr(e, 'dep_type') else "depends",
                    "color": color,
                    "width": getattr(e, 'weight', 1) * 3,
                    "title": getattr(e, 'version_constraint', ''),
                })

        return nodes, edges

    def _render_vis_html(self, title: str, nodes: List[Dict], edges: List[Dict]) -> str:
        return f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<style>
  body {{ margin:0; background:#1a1a2e; color:#eee; font-family:sans-serif; }}
  #mynetwork {{ width:100vw; height:100vh; }}
  .controls {{ position:fixed; top:10px; left:10px; z-index:100; background:rgba(0,0,0,0.8); padding:10px; border-radius:8px; }}
  .title {{ position:fixed; top:10px; left:50%; transform:translateX(-50%); z-index:100; background:rgba(0,0,0,0.8); padding:8px 16px; border-radius:8px; font-size:14px; }}
</style>
</head><body>
<div class="title">{title} | {len(nodes)} packages</div>
<div id="mynetwork"></div>
<script src="https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js"></script>
<script>
const data = {json.dumps(nodes)};
const rels = {json.dumps(edges)};
const container = document.getElementById('mynetwork');
const networkData = {{
  nodes: new vis.DataSet(data.map(n => ({{
    id: n.id, label: n.label, group: n.group,
    value: n.value, color: n.color, title: n.title
  }}))),
  edges: new vis.DataSet(rels.map(e => ({{
    from: e.from, to: e.to, label: e.label,
    color: e.color, width: e.width, title: e.title,
    arrows: 'to', smooth: {{ type: 'curvedCW' }}
  }})))
}};
const options = {{
  physics: {{ solver: 'forceAtlas2Based', forceAtlas2Based: {{ gravitationalConstant: -40, centralGravity: 0.005, springLength: 200, springConstant: 0.02 }}, stabilization: {{ iterations: 200 }} }},
  edges: {{ smooth: {{ type: 'continuous' }} }},
  interaction: {{ hover: true, tooltipDelay: 200, navigationButtons: true, keyboard: true }},
  layout: {{ improvedLayout: true }}
}};
new vis.Network(container, networkData, options);
</script></body></html>"""

    def to_stability_heatmap_html(self) -> str:
        stability = self._stability.compute_stability() if self._stability else None
        if not stability:
            return "<html><body>No stability data</body></html>"

        metrics = stability.to_dict()
        bars = ""
        for key in ["package_stability", "dependency_stability", "community_health",
                     "release_consistency", "adoption_depth", "overall_score"]:
            val = metrics.get(key, 0)
            color = "#4CAF50" if val >= 0.7 else "#FF9800" if val >= 0.4 else "#f44336"
            bars += f"<div style='margin:8px 0'><span style='display:inline-block;width:200px'>{key.replace('_', ' ').title()}</span><div style='display:inline-block;width:300px;height:20px;background:#333;border-radius:10px;overflow:hidden'><div style='width:{val*100}%;height:100%;background:{color};border-radius:10px'></div></div><span style='margin-left:10px'>{val:.0%}</span></div>"

        signals_html = ""
        for s in metrics.get("signals", []):
            signals_html += f"<div style='margin:4px 0;padding:4px 8px;border-left:3px solid {'#f44336' if s['severity']=='high' else '#FF9800'}'>{s['description']}</div>"

        return f"""<!DOCTYPE html>
<html><head><title>Ecosystem Stability Heatmap</title>
<style>body{{background:#1a1a2e;color:#eee;font-family:sans-serif;padding:40px}}</style></head><body>
<h2>Ecosystem Stability Metrics</h2>
<p>Overall: <strong>{stability.level.value}</strong> ({metrics['overall_score']:.0%})</p>
{bars}
<h3>Signals</h3>
{signals_html or '<p>No significant signals detected</p>'}
</body></html>"""

    def to_fragmentation_html(self) -> str:
        fragments = self._graph.detect_ecosystem_fragmentation() if hasattr(self._graph, 'detect_ecosystem_fragmentation') else []
        if not fragments:
            return "<html><body>No fragmentation detected</body></html>"

        table = "<table border='1' style='border-collapse:collapse;width:100%'><tr><th>Size</th><th>Members</th><th>Avg Centrality</th><th>Isolated</th></tr>"
        for f in fragments[:30]:
            table += f"<tr><td>{f['size']}</td><td>{', '.join(f['members'][:5])}</td><td>{f['avg_centrality']}</td><td>{f['is_isolated']}</td></tr>"
        table += "</table>"

        return f"""<!DOCTYPE html>
<html><head><title>Ecosystem Fragmentation</title>
<style>body{{background:#1a1a2e;color:#eee;font-family:sans-serif;padding:40px}} table{{margin-top:20px}} th,td{{padding:8px;text-align:left}}</style></head><body>
<h2>Ecosystem Fragmentation Analysis</h2>
<p>Communities detected: {len(fragments)}</p>
{table}
</body></html>"""
