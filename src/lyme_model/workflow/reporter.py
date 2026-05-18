"""PRReporter — generates PR summaries, risk reports, and verification evidence."""

from __future__ import annotations
from pathlib import Path
from .models import PRResult


class PRReporter:
    """Generate human-readable reports from PR results."""

    def generate_full_report(self, result: PRResult) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"ISSUE → VERIFIED PR REPORT")
        lines.append("=" * 60)
        lines.append(f"  Ticket:     {result.ticket_id}")
        lines.append(f"  Title:      {result.title}")
        lines.append(f"  Branch:     {result.branch_name}")
        lines.append(f"  Duration:   {result.duration_s:.1f}s")
        lines.append(f"  Success:    {'✓' if result.success else '✗'}")
        lines.append(f"  PR URL:     {result.pr_url or 'N/A'}")
        lines.append("")

        lines.append("── Implementation Plan ──")
        plan = result.implementation_plan
        lines.append(f"  Summary: {plan.summary}")
        lines.append(f"  Difficulty: {plan.estimated_difficulty}")
        lines.append(f"  Steps ({len(plan.steps)}):")
        for s in plan.steps:
            icon = "✓" if s.completed else "○"
            lines.append(f"    {icon} [{s.risk}] {s.action} on {s.file}: {s.description}")

        lines.append("")
        lines.append("── Risk Report ──")
        risk = result.risk_report
        lines.append(f"  Overall: {risk.overall_risk.upper()} ({risk.risk_score})")
        for r in risk.risks:
            lines.append(f"  ⚠ {r['description']} [{r['risk']}]")
        if risk.mitigations:
            for m in risk.mitigations:
                lines.append(f"  → {m}")
        if risk.concerns:
            for c in risk.concerns:
                lines.append(f"  ! {c}")

        lines.append("")
        lines.append("── Verification Evidence ──")
        ver = result.verification
        lines.append(f"  Tests:  {'✓ PASS' if ver.tests_pass else '✗ FAIL'} — {ver.test_summary[:60]}")
        lines.append(f"  Lint:   {'✓ PASS' if ver.lint_pass else '✗ FAIL'}")
        for check in ver.manual_checks:
            icon = "✓" if check.get("passed") else "○"
            lines.append(f"  {icon} {check['check']}")
        if ver.evidence_log:
            lines.append(f"  Log ({len(ver.evidence_log)} entries):")
            for entry in ver.evidence_log[-5:]:
                lines.append(f"    • {entry}")

        lines.append("")
        lines.append("── Rollback Instructions ──")
        for inst in result.rollback_instructions:
            lines.append(f"  $ {inst}")

        if result.files_changed:
            lines.append("")
            lines.append("── Files Changed ──")
            for f in result.files_changed:
                lines.append(f"  • {f}")

        if result.errors:
            lines.append("")
            lines.append("── Errors ──")
            for e in result.errors:
                lines.append(f"  ✗ {e}")

        lines.append("")
        lines.append(f"── PR Summary ──")
        lines.append(result.pr_summary)

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def save_report(self, result: PRResult, path: str = "") -> Path:
        if not path:
            path = f".lyme/workflow/reports/pr-{result.ticket_id}.md"
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate_full_report(result)
        p.write_text(report)
        return p
