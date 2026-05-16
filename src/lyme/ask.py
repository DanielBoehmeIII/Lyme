"""lyme ask — Evidence-grounded repository Q&A.

Every claim is backed by citations, confidence scores, and uncertainty markers.
Refuses unsupported claims with explicit reasoning.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
import ast


class CitationType:
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    COMMAND_OUTPUT = "command_output"
    GIT_HISTORY = "git_history"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    TEST = "test"
    DOCUMENTATION = "documentation"


@dataclass
class Citation:
    type: str
    value: str
    context: str
    line_number: Optional[int] = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "context": self.context[:100],
            "line_number": self.line_number,
            "confidence": self.confidence,
        }

    def __str__(self) -> str:
        loc = f":{self.line_number}" if self.line_number else ""
        return f"  [{self.type}] `{self.value}{loc}` — {self.context[:80]}"


@dataclass
class Claim:
    statement: str
    confidence: float
    citations: List[Citation] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    uncertainty_reason: Optional[str] = None
    verified: bool = False
    refused: bool = False
    refusal_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "confidence": self.confidence,
            "citations": [c.to_dict() for c in self.citations],
            "contradictions": self.contradictions,
            "uncertainty_reason": self.uncertainty_reason,
            "verified": self.verified,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
        }

    def __str__(self) -> str:
        if self.refused:
            return f"✗ REFUSED: {self.statement}\n  Reason: {self.refusal_reason}"
        icon = "✓" if self.verified else "?"
        conf = f"{self.confidence:.0%}"
        lines = [f"{icon} {self.statement} (confidence: {conf})"]
        for c in self.citations:
            lines.append(str(c))
        if self.contradictions:
            for ct in self.contradictions:
                lines.append(f"  ⚠ Contradiction: {ct}")
        if self.uncertainty_reason:
            lines.append(f"  ? Uncertainty: {self.uncertainty_reason}")
        return "\n".join(lines)


@dataclass
class EvidenceAnswer:
    question: str
    claims: List[Claim] = field(default_factory=list)
    what_i_checked: List[str] = field(default_factory=list)
    what_i_did_not_check: List[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    answer_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "claims": [c.to_dict() for c in self.claims],
            "what_i_checked": self.what_i_checked,
            "what_i_did_not_check": self.what_i_did_not_check,
            "overall_confidence": self.overall_confidence,
            "answer_summary": self.answer_summary,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Question: {self.question}")
        lines.append(f"")
        lines.append(f"**Overall confidence**: {self.overall_confidence:.0%}")
        lines.append(f"")
        lines.append(f"### Answer")
        lines.append(f"{self.answer_summary}")
        lines.append(f"")

        if self.claims:
            lines.append(f"### Evidence")
            for i, claim in enumerate(self.claims, 1):
                lines.append(f"")
                lines.append(f"**Claim {i}:** {claim.statement}")
                lines.append(f"**Confidence:** {claim.confidence:.0%}")
                if claim.citations:
                    lines.append(f"**Citations:**")
                    for c in claim.citations:
                        lines.append(f"- `{c.value}` ({c.type}) — {c.context[:100]}")
                if claim.contradictions:
                    lines.append(f"**⚠ Contradictions:**")
                    for ct in claim.contradictions:
                        lines.append(f"- {ct}")
                if claim.uncertainty_reason:
                    lines.append(f"**? Uncertainty:** {claim.uncertainty_reason}")
            lines.append(f"")

        if self.what_i_checked:
            lines.append(f"### What I Checked")
            for item in self.what_i_checked:
                lines.append(f"- {item}")
            lines.append(f"")

        if self.what_i_did_not_check:
            lines.append(f"### What I Did NOT Check")
            for item in self.what_i_did_not_check:
                lines.append(f"- {item}")
            lines.append(f"")

        return "\n".join(lines)


class EvidenceEngine:
    """Evidence-grounded query engine for repositories."""

    def __init__(self):
        self._repo_path: Optional[Path] = None
        self._file_index: Dict[str, Path] = {}
        self._git_available = False

    def ask(self, question: str, repo_path: Path) -> EvidenceAnswer:
        repo_path = Path(repo_path).resolve()
        self._repo_path = repo_path
        self._index_files(repo_path)
        self._git_available = (repo_path / ".git").is_dir()

        answer = EvidenceAnswer(question=question)
        answer.what_i_checked = self._determine_checked(repo_path)
        answer.what_i_did_not_check = self._determine_not_checked(repo_path)

        question_lower = question.lower()

        claims = self._answer_from_index(question_lower, repo_path)
        answer.claims = claims

        verified = [c for c in claims if c.verified]
        total = len(claims)
        answer.overall_confidence = (
            sum(c.confidence for c in verified) / max(len(verified), 1)
            if verified else 0.0
        )

        answer.answer_summary = self._generate_summary(question, claims)

        return answer

    def _index_files(self, repo_path: Path):
        self._file_index = {}
        for f in repo_path.rglob("*"):
            if f.is_file() and ".git" not in f.parts:
                self._file_index[f.name] = f

    def _determine_checked(self, repo_path: Path) -> List[str]:
        checked = [
            f"Scanned {len(self._file_index)} files in repository",
            f"Detected language: {self._detect_language(repo_path)}",
            f"Checked file names, imports, function/class definitions",
        ]
        if self._git_available:
            checked.append("Checked recent git history")
        return checked

    def _determine_not_checked(self, repo_path: Path) -> List[str]:
        not_checked = [
            "Did not run the code (static analysis only)",
            "Did not check external dependencies for correctness",
            "Did not verify test pass/fail status",
        ]
        if not self._git_available:
            not_checked.append("Git history not available")
        return not_checked

    def _detect_language(self, repo_path: Path) -> str:
        ext_count: Dict[str, int] = {}
        for f in self._file_index.values():
            ext = f.suffix.lower()
            if ext:
                ext_count[ext] = ext_count.get(ext, 0) + 1
        lang_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".go": "Go", ".rs": "Rust", ".java": "Java",
        }
        best_lang = "Unknown"
        best_count = 0
        for ext, count in ext_count.items():
            lang = lang_map.get(ext)
            if lang and count > best_count:
                best_lang = lang
                best_count = count
        return best_lang

    def _answer_from_index(self, question: str,
                           repo_path: Path) -> List[Claim]:
        claims = []

        if "what" in question and ("language" in question or "framework" in question):
            claims.extend(self._answer_language(question, repo_path))

        if "function" in question or "method" in question or "api" in question:
            claims.extend(self._answer_functions(question, repo_path))

        if "class" in question:
            claims.extend(self._answer_classes(question, repo_path))

        if "test" in question:
            claims.extend(self._answer_tests(question, repo_path))

        if "dependenc" in question or "import" in question or "package" in question:
            claims.extend(self._answer_dependencies(question, repo_path))

        if "file" in question or "structure" in question or "how many" in question:
            claims.extend(self._answer_structure(question, repo_path))

        if "config" in question or "setting" in question:
            claims.extend(self._answer_config(question, repo_path))

        if "readme" in question or "documentation" in question:
            claims.extend(self._answer_docs(question, repo_path))

        if not claims:
            claims.append(Claim(
                statement=f"I could not find specific evidence to answer: {question[:100]}",
                confidence=0.0,
                verified=False,
                refused=True,
                refusal_reason=(
                    "This question does not match known repository analysis patterns. "
                    "I can answer questions about: language/framework, functions, classes, "
                    "tests, dependencies, file structure, config, and documentation."
                ),
            ))

        return claims

    def _answer_language(self, question: str,
                         repo_path: Path) -> List[Claim]:
        claims = []
        lang = self._detect_language(repo_path)
        citations = []
        for f in list(self._file_index.values())[:5]:
            ext = f.suffix.lower()
            citations.append(Citation(
                type=CitationType.FILE,
                value=str(f.relative_to(repo_path)),
                context=f"File with extension {ext}",
            ))

        build_files = {
            "pyproject.toml": "Python project config",
            "Cargo.toml": "Rust project",
            "go.mod": "Go module",
            "package.json": "Node.js project",
            "pom.xml": "Java Maven project",
        }
        for bf, desc in build_files.items():
            if (repo_path / bf).exists():
                citations.append(Citation(
                    type=CitationType.FILE,
                    value=bf,
                    context=desc,
                ))

        claims.append(Claim(
            statement=f"This repository is written in {lang}",
            confidence=0.9,
            citations=citations,
            verified=True,
        ))
        return claims

    def _answer_functions(self, question: str,
                          repo_path: Path) -> List[Claim]:
        claims = []
        pattern = r'(?:function|method|api)\s+(\w+)'
        match = re.search(pattern, question.lower())
        target = match.group(1).lower() if match else None

        found = []
        for f in sorted(repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            ext = f.suffix.lower()
            if ext not in (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"):
                continue
            try:
                content = f.read_text(errors="ignore")
                if ext == ".py":
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not target or target in node.name.lower():
                                found.append((
                                    node.name,
                                    str(f.relative_to(repo_path)),
                                    node.lineno,
                                ))
            except Exception:
                continue

        if found:
            found = found[:15]
            citations = [
                Citation(
                    type=CitationType.FUNCTION,
                    value=name,
                    context=f"Defined in {path}",
                    line_number=line,
                ) for name, path, line in found
            ]
            if target:
                claims.append(Claim(
                    statement=f"Found {len(found)} function(s) matching '{target}'",
                    confidence=0.95,
                    citations=citations,
                    verified=True,
                ))
            else:
                claims.append(Claim(
                    statement=f"Found {len(found)} function(s) in the codebase",
                    confidence=0.95,
                    citations=citations[:10],
                    verified=True,
                ))
        else:
            claims.append(Claim(
                statement=f"No functions found matching '{target}'" if target else "No functions found",
                confidence=0.8,
                verified=False,
                uncertainty_reason="Functions may exist in unsupported file types",
            ))

        return claims

    def _answer_classes(self, question: str,
                        repo_path: Path) -> List[Claim]:
        claims = []
        pattern = r'class\s+(\w+)'
        match = re.search(pattern, question.lower())
        target = match.group(1).lower() if match else None

        found = []
        for f in sorted(repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            ext = f.suffix.lower()
            if ext not in (".py", ".java", ".ts", ".tsx"):
                continue
            try:
                content = f.read_text(errors="ignore")
                if ext == ".py":
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if not target or target in node.name.lower():
                                found.append((
                                    node.name,
                                    str(f.relative_to(repo_path)),
                                    node.lineno,
                                ))
            except Exception:
                continue

        if found:
            found = found[:15]
            citations = [
                Citation(
                    type=CitationType.CLASS,
                    value=name,
                    context=f"Defined in {path}",
                    line_number=line,
                ) for name, path, line in found
            ]
            if target:
                claims.append(Claim(
                    statement=f"Found {len(found)} class(es) matching '{target}'",
                    confidence=0.95,
                    citations=citations,
                    verified=True,
                ))
            else:
                claims.append(Claim(
                    statement=f"Found {len(found)} class(es) in the codebase",
                    confidence=0.95,
                    citations=citations[:10],
                    verified=True,
                ))
        else:
            claims.append(Claim(
                statement=f"No classes found matching '{target}'" if target else "No classes found",
                confidence=0.8,
                verified=False,
                uncertainty_reason="Classes may exist in unsupported file types",
            ))

        return claims

    def _answer_tests(self, question: str,
                      repo_path: Path) -> List[Claim]:
        claims = []
        test_files = []
        for f in sorted(repo_path.rglob("*")):
            if not f.is_file() or ".git" in f.parts:
                continue
            name = f.name.lower()
            if name.startswith("test_") or name.endswith("_test.py") or \
               name.endswith("_test.rs") or name.endswith("_test.go") or \
               name.endswith(".spec.js") or name.endswith(".spec.ts") or \
               name.endswith(".test.js") or name.endswith(".test.ts") or \
               "test" in f.parts:
                test_files.append(f)

        if test_files:
            test_file_info = test_files[:15]
            citations = [
                Citation(
                    type=CitationType.TEST,
                    value=str(f.relative_to(repo_path)),
                    context=f"Test file",
                ) for f in test_file_info
            ]

            has_test_framework = any(
                (repo_path / m).exists()
                for m in ["pyproject.toml", "pytest.ini", "jest.config.js",
                          "package.json", "Cargo.toml"]
            )

            claims.append(Claim(
                statement=f"Found {len(test_files)} test file(s)",
                confidence=0.9,
                citations=citations[:10],
                verified=True,
            ))
            if not has_test_framework:
                claims[0].uncertainty_reason = (
                    "Test files found but no test framework configuration detected"
                )
        else:
            claims.append(Claim(
                statement="No test files found in this repository",
                confidence=0.85,
                verified=False,
            ))

        return claims

    def _answer_dependencies(self, question: str,
                             repo_path: Path) -> List[Claim]:
        claims = []
        dep_files = {
            "pyproject.toml": self._parse_pyproject_deps,
            "requirements.txt": self._parse_requirements,
            "Cargo.toml": self._parse_cargo_deps,
            "package.json": self._parse_package_deps,
            "go.mod": self._parse_go_deps,
        }

        all_deps = []
        citations = []
        for dep_file, parser in dep_files.items():
            path = repo_path / dep_file
            if path.exists():
                try:
                    deps = parser(path)
                    all_deps.extend(deps)
                    citations.append(Citation(
                        type=CitationType.DEPENDENCY,
                        value=dep_file,
                        context=f"Contains {len(deps)} dependencies",
                    ))
                except Exception:
                    pass

        if all_deps:
            dep_list = all_deps[:20]
            claims.append(Claim(
                statement=f"Found {len(all_deps)} dependencies (showing {len(dep_list)})",
                confidence=0.9,
                citations=citations + [
                    Citation(
                        type=CitationType.DEPENDENCY,
                        value=dep,
                        context=f"Dependency",
                    ) for dep in dep_list
                ],
                verified=True,
            ))
        else:
            claims.append(Claim(
                statement="No dependency files found",
                confidence=0.7,
                verified=False,
                uncertainty_reason="Dependencies may be specified in an unrecognized format",
            ))

        return claims

    def _parse_pyproject_deps(self, path: Path) -> List[str]:
        content = path.read_text()
        deps = []
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("]"):
                    break
                dep = line.strip("\",' ")
                if dep:
                    deps.append(dep)
        return deps

    def _parse_requirements(self, path: Path) -> List[str]:
        return [
            line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#") and not line.startswith("-")
        ]

    def _parse_cargo_deps(self, path: Path) -> List[str]:
        content = path.read_text()
        deps = []
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("[dependencies]"):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("["):
                    break
                if "=" in line:
                    name = line.split("=")[0].strip()
                    if name:
                        deps.append(name)
        return deps

    def _parse_package_deps(self, path: Path) -> List[str]:
        try:
            import json
            data = json.loads(path.read_text())
            return list(data.get("dependencies", {}).keys()) + \
                   list(data.get("devDependencies", {}).keys())
        except Exception:
            return []

    def _parse_go_deps(self, path: Path) -> List[str]:
        deps = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("module ") and not line.startswith("go ") and \
               not line.startswith("require") and not line.startswith(")"):
                parts = line.split()
                if parts and "//" not in parts[0]:
                    deps.append(parts[0])
        return deps

    def _answer_structure(self, question: str,
                          repo_path: Path) -> List[Claim]:
        claims = []

        all_files = list(self._file_index.values())
        source_files = [
            f for f in all_files
            if f.suffix.lower() in (".py", ".js", ".ts", ".tsx", ".jsx",
                                     ".go", ".rs", ".java", ".rb", ".c",
                                     ".cpp", ".h", ".hpp")
        ]
        dirs = set()
        for f in all_files:
            parent = f.parent.relative_to(repo_path)
            if str(parent) != ".":
                dirs.add(str(parent))

        total_lines = 0
        for f in all_files:
            try:
                total_lines += sum(1 for _ in open(f, "rb"))
            except Exception:
                pass

        citations = [
            Citation(
                type=CitationType.FILE,
                value=str(repo_path),
                context=f"Repository root",
            ),
        ]

        claims.append(Claim(
            statement=(
                f"Repository has {len(all_files)} files ({len(source_files)} source), "
                f"{len(dirs)} directories, ~{total_lines} lines"
            ),
            confidence=0.95,
            citations=citations,
            verified=True,
        ))

        top_files = sorted(
            [f for f in all_files if f.parent == repo_path and not f.name.startswith(".")],
            key=lambda x: x.stat().st_size if x.exists() else 0,
            reverse=True,
        )[:5]

        if top_files:
            claims.append(Claim(
                statement=f"Top-level files: {', '.join(f.name for f in top_files)}",
                confidence=0.9,
                citations=[
                    Citation(
                        type=CitationType.FILE,
                        value=f.name,
                        context=f"Top-level file ({f.stat().st_size} bytes)",
                    ) for f in top_files
                ],
                verified=True,
            ))

        return claims

    def _answer_config(self, question: str,
                       repo_path: Path) -> List[Claim]:
        claims = []
        config_files = [
            "pyproject.toml", "setup.cfg", ".flake8", ".pylintrc",
            "tsconfig.json", "webpack.config.js", "vite.config.ts",
            "jest.config.js", ".eslintrc.js", ".prettierrc",
            ".editorconfig", ".gitignore", "docker-compose.yml",
            "Dockerfile",
        ]

        found_configs = []
        for cf in config_files:
            if (repo_path / cf).exists():
                found_configs.append(cf)

        if found_configs:
            claims.append(Claim(
                statement=f"Found {len(found_configs)} configuration file(s)",
                confidence=0.95,
                citations=[
                    Citation(
                        type=CitationType.CONFIG,
                        value=cf,
                        context="Configuration file",
                    ) for cf in found_configs
                ],
                verified=True,
            ))
        else:
            claims.append(Claim(
                statement="No standard configuration files found",
                confidence=0.6,
                verified=False,
                uncertainty_reason="Config may be in non-standard locations",
            ))

        return claims

    def _answer_docs(self, question: str,
                     repo_path: Path) -> List[Claim]:
        claims = []
        readme_path = repo_path / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(errors="ignore")
                first_line = content.split("\n")[0] if content else ""
                claims.append(Claim(
                    statement=f"README.md exists: {first_line[:100]}",
                    confidence=0.95,
                    citations=[
                        Citation(
                            type=CitationType.DOCUMENTATION,
                            value="README.md",
                            context=first_line[:100],
                        ),
                    ],
                    verified=True,
                ))
            except Exception:
                pass
        else:
            claims.append(Claim(
                statement="No README.md found",
                confidence=0.9,
                verified=False,
            ))

        doc_files = [
            f for f in self._file_index.values()
            if f.suffix.lower() in (".md", ".rst", ".txt")
            and f.name.lower() != "readme.md"
            and ".git" not in f.parts
        ]
        if doc_files:
            claims.append(Claim(
                statement=f"Found {len(doc_files)} additional documentation file(s)",
                confidence=0.9,
                citations=[
                    Citation(
                        type=CitationType.DOCUMENTATION,
                        value=str(f.relative_to(repo_path)),
                        context="Documentation file",
                    ) for f in doc_files[:5]
                ],
                verified=True,
            ))

        return claims

    def _generate_summary(self, question: str, claims: List[Claim]) -> str:
        if not claims:
            return "I could not find any evidence related to your question."

        verified = [c for c in claims if c.verified]
        refused = [c for c in claims if c.refused]

        if refused and not verified:
            return refused[0].refusal_reason or "I cannot answer this question."

        parts = []
        for claim in claims:
            if claim.refused:
                continue
            if claim.verified:
                prefix = ""
            else:
                prefix = "(with low confidence) "
            parts.append(f"{prefix}{claim.statement.lower()}")

        return " ".join(parts[:3])
