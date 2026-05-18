from __future__ import annotations
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class RepoSummary:
    name: str = ""
    description: str = ""
    language: str = ""
    total_files: int = 0
    total_lines: int = 0
    contributors: int = 0
    branches: int = 0
    open_prs: int = 0
    test_count: int = 0
    top_directories: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "contributors": self.contributors,
            "branches": self.branches,
            "open_prs": self.open_prs,
            "test_count": self.test_count,
            "top_directories": self.top_directories[:10],
            "key_files": self.key_files[:10],
            "frameworks": self.frameworks[:10],
            "conventions": self.conventions[:10],
        }

    def to_markdown(self) -> str:
        lines = [f"# {self.name}\n"]
        if self.description:
            lines.append(f"{self.description}\n")
        lines.append(f"**Language**: {self.language}\n")
        lines.append(f"**Contributors**: {self.contributors} | **Branches**: {self.branches}")
        lines.append(f"**Files**: {self.total_files} ({self.total_lines} lines) | **Tests**: {self.test_count}")
        lines.append("")
        if self.top_directories:
            lines.append("## Structure\n")
            for d in self.top_directories[:8]:
                lines.append(f"- {d}")
            lines.append("")
        if self.frameworks:
            lines.append("## Frameworks\n")
            for f in self.frameworks:
                lines.append(f"- {f}")
            lines.append("")
        if self.conventions:
            lines.append("## Conventions\n")
            for c in self.conventions:
                lines.append(f"- {c}")
            lines.append("")
        return "\n".join(lines)


class TeamKnowledgeBase:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "team" / "knowledge.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._knowledge: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                self._knowledge = json.loads(self._db_path.read_text())
            except Exception:
                self._knowledge = {}

    def _save(self) -> None:
        self._db_path.write_text(json.dumps(self._knowledge, indent=2))

    def store(self, key: str, value: Any) -> None:
        self._knowledge[key] = {"value": value, "updated": __import__("time").time()}
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._knowledge.get(key)
        if entry and isinstance(entry, dict):
            return entry.get("value", default)
        return default

    def get_all(self) -> Dict[str, Any]:
        return {k: v.get("value") if isinstance(v, dict) else v for k, v in self._knowledge.items()}

    def list_keys(self) -> List[str]:
        return list(self._knowledge.keys())

    # --- Team conventions ---

    def record_convention(self, name: str, pattern: str, description: str) -> None:
        conventions = self.get("team_conventions", [])
        conventions.append({"name": name, "pattern": pattern, "description": description, "added": __import__("time").time()})
        self.store("team_conventions", conventions)

    def conventions(self) -> List[Dict[str, Any]]:
        return self.get("team_conventions", [])

    # --- Architectural standards ---

    def record_standard(self, name: str, description: str, files: List[str]) -> None:
        standards = self.get("arch_standards", [])
        standards.append({"name": name, "description": description, "files": files, "added": __import__("time").time()})
        self.store("arch_standards", standards)

    def standards(self) -> List[Dict[str, Any]]:
        return self.get("arch_standards", [])

    # --- Repo memory ---

    def record_fact(self, key: str, fact: str) -> None:
        facts = self.get("repo_facts", {})
        facts[key] = {"fact": fact, "recorded": __import__("time").time()}
        self.store("repo_facts", facts)

    def facts(self) -> Dict[str, Any]:
        return self.get("repo_facts", {})

    # --- Generate onboarding summary ---

    def generate_summary(self) -> RepoSummary:
        summary = RepoSummary()
        try:
            summary.name = self._repo.name
            summary.description = self._get_repo_description()
            summary.language = self._detect_language()
            summary.total_files = self._count_files()
            summary.total_lines = self._count_lines()
            summary.contributors = self._count_contributors()
            summary.branches = self._count_branches()
            summary.test_count = self._count_tests()
            summary.top_directories = self._get_top_directories()
            summary.key_files = self._get_key_files()
            summary.frameworks = self._detect_frameworks()
            summary.conventions = self._detect_conventions()
        except Exception:
            pass
        return summary

    def _get_repo_description(self) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--format=%s", "-10"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self._repo),
            )
            commits = [l for l in result.stdout.splitlines() if l.strip()]
            return commits[0] if commits else ""
        except Exception:
            return ""

    def _detect_language(self) -> str:
        exts = Counter()
        for f in self._repo.rglob("*"):
            if f.suffix and not f.name.startswith("."):
                exts[f.suffix] += 1
        lang_map = {".py": "Python", ".ts": "TypeScript", ".js": "JavaScript",
                    ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
                    ".md": "Markdown", ".yaml": "YAML", ".json": "JSON"}
        for ext, lang in lang_map.items():
            if exts.get(ext, 0) > 5:
                return lang
        return "Unknown"

    def _count_files(self) -> int:
        return sum(1 for f in self._repo.rglob("*")
                   if f.is_file() and ".lyme" not in str(f) and ".git" not in str(f))

    def _count_lines(self) -> int:
        total = 0
        for f in list(self._repo.rglob("*.py"))[:50]:
            try:
                total += len(f.read_text().splitlines())
            except Exception:
                pass
        return total

    def _count_contributors(self) -> int:
        try:
            result = subprocess.run(
                ["git", "shortlog", "-sn"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            return len([l for l in result.stdout.splitlines() if l.strip()])
        except Exception:
            return 0

    def _count_branches(self) -> int:
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self._repo),
            )
            return len([l for l in result.stdout.splitlines() if l.strip()])
        except Exception:
            return 0

    def _count_tests(self) -> int:
        test_files = list(self._repo.rglob("test_*.py")) + list(self._repo.rglob("*_test.py"))
        return len(test_files)

    def _get_top_directories(self) -> List[str]:
        dirs = Counter()
        for f in self._repo.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                parent = f.relative_to(self._repo).parent
                if str(parent) != ".":
                    top = str(parent).split("/")[0]
                    dirs[top] += 1
        return [d for d, _ in dirs.most_common(15)]

    def _get_key_files(self) -> List[str]:
        key_files = []
        for name in ["README.md", "pyproject.toml", "package.json", "Makefile", "Dockerfile",
                      "docker-compose.yml", ".github/workflows/ci.yml"]:
            path = self._repo / name
            if path.exists():
                key_files.append(name)
        return key_files

    def _detect_frameworks(self) -> List[str]:
        frameworks = []
        pyproject = self._repo / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text()
            if "pytest" in text:
                frameworks.append("pytest")
            if "torch" in text or "tensorflow" in text:
                frameworks.append("PyTorch/TensorFlow")
            if "fastapi" in text or "flask" in text or "django" in text:
                frameworks.append("FastAPI/Flask/Django")
        return frameworks

    def _detect_conventions(self) -> List[str]:
        conv = []
        stored = self.conventions()
        for c in stored:
            conv.append(f"{c['name']}: {c['description']}")
        pyproject = self._repo / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text()
            if "black" in text:
                conv.append("Code formatting: black")
            if "ruff" in text:
                conv.append("Linting: ruff")
            if "mypy" in text:
                conv.append("Type checking: mypy")
        return conv


team_knowledge = TeamKnowledgeBase()
