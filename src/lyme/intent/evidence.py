from __future__ import annotations

import ast
import re
import subprocess
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .intent_model import IntentEvidence, IntentModel, SubsystemIntent


class EvidenceType(str, Enum):
    STRUCTURAL = "structural"
    HISTORICAL = "historical"
    DOCUMENTATION = "documentation"
    CODE_PATTERN = "code_pattern"
    NAMING_CONVENTION = "naming_convention"
    DEPENDENCY = "dependency"
    TEST = "test"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    SOCIAL = "social"


class EvidenceSource(str, Enum):
    DIRECTORY_STRUCTURE = "directory_structure"
    FILE_CONTENT = "file_content"
    AST_ANALYSIS = "ast_analysis"
    GIT_HISTORY = "git_history"
    DOCSTRINGS = "docstrings"
    COMMENTS = "comments"
    README = "readme"
    CONFIG_FILES = "config_files"
    TEST_FILES = "test_files"
    IMPORTS = "imports"
    NAMING = "naming"


class EvidenceGatherer:
    def gather(self, repo_path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence: List[IntentEvidence] = []
        subsystem_path = repo_path / subsystem

        if not subsystem_path.exists():
            return evidence

        evidence.extend(self._gather_structural(subsystem_path, subsystem))
        evidence.extend(self._gather_naming(subsystem_path, subsystem))
        evidence.extend(self._gather_documentation(subsystem_path, subsystem))
        evidence.extend(self._gather_dependencies(subsystem_path, subsystem))
        evidence.extend(self._gather_history(repo_path, subsystem))

        return evidence

    def _gather_structural(self, path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence = []
        py_files = list(path.rglob("*.py")) if path.is_dir() else []
        if not py_files and path.is_file() and path.suffix == ".py":
            py_files = [path]

        if py_files:
            evidence.append(IntentEvidence(
                source="directory_structure",
                evidence_type="structural",
                content=f"Subsystem '{subsystem}' contains {len(py_files)} Python files",
                confidence=0.7,
            ))

            total_lines = 0
            classes = 0
            functions = 0
            for f in py_files[:20]:
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    total_lines += len(text.splitlines())
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            classes += 1
                        elif isinstance(node, ast.FunctionDef):
                            functions += 1
                except Exception:
                    pass

            evidence.append(IntentEvidence(
                source="ast_analysis",
                evidence_type="code_pattern",
                content=f"Subsystem '{subsystem}': {total_lines} lines, {classes} classes, {functions} functions",
                confidence=0.6,
            ))

        return evidence

    def _gather_naming(self, path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence = []
        name_lower = subsystem.lower()

        name_map = {
            "controller": "handles HTTP requests and routes",
            "service": "implements business logic",
            "model": "defines data structures",
            "repository": "abstracts data access",
            "dao": "provides database access",
            "middleware": "processes requests through pipeline",
            "config": "manages configuration",
            "util": "provides shared utilities",
            "helper": "supports other modules",
            "api": "defines external interfaces",
            "route": "defines route handlers",
            "view": "renders presentation",
            "template": "stores presentation templates",
            "migration": "manages schema changes",
            "test": "contains automated tests",
            "schema": "defines validation schemas",
            "adapter": "integrates external systems",
            "handler": "handles events",
            "provider": "provides services via DI",
            "factory": "creates objects via factory pattern",
        }

        for keyword, purpose in name_map.items():
            if keyword in name_lower:
                evidence.append(IntentEvidence(
                    source="naming",
                    evidence_type="naming_convention",
                    content=f"Subsystem named '{subsystem}' suggests it {purpose}",
                    confidence=0.5,
                ))
                break

        return evidence

    def _gather_documentation(self, path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence = []

        docs = []
        if path.is_dir():
            for pattern in ("README*", "*.md", "*.rst", "docs/**/*"):
                for f in path.glob(pattern):
                    if f.is_file():
                        docs.append(f)

        for doc in docs[:3]:
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")[:500]
                evidence.append(IntentEvidence(
                    source="readme",
                    evidence_type="documentation",
                    content=f"Documentation in {doc.name}: {text[:200]}",
                    confidence=0.4,
                ))
            except Exception:
                pass

        return evidence

    def _gather_dependencies(self, path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence = []
        import_targets: Dict[str, int] = defaultdict(int)

        py_files = list(path.rglob("*.py")) if path.is_dir() else []
        if path.is_file() and path.suffix == ".py":
            py_files = [path]

        for f in py_files[:20]:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            import_targets[node.module] += 1
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            import_targets[alias.name] += 1
            except Exception:
                pass

        if import_targets:
            top_imports = sorted(import_targets.items(), key=lambda x: -x[1])[:5]
            deps_str = ", ".join(f"{m}({c})" for m, c in top_imports)
            evidence.append(IntentEvidence(
                source="imports",
                evidence_type="dependency",
                content=f"Top dependencies: {deps_str}",
                confidence=0.5,
            ))

        return evidence

    def _gather_history(self, repo_path: Path, subsystem: str) -> List[IntentEvidence]:
        evidence = []

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%an|%s", "--", subsystem, "-20"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                if lines:
                    authors = set()
                    purposes = set()
                    for line in lines:
                        if "|" in line:
                            author, msg = line.split("|", 1)
                            authors.add(author)
                            if any(kw in msg.lower() for kw in ("fix", "bug", "error")):
                                purposes.add("bug_fix")
                            elif any(kw in msg.lower() for kw in ("feat", "feature", "add")):
                                purposes.add("feature_development")
                            elif any(kw in msg.lower() for kw in ("refactor", "clean")):
                                purposes.add("refactoring")

                    evidence.append(IntentEvidence(
                        source="git_history",
                        evidence_type="historical",
                        content=f"Subsystem modified by {len(authors)} developers: {', '.join(list(authors)[:3])}. Activities: {', '.join(purposes)}",
                        confidence=0.5,
                    ))
        except Exception:
            pass

        return evidence
