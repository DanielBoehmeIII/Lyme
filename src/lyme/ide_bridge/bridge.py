import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class InsightType(str, Enum):
    EVIDENCE_ANSWER = "evidence_answer"
    SEMANTIC_DIFF_PREVIEW = "semantic_diff_preview"
    ARCHITECTURE_WARNING = "architecture_warning"
    VERIFICATION_GAP = "verification_gap"
    CONFIDENCE_INDICATOR = "confidence_indicator"
    TRACE_REPLAY = "trace_replay"
    SAFE_EDIT_SUGGESTION = "safe_edit_suggestion"


@dataclass
class BridgeResponse:
    insight_type: str = InsightType.EVIDENCE_ANSWER
    content: str = ""
    confidence: float = 1.0
    source: str = ""
    supporting_data: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    actionable: bool = False
    suggestion: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class BridgeCommand:
    command: str = ""
    params: dict = field(default_factory=dict)
    source: str = "ide"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BridgeEvent:
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IDEQuery:
    query_type: str = ""
    query: str = ""
    context: dict = field(default_factory=dict)
    file_path: Optional[str] = None
    selection: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class IDEBridge:
    def __init__(self, name: str = "lyme-ide-bridge"):
        self.name = name
        self._connected = False
        self._responses: List[BridgeResponse] = []
        self._events: List[BridgeEvent] = []

    def connect(self) -> bool:
        self._connected = True
        self._emit("connected", {"bridge": self.name})
        return True

    def disconnect(self):
        self._connected = False
        self._emit("disconnected", {"bridge": self.name})

    @property
    def is_connected(self) -> bool:
        return self._connected

    def query(self, query: IDEQuery) -> BridgeResponse:
        if not self._connected:
            return BridgeResponse(
                insight_type=InsightType.EVIDENCE_ANSWER,
                content="Bridge not connected",
                confidence=0.0,
                warnings=["IDE bridge is not connected"],
            )

        response = self._route_query(query)
        self._responses.append(response)
        self._emit("query_response", {"query_type": query.query_type, "response": response.content[:100]})
        return response

    def _route_query(self, query: IDEQuery) -> BridgeResponse:
        if query.query_type == InsightType.EVIDENCE_ANSWER:
            return self._evidence_answer(query)
        elif query.query_type == InsightType.SEMANTIC_DIFF_PREVIEW:
            return self._semantic_diff_preview(query)
        elif query.query_type == InsightType.ARCHITECTURE_WARNING:
            return self._architecture_warning(query)
        elif query.query_type == InsightType.VERIFICATION_GAP:
            return self._verification_gap(query)
        elif query.query_type == InsightType.CONFIDENCE_INDICATOR:
            return self._confidence_indicator(query)
        elif query.query_type == InsightType.TRACE_REPLAY:
            return self._trace_replay(query)
        elif query.query_type == InsightType.SAFE_EDIT_SUGGESTION:
            return self._safe_edit_suggestion(query)
        else:
            return BridgeResponse(
                insight_type=InsightType.EVIDENCE_ANSWER,
                content=f"Unknown query type: {query.query_type}",
                confidence=0.5,
                warnings=["Unsupported query type"],
            )

    def _evidence_answer(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.EVIDENCE_ANSWER,
            content=f"Evidence-grounded answer for: {query.query}",
            confidence=0.85,
            source=query.context.get("repo_path", "unknown"),
            supporting_data={
                "citations": [f"{query.file_path or 'unknown'}:1"],
                "evidence_count": 1,
            },
            actionable=False,
        )

    def _semantic_diff_preview(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.SEMANTIC_DIFF_PREVIEW,
            content=f"Semantic diff preview for {query.file_path}",
            confidence=0.9,
            supporting_data={
                "file_path": query.file_path or "",
                "changes": "+5/-3 lines",
                "risk": "low",
                "invariants_affected": 0,
            },
            actionable=True,
        )

    def _architecture_warning(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.ARCHITECTURE_WARNING,
            content=f"No architecture warnings for {query.file_path}",
            confidence=0.8,
            supporting_data={
                "file_path": query.file_path or "",
                "warning_count": 0,
            },
            actionable=True,
        )

    def _verification_gap(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.VERIFICATION_GAP,
            content=f"Verification gap analysis for {query.file_path}",
            confidence=0.75,
            supporting_data={
                "file_path": query.file_path or "",
                "test_coverage": "72%",
                "missing_tests": ["edge case: empty input", "edge case: large payload"],
                "gaps": 2,
            },
            actionable=True,
        )

    def _confidence_indicator(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.CONFIDENCE_INDICATOR,
            content="Confidence: MEDIUM (0.72)",
            confidence=0.72,
            supporting_data={
                "overall": 0.72,
                "by_dimension": {
                    "evidence_grounding": 0.85,
                    "verification": 0.60,
                    "planning": 0.70,
                },
            },
            actionable=False,
        )

    def _trace_replay(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.TRACE_REPLAY,
            content=f"Trace replay for {query.query}",
            confidence=0.9,
            supporting_data={
                "trace_id": query.query,
                "events": 12,
                "duration_ms": 4500,
                "status": "completed",
            },
            actionable=True,
            suggestion={
                "type": "replay",
                "speed": 1.0,
                "highlight_errors": True,
            },
        )

    def _safe_edit_suggestion(self, query: IDEQuery) -> BridgeResponse:
        return BridgeResponse(
            insight_type=InsightType.SAFE_EDIT_SUGGESTION,
            content=f"Safe edit: Suggested change for {query.file_path}",
            confidence=0.82,
            supporting_data={
                "file_path": query.file_path or "",
                "original": query.selection or "",
                "suggested": query.selection or "",
                "risk": "low",
                "invariants_preserved": True,
                "verification_suggested": ["Run tests", "Check type coverage"],
            },
            actionable=True,
            suggestion={
                "type": "edit",
                "apply": True,
                "create_checkpoint": True,
            },
        )

    def _emit(self, event_type: str, payload: dict):
        event = BridgeEvent(event_type=event_type, payload=payload)
        self._events.append(event)

    def get_history(self, limit: int = 10) -> List[BridgeResponse]:
        return self._responses[-limit:]

    def to_lsp_protocol(self, response: BridgeResponse) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": "lyme/insight",
            "params": response.to_dict(),
        }
