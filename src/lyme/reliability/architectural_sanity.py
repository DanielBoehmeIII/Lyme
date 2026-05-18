"""ArchitecturalSanity — detects bad architecture decisions mid-execution."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import re


class SanityVerdict(str, Enum):
    SANE = "sane"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class ArchitectureRule(str, Enum):
    LAYER_VIOLATION = "layer_violation"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    GOD_MODULE = "god_module"
    EXCESSIVE_COUPLING = "excessive_coupling"
    DUPLICATE_ABSTRACTION = "duplicate_abstraction"
    LEAKY_ABSTRACTION = "leaky_abstraction"
    UNUSED_ABSTRACTION = "unused_abstraction"
    INAPPROPRIATE_INTIMACY = "inappropriate_intimacy"
    CYCLIC_HIERARCHY = "cyclic_hierarchy"
    MISSING_INTERFACE = "missing_interface"


@dataclass
class SanityCheck:
    rule: ArchitectureRule
    verdict: SanityVerdict
    description: str
    files: List[str]
    severity: float
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "rule": self.rule.value,
            "verdict": self.verdict.value,
            "description": self.description,
            "files": self.files[:5],
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


@dataclass
class ArchitectureProfile:
    module_count: int
    depth: int
    coupling_scores: Dict[str, float]
    god_modules: List[str]
    circular_deps: List[Tuple[str, str]]
    layer_violations: List[Tuple[str, str, str]]
    abstraction_ratio: float

    def to_dict(self) -> Dict:
        return {
            "module_count": self.module_count,
            "depth": self.depth,
            "avg_coupling": round(sum(self.coupling_scores.values()) / max(len(self.coupling_scores), 1), 3),
            "god_modules": self.god_modules[:5],
            "circular_deps": self.circular_deps[:5],
            "layer_violations": self.layer_violations[:5],
            "abstraction_ratio": round(self.abstraction_ratio, 3),
        }

    @classmethod
    def from_files(cls, files: List[str], imports: Dict[str, List[str]]) -> ArchitectureProfile:
        modules = [f for f in files if f.endswith(".py")]
        depths = [f.count("/") for f in modules]
        max_depth = max(depths) if depths else 0

        coupling: Dict[str, float] = {}
        for mod, deps in imports.items():
            coupling[mod] = len(deps) / max(len(modules), 1)

        threshold = max(coupling.values()) * 0.8 if coupling else 0
        gods = [m for m, c in coupling.items() if c >= threshold and c > 0.3]

        circ_deps: List[Tuple[str, str]] = []
        def _find_cycles() -> List[Tuple[str, str]]:
            cycles = []
            all_nodes = list(imports.keys())
            for start in all_nodes:
                visited = set()
                stack = [(start, [start])]
                while stack:
                    node, path = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    for dep in imports.get(node, []):
                        if dep == start and len(path) > 1:
                            for i in range(len(path) - 1):
                                edge = (path[i], path[i + 1])
                                if edge not in cycles:
                                    cycles.append(edge)
                            cycles.append((node, start))
                        elif dep in imports:
                            stack.append((dep, path + [dep]))
            return cycles
        detected = _find_cycles()
        seen: Set[Tuple[str, str]] = set()
        for a, b in detected:
            if (a, b) not in seen and (b, a) not in seen:
                circ_deps.append((a, b))
                seen.add((a, b))

        layer_violations: List[Tuple[str, str, str]] = []
        layers = {"api/", "routes/", "handlers/", "controllers/"}
        lower = {"domain/", "core/", "model/", "models/", "entity/", "entities/", "service/", "repository/", "infra/", "infrastructure/"}
        for mod, deps in imports.items():
            for dep in deps:
                if any(l in mod.lower() for l in layers) and any(lw in dep.lower() for lw in lower):
                    layer_violations.append(("layer_up", mod, dep))

        abstract_count = sum(1 for f in modules if "abstract" in f.lower() or "base_" in f.lower() or "interface" in f.lower() or "protocol" in f.lower())
        ratio = abstract_count / max(len(modules), 1)

        return cls(
            module_count=len(modules),
            depth=max_depth,
            coupling_scores=coupling,
            god_modules=gods,
            circular_deps=circ_deps,
            layer_violations=layer_violations,
            abstraction_ratio=ratio,
        )


@dataclass
class SanityReport:
    checks: List[SanityCheck]
    profile: ArchitectureProfile
    verdict: SanityVerdict
    total_violations: int
    critical_count: int
    warning_count: int
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "profile": self.profile.to_dict(),
            "verdict": self.verdict.value,
            "total_violations": self.total_violations,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        icons = {"sane": "✅", "warning": "⚠️", "violation": "🚫", "critical": "🔴"}
        lines = []
        lines.append("=" * 70)
        lines.append("  ARCHITECTURAL SANITY CHECK")
        lines.append("=" * 70)
        lines.append(f"  Verdict: {icons.get(self.verdict.value, '•')} {self.verdict.value.upper()}")
        lines.append(f"  Violations: {self.total_violations} "
                     f"(Critical: {self.critical_count}, Warning: {self.warning_count})")
        lines.append(f"  Modules: {self.profile.module_count} | "
                     f"Depth: {self.profile.depth} | "
                     f"Abstraction: {self.profile.abstraction_ratio:.2f}")
        if self.profile.god_modules:
            lines.append(f"  God Modules: {', '.join(self.profile.god_modules[:3])}")
        if self.profile.circular_deps:
            lines.append(f"  Circular Dependencies: {len(self.profile.circular_deps)}")
        lines.append("-" * 70)
        for c in self.checks:
            if c.verdict in (SanityVerdict.VIOLATION, SanityVerdict.CRITICAL, SanityVerdict.WARNING):
                icon = icons.get(c.verdict.value, "•")
                lines.append(f"  {icon} [{c.rule.value}] {c.description[:70]}")
                lines.append(f"     → {c.recommendation}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ArchitecturalSanity:
    def __init__(self):
        self._allowed_patterns: List[str] = []
        self._forbidden_patterns: List[str] = []

    def add_allowed_pattern(self, pattern: str) -> None:
        self._allowed_patterns.append(pattern)

    def add_forbidden_pattern(self, pattern: str) -> None:
        self._forbidden_patterns.append(pattern)

    def check(self, files: List[str], imports: Dict[str, List[str]],
              changes: Optional[List[Dict]] = None) -> SanityReport:
        profile = ArchitectureProfile.from_files(files, imports)
        checks: List[SanityCheck] = []
        recommendations: List[str] = []

        for mod in profile.god_modules:
            checks.append(SanityCheck(
                rule=ArchitectureRule.GOD_MODULE,
                verdict=SanityVerdict.WARNING,
                description=f"Module '{mod}' has high coupling ({profile.coupling_scores.get(mod, 0):.2f})",
                files=[mod],
                severity=profile.coupling_scores.get(mod, 0),
                recommendation=f"Decompose '{mod}' into smaller focused modules",
            ))

        for a, b in profile.circular_deps[:10]:
            checks.append(SanityCheck(
                rule=ArchitectureRule.CIRCULAR_DEPENDENCY,
                verdict=SanityVerdict.VIOLATION,
                description=f"Circular dependency between '{a}' and '{b}'",
                files=[a, b],
                severity=0.7,
                recommendation=f"Extract shared dependency into a new module or invert one dependency",
            ))

        for violation_type, src, tgt in profile.layer_violations[:10]:
            checks.append(SanityCheck(
                rule=ArchitectureRule.LAYER_VIOLATION,
                verdict=SanityVerdict.WARNING,
                description=f"'{src}' depends on lower layer '{tgt}'",
                files=[src, tgt],
                severity=0.5,
                recommendation=f"Move shared logic to a service layer or inject dependency",
            ))

        if profile.abstraction_ratio > 0.5:
            checks.append(SanityCheck(
                rule=ArchitectureRule.DUPLICATE_ABSTRACTION,
                verdict=SanityVerdict.WARNING,
                description=f"High abstraction ratio ({profile.abstraction_ratio:.2f}) — possible over-engineering",
                files=[],
                severity=min(1.0, profile.abstraction_ratio),
                recommendation="Review if all abstractions are justified by actual variation points",
            ))
        elif profile.module_count > 5 and profile.abstraction_ratio < 0.1:
            checks.append(SanityCheck(
                rule=ArchitectureRule.MISSING_INTERFACE,
                verdict=SanityVerdict.WARNING,
                description=f"Low abstraction ratio ({profile.abstraction_ratio:.2f}) — possible missing interfaces",
                files=[],
                severity=0.4,
                recommendation="Consider extracting interfaces for modules with multiple implementations",
            ))

        if changes:
            for change in changes:
                file_path = change.get("file", "")
                if file_path:
                    for pattern in self._forbidden_patterns:
                        if pattern.lower() in file_path.lower():
                            checks.append(SanityCheck(
                                rule=ArchitectureRule.LAYER_VIOLATION,
                                verdict=SanityVerdict.CRITICAL,
                                description=f"Change touches forbidden zone matching '{pattern}': {file_path}",
                                files=[file_path],
                                severity=0.9,
                                recommendation=f"Move change outside forbidden zone '{pattern}'",
                            ))

        critical_count = sum(1 for c in checks if c.verdict == SanityVerdict.CRITICAL)
        warning_count = sum(1 for c in checks if c.verdict == SanityVerdict.WARNING)
        violation_count = sum(1 for c in checks if c.verdict in (SanityVerdict.VIOLATION, SanityVerdict.CRITICAL))

        if critical_count > 0:
            verdict = SanityVerdict.CRITICAL
        elif violation_count > 0:
            verdict = SanityVerdict.VIOLATION
        elif warning_count > 2:
            verdict = SanityVerdict.WARNING
        else:
            verdict = SanityVerdict.SANE

        if critical_count > 0:
            recommendations.append("Stop: critical architecture violations detected")
        if profile.circular_deps:
            recommendations.append("Resolve circular dependencies before making changes")
        if profile.god_modules:
            recommendations.append("Plan refactoring of god modules into focused services")
        if not recommendations:
            recommendations.append("Architecture appears healthy — proceed with confidence")

        return SanityReport(
            checks=checks,
            profile=profile,
            verdict=verdict,
            total_violations=violation_count,
            critical_count=critical_count,
            warning_count=warning_count,
            recommendations=recommendations,
        )

    @classmethod
    def check_from_repo(cls, repo_path: str) -> SanityReport:
        import ast
        from pathlib import Path

        root = Path(repo_path)
        py_files = list(root.rglob("*.py"))
        imports: Dict[str, List[str]] = {}
        for f in py_files:
            rel = str(f.relative_to(root))
            deps = set()
            try:
                tree = ast.parse(f.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            deps.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            deps.add(node.module.split(".")[0])
            except Exception:
                pass
            imports[rel] = list(deps)

        inst = cls()
        return inst.check([str(f) for f in py_files], imports)
