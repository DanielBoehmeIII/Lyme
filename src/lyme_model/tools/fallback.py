"""Tool fallback chain and error recovery for Lyme Model."""

from typing import Optional, Dict, Any
from .dispatch import ToolDispatcher, ToolResult


class ToolFallback:
    """Chain of fallback strategies when a tool fails."""

    def __init__(self, dispatcher: ToolDispatcher):
        self.dispatcher = dispatcher

    def try_with_fallback(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Try a tool, fall back to simpler alternatives on failure."""
        result = self.dispatcher.dispatch(tool_name, params)
        if result.success:
            return result

        fallbacks = {
            "inspect_ast": self._fallback_from_ast,
            "run_test": self._fallback_from_test,
            "edit_file": self._fallback_from_edit,
        }

        fallback_fn = fallbacks.get(tool_name)
        if fallback_fn:
            return fallback_fn(params, result)
        return result

    def _fallback_from_ast(self, params: dict, original: ToolResult) -> ToolResult:
        """Fallback: read the file directly if AST parsing fails."""
        return self.dispatcher.dispatch("read_file", params)

    def _fallback_from_test(self, params: dict, original: ToolResult) -> ToolResult:
        """Fallback: try running without -x flag."""
        return self.dispatcher.dispatch("run_test", {**params, "_no_x": True})

    def _fallback_from_edit(self, params: dict, original: ToolResult) -> ToolResult:
        """Fallback: report the error clearly."""
        return ToolResult(
            success=False,
            error=f"Edit failed: {original.error}. Suggestion: check file path and permissions.",
        )
