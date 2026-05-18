"""ToolUseFramework — planned tool execution integrated with agent loop."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ToolType(Enum):
    READ = "read"
    SEARCH = "search"
    EDIT = "edit"
    TEST = "test"
    GIT = "git"
    BROWSER = "browser"
    DOCS = "docs"
    PACKAGE = "package"
    TERMINAL = "terminal"


@dataclass
class ToolCall:
    tool_type: ToolType
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.tool_type.value,
            "params": self.params,
            "description": self.description[:80],
        }


@dataclass
class ToolResult:
    tool_call_id: str = ""
    success: bool = False
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output[:200],
            "error": self.error[:200] if self.error else None,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ToolPlan:
    goal: str = ""
    calls: List[ToolCall] = field(default_factory=list)
    results: List[ToolResult] = field(default_factory=list)

    def add_call(self, call: ToolCall) -> None:
        self.calls.append(call)

    def add_result(self, result: ToolResult) -> None:
        self.results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal[:80],
            "calls": [c.to_dict() for c in self.calls],
            "results": [r.to_dict() for r in self.results],
        }


class ToolUseFramework:
    def __init__(self):
        self._handlers: Dict[ToolType, Callable] = {}

    def register_handler(self, tool_type: ToolType, handler: Callable) -> None:
        self._handlers[tool_type] = handler

    def plan_for_task(self, task: str) -> ToolPlan:
        plan = ToolPlan(goal=task)
        task_lower = task.lower()

        # Always search first
        plan.add_call(ToolCall(
            tool_type=ToolType.SEARCH,
            params={"query": task},
            description="Search repository for relevant files",
        ))

        # Read
        plan.add_call(ToolCall(
            tool_type=ToolType.READ,
            params={"files": []},
            description="Read relevant files",
        ))

        # Edit or test based on task
        if any(kw in task_lower for kw in ("test", "verify", "check")):
            plan.add_call(ToolCall(
                tool_type=ToolType.TEST,
                params={},
                description="Run tests",
            ))
        else:
            plan.add_call(ToolCall(
                tool_type=ToolType.EDIT,
                params={},
                description="Apply code changes",
            ))
            plan.add_call(ToolCall(
                tool_type=ToolType.TEST,
                params={},
                description="Verify changes with tests",
            ))

        return plan

    def execute(self, plan: ToolPlan) -> ToolPlan:
        for call in plan.calls:
            handler = self._handlers.get(call.tool_type)
            if handler:
                try:
                    output = handler(call.params)
                    plan.add_result(ToolResult(
                        tool_call_id=call.id,
                        success=True,
                        output=str(output)[:500],
                    ))
                except Exception as e:
                    plan.add_result(ToolResult(
                        tool_call_id=call.id,
                        success=False,
                        error=str(e),
                    ))
            else:
                plan.add_result(ToolResult(
                    tool_call_id=call.id,
                    success=False,
                    error=f"No handler for {call.tool_type.value}",
                ))
        return plan
