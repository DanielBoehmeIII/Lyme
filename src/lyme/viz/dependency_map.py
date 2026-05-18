"""DependencyMap — interactive HTML dependency visualization."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DependencyMapConfig:
    title: str = "Dependency Map"
    width: int = 900
    height: int = 600
    show_cycles: bool = True
    group_by_directory: bool = True


HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
*{{margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:20px}}
h1{{color:#58a6ff;margin-bottom:16px}}
svg{{background:#161b22;border-radius:8px}}
.node circle{{fill:#58a6ff;stroke:#1f6feb;stroke-width:2}}
.node text{{fill:#c9d1d9;font-size:10px}}
.edge line{{stroke:#30363d;stroke-width:1.5}}
.edge.cycle line{{stroke:#f85149;stroke-width:2;stroke-dasharray:5,3}}
</style></head><body>
<h1>{title}</h1>
<div id="viz"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = {graph_json};
const width = {width}, height = {height};
const svg = d3.select("#viz").append("svg").attr("width",width).attr("height",height);
const simulation = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.edges).id(d=>d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(width/2, height/2));
const link = svg.append("g").selectAll("line").data(data.edges).join("line")
  .attr("stroke",d=>d.cycle?"#f85149":"#30363d").attr("stroke-width",1.5).attr("stroke-dasharray",d=>d.cycle?"5,3":"none");
const node = svg.append("g").selectAll("circle").data(data.nodes).join("circle")
  .attr("r",d=>d.size||5).attr("fill","#58a6ff").call(drag(simulation));
node.append("title").text(d=>d.id);
simulation.on("tick",()=>{{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("cx",d=>d.x).attr("cy",d=>d.y);
}});
function drag(sim){{return d3.drag().on("start",(e,d)=>{{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}})
  .on("drag",(e,d)=>{{d.fx=e.x;d.fy=e.y;}}).on("end",(e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}});}}
</script></body></html>"""


class DependencyMap:
    def __init__(self, config: DependencyMapConfig = None):
        self.config = config or DependencyMapConfig()

    def generate(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        graph_data = {
            "nodes": [{"id": n.get("id", n.get("file_path", f"node_{i}")),
                       "size": n.get("size", 5)}
                      for i, n in enumerate(nodes)],
            "edges": [{"source": e.get("source", ""), "target": e.get("target", ""),
                       "cycle": e.get("cycle", False)}
                      for e in edges],
        }
        return HTML_TEMPLATE.format(
            title=self.config.title,
            width=self.config.width,
            height=self.config.height,
            graph_json=str(graph_data).replace("'", '"'),
        )
