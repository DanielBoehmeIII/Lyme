"""TrialReport — generates reports from trial results.

Produces:
- Per-trial reports (JSON + text)
- Run summary reports
- Cross-run comparison reports
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TrialRun, TrialResult, Verdict


class TrialReport:
    """Generate reports from trial results."""

    def __init__(self, output_dir: str = ".lyme/trials"):
        self.output_dir = Path(output_dir)
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_trial_report(self, result: TrialResult) -> str:
        verdict_str = result.verdict.value if result.verdict else "unknown"
        lines = []
        lines.append("=" * 60)
        lines.append(f"TRIAL REPORT: {result.title}")
        lines.append("=" * 60)
        lines.append(f"  Trial ID:    {result.trial_id}")
        lines.append(f"  Task ID:     {result.task_id}")
        lines.append(f"  Status:      {result.status.value}")
        lines.append(f"  Verdict:     {verdict_str.upper()}")
        lines.append(f"  Score:       {result.score:.4f}")
        lines.append(f"  Duration:    {result.duration_s:.1f}s")
        lines.append(f"  Timestamp:   {result.timestamp}")

        lines.append(f"\n── Files Touched ({len(result.files_touched)}) ──")
        for f in result.files_touched:
            lines.append(f"  • {f}")

        lines.append(f"\n── File Changes ({len(result.file_changes)}) ──")
        for fc in result.file_changes:
            lines.append(f"  {fc.change_type}: {fc.path} (+{fc.lines_added}/-{fc.lines_removed})")

        lines.append(f"\n── Commands Run ({len(result.commands_run)}) ──")
        for cmd in result.commands_run:
            icon = "✓" if cmd.exit_code == 0 else "✗"
            lines.append(f"  {icon} {cmd.command}")
            lines.append(f"     exit={cmd.exit_code} duration={cmd.duration_s:.1f}s")

        if result.failures:
            lines.append(f"\n── Failures ({len(result.failures)}) ──")
            for f in result.failures:
                lines.append(f"  ✗ {f}")

        lines.append(f"\n── Test Results ──")
        for phase, tr in result.test_results.items():
            if isinstance(tr, dict):
                passed = tr.get("passed", False)
                icon = "✓" if passed else "✗"
                lines.append(f"  {icon} [{phase}] {tr.get('command', '?')}: "
                             f"{'PASSED' if passed else 'FAILED'}")
                if tr.get("error"):
                    lines.append(f"     error: {tr['error']}")

        diff = result.final_diff
        if diff:
            dlines = diff.strip().split("\n")
            lines.append(f"\n── Final Diff ({len(dlines)} lines) ──")
            for dl in dlines[:30]:
                lines.append(f"  {dl}")
            if len(dlines) > 30:
                lines.append(f"  ... ({len(dlines) - 30} more lines)")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def generate_summary_report(self, run: TrialRun) -> str:
        summary = run.compute_summary()
        lines = []
        lines.append("=" * 60)
        lines.append(f"TRIAL RUN SUMMARY: {run.run_id}")
        lines.append("=" * 60)
        lines.append(f"  Started:    {run.started_at}")
        lines.append(f"  Completed:  {summary.get('completed_at', 'N/A')}")
        lines.append(f"  Total:      {summary['total']}")
        lines.append(f"  Passed:     {summary['passed']}")
        lines.append(f"  Failed:     {summary['failed']}")
        lines.append(f"  Ambiguous:  {summary['ambiguous']}")
        lines.append(f"  Pass Rate:  {summary['pass_rate']:.1%}")
        lines.append(f"  Avg Score:  {summary['avg_score']:.4f}")
        lines.append(f"  Duration:   {summary['total_duration_s']:.1f}s")

        by_type = summary.get("by_type", {})
        if by_type:
            lines.append(f"\n── By Task Type ──")
            for ttype, data in sorted(by_type.items()):
                rate = data["passed"] / max(data["total"], 1)
                lines.append(f"  {ttype}: {data['passed']}/{data['total']} ({rate:.0%})")

        lines.append(f"\n── Results ──")
        for r in run.results:
            v = r.verdict.value if r.verdict else "?"
            icon = "✓" if v == "pass" else ("✗" if v == "fail" else "~")
            lines.append(f"  {icon} {r.title[:60]:60s} {r.score:.3f}  {v.upper()}")
            if r.error:
                lines.append(f"     ERROR: {r.error[:80]}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def generate_comparison_report(self, run_ids: list[str]) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("TRIAL COMPARISON REPORT")
        lines.append("=" * 60)

        all_results = []
        for run_id in run_ids:
            path = self.output_dir / "runs" / f"{run_id}.json"
            if path.exists():
                data = json.loads(path.read_text())
                all_results.append(data)

        if not all_results:
            return "No runs found for comparison."

        line = f"{'Metric':<30s}"
        for r in all_results:
            rid = r.get("run_id", "?")[:8]
            line += f"{rid:>12s}"
        lines.append(f"\n{line}")
        lines.append("-" * (30 + 12 * len(all_results)))

        metrics = ["total", "passed", "failed", "pass_rate", "avg_score"]
        for metric in metrics:
            line = f"{metric:<30s}"
            for r in all_results:
                summary = r.get("summary", {})
                val = summary.get(metric, "N/A")
                if isinstance(val, float):
                    line += f"{val:>12.4f}"
                else:
                    line += f"{str(val):>12s}"
            lines.append(line)

        lines.append(f"\n── Detailed Comparison ──")
        task_results: dict[str, list] = {}
        for r in all_results:
            for tr in r.get("results", []):
                tid = tr.get("task_id", "?")
                if tid not in task_results:
                    task_results[tid] = []
                task_results[tid].append(tr)

        for task_id, results in sorted(task_results.items()):
            title = results[0].get("title", "?")[:40] if results else "?"
            scores = [r.get("score", 0) for r in results]
            verdicts = [r.get("verdict", "?") for r in results]
            line = f"  {title:<40s}"
            for s, v in zip(scores, verdicts):
                line += f"{s:.3f}/{v:<5s}  "
            lines.append(line)

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def save_report(self, content: str, report_type: str, report_id: str) -> Path:
        path = self.reports_dir / f"{report_type}-{report_id}.txt"
        path.write_text(content)
        return path

    def export_json_report(self, data: dict, report_id: str) -> Path:
        path = self.reports_dir / f"json-{report_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return path
