import time
import uuid
from typing import Dict, Any, List, Optional
from .schema import (
    OpenAgentTrace, TraceHeader, TraceEvent,
    AgentIdentity, SystemMetadata,
    EventType, ModelCallEvent, ToolCallEvent,
    FileReadEvent, FileEditEvent, TestRunEvent,
    FailedAttemptEvent, EvidenceClaimEvent,
    VerificationStepEvent, HumanInterventionEvent,
    ConfidenceChangeEvent, RollbackEvent,
)


class LymeTraceConverter:
    def __init__(self):
        self._conversions = 0

    def convert_cognitive_trace(self, cognitive_trace: Any) -> OpenAgentTrace:
        oat = OpenAgentTrace()
        self._conversions += 1

        ct = cognitive_trace.to_dict() if hasattr(cognitive_trace, "to_dict") else cognitive_trace
        agent = AgentIdentity(
            name=ct.get("agent_name", "unknown"),
        )
        oat.header.agent = agent
        oat.header.trace_id = ct.get("trace_id", oat.header.trace_id)

        steps = ct.get("steps", [])
        decisions = ct.get("decisions", [])

        for i, step in enumerate(steps):
            event_type = self._map_thought_type(step.get("type", ""))
            event = TraceEvent(
                id=step.get("id", uuid.uuid4().hex[:12]),
                type=event_type,
                timestamp=step.get("timestamp", time.time()),
                duration_ms=step.get("duration_ms"),
                sequence=i,
                metadata={
                    "content": step.get("content", ""),
                    "confidence": step.get("confidence", 1.0),
                    "branch": step.get("branch", "main"),
                    "token_count": step.get("token_count", 0),
                }
            )
            if step.get("type") == "error":
                event.status = "error"
                event.error = step.get("content", "")
            oat.events.append(event.to_dict())

        for i, decision in enumerate(decisions):
            seq = len(steps) + i
            event = TraceEvent(
                id=decision.get("id", uuid.uuid4().hex[:12]),
                type=EventType.DECISION,
                timestamp=decision.get("timestamp", time.time()),
                sequence=seq,
                metadata={
                    "question": decision.get("question", ""),
                    "options": decision.get("options", []),
                    "chosen": decision.get("chosen", ""),
                    "rationale": decision.get("rationale", ""),
                    "confidence": decision.get("confidence", 1.0),
                    "outcome": decision.get("outcome", "pending"),
                    "alternatives_explored": decision.get("alternatives_explored", 0),
                }
            )
            if decision.get("outcome") == "failure":
                event.status = "error"
            oat.events.append(event.to_dict())

        oat.finalize(status=ct.get("status", "completed"), metrics=ct.get("summary", {}))
        return oat

    def convert_spans(self, spans: List[Any], trace_metadata: dict = None) -> OpenAgentTrace:
        oat = OpenAgentTrace()
        self._conversions += 1

        if trace_metadata:
            if "agent_name" in trace_metadata:
                oat.header.agent.name = trace_metadata["agent_name"]
            if "session_id" in trace_metadata:
                oat.header.session_id = trace_metadata["session_id"]

        span_dicts = [s.to_dict() if hasattr(s, "to_dict") else s for s in spans]

        for i, span in enumerate(span_dicts):
            event = TraceEvent(
                id=span.get("id", uuid.uuid4().hex[:12]),
                type=self._map_span_category(span.get("category", "")),
                timestamp=span.get("start_time", time.time()),
                duration_ms=span.get("duration_ms"),
                parent_id=span.get("parent_id"),
                sequence=i,
                status=span.get("status", "success"),
                error=span.get("error"),
                metadata={
                    "name": span.get("name", ""),
                    "category": span.get("category", ""),
                    "tags": span.get("tags", []),
                    **(span.get("metadata", {})),
                }
            )
            oat.events.append(event.to_dict())

        oat.finalize()
        return oat

    def convert_event_log(self, events: List[Any], metadata: dict = None) -> OpenAgentTrace:
        oat = OpenAgentTrace()
        self._conversions += 1

        if metadata:
            if "agent_name" in metadata:
                oat.header.agent.name = metadata["agent_name"]
            if "session_id" in metadata:
                oat.header.session_id = metadata["session_id"]

        event_dicts = [e.to_dict() if hasattr(e, "to_dict") else e for e in events]

        for i, evt in enumerate(event_dicts):
            event = TraceEvent(
                id=evt.get("id", uuid.uuid4().hex[:12]),
                type=self._map_event_log_type(evt.get("type", "system")),
                timestamp=evt.get("timestamp", time.time()),
                parent_id=evt.get("span_id"),
                sequence=i,
                severity=evt.get("severity", "info"),
                metadata=evt.get("payload", {}),
            )
            oat.events.append(event.to_dict())

        oat.finalize()
        return oat

    def build_from_run(self, cognitive_trace: Any = None,
                       spans: List[Any] = None,
                       events: List[Any] = None) -> OpenAgentTrace:
        if cognitive_trace:
            oat = self.convert_cognitive_trace(cognitive_trace)
        elif spans:
            oat = self.convert_spans(spans)
        elif events:
            oat = self.convert_event_log(events)
        else:
            oat = OpenAgentTrace()
            self._conversions += 1

        oat.header.system.repo_name = "lyme"
        oat.finalize()
        return oat

    def _map_thought_type(self, t: str) -> str:
        mapping = {
            "plan": EventType.PLAN,
            "decision": EventType.DECISION,
            "error": EventType.FAILED_ATTEMPT,
            "uncertainty": EventType.CONFIDENCE_CHANGE,
            "exploration": EventType.SEARCH,
            "tool_selection": EventType.TOOL_CALL,
            "insight": EventType.EVIDENCE_CLAIM,
            "conclusion": EventType.EVIDENCE_CLAIM,
        }
        return mapping.get(t, EventType.THOUGHT)

    def _map_span_category(self, cat: str) -> str:
        mapping = {
            "model": EventType.MODEL_CALL,
            "tool": EventType.TOOL_CALL,
            "read": EventType.FILE_READ,
            "edit": EventType.FILE_EDIT,
            "test": EventType.TEST_RUN,
            "search": EventType.SEARCH,
            "plan": EventType.PLAN,
            "verify": EventType.VERIFICATION_STEP,
        }
        return mapping.get(cat, EventType.SYSTEM)

    def _map_event_log_type(self, t: str) -> str:
        mapping = {
            "tool_call": EventType.TOOL_CALL,
            "tool_result": EventType.TOOL_CALL,
            "file_read": EventType.FILE_READ,
            "file_write": EventType.FILE_EDIT,
            "file_edit": EventType.FILE_EDIT,
            "search": EventType.SEARCH,
            "decision": EventType.DECISION,
            "plan": EventType.PLAN,
            "error": EventType.FAILED_ATTEMPT,
            "retry": EventType.FAILED_ATTEMPT,
            "hallucination": EventType.EVIDENCE_CLAIM,
            "uncertainty": EventType.CONFIDENCE_CHANGE,
            "repair": EventType.ROLLBACK,
        }
        return mapping.get(t, EventType.SYSTEM)
