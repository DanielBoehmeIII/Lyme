from __future__ import annotations

import difflib
import time
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    EventSeverity,
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
)


class FailureCategory(str, Enum):
    RACE_CONDITION = "race_condition"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    STATE_CORRUPTION = "state_corruption"
    CACHE_STALE = "cache_stale"
    DEADLOCK = "deadlock"
    NETWORK_PARTITION = "network_partition"
    ASYNC_MISORDER = "async_misorder"
    CONFIG_DRIFT = "config_drift"
    DATA_RACE = "data_race"
    MEMORY_LEAK = "memory_leak"
    EXCEPTION_CASCADE = "exception_cascade"
    INVARIANT_VIOLATION = "invariant_violation"
    CONTRACT_BREACH = "contract_breach"
    COUPLED_DEPLOYMENT = "coupled_deployment"
    UNKNOWN = "unknown"


class HypothesisConfidence(str, Enum):
    CERTAIN = "certain"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


@dataclass
class ReplayEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    original_event_id: str = ""
    timestamp: float = 0.0
    event_type: str = ""
    description: str = ""
    source_file: str = ""
    source_line: int = 0
    source_function: str = ""
    subsystem: str = ""
    severity: str = "info"
    duration_ms: Optional[float] = None
    trace_id: str = ""
    related_events: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_event_id": self.original_event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "description": self.description,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "source_function": self.source_function,
            "subsystem": self.subsystem,
            "severity": self.severity,
            "duration_ms": self.duration_ms,
            "trace_id": self.trace_id,
            "related_events": self.related_events,
        }


@dataclass
class ReplayTimeline:
    events: List[ReplayEvent] = field(default_factory=list)
    total_duration_ms: float = 0.0
    phases: List[Dict[str, Any]] = field(default_factory=list)
    uncertainty_intervals: List[Dict[str, Any]] = field(default_factory=list)

    def add_event(self, event: ReplayEvent):
        self.events.append(event)

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in sorted(self.events, key=lambda e: e.timestamp)],
            "total_duration_ms": self.total_duration_ms,
            "phases": self.phases,
            "uncertainty_intervals": self.uncertainty_intervals,
        }


@dataclass
class CausalChain:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trigger_event_id: str = ""
    propagation_events: List[str] = field(default_factory=list)
    final_failure_event_id: str = ""
    propagation_delay_ms: float = 0.0
    confidence: float = 0.0
    intermediate_states: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trigger_event_id": self.trigger_event_id,
            "propagation_events": self.propagation_events,
            "final_failure_event_id": self.final_failure_event_id,
            "propagation_delay_ms": self.propagation_delay_ms,
            "confidence": self.confidence,
            "intermediate_states": self.intermediate_states,
        }


@dataclass
class RepairHypothesis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    file_path: str = ""
    line_number: int = 0
    repair_type: str = ""
    confidence: HypothesisConfidence = HypothesisConfidence.WEAK
    explanation: str = ""
    estimated_effort: str = "medium"
    side_effects: List[str] = field(default_factory=list)
    similar_historical_fixes: List[str] = field(default_factory=list)
    test_suggestions: List[str] = field(default_factory=list)
    invariant_restored: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "repair_type": self.repair_type,
            "confidence": self.confidence.value,
            "explanation": self.explanation,
            "estimated_effort": self.estimated_effort,
            "side_effects": self.side_effects,
            "similar_historical_fixes": self.similar_historical_fixes,
            "test_suggestions": self.test_suggestions,
            "invariant_restored": self.invariant_restored,
        }


@dataclass
class FailureReplayResult:
    failure_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    failure_category: FailureCategory = FailureCategory.UNKNOWN
    trace_id: str = ""
    git_commit: str = ""
    git_branch: str = ""
    timeline: ReplayTimeline = field(default_factory=ReplayTimeline)
    causal_chains: List[CausalChain] = field(default_factory=list)
    root_causes: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: List[RepairHypothesis] = field(default_factory=list)
    uncertainty_score: float = 0.0
    similar_historical_failures: List[str] = field(default_factory=list)
    reconstruction_confidence: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "failure_id": self.failure_id,
            "failure_category": self.failure_category.value,
            "trace_id": self.trace_id,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "timeline": self.timeline.to_dict(),
            "causal_chains": [c.to_dict() for c in self.causal_chains],
            "root_causes": self.root_causes,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "uncertainty_score": self.uncertainty_score,
            "similar_historical_failures": self.similar_historical_failures,
            "reconstruction_confidence": self.reconstruction_confidence,
            "summary": self.summary,
        }


