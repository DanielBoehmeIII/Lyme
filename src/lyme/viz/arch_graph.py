"""ArchitectureGraph — Mermaid-based architecture visualization."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArchGraphConfig:
    title: str = "Architecture Graph"
    direction: str = "LR"


class ArchitectureGraph:
    def __init__(self, config: ArchGraphConfig = None):
        self.config = config or ArchGraphConfig()

    def mermaid(self, subsystems: Dict[str, List[str]]) -> str:
        lines = [f"graph {self.config.direction}"]
        for sub, deps in subsystems.items():
            clean = sub.replace(" ", "_").replace("-", "_")
            for dep in deps:
                dep_clean = dep.replace(" ", "_").replace("-", "_")
                lines.append(f"  {clean} --> {dep_clean}")
        return "\n".join(lines)

    def html(self, subsystems: Dict[str, List[str]]) -> str:
        mmd = self.mermaid(subsystems)
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{self.config.title}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:20px}}
h1{{color:#58a6ff}}</style></head><body>
<h1>{self.config.title}</h1>
<pre class="mermaid">{mmd}</pre>
<script>mermaid.initialize({{theme:'dark'}});</script>
</body></html>"""

    def render(self, subsystems: Dict[str, List[str]]) -> str:
        return self.html(subsystems)
