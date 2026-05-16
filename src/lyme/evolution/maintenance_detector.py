from __future__ import annotations

import ast
import json
import math
import re
import subprocess
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .fitness_refactoring import FitnessAssessor


class OpportunityCategory(str, Enum):
    CLEANUP = "cleanup"
    STALE_DEPENDENCY = "stale_dependency"
    REPEATED_CODE = "repeated_code"
    UNUSED_FILE = "unused_file"
    WEAK_TEST = "weak_test"
    FRAGILE_API = "fragile_api"
    DOCUMENTATION_GAP = "documentation_gap"
    ARCHITECTURAL_EROSION = "architectural_erosion"


@dataclass
class MaintenanceOpportunity:
    opportunity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    category: OpportunityCategory = OpportunityCategory.CLEANUP
    title: str = ""
    description: str = ""
    target_files: List[str] = field(default_factory=list)
    value: float = 0.0
    risk: float = 0.0
    effort: float = 0.0
    confidence: float = 0.0
    verification_cost: float = 0.0
    evidence: str = ""
    created_at: float = field(default_factory=time.time)

    def score(self) -> float:
        return (self.value * 0.4 - self.risk * 0.2 - self.effort * 0.15 + self.confidence * 0.15 - self.verification_cost * 0.1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "target_files": self.target_files,
            "value": round(self.value, 4),
            "risk": round(self.risk, 4),
            "effort": round(self.effort, 4),
            "confidence": round(self.confidence, 4),
            "verification_cost": round(self.verification_cost, 4),
            "score": round(self.score(), 4),
            "evidence": self.evidence,
        }


