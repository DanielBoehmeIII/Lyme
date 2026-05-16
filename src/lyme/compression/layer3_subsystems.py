from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class SubsystemLayer:
    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def extract(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        repo_path = Path(repo_path).resolve()
        self._graph.clear()
        self._reverse_graph.clear()

        python_files = []
        js_files = []
        for f in repo_path.rglob("*"):
            if not f.is_file():
                continue
            if any(p.startswith(".") or p == "__pycache__" or p == "node_modules"
                   for p in f.parts):
                continue
            if f.suffix == ".py":
                python_files.append(f)
            elif f.suffix in (".js", ".ts", ".tsx", ".jsx"):
                js_files.append(f)

        for f in python_files:
            self._trace_python_imports(f, repo_path)
        for f in js_files:
            self._trace_js_imports(f, repo_path)

        subsystems = self._cluster_subsystems(repo_path)
        subsystem_graph = self._build_subsystem_graph(subsystems, repo_path)
        circular_deps = self._find_circular_dependencies()

        return {
            "subsystems": subsystems,
            "subsystem_dependency_graph": subsystem_graph,
            "total_files_in_graph": len(self._graph),
            "circular_dependencies": circular_deps,
            "import_edges": [
                {"source": src, "targets": sorted(tgts)}
                for src, tgts in sorted(self._graph.items())
            ],
        }

    def _trace_python_imports(self, filepath: Path, repo_root: Path) -> None:
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (SyntaxError, Exception):
            return

        rel = self._relative(filepath, repo_root)
        targets: Set[str] = set()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.level is not None and node.level > 0:
                    base = Path(*filepath.parts[:-node.level])
                    if node.module:
                        resolved = (base / node.module.replace(".", "/")).resolve()
                    else:
                        resolved = base.resolve()
                    try:
                        r = self._relative(resolved, repo_root)
                        targets.add(r)
                    except ValueError:
                        pass
                elif node.module:
                    targets.add(node.module.replace(".", "/"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    targets.add(alias.name.replace(".", "/"))

        for t in targets:
            self._graph[rel].add(t)
            self._reverse_graph[t].add(rel)

    def _trace_js_imports(self, filepath: Path, repo_root: Path) -> None:
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        rel = self._relative(filepath, repo_root)
        targets: Set[str] = set()

        patterns = [
            r"""from\s+['"]([^'"]+)['"]""",
            r"""require\s*\(\s*['"]([^'"]+)['"]""",
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                mod = m.group(1)
                if mod.startswith("."):
                    base = filepath.parent
                    parts = mod.split("/")
                    for p in parts:
                        if p == "..":
                            base = base.parent
                        elif p == ".":
                            continue
                        else:
                            base = base / p
                    try:
                        r = self._relative(base, repo_root)
                        targets.add(r)
                    except ValueError:
                        pass
                else:
                    targets.add(mod.replace("/", "/"))

        for t in targets:
            self._graph[rel].add(t)
            self._reverse_graph[t].add(rel)

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        try:
            return str(filepath.relative_to(repo_root))
        except ValueError:
            raise

    def _cluster_subsystems(self, repo_root: Path) -> Dict[str, List[str]]:
        subsystems: Dict[str, List[str]] = {}
        for filepath in sorted(self._graph.keys()):
            parts = Path(filepath).parts
            if len(parts) >= 2:
                subsystem = parts[0]
            else:
                subsystem = "/"
            subsystems.setdefault(subsystem, []).append(filepath)

        top_level = subsystems.pop("/", [])
        for f in top_level:
            if f.endswith(".py"):
                stem = Path(f).stem
                if stem not in subsystems:
                    subsystems[stem] = []
                subsystems[stem].append(f)

        return dict(sorted(subsystems.items()))

    def _build_subsystem_graph(
        self, subsystems: Dict[str, List[str]], repo_root: Path
    ) -> Dict[str, List[Dict[str, Any]]]:
        sub_deps: Dict[str, Set[str]] = defaultdict(set)
        for src, targets in self._graph.items():
            src_sub = self._file_to_subsystem(src, subsystems)
            for tgt in targets:
                tgt_sub = self._file_to_subsystem(tgt, subsystems)
                if src_sub and tgt_sub and src_sub != tgt_sub:
                    sub_deps[src_sub].add(tgt_sub)

        return {
            sub: [{"target": t, "edge_count": 1} for t in sorted(deps)]
            for sub, deps in sorted(sub_deps.items())
        }

    def _file_to_subsystem(self, filepath: str, subsystems: Dict[str, List[str]]) -> str:
        for sub, files in subsystems.items():
            if filepath in files:
                return sub
        parts = Path(filepath).parts
        return parts[0] if parts else "/"

    def _find_circular_dependencies(self) -> List[Dict[str, Any]]:
        cycles: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if self._is_notable_cycle(cycle):
                        cycles.append({
                            "cycle": cycle,
                            "length": len(cycle) - 1,
                        })
            path.pop()
            rec_stack.discard(node)

        for node in list(self._graph.keys()):
            if node not in visited:
                dfs(node)

        return cycles

    def _is_notable_cycle(self, cycle: List[str]) -> bool:
        cutoff = 20
        if len(cycle) > cutoff:
            return False
        key = " -> ".join(sorted(set(cycle)))
        for existing in cycles:
            existing_key = " -> ".join(sorted(set(existing.get("cycle", []))))
            if key == existing_key:
                return False
        return True
