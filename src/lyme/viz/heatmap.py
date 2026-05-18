"""EditHeatmap — visual heatmap of edit frequency across the codebase."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HeatmapConfig:
    title: str = "Edit Heatmap"
    max_files: int = 50


HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
*{{margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:20px}}
h1{{color:#58a6ff;margin-bottom:16px}}
.cell{{display:inline-block;width:16px;height:16px;margin:1px;border-radius:2px;cursor:pointer}}
.cell:hover{{outline:2px solid #58a6ff}}
.legend{{margin:10px 0;display:flex;gap:4px;align-items:center}}
.legend-item{{width:16px;height:16px;border-radius:2px}}
.label{{color:#8b949e;font-size:12px;margin:2px}}
</style></head><body>
<h1>{title}</h1>
<div class="legend">
  <span class="label">Less</span>
  <div class="legend-item" style="background:#0e4429"></div>
  <div class="legend-item" style="background:#006d32"></div>
  <div class="legend-item" style="background:#26a641"></div>
  <div class="legend-item" style="background:#39d353"></div>
  <span class="label">More</span>
</div>
<div id="heatmap">{cells}</div>
</body></html>"""


class EditHeatmap:
    def __init__(self, config: HeatmapConfig = None):
        self.config = config or HeatmapConfig()

    def generate(self, file_edits: Dict[str, int]) -> str:
        sorted_files = sorted(file_edits.items(), key=lambda x: x[1], reverse=True)
        if self.config.max_files:
            sorted_files = sorted_files[:self.config.max_files]

        max_count = max(c for _, c in sorted_files) if sorted_files else 1
        cells = []
        for i, (fp, count) in enumerate(sorted_files):
            intensity = count / max(max_count, 1)
            r, g = self._color(intensity)
            cells.append(
                f'<div class="cell" style="background:#{r:02x}{g:02x}00" '
                f'title="{fp}: {count} edits"></div>'
            )
            if (i + 1) % 10 == 0:
                cells.append("<br>")

        return HTML.format(title=self.config.title, cells="\n".join(cells))

    def _color(self, intensity: float) -> tuple:
        g = int(50 + 150 * intensity)
        return (14, min(g, 211))
