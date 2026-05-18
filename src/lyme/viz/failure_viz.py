"""FailureVisualizer — visualizes failure patterns and root causes."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FailureVizConfig:
    title: str = "Failure Analysis"
    max_items: int = 20


HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
*{{margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:20px}}
h1{{color:#58a6ff;margin-bottom:16px}}
.bar{{display:flex;align-items:center;margin:4px 0}}
.bar-fill{{height:24px;border-radius:4px;min-width:4px}}
.bar-label{{width:200px;color:#8b949e;font-size:12px;text-align:right;padding-right:12px}}
.bar-value{{color:#c9d1d9;font-size:12px;padding-left:8px}}
</style></head><body>
<h1>{title}</h1>
{bars}
</body></html>"""


class FailureVisualizer:
    def __init__(self, config: FailureVizConfig = None):
        self.config = config or FailureVizConfig()

    def generate(self, failure_counts: Dict[str, int]) -> str:
        items = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        max_count = max(c for _, c in items) if items else 1
        bars = []
        colors = ["#f85149", "#d29922", "#58a6ff", "#3fb950", "#8b949e"]

        for i, (label, count) in enumerate(items[:self.config.max_items]):
            pct = count / max_count
            color = colors[i % len(colors)]
            bars.append(
                f'<div class="bar">'
                f'<div class="bar-label">{label}</div>'
                f'<div class="bar-fill" style="width:{pct * 300:.0f}px;background:{color}"></div>'
                f'<div class="bar-value">{count}</div>'
                f'</div>'
            )

        return HTML.format(title=self.config.title, bars="\n".join(bars))
