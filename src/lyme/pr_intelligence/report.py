import json
import time
from typing import Optional
from .analyzer import PRIntelligenceReport, PRAnalyzer
from .github_client import GitHubPRClient, GitHubPRData


class PRReportGenerator:
    def __init__(self, github_token: Optional[str] = None):
        self.client = GitHubPRClient(github_token)
        self.analyzer = PRAnalyzer()

    def analyze_pr(self, repo: str, pr_number: int) -> Optional[PRIntelligenceReport]:
        pr_data = self.client.fetch_pr(repo, pr_number)
        if not pr_data:
            return None
        report = self.analyzer.analyze(pr_data.to_dict())

        report.trace_export = self._build_trace(report, pr_data)
        return report

    def generate_markdown(self, report: PRIntelligenceReport) -> str:
        r = report.to_dict()
        lines = []
        lines.append(f"# PR Intelligence Report: #{r['pr_number']} - {r['pr_title']}")
        lines.append(f"")
        lines.append(f"- **Repository**: {r['repository']}")
        lines.append(f"- **Branch**: {r['branch']}")
        lines.append(f"- **Author**: {r['author']}")
        if r.get("pr_url"):
            lines.append(f"- **URL**: {r['pr_url']}")
        lines.append(f"")

        risk = r.get("risk_score", {})
        lines.append(f"## Risk Score: {risk.get('score', 0):.2f} ({risk.get('overall', 'unknown')})")
        for f in risk.get("factors", []):
            lines.append(f"- ⚠ {f}")
        lines.append(f"")

        violations = r.get("invariant_violations", [])
        if violations:
            lines.append(f"## Invariant Violations ({len(violations)})")
            for v in violations:
                lines.append(f"- **{v.get('invariant_type', '?')}**: {v.get('description', '')} "
                             f"(severity: {v.get('severity', '?')}, confidence: {v.get('confidence', 0):.0%})")
            lines.append(f"")

        zones = r.get("risk_zones", [])
        if zones:
            lines.append(f"## Risk Zones ({len(zones)})")
            for z in zones:
                lines.append(f"- **{z.get('file_path', '?')}**: {z.get('description', '')} "
                             f"(level: {z.get('risk_level', '?')})")
            lines.append(f"")

        gaps = r.get("test_gaps", [])
        if gaps:
            lines.append(f"## Test Gaps ({len(gaps)})")
            for g in gaps:
                lines.append(f"- **{g.get('area', '?')}**: {g.get('description', '')} ({g.get('gap_type', '?')})")
            lines.append(f"")

        evidence = r.get("missing_evidence", [])
        if evidence:
            lines.append(f"## Missing Evidence ({len(evidence)})")
            for e in evidence:
                lines.append(f"- **{e.get('claim', '?')}**: needs {e.get('evidence_needed', '?')}")
            lines.append(f"")

        checklist = r.get("verification_checklist", {})
        items = checklist.get("items", [])
        if items:
            lines.append(f"## Verification Checklist")
            for item in items:
                status_symbol = {"done": "✓", "pass": "✓", "fail": "✗", "warn": "⚠", "pending": "○"}
                sym = status_symbol.get(item.get("status", "pending"), "○")
                lines.append(f"- {sym} {item['check']}")
            lines.append(f"")

        summary = r.get("review_summary", {})
        lines.append(f"## Review Summary")
        lines.append(f"**Verdict**: {summary.get('verdict', 'unknown')}")
        lines.append(f"{summary.get('summary', '')}")
        lines.append(f"")

        focus = r.get("suggested_focus", {})
        if focus:
            lines.append(f"## Suggested Reviewer Focus")
            lines.append(f"- **Focus**: {focus.get('primary_focus', '')}")
            if focus.get("files_to_review"):
                lines.append(f"- **Files**: {', '.join(focus['files_to_review'])}")
            if focus.get("expertise_needed"):
                lines.append(f"- **Expertise**: {', '.join(focus['expertise_needed'])}")

        rd = r.get("rollback_difficulty", {})
        if rd:
            lines.append(f"")
            lines.append(f"## Rollback Strategy")
            lines.append(f"- **Level**: {rd.get('level', '?')}")
            lines.append(f"- **Strategy**: {rd.get('strategy', '?')}")
            lines.append(f"- **Est. time**: {rd.get('estimated_time_minutes', 0)} min")
            for step in rd.get("steps", []):
                lines.append(f"  1. {step}")

        return "\n".join(lines)

    def _build_trace(self, report: PRIntelligenceReport, pr_data: GitHubPRData) -> dict:
        return {
            "trace_id": f"pr-analyze-{report.pr_number}-{int(time.time())}",
            "schema": "open-agent-trace-standard",
            "schema_version": "0.7.0",
            "pr_number": report.pr_number,
            "repository": report.repository,
            "analysis_summary": report.review_summary.get("summary", "") if report.review_summary else "",
            "risk_score": report.risk_score.get("score", 0) if report.risk_score else 0,
            "risk_level": report.risk_score.get("overall", "unknown") if report.risk_score else "unknown",
            "invariant_violations": len(report.invariant_violations),
            "risk_zones": len(report.risk_zones),
            "test_gaps": len(report.test_gaps),
            "generated_at": report.generated_at,
        }

    def to_json(self, report: PRIntelligenceReport, indent: int = 2) -> str:
        return json.dumps(report.to_dict(), indent=indent, default=str)

    def print_console(self, report: PRIntelligenceReport):
        r = report.to_dict()
        risk = r.get("risk_score", {})
        summary = r.get("review_summary", {})

        print(f"\n{'='*60}")
        print(f"PR #{r['pr_number']}: {r['pr_title']}")
        print(f"{'='*60}")
        print(f"Risk: {risk.get('score', 0):.2f} ({risk.get('overall', 'unknown')})")
        print(f"Verdict: {summary.get('verdict', 'unknown')}")
        print(f"Issues: {len(r.get('invariant_violations', []))} violations, "
              f"{len(r.get('risk_zones', []))} risk zones, "
              f"{len(r.get('test_gaps', []))} test gaps")
        print(f"{'='*60}\n")
