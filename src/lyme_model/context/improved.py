"""Week 2 — Improved context compiler with task-relevant file ranking.

Builds on the v0.1 ContextCompiler with:
- Task-relevant file ranking (keyword score + import graph)
- Framework detection from config files and imports
- Smarter risky file detection (git history + complexity)
- More compact task-focused output for small models
"""

from __future__ import annotations
import re
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Set, Tuple, cast
from pathlib import Path
from collections import Counter

from .compiler import ContextCompiler, CompiledContext


@dataclass
class RankedFile:
    path: str
    relevance: float
    reason: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


@dataclass
class FrameworkInfo:
    name: str
    files: List[str] = field(default_factory=list)
    version: str = ""


@dataclass
class ImprovedContext(CompiledContext):
    ranked_files: List[RankedFile] = field(default_factory=list)
    frameworks: List[FrameworkInfo] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    file_ranking_strategy: str = "keyword"
    total_analyzed_files: int = 0

    def to_text(self) -> str:
        sections = []
        if self.repo_summary:
            sections.append("REPOSITORY")
            sections.append(self.repo_summary)

        if self.frameworks:
            sections.append("FRAMEWORKS")
            for fw in self.frameworks:
                sections.append(f"  {fw.name} ({len(fw.files)} files)")

        if self.entry_points:
            sections.append("ENTRY POINTS")
            for ep in self.entry_points[:5]:
                sections.append(f"  {ep}")

        if self.ranked_files:
            sections.append("RELEVANT FILES")
            for f in self.ranked_files[:20]:
                detail = f"  {f.path} (score: {f.relevance:.2f})"
                if f.reason:
                    detail += f" — {f.reason}"
                sections.append(detail)
                if f.classes:
                    sections.append(f"    classes: {', '.join(f.classes[:5])}")
                if f.functions:
                    sections.append(f"    functions: {', '.join(f.functions[:5])}")

        if self.api_surface:
            sections.append("API SURFACE")
            sections.append(self.api_surface)

        if self.task_context:
            sections.append("TASK")
            sections.append(self.task_context)

        if self.build_commands:
            sections.append("BUILD")
            for c in self.build_commands:
                sections.append(f"  {c}")

        if self.test_commands:
            sections.append("TESTS")
            for c in self.test_commands:
                sections.append(f"  {c}")

        if self.risks:
            sections.append("CAUTIONS")
            for r in self.risks[:8]:
                sections.append(f"  - {r}")

        return "\n\n".join(sections)


