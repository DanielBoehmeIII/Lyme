"""FileSelector — dependency-aware file selection for coding tasks."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .planner import TaskPlan


@dataclass
class FileSelection:
    primary_files: List[str] = field(default_factory=list)
    context_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_files": self.primary_files,
            "context_files": self.context_files[:20],
            "test_files": self.test_files[:10],
            "total_primary": len(self.primary_files),
            "total_context": len(self.context_files),
            "total_tests": len(self.test_files),
            "reasoning": self.reasoning,
        }


class FileSelector:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self._import_graph: Dict[str, Set[str]] = {}
        self._build_import_graph()

    def _build_import_graph(self) -> None:
        for f in self.repo_path.rglob("*.py"):
            if ".git" in f.parts or "__pycache__" in f.parts:
                continue
            try:
                content = f.read_text(errors="replace")
                rel = str(f.relative_to(self.repo_path))
                imports: Set[str] = set()
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("import "):
                        parts = line[7:].split()
                        imports.add(parts[0].split(".")[0])
                    elif line.startswith("from "):
                        parts = line.split()
                        if len(parts) > 1:
                            imports.add(parts[1].split(".")[0])
                self._import_graph[rel] = imports
            except Exception:
                continue

    def select(self, task: str, plan: TaskPlan) -> FileSelection:
        task_lower = task.lower()
        keywords = {w for w in task_lower.split() if len(w) > 3}
        selection = FileSelection()

        # Score files by keyword match
        scored_files: List[tuple[float, str]] = []

        for fp in self._import_graph:
            score = 0.0
            path_lower = fp.lower()
            for kw in keywords:
                if kw in path_lower:
                    score += 2.0
            if score > 0:
                scored_files.append((score, fp))

        # Handle no matches
        if not scored_files:
            for fp in sorted(self._import_graph.keys()):
                scored_files.append((0.5, fp))
                if len(scored_files) >= 10:
                    break

        scored_files.sort(key=lambda x: x[0], reverse=True)

        # Primary files: top matches
        for _, fp in scored_files[:5]:
            if self._is_source_file(fp):
                selection.primary_files.append(fp)

        # Context files: imports of primary files
        primary_imports: Set[str] = set()
        for fp in selection.primary_files:
            for imp in self._import_graph.get(fp, set()):
                primary_imports.add(imp)

        for imp in primary_imports:
            for fp in self._import_graph:
                if imp in fp.replace("/", ".").replace(".py", ""):
                    if fp not in selection.primary_files and fp not in selection.context_files:
                        selection.context_files.append(fp)

        # Test files
        for fp in self._import_graph:
            name = Path(fp).name
            is_test = name.startswith("test_") or name.endswith("_test.py")
            if is_test:
                # Check if test imports any primary file
                test_imports = self._import_graph.get(fp, set())
                for pf in selection.primary_files:
                    module_name = pf.replace("/", ".").replace(".py", "")
                    if any(module_name in imp for imp in test_imports):
                        selection.test_files.append(fp)
                        break

        if not selection.test_files:
            for fp in self._import_graph:
                name = Path(fp).name
                if name.startswith("test_") or name.endswith("_test.py"):
                    selection.test_files.append(fp)
                    if len(selection.test_files) >= 5:
                        break

        selection.reasoning = (
            f"Found {len(selection.primary_files)} primary files by keyword match, "
            f"{len(selection.context_files)} context files by import dependencies, "
            f"{len(selection.test_files)} test files"
        )

        return selection

    def _is_source_file(self, fp: str) -> bool:
        name = Path(fp).name
        return not name.startswith("test_") and not name.endswith("_test.py")
