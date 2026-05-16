"""Week 3 — Safe local tool use session.

Provides:
- Model-requested tool execution loop
- Tool call parsing from model output
- Evidence tracking and citation
- Audit trace emission per tool call
- Latency tracking
- Readonly mode enforcement
- Failure handling with bounded retries
"""

from __future__ import annotations
import re
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Callable, Any
from pathlib import Path
from enum import Enum

from .dispatch import ToolDispatcher, ToolResult
from .registry import ToolRegistry, ToolCategory


class SafetyMode(str, Enum):
    READONLY = "readonly"
    CAREFUL = "careful"  # allow test, allow user-confirmed edit
    FULL = "full"


@dataclass
class ToolCall:
    tool_name: str
    params: Dict[str, str]
    raw_line: str = ""

    def to_dict(self) -> dict:
        return {"tool": self.tool_name, "params": self.params, "raw": self.raw_line}


@dataclass
class ToolTrace:
    call_id: str
    tool_name: str
    params: Dict[str, str]
    result: Optional[ToolResult] = None
    start_time: float = 0.0
    end_time: float = 0.0
    latency_ms: float = 0.0
    evidence: str = ""
    error: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "tool": self.tool_name,
            "params": self.params,
            "success": self.result.success if self.result else False,
            "latency_ms": self.latency_ms,
            "output_preview": (self.result.output[:200] if self.result and self.result.output else ""),
            "error": self.error or (self.result.error if self.result else None),
            "retry_count": self.retry_count,
            "evidence": self.evidence,
        }


@dataclass
class ToolSessionResult:
    model_output: str = ""
    tool_calls: List[ToolTrace] = field(default_factory=list)
    total_latency_ms: float = 0.0
    tool_call_count: int = 0
    failed_calls: int = 0
    evidence_used: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "model_output": self.model_output[:500],
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "total_latency_ms": self.total_latency_ms,
            "tool_call_count": self.tool_call_count,
            "failed_calls": self.failed_calls,
            "evidence_used": self.evidence_used[:20],
        }


class ToolCallParser:
    """Parses tool calls from model output text."""

    TOOL_PATTERN = re.compile(
        r'(?:TOOL|Tool|tool):\s*(\w+)\s*\(([^)]*)\)',
        re.MULTILINE,
    )

    @classmethod
    def parse(cls, text: str) -> List[ToolCall]:
        calls = []
        for match in cls.TOOL_PATTERN.finditer(text):
            name = match.group(1)
            params_str = match.group(2)
            params = cls._parse_params(params_str)
            calls.append(ToolCall(
                tool_name=name,
                params=params,
                raw_line=match.group(0),
            ))
        return calls

    @classmethod
    def _parse_params(cls, params_str: str) -> Dict[str, str]:
        params = {}
        if not params_str.strip():
            return params
        for pair in params_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, _, value = pair.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"").strip()
                params[key] = value
        return params


