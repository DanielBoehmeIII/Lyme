from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import re


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CompatibilityIssue:
    library: str
    version: str
    peer_library: str
    peer_version: str
    description: str
    severity: IssueSeverity
    resolution: str = ""
    automated_fix_available: bool = False

    def to_dict(self) -> Dict:
        return {
            "library": self.library,
            "version": self.version,
            "peer_library": self.peer_library,
            "peer_version": self.peer_version,
            "description": self.description,
            "severity": self.severity.value,
            "resolution": self.resolution,
            "automated_fix_available": self.automated_fix_available,
        }


@dataclass
class CompatibilityReport:
    issues: List[CompatibilityIssue]
    overall_score: float
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    ecosystem: str = "python"

    def to_dict(self) -> Dict:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "overall_score": self.overall_score,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "ecosystem": self.ecosystem,
        }


class CompatibilityChecker:
    def __init__(self):
        self._rules = self._build_rules()

    def _build_rules(self) -> List[CompatibilityIssue]:
        return [
            CompatibilityIssue("pydantic", "<2.0", "fastapi", ">=0.100", "FastAPI 0.100+ requires Pydantic v2", IssueSeverity.ERROR, "Upgrade Pydantic to v2", automated_fix_available=True),
            CompatibilityIssue("pydantic", ">=2.0", "fastapi", "<0.100", "FastAPI <0.100 may not fully support Pydantic v2", IssueSeverity.WARNING, "Upgrade FastAPI to 0.100+", automated_fix_available=True),
            CompatibilityIssue("sqlalchemy", "<2.0", "fastapi", ">=0.95", "SQLAlchemy 1.x is deprecated; 2.0 recommended", IssueSeverity.WARNING, "Upgrade SQLAlchemy to 2.0", automated_fix_available=False),
            CompatibilityIssue("databases", ">=0.5", "fastapi", ">=0.95", "Databases library not recommended; use SQLAlchemy 2.0 async", IssueSeverity.WARNING, "Migrate from Databases to SQLAlchemy 2.0", automated_fix_available=False),
            CompatibilityIssue("python", "<3.10", "fastapi", ">=0.115", "FastAPI 0.115+ requires Python 3.10+", IssueSeverity.ERROR, "Upgrade Python to 3.10+", automated_fix_available=True),
            CompatibilityIssue("python", "<3.8", "pydantic", ">=2.0", "Pydantic v2 requires Python 3.8+", IssueSeverity.ERROR, "Upgrade Python to 3.8+", automated_fix_available=True),
            CompatibilityIssue("uvicorn", "<0.20", "fastapi", ">=0.90", "Older uvicorn may lack features FastAPI depends on", IssueSeverity.INFO, "Upgrade uvicorn to 0.20+", automated_fix_available=True),
            CompatibilityIssue("python-jose", "<3.0", "fastapi", ">=0.90", "Older python-jose versions have known security issues", IssueSeverity.CRITICAL, "Upgrade python-jose", automated_fix_available=True),
            CompatibilityIssue("gunicorn", "<22.0", "uvicorn", ">=0.30", "Older gunicorn may not support uvicorn workers", IssueSeverity.WARNING, "Upgrade gunicorn", automated_fix_available=True),
            CompatibilityIssue("pydantic", ">=2.0", "pydantic_v1", ">=0", "Pydantic v1 and v2 cannot coexist in the same process", IssueSeverity.ERROR, "Migrate all v1 usage to v2", automated_fix_available=False),
            CompatibilityIssue("httpx", "<0.25", "fastapi", ">=0.105", "Older httpx may not support all test client features", IssueSeverity.INFO, "Upgrade httpx to 0.25+", automated_fix_available=True),
            CompatibilityIssue("orjson", "<3.8", "fastapi", ">=0.100", "orjson 3.8+ recommended for optimal performance", IssueSeverity.INFO, "Upgrade orjson", automated_fix_available=True),
        ]

    def check_compatibility(self, dependencies: Dict[str, str]) -> CompatibilityReport:
        issues: List[CompatibilityIssue] = []

        for rule in self._rules:
            lib_version = dependencies.get(rule.library)
            if lib_version:
                if self._version_in_range(lib_version, rule.version):
                    issues.append(rule)

        for issue in issues:
            peer_version = dependencies.get(issue.peer_library)
            if not peer_version:
                pass

        total = len(issues)
        critical = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        errors = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        info_count = sum(1 for i in issues if i.severity == IssueSeverity.INFO)

        score = max(0.0, 1.0 - (critical * 0.3 + errors * 0.15 + warnings * 0.05 + info_count * 0.01))

        return CompatibilityReport(
            issues=issues,
            overall_score=round(score, 3),
            total_issues=total,
            critical_count=critical,
            warning_count=warnings,
            info_count=info_count,
        )

    def parse_pyproject(self, text: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        in_deps = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[tool.poetry.dependencies]") or stripped == "[project.dependencies]":
                in_deps = True
                continue
            if in_deps and stripped.startswith("["):
                in_deps = False
            if in_deps:
                m = re.match(r'"?(\w[\w-]*)"?\s*=\s*"(.*)"', stripped)
                if m:
                    deps[m.group(1)] = m.group(2)
                m2 = re.match(r'(\w[\w-]*)\s*[>=~<]+\s*([\d.]+)', stripped)
                if m2:
                    deps[m2.group(1)] = m2.group(2)
        return deps

    def parse_requirements(self, text: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "-", "//")):
                m = re.match(r'(\w[\w-]*)\s*[>=~<!]+\s*([\d.]+)', stripped)
                if m:
                    deps[m.group(1)] = m.group(2)
                elif "=" not in stripped and "#" not in stripped:
                    deps[stripped] = "latest"
        return deps

    def _version_in_range(self, actual: str, constraint: str) -> bool:
        if constraint.startswith("<"):
            max_v = constraint[1:]
            return self._version_to_tuple(actual) < self._version_to_tuple(max_v)
        if constraint.startswith(">="):
            min_v = constraint[2:]
            return self._version_to_tuple(actual) >= self._version_to_tuple(min_v)
        if constraint.startswith(">"):
            min_v = constraint[1:]
            return self._version_to_tuple(actual) > self._version_to_tuple(min_v)
        if constraint.startswith("=="):
            exact = constraint[2:]
            return actual.startswith(exact)
        if constraint.startswith("~="):
            major_minor = ".".join(constraint[2:].split(".")[:2])
            return actual.startswith(major_minor)
        if constraint.startswith("^"):
            major = constraint[1:].split(".")[0]
            return actual.split(".")[0] == major
        if "||" in constraint or "|" in constraint:
            separator = "||" if "||" in constraint else "|"
            for alt in constraint.split(separator):
                alt = alt.strip()
                if self._version_in_range(actual, alt):
                    return True
            return False
        return True

    def _version_to_tuple(self, version: str) -> Tuple:
        parts = version.replace("-", ".").replace("rc", ".").replace("b", ".").replace("a", ".").split(".")[:3]
        while len(parts) < 3:
            parts.append("0")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return (0, 0, 0)
