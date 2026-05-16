"""Machine-Readable Architecture File System.

A package.json for architecture — describing:
- subsystems
- responsibilities
- boundaries
- allowed dependencies
- forbidden dependencies
- runtime flows
- state ownership
- invariants
- risk zones
- historical notes
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import json
import hashlib
import re
import subprocess


@dataclass
class Responsibility:
    name: str
    description: str
    owned_files: List[str] = field(default_factory=list)
    apis_provided: List[str] = field(default_factory=list)
    apis_consumed: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BoundaryRule:
    description: str
    direction: str
    from_subsystem: str
    to_subsystem: str
    allowed: bool = True
    reason: str = ""
    severity: str = "error"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DependencyRule:
    description: str
    source_subsystem: str
    target_subsystem: str
    allowed: bool = True
    through_interface: Optional[str] = None
    reason: str = ""
    severity: str = "error"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuntimeFlow:
    name: str
    description: str
    steps: List[str] = field(default_factory=list)
    subsystems_involved: List[str] = field(default_factory=list)
    criticality: str = "medium"
    frequency: str = "often"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StateOwnership:
    subsystem: str
    owned_state: List[str] = field(default_factory=list)
    persistence: str = "memory"
    access_pattern: str = "read-write"
    consistency_requirements: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvariantDef:
    name: str
    description: str
    scope: str
    severity: str = "medium"
    rule: str = ""
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskZone:
    name: str
    description: str
    subsystems_affected: List[str] = field(default_factory=list)
    severity: str = "medium"
    mitigation: str = ""
    indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HistoricalNote:
    date: str
    event: str
    description: str
    author: str = ""
    commit: str = ""
    impact: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubsystemDef:
    name: str
    description: str
    path: str
    responsibilities: List[Responsibility] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    stability: str = "stable"
    owner: str = ""
    file_count: int = 0
    complexity_score: float = 0.0
    test_coverage: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "responsibilities": [r.to_dict() for r in self.responsibilities],
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "stability": self.stability,
            "owner": self.owner,
            "file_count": self.file_count,
            "complexity_score": self.complexity_score,
            "test_coverage": self.test_coverage,
        }


@dataclass
class ArchitectureFile:
    schema_version: str = "0.1.0"
    repo_name: str = ""
    repo_path: str = ""
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    repo_hash: str = ""

    subsystems: List[SubsystemDef] = field(default_factory=list)
    boundary_rules: List[BoundaryRule] = field(default_factory=list)
    dependency_rules: List[DependencyRule] = field(default_factory=list)
    runtime_flows: List[RuntimeFlow] = field(default_factory=list)
    state_ownerships: List[StateOwnership] = field(default_factory=list)
    invariants: List[InvariantDef] = field(default_factory=list)
    risk_zones: List[RiskZone] = field(default_factory=list)
    historical_notes: List[HistoricalNote] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "generated_at": self.generated_at,
            "repo_hash": self.repo_hash,
            "subsystems": [s.to_dict() for s in self.subsystems],
            "boundary_rules": [b.to_dict() for b in self.boundary_rules],
            "dependency_rules": [d.to_dict() for d in self.dependency_rules],
            "runtime_flows": [f.to_dict() for f in self.runtime_flows],
            "state_ownerships": [s.to_dict() for s in self.state_ownerships],
            "invariants": [i.to_dict() for i in self.invariants],
            "risk_zones": [z.to_dict() for z in self.risk_zones],
            "historical_notes": [n.to_dict() for n in self.historical_notes],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Architecture: {self.repo_name}")
        lines.append(f"")
        lines.append(f"**Schema**: v{self.schema_version}")
        lines.append(f"**Path**: {self.repo_path}")
        lines.append(f"**Generated**: {self.generated_at}")
        lines.append(f"")

        lines.append(f"## Subsystems ({len(self.subsystems)})")
        for s in self.subsystems:
            lines.append(f"")
            lines.append(f"### {s.name}")
            lines.append(f"- **Path**: `{s.path}`")
            lines.append(f"- **Description**: {s.description}")
            lines.append(f"- **Stability**: {s.stability}")
            lines.append(f"- **Files**: {s.file_count}")
            lines.append(f"- **Responsibilities**:")
            for r in s.responsibilities:
                lines.append(f"  - {r.name}: {r.description}")
                if r.owned_files:
                    for pf in r.owned_files[:3]:
                        lines.append(f"    - `{pf}`")
            lines.append(f"- **Dependencies**: {', '.join(s.dependencies) if s.dependencies else '(none)'}")
            lines.append(f"- **Dependents**: {', '.join(s.dependents) if s.dependents else '(none)'}")
        lines.append(f"")

        if self.boundary_rules:
            lines.append(f"## Boundary Rules ({len(self.boundary_rules)})")
            for b in self.boundary_rules:
                arrow = "→" if b.allowed else "✗"
                lines.append(f"- {arrow} {b.from_subsystem} → {b.to_subsystem}: {b.description}")
            lines.append(f"")

        if self.dependency_rules:
            lines.append(f"## Dependency Rules ({len(self.dependency_rules)})")
            for d in self.dependency_rules:
                arrow = "→" if d.allowed else "✗"
                through = f" (via {d.through_interface})" if d.through_interface else ""
                lines.append(f"- {arrow} {d.source_subsystem} → {d.target_subsystem}{through}: {d.description}")
            lines.append(f"")

        if self.runtime_flows:
            lines.append(f"## Runtime Flows ({len(self.runtime_flows)})")
            for f in self.runtime_flows:
                lines.append(f"")
                lines.append(f"### {f.name} [{f.criticality}]")
                lines.append(f"- {f.description}")
                lines.append(f"- **Steps**:")
                for step in f.steps:
                    lines.append(f"  1. {step}")
                lines.append(f"- **Subsystems**: {', '.join(f.subsystems_involved)}")
        lines.append(f"")

        if self.invariants:
            lines.append(f"## Invariants ({len(self.invariants)})")
            for inv in self.invariants:
                lines.append(f"- [{inv.severity}] {inv.name}: {inv.description}")
        lines.append(f"")

        if self.risk_zones:
            lines.append(f"## Risk Zones ({len(self.risk_zones)})")
            for z in self.risk_zones:
                lines.append(f"- [{z.severity}] {z.name}: {z.description}")
                if z.mitigation:
                    lines.append(f"  - Mitigation: {z.mitigation}")
        lines.append(f"")

        if self.historical_notes:
            lines.append(f"## Historical Notes ({len(self.historical_notes)})")
            for n in self.historical_notes:
                lines.append(f"- {n.date}: {n.event} — {n.description}")
        lines.append(f"")

        return "\n".join(lines)


class ArchitectureSchema:
    SCHEMA_URL = "https://lyme.dev/schema/architecture-v0.1.0"

    @classmethod
    def validate(cls, arch: ArchitectureFile) -> List[str]:
        errors = []
        if not arch.repo_name:
            errors.append("Missing repo_name")
        if not arch.schema_version:
            errors.append("Missing schema_version")
        if not arch.subsystems:
            errors.append("No subsystems defined")

        system_names = {s.name for s in arch.subsystems}
        for s in arch.subsystems:
            if not s.name:
                errors.append("Subsystem missing name")
            for dep in s.dependencies:
                if dep not in system_names:
                    errors.append(f"Subsystem '{s.name}' depends on unknown subsystem '{dep}'")

        for b in arch.boundary_rules:
            if b.from_subsystem not in system_names:
                errors.append(f"Boundary rule references unknown subsystem '{b.from_subsystem}'")
            if b.to_subsystem not in system_names:
                errors.append(f"Boundary rule references unknown subsystem '{b.to_subsystem}'")

        for d in arch.dependency_rules:
            if d.source_subsystem not in system_names:
                errors.append(f"Dependency rule references unknown subsystem '{d.source_subsystem}'")

        return errors


class ArchitectureFileValidator:
    def validate(self, arch: ArchitectureFile) -> Dict[str, Any]:
        schema_errors = ArchitectureSchema.validate(arch)
        warnings = []
        info = []

        for s in arch.subsystems:
            if s.stability == "unstable" and s.complexity_score > 0.7:
                warnings.append(f"Subsystem '{s.name}' is both unstable and highly complex")
            if s.file_count > 50:
                warnings.append(f"Subsystem '{s.name}' has {s.file_count} files — consider splitting")

        for z in arch.risk_zones:
            if z.severity == "critical" and not z.mitigation:
                warnings.append(f"Critical risk zone '{z.name}' has no mitigation plan")

        return {
            "valid": len(schema_errors) == 0,
            "errors": schema_errors,
            "warnings": warnings,
            "info": info,
            "total_subsystems": len(arch.subsystems),
            "total_rules": len(arch.boundary_rules) + len(arch.dependency_rules),
        }


class ArchitectureFileGenerator:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        self._git_available = (self.repo_path / ".git").is_dir()

    def generate(self) -> ArchitectureFile:
        arch = ArchitectureFile(
            repo_name=self.repo_path.name,
            repo_path=str(self.repo_path),
            repo_hash=self._compute_hash(),
        )

        arch.subsystems = self._discover_subsystems()
        arch.boundary_rules = self._infer_boundary_rules(arch.subsystems)
        arch.dependency_rules = self._infer_dependency_rules(arch.subsystems)
        arch.runtime_flows = self._infer_runtime_flows(arch.subsystems)
        arch.state_ownerships = self._infer_state_ownership(arch.subsystems)
        arch.invariants = self._infer_invariants(arch.subsystems)
        arch.risk_zones = self._infer_risk_zones(arch.subsystems)
        arch.historical_notes = self._collect_historical_notes()
        arch.metadata = {
            "generator": "lyme archfile generate",
            "git_available": self._git_available,
            "file_count": len(list(self.repo_path.rglob("*.py"))),
        }

        return arch

    def _compute_hash(self) -> str:
        return hashlib.sha256(str(self.repo_path).encode()).hexdigest()[:16]

    def _discover_subsystems(self) -> List[SubsystemDef]:
        subsystems: List[SubsystemDef] = {}

        if (self.repo_path / "src").exists():
            src_dir = self.repo_path / "src"
            for item in sorted(src_dir.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    py_files = list(item.rglob("*.py"))
                    file_count = len(py_files)
                    if file_count == 0:
                        continue

                    complexity = 0.0
                    total_lines = 0
                    for pf in py_files:
                        try:
                            lines = sum(1 for _ in open(pf, "rb"))
                            total_lines += lines
                        except Exception:
                            pass
                    complexity = min(1.0, total_lines / 2000)

                    responsibilities = []
                    for pf in py_files[:10]:
                        try:
                            content = pf.read_text(errors="ignore")
                            classes = re.findall(r'class\s+(\w+)', content)
                            funcs = re.findall(r'(?:async\s+)?def\s+(\w+)', content)
                            if classes or funcs:
                                responsibilities.append(Responsibility(
                                    name=pf.stem,
                                    description=f"Provides {len(classes)} classes, {len(funcs)} functions",
                                    owned_files=[str(pf.relative_to(self.repo_path))],
                                ))
                        except Exception:
                            pass

                    subsystem = SubsystemDef(
                        name=item.name,
                        description=f"Module at src/{item.name}",
                        path=str(item.relative_to(self.repo_path)),
                        responsibilities=responsibilities[:5],
                        file_count=file_count,
                        complexity_score=round(complexity, 2),
                    )
                    subsystems[item.name] = subsystem

        for name, sub in subsystems.items():
            deps = set()
            for pf_path in [self.repo_path / sub.path]:
                if pf_path.is_dir():
                    for pf in pf_path.rglob("*.py"):
                        try:
                            content = pf.read_text(errors="ignore")
                            for match in re.finditer(r'from\s+(\w+)', content):
                                dep = match.group(1)
                                if dep in subsystems and dep != name:
                                    deps.add(dep)
                            for match in re.finditer(r'import\s+(\w+)', content):
                                dep = match.group(1)
                                if dep in subsystems and dep != name:
                                    deps.add(dep)
                        except Exception:
                            pass
            sub.dependencies = sorted(deps)
            for dep in sub.dependencies:
                if dep in subsystems:
                    subsystems[dep].dependents.append(name)

        return list(subsystems.values())

    def _infer_boundary_rules(self, subsystems: List[SubsystemDef]) -> List[BoundaryRule]:
        rules = []
        system_names = {s.name for s in subsystems}
        for s in subsystems:
            for dep in s.dependencies:
                rules.append(BoundaryRule(
                    description=f"{s.name} may depend on {dep}",
                    direction="outbound",
                    from_subsystem=s.name,
                    to_subsystem=dep,
                    allowed=True,
                    reason="Inferred from source imports",
                ))
        return rules

    def _infer_dependency_rules(self, subsystems: List[SubsystemDef]) -> List[DependencyRule]:
        rules = []
        for s in subsystems:
            for dep in s.dependencies:
                rules.append(DependencyRule(
                    description=f"{s.name} imports {dep}",
                    source_subsystem=s.name,
                    target_subsystem=dep,
                    allowed=True,
                    reason="Inferred from source analysis",
                ))
        return rules

    def _infer_runtime_flows(self, subsystems: List[SubsystemDef]) -> List[RuntimeFlow]:
        flows = []
        system_names = [s.name for s in subsystems]
        if len(system_names) >= 2:
            flows.append(RuntimeFlow(
                name="typical_call_flow",
                description="Typical module call flow through dependency chain",
                steps=[f"{s} processes request" for s in system_names[:4]],
                subsystems_involved=system_names[:4],
                criticality="high",
                frequency="often",
            ))
        return flows

    def _infer_state_ownership(self, subsystems: List[SubsystemDef]) -> List[StateOwnership]:
        ownerships = []
        for s in subsystems:
            if s.file_count > 0:
                storage_files = [r.name for r in s.responsibilities if "store" in r.name.lower() or "storage" in r.name.lower() or "db" in r.name.lower()]
                if storage_files:
                    ownerships.append(StateOwnership(
                        subsystem=s.name,
                        owned_state=storage_files,
                        persistence="file",
                        access_pattern="read-write",
                    ))
        return ownerships

    def _infer_invariants(self, subsystems: List[SubsystemDef]) -> List[InvariantDef]:
        invariants = []
        for s in subsystems:
            if s.complexity_score > 0.8:
                invariants.append(InvariantDef(
                    name=f"{s.name}_complexity_limit",
                    description=f"{s.name} complexity ({s.complexity_score:.2f}) exceeds threshold",
                    scope=s.name,
                    severity="warning",
                    rule=f"{s.name}.complexity <= 0.8",
                ))
        return invariants

    def _infer_risk_zones(self, subsystems: List[SubsystemDef]) -> List[RiskZone]:
        zones = []
        for s in subsystems:
            if s.complexity_score > 0.7:
                zones.append(RiskZone(
                    name=f"{s.name}_risk",
                    description=f"High complexity subsystem: {s.name} ({s.complexity_score:.2f})",
                    subsystems_affected=[s.name] + s.dependents,
                    severity="high" if s.complexity_score > 0.9 else "medium",
                    indicators=["complexity_score > 0.7"],
                ))
        return zones

    def _collect_historical_notes(self) -> List[HistoricalNote]:
        notes = []
        if not self._git_available:
            return notes

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-20", "--format=%H %ct %an %s"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10,
            )
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.strip().split(" ", 3)
                if len(parts) >= 4:
                    commit_hash = parts[0]
                    timestamp = parts[1]
                    author = parts[2]
                    message = parts[3]
                    from datetime import datetime
                    try:
                        date_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        date_str = "unknown"
                    notes.append(HistoricalNote(
                        date=date_str,
                        event="commit",
                        description=message[:100],
                        author=author,
                        commit=commit_hash[:8],
                    ))
        except Exception:
            pass
        return notes


class ArchitectureFileUpdater:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        self._arch_path = self.repo_path / ".lyme" / "architecture.json"

    def update(self) -> ArchitectureFile:
        generator = ArchitectureFileGenerator(self.repo_path)
        arch = generator.generate()

        existing = self.load()
        if existing:
            arch.historical_notes = existing.historical_notes
            for s in arch.subsystems:
                for es in existing.subsystems:
                    if s.name == es.name:
                        s.stability = es.stability
                        s.owner = es.owner
                        s.test_coverage = es.test_coverage

        self._arch_path.parent.mkdir(parents=True, exist_ok=True)
        self._arch_path.write_text(arch.to_json())

        return arch

    def load(self) -> Optional[ArchitectureFile]:
        if not self._arch_path.exists():
            return None
        try:
            data = json.loads(self._arch_path.read_text())
            arch = ArchitectureFile(
                schema_version=data.get("schema_version", "0.1.0"),
                repo_name=data.get("repo_name", ""),
                repo_path=data.get("repo_path", ""),
                generated_at=data.get("generated_at", ""),
                repo_hash=data.get("repo_hash", ""),
            )
            for sd in data.get("subsystems", []):
                sub = SubsystemDef(
                    name=sd.get("name", ""),
                    description=sd.get("description", ""),
                    path=sd.get("path", ""),
                    stability=sd.get("stability", "stable"),
                    owner=sd.get("owner", ""),
                    file_count=sd.get("file_count", 0),
                    complexity_score=sd.get("complexity_score", 0.0),
                    test_coverage=sd.get("test_coverage"),
                )
                for rd in sd.get("responsibilities", []):
                    sub.responsibilities.append(Responsibility(**rd))
                sub.dependencies = sd.get("dependencies", [])
                sub.dependents = sd.get("dependents", [])
                arch.subsystems.append(sub)

            for bd in data.get("boundary_rules", []):
                arch.boundary_rules.append(BoundaryRule(**bd))
            for dd in data.get("dependency_rules", []):
                arch.dependency_rules.append(DependencyRule(**dd))
            for fd in data.get("runtime_flows", []):
                arch.runtime_flows.append(RuntimeFlow(**fd))
            for sd in data.get("state_ownerships", []):
                arch.state_ownerships.append(StateOwnership(**sd))
            for id_ in data.get("invariants", []):
                arch.invariants.append(InvariantDef(**id_))
            for zd in data.get("risk_zones", []):
                arch.risk_zones.append(RiskZone(**zd))
            for nd in data.get("historical_notes", []):
                arch.historical_notes.append(HistoricalNote(**nd))
            arch.metadata = data.get("metadata", {})
            return arch
        except (json.JSONDecodeError, Exception):
            return None


class ArchitectureViolationDetector:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()

    def detect(self, arch: ArchitectureFile) -> List[Dict[str, Any]]:
        violations = []

        current_deps: Dict[str, set] = {}
        for s in arch.subsystems:
            current_deps[s.name] = set()

            src_path = self.repo_path / s.path
            if src_path.exists() and src_path.is_dir():
                for pf in src_path.rglob("*.py"):
                    try:
                        content = pf.read_text(errors="ignore")
                        for match in re.finditer(r'from\s+(\w+)', content):
                            dep = match.group(1)
                            if dep in {ss.name for ss in arch.subsystems} and dep != s.name:
                                current_deps[s.name].add(dep)
                        for match in re.finditer(r'import\s+(\w+)', content):
                            dep = match.group(1)
                            if dep in {ss.name for ss in arch.subsystems} and dep != s.name:
                                current_deps[s.name].add(dep)
                    except Exception:
                        pass

        for rule in arch.dependency_rules:
            if not rule.allowed:
                if rule.target_subsystem in current_deps.get(rule.source_subsystem, set()):
                    violations.append({
                        "type": "forbidden_dependency",
                        "source": rule.source_subsystem,
                        "target": rule.target_subsystem,
                        "description": rule.description,
                        "severity": rule.severity,
                    })

        allowed_deps_map: Dict[str, set] = {}
        for rule in arch.dependency_rules:
            if rule.allowed:
                if rule.source_subsystem not in allowed_deps_map:
                    allowed_deps_map[rule.source_subsystem] = set()
                allowed_deps_map[rule.source_subsystem].add(rule.target_subsystem)

        for sub_name, deps in current_deps.items():
            allowed = allowed_deps_map.get(sub_name, set())
            for dep in deps:
                if dep not in allowed and allowed:
                    violations.append({
                        "type": "undeclared_dependency",
                        "source": sub_name,
                        "target": dep,
                        "description": f"Undeclared dependency: {sub_name} → {dep}",
                        "severity": "warning",
                    })

        for s in arch.subsystems:
            if s.stability in ("stable", "core"):
                if s.complexity_score > 0.8:
                    violations.append({
                        "type": "stable_subsystem_high_complexity",
                        "source": s.name,
                        "target": "",
                        "description": f"Stable subsystem '{s.name}' has high complexity ({s.complexity_score:.2f})",
                        "severity": "warning",
                    })

        return violations


class ArchitectureFileRenderer:
    @staticmethod
    def to_mermaid(arch: ArchitectureFile) -> str:
        lines = ["graph TD"]
        for s in arch.subsystems:
            node_id = s.name.replace("-", "_").replace(" ", "_")
            lines.append(f"    {node_id}[\"{s.name}\"]")
        lines.append("")
        for rule in arch.dependency_rules:
            if rule.allowed:
                src = rule.source_subsystem.replace("-", "_").replace(" ", "_")
                tgt = rule.target_subsystem.replace("-", "_").replace(" ", "_")
                lines.append(f"    {src} -->|{rule.description[:20]}| {tgt}")
        return "\n".join(lines)

    @staticmethod
    def to_d3_json(arch: ArchitectureFile) -> Dict[str, Any]:
        nodes = []
        links = []
        for s in arch.subsystems:
            nodes.append({
                "id": s.name,
                "group": 1,
                "file_count": s.file_count,
                "complexity": s.complexity_score,
                "stability": s.stability,
            })
        for rule in arch.dependency_rules:
            if rule.allowed:
                links.append({
                    "source": rule.source_subsystem,
                    "target": rule.target_subsystem,
                    "value": 1,
                    "label": rule.description[:30],
                })
        return {"nodes": nodes, "links": links}