class FailureClassifier:
    def __init__(self):
        self._patterns: Dict[FailureCategory, List[str]] = {
            FailureCategory.RACE_CONDITION: [
                "race", "concurrent", "racy", "data race", "TOCTOU",
            ],
            FailureCategory.TIMEOUT: [
                "timeout", "timed out", "deadline exceeded",
            ],
            FailureCategory.RESOURCE_EXHAUSTION: [
                "out of memory", "OOM", "memory", "too many", "exhausted",
                "quota", "limit exceeded",
            ],
            FailureCategory.STATE_CORRUPTION: [
                "corrupt", "inconsistent state", "unexpected value",
                "null reference", "undefined", "NaN",
            ],
            FailureCategory.CACHE_STALE: [
                "stale", "cache miss", "invalid cache",
            ],
            FailureCategory.DEADLOCK: [
                "deadlock", "circular wait", "lock contention",
            ],
            FailureCategory.NETWORK_PARTITION: [
                "network", "connection refused", "connection reset",
                "no route", "broken pipe",
            ],
            FailureCategory.ASYNC_MISORDER: [
                "async", "callback", "promise", "unhandled",
                "out of order", "sequence",
            ],
            FailureCategory.EXCEPTION_CASCADE: [
                "exception", "traceback", "uncaught", "throw",
                "raise", "propagated",
            ],
            FailureCategory.INVARIANT_VIOLATION: [
                "invariant", "assertion", "assert", "precondition",
                "postcondition", "validation failed",
            ],
        }

    def classify(self, trace: RuntimeTrace) -> FailureCategory:
        scores: Dict[FailureCategory, int] = defaultdict(int)
        for event in trace.events:
            text = (
                event.metadata.get("raw", "")
                + event.metadata.get("message", "")
                + event.metadata.get("exception_type", "")
                + " ".join(event.tags)
            ).lower()
            for category, patterns in self._patterns.items():
                for pattern in patterns:
                    if pattern in text:
                        scores[category] += 1
            if event.event_type == RuntimeEventType.RACE_CONDITION:
                scores[FailureCategory.RACE_CONDITION] += 5
            elif event.event_type == RuntimeEventType.TIMEOUT:
                scores[FailureCategory.TIMEOUT] += 5
            elif event.event_type == RuntimeEventType.MEMORY_PRESSURE:
                scores[FailureCategory.RESOURCE_EXHAUSTION] += 5

        if not scores:
            return FailureCategory.UNKNOWN
        return max(scores, key=scores.get)


