"""TrialReplay — replay trials from saved results.

Replays show the step-by-step execution of a completed trial,
including commands run, files changed, and test results.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Optional


class TrialReplay:
    """Replay previous trial runs for inspection."""

    def __init__(self, output_dir: Path):
        self.trials_dir = output_dir / "trials"
        self.runs_dir = output_dir / "runs"

    def replay_trial(self, trial_id: str, output_format: str = "text") -> Optional[str]:
        path = self.trials_dir / f"{trial_id}.json"
        if not path.exists():
            runs = self.runs_dir / f"{trial_id}.json"
            if runs.exists():
                return self._replay_run(runs, output_format)
            return None

        data = json.loads(path.read_text())
        if output_format == "json":
            return json.dumps(data, indent=2)

        lines = []
        lines.append("=" * 60)
        lines.append(f"TRIAL REPLAY: {data.get('title', 'Unknown')}")
        lines.append("=" * 60)
        lines.append(f"  Trial ID:   {data.get('trial_id', 'N/A')}")
        lines.append(f"  Task ID:    {data.get('task_id', 'N/A')}")
        lines.append(f"  Status:     {data.get('status', 'N/A')}")
        lines.append(f"  Verdict:    {data.get('verdict', 'N/A')}")
        lines.append(f"  Score:      {data.get('score', 0)}")
        lines.append(f"  Duration:   {data.get('duration_s', 0):.1f}s")
        lines.append(f"  Timestamp:  {data.get('timestamp', 'N/A')}")
        lines.append("")

        commands = data.get("commands_run", [])
        lines.append(f"Commands Run ({len(commands)}):")
        for cmd in commands:
            status = "✓" if cmd.get("exit_code", -1) == 0 else "✗"
            lines.append(f"  {status} {cmd.get('command', '?')}")
            lines.append(f"     exit: {cmd.get('exit_code', '?')} | {cmd.get('duration_s', 0):.1f}s")
            stdout = cmd.get("stdout_preview", "")
            if stdout:
                lines.append(f"     stdout: {stdout[:120]}")
            stderr = cmd.get("stderr_preview", "")
            if stderr:
                lines.append(f"     stderr: {stderr[:120]}")

        files = data.get("files_touched", [])
        if files:
            lines.append(f"\nFiles Touched ({len(files)}):")
            for f in files:
                lines.append(f"  - {f}")

        changes = data.get("file_changes", [])
        if changes:
            lines.append(f"\nFile Changes ({len(changes)}):")
            for c in changes:
                lines.append(f"  {c.get('change_type', '?')}: {c.get('path', '?')} "
                             f"(+{c.get('lines_added', 0)}/-{c.get('lines_removed', 0)})")

        failures = data.get("failures", [])
        if failures:
            lines.append(f"\nFailures ({len(failures)}):")
            for f in failures:
                lines.append(f"  ✗ {f}")

        test_results = data.get("test_results", {})
        if test_results:
            lines.append(f"\nTest Results:")
            for phase, tr in test_results.items():
                if isinstance(tr, dict):
                    status = "✓" if tr.get("passed") else "✗"
                    lines.append(f"  {status} [{phase}] {tr.get('command', '?')}")
                    if tr.get("error"):
                        lines.append(f"     error: {tr['error']}")

        diff = data.get("final_diff", "")
        if diff:
            diff_lines = diff.strip().split("\n")
            lines.append(f"\nFinal Diff ({len(diff_lines)} lines):")
            for dl in diff_lines[:20]:
                lines.append(f"  {dl}")
            if len(diff_lines) > 20:
                lines.append(f"  ... ({len(diff_lines) - 20} more lines)")

        agent_log = data.get("agent_log", [])
        if agent_log:
            lines.append(f"\nAgent Log ({len(agent_log)} entries):")
            for entry in agent_log:
                lines.append(f"  {entry}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def _replay_run(self, path: Path, output_format: str) -> str:
        data = json.loads(path.read_text())
        if output_format == "json":
            return json.dumps(data, indent=2)
        lines = []
        summary = data.get("summary", {})
        lines.append("=" * 60)
        lines.append(f"RUN REPLAY: {data.get('run_id', 'Unknown')}")
        lines.append("=" * 60)
        lines.append(f"  Started:    {data.get('started_at', 'N/A')}")
        lines.append(f"  Completed:  {data.get('completed_at', 'N/A')}")
        lines.append(f"  Total:      {summary.get('total', 0)}")
        lines.append(f"  Passed:     {summary.get('passed', 0)}")
        lines.append(f"  Failed:     {summary.get('failed', 0)}")
        lines.append(f"  Pass Rate:  {summary.get('pass_rate', 0):.1%}")
        lines.append(f"  Avg Score:  {summary.get('avg_score', 0):.3f}")
        lines.append(f"  Duration:   {summary.get('total_duration_s', 0):.1f}s")
        lines.append("")
        for result in data.get("results", []):
            v = result.get("verdict", "?")
            icon = "✓" if v == "pass" else ("✗" if v == "fail" else "?")
            lines.append(f"  {icon} {result.get('title', '?')}")
            lines.append(f"     Score: {result.get('score', 0)} | {result.get('duration_s', 0):.1f}s | {result.get('status', '?')}")
        return "\n".join(lines)

    def list_replays(self) -> list[dict]:
        entries = []
        if self.trials_dir.exists():
            for path in self.trials_dir.glob("*.json"):
                data = json.loads(path.read_text())
                entries.append({
                    "id": data.get("trial_id", path.stem),
                    "type": "trial",
                    "title": data.get("title", ""),
                    "status": data.get("status", ""),
                    "timestamp": data.get("timestamp", ""),
                })
        if self.runs_dir.exists():
            for path in self.runs_dir.glob("*.json"):
                data = json.loads(path.read_text())
                summary = data.get("summary", {})
                entries.append({
                    "id": data.get("run_id", path.stem),
                    "type": "run",
                    "title": f"Run {data.get('run_id', path.stem)[:8]}",
                    "status": f"{summary.get('passed', 0)}/{summary.get('total', 0)} passed",
                    "timestamp": data.get("started_at", ""),
                })
        return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
