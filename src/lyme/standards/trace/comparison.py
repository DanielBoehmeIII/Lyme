import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from .schema import OpenAgentTrace, EventType


@dataclass
class TraceComparisonReport:
    trace_a_id: str = ""
    trace_b_id: str = ""
    total_events_a: int = 0
    total_events_b: int = 0
    duration_ms_a: float = 0.0
    duration_ms_b: float = 0.0
    agent_a: str = ""
    agent_b: str = ""
    event_overlap: Dict[str, int] = field(default_factory=dict)
    event_divergence: Dict[str, Dict[str, int]] = field(default_factory=dict)
    sequence_deviation: float = 0.0
    efficiency_ratio: float = 0.0
    error_count_a: int = 0
    error_count_b: int = 0
    tool_usage_diff: Dict[str, Dict[str, int]] = field(default_factory=dict)
    file_edit_overlap: List[str] = field(default_factory=list)
    files_only_in_a: List[str] = field(default_factory=list)
    files_only_in_b: List[str] = field(default_factory=list)
    confidence_trajectory_a: List[float] = field(default_factory=list)
    confidence_trajectory_b: List[float] = field(default_factory=list)
    intervention_count_a: int = 0
    intervention_count_b: int = 0
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class TraceComparer:
    def __init__(self):
        self._comparisons = 0

    def compare(self, trace_a: OpenAgentTrace, trace_b: OpenAgentTrace) -> TraceComparisonReport:
        self._comparisons += 1

        events_a = trace_a.events
        events_b = trace_b.events

        type_counts_a = self._count_by_type(events_a)
        type_counts_b = self._count_by_type(events_b)

        overlap = {}
        divergence = {}
        all_types = set(type_counts_a.keys()) | set(type_counts_b.keys())
        for t in all_types:
            ca = type_counts_a.get(t, 0)
            cb = type_counts_b.get(t, 0)
            overlap[t] = min(ca, cb)
            if ca != cb:
                divergence[t] = {"a_only": max(0, ca - cb), "b_only": max(0, cb - ca)}

        tool_usage = self._compare_tool_usage(events_a, events_b)
        files_a = self._get_edited_files(events_a)
        files_b = self._get_edited_files(events_b)
        file_overlap = list(set(files_a) & set(files_b))
        files_only_a = list(set(files_a) - set(files_b))
        files_only_b = list(set(files_b) - set(files_a))

        seq_dev = self._compute_sequence_deviation(events_a, events_b)
        eff_ratio = self._compute_efficiency(trace_a, trace_b)
        errors_a = sum(1 for e in events_a if e.get("status") == "error")
        errors_b = sum(1 for e in events_b if e.get("status") == "error")

        report = TraceComparisonReport(
            trace_a_id=trace_a.header.trace_id,
            trace_b_id=trace_b.header.trace_id,
            total_events_a=len(events_a),
            total_events_b=len(events_b),
            duration_ms_a=trace_a.header.duration_ms,
            duration_ms_b=trace_b.header.duration_ms,
            agent_a=trace_a.header.agent.name,
            agent_b=trace_b.header.agent.name,
            event_overlap=overlap,
            event_divergence=divergence,
            sequence_deviation=seq_dev,
            efficiency_ratio=eff_ratio,
            error_count_a=errors_a,
            error_count_b=errors_b,
            tool_usage_diff=tool_usage,
            file_edit_overlap=file_overlap,
            files_only_in_a=files_only_a,
            files_only_in_b=files_only_b,
            intervention_count_a=sum(1 for e in events_a if e.get("type") == EventType.HUMAN_INTERVENTION),
            intervention_count_b=sum(1 for e in events_b if e.get("type") == EventType.HUMAN_INTERVENTION),
        )

        report.summary = self._generate_summary(report)
        return report

    def _count_by_type(self, events: List[dict]) -> Dict[str, int]:
        counts = {}
        for e in events:
            t = e.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    def _compare_tool_usage(self, events_a: List[dict], events_b: List[dict]) -> dict:
        def _tool_counts(events):
            counts = {}
            for e in events:
                if e.get("type") == EventType.TOOL_CALL:
                    name = e.get("tool_name", "unknown")
                    counts[name] = counts.get(name, 0) + 1
            return counts

        ta = _tool_counts(events_a)
        tb = _tool_counts(events_b)
        result = {}
        all_tools = set(ta.keys()) | set(tb.keys())
        for tool in sorted(all_tools):
            result[tool] = {"a": ta.get(tool, 0), "b": tb.get(tool, 0)}
        return result

    def _get_edited_files(self, events: List[dict]) -> List[str]:
        files = set()
        for e in events:
            if e.get("type") == EventType.FILE_EDIT:
                fp = e.get("file_path", "")
                if fp:
                    files.add(fp)
        return sorted(files)

    def _compute_sequence_deviation(self, events_a: List[dict], events_b: List[dict]) -> float:
        type_seq_a = [e.get("type", "") for e in events_a]
        type_seq_b = [e.get("type", "") for e in events_b]
        max_len = max(len(type_seq_a), len(type_seq_b))
        if max_len == 0:
            return 0.0
        diffs = 0
        for i in range(min(len(type_seq_a), len(type_seq_b))):
            if type_seq_a[i] != type_seq_b[i]:
                diffs += 1
        diffs += abs(len(type_seq_a) - len(type_seq_b)) * 0.5
        return round(diffs / max_len, 4)

    def _compute_efficiency(self, trace_a: OpenAgentTrace, trace_b: OpenAgentTrace) -> float:
        dur_a = trace_a.header.duration_ms or 1
        dur_b = trace_b.header.duration_ms or 1
        events_a = len(trace_a.events) or 1
        events_b = len(trace_b.events) or 1
        rate_a = events_a / dur_a
        rate_b = events_b / dur_b
        if rate_b == 0:
            return float("inf")
        return round(rate_a / rate_b, 4)

    def _generate_summary(self, r: TraceComparisonReport) -> str:
        parts = [
            f"Trace Comparison: {r.agent_a} vs {r.agent_b}",
            f"  Events: {r.total_events_a} vs {r.total_events_b}",
            f"  Duration: {r.duration_ms_a:.0f}ms vs {r.duration_ms_b:.0f}ms",
            f"  Efficiency ratio: {r.efficiency_ratio:.2f}x",
            f"  Sequence deviation: {r.sequence_deviation:.2%}",
            f"  Errors: {r.error_count_a} vs {r.error_count_b}",
            f"  Interventions: {r.intervention_count_a} vs {r.intervention_count_b}",
        ]
        if r.event_divergence:
            parts.append("  Type divergences:")
            for t, v in sorted(r.event_divergence.items()):
                parts.append(f"    {t}: A+{v.get('a_only', 0)} B+{v.get('b_only', 0)}")
        if r.files_only_in_a or r.files_only_in_b:
            parts.append("  File edits:")
            if r.file_edit_overlap:
                parts.append(f"    Shared: {len(r.file_edit_overlap)} files")
            if r.files_only_in_a:
                parts.append(f"    Only in A: {len(r.files_only_in_a)} files")
            if r.files_only_in_b:
                parts.append(f"    Only in B: {len(r.files_only_in_b)} files")
        return "\n".join(parts)

    def to_dict(self, report: TraceComparisonReport) -> dict:
        return report.to_dict()

    def to_json(self, report: TraceComparisonReport, indent: int = 2) -> str:
        return json.dumps(report.to_dict(), indent=indent, default=str)

    def compare_files(self, path_a: str, path_b: str) -> TraceComparisonReport:
        with open(path_a) as f:
            trace_a = OpenAgentTrace.from_dict(json.load(f))
        with open(path_b) as f:
            trace_b = OpenAgentTrace.from_dict(json.load(f))
        return self.compare(trace_a, trace_b)
