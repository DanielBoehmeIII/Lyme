from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class InvariantLayer:
    def __init__(self, large_file_threshold: int = 500):
        self.large_file_threshold = large_file_threshold

    def extract(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        repo_path = Path(repo_path).resolve()
        if not repo_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {repo_path}")

        change_patterns = self._analyze_git_history(repo_path)
        shared_constants = self._find_shared_constants(repo_path)
        duplicated_patterns = self._find_duplicated_patterns(repo_path)
        circular = self._find_circular_imports(repo_path)
        large_files = self._find_large_files(repo_path)
        high_import_files = self._find_high_import_files(repo_path)
        risk_zones = self._assess_risk(
            change_patterns=change_patterns,
            shared_constants=shared_constants,
            duplicated_patterns=duplicated_patterns,
            circular=circular,
            large_files=large_files,
            high_import_files=high_import_files,
        )

        return {
            "change_patterns": change_patterns,
            "shared_constants": shared_constants,
            "duplicated_patterns": duplicated_patterns,
            "circular_imports": circular,
            "large_files": large_files,
            "high_import_files": high_import_files,
            "risk_zones": risk_zones,
        }

    def _analyze_git_history(self, repo_path: Path) -> Dict[str, Any]:
        change_cooccurrence: Dict[str, Counter] = defaultdict(Counter)
        file_change_count: Counter = Counter()
        author_file_count: Dict[str, Counter] = defaultdict(Counter)

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%an", "--name-only", "--diff-filter=AM"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return {"available": False, "reason": "git log failed"}

            current_author: Optional[str] = None
            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if current_author is None and self._is_author_line(line):
                    current_author = line
                    current_files = []
                elif self._is_author_line(line):
                    self._process_commit_files(
                        current_files, current_author,
                        change_cooccurrence, file_change_count,
                        author_file_count,
                    )
                    current_author = line
                    current_files = []
                elif not line.startswith("commit "):
                    current_files.append(line)

            if current_author:
                self._process_commit_files(
                    current_files, current_author,
                    change_cooccurrence, file_change_count,
                    author_file_count,
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"available": False, "reason": "git not available or too slow"}

        top_cooccurrence = self._top_cooccurrence(change_cooccurrence, 5)
        return {
            "available": True,
            "commits_analyzed": sum(1 for _ in change_cooccurrence),
            "file_change_frequencies": dict(file_change_count.most_common(20)),
            "top_cooccurring_changes": top_cooccurrence,
            "authors_per_file": {
                f: dict(author_file_count[f].most_common(5))
                for f in sorted(file_change_count.keys())[:20]
            },
        }

    def _is_author_line(self, line: str) -> bool:
        return bool(re.match(r"^[A-Za-z][\w\s.-]+$", line)) and len(line) < 100

    def _process_commit_files(
        self,
        files: List[str],
        author: Optional[str],
        cooccurrence: Dict[str, Counter],
        file_change_count: Counter,
        author_file_count: Dict[str, Counter],
    ) -> None:
        for i, f1 in enumerate(files):
            file_change_count[f1] += 1
            if author:
                author_file_count[f1][author] += 1
            for f2 in files[i + 1:]:
                cooccurrence[f1][f2] += 1
                cooccurrence[f2][f1] += 1

    def _top_cooccurrence(
        self, cooccurrence: Dict[str, Counter], top_n: int
    ) -> List[Dict[str, Any]]:
        scored = []
        for f1, counter in cooccurrence.items():
            for f2, count in counter.most_common(top_n):
                if f1 < f2:
                    scored.append((count, f1, f2))
        scored.sort(reverse=True)
        return [
            {"file_a": f1, "file_b": f2, "cooccurrences": c}
            for c, f1, f2 in scored[:top_n * 5]
        ]

    def _find_shared_constants(self, repo_path: Path) -> List[Dict[str, Any]]:
        constant_patterns: Dict[str, List[str]] = defaultdict(list)
        pattern = re.compile(r"^([A-Z][A-Z0-9_]+)\s*=\s*(.+)$", re.MULTILINE)

        for f in repo_path.rglob("*.py"):
            if f.is_file() and not any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for m in pattern.finditer(text):
                        key = m.group(1)
                        value = m.group(2).strip()
                        sig = f"{key} = {value}"
                        constant_patterns[sig].append(str(f.relative_to(repo_path)))
                except Exception:
                    pass

        return [
            {"constant": key, "files": files}
            for key, files in constant_patterns.items()
            if len(files) >= 3
        ][:30]

    def _find_duplicated_patterns(self, repo_path: Path) -> List[Dict[str, Any]]:
        class_bodies: Dict[str, List[str]] = defaultdict(list)
        function_bodies: Dict[str, List[str]] = defaultdict(list)

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(
                p.startswith(".") or p == "__pycache__" for p in f.parts
            ):
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue

            rel = str(f.relative_to(repo_path))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    body_sig = self._body_signature(node.body)
                    class_bodies[body_sig].append(rel)
                elif isinstance(node, ast.FunctionDef):
                    body_sig = self._body_signature(node.body)
                    function_bodies[body_sig].append(rel)

        return [
            {"type": "class", "signature_hash": sig, "files": files}
            for sig, files in class_bodies.items()
            if len(files) >= 3
        ][:20] + [
            {"type": "function", "signature_hash": sig, "files": files}
            for sig, files in function_bodies.items()
            if len(files) >= 3
        ][:20]

    def _body_signature(self, body: List[ast.stmt]) -> str:
        sig_parts = []
        for node in body[:5]:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig_parts.append(f"def {node.name}({len(node.args.args)} args)")
            elif isinstance(node, ast.Assign):
                sig_parts.append("assign")
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                sig_parts.append("call")
            elif isinstance(node, ast.Return):
                sig_parts.append("return")
            else:
                sig_parts.append(type(node).__name__)
        return "|".join(sig_parts)

    def _find_circular_imports(self, repo_path: Path) -> List[Dict[str, Any]]:
        import_graph: Dict[str, Set[str]] = defaultdict(set)
        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(
                p.startswith(".") or p == "__pycache__" for p in f.parts
            ):
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue
            rel = str(f.relative_to(repo_path)).replace("/", ".").replace(".py", "")
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        import_graph[rel].add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        import_graph[rel].add(alias.name)

        cycles = []
        for start in list(import_graph.keys()):
            visited: Set[str] = set()
            path: List[str] = []
            stack: Set[str] = set()

            def dfs(node: str) -> None:
                if node in stack:
                    idx = path.index(node)
                    cycle = path[idx:] + [node]
                    cycles.append(
                        {"cycle": cycle, "length": len(cycle) - 1}
                    )
                    return
                if node in visited:
                    return
                visited.add(node)
                stack.add(node)
                path.append(node)
                for neighbor in list(import_graph.get(node, set()))[:50]:
                    dfs(neighbor)
                path.pop()
                stack.discard(node)

            dfs(start)

        unique = []
        seen_keys: Set[str] = set()
        for c in cycles:
            k = " -> ".join(sorted(set(c["cycle"])))
            if k not in seen_keys:
                seen_keys.add(k)
                unique.append(c)
        return unique[:20]

    def _find_large_files(self, repo_path: Path) -> List[Dict[str, Any]]:
        files = []
        for f in repo_path.rglob("*"):
            if f.is_file() and not any(
                p.startswith(".") or p == "__pycache__" or p == "node_modules"
                for p in f.parts
            ):
                try:
                    lines = len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
                    if lines >= self.large_file_threshold:
                        files.append({
                            "file": str(f.relative_to(repo_path)),
                            "lines": lines,
                            "size_bytes": f.stat().st_size,
                        })
                except Exception:
                    pass
        return sorted(files, key=lambda x: -x["lines"])[:20]

    def _find_high_import_files(self, repo_path: Path) -> List[Dict[str, Any]]:
        files = []
        for f in repo_path.rglob("*.py"):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                imports = len(re.findall(r"^\s*(?:from\s+[\w.]+\s+)?import\s+", text, re.MULTILINE))
                if imports >= 10:
                    files.append({
                        "file": str(f.relative_to(repo_path)),
                        "import_count": imports,
                    })
            except Exception:
                pass
        return sorted(files, key=lambda x: -x["import_count"])[:20]

    def _assess_risk(
        self,
        change_patterns: Dict[str, Any],
        shared_constants: List[Dict[str, Any]],
        duplicated_patterns: List[Dict[str, Any]],
        circular: List[Dict[str, Any]],
        large_files: List[Dict[str, Any]],
        high_import_files: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        zones: List[Dict[str, Any]] = []

        for lf in large_files:
            zones.append({
                "file": lf["file"],
                "risk": "high",
                "reason": f"Large file ({lf['lines']} lines) - maintenance burden",
                "type": "large_file",
            })

        for hif in high_import_files:
            zones.append({
                "file": hif["file"],
                "risk": "medium",
                "reason": f"High import count ({hif['import_count']} imports) - potential coupling",
                "type": "high_imports",
            })

        for sc in shared_constants:
            zones.append({
                "file": ", ".join(sc["files"][:5]),
                "risk": "medium",
                "reason": f"Shared constant '{sc['constant']}' in {len(sc['files'])} files - hidden coupling",
                "type": "shared_constant",
            })

        for dp in duplicated_patterns:
            zones.append({
                "file": ", ".join(dp["files"][:3]),
                "risk": "medium",
                "reason": f"Duplicated {dp['type']} pattern in {len(dp['files'])} locations",
                "type": "duplicate",
            })

        for c in circular:
            zones.append({
                "file": " -> ".join(c["cycle"]),
                "risk": "high",
                "reason": f"Circular dependency ({c['length']} files)",
                "type": "circular_dependency",
            })

        if change_patterns.get("available"):
            for cc in change_patterns.get("top_cooccurring_changes", [])[:10]:
                zones.append({
                    "file": f"{cc['file_a']} + {cc['file_b']}",
                    "risk": "medium",
                    "reason": f"Frequent co-change ({cc['cooccurrences']} times) - coupling",
                    "type": "change_coupling",
                })

        return sorted(zones, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["risk"]])[:50]
