from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime, timezone


@dataclass
class BenchmarkReport:
    title: str = ""
    run_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_name: str = ""
    scenario_name: str = ""
    summary: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    spans_count: int = 0
    events_count: int = 0
    total_duration_ms: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    tool_calls_count: int = 0
    retries_count: int = 0
    errors_count: int = 0
    hallucinations_detected: int = 0
    diff_files_changed: int = 0
    success: bool = False
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "scenario_name": self.scenario_name,
            "summary": self.summary,
            "metrics": self.metrics,
            "spans_count": self.spans_count,
            "events_count": self.events_count,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "tool_calls_count": self.tool_calls_count,
            "retries_count": self.retries_count,
            "errors_count": self.errors_count,
            "hallucinations_detected": self.hallucinations_detected,
            "diff_files_changed": self.diff_files_changed,
            "success": self.success,
            "tags": self.tags,
        }


class StructuredOutput:
    @staticmethod
    def report_to_markdown(report: BenchmarkReport) -> str:
        lines = [
            f"# {report.title}",
            f"",
            f"- **Run ID**: {report.run_id}",
            f"- **Agent**: {report.agent_name}",
            f"- **Scenario**: {report.scenario_name}",
            f"- **Timestamp**: {report.timestamp}",
            f"- **Duration**: {report.total_duration_ms:.1f}ms",
            f"- **Success**: {report.success}",
            f"",
            f"## Summary",
            f"",
        ]
        for k, v in report.summary.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")
        lines.append("## Metrics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        for k, v in report.metrics.items():
            if isinstance(v, float):
                lines.append(f"| {k} | {v:.3f} |")
            else:
                lines.append(f"| {k} | {v} |")
        lines.append("")
        lines.append(f"## Statistics")
        lines.append(f"")
        lines.append(f"- Total Spans: {report.spans_count}")
        lines.append(f"- Total Events: {report.events_count}")
        lines.append(f"- Tool Calls: {report.tool_calls_count}")
        lines.append(f"- Retries: {report.retries_count}")
        lines.append(f"- Errors: {report.errors_count}")
        lines.append(f"- Hallucinations: {report.hallucinations_detected}")
        lines.append(f"- Files Changed: {report.diff_files_changed}")
        lines.append(f"- Input Tokens: {report.total_tokens_input:,}")
        lines.append(f"- Output Tokens: {report.total_tokens_output:,}")
        return "\n".join(lines)

    @staticmethod
    def metrics_to_csv(metrics: dict) -> str:
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["metric", "value"])
        for k, v in metrics.items():
            writer.writerow([k, v])
        return buf.getvalue()
