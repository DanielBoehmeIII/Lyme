import json
from typing import Optional
from .schema import SemanticDiff, DiffReport


class MarkdownRenderer:
    def render_semantic_diff(self, sd: SemanticDiff, report: Optional[DiffReport] = None) -> str:
        d = sd.to_dict()
        lines = []
        lines.append(f"# Semantic Diff: {sd.header.diff_id}")
        lines.append(f"")
        lines.append(f"**Summary**: {d.get('summary', '')}")
        lines.append(f"**Confidence**: {sd.confidence:.0%}")
        lines.append(f"")

        hdr = d.get("header", {})
        lines.append(f"## Header")
        lines.append(f"- Repository: {hdr.get('repository', 'N/A')}")
        lines.append(f"- Branch: {hdr.get('branch', 'N/A')}")
        lines.append(f"- Source: {hdr.get('source_commit', 'N/A')} → {hdr.get('target_commit', 'N/A')}")
        lines.append(f"- Author: {hdr.get('author', 'N/A')}")
        if hdr.get("pr_url"):
            lines.append(f"- PR: {hdr['pr_url']}")
        lines.append(f"")

        changes = d.get("syntactic_changes", [])
        lines.append(f"## Syntactic Changes ({len(changes)} files)")
        lines.append(f"")
        lines.append(f"| File | Type | + | - | Scope |")
        lines.append(f"|------|------|---|---|-------|")
        for c in changes:
            fn = c.get("function_name") or c.get("class_name") or ""
            lines.append(f"| {c.get('file_path', '?')} | {c.get('diff_type', '?')} | {c.get('lines_added', 0)} | {c.get('lines_removed', 0)} | {c.get('change_scope', '?')} {fn} |")
        lines.append(f"")

        intent = d.get("behavioral_intent")
        if intent:
            lines.append(f"## Behavioral Intent")
            lines.append(f"- Type: {intent.get('intent_type', '?')}")
            lines.append(f"- Description: {intent.get('description', '')}")
            lines.append(f"- Motivation: {intent.get('motivation', '')}")
            lines.append(f"- Expected: {intent.get('expected_behavior', '')}")
            lines.append(f"- Previous: {intent.get('previous_behavior', '')}")
            lines.append(f"- Backward compatible: {intent.get('backward_compatible', '?')}")
            if intent.get("affected_interfaces"):
                lines.append(f"- Affected interfaces: {', '.join(intent['affected_interfaces'])}")
            lines.append(f"")

        invariants = d.get("affected_invariants", [])
        if invariants:
            lines.append(f"## Affected Invariants ({len(invariants)})")
            lines.append(f"")
            for inv in invariants:
                lines.append(f"- **{inv.get('invariant_type', '?')}**: {inv.get('description', '')} (status: {inv.get('status', '?')}, confidence: {inv.get('confidence', 0):.0%})")
            lines.append(f"")

        arch = d.get("architectural_impact")
        if arch:
            lines.append(f"## Architectural Impact")
            lines.append(f"- Level: {arch.get('impact_level', '?')}")
            lines.append(f"- Subsystems: {', '.join(arch.get('affected_subsystems', ['none']))}")
            lines.append(f"- Coupling change: {arch.get('coupling_change', 0):+.2f}")
            lines.append(f"- Complexity delta: {arch.get('complexity_delta', 0):+d}")
            if arch.get("architecture_description"):
                lines.append(f"- Description: {arch['architecture_description']}")
            lines.append(f"")

        risk = d.get("risk")
        if risk:
            lines.append(f"## Risk Assessment")
            lines.append(f"- Overall: **{risk.get('overall', '?')}**")
            lines.append(f"- Regression: {risk.get('regression_risk', '?')}")
            lines.append(f"- Security: {risk.get('security_risk', '?')}")
            lines.append(f"- Performance: {risk.get('performance_risk', '?')}")
            lines.append(f"- Rollback difficulty: {risk.get('rollback_difficulty', '?')}")
            lines.append(f"- Score: {risk.get('risk_score_numeric', 0):.2f}")
            for rf in risk.get("risk_factors", []):
                lines.append(f"  - ⚠ {rf}")
            lines.append(f"")

        ver = d.get("verification")
        if ver:
            lines.append(f"## Verification")
            lines.append(f"- Status: **{ver.get('status', '?')}**")
            lines.append(f"- Tests: {ver.get('tests_passed', 0)}/{ver.get('tests_run', 0)} passed")
            if ver.get("coverage_percent") is not None:
                lines.append(f"- Coverage: {ver['coverage_percent']:.1f}%")
            lines.append(f"- Static analysis: {'✓' if ver.get('static_analysis_passed') else '✗'}")
            lines.append(f"- Type checks: {'✓' if ver.get('type_checks_passed') else '✗'}")
            for gap in ver.get("verification_gaps", []):
                lines.append(f"  - ⚠ Gap: {gap}")
            lines.append(f"")

        rollback = d.get("rollback")
        if rollback:
            lines.append(f"## Rollback Strategy")
            lines.append(f"- Strategy: {rollback.get('strategy', '?')}")
            lines.append(f"- Complexity: {rollback.get('complexity', '?')}")
            lines.append(f"- Est. time: {rollback.get('estimated_time_minutes', 0)} min")
            for step in rollback.get("steps", []):
                lines.append(f"  1. {step}")
            lines.append(f"")

        if report:
            r = report.to_dict()
            lines.append(f"## Review Notes")
            lines.append(f"- Recommended: **{r.get('recommended_action', '?')}**")
            for issue in r.get("blocking_issues", []):
                lines.append(f"  - 🚫 {issue}")
            for item in r.get("review_checklist", []):
                lines.append(f"  - ☐ {item}")
            if r.get("agent_notes"):
                lines.append(f"")
                lines.append(f"*{r['agent_notes']}*")

        return "\n".join(lines)