class TimelineReconstructor:
    def __init__(self):
        pass

    def reconstruct(self, trace: RuntimeTrace, git_diff: str = "",
                    user_actions: List[Dict[str, Any]] = None) -> ReplayTimeline:
        timeline = ReplayTimeline()
        sorted_events = sorted(trace.events, key=lambda e: e.timestamp)
        if not sorted_events:
            return timeline

        timeline.total_duration_ms = (
            sorted_events[-1].timestamp - sorted_events[0].timestamp
        ) * 1000

        for i, event in enumerate(sorted_events):
            replay_event = ReplayEvent(
                original_event_id=event.id,
                timestamp=event.timestamp,
                event_type=event.event_type.value,
                description=self._describe_event(event),
                source_file=event.source_file,
                source_line=event.source_line,
                source_function=event.source_function,
                subsystem=event.subsystem,
                severity=event.severity.value,
                duration_ms=event.duration_ms,
                trace_id=event.trace_id,
            )
            nearby = []
            for j in range(max(0, i - 3), min(len(sorted_events), i + 4)):
                if j != i:
                    nearby.append(sorted_events[j].id)
            replay_event.related_events = nearby
            timeline.add_event(replay_event)

        timeline.phases = self._identify_phases(sorted_events)
        timeline.uncertainty_intervals = self._identify_uncertainty(sorted_events)
        return timeline

    def _describe_event(self, event: RuntimeTraceEvent) -> str:
        meta = event.metadata or {}
        descriptions = {
            RuntimeEventType.LOG: f"Log: {meta.get('raw', '')[:100]}",
            RuntimeEventType.STACK_TRACE: f"Stack trace: {meta.get('exception_type', 'Exception')}: {meta.get('message', '')[:100]}",
            RuntimeEventType.EXCEPTION_FLOW: f"Exception: {meta.get('exception_type', '')} in {event.source_function}",
            RuntimeEventType.API_CALL: f"API: {meta.get('method', 'GET')} {meta.get('api', meta.get('endpoint', ''))}",
            RuntimeEventType.STATE_MUTATION: f"State change: {meta.get('state_name', '')}",
            RuntimeEventType.NETWORK_EVENT: f"Network: {meta.get('type', '')}",
            RuntimeEventType.DB_QUERY: f"DB: {meta.get('query', '')[:100]}",
            RuntimeEventType.METRIC: f"Metric: {meta.get('metric_name', '')} = {meta.get('metric_value', '')}",
            RuntimeEventType.TEST_TRACE: f"Test: {meta.get('test_name', '')}",
        }
        return descriptions.get(event.event_type, f"{event.event_type.value}: {str(meta)[:100]}")

    def _identify_phases(self, events: List[RuntimeTraceEvent]) -> List[Dict[str, Any]]:
        if not events:
            return []
        phases = []
        current_phase = {
            "start_time": events[0].timestamp,
            "event_types": Counter(),
            "subsystems": set(),
            "error_count": 0,
        }
        gap_threshold = 2.0
        for event in events:
            if current_phase["start_time"] and (
                event.timestamp - current_phase["start_time"] > gap_threshold
                and len(current_phase["event_types"]) > 0
            ):
                current_phase["end_time"] = event.timestamp
                current_phase["duration_ms"] = (
                    current_phase["end_time"] - current_phase["start_time"]
                ) * 1000
                current_phase["dominant_type"] = current_phase["event_types"].most_common(1)[0][0]
                current_phase["subsystems"] = list(current_phase["subsystems"])
                current_phase["event_types"] = dict(current_phase["event_types"])
                phases.append(current_phase)
                current_phase = {
                    "start_time": event.timestamp,
                    "event_types": Counter(),
                    "subsystems": set(),
                    "error_count": 0,
                }
            current_phase["event_types"][event.event_type.value] += 1
            if event.subsystem:
                current_phase["subsystems"].add(event.subsystem)
            if event.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
                current_phase["error_count"] += 1

        if current_phase["event_types"]:
            current_phase["end_time"] = events[-1].timestamp
            current_phase["duration_ms"] = (
                current_phase["end_time"] - current_phase["start_time"]
            ) * 1000
            current_phase["dominant_type"] = current_phase["event_types"].most_common(1)[0][0]
            current_phase["subsystems"] = list(current_phase["subsystems"])
            current_phase["event_types"] = dict(current_phase["event_types"])
            phases.append(current_phase)
        return phases

    def _identify_uncertainty(self, events: List[RuntimeTraceEvent]) -> List[Dict[str, Any]]:
        gaps = []
        for i in range(len(events) - 1):
            gap = (events[i + 1].timestamp - events[i].timestamp) * 1000
            if gap > 5000:
                gaps.append({
                    "from_time": events[i].timestamp,
                    "to_time": events[i + 1].timestamp,
                    "gap_ms": gap,
                    "from_event": events[i].id,
                    "to_event": events[i + 1].id,
                    "uncertainty": min(1.0, gap / 30000),
                })
        return gaps


