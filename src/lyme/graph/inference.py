from __future__ import annotations

import ast
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .causal_graph import CausalGraph, CausalNode, CausalEdge, CausalRelationType, NodeType


class CoChangeAnalyzer:
    def __init__(self, window_size: int = 100, min_cooccurrences: int = 2):
        self.window_size = window_size
        self.min_cooccurrences = min_cooccurrences

    def analyze(self, repo_path: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []
        cooccurrence: Dict[Tuple[str, str], List[int]] = defaultdict(list)
        file_change_order: Dict[str, int] = {}
        commit_sequence: List[List[str]] = []

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H", "--name-only",
                 "--diff-filter=AM", f"-{self.window_size}"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return edges

            current_commit: Optional[str] = None
            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^[a-f0-9]{40}$", line):
                    if current_commit and len(current_files) >= 2:
                        commit_sequence.append(current_files)
                    current_commit = line
                    current_files = []
                else:
                    current_files.append(line)
            if current_commit and len(current_files) >= 2:
                commit_sequence.append(current_files)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return edges

        for seq_idx, files in enumerate(commit_sequence):
            for i, f1 in enumerate(files):
                file_change_order[f1] = seq_idx
                for f2 in files[i + 1:]:
                    key = (f1, f2) if f1 < f2 else (f2, f1)
                    cooccurrence[key].append(seq_idx)

        for (f1, f2), commit_indices in cooccurrence.items():
            if len(commit_indices) < self.min_cooccurrences:
                continue

            source_node = graph.find_node_by_name(f1)
            target_node = graph.find_node_by_name(f2)
            if not source_node or not target_node:
                continue

            freq = len(commit_indices)
            spread = max(commit_indices) - min(commit_indices) + 1 if len(commit_indices) > 1 else 1
            confidence = min(1.0, (freq / self.window_size) * (1.0 + 1.0 / spread))

            edge = CausalEdge(
                source_id=source_node.id,
                target_id=target_node.id,
                relation_type=CausalRelationType.CO_CHANGE,
                weight=freq / self.window_size,
                confidence=min(confidence, 1.0),
                frequency=freq,
                evidence_sources=[f"co-change in {freq} commits over {spread} commits"],
                temporal_ordering="concurrent",
            )
            edges.append(edge)

        return edges


class ImportGraphAnalyzer:
    def analyze(self, repo_path: Path, files: List[Path], graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        for f in files:
            if f.suffix == ".py":
                py_edges = self._analyze_python_imports(f, repo_path, graph)
                edges.extend(py_edges)
            elif f.suffix in (".js", ".ts", ".tsx", ".jsx"):
                js_edges = self._analyze_js_imports(f, repo_path, graph)
                edges.extend(js_edges)

        return edges

    def _analyze_python_imports(self, filepath: Path, repo_root: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges = []
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (SyntaxError, Exception):
            return edges

        rel_path = self._relative(filepath, repo_root)
        source_node = graph.find_node_by_name(rel_path)
        if not source_node:
            return edges

        for node in ast.iter_child_nodes(tree):
            targets: List[str] = []
            if isinstance(node, ast.ImportFrom):
                if node.module and node.level is not None and node.level > 0:
                    base = Path(*filepath.parts[:-node.level])
                    if node.module:
                        resolved = (base / node.module.replace(".", "/")).resolve()
                    else:
                        resolved = base.resolve()
                    try:
                        targets.append(self._relative(resolved, repo_root))
                    except ValueError:
                        targets.append(node.module)
                elif node.module:
                    targets.append(node.module.replace(".", "/"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    targets.append(alias.name.replace(".", "/"))

            for tgt in targets:
                target_node = graph.find_node_by_name(tgt)
                if target_node:
                    edge = CausalEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation_type=CausalRelationType.IMPORT,
                        weight=1.0,
                        confidence=0.95,
                        evidence_sources=["static import analysis"],
                        temporal_ordering="source_before_target",
                        frequency=1,
                    )
                    edges.append(edge)

        return edges

    def _analyze_js_imports(self, filepath: Path, repo_root: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges = []
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return edges

        rel_path = self._relative(filepath, repo_root)
        source_node = graph.find_node_by_name(rel_path)
        if not source_node:
            return edges

        patterns = [
            r"""from\s+['"]([^'"]+)['"]""",
            r"""require\s*\(\s*['"]([^'"]+)['"]""",
        ]
        targets = []
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
                        targets.append(self._relative(base, repo_root))
                    except ValueError:
                        pass
                else:
                    targets.append(mod.replace("/", "/"))

        for tgt in targets:
            target_node = graph.find_node_by_name(tgt)
            if target_node:
                edge = CausalEdge(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    relation_type=CausalRelationType.IMPORT,
                    weight=1.0,
                    confidence=0.9,
                    evidence_sources=["static import analysis"],
                    temporal_ordering="source_before_target",
                )
                edges.append(edge)

        return edges

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        return str(filepath.relative_to(repo_root))


class DataFlowAnalyzer:
    def analyze(self, repo_path: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = self._relative(f, repo_path)
            source_node = graph.find_node_by_name(rel_path)
            if not source_node:
                continue

            calls = self._extract_calls(tree)
            for call_name in calls:
                target_node = graph.find_node_by_name(call_name)
                if target_node:
                    edge = CausalEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation_type=CausalRelationType.DATA_FLOW,
                        weight=0.7,
                        confidence=0.6,
                        evidence_sources=["function call analysis"],
                        temporal_ordering="source_before_target",
                    )
                    edges.append(edge)

            shared_vars = self._extract_shared_variable_refs(tree)
            for var_name, var_value in shared_vars:
                target_node = graph.find_node_by_name(var_value)
                if target_node:
                    edge = CausalEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation_type=CausalRelationType.DATA_FLOW,
                        weight=0.5,
                        confidence=0.4,
                        evidence_sources=[f"shared variable reference: {var_name}"],
                    )
                    edges.append(edge)

        return edges

    def _extract_calls(self, tree: ast.AST) -> List[str]:
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
        return calls[:50]

    def _extract_shared_variable_refs(self, tree: ast.AST) -> List[Tuple[str, str]]:
        refs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
                        refs.append((target.id, node.value.id))
        return refs[:30]

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        return str(filepath.relative_to(repo_root))


class ApiContractAnalyzer:
    def analyze(self, repo_path: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        api_consumers: Dict[str, Set[str]] = defaultdict(set)
        api_providers: Dict[str, Set[str]] = defaultdict(set)

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = self._relative(f, repo_path)
            source_node = graph.find_node_by_name(rel_path)
            if not source_node:
                continue

            decorators = self._extract_decorators(tree)
            for dec in decorators:
                if dec in ("route", "app.route", "bp.route", "api.route", "get", "post", "put", "delete", "patch"):
                    api_providers["api_endpoint"].add(rel_path)

            imports = self._extract_imports(tree)
            for imp in imports:
                api_consumers[imp].add(rel_path)

        if api_providers.get("api_endpoint"):
            for api_file in api_providers["api_endpoint"]:
                api_node = graph.find_node_by_name(api_file)
                if not api_node:
                    continue
                for consumer_file in api_consumers.get(api_file, set()):
                    consumer_node = graph.find_node_by_name(consumer_file)
                    if consumer_node:
                        edge = CausalEdge(
                            source_id=consumer_node.id,
                            target_id=api_node.id,
                            relation_type=CausalRelationType.API_CALL,
                            weight=0.8,
                            confidence=0.7,
                            evidence_sources=["API contract: consumer-provider"],
                            temporal_ordering="source_before_target",
                        )
                        edges.append(edge)

        return edges

    def _extract_decorators(self, tree: ast.AST) -> List[str]:
        decs = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Attribute):
                        decs.append(f"{dec.value}.{dec.attr}" if hasattr(dec.value, 'id') else dec.attr)
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        decs.append(f"{dec.func.value}.{dec.func.attr}" if hasattr(dec.func.value, 'id') else dec.func.attr)
                    elif isinstance(dec, ast.Name):
                        decs.append(dec.id)
        return decs

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
        return imports

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        return str(filepath.relative_to(repo_root))


class TestCouplingAnalyzer:
    def analyze(self, repo_path: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        test_files: List[Path] = []
        source_files: List[Path] = []
        for f in repo_path.rglob("*"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in f.parts):
                continue
            if "test" in f.stem.lower() or f.stem.startswith("test_"):
                test_files.append(f)
            elif f.suffix in (".py", ".js", ".ts", ".tsx", ".jsx"):
                source_files.append(f)

        test_imports: Dict[str, Set[str]] = defaultdict(set)
        for test_file in test_files:
            try:
                text = test_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel_test = self._relative(test_file, repo_path)
            test_name = test_file.stem.replace("test_", "").replace("_test", "")

            for source_file in source_files:
                source_stem = source_file.stem
                if source_stem in text or test_name == source_stem:
                    test_imports[rel_test].add(self._relative(source_file, repo_path))

            if test_file.suffix == ".py":
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module:
                                for source_file in source_files:
                                    source_rel = self._relative(source_file, repo_path)
                                    source_mod = source_rel.replace("/", ".").replace(".py", "")
                                    if source_mod == node.module or node.module in source_mod or source_mod in node.module:
                                        test_imports[rel_test].add(source_rel)
                except SyntaxError:
                    pass

        for test_path, source_paths in test_imports.items():
            test_node = graph.find_node_by_name(test_path)
            if not test_node:
                continue
            for src_path in source_paths:
                src_node = graph.find_node_by_name(src_path)
                if src_node:
                    edge = CausalEdge(
                        source_id=test_node.id,
                        target_id=src_node.id,
                        relation_type=CausalRelationType.TEST_COUPLING,
                        weight=0.6,
                        confidence=0.5,
                        evidence_sources=["test imports source module"],
                    )
                    edges.append(edge)

        return edges

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        return str(filepath.relative_to(repo_root))


class SharedStateAnalyzer:
    def analyze(self, repo_path: Path, graph: CausalGraph, files: Optional[List[Path]] = None) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        global_state_refs: Dict[str, Set[str]] = defaultdict(set)

        if files is None:
            files = list(repo_path.rglob("*.py"))

        for f in files:
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = self._relative(f, repo_path)
            globals_in_file = self._extract_global_assignments(tree)
            for g in globals_in_file:
                global_state_refs[g].add(rel_path)

        for state_var, files_set in global_state_refs.items():
            if len(files_set) < 2:
                continue
            file_list = list(files_set)
            for i in range(len(file_list)):
                for j in range(i + 1, len(file_list)):
                    source_node = graph.find_node_by_name(file_list[i])
                    target_node = graph.find_node_by_name(file_list[j])
                    if source_node and target_node:
                        edge = CausalEdge(
                            source_id=source_node.id,
                            target_id=target_node.id,
                            relation_type=CausalRelationType.SHARED_STATE,
                            weight=0.5,
                            confidence=0.4,
                            evidence_sources=[f"shared global state: {state_var}"],
                        )
                        edges.append(edge)

        return edges

    def _extract_global_assignments(self, tree: ast.AST) -> List[str]:
        globals_list = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        globals_list.append(target.id)
        return globals_list

    def _relative(self, filepath: Path, repo_root: Path) -> str:
        return str(filepath.relative_to(repo_root))


class TemporalAnalyzer:
    def analyze(self, repo_path: Path, graph: CausalGraph) -> List[CausalEdge]:
        edges: List[CausalEdge] = []

        file_creation_order: List[str] = []
        file_first_seen: Dict[str, int] = {}
        seen_order: int = 0

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H", "--name-only",
                 "--diff-filter=A", "--reverse"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if re.match(r"^[a-f0-9]{40}$", line):
                        continue
                    if line not in file_first_seen:
                        file_first_seen[line] = seen_order
                        file_creation_order.append(line)
                        seen_order += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        if len(file_creation_order) < 2:
            return edges

        for i in range(min(len(file_creation_order), 50)):
            for j in range(i + 1, min(i + 10, len(file_creation_order))):
                source_node = graph.find_node_by_name(file_creation_order[i])
                target_node = graph.find_node_by_name(file_creation_order[j])
                if source_node and target_node:
                    edge = CausalEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation_type=CausalRelationType.TEMPORAL_ORDERING,
                        weight=max(0, 1.0 - (j - i) * 0.1),
                        confidence=0.3,
                        evidence_sources=[f"temporal proximity: {j-i} commits apart"],
                        temporal_ordering="source_before_target",
                    )
                    edges.append(edge)

        return edges


class CausalInferenceEngine:
    def __init__(self):
        self.co_change = CoChangeAnalyzer()
        self.imports = ImportGraphAnalyzer()
        self.data_flow = DataFlowAnalyzer()
        self.api_contracts = ApiContractAnalyzer()
        self.test_coupling = TestCouplingAnalyzer()
        self.shared_state = SharedStateAnalyzer()
        self.temporal = TemporalAnalyzer()

        self.active_analyzers = [
            ("co_change", self.co_change),
            ("imports", self.imports),
            ("data_flow", self.data_flow),
            ("api_contracts", self.api_contracts),
            ("test_coupling", self.test_coupling),
            ("shared_state", self.shared_state),
            ("temporal", self.temporal),
        ]

    def infer(self, repo_path: Path) -> CausalGraph:
        repo_path = Path(repo_path).resolve()
        graph = CausalGraph(name=repo_path.name, repo_path=str(repo_path))

        self._build_initial_nodes(repo_path, graph)
        all_edges: List[CausalEdge] = []

        for analyzer_name, analyzer in self.active_analyzers:
            try:
                edges = analyzer.analyze(repo_path, graph)
                all_edges.extend(edges)
            except Exception as e:
                pass

        deduplicated = self._deduplicate_edges(all_edges)
        for edge in deduplicated:
            graph.add_edge(edge)

        self._compute_risk_scores(graph)

        return graph

    def _build_initial_nodes(self, repo_path: Path, graph: CausalGraph):
        for f in repo_path.rglob("*"):
            if not f.is_file():
                continue
            if any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in f.parts):
                continue

            rel_path = str(f.relative_to(repo_path))
            file_type = NodeType.FILE
            if f.suffix in (".py", ".js", ".ts", ".tsx", ".jsx"):
                file_type = NodeType.FILE
            elif f.suffix in (".json", ".yaml", ".yml", ".toml", ".cfg", ".ini"):
                file_type = NodeType.CONFIG

            parts = Path(rel_path).parts
            subsystem = parts[0] if len(parts) >= 2 else "/"

            try:
                lines = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
            except Exception:
                lines = 0

            node = CausalNode(
                name=rel_path,
                node_type=file_type,
                file_path=rel_path,
                subsystem=subsystem,
                complexity=lines / 100.0,
                metadata={"extension": f.suffix, "size_bytes": f.stat().st_size, "lines": lines},
            )
            graph.add_node(node)

    def _deduplicate_edges(self, edges: List[CausalEdge]) -> List[CausalEdge]:
        edge_map: Dict[Tuple[str, str, str], CausalEdge] = {}

        for edge in edges:
            key = (edge.source_id, edge.target_id, edge.relation_type.value)
            if key in edge_map:
                existing = edge_map[key]
                existing.weight = max(existing.weight, edge.weight)
                existing.confidence = max(existing.confidence, edge.confidence)
                existing.frequency += edge.frequency
                existing.evidence_sources = list(set(existing.evidence_sources + edge.evidence_sources))
            else:
                edge_map[key] = edge

        return list(edge_map.values())

    def _compute_risk_scores(self, graph: CausalGraph):
        for node in graph._nodes.values():
            incoming = graph.get_incoming_edges(node.id)
            outgoing = graph.get_outgoing_edges(node.id)

            import_risk = sum(
                e.weight for e in outgoing
                if e.relation_type == CausalRelationType.IMPORT
            ) * 0.1

            co_change_risk = sum(
                e.weight for e in outgoing
                if e.relation_type == CausalRelationType.CO_CHANGE
            ) * 0.3

            coupling_risk = len(incoming) * 0.05 + len(outgoing) * 0.05

            complexity_risk = node.complexity * 0.2

            node.risk_score = min(1.0, import_risk + co_change_risk + coupling_risk + complexity_risk)
            node.import_count = len(outgoing)
            node.dependents_count = len(incoming)