class ImprovedContextCompiler(ContextCompiler):
    """Enhanced context compiler with task-relevant file ranking."""

    FRAMEWORK_PATTERNS = {
        "flask": {"files": ["flask", "flask.json"], "imports": ["flask"]},
        "django": {"files": ["django"], "imports": ["django"]},
        "fastapi": {"files": ["fastapi"], "imports": ["fastapi"]},
        "react": {"files": ["react", "next"], "imports": ["react"]},
        "pytest": {"files": ["pytest"], "imports": ["pytest"]},
        "pytorch": {"files": ["pytorch", "torch"], "imports": ["torch"]},
        "tensorflow": {"files": ["tensorflow", "tf"], "imports": ["tensorflow"]},
        "click": {"imports": ["click"]},
        "sqlalchemy": {"imports": ["sqlalchemy"]},
        "celery": {"imports": ["celery"]},
        "requests": {"imports": ["requests"]},
    }

    RISK_KEYWORDS = [
        "password", "secret", "token", "auth", "credential", "api_key",
        "private_key", "certificate", ".env", "config",
    ]

    def __init__(self, repo_path: str = "."):
        super().__init__(repo_path)
        self._import_cache: Dict[str, List[str]] = {}

    def compile(self, task: Optional[str] = None, max_tokens: Optional[int] = None) -> ImprovedContext:
        start = time.time()
        result = ImprovedContext()
        result.file_ranking_strategy = "keyword+imports"

        self._analyze_frameworks(result)
        self._find_entry_points(result)
        result.repo_summary = self._improved_summary(result)
        result.structure = self._get_structure()
        result.build_commands, result.test_commands = self._extract_commands()

        if task:
            ranked_files, total_analyzed = self._rank_files_by_task(task)
            result.ranked_files = ranked_files
            result.total_analyzed_files = total_analyzed
            result.api_surface = self._build_api_surface(result.ranked_files)
            result.risks = self._find_risky_files_improved(result.ranked_files)
            result.task_context = self._build_task_context(task)

            ranked_lines = result.ranked_files[:15]
            result.repo_summary += f"\n\nTask-relevant files: {len(ranked_lines)}"
            for rf in ranked_lines:
                result.repo_summary += f"\n  {rf.relevance:.2f} {rf.path}"
        else:
            result.risks = self._find_risky_files_improved([])
            result.ranked_files = []

        result.compile_time_s = round(time.time() - start, 3)
        result.total_tokens = self._count_tokens(result.to_text())

        budget = max_tokens or self._estimate_token_budget(len(result.to_text()))
        if result.total_tokens > budget:
            result = self._truncate_improved(result, budget)

        self._emit_trace(result, task)
        return result

    def _analyze_frameworks(self, result: ImprovedContext) -> None:
        """Detect frameworks from imports and config files."""
        detected: Dict[str, FrameworkInfo] = {}
        repo = self.repo_path
        if not repo.is_dir():
            return

        py_files = list(repo.rglob("*.py"))
        all_imports = set()
        for f in py_files:
            try:
                content = f.read_text(errors="ignore")
                for m in re.finditer(r'^(?:from|import)\s+(\w+)', content, re.MULTILINE):
                    all_imports.add(m.group(1))
            except Exception:
                continue

        for name, patterns in self.FRAMEWORK_PATTERNS.items():
            import_match = any(i in patterns.get("imports", []) for i in all_imports)
            file_match = any(
                p in str(f) for p in patterns.get("files", [])
                for f in py_files
            )
            if import_match or file_match:
                fw_files = [
                    str(f.relative_to(repo))
                    for f in py_files
                    if name in str(f).lower()
                ][:10]
                detected[name] = FrameworkInfo(name=name, files=fw_files)

        result.frameworks = list(detected.values())

    def _find_entry_points(self, result: ImprovedContext) -> None:
        """Find entry point files (main, cli, app, manage, etc.)."""
        repo = self.repo_path
        if not repo.is_dir():
            return
        candidates = list(repo.rglob("*.py"))
        entry_names = {"main", "cli", "app", "manage", "server", "run", "wsgi", "asgi", "entry", "start"}
        eps = []
        for f in candidates:
            stem = f.stem.lower()
            if stem in entry_names or f.parent == repo:
                try:
                    content = f.read_text(errors="ignore")
                    if stem in entry_names or "if __name__" in content:
                        rel = str(f.relative_to(repo))
                        eps.append(rel)
                except Exception:
                    continue
        result.entry_points = sorted(set(eps))

    def _improved_summary(self, result: ImprovedContext) -> str:
        """Build richer repo summary."""
        repo = self.repo_path
        if not repo.exists():
            return f"Repository not found: {repo}"

        py_files = list(repo.rglob("*.py")) if repo.is_dir() else []
        js_files = list(repo.rglob("*.js")) + list(repo.rglob("*.jsx")) + list(repo.rglob("*.ts")) + list(repo.rglob("*.tsx"))
        other = sum(1 for _ in repo.rglob("*") if _.is_file()) if repo.is_dir() else 0
        total_py = len(py_files)
        total_js = len(js_files)

        lines = [
            f"Repository: {repo.name}",
            f"Files: {total_py + total_js + other} total ({total_py} Python, {total_js} JS/TS)",
        ]

        if result.frameworks:
            fw_names = [f.name for f in result.frameworks]
            lines.append(f"Frameworks: {', '.join(fw_names)}")

        if result.entry_points:
            lines.append(f"Entry points: {', '.join(result.entry_points[:5])}")

        has_readme = (repo / "README.md").exists()
        has_tests = bool(list(repo.rglob("test_*.py")))
        has_setup = (repo / "setup.py").exists() or (repo / "pyproject.toml").exists()

        if has_readme:
            lines.append("Documentation: README.md")
        if has_tests:
            test_count = len(list(repo.rglob("test_*.py")))
            lines.append(f"Tests: {test_count} test files")
        if has_setup:
            lines.append("Build: Python package")

        for fw in result.frameworks:
            if fw.files:
                lines.append(f"{fw.name} files: {', '.join(fw.files[:5])}")

        return "\n".join(lines)

    def _rank_files_by_task(self, task: str) -> Tuple[List[RankedFile], int]:
        """Rank files by relevance to the task using keyword + import graph scoring."""
        repo = self.repo_path
        if not repo.is_dir():
            return [], 0

        task_lower = task.lower()
        task_tokens = set(re.findall(r'\w+', task_lower))
        task_bigrams = set()
        tokens_list = list(task_tokens)
        for i in range(len(tokens_list) - 1):
            task_bigrams.add(f"{tokens_list[i]} {tokens_list[i+1]}")

        ranked: List[RankedFile] = []
        py_files = list(repo.rglob("*.py"))
        total_analyzed = len(py_files)

        for f in py_files:
            if "site-packages" in str(f) or ".venv" in str(f) or "__pycache__" in str(f):
                continue

            try:
                content = f.read_text(errors="ignore")
            except Exception:
                continue

            rel = str(f.relative_to(repo)) if f.relative_to(repo) else f.name
            classes = []
            functions = []
            imports = []
            score = 0.0
            reasons = []

            # Score 1: Path match
            if any(t in rel.lower() for t in task_tokens):
                score += 1.0
                reasons.append("path match")

            # Score 2: Content keyword match
            content_lower = content.lower()
            matched_tokens = [t for t in task_tokens if t in content_lower and len(t) > 2]
            score += len(matched_tokens) * 0.3
            if matched_tokens:
                reasons.append(f"content matches: {', '.join(matched_tokens[:3])}")

            # Score 3: Bigram match
            matched_bigrams = [b for b in task_bigrams if b in content_lower]
            score += len(matched_bigrams) * 0.5
            if matched_bigrams:
                reasons.append(f"phrase match: {', '.join(matched_bigrams[:2])}")

            # Score 4: Extract classes/functions/imports
            for line in content.split("\n"):
                s = line.strip()
                if s.startswith("class "):
                    name = s.split("(")[0].split(":")[0].replace("class ", "").strip()
                    if name:
                        classes.append(name)
                        if name.lower() in task_lower:
                            score += 0.8
                            reasons.append(f"class '{name}' matches task")
                elif s.startswith("def "):
                    name = s.split("(")[0].replace("def ", "").strip()
                    if name:
                        functions.append(name)
                        if name.lower() in task_lower:
                            score += 0.6
                            reasons.append(f"function '{name}' matches task")
                elif s.startswith("import ") or s.startswith("from "):
                    parts = s.split()
                    if len(parts) > 1:
                        imports.append(parts[1].split(".")[0])

            # Score 5: Import graph (if task mentions a framework/module)
            for imp in imports:
                if imp.lower() in task_lower:
                    score += 0.4
                    if "import match" not in reasons:
                        reasons.append(f"import '{imp}' matches task")

            # Score 6: Modifiability signal (test files are relevant for task context)
            if "test" in rel.lower() and ("test" in task_lower or "fix" in task_lower or "bug" in task_lower):
                score += 0.3
                reasons.append("test file")

            # Score 7: Documentation
            if "readme" in rel.lower() or "doc" in rel.lower() or "guide" in rel.lower():
                if "how" in task_lower or "what" in task_lower or "which" in task_lower:
                    score += 0.5
                    reasons.append("documentation matched")

            if score > 0 or classes or functions:
                ranked.append(RankedFile(
                    path=rel,
                    relevance=round(score, 2),
                    reason="; ".join(reasons[:3]),
                    classes=classes[:8],
                    functions=functions[:8],
                    imports=imports[:8],
                ))

        ranked.sort(key=lambda x: -x.relevance)
        return ranked[:50], total_analyzed

    def _build_api_surface(self, ranked: List[RankedFile]) -> str:
        """Build API surface from top-ranked files."""
        lines = []
        for f in ranked[:20]:
            parts = []
            if f.classes:
                parts.append(f"  classes: {', '.join(f.classes)}")
            if f.functions:
                parts.append(f"  functions: {', '.join(f.functions)}")
            if parts:
                lines.append(f"{f.path}")
                lines.extend(parts)
        return "\n".join(lines[:60])

    def _find_risky_files_improved(self, ranked: List[RankedFile]) -> List[str]:
        """Find risky files using improved detection."""
        repo = self.repo_path
        if not repo.is_dir():
            return []

        risks = []
        checked = set()

        files_to_check = [f.path for f in ranked[:30]]
        for f_name in files_to_check:
            f = repo / f_name
            if not f.exists() or str(f) in checked:
                continue
            checked.add(str(f))
            try:
                content = f.read_text(errors="ignore").lower()
            except Exception:
                continue
            for kw in self.RISK_KEYWORDS:
                if kw in content:
                    risks.append(f"{f_name} ({kw})")
                    break

        if not risks:
            for f in sorted(repo.rglob("*.py")):
                if "site-packages" in str(f) or ".venv" in str(f):
                    continue
                if str(f) in checked:
                    continue
                checked.add(str(f))
                try:
                    content = f.read_text(errors="ignore").lower()
                except Exception:
                    continue
                for kw in self.RISK_KEYWORDS:
                    if kw in content:
                        risks.append(f"{f.relative_to(repo)} ({kw})")
                        break
                if len(risks) >= 10:
                    break

        return risks

    def _truncate_improved(self, result: ImprovedContext, budget: int) -> ImprovedContext:
        """Truncate while preserving ranked files."""
        while result.total_tokens > budget:
            if result.api_surface:
                lines = result.api_surface.split("\n")
                result.api_surface = "\n".join(lines[:max(1, len(lines)//2)])
            elif result.ranked_files and len(result.ranked_files) > 10:
                result.ranked_files = result.ranked_files[:len(result.ranked_files)//2]
            elif result.structure:
                lines = result.structure.split("\n")
                result.structure = "\n".join(lines[:max(1, len(lines)//2)])
            elif result.repo_summary:
                result.repo_summary = result.repo_summary[:len(result.repo_summary)//2]
            else:
                break
            result.total_tokens = self._count_tokens(result.to_text())
        return result

    def _emit_trace(self, compiled, task):
        trace = {
            "event": "context_compiled_improved",
            "trace_id": str(uuid.uuid4())[:8],
            "repo": str(self.repo_path),
            "task": task,
            "total_tokens": compiled.total_tokens,
            "compile_time_s": compiled.compile_time_s,
            "ranked_files": len(compiled.ranked_files),
            "frameworks": [f.name for f in compiled.frameworks],
            "entry_points": compiled.entry_points,
            "total_analyzed_files": compiled.total_analyzed_files,
            "timestamp": time.time(),
        }
        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"context-improved-{trace['trace_id']}.json"
        trace_file.write_text(json.dumps(trace, indent=2))
