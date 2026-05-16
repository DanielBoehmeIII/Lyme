"""Tool definitions and metadata for Lyme Model.

Defines the available tools with descriptions, parameters, and success tracking.
Optimized for small models: fewer tools, better descriptions, cached schemas.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from enum import Enum


class ToolCategory(str, Enum):
    READ = "read"
    SEARCH = "search"
    EDIT = "edit"
    TEST = "test"
    ANALYSIS = "analysis"
    VERIFY = "verify"
    META = "meta"  # thinking, planning, asking for help


@dataclass
class ToolDef:
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, str]  # param_name -> description
    examples: List[str] = field(default_factory=list)
    cost_estimate: str = "fast"  # fast, medium, slow
    requires_file_context: bool = False
    enabled_for_small_models: bool = True

    def to_prompt(self) -> str:
        """Return tool description formatted for a small model prompt."""
        params_str = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"- {self.name}({params_str}): {self.description}"


# Core tool set for Lyme Model — minimum viable, maximum clarity
CORE_TOOLS = [
    ToolDef(
        name="read_file",
        description="Read the contents of a file. Use when you need to see the full implementation.",
        category=ToolCategory.READ,
        parameters={"path": "File path relative to repo root"},
        examples=["read_file(src/main.py)"],
        cost_estimate="fast",
    ),
    ToolDef(
        name="grep_search",
        description="Search for a pattern in the codebase. Use when you need to find where something is used or defined.",
        category=ToolCategory.SEARCH,
        parameters={"pattern": "Regex pattern to search for", "path": "Optional path to limit search"},
        examples=["grep_search(def login)", "grep_search(TODO, src/)"],
        cost_estimate="fast",
    ),
    ToolDef(
        name="list_directory",
        description="List files in a directory. Use to explore the project structure.",
        category=ToolCategory.READ,
        parameters={"path": "Directory path relative to repo root"},
        examples=["list_directory(src/)"],
        cost_estimate="fast",
    ),
    ToolDef(
        name="run_test",
        description="Run a specific test file or test function. Use to verify changes don't break existing behavior.",
        category=ToolCategory.TEST,
        parameters={"target": "Test file path or test name"},
        examples=["run_test(tests/test_api.py)", "run_test(tests/test_api.py::test_login)"],
        cost_estimate="slow",
    ),
    ToolDef(
        name="edit_file",
        description="Create or modify a file. Provide the full path and new content. Use when you need to make changes.",
        category=ToolCategory.EDIT,
        parameters={"path": "File path", "content": "New file content (the complete file)"},
        examples=["edit_file(src/main.py, ...)"],
        cost_estimate="medium",
    ),
    ToolDef(
        name="git_log",
        description="View recent git history. Use to understand recent changes in a file or directory.",
        category=ToolCategory.ANALYSIS,
        parameters={"path": "Optional path to filter history", "count": "Number of entries (default 5)"},
        examples=["git_log(src/main.py, 10)"],
        cost_estimate="fast",
    ),
    ToolDef(
        name="inspect_ast",
        description="Parse and analyze the AST of a Python file. Returns classes, functions, and their signatures.",
        category=ToolCategory.ANALYSIS,
        parameters={"path": "Python file path"},
        examples=["inspect_ast(src/models.py)"],
        cost_estimate="fast",
    ),
    ToolDef(
        name="think",
        description="Use this to reason about the problem before taking action. Describe your plan, what you know, and what you need to find out.",
        category=ToolCategory.META,
        parameters={"thought": "Your reasoning about the current situation"},
        examples=[],
        cost_estimate="fast",
    ),
    ToolDef(
        name="verify_change",
        description="Verify that a change is correct by running tests or checking syntax. Use after every edit.",
        category=ToolCategory.VERIFY,
        parameters={"path": "Path to the changed file"},
        examples=["verify_change(src/main.py)"],
        cost_estimate="medium",
    ),
    ToolDef(
        name="ask_for_help",
        description="Ask the user for clarification when the task is ambiguous or you're stuck.",
        category=ToolCategory.META,
        parameters={"question": "What you need clarification on"},
        examples=[],
        cost_estimate="fast",
    ),
]

# Minimal set for 3B models (fewer tools, simpler descriptions)
MINIMAL_TOOLS = [
    ToolDef(name="read_file", description="Read a file", category=ToolCategory.READ,
            parameters={"path": "File path"}),
    ToolDef(name="grep_search", description="Search code", category=ToolCategory.SEARCH,
            parameters={"pattern": "Search term"}),
    ToolDef(name="edit_file", description="Edit or create a file", category=ToolCategory.EDIT,
            parameters={"path": "File path", "content": "New content"}),
    ToolDef(name="run_test", description="Run a test", category=ToolCategory.TEST,
            parameters={"target": "Test to run"}),
    ToolDef(name="think", description="Think step by step", category=ToolCategory.META,
            parameters={"thought": "Your thinking"}),
    ToolDef(name="ask_for_help", description="Ask user for help", category=ToolCategory.META,
            parameters={"question": "What you need"}),
]


class ToolRegistry:
    """Registry of available tools with metadata and success tracking."""

    def __init__(self, tools: Optional[List[ToolDef]] = None):
        self._tools: Dict[str, ToolDef] = {}
        self._success_rates: Dict[str, float] = {}
        self._call_counts: Dict[str, int] = {}
        for tool in (tools or CORE_TOOLS):
            self.register(tool)

    def register(self, tool: ToolDef):
        self._tools[tool.name] = tool
        self._success_rates[tool.name] = 1.0
        self._call_counts[tool.name] = 0

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def all_tools(self) -> List[ToolDef]:
        return list(self._tools.values())

    def by_category(self, category: ToolCategory) -> List[ToolDef]:
        return [t for t in self._tools.values() if t.category == category]

    def prompt_for_model(self, model_size: str = "7b") -> str:
        """Generate tool description text optimized for the model size."""
        if model_size == "3b":
            tools = MINIMAL_TOOLS
        else:
            tools = CORE_TOOLS

        lines = ["Available tools:", ""]
        # Group by category
        categories = {}
        for tool in tools:
            categories.setdefault(tool.category, []).append(tool)

        for cat in [ToolCategory.READ, ToolCategory.SEARCH, ToolCategory.EDIT,
                     ToolCategory.TEST, ToolCategory.ANALYSIS, ToolCategory.VERIFY,
                     ToolCategory.META]:
            if cat in categories:
                lines.append(f"[{cat.value.upper()}]")
                for tool in categories[cat]:
                    lines.append(tool.to_prompt())
                lines.append("")

        lines.append("Use tools by writing TOOL: tool_name(param=value)")
        return "\n".join(lines)

    def record_call(self, tool_name: str, success: bool):
        self._call_counts[tool_name] = self._call_counts.get(tool_name, 0) + 1
        n = self._call_counts[tool_name]
        old = self._success_rates.get(tool_name, 1.0)
        self._success_rates[tool_name] = (old * (n - 1) + (1.0 if success else 0.0)) / n

    def get_stats(self) -> Dict:
        return {
            "tools": list(self._tools.keys()),
            "call_counts": self._call_counts,
            "success_rates": self._success_rates,
        }
