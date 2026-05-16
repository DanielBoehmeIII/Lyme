from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import hashlib
import re


class FingerprintComponent(str, Enum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    BUILD_SYSTEM = "build_system"
    TEST_FRAMEWORK = "test_framework"
    DEPENDENCIES = "dependencies"
    FILE_STRUCTURE = "file_structure"
    ARCH_PATTERNS = "arch_patterns"
    NAMING_CONVENTIONS = "naming_conventions"
    COMMIT_PATTERNS = "commit_patterns"
    COMPLEXITY_PROFILE = "complexity_profile"
    ERROR_HANDLING = "error_handling"
    TESTING_PATTERN = "testing_pattern"
    CONFIGURATION = "configuration"


@dataclass
class AnonymizedDependency:
    category: str
    role: str
    prevalence: float


@dataclass
class StructuralSignature:
    depth: int
    breadth: int
    file_ratio: Dict[str, float]
    dir_pattern: str


@dataclass
class ComplexityProfile:
    avg_function_length: float
    max_nesting_depth: int
    cyclomatic_summary: Dict[str, float]
    file_size_distribution: Dict[str, int]


@dataclass
class RepoFingerprint:
    repo_id: str
    components: Dict[FingerprintComponent, Dict]
    dependency_signature: List[AnonymizedDependency]
    structural_signature: StructuralSignature
    complexity_profile: ComplexityProfile
    convention_signature: Dict[str, float]
    security_sensitive_ratio: float
    test_to_code_ratio: float
    hash: str

    def to_dict(self) -> Dict:
        return {
            "repo_id": self.repo_id,
            "components": {k.value: v for k, v in self.components.items()},
            "dependency_signature": [d.__dict__ for d in self.dependency_signature],
            "structural_signature": self.structural_signature.__dict__,
            "complexity_profile": self.complexity_profile.__dict__,
            "convention_signature": self.convention_signature,
            "security_sensitive_ratio": self.security_sensitive_ratio,
            "test_to_code_ratio": self.test_to_code_ratio,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> RepoFingerprint:
        components = {}
        for k, v in d.get("components", {}).items():
            try:
                comp = FingerprintComponent(k)
                components[comp] = v
            except ValueError:
                pass
        return cls(
            repo_id=d["repo_id"],
            components=components,
            dependency_signature=[AnonymizedDependency(**dd) for dd in d.get("dependency_signature", [])],
            structural_signature=StructuralSignature(**d.get("structural_signature", {})),
            complexity_profile=ComplexityProfile(**d.get("complexity_profile", {})),
            convention_signature=d.get("convention_signature", {}),
            security_sensitive_ratio=d.get("security_sensitive_ratio", 0.0),
            test_to_code_ratio=d.get("test_to_code_ratio", 0.0),
            hash=d.get("hash", ""),
        )


class RepoFingerprinter:
    def __init__(self, repo_path: Path, anonymize: bool = True):
        self.repo_path = Path(repo_path).resolve()
        self.anonymize = anonymize
        self._salt = hashlib.sha256(str(repo_path).encode()).hexdigest()[:16]

    def fingerprint(self) -> RepoFingerprint:
        components = self._extract_all_components()
        deps = self._anonymize_dependencies(components)
        struct = self._structural_signature()
        complexity = self._complexity_profile()
        conventions = self._naming_conventions()
        sec_ratio = self._security_sensitive_ratio()
        test_ratio = self._test_to_code_ratio()
        fp_hash = self._compute_hash(components, struct, complexity)

        return RepoFingerprint(
            repo_id=self._anonymize_path(),
            components=components,
            dependency_signature=deps,
            structural_signature=struct,
            complexity_profile=complexity,
            convention_signature=conventions,
            security_sensitive_ratio=sec_ratio,
            test_to_code_ratio=test_ratio,
            hash=fp_hash,
        )

    def _anonymize_path(self) -> str:
        raw = str(self.repo_path)
        h = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"repo_{h}"

    def _extract_all_components(self) -> Dict[FingerprintComponent, Dict]:
        components = {}
        components[FingerprintComponent.LANGUAGE] = self._detect_languages()
        components[FingerprintComponent.FRAMEWORK] = self._detect_frameworks()
        components[FingerprintComponent.BUILD_SYSTEM] = self._detect_build_system()
        components[FingerprintComponent.TEST_FRAMEWORK] = self._detect_test_framework()
        components[FingerprintComponent.DEPENDENCIES] = self._detect_dependencies()
        components[FingerprintComponent.FILE_STRUCTURE] = self._file_structure_profile()
        components[FingerprintComponent.ARCH_PATTERNS] = self._detect_arch_patterns()
        components[FingerprintComponent.ERROR_HANDLING] = self._error_handling_profile()
        components[FingerprintComponent.TESTING_PATTERN] = self._testing_pattern_profile()
        components[FingerprintComponent.CONFIGURATION] = self._config_profile()
        return components

    def _detect_languages(self) -> Dict:
        ext_map: Dict[str, int] = {}
        for f in self.repo_path.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                ext = f.suffix.lower()
                if ext:
                    ext_map[ext] = ext_map.get(ext, 0) + 1
        total = sum(ext_map.values()) or 1
        return {ext: count / total for ext, count in sorted(ext_map.items(), key=lambda x: -x[1])}

    def _detect_frameworks(self) -> Dict:
        frameworks: Dict[str, float] = {}
        patterns = {
            "fastapi": ["fastapi", "uvicorn"],
            "flask": ["flask"],
            "django": ["django"],
            "react": ["react", "jsx"],
            "nextjs": ["next"],
            "express": ["express"],
            "spring": ["spring"],
            "actix": ["actix"],
            "axum": ["axum"],
            "rocket": ["rocket"],
        }
        all_text = self._sample_files(20)
        all_text_lower = all_text.lower()
        for framework, keywords in patterns.items():
            score = sum(1 for kw in keywords if kw in all_text_lower) / len(keywords)
            if score > 0:
                frameworks[framework] = score
        return frameworks

    def _detect_build_system(self) -> Dict:
        indicators: Dict[str, float] = {}
        checks = [
            ("pyproject.toml", "python_poetry_or_setuptools"),
            ("setup.py", "python_setuptools"),
            ("setup.cfg", "python_setuptools"),
            ("Pipfile", "python_pipenv"),
            ("Cargo.toml", "rust_cargo"),
            ("package.json", "node_npm"),
            ("yarn.lock", "node_yarn"),
            ("pnpm-lock.yaml", "node_pnpm"),
            ("go.mod", "go_modules"),
            ("Gemfile", "ruby_bundler"),
            ("CMakeLists.txt", "cmake"),
            ("Makefile", "make"),
            ("justfile", "just"),
            ("gradle.build", "gradle"),
            ("pom.xml", "maven"),
            ("build.sbt", "sbt"),
        ]
        for filename, system in checks:
            if (self.repo_path / filename).exists():
                indicators[system] = 1.0
        return indicators

    def _detect_test_framework(self) -> Dict:
        frameworks: Dict[str, float] = {}
        all_text = self._sample_files(30)
        patterns = {
            "pytest": ["pytest", "def test_", "class Test"],
            "unittest": ["unittest", "TestCase"],
            "jest": ["jest", "describe(", "it("],
            "mocha": ["mocha", "describe(", "it("],
            "rspec": ["rspec", "describe ", "it "],
            "go_test": ["func Test", "testing.T"],
            "cargo_test": ["#[test]", "#[cfg(test)]"],
            "junit": ["@Test", "JUnit"],
        }
        for framework, keywords in patterns.items():
            score = sum(1 for kw in keywords if kw in all_text) / len(keywords)
            if score > 0.3:
                frameworks[framework] = score
        return frameworks

    def _detect_dependencies(self) -> Dict:
        deps: Dict[str, List[str]] = {}
        dep_files = {
            "pyproject.toml": self._parse_pyproject,
            "Cargo.toml": self._parse_cargo,
            "package.json": self._parse_package_json,
            "go.mod": self._parse_go_mod,
        }
        for filename, parser in dep_files.items():
            path = self.repo_path / filename
            if path.exists():
                try:
                    result = parser(path)
                    if result:
                        deps[filename] = result
                except Exception:
                    pass
        return deps

    def _parse_pyproject(self, path: Path) -> List[str]:
        text = path.read_text()
        deps = re.findall(r'"(.*?)"', text)
        return [d for d in deps if "=" in d or ">" in d or "<" in d or "~" in d or "^" in d]

    def _parse_cargo(self, path: Path) -> List[str]:
        text = path.read_text()
        deps = re.findall(r'^([a-z][a-z0-9_-]+)\s*=', text, re.MULTILINE)
        return deps

    def _parse_package_json(self, path: Path) -> List[str]:
        try:
            data = json.loads(path.read_text())
            return list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
        except json.JSONDecodeError:
            return []

    def _parse_go_mod(self, path: Path) -> List[str]:
        lines = path.read_text().splitlines()
        deps = []
        for line in lines:
            m = re.match(r'\t([a-z./]+)\s+v', line)
            if m:
                deps.append(m.group(1))
        return deps

    def _file_structure_profile(self) -> Dict:
        dirs: Dict[str, int] = {}
        for d in self.repo_path.rglob("*"):
            if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("__"):
                parts = d.relative_to(self.repo_path).parts
                key = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
                dirs[key] = dirs.get(key, 0) + 1
        total = sum(dirs.values()) or 1
        return {k: v / total for k, v in sorted(dirs.items(), key=lambda x: -x[1])[:30]}

    def _detect_arch_patterns(self) -> Dict:
        patterns: Dict[str, float] = {}
        all_text = self._sample_files(40)
        indicators = {
            "mvc": ["controller", "model", "view", "routes"],
            "layered": ["repository", "service", "handler", "middleware"],
            "hexagonal": ["port", "adapter", "domain", "application"],
            "microservices": ["service", "client", "rpc", "endpoint"],
            "event-driven": ["event", "handler", "subscribe", "emit"],
            "pipeline": ["pipe", "filter", "transform", "stage"],
            "plugin": ["plugin", "extension", "hook", "registry"],
            "repository": ["repository", "dao", "datastore", "crud"],
            "cqrs": ["command", "query", "separate", "mediator"],
            "actor": ["actor", "message", "mailbox", "supervisor"],
        }
        for pattern, keywords in indicators.items():
            score = sum(1 for kw in keywords if kw.lower() in all_text.lower()) / len(keywords)
            if score > 0.2:
                patterns[pattern] = score
        return patterns

    def _naming_conventions(self) -> Dict[str, float]:
        conventions: Dict[str, float] = {
            "snake_case": 0.0,
            "camelCase": 0.0,
            "PascalCase": 0.0,
            "kebab-case": 0.0,
        }
        file_count = 0
        for f in self.repo_path.rglob("*.py"):
            if f.is_file() and f.stat().st_size > 0:
                file_count += 1
                text = f.read_text(errors="ignore")
                snake = len(re.findall(r'\b[a-z]+_[a-z]+\b', text))
                camel = len(re.findall(r'\b[a-z]+[A-Z][a-z]+\b', text))
                pascal = len(re.findall(r'\b[A-Z][a-z]+[A-Z][a-z]+\b', text))
                total = snake + camel + pascal + 1
                conventions["snake_case"] += snake / total
                conventions["camelCase"] += camel / total
                conventions["PascalCase"] += pascal / total
        if file_count:
            for k in conventions:
                conventions[k] /= file_count
        return conventions

    def _error_handling_profile(self) -> Dict:
        profile: Dict[str, float] = {
            "try_except": 0.0,
            "result_type": 0.0,
            "panic": 0.0,
            "optional": 0.0,
            "error_return": 0.0,
        }
        all_text = self._sample_files(30)
        profile["try_except"] = len(re.findall(r'\btry\b|\bexcept\b', all_text)) / max(len(all_text.splitlines()), 1)
        profile["result_type"] = len(re.findall(r'\bResult\b|\bOk\b|\bErr\b', all_text)) / max(len(all_text.splitlines()), 1)
        profile["panic"] = len(re.findall(r'\bpanic\b|\bunwrap\b|\bexpect\b', all_text)) / max(len(all_text.splitlines()), 1)
        profile["optional"] = len(re.findall(r'\bOptional\b|\bMaybe\b|\bNone\b', all_text)) / max(len(all_text.splitlines()), 1)
        profile["error_return"] = len(re.findall(r'\berror\b|\berr\b|\bfail\b', all_text)) / max(len(all_text.splitlines()), 1)
        return profile

    def _testing_pattern_profile(self) -> Dict:
        profile: Dict[str, float] = {
            "unit_test": 0.0,
            "integration_test": 0.0,
            "fixture_heavy": 0.0,
            "mock_heavy": 0.0,
            "parametrized": 0.0,
        }
        all_text = self._sample_files(20, pattern="*test*")
        lines = all_text.splitlines()
        total = len(lines) or 1
        profile["unit_test"] = len(re.findall(r'\bdef test_\b', all_text)) / total
        profile["integration_test"] = len(re.findall(r'\bintegration\b|\be2e\b', all_text)) / total
        profile["fixture_heavy"] = len(re.findall(r'\bfixture\b|\bsetUp\b|\bsetup_method\b', all_text)) / total
        profile["mock_heavy"] = len(re.findall(r'\bmock\b|\bMock\b|\bpatch\b', all_text)) / total
        profile["parametrized"] = len(re.findall(r'\bparametrize\b|\bparameterize\b', all_text)) / total
        return profile

    def _config_profile(self) -> Dict:
        configs: Dict[str, bool] = {}
        for f in self.repo_path.rglob("*"):
            if f.is_file():
                name = f.name.lower()
                if name in (".env", ".env.example", "config.yaml", "config.yml", "config.json",
                            "settings.py", "settings.json", "configuration.py", "config.toml"):
                    configs[name] = True
        return configs

    def _structural_signature(self) -> StructuralSignature:
        dirs = [d for d in self.repo_path.rglob("*") if d.is_dir() and not d.name.startswith(".")]
        depth = max((len(d.relative_to(self.repo_path).parts) for d in dirs), default=0)
        breadth = len([d for d in self.repo_path.iterdir() if d.is_dir() and not d.name.startswith(".")])

        exts: Dict[str, int] = {}
        for f in self.repo_path.rglob("*"):
            if f.is_file() and f.suffix:
                exts[f.suffix] = exts.get(f.suffix, 0) + 1
        total = sum(exts.values()) or 1
        file_ratio = {k: v / total for k, v in sorted(exts.items(), key=lambda x: -x[1])[:10]}

        dirs_by_depth: Dict[int, int] = {}
        for d in dirs:
            dp = len(d.relative_to(self.repo_path).parts)
            dirs_by_depth[dp] = dirs_by_depth.get(dp, 0) + 1

        import json as _j
        return StructuralSignature(
            depth=depth,
            breadth=breadth,
            file_ratio=file_ratio,
            dir_pattern=_j.dumps({str(k): v for k, v in sorted(dirs_by_depth.items())}),
        )

    def _complexity_profile(self) -> ComplexityProfile:
        func_lengths: List[int] = []
        max_nesting = 0

        for f in self.repo_path.rglob("*.py"):
            if f.is_file() and f.stat().st_size > 0:
                text = f.read_text(errors="ignore")
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if re.match(r'^\s*def \w+', line):
                        block = 0
                        for j in range(i + 1, min(i + 200, len(lines))):
                            if lines[j].strip() and not lines[j].startswith(" ") and not lines[j].startswith("\t"):
                                break
                            block += 1
                        func_lengths.append(block)

                nesting = 0
                max_nest = 0
                for line in lines:
                    nesting += line.count("    ") + line.count("\t")
                    nesting -= line.count("    return") + line.count("\treturn")
                    max_nest = max(max_nest, nesting)
                max_nesting = max(max_nesting, max_nest)

        avg_len = sum(func_lengths) / len(func_lengths) if func_lengths else 0.0

        sizes: Dict[str, int] = {"<50": 0, "50-200": 0, "200-500": 0, "500-2000": 0, ">2000": 0}
        for f in self.repo_path.rglob("*"):
            if f.is_file() and f.stat().st_size > 0:
                s = f.stat().st_size
                if s < 50 * 1024:
                    sizes["<50"] += 1
                elif s < 200 * 1024:
                    sizes["50-200"] += 1
                elif s < 500 * 1024:
                    sizes["200-500"] += 1
                elif s < 2000 * 1024:
                    sizes["500-2000"] += 1
                else:
                    sizes[">2000"] += 1

        return ComplexityProfile(
            avg_function_length=round(avg_len, 1),
            max_nesting_depth=max_nesting,
            cyclomatic_summary={"avg_func_len": round(avg_len, 1), "max_nesting": max_nesting},
            file_size_distribution=sizes,
        )

    def _security_sensitive_ratio(self) -> float:
        sensitive_patterns = [
            "auth", "password", "secret", "token", "credential",
            "encrypt", "decrypt", "ssl", "tls", "certificate",
            "sanitize", "escape", "sql", "injection", "xss",
        ]
        sensitive_count = 0
        total_files = 0
        for f in self.repo_path.rglob("*"):
            if f.is_file():
                total_files += 1
                name = f.name.lower()
                if any(p in name for p in sensitive_patterns):
                    sensitive_count += 1
        return sensitive_count / max(total_files, 1)

    def _test_to_code_ratio(self) -> float:
        code_lines = 0
        test_lines = 0
        for f in self.repo_path.rglob("*"):
            if f.is_file() and f.name.endswith((".py", ".ts", ".js", ".rs", ".go", ".java")):
                lines = len(f.read_text(errors="ignore").splitlines())
                if "test" in f.name.lower() or "spec" in f.name.lower():
                    test_lines += lines
                else:
                    code_lines += lines
        return test_lines / max(code_lines, 1)

    def _compute_hash(self, components: Dict, struct: StructuralSignature, complexity: ComplexityProfile) -> str:
        data = {
            "components": {k.value: v for k, v in components.items()},
            "structure": struct.__dict__,
            "complexity": complexity.__dict__,
        }
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _sample_files(self, max_files: int, pattern: str = "*") -> str:
        texts: List[str] = []
        files = list(self.repo_path.rglob(pattern))
        import random as _r
        selected = _r.sample(files, min(max_files, len(files)))
        for f in selected:
            if f.is_file() and f.stat().st_size < 500 * 1024:
                try:
                    texts.append(f.read_text(errors="ignore"))
                except Exception:
                    pass
        return "\n".join(texts)

    def _anonymize_dependencies(self, components: Dict) -> List[AnonymizedDependency]:
        deps = components.get(FingerprintComponent.DEPENDENCIES, {})
        anonymized = []
        for filename, dep_list in deps.items():
            for dep in dep_list[:10]:
                category = self._categorize_dep(dep)
                anonymized.append(AnonymizedDependency(
                    category=category,
                    role=filename,
                    prevalence=1.0 / max(len(dep_list), 1),
                ))
        return anonymized

    def _categorize_dep(self, dep: str) -> str:
        dep_lower = dep.lower()
        if any(kw in dep_lower for kw in ["fastapi", "flask", "django", "express", "spring"]):
            return "web_framework"
        if any(kw in dep_lower for kw in ["pytest", "jest", "mocha", "unittest"]):
            return "testing"
        if any(kw in dep_lower for kw in ["sqlalchemy", "prisma", "diesel", "django-db"]):
            return "database"
        if any(kw in dep_lower for kw in ["auth", "jwt", "oauth", "passport"]):
            return "authentication"
        if any(kw in dep_lower for kw in ["redis", "rabbitmq", "kafka", "celery"]):
            return "infrastructure"
        return "utility"