class MaintenanceDetector:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()

    def detect_all(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        opportunities.extend(self._detect_cleanup_opportunities())
        opportunities.extend(self._detect_stale_dependencies())
        opportunities.extend(self._detect_repeated_code())
        opportunities.extend(self._detect_unused_files())
        opportunities.extend(self._detect_weak_tests())
        opportunities.extend(self._detect_fragile_apis())
        opportunities.extend(self._detect_documentation_gaps())
        opportunities.extend(self._detect_architectural_erosion())
        opportunities.sort(key=lambda o: o.score(), reverse=True)
        return opportunities

    def _detect_cleanup_opportunities(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = str(f.relative_to(self.repo_path))
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                tree = ast.parse(text)
            except (SyntaxError, Exception):
                continue

            pass_count = sum(1 for l in lines if l.strip() == "pass")
            if pass_count > 3:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.CLEANUP,
                    title=f"Excessive 'pass' statements in {rel}",
                    description=f"{pass_count} 'pass' statements suggest incomplete implementations",
                    target_files=[rel],
                    value=0.3,
                    risk=0.05,
                    effort=0.2,
                    confidence=0.8,
                    verification_cost=0.1,
                    evidence=f"{pass_count} pass statements found",
                ))

            todo_count = sum(1 for l in lines if "TODO" in l)
            fixme_count = sum(1 for l in lines if "FIXME" in l or "HACK" in l or "XXX" in l)
            if todo_count + fixme_count > 5:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.CLEANUP,
                    title=f"Accumulated TODOs/FIXMEs in {rel}",
                    description=f"{todo_count} TODOs + {fixme_count} FIXMEs/HACKs",
                    target_files=[rel],
                    value=0.4,
                    risk=0.05,
                    effort=0.3,
                    confidence=0.9,
                    verification_cost=0.1,
                    evidence=f"{todo_count} TODOs, {fixme_count} FIXMEs/HACKs",
                ))

            if len(lines) > 1000:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.CLEANUP,
                    title=f"Very large file: {rel}",
                    description=f"{len(lines)} lines — consider splitting",
                    target_files=[rel],
                    value=0.5,
                    risk=0.15,
                    effort=0.5,
                    confidence=0.7,
                    verification_cost=0.2,
                    evidence=f"{len(lines)} lines in single file",
                ))

            blank_lines = sum(1 for l in lines if not l.strip())
            if blank_lines > len(lines) * 0.3 and len(lines) > 50:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.CLEANUP,
                    title=f"Excessive blank lines in {rel}",
                    description=f"{blank_lines} blank lines ({blank_lines/len(lines):.0%})",
                    target_files=[rel],
                    value=0.15,
                    risk=0.02,
                    effort=0.1,
                    confidence=0.95,
                    verification_cost=0.05,
                    evidence=f"{blank_lines}/{len(lines)} lines are blank",
                ))

        return opportunities

    def _detect_stale_dependencies(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        dep_files = ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"]
        for df in dep_files:
            path = self.repo_path / df
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                comments = [l for l in text.splitlines() if l.strip().startswith("#") and len(l.strip()) > 20]
                for comment in comments:
                    if any(kw in comment for kw in ("deprecated", "old", "legacy", "pinned", "frozen")):
                        opportunities.append(MaintenanceOpportunity(
                            category=OpportunityCategory.STALE_DEPENDENCY,
                            title=f"Potentially stale dependency annotation in {df}",
                            description=comment.strip("# ")[:100],
                            target_files=[df],
                            value=0.4,
                            risk=0.2,
                            effort=0.3,
                            confidence=0.5,
                            verification_cost=0.3,
                            evidence=comment.strip("# ")[:200],
                        ))
            except Exception:
                pass

        if (self.repo_path / "requirements.txt").exists():
            opportunities.append(MaintenanceOpportunity(
                category=OpportunityCategory.STALE_DEPENDENCY,
                title="requirements.txt vs pyproject.toml duplication",
                description="Both requirements.txt and pyproject.toml exist — possible dependency drift",
                target_files=["requirements.txt", "pyproject.toml"],
                value=0.3,
                risk=0.1,
                effort=0.2,
                confidence=0.6,
                verification_cost=0.15,
                evidence="Multiple dependency declaration files",
            ))

        return opportunities

    def _detect_repeated_code(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        file_funcs: Dict[str, List[Tuple[str, str]]] = {}

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                funcs = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        body_text = "".join(
                            ast.get_source_segment(text, s) or ""
                            for s in node.body[:5]
                        )
                        funcs.append((node.name, body_text[:200]))
                if funcs:
                    file_funcs[str(f.relative_to(self.repo_path))] = funcs
            except Exception:
                pass

        files_list = list(file_funcs.items())
        for i, (fpath_a, funcs_a) in enumerate(files_list):
            for fpath_b, funcs_b in files_list[i + 1:]:
                for name_a, body_a in funcs_a:
                    for name_b, body_b in funcs_b:
                        if body_a and body_b and len(body_a) > 50 and len(body_b) > 50:
                            similarity = len(set(body_a.split()) & set(body_b.split())) / max(len(set(body_a.split()) | set(body_b.split())), 1)
                            if similarity > 0.7:
                                opportunities.append(MaintenanceOpportunity(
                                    category=OpportunityCategory.REPEATED_CODE,
                                    title=f"Similar functions: {name_a} in {Path(fpath_a).name} ↔ {name_b} in {Path(fpath_b).name}",
                                    description=f"Look-alike functions with {similarity:.0%} structural similarity",
                                    target_files=[fpath_a, fpath_b],
                                    value=0.6,
                                    risk=0.2,
                                    effort=0.4,
                                    confidence=0.65,
                                    verification_cost=0.3,
                                    evidence=f"Similarity: {similarity:.0%} between {name_a} and {name_b}",
                                ))
                            break
                break

        return opportunities[:10]

    def _detect_unused_files(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        py_files = list(self.repo_path.rglob("*.py"))
        all_imports: Set[str] = set()

        for f in py_files:
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            all_imports.add(node.module.split(".")[0])
            except Exception:
                pass

        for f in py_files:
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = str(f.relative_to(self.repo_path))
            if "test" in rel or "migrations" in rel:
                continue
            if rel.endswith("__init__.py"):
                continue

            mod_name = f.stem
            is_imported = mod_name in all_imports

            try:
                result = subprocess.run(
                    ["git", "-C", str(self.repo_path), "log", "--oneline", "--", rel],
                    capture_output=True, text=True, timeout=10,
                )
                commit_count = len(result.stdout.splitlines())
            except Exception:
                commit_count = 0

            if not is_imported and commit_count == 0:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.UNUSED_FILE,
                    title=f"Potentially unused: {rel}",
                    description="Not imported by any other module and no git history",
                    target_files=[rel],
                    value=0.3,
                    risk=0.1,
                    effort=0.1,
                    confidence=0.5,
                    verification_cost=0.2,
                    evidence=f"Zero imports, {commit_count} commits",
                ))

        return opportunities

    def _detect_weak_tests(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        for f in self.repo_path.rglob("test_*.py"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(self.repo_path))
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except Exception:
                continue

            test_funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
            for func in test_funcs:
                body = func.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    opportunities.append(MaintenanceOpportunity(
                        category=OpportunityCategory.WEAK_TEST,
                        title=f"Empty test: {func.name} in {rel}",
                        description="Test function contains only 'pass'",
                        target_files=[rel],
                        value=0.5,
                        risk=0.05,
                        effort=0.1,
                        confidence=0.95,
                        verification_cost=0.05,
                        evidence=f"'{func.name}()' contains only 'pass'",
                    ))

                has_assert = any(
                    isinstance(stmt, ast.Assert) or
                    (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and hasattr(stmt.value.func, "attr") and "assert" in stmt.value.func.attr)
                    for stmt in ast.walk(func)
                )
                if not has_assert and not any(isinstance(stmt, ast.Pass) for stmt in func.body):
                    opportunities.append(MaintenanceOpportunity(
                        category=OpportunityCategory.WEAK_TEST,
                        title=f"Non-asserting test: {func.name} in {rel}",
                        description="Test function has no assertions",
                        target_files=[rel],
                        value=0.4,
                        risk=0.05,
                        effort=0.1,
                        confidence=0.85,
                        verification_cost=0.05,
                        evidence=f"'{func.name}()' has no assert statements",
                    ))

        return opportunities

    def _detect_fragile_apis(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        fragile_patterns = {
            "except:": "Bare except clause",
            "except Exception:": "Overly broad exception",
            "try:": "Missing finally",
            "pass": "Unimplemented handler",
        }

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = str(f.relative_to(self.repo_path))
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            issues = []
            for pattern, label in fragile_patterns.items():
                if pattern == "except:" and "except:" in text:
                    issues.append(label)
                elif pattern in text:
                    pass

            if "except:" in text and "except Exception as" not in text:
                issues.append("Bare except without named exception handling")

            if issues:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.FRAGILE_API,
                    title=f"Fragile error handling in {rel}",
                    description="; ".join(issues),
                    target_files=[rel],
                    value=0.5,
                    risk=0.15,
                    effort=0.2,
                    confidence=0.7,
                    verification_cost=0.15,
                    evidence=f"Issues: {'; '.join(issues)}",
                ))

        return opportunities

    def _detect_documentation_gaps(self) -> List[MaintenanceOpportunity]:
        opportunities = []
        undoc_functions = []

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = str(f.relative_to(self.repo_path))
            if "test" in rel:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue
                    has_docstring = (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str))
                    if not has_docstring:
                        undoc_functions.append((rel, node.name))

        if undoc_functions:
            by_file = Counter(f for f, _ in undoc_functions)
            for file_path, count in by_file.most_common(5):
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.DOCUMENTATION_GAP,
                    title=f"Documentation gaps in {file_path}",
                    description=f"{count} public functions without docstrings",
                    target_files=[file_path],
                    value=0.3,
                    risk=0.02,
                    effort=0.2,
                    confidence=0.9,
                    verification_cost=0.05,
                    evidence=f"{count} undocumented public functions",
                ))

        if not (self.repo_path / "README.md").exists():
            opportunities.append(MaintenanceOpportunity(
                category=OpportunityCategory.DOCUMENTATION_GAP,
                title="Missing README.md",
                description="No top-level README documentation file",
                target_files=["README.md"],
                value=0.5,
                risk=0.01,
                effort=0.3,
                confidence=1.0,
                verification_cost=0.01,
                evidence="README.md does not exist",
            ))

        return opportunities

    def _detect_architectural_erosion(self) -> List[MaintenanceOpportunity]:
        opportunities = []

        try:
            assessor = FitnessAssessor(self.repo_path)
            assessment = assessor.assess()

            if assessment.overall_fitness < 0.4:
                opportunities.append(MaintenanceOpportunity(
                    category=OpportunityCategory.ARCHITECTURAL_EROSION,
                    title="Low overall architecture fitness",
                    description=f"Overall fitness score: {assessment.overall_fitness:.2f}",
                    target_files=[],
                    value=0.7,
                    risk=0.3,
                    effort=0.6,
                    confidence=0.6,
                    verification_cost=0.3,
                    evidence=f"Fitness assessment: {assessment.to_dict()}",
                ))

            for dim_name, score in assessment.scores.items():
                if score.score < 0.3:
                    opportunities.append(MaintenanceOpportunity(
                        category=OpportunityCategory.ARCHITECTURAL_EROSION,
                        title=f"Critical {dim_name} score: {score.score:.2f}",
                        description=score.explanation,
                        target_files=[],
                        value=0.6,
                        risk=0.25,
                        effort=0.5,
                        confidence=score.confidence,
                        verification_cost=0.25,
                        evidence=score.explanation,
                    ))
        except Exception as e:
            pass

        return opportunities

    def to_dict(self, opportunities: List[MaintenanceOpportunity]) -> List[Dict[str, Any]]:
        return [o.to_dict() for o in opportunities]
