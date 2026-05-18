"""Imports — import resolution and dependency graph construction."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ImportEdge:
    source: str
    target: str
    symbol: str = ""
    is_local: bool = True
    is_test: bool = False
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "symbol": self.symbol,
            "is_local": self.is_local,
            "is_test": self.is_test,
            "weight": self.weight,
        }


@dataclass
class ImportGraph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[ImportEdge] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    _adj: Dict[str, Set[str]] = field(default_factory=dict)

    def add_edge(self, edge: ImportEdge) -> None:
        self.edges.append(edge)
        if edge.source not in self._adj:
            self._adj[edge.source] = set()
        if edge.target:
            self._adj[edge.source].add(edge.target)
        if edge.source not in self.nodes:
            self.nodes[edge.source] = {"file_path": edge.source}
        if edge.target and edge.target not in self.nodes:
            self.nodes[edge.target] = {"file_path": edge.target}

    def detect_cycles(self) -> List[List[str]]:
        visited: Set[str] = set()
        path_stack: List[str] = []
        cycles: List[List[str]] = []

        def dfs(node: str) -> None:
            if node in path_stack:
                cycle_start = path_stack.index(node)
                cycle = path_stack[cycle_start:] + [node]
                cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            path_stack.append(node)
            for dep in self._adj.get(node, []):
                dfs(dep)
            path_stack.pop()

        for node in list(self._adj.keys()):
            dfs(node)

        seen = set()
        deduped = []
        for cycle in cycles:
            key = " -> ".join(sorted(set(cycle)))
            if key not in seen:
                seen.add(key)
                deduped.append(cycle)
        self.cycles = deduped
        return deduped

    def downstream(self, file_path: str) -> Set[str]:
        result: Set[str] = set()
        visited: Set[str] = set()
        stack = [file_path]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if node != file_path:
                result.add(node)
            for edge in self.edges:
                if edge.source == node and edge.target:
                    stack.append(edge.target)
        return result

    def upstream(self, file_path: str) -> Set[str]:
        result: Set[str] = set()
        for edge in self.edges:
            if edge.target == file_path:
                result.add(edge.source)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "cycle_count": len(self.cycles),
            "nodes": list(self.nodes.keys()),
            "edges": [e.to_dict() for e in self.edges],
            "cycles": self.cycles,
        }


class ImportResolver:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root).resolve()
        self._stdlib_modules: Set[str] = set()

    def resolve(self, module_name: str, from_file: str) -> Optional[str]:
        if module_name in self._stdlib_modules:
            return None

        from_path = Path(from_file)
        is_local = module_name.startswith(".") or module_name.startswith(from_path.parent.name)

        if module_name.startswith("."):
            relative = module_name.lstrip(".")
            parent = from_path.parent
            depth = len(module_name) - len(relative) - 1
            for _ in range(depth):
                parent = parent.parent
            candidate = (parent / relative).resolve()
            if candidate.is_dir():
                init_py = candidate / "__init__.py"
                if init_py.exists():
                    return str(init_py)
            elif candidate.exists():
                return str(candidate)
            for ext in [".py", ".pyi"]:
                with_ext = candidate.with_suffix(ext) if candidate.suffix != ext else candidate
                if with_ext.exists():
                    return str(with_ext)
            return None

        # Try direct match
        module_path = module_name.replace(".", "/")
        for base in [from_path.parent, self.repo_root]:
            file_candidate = base / f"{module_path}.py"
            if file_candidate.exists():
                return str(file_candidate)
            file_candidate = base / f"{module_path}.pyi"
            if file_candidate.exists():
                return str(file_candidate)
            init_candidate = base / module_path / "__init__.py"
            if init_candidate.exists():
                return str(init_candidate)

        # Try from repo root
        file_candidate = self.repo_root / f"{module_path}.py"
        if file_candidate.exists():
            return str(file_candidate)
        file_candidate = self.repo_root / f"{module_path}.pyi"
        if file_candidate.exists():
            return str(file_candidate)
        init_candidate = self.repo_root / module_path / "__init__.py"
        if init_candidate.exists():
            return str(init_candidate)

        return None

    def build_graph(self, file_imports: Dict[str, List[str]]) -> ImportGraph:
        graph = ImportGraph()
        for file_path, imports in file_imports.items():
            for imp in imports:
                resolved = self.resolve(imp, file_path)
                edge = ImportEdge(
                    source=file_path,
                    target=resolved or imp,
                    symbol=imp,
                    is_local=resolved is not None,
                )
                graph.add_edge(edge)
        graph.detect_cycles()
        return graph
