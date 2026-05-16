import json
import sys
from pathlib import Path
from typing import Optional, List, TextIO
from dataclasses import dataclass, field
from enum import Enum

from .schema import SemanticDiff, DiffReport
from .renderer import SemanticDiffRenderer


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    CONSOLE = "console"


def _color(text: str, color_code: str) -> str:
    return f"\033[{color_code}m{text}\033[0m"


class DiffCLIExporter:
    def __init__(self, format: str = "console"):
        self.format = format

    def export(self, sd: SemanticDiff, report: Optional[DiffReport] = None,
               output_path: Optional[str] = None) -> Optional[str]:
        if self.format == "console":
            rendered = self._render_console(sd, report)
        else:
            renderer = SemanticDiffRenderer(format=self.format)
            rendered = renderer.render(sd, report)

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)
            print(f"Semantic diff exported to {output_path}", file=sys.stderr)
            return None

        return rendered

    def _render_console(self, sd: SemanticDiff, report: Optional[DiffReport] = None) -> str:
        d = sd.to_dict()
        lines = []

        lines.append(_color(f"═══ Semantic Diff: {sd.header.diff_id} ═══", "1;36"))
        lines.append(_color(f"  {d.get('summary', '')}", "37"))
        lines.append(f"  Confidence: {sd.confidence:.0%}")
        lines.append("")

        hdr = d.get("header", {})
        lines.append(_color("📋 Header", "1;33"))
        lines.append(f"  Repo: {hdr.get('repository', 'N/A')}  Branch: {hdr.get('branch', 'N/A')}")
        if hdr.get("source_commit"):
            lines.append(f"  {hdr.get('source_commit', '')[:12]}..{hdr.get('target_commit', '')[:12]}")
        lines.append("")

        changes = d.get("syntactic_changes", [])
        lines.append(_color(f"📄 Files Changed ({len(changes)})", "1;33"))
        for c in changes:
            scope = f" ({c.get('change_scope', '')})" if c.get("change_scope") else ""
            delta = f"+{c.get('lines_added', 0)}/-{c.get('lines_removed', 0)}"
            lines.append(f"  {c.get('file_path', '?')} [{delta}] {scope}")
        lines.append("")

        intent = d.get("behavioral_intent")
        if intent:
            lines.append(_color("🎯 Intent", "1;33"))
            lines.append(f"  Type: {intent.get('intent_type', '?')}")
            lines.append(f"  {intent.get('description', '')}")
            if not intent.get("backward_compatible", True):
                lines.append(_color("  ⚠ NOT backward compatible", "1;31"))
            lines.append("")

        risk = d.get("risk")
        if risk:
            risk_color = "1;31" if risk.get("overall") in ("high", "critical") else "1;33"
            lines.append(_color(f"⚠ Risk: {risk.get('overall', '?').upper()}", risk_color))
            lines.append(f"  Score: {risk.get('risk_score_numeric', 0):.2f}")
            for rf in risk.get("risk_factors", []):
                lines.append(_color(f"  • {rf}", "33"))
            lines.append("")

        ver = d.get("verification")
        if ver:
            status = ver.get("status", "?")
            color = "1;32" if status == "passed" else "1;31"
            lines.append(_color(f"🔬 Verification: {status.upper()}", color))
            if ver.get("tests_run", 0) > 0:
                lines.append(f"  Tests: {ver.get('tests_passed', 0)}/{ver.get('tests_run', 0)} passed")
            for gap in ver.get("verification_gaps", []):
                lines.append(_color(f"  ⚠ Gap: {gap}", "33"))
            lines.append("")

        if report:
            r = report.to_dict()
            action = r.get("recommended_action", "?")
            action_color = "1;32" if action == "approve" else ("1;33" if action == "review" else "1;31")
            lines.append(_color(f"🏁 Recommended: {action.upper()}", action_color))
            for issue in r.get("blocking_issues", []):
                lines.append(_color(f"  🚫 {issue}", "1;31"))
            for item in r.get("review_checklist", []):
                lines.append(f"  ☐ {item}")

        return "\n".join(lines)

    @classmethod
    def export_files(cls, diffs: List[SemanticDiff], output_dir: str, format: str = "json"):
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        for sd in diffs:
            exporter = cls(format=format)
            fname = f"semantic-diff-{sd.header.diff_id}.{format}"
            exporter.export(sd, output_path=str(path / fname))
        print(f"Exported {len(diffs)} semantic diffs to {output_dir}")
