from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    CorrelationConfidence,
    EventSeverity,
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
)


@dataclass
class CorrelationLink:
    source_event_id: str = ""
    target_event_id: str = ""
    relation: str = ""
    confidence: CorrelationConfidence = CorrelationConfidence.MEDIUM
    evidence: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "source_event_id": self.source_event_id,
            "target_event_id": self.target_event_id,
            "relation": self.relation,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "latency_ms": self.latency_ms,
        }


@dataclass
class CorrelationResult:
    trace_id: str = ""
    links: List[CorrelationLink] = field(default_factory=list)
    clusters: Dict[str, List[str]] = field(default_factory=dict)
    root_causes: List[str] = field(default_factory=list)
    propagation_paths: List[List[str]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "links": [l.to_dict() for l in self.links],
            "clusters": self.clusters,
            "root_causes": self.root_causes,
            "propagation_paths": self.propagation_paths,
            "summary": self.summary,
        }


class CorrelationEngine:
    def __init__(self):
        self._source_map: Dict[str, Dict[str, List[RuntimeTraceEvent]]] = defaultdict(lambda: defaultdict(list))

    def index_events(self, trace: RuntimeTrace):
        for event in trace.events:
            if event.source_file:
                self._source_map["file"][event.source_file].append(event)
            if event.subsystem:
                self._source_map["subsystem"][event.subsystem].append(event)
            if event.service:
                self._source_map["service"][event.service].append(event)
            if event.source_function:
                self._source_map["function"][event.source_function].append(event)

    def correlate_by_file(self, trace: RuntimeTrace) -> List[CorrelationLink]:
        links = []
        file_events: Dict[str, List[RuntimeTraceEvent]] = defaultdict(list)
        for event in trace.events:
            if event.source_file:
                file_events[event.source_file].append(event)
        for file_path, events in file_events.items():
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            for i in range(len(sorted_events) - 1):
                latency = (sorted_events[i + 1].timestamp - sorted_events[i].timestamp) * 1000
                if latency < 5000:
                    links.append(CorrelationLink(
                        source_event_id=sorted_events[i].id,
                        target_event_id=sorted_events[i + 1].id,
                        relation="temporal_proximity",
                        confidence=CorrelationConfidence.HIGH if latency < 100 else CorrelationConfidence.MEDIUM,
                        evidence=[f"same_file:{file_path}", f"latency_ms:{latency:.1f}"],
                        latency_ms=latency,
                    ))
        return links

    def correlate_by_stack(self, trace: RuntimeTrace) -> List[CorrelationLink]:
        links = []
        error_events = trace.get_error_events()
        for event in error_events:
            if event.stack_frames:
                for frame in event.stack_frames:
                    related = self._source_map["file"].get(frame.file, [])
                    for related_event in related:
                        if related_event.id != event.id:
                            links.append(CorrelationLink(
                                source_event_id=event.id,
                                target_event_id=related_event.id,
                                relation="stack_frame_shared",
                                confidence=CorrelationConfidence.HIGH,
                                evidence=[f"shared_file:{frame.file}", f"line:{frame.line}"],
                            ))
        return links

    def correlate_by_correlation_id(self, trace: RuntimeTrace) -> List[CorrelationLink]:
        links = []
        corr_groups: Dict[str, List[RuntimeTraceEvent]] = defaultdict(list)
        for event in trace.events:
            if event.correlation_id:
                corr_groups[event.correlation_id].append(event)
        for corr_id, events in corr_groups.items():
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            for event in sorted_events:
                if event.causal_parent:
                    parent = next((e for e in sorted_events if e.id == event.causal_parent), None)
                    if parent:
                        latency = (event.timestamp - parent.timestamp) * 1000
                        links.append(CorrelationLink(
                            source_event_id=parent.id,
                            target_event_id=event.id,
                            relation="causal_parent",
                            confidence=CorrelationConfidence.CERTAIN,
                            evidence=[f"correlation_id:{corr_id}", f"explicit_causal_link"],
                            latency_ms=latency,
                        ))
        return links

    def correlate_by_temporal_overlap(self, trace: RuntimeTrace, window_ms: float = 100) -> List[CorrelationLink]:
        links = []
        sorted_events = sorted(trace.events, key=lambda e: e.timestamp)
        for i, event_a in enumerate(sorted_events):
            for j, event_b in enumerate(sorted_events):
                if j <= i:
                    continue
                latency = (event_b.timestamp - event_a.timestamp) * 1000
                if latency < window_ms:
                    if event_a.source_file and event_b.source_file and event_a.source_file != event_b.source_file:
                        links.append(CorrelationLink(
                            source_event_id=event_a.id,
                            target_event_id=event_b.id,
                            relation="temporal_overlap",
                            confidence=CorrelationConfidence.LOW,
                            evidence=[f"latency_ms:{latency:.1f}", f"cross_file"],
                            latency_ms=latency,
                        ))
        return links

    def correlate_error_propagation(self, trace: RuntimeTrace) -> List[CorrelationLink]:
        links = []
        error_events = trace.get_error_events()
        sorted_errors = sorted(error_events, key=lambda e: e.timestamp)
        for i in range(len(sorted_errors) - 1):
            latency = (sorted_errors[i + 1].timestamp - sorted_errors[i].timestamp) * 1000
            if latency < 10000:
                links.append(CorrelationLink(
                    source_event_id=sorted_errors[i].id,
                    target_event_id=sorted_errors[i + 1].id,
                    relation="error_propagation",
                    confidence=CorrelationConfidence.HIGH,
                    evidence=["sequential_errors", f"latency_ms:{latency:.1f}"],
                    latency_ms=latency,
                ))
        parent_map: Dict[str, str] = {}
        for event in trace.events:
            if event.event_type == RuntimeEventType.API_CALL and event.metadata.get("status") == "error":
                for other in trace.events:
                    if other.event_type == RuntimeEventType.EXCEPTION_FLOW:
                        latency = (other.timestamp - event.timestamp) * 1000
                        if 0 < latency < 5000:
                            links.append(CorrelationLink(
                                source_event_id=event.id,
                                target_event_id=other.id,
                                relation="api_failure_to_exception",
                                confidence=CorrelationConfidence.HIGH,
                                evidence=["api_error_precedes_exception"],
                                latency_ms=latency,
                            ))
        return links

    def correlate(self, trace: RuntimeTrace) -> CorrelationResult:
        self.index_events(trace)
        all_links = []
        all_links.extend(self.correlate_by_file(trace))
        all_links.extend(self.correlate_by_stack(trace))
        all_links.extend(self.correlate_by_correlation_id(trace))
        all_links.extend(self.correlate_by_temporal_overlap(trace))
        all_links.extend(self.correlate_error_propagation(trace))

        deduped = self._deduplicate_links(all_links)
        clusters = self._build_clusters(deduped, trace)
        root_causes = self._find_root_causes(deduped, trace)
        propagation_paths = self._build_propagation_paths(deduped, trace)

        return CorrelationResult(
            trace_id=trace.trace_id,
            links=deduped,
            clusters=clusters,
            root_causes=root_causes,
            propagation_paths=propagation_paths,
            summary=self._generate_summary(trace, clusters, root_causes),
        )

    def correlate_runtime_to_source(self, trace: RuntimeTrace,
                                    source_files: List[str]) -> Dict[str, List[CorrelationLink]]:
        mapping: Dict[str, List[CorrelationLink]] = {}
        for file_path in source_files:
            file_links = []
            for event in trace.events:
                if event.source_file == file_path:
                    file_links.append(CorrelationLink(
                        target_event_id=event.id,
                        relation="runtime_event_in_source",
                        confidence=CorrelationConfidence.CERTAIN,
                        evidence=[f"direct_file_match:{file_path}"],
                    ))
                elif event.stack_frames:
                    for frame in event.stack_frames:
                        if frame.file == file_path:
                            file_links.append(CorrelationLink(
                                target_event_id=event.id,
                                relation="stack_frame_reference",
                                confidence=CorrelationConfidence.HIGH,
                                evidence=[f"stack_file:{file_path}", f"line:{frame.line}"],
                            ))
            if file_links:
                mapping[file_path] = file_links
        return mapping

    def _deduplicate_links(self, links: List[CorrelationLink]) -> List[CorrelationLink]:
        seen: Set[Tuple[str, str, str]] = set()
        result = []
        for link in links:
            key = (link.source_event_id, link.target_event_id, link.relation)
            if key not in seen:
                seen.add(key)
                result.append(link)
        return result

    def _build_clusters(self, links: List[CorrelationLink], trace: RuntimeTrace) -> Dict[str, List[str]]:
        adj: Dict[str, Set[str]] = defaultdict(set)
        for link in links:
            adj[link.source_event_id].add(link.target_event_id)
            adj[link.target_event_id].add(link.source_event_id)

        clusters: Dict[str, List[str]] = {}
        visited: Set[str] = set()
        cluster_id = 0
        for event in trace.events:
            if event.id not in visited:
                cluster_id += 1
                queue = [event.id]
                cluster_events = []
                while queue:
                    eid = queue.pop(0)
                    if eid in visited:
                        continue
                    visited.add(eid)
                    cluster_events.append(eid)
                    for neighbor in adj.get(eid, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)
                if len(cluster_events) > 1:
                    clusters[f"cluster_{cluster_id}"] = cluster_events
        return clusters

    def _find_root_causes(self, links: List[CorrelationLink], trace: RuntimeTrace) -> List[str]:
        in_degree: Dict[str, int] = defaultdict(int)
        all_ids: Set[str] = set()
        for link in links:
            in_degree[link.target_event_id] += 1
            all_ids.add(link.source_event_id)
            all_ids.add(link.target_event_id)

        zero_in = [eid for eid in all_ids if in_degree[eid] == 0]
        error_zero_in = []
        for eid in zero_in:
            event = next((e for e in trace.events if e.id == eid), None)
            if event and event.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
                error_zero_in.append(eid)
        root_events = sorted(
            error_zero_in,
            key=lambda eid: next(
                (e.timestamp for e in trace.events if e.id == eid), float("inf")
            ),
        )
        return root_events[:10]

    def _build_propagation_paths(self, links: List[CorrelationLink], trace: RuntimeTrace) -> List[List[str]]:
        paths = []
        ordered_events = sorted(trace.events, key=lambda e: e.timestamp)
        for event in ordered_events:
            if event.severity not in (EventSeverity.ERROR, EventSeverity.CRITICAL):
                continue
            path = [event.id]
            visited = {event.id}
            queue = [(event.id, 0)]
            while queue:
                current_id, depth = queue.pop(0)
                if depth > 10:
                    continue
                for link in links:
                    target = None
                    if link.source_event_id == current_id and link.target_event_id not in visited:
                        target = link.target_event_id
                    elif link.target_event_id == current_id and link.source_event_id not in visited:
                        target = link.source_event_id
                    if target:
                        visited.add(target)
                        path.append(target)
                        queue.append((target, depth + 1))
            if len(path) > 1:
                paths.append(path)
        return paths[:20]

    def _generate_summary(self, trace: RuntimeTrace, clusters: Dict[str, List[str]],
                          root_causes: List[str]) -> str:
        parts = []
        error_count = trace.error_count
        cluster_count = len(clusters)
        root_count = len(root_causes)
        if error_count > 0:
            parts.append(f"{error_count} errors detected")
        if cluster_count > 0:
            parts.append(f"{cluster_count} correlation clusters found")
        if root_count > 0:
            parts.append(f"{root_count} potential root causes identified")
        event_types = defaultdict(int)
        for e in trace.events:
            event_types[e.event_type.value] += 1
        type_summary = ", ".join(f"{n}={c}" for n, c in sorted(event_types.items(), key=lambda x: -x[1])[:5])
        if type_summary:
            parts.append(f"events: {type_summary}")
        return "; ".join(parts) if parts else "No correlations identified"


class SourceCodeCorrelator:
    def __init__(self, correlation_engine: CorrelationEngine):
        self.correlation_engine = correlation_engine

    def correlate_failure_to_source(self, trace: RuntimeTrace,
                                    source_files: Dict[str, str]) -> Dict[str, Any]:
        file_links = self.correlation_engine.correlate_runtime_to_source(
            trace, list(source_files.keys())
        )
        result = {}
        for file_path, links in file_links.items():
            content = source_files.get(file_path, "")
            events = [l.target_event_id for l in links]
            error_events = [
                e for e in trace.events
                if e.id in events and e.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL)
            ]
            result[file_path] = {
                "correlation_count": len(links),
                "error_count": len(error_events),
                "related_event_ids": events,
                "file_snippet": content[:500],
            }
        return result
