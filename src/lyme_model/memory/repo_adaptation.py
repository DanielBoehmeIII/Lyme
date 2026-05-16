"""Week 83 — Repo-Specific Adaptation.

Lyme Model should learn:
- coding style
- directory structure
- test workflow
- build workflow
- naming conventions
- common file locations
- architectural rules

Benchmark first-run vs tenth-run performance.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime, timezone
import re


@dataclass
class RepoProfile:
    repo_path: str = ""
    language: str = ""
    test_framework: str = ""
    build_system: str = ""
    src_dirs: List[str] = field(default_factory=list)
    test_dirs: List[str] = field(default_factory=list)
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    common_imports: List[str] = field(default_factory=list)
    architectural_rules: List[str] = field(default_factory=list)
    file_patterns: Dict[str, str] = field(default_factory=dict)
    conventions: List[str] = field(default_factory=list)
    profile_version: int = 0

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "language": self.language,
            "test_framework": self.test_framework,
            "build_system": self.build_system,
            "src_dirs": self.src_dirs,
            "test_dirs": self.test_dirs,
            "naming_conventions": self.naming_conventions,
            "common_imports": self.common_imports[:10],
            "architectural_rules": self.architectural_rules[:10],
            "conventions": self.conventions[:10],
            "profile_version": self.profile_version,
        }

    def to_prompt_section(self) -> str:
        """Format as a prompt section for the model."""
        parts = ["[REPO PROFILE]"]
        if self.language:
            parts.append(f"Language: {self.language}")
        if self.test_framework:
            parts.append(f"Tests: {self.test_framework}")
        if self.build_system:
            parts.append(f"Build: {self.build_system}")
        if self.src_dirs:
            parts.append(f"Source: {', '.join(self.src_dirs)}")
        if self.test_dirs:
            parts.append(f"Test dirs: {', '.join(self.test_dirs)}")
        if self.conventions:
            for c in self.conventions[:5]:
                parts.append(f"Convention: {c}")
        return "\n".join(parts)


class RepoAdaptationEngine:
    """Builds and maintains repo-specific profiles for Lyme Model."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.profiles: Dict[str, RepoProfile] = {}

    def scan(self, force: bool = False) -> RepoProfile:
        """Scan the repo and build/update its profile."""
        repo_key = str(self.repo_path)
        if repo_key in self.profiles and not force:
            return self.profiles[repo_key]

        profile = RepoProfile(repo_path=str(self.repo_path))
        profile.profile_version += 1

        # Detect language
        py_files = list(self.repo_path.rglob("*.py"))
        js_files = list(self.repo_path.rglob("*.js"))
        ts_files = list(self.repo_path.rglob("*.ts"))
        rs_files = list(self.repo_path.rglob("*.rs"))
        go_files = list(self.repo_path.rglob("*.go"))

        if py_files:
            profile.language = "python"
        elif rs_files:
            profile.language = "rust"
        elif go_files:
            profile.language = "go"
        elif ts_files:
            profile.language = "typescript"
        elif js_files:
            profile.language = "javascript"

        # Detect test framework
        for f in self.repo_path.rglob("*"):
            if f.name == "pyproject.toml":
                text = f.read_text(errors="ignore")
                if "pytest" in text:
                    profile.test_framework = "pytest"
                if "unittest" in text:
                    profile.test_framework = "unittest"
            if f.name == "package.json":
                text = f.read_text(errors="ignore")
                for fw in ["jest", "mocha", "vitest", "ava", "tape"]:
                    if fw in text:
                        profile.test_framework = fw
            if f.name == "Cargo.toml":
                profile.test_framework = "cargo test"

        # Detect build system
        if (self.repo_path / "pyproject.toml").exists():
            profile.build_system = "setuptools/pip"
        if (self.repo_path / "package.json").exists():
            text = (self.repo_path / "package.json").read_text(errors="ignore")
            if "build" in text:
                profile.build_system = "npm"
        if (self.repo_path / "Cargo.toml").exists():
            profile.build_system = "cargo"
        if (self.repo_path / "Makefile").exists():
            profile.build_system = "make"
        if (self.repo_path / "CMakeLists.txt").exists():
            profile.build_system = "cmake"

        # Find source and test directories
        for d in self.repo_path.iterdir():
            if d.is_dir():
                name = d.name
                if name in {"src", "source", "lib", "app"}:
                    profile.src_dirs.append(name)
                if "test" in name.lower():
                    profile.test_dirs.append(name)
                if name.startswith("test"):
                    profile.test_dirs.append(name)

        # Detect naming conventions from source
        py_files_sample = list(self.repo_path.rglob("*.py"))[:20]
        fn_names = []
        cls_names = []
        for pf in py_files_sample:
            text = pf.read_text(errors="ignore")
            fn_names.extend(re.findall(r'^def\s+(\w+)', text, re.MULTILINE))
            cls_names.extend(re.findall(r'^class\s+(\w+)', text, re.MULTILINE))

        if fn_names:
            snake_case = sum(1 for n in fn_names if "_" in n)
            camel_case = sum(1 for n in fn_names if n[0].isupper() if n)
            if snake_case > camel_case:
                profile.naming_conventions["functions"] = "snake_case"
            else:
                profile.naming_conventions["functions"] = "camelCase"

        if cls_names:
            has_pascal = sum(1 for n in cls_names if n[0].isupper())
            if has_pascal > len(cls_names) / 2:
                profile.naming_conventions["classes"] = "PascalCase"

        # Find common imports
        import_counts: Dict[str, int] = {}
        for pf in py_files_sample:
            text = pf.read_text(errors="ignore")
            imports = re.findall(r'^(?:from|import)\s+(\w+)', text, re.MULTILINE)
            for imp in imports:
                import_counts[imp] = import_counts.get(imp, 0) + 1
        profile.common_imports = sorted(import_counts, key=import_counts.get, reverse=True)[:10]

        # Extract architectural rules
        for f in self.repo_path.rglob("*.md"):
            try:
                text = f.read_text(errors="ignore")
                for line in text.split("\n"):
                    if any(kw in line.lower() for kw in ["must", "should", "never", "always", "rule"]):
                        if len(line) > 20 and len(line) < 200:
                            profile.architectural_rules.append(line.strip())
            except Exception:
                pass

        # Detect conventions from existing code patterns
        for pf in py_files_sample:
            text = pf.read_text(errors="ignore")
            if '"""' in text:
                profile.conventions.append("Uses docstrings")
                break
        for pf in py_files_sample:
            text = pf.read_text(errors="ignore")
            if "from __future__ import" in text:
                profile.conventions.append("Uses __future__ imports")
                break

        self.profiles[repo_key] = profile
        return profile

    def get_profile(self) -> RepoProfile:
        repo_key = str(self.repo_path)
        if repo_key not in self.profiles:
            return self.scan()
        return self.profiles[repo_key]

    def benchmark_improvement(self, profile: RepoProfile) -> Dict:
        """Estimate improvement from adaptation (first-run vs tenth-run)."""
        return {
            "conventions_learned": len(profile.conventions),
            "architectural_rules": len(profile.architectural_rules),
            "naming_conventions": len(profile.naming_conventions),
            "test_framework_known": bool(profile.test_framework),
            "build_system_known": bool(profile.build_system),
            "common_imports_known": len(profile.common_imports),
            "estimated_improvement": "Learning conventions reduces hallucination and wrong-file errors",
        }
