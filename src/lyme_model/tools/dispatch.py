"""Tool execution and result processing for Lyme Model."""

import subprocess, os, json, ast, re
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from .registry import ToolRegistry, ToolDef


@dataclass
class ToolResult:
    success: bool = False
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class ToolDispatcher:
    """Executes tools and processes results."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.registry = ToolRegistry()

    def dispatch(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

        handlers = {
            "read_file": self._read_file,
            "grep_search": self._grep_search,
            "list_directory": self._list_directory,
            "run_test": self._run_test,
            "edit_file": self._edit_file,
            "git_log": self._git_log,
            "inspect_ast": self._inspect_ast,
            "verify_change": self._verify_change,
            "think": self._think,
            "ask_for_help": self._ask_for_help,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return ToolResult(success=False, error=f"No handler for tool: {tool_name}")

        try:
            self.registry.record_call(tool_name, True)
            return handler(params)
        except Exception as e:
            self.registry.record_call(tool_name, False)
            return ToolResult(success=False, error=str(e))

    def _read_file(self, params: dict) -> ToolResult:
        path = self.repo_path / params.get("path", "")
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if path.is_dir():
            return ToolResult(success=False, error=f"Path is a directory, use list_directory")
        content = path.read_text(encoding="utf-8", errors="replace")
        return ToolResult(success=True, output=content)

    def _grep_search(self, params: dict) -> ToolResult:
        pattern = params.get("pattern", "")
        search_path = params.get("path", ".")
        full_path = self.repo_path / search_path
        try:
            # Use rg if available, fallback to grep
            rg = subprocess.run(
                ["rg", "-n", pattern, str(full_path)],
                capture_output=True, text=True, timeout=10
            )
            if rg.returncode == 0 and rg.stdout.strip():
                return ToolResult(success=True, output=rg.stdout[:2000])
            # Fallback to grep -r
            grep = subprocess.run(
                ["grep", "-rn", pattern, str(full_path)],
                capture_output=True, text=True, timeout=10
            )
            if grep.stdout.strip():
                return ToolResult(success=True, output=grep.stdout[:2000])
            return ToolResult(success=True, output=f"No matches for '{pattern}'")
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Search timed out")
        except FileNotFoundError:
            return ToolResult(success=False, error="grep/rg not available")

    def _list_directory(self, params: dict) -> ToolResult:
        path = self.repo_path / params.get("path", ".")
        if not path.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")
        items = []
        for f in sorted(path.iterdir()):
            suffix = "/" if f.is_dir() else ""
            items.append(f.name + suffix)
        return ToolResult(success=True, output="\n".join(items))

    def _run_test(self, params: dict) -> ToolResult:
        target = params.get("target", "")
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", target, "-v", "--no-header", "-x"],
                capture_output=True, text=True, timeout=60, cwd=str(self.repo_path)
            )
            output = result.stdout + "\n" + result.stderr
            success = result.returncode == 0
            return ToolResult(success=success, output=output[:1000])
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Test timed out (60s)")

    def _edit_file(self, params: dict) -> ToolResult:
        path = self.repo_path / params.get("path", "")
        content = params.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")

    def _git_log(self, params: dict) -> ToolResult:
        try:
            cmd = ["git", "log", "--oneline", "-n", str(params.get("count", 5))]
            if params.get("path"):
                cmd.extend(["--", params["path"]])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                    cwd=str(self.repo_path))
            return ToolResult(success=True, output=result.stdout[:1000])
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _inspect_ast(self, params: dict) -> ToolResult:
        path = self.repo_path / params.get("path", "")
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        try:
            tree = ast.parse(path.read_text())
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            imports = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports.extend(alias.name for alias in n.names)
                elif isinstance(n, ast.ImportFrom):
                    module = n.module or ""
                    imports.extend(f"{module}.{alias.name}" for alias in n.names)
            result = {
                "classes": classes,
                "functions": functions,
                "imports": imports,
            }
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except SyntaxError as e:
            return ToolResult(success=False, error=f"Syntax error: {e}")

    def _verify_change(self, params: dict) -> ToolResult:
        path = self.repo_path / params.get("path", "")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text())
                return ToolResult(success=True, output="Syntax OK")
            except SyntaxError as e:
                return ToolResult(success=False, error=f"Syntax error: {e}")
        return ToolResult(success=True, output=f"File exists ({path.stat().st_size} bytes)")

    def _think(self, params: dict) -> ToolResult:
        return ToolResult(success=True, output=f"[Thinking: {params.get('thought', '')[:500]}]")

    def _ask_for_help(self, params: dict) -> ToolResult:
        return ToolResult(success=True, output=f"[HELP REQUESTED: {params.get('question', '')}]")


class ToolUseOptimizer:
    """Optimizes tool selection and usage for small models."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def minimize_for_task(self, task_type: str) -> list:
        """Return minimal tool set for a given task type."""
        minimal = {
            "bugfix": ["read_file", "grep_search", "edit_file", "run_test", "think"],
            "feature": ["read_file", "list_directory", "edit_file", "run_test", "think"],
            "refactor": ["read_file", "grep_search", "edit_file", "run_test", "verify_change", "think"],
            "qa": ["read_file", "grep_search", "list_directory", "think"],
            "test": ["read_file", "edit_file", "run_test", "think"],
        }
        names = minimal.get(task_type, ["read_file", "grep_search", "edit_file", "think"])
        return [self.registry.get(n) for n in names if self.registry.get(n)]