class JSONRenderer:
    def render_semantic_diff(self, sd: SemanticDiff, report: Optional[DiffReport] = None) -> str:
        if report:
            return json.dumps(report.to_dict(), indent=2, default=str)
        return sd.to_json()


class HTMLRenderer:
    def render_semantic_diff(self, sd: SemanticDiff, report: Optional[DiffReport] = None) -> str:
        md = MarkdownRenderer().render_semantic_diff(sd, report)
        import re
        html_lines = ["<!DOCTYPE html><html><head>",
                       '<meta charset="utf-8">',
                       "<title>Semantic Diff</title>",
                       "<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
                       "max-width:960px;margin:40px auto;padding:0 20px;line-height:1.6;color:#1a1a2e;"
                       "background:#f8f9fa}h1{color:#16213e}h2{color:#0f3460;border-bottom:2px solid #e2e8f0;"
                       "padding-bottom:4px}table{border-collapse:collapse;width:100%}"
                       "th,td{border:1px solid #e2e8f0;padding:8px 12px;text-align:left}"
                       "th{background:#e2e8f0}.risk-high{color:#e53e3e}.risk-medium{color:#dd6b20}"
                       "code{background:#edf2f7;padding:2px 6px;border-radius:3px}</style></head><body>",
                       "<div class='content'>"]

        current_section = ""
        for line in md.split("\n"):
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("| "):
                continue
            elif line.startswith("---"):
                continue
            elif line.startswith("  - ⚠"):
                html_lines.append(f'<div class="risk-medium">⚠ {line[5:]}</div>')
            elif line.startswith("  - 🚫"):
                html_lines.append(f'<div class="risk-high">🚫 {line[5:]}</div>')
            elif line.startswith("- "):
                text = line[2:]
                if "**" in text:
                    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
                html_lines.append(f"<p>{text}</p>")
            else:
                if line.strip():
                    html_lines.append(f"<p>{line}</p>")

        html_lines.append("</div></body></html>")
        return "\n".join(html_lines)


class SemanticDiffRenderer:
    def __init__(self, format: str = "markdown"):
        self.format = format
        self._renderers = {
            "markdown": MarkdownRenderer(),
            "json": JSONRenderer(),
            "html": HTMLRenderer(),
        }

    def render(self, sd: SemanticDiff, report: Optional[DiffReport] = None) -> str:
        renderer = self._renderers.get(self.format, self._renderers["markdown"])
        return renderer.render_semantic_diff(sd, report)