class ToolSession:
    """Orchestrates model tool use with safety, tracing, and evidence tracking.

    Flow:
    1. Model outputs text with embedded tool calls (TOOL: tool_name(params))
    2. Session parses tool calls
    3. Dispatches each call through ToolDispatcher
    4. Returns tool output to model
    5. Tracks latency, traces, and evidence
    """

    def __init__(
        self,
        repo_path: str = ".",
        safety_mode: SafetyMode | str = SafetyMode.READONLY,
        max_retries: int = 1,
        max_tool_calls: int = 10,
        dispatcher: Optional[ToolDispatcher] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        if isinstance(safety_mode, str):
            self.safety_mode = SafetyMode(safety_mode)
        else:
            self.safety_mode = safety_mode
        self.max_retries = max_retries
        self.max_tool_calls = max_tool_calls
        self.dispatcher = dispatcher or ToolDispatcher(str(self.repo_path))
        self.traces: List[ToolTrace] = []

    def execute_model_tool_calls(self, model_output: str) -> List[ToolTrace]:
        """Parse and execute tool calls from model output."""
        calls = ToolCallParser.parse(model_output)
        traces = []

        for call in calls[:self.max_tool_calls]:
            trace = self._execute_single(call)
            traces.append(trace)

        self.traces.extend(traces)
        return traces

    def _execute_single(self, call: ToolCall) -> ToolTrace:
        """Execute a single tool call with safety checks and tracing."""
        trace = ToolTrace(
            call_id=str(uuid.uuid4())[:8],
            tool_name=call.tool_name,
            params=call.params,
            start_time=time.time(),
        )

        safety_error = self._check_safety(call)
        if safety_error:
            trace.error = safety_error
            trace.end_time = time.time()
            trace.latency_ms = round((trace.end_time - trace.start_time) * 1000, 1)
            result = ToolResult(success=False, error=safety_error)
            trace.result = result
            self._emit_trace(trace)
            return trace

        for attempt in range(self.max_retries + 1):
            trace.retry_count = attempt
            result = self.dispatcher.dispatch(call.tool_name, call.params)
            trace.result = result

            if result.success:
                break

            if attempt < self.max_retries and self._should_retry(result):
                continue
            break

        trace.end_time = time.time()
        trace.latency_ms = round((trace.end_time - trace.start_time) * 1000, 1)

        if not result.success:
            trace.error = result.error

        if result.success and result.output:
            trace.evidence = self._extract_evidence(call, result.output)

        self._emit_trace(trace)
        return trace

    def _check_safety(self, call: ToolCall) -> Optional[str]:
        """Check if a tool call is allowed in the current safety mode."""
        if self.safety_mode == SafetyMode.READONLY:
            disallowed = {"edit_file", "run_test"}
            if call.tool_name in disallowed:
                return (
                    f"Safety: '{call.tool_name}' not allowed in readonly mode. "
                    f"Available: read_file, grep_search, list_directory, git_log, inspect_ast"
                )

        if self.safety_mode == SafetyMode.CAREFUL:
            if call.tool_name == "edit_file":
                return (
                    f"Safety: '{call.tool_name}' requires user confirmation in careful mode. "
                    f"Use --safety full to allow edits."
                )

        return None

    def _should_retry(self, result: ToolResult) -> bool:
        """Determine if a failed tool call should be retried."""
        if not result.error:
            return False
        retryable_errors = ["timeout", "timed out", "not found", "no such file"]
        return any(e in result.error.lower() for e in retryable_errors)

    def _extract_evidence(self, call: ToolCall, output: str) -> str:
        """Extract evidence summary from tool output."""
        preview = output[:300].strip()
        return f"[{call.tool_name}] {preview[:200]}"

    def _emit_trace(self, trace: ToolTrace) -> None:
        """Emit audit trace for a tool call."""
        trace_data = trace.to_dict()
        trace_data["event"] = "tool_call"
        trace_data["repo"] = str(self.repo_path)
        trace_data["safety_mode"] = self.safety_mode.value

        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"tool-{trace.call_id}.json"
        trace_file.write_text(json.dumps(trace_data, indent=2))

    def format_tool_output_for_model(self, traces: List[ToolTrace]) -> str:
        """Format tool execution results for model consumption."""
        if not traces:
            return ""

        parts = ["\n[TOOL RESULTS]"]
        for t in traces:
            status = "OK" if t.result and t.result.success else "FAIL"
            parts.append(f"\nTOOL: {t.tool_name} [{status}] ({t.latency_ms:.0f}ms)")
            if t.result and t.result.output:
                parts.append(t.result.output[:1000])
            if t.error:
                parts.append(f"Error: {t.error}")
            if t.evidence:
                parts.append(f"Evidence: {t.evidence}")

        parts.append("\n[END TOOL RESULTS]")
        return "\n".join(parts)

    def get_stats(self) -> Dict:
        """Get tool session statistics."""
        if not self.traces:
            return {"tool_calls": 0}

        total_ms = sum(t.latency_ms for t in self.traces)
        failed = sum(1 for t in self.traces if t.result and not t.result.success)
        by_tool: Dict[str, int] = {}
        for t in self.traces:
            by_tool[t.tool_name] = by_tool.get(t.tool_name, 0) + 1

        return {
            "tool_calls": len(self.traces),
            "total_latency_ms": round(total_ms, 1),
            "avg_latency_ms": round(total_ms / len(self.traces), 1) if self.traces else 0,
            "failed": failed,
            "by_tool": by_tool,
        }

    def get_evidence_summary(self) -> List[str]:
        """Get all evidence collected during the session."""
        evidence = []
        for t in self.traces:
            if t.evidence:
                evidence.append(t.evidence)
        return evidence