class CausalReconstructor:
    def __init__(self):
        self._propagation_windows = [10, 100, 1000, 5000]

    def reconstruct(self, trace: RuntimeTrace, timeline: ReplayTimeline) -> Tuple[List[CausalChain], List[Dict[str, Any]]]:
        chains = []
        root_causes = []

        error_events = trace.get_error_events()
        sorted_errors = sorted(error_events, key=lambda e: e.timestamp)

        chain_map: Dict[str, CausalChain] = {}
        for error in sorted_errors:
            for window in self._propagation_windows:
                for other in sorted_errors:
                    if other.id == error.id:
                        continue
                    latency = (other.timestamp - error.timestamp) * 1000
                    if 0 < latency < window:
                        chain_id = error.id
                        if chain_id not in chain_map:
                            chain_map[chain_id] = CausalChain(
                                trigger_event_id=error.id,
                                final_failure_event_id=other.id,
                                propagation_delay_ms=latency,
                                confidence=max(0.3, 1.0 - (latency / (window * 2))),
                            )
                        chain = chain_map[chain_id]
                        if other.id not in chain.propagation_events:
                            chain.propagation_events.append(other.id)
                        chain.final_failure_event_id = other.id
                        chain.propagation_delay_ms = max(
                            chain.propagation_delay_ms, latency
                        )
                        chain.confidence = max(
                            chain.confidence, max(0.3, 1.0 - (latency / (window * 2)))
                        )

        for event in sorted_errors:
            if event.stack_frames:
                chain = CausalChain(
                    trigger_event_id=event.id,
                    final_failure_event_id=event.id,
                    confidence=0.6,
                )
                for frame in event.stack_frames:
                    chain.intermediate_states.append({
                        "file": frame.file,
                        "function": frame.function,
                        "line": frame.line,
                    })
                chains.append(chain)

        chains.extend(chain_map.values())

        for event in sorted_errors:
            file_risk: Dict[str, float] = defaultdict(float)
            if event.stack_frames:
                for frame in event.stack_frames:
                    file_risk[frame.file] += 1.0
                    if frame.function:
                        file_risk[frame.file] += 0.5
            for file_path, score in sorted(file_risk.items(), key=lambda x: -x[1])[:3]:
                root_causes.append({
                    "event_id": event.id,
                    "file_path": file_path,
                    "confidence": min(1.0, score / max(len(event.stack_frames), 1)),
                    "trigger_type": event.event_type.value,
                    "message": event.metadata.get("message",
                               event.metadata.get("raw", ""))[:200],
                })

        root_causes.sort(key=lambda r: -r["confidence"])
        return chains[:20], root_causes[:10]


class HistoricalFailureMatcher:
    def __init__(self):
        self._failure_db: List[Dict[str, Any]] = []

    def add_failure(self, failure: Dict[str, Any]):
        self._failure_db.append(failure)

    def find_similar(self, result: FailureReplayResult, top_k: int = 5) -> List[str]:
        if not self._failure_db:
            return []
        scores: List[Tuple[float, str]] = []
        current_files = set(
            rc["file_path"] for rc in result.root_causes if rc.get("file_path")
        )
        for past in self._failure_db:
            past_files = set(past.get("files", []))
            if current_files and past_files:
                overlap = len(current_files & past_files) / len(current_files | past_files)
            else:
                overlap = 0
            cat_match = 1.0 if past.get("category") == result.failure_category.value else 0.0
            score = overlap * 0.7 + cat_match * 0.3
            if score > 0.3:
                scores.append((score, past.get("failure_id", "")))
        scores.sort(key=lambda x: -x[0])
        return [fid for _, fid in scores[:top_k]]


