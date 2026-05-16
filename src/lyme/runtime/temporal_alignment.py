from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    EventSeverity,
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
)


@dataclass
class AlignedSegment:
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    event_ids: List[str] = field(default_factory=list)
    subsystem: str = ""
    event_type: str = ""
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "event_ids": self.event_ids,
            "subsystem": self.subsystem,
            "event_type": self.event_type,
            "error_count": self.error_count,
            "metadata": self.metadata,
        }


@dataclass
class ReconstructedTimeline:
    trace_id: str = ""
    segments: List[AlignedSegment] = field(default_factory=list)
    parallel_branches: List[List[AlignedSegment]] = field(default_factory=list)
    critical_path: List[str] = field(default_factory=list)
    time_compression_ratio: float = 1.0
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "segments": [s.to_dict() for s in self.segments],
            "parallel_branches": [
                [s.to_dict() for s in branch] for branch in self.parallel_branches
            ],
            "critical_path": self.critical_path,
            "time_compression_ratio": self.time_compression_ratio,
            "gaps": self.gaps,
            "total_duration_ms": self.total_duration_ms,
        }


class TemporalAligner:
    def __init__(self, max_gap_ms: float = 1000):
        self.max_gap_ms = max_gap_ms

    def align_by_timestamp(self, trace: RuntimeTrace) -> ReconstructedTimeline:
        sorted_events = sorted(trace.events, key=lambda e: e.timestamp)
        if not sorted_events:
            return ReconstructedTimeline(trace_id=trace.trace_id)

        total_duration = (sorted_events[-1].timestamp - sorted_events[0].timestamp) * 1000
        timeline = ReconstructedTimeline(
            trace_id=trace.trace_id,
            total_duration_ms=total_duration,
        )

        current_seg = AlignedSegment(
            start_time=sorted_events[0].timestamp,
            end_time=sorted_events[0].timestamp,
            subsystem=sorted_events[0].subsystem,
            event_type=sorted_events[0].event_type.value,
        )
        current_seg.event_ids.append(sorted_events[0].id)
        if sorted_events[0].severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
            current_seg.error_count += 1

        for i in range(1, len(sorted_events)):
            event = sorted_events[i]
            gap = (event.timestamp - current_seg.end_time) * 1000

            if gap <= self.max_gap_ms and event.subsystem == current_seg.subsystem:
                current_seg.end_time = event.timestamp
                current_seg.duration_ms = (current_seg.end_time - current_seg.start_time) * 1000
                current_seg.event_ids.append(event.id)
                if event.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
                    current_seg.error_count += 1
            else:
                if gap > self.max_gap_ms:
                    timeline.gaps.append({
                        "from_time": current_seg.end_time,
                        "to_time": event.timestamp,
                        "gap_ms": gap,
                        "from_event": current_seg.event_ids[-1] if current_seg.event_ids else "",
                        "to_event": event.id,
                    })
                current_seg.duration_ms = (current_seg.end_time - current_seg.start_time) * 1000
                timeline.segments.append(current_seg)
                current_seg = AlignedSegment(
                    start_time=event.timestamp,
                    end_time=event.timestamp,
                    subsystem=event.subsystem,
                    event_type=event.event_type.value,
                )
                current_seg.event_ids.append(event.id)
                if event.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
                    current_seg.error_count += 1

        current_seg.duration_ms = (current_seg.end_time - current_seg.start_time) * 1000
        timeline.segments.append(current_seg)

        timeline.critical_path = self._find_critical_path(timeline.segments, trace)
        timeline.parallel_branches = self._find_parallel_branches(timeline.segments)
        timeline.time_compression_ratio = self._compute_compression(timeline.segments, trace)

        return timeline

    def _find_critical_path(self, segments: List[AlignedSegment], trace: RuntimeTrace) -> List[str]:
        scored: List[Tuple[float, str]] = []
        for seg in segments:
            score = seg.duration_ms + seg.error_count * 1000
            scored.append((score, seg.event_ids[0] if seg.event_ids else ""))
        scored.sort(key=lambda x: -x[0])
        return [eid for _, eid in scored[:5] if eid]

    def _find_parallel_branches(self, segments: List[AlignedSegment]) -> List[List[AlignedSegment]]:
        if len(segments) < 2:
            return []
        branches: List[List[AlignedSegment]] = []
        current_branch = [segments[0]]
        for i in range(1, len(segments)):
            prev = segments[i - 1]
            curr = segments[i]
            overlap = prev.end_time > curr.start_time
            if overlap:
                current_branch.append(curr)
            else:
                if len(current_branch) > 1:
                    branches.append(current_branch)
                current_branch = [curr]
        if len(current_branch) > 1:
            branches.append(current_branch)
        return branches

    def _compute_compression(self, segments: List[AlignedSegment], trace: RuntimeTrace) -> float:
        if not trace.events or not segments:
            return 1.0
        raw_duration = (trace.events[-1].timestamp - trace.events[0].timestamp) * 1000
        aligned_duration = sum(s.duration_ms for s in segments)
        return aligned_duration / raw_duration if raw_duration > 0 else 1.0

    def align_by_subsystem(self, trace: RuntimeTrace) -> Dict[str, ReconstructedTimeline]:
        subsystem_events: Dict[str, List[RuntimeTraceEvent]] = defaultdict(list)
        for event in trace.events:
            if event.subsystem:
                subsystem_events[event.subsystem].append(event)

        timelines = {}
        for subsystem, events in subsystem_events.items():
            sub_trace = RuntimeTrace(
                trace_id=f"{trace.trace_id}_{subsystem}",
                name=f"{trace.name}/{subsystem}",
            )
            for e in events:
                sub_trace.add_event(e)
            timelines[subsystem] = self.align_by_timestamp(sub_trace)
        return timelines

    def align_by_event_type(self, trace: RuntimeTrace) -> Dict[RuntimeEventType, ReconstructedTimeline]:
        type_events: Dict[RuntimeEventType, List[RuntimeTraceEvent]] = defaultdict(list)
        for event in trace.events:
            type_events[event.event_type].append(event)

        timelines = {}
        for event_type, events in type_events.items():
            type_trace = RuntimeTrace(trace_id=f"{trace.trace_id}_{event_type.value}")
            for e in events:
                type_trace.add_event(e)
            timelines[event_type] = self.align_by_timestamp(type_trace)
        return timelines


