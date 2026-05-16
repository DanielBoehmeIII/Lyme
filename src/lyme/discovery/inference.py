from __future__ import annotations

import ast
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .invariant import (
    Invariant, InvariantSet, InvariantType, InvariantSeverity,
)


class ExplicitInvariantMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = str(f.relative_to(repo_path))

            invariants.extend(self._find_assertions(tree, rel_path))
            invariants.extend(self._find_type_annotations(tree, rel_path))
            invariants.extend(self._find_decorator_contracts(tree, rel_path))
            invariants.extend(self._find_docstring_rules(text, rel_path))
            invariants.extend(self._find_config_validators(tree, rel_path))

        return invariants

    def _find_assertions(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                test_str = ast.unparse(node.test) if hasattr(ast, 'unparse') else ""
                if test_str:
                    inv = Invariant(
                        name=f"assertion: {test_str[:60]}",
                        invariant_type=InvariantType.API_CONTRACT,
                        description=f"Explicit assertion in {file_path}: {test_str}",
                        rule=test_str,
                        severity=InvariantSeverity.HIGH,
                        scope=file_path,
                        confidence=0.9,
                        evidence=[f"assert statement in {file_path}"],
                        source="explicit",
                    )
                    invariants.append(inv)
        return invariants[:10]

    def _find_type_annotations(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                returns = node.returns
                if returns:
                    ret_str = ast.unparse(returns) if hasattr(ast, 'unparse') else ""
                    if ret_str:
                        invariants.append(Invariant(
                            name=f"return type: {node.name} -> {ret_str}",
                            invariant_type=InvariantType.API_CONTRACT,
                            description=f"Function {node.name} must return {ret_str}",
                            rule=f"{node.name}() -> {ret_str}",
                            severity=InvariantSeverity.MEDIUM,
                            scope=file_path,
                            confidence=0.7,
                            evidence=[f"type annotation in {file_path}:{node.lineno}"],
                            source="explicit",
                        ))
        return invariants[:10]

    def _find_decorator_contracts(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr

                    contract_map = {
                        "login_required": InvariantType.AUTH_REQUIRED,
                        "permission_required": InvariantType.AUTH_REQUIRED,
                        "authenticated": InvariantType.AUTH_REQUIRED,
                        "transaction": InvariantType.TRANSACTION_BOUNDARY,
                        "transactional": InvariantType.TRANSACTION_BOUNDARY,
                        "atomic": InvariantType.TRANSACTION_BOUNDARY,
                        "cache": InvariantType.PERFORMANCE_BUDGET,
                        "ratelimit": InvariantType.PERFORMANCE_BUDGET,
                        "validate": InvariantType.API_CONTRACT,
                        "ensure": InvariantType.API_CONTRACT,
                        "requires": InvariantType.API_CONTRACT,
                    }
                    if dec_name in contract_map:
                        invariants.append(Invariant(
                            name=f"decorator: @{dec_name} on {node.name}",
                            invariant_type=contract_map[dec_name],
                            description=f"@{dec_name} decorator imposes contract on {node.name}",
                            rule=f"{dec_name} decorator required for {node.name}",
                            severity=InvariantSeverity.HIGH,
                            scope=file_path,
                            confidence=0.85,
                            evidence=[f"@{dec_name} on {node.name} in {file_path}:{node.lineno}"],
                            source="explicit",
                        ))
        return invariants

    def _find_docstring_rules(self, text: str, file_path: str) -> List[Invariant]:
        invariants = []
        patterns = [
            (r"(?i)must\s+be\s+(\w+)", "requirement: {}"),
            (r"(?i)should\s+not\s+(\w+)", "prohibition: {}"),
            (r"(?i)requires?\s+(\w+)", "dependency: {}"),
            (r"(?i)guarantees?\s+(\w+)", "guarantee: {}"),
            (r"(?i)invariant:\s*(.+)", "invariant: {}"),
            (r"(?i)contract:\s*(.+)", "contract: {}"),
            (r"(?i)precondition:\s*(.+)", "precondition: {}"),
            (r"(?i)postcondition:\s*(.+)", "postcondition: {}"),
        ]
        for pattern, template in patterns:
            for m in re.finditer(pattern, text):
                constraint = m.group(1).strip()
                if constraint and len(constraint) > 3:
                    invariants.append(Invariant(
                        name=f"docstring: {template.format(constraint[:50])}",
                        invariant_type=InvariantType.API_CONTRACT,
                        description=f"Documented constraint in {file_path}: {m.group(0)}",
                        rule=m.group(0),
                        severity=InvariantSeverity.MEDIUM,
                        scope=file_path,
                        confidence=0.5,
                        evidence=[f"docstring in {file_path}"],
                        source="explicit",
                    ))
        return invariants[:5]

    def _find_config_validators(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name in (
                        "validate", "clean", "check", "_validate", "sanitize"
                    ):
                        invariants.append(Invariant(
                            name=f"validation: {node.name}.{item.name}",
                            invariant_type=InvariantType.CONFIG_SCHEMA,
                            description=f"{node.name} has validation method {item.name}",
                            rule=f"{node.name} data must pass {item.name} validation",
                            severity=InvariantSeverity.HIGH,
                            scope=file_path,
                            confidence=0.75,
                            evidence=[f"validator method in {file_path}:{item.lineno}"],
                            source="explicit",
                        ))
        return invariants[:5]


class ImplicitInvariantMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = str(f.relative_to(repo_path))

            invariants.extend(self._find_layer_patterns(tree, rel_path))
            invariants.extend(self._find_stateless_patterns(tree, rel_path))
            invariants.extend(self._find_cleanup_patterns(tree, rel_path))
            invariants.extend(self._find_error_patterns(tree, rel_path))
            invariants.extend(self._find_idempotency_patterns(tree, rel_path))
            invariants.extend(self._find_db_layer_patterns(tree, rel_path, repo_path))

        return invariants

    def _find_layer_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        path_parts = Path(file_path).parts
        layer_keywords = {
            "controller": "controllers",
            "view": "views",
            "route": "routes",
            "service": "services",
            "repository": "repositories",
            "model": "models",
            "dao": "dao",
            "middleware": "middleware",
            "handler": "handlers",
        }

        current_layer = None
        for part in path_parts:
            part_lower = part.lower()
            for keyword, layer in layer_keywords.items():
                if keyword in part_lower:
                    current_layer = layer
                    break

        if current_layer:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for keyword, target_layer in layer_keywords.items():
                        if keyword in node.module:
                            invariants.append(Invariant(
                                name=f"layer boundary: {current_layer} imports {target_layer}",
                                invariant_type=InvariantType.LAYER_VIOLATION,
                                description=f"Layer '{current_layer}' in {file_path} imports from '{target_layer}'",
                                rule=f"{current_layer} should not import {target_layer}",
                                severity=InvariantSeverity.MEDIUM,
                                scope=file_path,
                                confidence=0.4,
                                evidence=[f"import {node.module} in {file_path}"],
                                source="implicit",
                            ))
        return invariants[:10]

    def _find_stateless_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []

        global_mutations = 0
        class_mutations = 0
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        global_mutations += 1
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for sub in ast.walk(item):
                            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                                if sub.value.id == "self" and sub.attr != "__init__":
                                    class_mutations += 1

        if "service" in Path(file_path).stem.lower() and class_mutations == 0 and global_mutations == 0:
            invariants.append(Invariant(
                name=f"stateless service: {Path(file_path).stem}",
                invariant_type=InvariantType.STATELESS_REQUIREMENT,
                description=f"Service {file_path} appears stateless",
                rule=f"{Path(file_path).stem} must remain stateless",
                severity=InvariantSeverity.LOW,
                scope=file_path,
                confidence=0.5,
                evidence=[f"no state mutations detected in {file_path}"],
                source="implicit",
            ))

        return invariants

    def _find_cleanup_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []

        resource_openers = set()
        cleanup_methods = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("open", "connect", "acquire", "lock"):
                        resource_openers.add(node.func.attr)
                    elif node.func.attr in ("close", "disconnect", "release", "unlock", "cleanup", "__exit__"):
                        cleanup_methods.add(node.func.attr)

        for opener in resource_openers:
            if opener == "open" and "close" not in cleanup_methods:
                if "with" not in ast.dump(tree):
                    invariants.append(Invariant(
                        name=f"missing cleanup: {opener}",
                        invariant_type=InvariantType.RESOURCE_CLEANUP,
                        description=f"Resource '{opener}' used but no corresponding cleanup in {file_path}",
                        rule=f"resources opened with {opener} must be cleaned up",
                        severity=InvariantSeverity.HIGH,
                        scope=file_path,
                        confidence=0.4,
                        evidence=[f"{opener} without close/cleanup in {file_path}"],
                        source="implicit",
                    ))

        return invariants[:5]

    def _find_error_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        has_try = False
        has_except = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_try = True
                for handler in node.handlers:
                    if handler.type is None or (
                        isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
                    ):
                        has_except = True

        if has_try and not has_except:
            invariants.append(Invariant(
                name="error handling: bare except",
                invariant_type=InvariantType.ERROR_HANDLING,
                description=f"Broad exception handling in {file_path}",
                rule="exceptions should be specific, not bare",
                severity=InvariantSeverity.MEDIUM,
                scope=file_path,
                confidence=0.6,
                evidence=[f"bare except in {file_path}"],
                source="implicit",
            ))
        return invariants

    def _find_idempotency_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        idempotent_keywords = {"upsert", "put", "set", "ensure", "sync", "reconcile"}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if any(kw in node.name.lower() for kw in idempotent_keywords):
                    invariants.append(Invariant(
                        name=f"idempotency: {node.name}",
                        invariant_type=InvariantType.IDEMPOTENCY_EXPECTED,
                        description=f"Function '{node.name}' in {file_path} suggests idempotent operation",
                        rule=f"{node.name} should be idempotent",
                        severity=InvariantSeverity.MEDIUM,
                        scope=file_path,
                        confidence=0.5,
                        evidence=[f"idempotent keyword in function name: {node.name} at {file_path}:{node.lineno}"],
                        source="implicit",
                    ))
        return invariants[:5]

    def _find_db_layer_patterns(self, tree: ast.AST, file_path: str, repo_path: Path) -> List[Invariant]:
        invariants = []
        db_keywords = {"execute", "query", "session", "cursor", "commit", "rollback", "save", "update", "delete", "insert"}
        has_db_ops = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if any(kw in node.func.attr.lower() for kw in db_keywords):
                    has_db_ops = True
                    break
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if any(kw in node.attr.lower() for kw in db_keywords):
                    has_db_ops = True
                    break

        if has_db_ops:
            stack_parts = Path(file_path).parts
            in_dao = any("dao" in p.lower() or "repository" in p.lower() for p in stack_parts)
            if in_dao:
                invariants.append(Invariant(
                    name="database operations through DAO layer",
                    invariant_type=InvariantType.DATA_FLOW_CONSTRAINT,
                    description=f"DB operations in DAO layer: {file_path}",
                    rule="all database writes go through this layer",
                    severity=InvariantSeverity.HIGH,
                    scope=file_path,
                    confidence=0.7,
                    evidence=[f"database operations in DAO: {file_path}"],
                    source="implicit",
                ))

        return invariants[:5]


class HistoricalInvariantMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []
        co_change_patterns: Dict[str, Counter] = defaultdict(Counter)
        file_sequence: Dict[str, List[int]] = defaultdict(list)
        commit_count = 0

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H", "--name-only",
                 "--diff-filter=AM", "-200"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return invariants

            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^[a-f0-9]{40}$", line):
                    if current_files:
                        commit_count += 1
                        for f in current_files:
                            file_sequence[f].append(commit_count)
                        for i, f1 in enumerate(current_files):
                            for f2 in current_files[i + 1:]:
                                key = (f1, f2) if f1 < f2 else (f2, f1)
                                co_change_patterns[key[0]][key[1]] += 1
                    current_files = []
                else:
                    current_files.append(line)
            if current_files:
                commit_count += 1
                for f in current_files:
                    file_sequence[f].append(commit_count)
                for i, f1 in enumerate(current_files):
                    for f2 in current_files[i + 1:]:
                        key = (f1, f2) if f1 < f2 else (f2, f1)
                        co_change_patterns[key[0]][key[1]] += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return invariants

        for f1, counter in co_change_patterns.items():
            for f2, count in counter.most_common(5):
                if count >= 5:
                    invariants.append(Invariant(
                        name=f"co-evolution: {Path(f1).name} + {Path(f2).name}",
                        invariant_type=InvariantType.CO_EVOLUTION,
                        description=f"Files {f1} and {f2} changed together {count} times",
                        rule=f"{f1} and {f2} should evolve together",
                        severity=InvariantSeverity.MEDIUM,
                        scope=f"{f1}, {f2}",
                        confidence=min(0.9, 0.3 + count * 0.05),
                        evidence=[f"co-changed {count} times in {commit_count} commits"],
                        source="historical",
                        observation_count=count,
                    ))

        return invariants[:30]


class SocialInvariantMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []
        author_files: Dict[str, Counter] = defaultdict(Counter)

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%an", "--name-only",
                 "--diff-filter=AM", "-200"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return invariants

            current_author = ""
            current_files: List[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line and not re.match(r"^[a-f0-9]{40}$", line) and len(line) < 100:
                    if not current_files or current_author:
                        pass
                    if current_files and current_author:
                        for f in current_files:
                            author_files[current_author][f] += 1
                    if re.match(r"^[A-Za-z]", line) and len(line) < 100 and "/" not in line:
                        current_author = line
                        current_files = []
                    else:
                        current_files.append(line)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return invariants

        owned_files: Dict[str, List[Tuple[str, int]]] = {}
        for author, counter in author_files.items():
            total = sum(counter.values())
            for f, count in counter.most_common(10):
                ratio = count / total
                if ratio > 0.5 and count >= 3:
                    owned_files.setdefault(f, []).append((author, ratio))

        for f, owners in owned_files.items():
            owners_str = ", ".join(f"{o[0]} ({o[1]:.0%})" for o in owners[:3])
            invariants.append(Invariant(
                name=f"social ownership: {Path(f).name}",
                invariant_type=InvariantType.DEPENDENCY_RULE,
                description=f"File {f} primarily owned by: {owners_str}",
                rule=f"Changes to {f} should involve primary owners",
                severity=InvariantSeverity.LOW,
                scope=f,
                confidence=0.5,
                evidence=[f"ownership by {owners_str}"],
                source="social",
            ))

        return invariants[:20]


class FragileAssumptionMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = str(f.relative_to(repo_path))

            invariants.extend(self._find_hardcoded_assumptions(tree, rel_path))
            invariants.extend(self._find_brittle_patterns(tree, rel_path))

        invariants.extend(self._find_version_coupling(repo_path))

        return invariants

    def _find_hardcoded_assumptions(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(kw in node.value.lower() for kw in ("localhost", "127.0.0.1", "password", "secret", "api_key")):
                    pass
                if len(node.value) > 100:
                    continue
                if re.match(r"https?://", node.value):
                    invariants.append(Invariant(
                        name=f"hardcoded URL: {node.value[:40]}",
                        invariant_type=InvariantType.CONFIG_SCHEMA,
                        description=f"Hardcoded URL in {file_path}: {node.value[:60]}",
                        rule="external URLs should be configurable",
                        severity=InvariantSeverity.MEDIUM,
                        scope=file_path,
                        confidence=0.6,
                        evidence=[f"hardcoded URL at {file_path}"],
                        source="fragile",
                    ))
        return invariants[:5]

    def _find_brittle_patterns(self, tree: ast.AST, file_path: str) -> List[Invariant]:
        invariants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "sleep" and isinstance(node.args[0], ast.Constant):
                    seconds = node.args[0].value
                    if isinstance(seconds, (int, float)) and seconds > 5:
                        invariants.append(Invariant(
                            name=f"long sleep: {seconds}s",
                            invariant_type=InvariantType.PERFORMANCE_BUDGET,
                            description=f"Long sleep({seconds}s) in {file_path}",
                            rule="avoid long blocking sleeps",
                            severity=InvariantSeverity.MEDIUM,
                            scope=file_path,
                            confidence=0.5,
                            evidence=[f"sleep({seconds}) at {file_path}"],
                            source="fragile",
                        ))
        return invariants[:5]

    def _find_version_coupling(self, repo_path: Path) -> List[Invariant]:
        invariants = []
        version_files = {}

        for f in repo_path.rglob("*"):
            if f.name in ("package.json", "setup.py", "pyproject.toml", "Cargo.toml", "Gemfile", "requirements.txt"):
                rel = str(f.relative_to(repo_path))
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    version_files[rel] = text
                except Exception:
                    pass

        if len(version_files) >= 2:
            names = list(version_files.keys())
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    invariants.append(Invariant(
                        name=f"version coupling: {names[i]} + {names[j]}",
                        invariant_type=InvariantType.VERSION_COUPLING,
                        description=f"Dependency files {names[i]} and {names[j]} should stay in sync",
                        rule=f"{names[i]} and {names[j]} versions must be compatible",
                        severity=InvariantSeverity.HIGH,
                        scope=f"{names[i]}, {names[j]}",
                        confidence=0.7,
                        evidence=["multiple dependency files found"],
                        source="fragile",
                    ))

        return invariants[:10]


class HiddenContractMiner:
    def mine(self, repo_path: Path, inv_set: InvariantSet) -> List[Invariant]:
        invariants: List[Invariant] = []
        interface_implementations: Dict[str, List[str]] = defaultdict(list)

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            rel_path = str(f.relative_to(repo_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            interface_implementations[base.id].append(rel_path)
                        elif isinstance(base, ast.Attribute):
                            interface_implementations[base.attr].append(rel_path)

        for interface, implementors in interface_implementations.items():
            if len(implementors) >= 2:
                methods: Dict[str, Set[str]] = defaultdict(set)
                for impl_path in implementors:
                    try:
                        f_path = repo_path / impl_path
                        text = f_path.read_text(encoding="utf-8", errors="replace")
                        tree = ast.parse(text)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                methods[node.name].add(impl_path)
                    except Exception:
                        pass

                for method_name, impl_files in methods.items():
                    if len(impl_files) >= 2:
                        invariants.append(Invariant(
                            name=f"interface contract: {interface}.{method_name}",
                            invariant_type=InvariantType.API_CONTRACT,
                            description=f"Method '{method_name}' implements '{interface}' in {len(impl_files)} files",
                            rule=f"{interface}.{method_name} must maintain consistent contract across implementations",
                            severity=InvariantSeverity.HIGH,
                            scope=", ".join(sorted(impl_files)[:5]),
                            confidence=0.6,
                            evidence=[f"implemented by: {', '.join(sorted(impl_files)[:3])}"],
                            source="hidden",
                        ))

        return invariants[:20]


class InvariantInferenceEngine:
    def __init__(self):
        self.explicit = ExplicitInvariantMiner()
        self.implicit = ImplicitInvariantMiner()
        self.historical = HistoricalInvariantMiner()
        self.social = SocialInvariantMiner()
        self.fragile = FragileAssumptionMiner()
        self.hidden_contracts = HiddenContractMiner()

        self.miners = [
            ("explicit", self.explicit),
            ("implicit", self.implicit),
            ("historical", self.historical),
            ("social", self.social),
            ("fragile", self.fragile),
            ("hidden_contracts", self.hidden_contracts),
        ]

    def discover(self, repo_path: Path) -> InvariantSet:
        repo_path = Path(repo_path).resolve()
        inv_set = InvariantSet(repo_path=str(repo_path))

        for miner_name, miner in self.miners:
            try:
                invariants = miner.mine(repo_path, inv_set)
                for inv in invariants:
                    inv_set.add_invariant(inv)
            except Exception:
                pass

        return inv_set

    def discover_with_confidence(
        self, repo_path: Path, min_confidence: float = 0.3
    ) -> InvariantSet:
        inv_set = self.discover(repo_path)
        filtered = InvariantSet(repo_path=str(repo_path))
        for inv in inv_set._invariants.values():
            if inv.confidence >= min_confidence:
                filtered.add_invariant(inv)
        for viol in inv_set._violations.values():
            filtered.add_violation(viol)
        return filtered