class RepairSuggester:
    def __init__(self):
        self._repair_templates: Dict[FailureCategory, List[Dict[str, Any]]] = {
            FailureCategory.RACE_CONDITION: [
                {"type": "synchronization", "description": "Add synchronization primitive",
                 "effort": "medium"},
                {"type": "atomic_update", "description": "Make state update atomic",
                 "effort": "low"},
                {"type": "ordering", "description": "Enforce operation ordering",
                 "effort": "medium"},
            ],
            FailureCategory.TIMEOUT: [
                {"type": "retry", "description": "Add retry with backoff",
                 "effort": "low"},
                {"type": "timeout_increase", "description": "Increase timeout threshold",
                 "effort": "low"},
                {"type": "circuit_breaker", "description": "Add circuit breaker pattern",
                 "effort": "high"},
            ],
            FailureCategory.STATE_CORRUPTION: [
                {"type": "validation", "description": "Add input validation",
                 "effort": "low"},
                {"type": "state_machine", "description": "Enforce valid state transitions",
                 "effort": "high"},
                {"type": "defensive_copy", "description": "Add defensive copying",
                 "effort": "medium"},
            ],
            FailureCategory.EXCEPTION_CASCADE: [
                {"type": "try_catch", "description": "Add exception handling boundary",
                 "effort": "low"},
                {"type": "circuit_breaker", "description": "Add circuit breaker at boundary",
                 "effort": "high"},
                {"type": "fallback", "description": "Provide fallback behavior",
                 "effort": "medium"},
            ],
            FailureCategory.RESOURCE_EXHAUSTION: [
                {"type": "pool_limits", "description": "Add resource pool limits",
                 "effort": "medium"},
                {"type": "cleanup", "description": "Add explicit resource cleanup",
                 "effort": "low"},
                {"type": "backpressure", "description": "Add backpressure mechanism",
                 "effort": "high"},
            ],
            FailureCategory.ASYNC_MISORDER: [
                {"type": "ordering", "description": "Add async operation ordering",
                 "effort": "medium"},
                {"type": "state_check", "description": "Add state precondition checks",
                 "effort": "low"},
                {"type": "queue", "description": "Use serial queue for ordering",
                 "effort": "medium"},
            ],
            FailureCategory.INVARIANT_VIOLATION: [
                {"type": "invariant_check", "description": "Add explicit invariant check",
                 "effort": "low"},
                {"type": "precondition", "description": "Strengthen preconditions",
                 "effort": "medium"},
                {"type": "postcondition", "description": "Add postcondition validation",
                 "effort": "medium"},
            ],
        }

    def suggest(self, result: FailureReplayResult, trace: RuntimeTrace,
                source_files: Dict[str, str] = None) -> List[RepairHypothesis]:
        hypotheses = []
        templates = self._repair_templates.get(
            result.failure_category, []
        )

        for root_cause in result.root_causes[:3]:
            file_path = root_cause.get("file_path", "")
            line = root_cause.get("line", 0)

            for i, template in enumerate(templates):
                source_context = ""
                if source_files and file_path in source_files:
                    source_context = source_files[file_path][:200]

                conf = self._estimate_confidence(result, template, i)
                hypothesis = RepairHypothesis(
                    description=template["description"],
                    file_path=file_path,
                    line_number=line,
                    repair_type=template["type"],
                    confidence=conf,
                    explanation=self._build_explanation(
                        template, root_cause, result.failure_category
                    ),
                    estimated_effort=template.get("effort", "medium"),
                    side_effects=self._estimate_side_effects(template),
                    test_suggestions=self._suggest_tests(template, file_path),
                )
                hypotheses.append(hypothesis)

        for event in trace.get_error_events()[:3]:
            if event.stack_frames and event.stack_frames[0].file:
                frame = event.stack_frames[0]
                hypotheses.append(RepairHypothesis(
                    description=f"Check exception handling at {frame.function}",
                    file_path=frame.file,
                    line_number=frame.line,
                    repair_type="exception_boundary",
                    confidence=HypothesisConfidence.MODERATE,
                    explanation=f"Exception {event.metadata.get('exception_type', '')} originates at {frame.function} (line {frame.line})",
                    estimated_effort="medium",
                ))
        return self._rank_hypotheses(hypotheses)

    def _estimate_confidence(self, result: FailureReplayResult, template: Dict[str, Any],
                             index: int) -> HypothesisConfidence:
        base_scores = {
            "low": 0.3, "medium": 0.5, "high": 0.7,
        }
        base = base_scores.get(template.get("effort", "medium"), 0.5)
        adjusted = base + (0.1 if result.reconstruction_confidence > 0.7 else 0) - (index * 0.05)
        if adjusted >= 0.7:
            return HypothesisConfidence.STRONG
        elif adjusted >= 0.5:
            return HypothesisConfidence.MODERATE
        elif adjusted >= 0.3:
            return HypothesisConfidence.WEAK
        return HypothesisConfidence.SPECULATIVE

    def _build_explanation(self, template: Dict[str, Any], root_cause: Dict[str, Any],
                           category: FailureCategory) -> str:
        file_path = root_cause.get("file_path", "unknown")
        trigger = root_cause.get("trigger_type", "unknown")
        return (
            f"Failure category: {category.value}. "
            f"Trigger at {file_path} ({trigger}). "
            f"Suggestion: {template['description']}."
        )

    def _estimate_side_effects(self, template: Dict[str, Any]) -> List[str]:
        side_effects_map = {
            "synchronization": ["potential performance impact", "possible deadlock risk"],
            "atomic_update": ["slightly reduced throughput"],
            "ordering": ["may increase latency"],
            "retry": ["possible duplicate operations"],
            "timeout_increase": ["delayed failure detection"],
            "circuit_breaker": ["complex state management"],
            "validation": ["additional computation overhead"],
            "try_catch": ["may mask real errors if too broad"],
            "pool_limits": ["may cause new contention points"],
            "cleanup": ["minimal"],
            "backpressure": ["may cause upstream blocking"],
        }
        return side_effects_map.get(template["type"], ["unknown"])

    def _suggest_tests(self, template: Dict[str, Any], file_path: str) -> List[str]:
        suggestions = {
            "synchronization": [f"Add concurrent access test for {file_path}",
                                f"Add race condition detection test"],
            "retry": [f"Add retry behavior test for {file_path}",
                      f"Add backoff timing verification"],
            "validation": [f"Add boundary value tests for {file_path}",
                           f"Add invalid input tests"],
            "try_catch": [f"Add exception propagation test for {file_path}",
                          f"Add error boundary coverage test"],
            "ordering": [f"Add sequence verification test",
                         f"Add async ordering test"],
            "atomic_update": [f"Add concurrent update test for {file_path}"],
        }
        return suggestions.get(template["type"], [f"Add tests for {file_path}"])

    def _rank_hypotheses(self, hypotheses: List[RepairHypothesis]) -> List[RepairHypothesis]:
        conf_order = {
            HypothesisConfidence.CERTAIN: 0,
            HypothesisConfidence.STRONG: 1,
            HypothesisConfidence.MODERATE: 2,
            HypothesisConfidence.WEAK: 3,
            HypothesisConfidence.SPECULATIVE: 4,
        }
        return sorted(hypotheses, key=lambda h: conf_order.get(h.confidence, 99))