class EventWindowAggregator:
    def __init__(self, window_ms: float = 1000):
        self.window_ms = window_ms

    def aggregate(self, events: List[RuntimeTraceEvent]) -> List[Dict[str, Any]]:
        if not events:
            return []
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        start_time = sorted_events[0].timestamp
        windows: List[Dict[str, Any]] = []
        current_window: List[RuntimeTraceEvent] = []
        window_start = start_time

        for event in sorted_events:
            if (event.timestamp - window_start) * 1000 <= self.window_ms:
                current_window.append(event)
            else:
                windows.append(self._summarize_window(current_window, window_start))
                window_start = event.timestamp
                current_window = [event]
        if current_window:
            windows.append(self._summarize_window(current_window, window_start))
        return windows

    def _summarize_window(self, events: List[RuntimeTraceEvent], start_time: float) -> Dict[str, Any]:
        error_count = sum(
            1 for e in events if e.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL)
        )
        type_counts: Dict[str, int] = defaultdict(int)
        subsystems: Set[str] = set()
        for e in events:
            type_counts[e.event_type.value] += 1
            if e.subsystem:
                subsystems.add(e.subsystem)

        return {
            "window_start": start_time,
            "window_end": events[-1].timestamp if events else start_time,
            "event_count": len(events),
            "error_count": error_count,
            "type_breakdown": dict(type_counts),
            "subsystems": list(subsystems),
            "dominant_type": max(type_counts, key=type_counts.get) if type_counts else "",
        }
