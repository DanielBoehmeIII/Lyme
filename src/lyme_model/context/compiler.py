"""Context compiler — transforms repo + task into optimized context for small local models.

Bridges the Lyme Audit compression pipeline with the Lyme Model runtime.
Produces context strings optimized for 3-8B parameter model context windows.
"""

from __future__ import annotations
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path


@dataclass
class CompiledContext:
    repo_summary: str = ""
    task_context: str = ""
    structure: str = ""
    api_surface: str = ""
    risks: List[str] = field(default_factory=list)
    build_commands: List[str] = field(default_factory=list)
    test_commands: List[str] = field(default_factory=list)
    total_tokens: int = 0
    compile_time_s: float = 0.0

    def to_text(self) -> str:
        sections = []
        if self.repo_summary:
            sections.append("REPOSITORY SUMMARY")
            sections.append(self.repo_summary)
        if self.structure:
            sections.append("STRUCTURE")
            sections.append(self.structure)
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
            sections.append("RISKS")
            for r in self.risks:
                sections.append(f"  - {r}")
        return "\n\n".join(sections)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["text"] = self.to_text()
        return d


class ContextCompiler:
    """Compiles repository context optimized for small local models.

    Integrates with:
    - Lyme Audit compression pipeline (RepoSummarizer, CodebaseCompressor)
    - Hardware detection for context budget
    - Amplify context packet assembler for task-specific content
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    def compile(self, task: Optional[str] = None, max_tokens: Optional[int] = None) -> CompiledContext:
        """Compile repo context, optionally focused on a task."""
        start = time.time()

        compiled = CompiledContext()
        compiled.repo_summary = self._summarize_repo()
        compiled.structure = self._get_structure()
        compiled.api_surface = self._extract_api_surface()
        compiled.risks = self._find_risky_files()
        build_cmds, test_cmds = self._extract_commands()
        compiled.build_commands = build_cmds
        compiled.test_commands = test_cmds

        if task:
            compiled.task_context = self._build_task_context(task)

        compiled.compile_time_s = round(time.time() - start, 3)

        budget = max_tokens or self._estimate_token_budget(len(compiled.to_text()))
        compiled.total_tokens = self._count_tokens(compiled.to_text())

        if compiled.total_tokens > budget:
            compiled = self._truncate(compiled, budget)

        self._emit_trace(compiled, task)

        return compiled

    def _summarize_repo(self) -> str:
        """Quick repo summary using file tree scan."""
        repo = self.repo_path
        if not repo.exists():
            return f"Repository not found: {repo}"

        py_files = list(repo.rglob("*.py")) if repo.is_dir() else []
        js_files = list(repo.rglob("*.js")) + list(repo.rglob("*.jsx")) + list(repo.rglob("*.ts")) + list(repo.rglob("*.tsx"))
        total_files = len(py_files) + len(js_files)
        other = sum(1 for _ in repo.rglob("*") if _.is_file()) if repo.is_dir() else 0

        has_readme = (repo / "README.md").exists() or (repo / "README.rst").exists()
        has_tests = bool(list(repo.rglob("test_*.py")) + list(repo.rglob("*_test.py")) + list(repo.rglob("*.test.js")))
        has_setup = (repo / "setup.py").exists() or (repo / "setup.cfg").exists() or (repo / "pyproject.toml").exists()
        has_package_json = (repo / "package.json").exists()

        lines = [
            f"Repository: {repo.name}",
            f"Total files: {total_files + other}",
        ]
        if py_files:
            lines.append(f"Python files: {len(py_files)}")
        if js_files:
            lines.append(f"JS/TS files: {len(js_files)}")
        if has_readme:
            lines.append("Has README: yes")
        if has_tests:
            lines.append(f"Test files: {len(list(repo.rglob('test_*.py')))}")
        if has_setup:
            lines.append("Build: Python (setuptools/poetry)")
        if has_package_json:
            lines.append("Build: Node.js (npm/yarn)")

        return "\n".join(lines)

    def _get_structure(self) -> str:
        """Get top-level directory structure."""
        repo = self.repo_path
        if not repo.is_dir():
            return ""

        dirs = sorted([d.name + "/" for d in repo.iterdir() if d.is_dir() and not d.name.startswith((".", "__"))])
        files = sorted([f.name for f in repo.iterdir() if f.is_file() and not f.name.startswith(".")])
        items = dirs + files

        if len(items) > 40:
            items = items[:40]
        return "\n".join(items)

    def _extract_api_surface(self) -> str:
        """Extract top-level function/class names from Python files."""
        repo = self.repo_path
        if not repo.is_dir():
            return ""

        lines = []
        for f in sorted(repo.rglob("*.py")):
            if "site-packages" in str(f) or ".venv" in str(f) or "__pycache__" in str(f):
                continue
            content = f.read_text(errors="ignore")
            classes = []
            functions = []
            for line in content.split("\n"):
                s = line.strip()
                if s.startswith("class "):
                    name = s.split("(")[0].split(":")[0].replace("class ", "").strip()
                    if name and not name.startswith("_"):
                        classes.append(name)
                elif s.startswith("def ") and not s.startswith("def _"):
                    name = s.split("(")[0].replace("def ", "").strip()
                    if name:
                        functions.append(name)
            if classes or functions:
                rel = f.relative_to(repo)
                parts = []
                if classes:
                    parts.append(f"  classes: {', '.join(classes[:8])}")
                if functions:
                    parts.append(f"  functions: {', '.join(functions[:8])}")
                lines.append(f"{rel}")
                lines.extend(parts)

            if len(lines) > 100:
                lines.append("... (truncated)")
                break

        return "\n".join(lines[:120])

    def _find_risky_files(self) -> List[str]:
        """Identify files that are risky to modify."""
        repo = self.repo_path
        if not repo.is_dir():
            return []

        risks = []
        keywords = ["password", "secret", "token", "auth", "credential", "api_key"]
        for f in sorted(repo.rglob("*.py")):
            if "site-packages" in str(f) or ".venv" in str(f):
                continue
            try:
                content = f.read_text(errors="ignore").lower()
                if any(k in content for k in keywords):
                    rel = f.relative_to(repo)
                    risks.append(f"{rel} (contains sensitive keywords)")
            except Exception:
                continue
            if len(risks) >= 10:
                break
        return risks

    def _extract_commands(self) -> tuple:
        """Extract build and test commands from config files."""
        repo = self.repo_path
        build_cmds = []
        test_cmds = []

        if (repo / "Makefile").exists():
            make = (repo / "Makefile").read_text(errors="ignore")
            if "build:" in make:
                build_cmds.append("make build")
            if "test:" in make:
                test_cmds.append("make test")

        if (repo / "pyproject.toml").exists():
            build_cmds.append("pip install -e .")
            test_cmds.append("pytest")

        if (repo / "package.json").exists():
            build_cmds.append("npm run build")
            test_cmds.append("npm test")

        if (repo / "setup.py").exists():
            build_cmds.append("python setup.py install")

        if (repo / "Cargo.toml").exists():
            build_cmds.append("cargo build")
            test_cmds.append("cargo test")

        if (repo / "go.mod").exists():
            build_cmds.append("go build ./...")
            test_cmds.append("go test ./...")

        if not build_cmds:
            build_cmds.append("pip install -e .")
        if not test_cmds:
            test_cmds.append("pytest")

        return build_cmds, test_cmds

    def _build_task_context(self, task: str) -> str:
        """Build task-specific context."""
        return f"Request: {task}\nFocus on relevant files only."

    def _estimate_token_budget(self, text_length: int) -> int:
        """Estimate token budget based on text length."""
        from ..hardware.detector import detect_all
        try:
            profile = detect_all()
            vram = profile.gpu.vram_total_mb
            budget = estimate_context_limit(vram, 7.0, 4)
            return max(budget, 2048)
        except Exception:
            return 4096

    def _count_tokens(self, text: str) -> int:
        """Rough token count."""
        return len(text.split())

    def _truncate(self, compiled: CompiledContext, budget: int) -> CompiledContext:
        """Truncate context to fit within budget."""
        while compiled.total_tokens > budget:
            if compiled.api_surface:
                lines = compiled.api_surface.split("\n")
                compiled.api_surface = "\n".join(lines[:len(lines)//2])
            elif compiled.structure:
                lines = compiled.structure.split("\n")
                compiled.structure = "\n".join(lines[:len(lines)//2])
            elif compiled.repo_summary:
                compiled.repo_summary = compiled.repo_summary[:len(compiled.repo_summary)//2]
            else:
                break
            compiled.total_tokens = self._count_tokens(compiled.to_text())
        return compiled

    def _emit_trace(self, compiled: CompiledContext, task: Optional[str] = None) -> None:
        """Emit an audit trace for context compilation."""
        trace = {
            "event": "context_compiled",
            "trace_id": str(uuid.uuid4())[:8],
            "repo": str(self.repo_path),
            "task": task,
            "total_tokens": compiled.total_tokens,
            "compile_time_s": compiled.compile_time_s,
            "has_summary": bool(compiled.repo_summary),
            "has_task_context": bool(compiled.task_context),
            "risk_count": len(compiled.risks),
            "timestamp": time.time(),
        }
        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"context-{trace['trace_id']}.json"
        trace_file.write_text(json.dumps(trace, indent=2))


def estimate_context_limit(vram_total_mb: int, model_size_b: float, bits: int) -> int:
    from ..hardware.budget import estimate_context_limit as _estimate
    return _estimate(vram_total_mb, model_size_b, bits)
