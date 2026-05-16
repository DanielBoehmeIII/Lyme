"""lyme doctor — Local Repo Doctor.

Product: inspect a repository and produce a useful diagnosis.
Research: collect graph quality metrics, uncertainty, invariants, failure zones.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import os
import subprocess
import re


@dataclass
class ProjectStructure:
    language: str = "unknown"
    framework: str = "unknown"
    build_system: str = "unknown"
    file_count: int = 0
    dir_count: int = 0
    total_lines: int = 0
    test_file_count: int = 0
    doc_file_count: int = 0
    config_file_count: int = 0
    has_readme: bool = False
    has_license: bool = False
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    top_level_dirs: List[str] = field(default_factory=list)
    source_dirs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "framework": self.framework,
            "build_system": self.build_system,
            "file_count": self.file_count,
            "dir_count": self.dir_count,
            "total_lines": self.total_lines,
            "test_file_count": self.test_file_count,
            "doc_file_count": self.doc_file_count,
            "config_file_count": self.config_file_count,
            "has_readme": self.has_readme,
            "has_license": self.has_license,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "has_ci": self.has_ci,
            "top_level_dirs": self.top_level_dirs,
            "source_dirs": self.source_dirs,
        }


@dataclass
class BuildCommands:
    build: Optional[str] = None
    test: Optional[str] = None
    lint: Optional[str] = None
    typecheck: Optional[str] = None
    format: Optional[str] = None
    clean: Optional[str] = None
    dev: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "build": self.build,
            "test": self.test,
            "lint": self.lint,
            "typecheck": self.typecheck,
            "format": self.format,
            "clean": self.clean,
            "dev": self.dev,
        }


@dataclass
class RiskyFile:
    path: str
    risk_score: float
    reasons: List[str]
    complexity: float = 0.0
    change_frequency: int = 0
    lines: int = 0
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "risk_score": self.risk_score,
            "reasons": self.reasons,
            "complexity": self.complexity,
            "change_frequency": self.change_frequency,
            "lines": self.lines,
            "dependencies": self.dependencies[:10],
        }


@dataclass
class ArchitecturalHotspot:
    subsystem: str
    risk_score: float
    file_count: int
    total_complexity: float
    coupling_count: int
    description: str
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subsystem": self.subsystem,
            "risk_score": self.risk_score,
            "file_count": self.file_count,
            "total_complexity": self.total_complexity,
            "coupling_count": self.coupling_count,
            "description": self.description,
            "files": self.files[:10],
        }


@dataclass
class CircularDependency:
    cycle: List[str]
    length: int
    severity: str
    files_involved: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "length": self.length,
            "severity": self.severity,
            "files_involved": self.files_involved,
        }


@dataclass
class StaleArea:
    path: str
    last_modified_days: int
    file_count: int
    risk_of_decay: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "last_modified_days": self.last_modified_days,
            "file_count": self.file_count,
            "risk_of_decay": self.risk_of_decay,
            "reason": self.reason,
        }


@dataclass
class MissingDocumentation:
    path: str
    type: str
    severity: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "type": self.type,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


@dataclass
class OnboardingPath:
    entry_points: List[str] = field(default_factory=list)
    recommended_order: List[str] = field(default_factory=list)
    estimated_ramp_up: str = "unknown"
    key_concepts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entry_points": self.entry_points,
            "recommended_order": self.recommended_order,
            "estimated_ramp_up": self.estimated_ramp_up,
            "key_concepts": self.key_concepts,
        }


@dataclass
class SuggestedImprovement:
    category: str
    priority: str
    description: str
    effort: str
    impact: str
    files_involved: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "priority": self.priority,
            "description": self.description,
            "effort": self.effort,
            "impact": self.impact,
            "files_involved": self.files_involved,
        }


@dataclass
class ResearchDiagnostics:
    graph_quality_score: float = 0.0
    uncertainty_estimates: dict = field(default_factory=dict)
    missing_evidence: List[str] = field(default_factory=list)
    confidence_scores: dict = field(default_factory=dict)
    inferred_invariants_count: int = 0
    likely_failure_zones: List[str] = field(default_factory=list)
    invariant_hypotheses: List[dict] = field(default_factory=list)
    graph_completeness: float = 0.0

    def to_dict(self) -> dict:
        return {
            "graph_quality_score": self.graph_quality_score,
            "uncertainty_estimates": self.uncertainty_estimates,
            "missing_evidence": self.missing_evidence,
            "confidence_scores": self.confidence_scores,
            "inferred_invariants_count": self.inferred_invariants_count,
            "likely_failure_zones": self.likely_failure_zones,
            "invariant_hypotheses": self.invariant_hypotheses,
            "graph_completeness": self.graph_completeness,
        }


@dataclass
class RepoDiagnosis:
    repo_path: str
    repo_name: str
    project_structure: ProjectStructure = field(default_factory=ProjectStructure)
    build_commands: BuildCommands = field(default_factory=BuildCommands)
    test_commands: List[str] = field(default_factory=list)
    risky_files: List[RiskyFile] = field(default_factory=list)
    architectural_hotspots: List[ArchitecturalHotspot] = field(default_factory=list)
    circular_dependencies: List[CircularDependency] = field(default_factory=list)
    stale_areas: List[StaleArea] = field(default_factory=list)
    missing_documentation: List[MissingDocumentation] = field(default_factory=list)
    onboarding_path: OnboardingPath = field(default_factory=OnboardingPath)
    suggested_improvements: List[SuggestedImprovement] = field(default_factory=list)
    research: ResearchDiagnostics = field(default_factory=ResearchDiagnostics)
    diagnosis_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "repo_name": self.repo_name,
            "project_structure": self.project_structure.to_dict(),
            "build_commands": self.build_commands.to_dict(),
            "test_commands": self.test_commands,
            "risky_files": [f.to_dict() for f in self.risky_files[:20]],
            "architectural_hotspots": [h.to_dict() for h in self.architectural_hotspots],
            "circular_dependencies": [c.to_dict() for c in self.circular_dependencies],
            "stale_areas": [s.to_dict() for s in self.stale_areas],
            "missing_documentation": [m.to_dict() for m in self.missing_documentation],
            "onboarding_path": self.onboarding_path.to_dict(),
            "suggested_improvements": [s.to_dict() for s in self.suggested_improvements],
            "research": self.research.to_dict(),
            "diagnosis_confidence": self.diagnosis_confidence,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# `lyme doctor`: {self.repo_name}")
        lines.append(f"")
        lines.append(f"**Confidence**: {self.diagnosis_confidence:.0%}")
        lines.append(f"")

        s = self.project_structure
        lines.append(f"## Project Structure")
        lines.append(f"- Language: {s.language}")
        lines.append(f"- Framework: {s.framework}")
        lines.append(f"- Build system: {s.build_system}")
        lines.append(f"- Files: {s.file_count} in {s.dir_count} directories ({s.total_lines} lines)")
        lines.append(f"- Tests: {s.test_file_count} test files")
        lines.append(f"- Docs: {s.doc_file_count} doc files")
        lines.append(f"- Config: {s.config_file_count} config files")
        lines.append(f"")

        bc = self.build_commands
        lines.append(f"## Build & Test Commands")
        for label, cmd in [("Build", bc.build), ("Test", bc.test),
                           ("Lint", bc.lint), ("Typecheck", bc.typecheck)]:
            if cmd:
                lines.append(f"- `{label}`: `{cmd}`")
        if self.test_commands:
            lines.append(f"- Test commands found: {len(self.test_commands)}")
        lines.append(f"")

        if self.risky_files:
            lines.append(f"## Risky Files ({len(self.risky_files)})")
            for f in self.risky_files[:10]:
                reasons = "; ".join(f.reasons[:3])
                lines.append(f"- `{f.path}` (score: {f.risk_score:.2f}) — {reasons}")
            lines.append(f"")

        if self.architectural_hotspots:
            lines.append(f"## Architectural Hotspots ({len(self.architectural_hotspots)})")
            for h in self.architectural_hotspots:
                lines.append(f"- {h.subsystem}: {h.description} (risk: {h.risk_score:.2f})")
            lines.append(f"")

        if self.circular_dependencies:
            lines.append(f"## Circular Dependencies ({len(self.circular_dependencies)})")
            for c in self.circular_dependencies:
                cycle_str = " -> ".join(c.cycle[:5])
                lines.append(f"- [{c.severity}] {cycle_str}")
            lines.append(f"")

        if self.stale_areas:
            lines.append(f"## Stale Areas ({len(self.stale_areas)})")
            for s in self.stale_areas:
                lines.append(f"- `{s.path}` ({s.last_modified_days} days, {s.risk_of_decay})")
            lines.append(f"")

        if self.missing_documentation:
            lines.append(f"## Documentation Gaps ({len(self.missing_documentation)})")
            for m in self.missing_documentation:
                lines.append(f"- [{m.severity}] `{m.path}` — {m.suggestion}")
            lines.append(f"")

        if self.suggested_improvements:
            lines.append(f"## Suggested Improvements")
            for imp in self.suggested_improvements[:5]:
                lines.append(f"- [{imp.priority}] {imp.description} ({imp.effort})")
            lines.append(f"")

        lines.append(f"## Research Diagnostics")
        r = self.research
        lines.append(f"- Graph quality: {r.graph_quality_score:.2f}")
        lines.append(f"- Graph completeness: {r.graph_completeness:.2f}")
        lines.append(f"- Inferred invariants: {r.inferred_invariants_count}")
        lines.append(f"- Likely failure zones: {len(r.likely_failure_zones)}")
        lines.append(f"- Missing evidence: {len(r.missing_evidence)} items")
        lines.append(f"")

        return "\n".join(lines)


class RepoDoctor:
    """Diagnose a repository. Product + Research in one pass."""

    def __init__(self):
        self._git_available = False

    def diagnose(self, repo_path: Path) -> RepoDiagnosis:
        repo_path = Path(repo_path).resolve()
        diagnosis = RepoDiagnosis(
            repo_path=str(repo_path),
            repo_name=repo_path.name,
        )

        self._check_git(repo_path)
        structure = self._analyze_structure(repo_path)
        diagnosis.project_structure = structure
        diagnosis.build_commands = self._detect_build_commands(repo_path, structure)
        diagnosis.test_commands = self._detect_test_commands(repo_path, structure)
        diagnosis.risky_files = self._find_risky_files(repo_path, structure)
        diagnosis.architectural_hotspots = self._find_hotspots(repo_path, structure, diagnosis.risky_files)
        diagnosis.circular_dependencies = self._find_circular_deps(repo_path, structure)
        diagnosis.stale_areas = self._find_stale_areas(repo_path)
        diagnosis.missing_documentation = self._find_missing_docs(repo_path, structure)
        diagnosis.onboarding_path = self._infer_onboarding_path(repo_path, structure)
        diagnosis.suggested_improvements = self._suggest_improvements(diagnosis)
        diagnosis.research = self._collect_research_data(repo_path, structure, diagnosis)
        diagnosis.diagnosis_confidence = self._compute_confidence(diagnosis)

        return diagnosis

    def _check_git(self, repo_path: Path):
        git_dir = repo_path / ".git"
        self._git_available = git_dir.is_dir()

    def _analyze_structure(self, repo_path: Path) -> ProjectStructure:
        s = ProjectStructure()
        all_files = list(repo_path.rglob("*"))
        all_dirs = [d for d in all_files if d.is_dir()]
        all_files_only = [f for f in all_files if f.is_file()]

        for d in all_dirs:
            if d.parent == repo_path and d.name != ".git":
                s.top_level_dirs.append(d.name)

        s.file_count = len(all_files_only)
        s.dir_count = len(all_dirs)

        total_lines = 0
        for f in all_files_only:
            try:
                with open(f, "rb") as fh:
                    total_lines += sum(1 for _ in fh)
            except Exception:
                pass
        s.total_lines = total_lines

        ext_map: Dict[str, int] = {}
        for f in all_files_only:
            ext = f.suffix.lower()
            if ext:
                ext_map[ext] = ext_map.get(ext, 0) + 1

            name = f.name.lower()
            if name == "readme.md":
                s.has_readme = True
            if name in ("license", "license.md", "license.txt", "copying"):
                s.has_license = True

        s.language = self._detect_language(ext_map)
        s.framework = self._detect_framework(repo_path, s.language)
        s.build_system = self._detect_build_system(repo_path)
        s.source_dirs = self._find_source_dirs(repo_path)

        test_files = [f for f in all_files_only if self._is_test_file(f)]
        s.test_file_count = len(test_files)
        s.has_tests = s.test_file_count > 0

        doc_files = [f for f in all_files_only if self._is_doc_file(f)]
        s.doc_file_count = len(doc_files)
        s.has_docs = s.doc_file_count > 0

        config_files = [f for f in all_files_only if self._is_config_file(f)]
        s.config_file_count = len(config_files)

        s.has_ci = self._detect_ci(repo_path)

        return s

    def _detect_language(self, ext_map: Dict[str, int]) -> str:
        lang_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".tsx": "TypeScript", ".jsx": "JavaScript", ".go": "Go",
            ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
            ".c": "C", ".cpp": "C++", ".h": "C/C++", ".hpp": "C++",
            ".cs": "C#", ".swift": "Swift", ".kt": "Kotlin",
            ".scala": "Scala", ".r": "R", ".m": "Objective-C",
            ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML",
            ".toml": "TOML", ".json": "JSON", ".md": "Markdown",
            ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
        }
        best_lang = "Unknown"
        best_count = 0
        for ext, count in ext_map.items():
            lang = lang_map.get(ext)
            if lang and count > best_count:
                best_lang = lang
                best_count = count
        return best_lang

    def _detect_framework(self, repo_path: Path, language: str) -> str:
        indicators = {
            "django": ["manage.py", "settings.py", "urls.py", "wsgi.py"],
            "flask": ["app.py", "application.py", "flask"],
            "fastapi": ["fastapi", "main.py"],
            "react": ["package.json", "node_modules/react"],
            "next.js": ["next.config.js", "next.config.ts"],
            "express": ["express", "app.js"],
            "spring": ["pom.xml", "build.gradle", "application.java"],
            "rails": ["Gemfile", "config/routes.rb", "app/controllers"],
            "gin": ["gin", "go.mod"],
            "axum": ["axum", "Cargo.toml"],
        }
        for framework, hints in indicators.items():
            for hint in hints:
                if hint.endswith(".py") or hint.endswith(".js") or hint.endswith(".ts") or hint.endswith(".java") or hint.endswith(".rb"):
                    if (repo_path / hint).exists():
                        return framework
                else:
                    if any(f.name == hint or hint in f.name for f in repo_path.rglob("*") if f.is_file()):
                        return framework
        return language

    def _detect_build_system(self, repo_path: Path) -> str:
        markers = [
            ("pyproject.toml", "setuptools/poetry"),
            ("setup.py", "setuptools"),
            ("setup.cfg", "setuptools"),
            ("Cargo.toml", "cargo"),
            ("go.mod", "go modules"),
            ("package.json", "npm/yarn"),
            ("Makefile", "make"),
            ("CMakeLists.txt", "cmake"),
            ("pom.xml", "maven"),
            ("build.gradle", "gradle"),
            ("Gemfile", "bundler"),
            ("Cask", "emacs"),
            ("stack.yaml", "stack"),
            ("mix.exs", "mix"),
            ("rebar.config", "rebar3"),
            ("dune-project", "dune"),
        ]
        for marker, system in markers:
            if (repo_path / marker).exists():
                return system
        return "unknown"

    def _find_source_dirs(self, repo_path: Path) -> List[str]:
        source_indicators = ["src", "lib", "app", "source", "packages", "module"]
        found = []
        for d in repo_path.iterdir():
            if d.is_dir() and d.name in source_indicators and not d.name.startswith("."):
                found.append(d.name)
        return found

    def _is_test_file(self, path: Path) -> bool:
        name = path.name.lower()
        return name.startswith("test_") or name.startswith("test-") or \
               name.endswith("_test.py") or name.endswith("_test.rs") or \
               name.endswith("_test.go") or name.endswith(".spec.js") or \
               name.endswith(".spec.ts") or name.endswith(".test.js") or \
               name.endswith(".test.ts") or "test" in path.parts

    def _is_doc_file(self, path: Path) -> bool:
        name = path.name.lower()
        return name.endswith(".md") or name.endswith(".rst") or \
               name.endswith(".txt") or "doc" in path.parts or \
               "docs" in path.parts

    def _is_config_file(self, path: Path) -> bool:
        name = path.name.lower()
        config_names = [
            "package.json", "pyproject.toml", "setup.py", "setup.cfg",
            "cargo.toml", "go.mod", "makefile", "cmakelists.txt",
            "pom.xml", "build.gradle", "gemfile", "dockerfile",
            "docker-compose.yml", ".env.example", "pre-commit-config.yaml",
            ".flake8", ".pylintrc", ".editorconfig", ".gitignore",
            "tsconfig.json", "webpack.config.js", "vite.config.ts",
            "jest.config.js", ".eslintrc.js", ".prettierrc",
        ]
        return name in config_names or name.endswith(".cfg") or \
               name.endswith(".ini") or name.endswith(".conf")

    def _detect_ci(self, repo_path: Path) -> bool:
        ci_indicators = [
            ".github/workflows", ".circleci", ".gitlab-ci.yml",
            ".travis.yml", "jenkinsfile", ".drone.yml",
        ]
        for indicator in ci_indicators:
            if (repo_path / indicator).exists():
                return True
        return False

    def _detect_build_commands(self, repo_path: Path,
                               structure: ProjectStructure) -> BuildCommands:
        bc = BuildCommands()
        markers = {
            "pyproject.toml": lambda f: self._parse_pyproject_toml(f),
            "setup.py": lambda f: {"build": "python setup.py build", "test": "python setup.py test"},
            "Cargo.toml": lambda f: {"build": "cargo build", "test": "cargo test", "lint": "cargo clippy"},
            "package.json": lambda f: self._parse_package_json(f),
            "go.mod": lambda f: {"build": "go build ./...", "test": "go test ./..."},
            "Makefile": lambda f: self._parse_makefile(f),
        }
        for marker, parser in markers.items():
            marker_path = repo_path / marker
            if marker_path.exists():
                try:
                    result = parser(marker_path)
                    if result:
                        bc.build = result.get("build", bc.build)
                        bc.test = result.get("test", bc.test)
                        bc.lint = result.get("lint", bc.lint)
                        bc.typecheck = result.get("typecheck", bc.typecheck)
                        bc.dev = result.get("dev", bc.dev)
                except Exception:
                    pass
        return bc

    def _parse_pyproject_toml(self, path: Path) -> dict:
        try:
            content = path.read_text()
            commands = {}
            # Detect poetry
            if '[tool.poetry]' in content:
                commands["build"] = "poetry build"
                commands["test"] = "poetry run pytest"
            # Detect hatch
            if '[build-system]' in content and 'hatchling' in content:
                commands["build"] = "hatch build"
                commands["test"] = "hatch run pytest"
            # Common scripts
            if '[tool.taskipy.tasks]' in content:
                pass
            if '[tool.pytest.ini_options]' in content:
                commands["test"] = "pytest"
            return commands
        except Exception:
            return {}

    def _parse_package_json(self, path: Path) -> dict:
        try:
            import json
            data = json.loads(path.read_text())
            scripts = data.get("scripts", {})
            commands = {}
            if "build" in scripts:
                commands["build"] = f"npm run build"
            if "test" in scripts:
                commands["test"] = f"npm test"
            if "lint" in scripts:
                commands["lint"] = f"npm run lint"
            if "dev" in scripts:
                commands["dev"] = f"npm run dev"
            if "typecheck" in scripts or "type-check" in scripts:
                commands["typecheck"] = f"npm run typecheck"
            return commands
        except Exception:
            return {}

    def _parse_makefile(self, path: Path) -> dict:
        try:
            content = path.read_text()
            commands = {}
            if re.search(r'^build:', content, re.MULTILINE):
                commands["build"] = "make build"
            if re.search(r'^test:', content, re.MULTILINE):
                commands["test"] = "make test"
            if re.search(r'^lint:', content, re.MULTILINE):
                commands["lint"] = "make lint"
            if re.search(r'^dev:', content, re.MULTILINE):
                commands["dev"] = "make dev"
            return commands
        except Exception:
            return {}

    def _detect_test_commands(self, repo_path: Path,
                               structure: ProjectStructure) -> List[str]:
        commands = []
        markers_tests = [
            ("pyproject.toml", ["pytest", "pytest tests/"]),
            ("setup.cfg", ["pytest"]),
            ("pytest.ini", ["pytest"]),
            ("package.json", ["npm test"]),
            ("Cargo.toml", ["cargo test"]),
            ("go.mod", ["go test ./..."]),
            ("Gemfile", ["bundle exec rspec"]),
            ("build.gradle", ["./gradlew test"]),
            ("pom.xml", ["mvn test"]),
        ]
        for marker, cmds in markers_tests:
            if (repo_path / marker).exists():
                commands.extend(cmds)
                break
        if not commands and structure.has_tests:
            commands.append("pytest")
        return commands

    def _find_risky_files(self, repo_path: Path,
                          structure: ProjectStructure) -> List[RiskyFile]:
        risky = []
        large_files = []

        for f in sorted(repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            try:
                lines = sum(1 for _ in open(f, "rb"))
            except Exception:
                continue

            ext = f.suffix.lower()
            name = f.name.lower()
            reasons = []
            risk = 0.0
            complexity = 0.0

            if lines > 500:
                reasons.append(f"Large file ({lines} lines)")
                risk += 0.3
                complexity = min(1.0, lines / 2000)

            if lines > 1000:
                reasons.append(f"Very large file ({lines} lines, high complexity)")
                risk += 0.2

            if ext in (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"):
                try:
                    content = f.read_text(errors="ignore")
                    import_count = content.count("import ") + content.count("from ")
                    if import_count > 30:
                        reasons.append(f"High dependency count ({import_count} imports)")
                        risk += 0.2
                    if "TODO" in content or "FIXME" in content or "HACK" in content:
                        reasons.append("Contains TODO/FIXME/HACK markers")
                        risk += 0.1
                    if "pass" in content and ext == ".py":
                        pass_count = content.count("pass")
                        if pass_count > 5:
                            reasons.append(f"Unimplemented stubs ({pass_count} pass statements)")
                            risk += 0.1
                    if "except:" in content or "except Exception:" in content:
                        reasons.append("Bare except clauses")
                        risk += 0.15
                    if "eval(" in content or "exec(" in content:
                        reasons.append("Uses eval/exec (security risk)")
                        risk += 0.3
                    if "subprocess." in content or "os.system" in content:
                        reasons.append("Subprocess/shell execution")
                        risk += 0.1
                    if "password" in content.lower() or "secret" in content.lower() or "api_key" in content.lower():
                        reasons.append("May contain secrets/credentials")
                        risk += 0.3
                    complexity = min(1.0, (import_count / 50) + (lines / 2000))
                except Exception:
                    pass

            if risk > 0:
                risky.append(RiskyFile(
                    path=str(f.relative_to(repo_path)),
                    risk_score=round(risk, 2),
                    reasons=reasons,
                    complexity=round(complexity, 2),
                    lines=lines,
                ))

        risky.sort(key=lambda x: x.risk_score, reverse=True)
        return risky[:30]

    def _find_hotspots(self, repo_path: Path, structure: ProjectStructure,
                       risky_files: List[RiskyFile]) -> List[ArchitecturalHotspot]:
        hotspots = {}
        for rf in risky_files:
            parts = Path(rf.path).parts
            subsystem = parts[0] if len(parts) > 1 else "root"
            if subsystem not in hotspots:
                hotspots[subsystem] = {"files": [], "total_risk": 0.0, "total_complexity": 0.0}
            hotspots[subsystem]["files"].append(rf.path)
            hotspots[subsystem]["total_risk"] += rf.risk_score
            hotspots[subsystem]["total_complexity"] += rf.complexity

        results = []
        i = 0
        for subsystem, data in sorted(hotspots.items(), key=lambda x: x[1]["total_risk"], reverse=True):
            i += 1
            if i > 10:
                break
            results.append(ArchitecturalHotspot(
                subsystem=subsystem,
                risk_score=round(data["total_risk"], 2),
                file_count=len(data["files"]),
                total_complexity=round(data["total_complexity"], 2),
                coupling_count=len(data["files"]),
                description=f"High risk concentration in {subsystem} ({len(data['files'])} files)",
                files=data["files"],
            ))
        return results

    def _find_circular_deps(self, repo_path: Path,
                            structure: ProjectStructure) -> List[CircularDependency]:
        if structure.language not in ("Python", "TypeScript", "JavaScript"):
            return []

        import_graph: Dict[str, List[str]] = {}
        for f in sorted(repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            ext = f.suffix.lower()
            if ext not in (".py", ".js", ".ts"):
                continue
            try:
                content = f.read_text(errors="ignore")
                rel_path = str(f.relative_to(repo_path))
                imports = []
                if ext == ".py":
                    for line in content.split("\n"):
                        m = re.match(r'^\s*(?:from|import)\s+(\S+)', line)
                        if m:
                            imports.append(m.group(1).split(".")[0])
                else:
                    for m in re.finditer(r'(?:import|require)\s+["\']([^"\']+)["\']', content):
                        imports.append(m.group(1).split("/")[0])
                import_graph[rel_path] = imports
            except Exception:
                continue

        cycles = []
        visited = set()
        path_stack = []

        def dfs(node: str, path: List[str]):
            if node in path_stack:
                cycle_start = path_stack.index(node)
                cycle = path_stack[cycle_start:] + [node]
                if len(cycle) >= 3:
                    cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            path_stack.append(node)
            for dep in import_graph.get(node, []):
                dfs(dep, path)
            path_stack.pop()

        for node in import_graph:
            dfs(node, [])

        results = []
        seen_cycles = set()
        for cycle in cycles:
            cycle_key = " -> ".join(sorted(set(cycle)))
            if cycle_key not in seen_cycles:
                seen_cycles.add(cycle_key)
                results.append(CircularDependency(
                    cycle=cycle,
                    length=len(cycle),
                    severity="high" if len(cycle) <= 4 else "medium",
                    files_involved=list(set(cycle)),
                ))

        results.sort(key=lambda x: x.length)
        return results[:10]

    def _find_stale_areas(self, repo_path: Path) -> List[StaleArea]:
        if not self._git_available:
            return []
        try:
            result = subprocess.run(
                ["git", "log", "--name-only", "--pretty=format:", "-50"],
                capture_output=True, text=True, cwd=repo_path, timeout=10,
            )
            recently_changed = set()
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    recently_changed.add(line)

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)

            stale = []
            for f in sorted(repo_path.rglob("*")):
                if not f.is_file() or ".git" in f.parts:
                    continue
                rel = str(f.relative_to(repo_path))
                if rel not in recently_changed and recently_changed:
                    try:
                        mtime = os.path.getmtime(f)
                        days_ago = (now.timestamp() - mtime) / 86400
                        if days_ago > 180:
                            stale.append(StaleArea(
                                path=rel,
                                last_modified_days=int(days_ago),
                                file_count=1,
                                risk_of_decay="high" if days_ago > 365 else "medium",
                                reason=f"Not modified in {int(days_ago)} days, not in recent history",
                            ))
                    except Exception:
                        continue

            stale.sort(key=lambda x: x.last_modified_days, reverse=True)
            return stale[:10]
        except Exception:
            return []

    def _find_missing_docs(self, repo_path: Path,
                           structure: ProjectStructure) -> List[MissingDocumentation]:
        missing = []

        if not structure.has_readme:
            missing.append(MissingDocumentation(
                path=str(repo_path),
                type="readme",
                severity="high",
                suggestion="Add a README.md describing project purpose, setup, and usage",
            ))

        if not structure.has_license:
            missing.append(MissingDocumentation(
                path=str(repo_path),
                type="license",
                severity="medium",
                suggestion="Add a LICENSE file to clarify usage rights",
            ))

        for src_dir in structure.source_dirs:
            src_path = repo_path / src_dir
            if src_path.is_dir():
                modules_without_docs = 0
                for py_file in sorted(src_path.rglob("*.py")):
                    if py_file.name == "__init__.py":
                        continue
                    rel = str(py_file.relative_to(repo_path))
                    try:
                        content = py_file.read_text(errors="ignore")
                        if not content.strip().startswith('"""') and '"""' not in content[:200]:
                            if not content.strip().startswith("'''"):
                                modules_without_docs += 1
                                if modules_without_docs <= 5:
                                    missing.append(MissingDocumentation(
                                        path=rel,
                                        type="module_docstring",
                                        severity="low",
                                        suggestion="Add module-level docstring",
                                    ))
                    except Exception:
                        continue

                if modules_without_docs > 5:
                    missing.append(MissingDocumentation(
                        path=src_dir,
                        type="module_docstrings",
                        severity="medium",
                        suggestion=f"{modules_without_docs} modules missing docstrings in {src_dir}",
                    ))

        return missing[:15]

    def _infer_onboarding_path(self, repo_path: Path,
                               structure: ProjectStructure) -> OnboardingPath:
        op = OnboardingPath()

        entry_candidates = [
            "README.md", "CONTRIBUTING.md", "docs/", "examples/",
            "main.py", "app.py", "cli.py", "index.js", "index.ts",
            "src/", "lib/", "bin/",
        ]
        for candidate in entry_candidates:
            path = repo_path / candidate
            if path.exists():
                op.entry_points.append(candidate)

        op.recommended_order = [
            "README.md",
            "CONTRIBUTING.md",
        ]
        if structure.has_tests:
            op.recommended_order.append("test files (understand expected behavior)")
        if structure.source_dirs:
            op.recommended_order.append(f"source code in {', '.join(structure.source_dirs)}")
        if structure.has_docs:
            op.recommended_order.append("documentation")

        op.key_concepts = [structure.language, structure.build_system]
        if structure.framework != structure.language:
            op.key_concepts.append(structure.framework)

        if structure.file_count < 50:
            op.estimated_ramp_up = "minutes"
        elif structure.file_count < 200:
            op.estimated_ramp_up = "hours"
        elif structure.file_count < 1000:
            op.estimated_ramp_up = "days"
        else:
            op.estimated_ramp_up = "weeks"

        return op

    def _suggest_improvements(self, diagnosis: RepoDiagnosis) -> List[SuggestedImprovement]:
        suggestions = []

        d = diagnosis
        if d.missing_documentation:
            high_docs = [m for m in d.missing_documentation if m.severity == "high"]
            if high_docs:
                suggestions.append(SuggestedImprovement(
                    category="documentation",
                    priority="high",
                    description=f"Add missing documentation: {', '.join(m.type for m in high_docs[:3])}",
                    effort="small",
                    impact="high",
                ))

        if d.circular_dependencies:
            suggestions.append(SuggestedImprovement(
                category="architecture",
                priority="high",
                description=f"Resolve {len(d.circular_dependencies)} circular dependencies "
                           f"to improve modularity",
                effort="medium",
                impact="high",
            ))

        hotspots = [h for h in d.architectural_hotspots if h.risk_score > 1.0]
        if hotspots:
            suggestions.append(SuggestedImprovement(
                category="architecture",
                priority="medium",
                description=f"Refactor {len(hotspots)} high-risk subsystems: "
                           f"{', '.join(h.subsystem for h in hotspots[:3])}",
                effort="large",
                impact="high",
            ))

        if d.stale_areas:
            high_stale = [s for s in d.stale_areas if s.risk_of_decay == "high"]
            if high_stale:
                suggestions.append(SuggestedImprovement(
                    category="maintenance",
                    priority="medium",
                    description=f"Review {len(high_stale)} stale files not modified in 180+ days",
                    effort="small",
                    impact="medium",
                ))

        if d.build_commands.test is None:
            suggestions.append(SuggestedImprovement(
                category="testing",
                priority="high",
                description="Set up test framework and add test commands",
                effort="medium",
                impact="high",
            ))

        return suggestions

    def _collect_research_data(self, repo_path: Path,
                                structure: ProjectStructure,
                                diagnosis: RepoDiagnosis) -> ResearchDiagnostics:
        r = ResearchDiagnostics()

        graph_factor = 1.0
        if not self._git_available:
            graph_factor -= 0.3
        if not structure.has_tests:
            graph_factor -= 0.15
        if not structure.has_readme:
            graph_factor -= 0.1
        if not structure.has_ci:
            graph_factor -= 0.1
        r.graph_quality_score = round(max(0.0, graph_factor), 2)

        total_files = max(structure.file_count, 1)
        analyzed = len(diagnosis.risky_files)
        docs_covered = max(structure.doc_file_count, 1)
        r.graph_completeness = round(
            min(1.0, (analyzed + structure.test_file_count + docs_covered) / total_files), 2
        )

        if self._git_available:
            try:
                result = subprocess.run(
                    ["git", "log", "--oneline", "-1"],
                    capture_output=True, text=True, cwd=repo_path, timeout=5,
                )
                r.missing_evidence.append("git history depth (only recent commits sampled)")
            except Exception:
                r.missing_evidence.append("git history unavailable")
        else:
            r.missing_evidence.append("git history unavailable")

        if not structure.has_tests:
            r.missing_evidence.append("no test suite to validate correctness")
        if not structure.has_ci:
            r.missing_evidence.append("no CI pipeline to verify build")
        if structure.file_count > 200:
            r.missing_evidence.append("large repository — only sampled top risks")

        r.confidence_scores = {
            "structure": 0.95,
            "build_commands": 0.7 if diagnosis.build_commands.build else 0.3,
            "risky_files": 0.6,
            "circular_deps": 0.5 if diagnosis.circular_dependencies else 0.8,
            "stale_areas": 0.5 if self._git_available else 0.0,
            "onboarding": 0.7,
        }

        r.uncertainty_estimates = {
            "language_detection": 0.1,
            "framework_detection": 0.3,
            "risk_scoring": 0.4,
            "hotspot_identification": 0.35,
            "circular_dependency_detection": 0.4,
        }

        r.inferred_invariants_count = len(diagnosis.risky_files) + len(diagnosis.circular_dependencies)
        r.invariant_hypotheses = []
        if diagnosis.circular_dependencies:
            r.invariant_hypotheses.append({
                "type": "no_cycles",
                "description": "Modules should not have circular dependencies",
                "confidence": 0.6,
                "evidence": f"{len(diagnosis.circular_dependencies)} cycles found",
            })
        if diagnosis.risky_files:
            large_count = len([f for f in diagnosis.risky_files if f.lines > 500])
            if large_count > 0:
                r.invariant_hypotheses.append({
                    "type": "file_size_limit",
                    "description": "Files should not exceed 500 lines",
                    "confidence": 0.5,
                    "evidence": f"{large_count} files exceed limit",
                })

        r.likely_failure_zones = []
        for hotspot in diagnosis.architectural_hotspots[:5]:
            if hotspot.risk_score > 1.0:
                r.likely_failure_zones.append(
                    f"{hotspot.subsystem} (risk: {hotspot.risk_score:.2f}, "
                    f"{hotspot.file_count} files)"
                )

        return r

    def _compute_confidence(self, diagnosis: RepoDiagnosis) -> float:
        factors = [
            0.2 if diagnosis.project_structure.file_count > 0 else 0.0,
            0.15 if self._git_available else 0.0,
            0.15 if diagnosis.build_commands.build else 0.05,
            0.1 if diagnosis.project_structure.has_tests else 0.0,
            0.1 if diagnosis.project_structure.has_readme else 0.0,
            0.1 if diagnosis.risky_files else 0.0,
            0.1 if diagnosis.circular_dependencies else 0.0,
            0.1 if diagnosis.stale_areas else 0.0,
        ]
        return round(min(1.0, sum(factors)), 2)
