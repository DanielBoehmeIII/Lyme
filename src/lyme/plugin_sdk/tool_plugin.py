"""ToolPlugin — plugin for custom tools."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    name: str = ""
    description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    handler: Optional[Callable] = None


class ToolPlugin:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description,
             "parameters": len(t.parameters)}
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        tool = self._tools.get(tool_name)
        if not tool:
            raise KeyError(f"Unknown tool: {tool_name}")
        if tool.handler:
            return tool.handler(**params)
        raise RuntimeError(f"Tool '{tool_name}' has no handler")