class FailureReplayEngine:
    def __init__(self):
        self.classifier = FailureClassifier()
        self.timeline_reconstructor = TimelineReconstructor()
        self.causal_reconstructor = CausalReconstructor()
        self.historical_matcher = HistoricalFailureMatcher()
        self.repair_suggester = RepairSuggester()

    def replay(self, trace: RuntimeTrace, git_diff: str = "",
               user_actions: List[Dict[str, Any]] = None,
               source_files: Dict[str, str] = None) -> FailureReplayResult:
        category = self.classifier.classify(trace)
        timeline = self.timeline_reconstructor.reconstruct(
            trace, git_diff, user_actions
        )
        causal_chains, root_causes = self.causal_reconstructor.reconstruct(
            trace, timeline
        )
        result = FailureReplayResult(
            failure_category=category,
            trace_id=trace.trace_id,
            timeline=timeline,
            causal_chains=causal_chains,
            root_causes=root_causes,
            reconstruction_confidence=self._compute_reconstruction_confidence(
                trace, timeline
            ),
        )

        result.hypotheses = self.repair_suggester.suggest(result, trace, source_files)
        result.similar_historical_failures = self.historical_matcher.find_similar(result)
        result.uncertainty_score = self._compute_uncertainty(timeline, causal_chains)
        result.summary = self._generate_summary(result)

        return result

    def _compute_reconstruction_confidence(self, trace: RuntimeTrace,
                                            timeline: ReplayTimeline) -> float:
        if not trace.events:
            return 0.0
        event_count = len(trace.events)
        error_count = trace.error_count
        gap_penalty = len(timeline.uncertainty_intervals) * 0.1
        base = min(1.0, (event_count / 100) * 0.5 + (error_count / max(event_count, 1)))
        return max(0.1, min(0.95, base - gap_penalty))

    def _compute_uncertainty(self, timeline: ReplayTimeline,
                              chains: List[CausalChain]) -> float:
        gap_uncertainty = sum(
            gap.get("uncertainty", 0) for gap in timeline.uncertainty_intervals
        ) / max(len(timeline.uncertainty_intervals), 1)
        chain_uncertainty = sum(
            1 - c.confidence for c in chains
        ) / max(len(chains), 1)
        return (gap_uncertainty * 0.4 + chain_uncertainty * 0.6)

    def _generate_summary(self, result: FailureReplayResult) -> str:
        parts = []
        parts.append(f"Failure: {result.failure_category.value}")
        parts.append(f"Reconstruction confidence: {result.reconstruction_confidence:.1%}")
        if result.root_causes:
            parts.append(f"Root causes: {len(result.root_causes)} identified")
            top = result.root_causes[0]
            if top.get("file_path"):
                parts.append(f"Primary: {top['file_path']}")
        if result.causal_chains:
            parts.append(f"Causal chains: {len(result.causal_chains)} reconstructed")
        if result.hypotheses:
            strong = sum(
                1 for h in result.hypotheses
                if h.confidence in (HypothesisConfidence.STRONG, HypothesisConfidence.CERTAIN)
            )
            parts.append(f"Repair hypotheses: {len(result.hypotheses)} ({strong} strong)")
        if result.uncertainty_score > 0.5:
            parts.append(f"High uncertainty ({result.uncertainty_score:.1%}) - gaps in trace data")
        return " | ".join(parts)
