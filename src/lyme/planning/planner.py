"""Architecture-Aware Agent Planning.

Before any task, the agent should:
- inspect architecture files
- identify affected subsystems
- check boundary rules
- detect likely invariant violations
- choose context based on architecture
- select tests based on impacted areas
- explain plan in architectural terms
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import json
import subprocess
import time


class ImpactType(Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    DEPENDENCY = "dependency"
    INTERFACE = "interface"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AffectedSubsystem:
    name: str
    impact_type: ImpactType
    risk_level: RiskLevel
    confidence: float = 0.0
    description: str = ""
    relevant_files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "impact_type": self.impact_type.value,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "description": self.description,
            "relevant_files": self.relevant_files[:10],
        }


@dataclass
class SubsystemImpact:
    subsystem: str
    impact_score: float
    boundary_violations: List[str] = field(default_factory=list)
    invariant_violations: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    suggested_context_files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subsystem": self.subsystem,
            "impact_score": self.impact_score,
            "boundary_violations": self.boundary_violations[:5],
            "invariant_violations": self.invariant_violations[:5],
            "affected_files": self.affected_files[:10],
            "suggested_context_files": self.suggested_context_files[:10],
        }


@dataclass
class ContextSelection:
    total_files_available: int = 0
    files_selected: int = 0
    selection_strategy: str = "architecture_aware"
    subsystems_covered: int = 0
    estimated_tokens: int = 0
    selected_files: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "total_files_available": self.total_files_available,
            "files_selected": self.files_selected,
            "selection_strategy": self.selection_strategy,
            "subsystems_covered": self.subsystems_covered,
            "estimated_tokens": self.estimated_tokens,
            "selected_files": self.selected_files[:20],
            "rationale": self.rationale,
        }


@dataclass
class TestSelection:
    test_files_found: int = 0
    tests_relevant: int = 0
    recommended_commands: List[str] = field(default_factory=list)
    coverage_gaps: List[str] = field(default_factory=list)
    estimated_runtime_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "test_files_found": self.test_files_found,
            "tests_relevant": self.tests_relevant,
            "recommended_commands": self.recommended_commands[:5],
            "coverage_gaps": self.coverage_gaps[:5],
            "estimated_runtime_s": self.estimated_runtime_s,
        }


@dataclass
class PlanStep:
    step_id: str
    description: str
    subsystem_focus: str = ""
    estimated_effort: str = "medium"
    risk: RiskLevel = RiskLevel.LOW
    depends_on: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "subsystem_focus": self.subsystem_focus,
            "estimated_effort": self.estimated_effort,
            "risk": self.risk.value,
            "depends_on": self.depends_on,
            "success_criteria": self.success_criteria,
        }


@dataclass
class PlanResult:
    task_description: str = ""
    affected_subsystems: List[AffectedSubsystem] = field(default_factory=list)
    impacts: List[SubsystemImpact] = field(default_factory=list)
    context_selection: ContextSelection = field(default_factory=ContextSelection)
    test_selection: TestSelection = field(default_factory=TestSelection)
    plan_steps: List[PlanStep] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    planning_time_ms: float = 0.0
    architecture_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "task_description": self.task_description,
            "affected_subsystems": [s.to_dict() for s in self.affected_subsystems],
            "impacts": [i.to_dict() for i in self.impacts],
            "context_selection": self.context_selection.to_dict(),
            "test_selection": self.test_selection.to_dict(),
            "plan_steps": [s.to_dict() for s in self.plan_steps],
            "overall_risk": self.overall_risk.value,
            "planning_time_ms": self.planning_time_ms,
            "architecture_summary": self.architecture_summary,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Architecture-Aware Plan")
        lines.append(f"")
        lines.append(f"**Task**: {self.task_description}")
        lines.append(f"**Overall Risk**: {self.overall_risk.value.upper()}")
        lines.append(f"**Planning Time**: {self.planning_time_ms:.0f}ms")
        lines.append(f"")

        if self.architecture_summary:
            lines.append(f"### Architecture Summary")
            lines.append(f"{self.architecture_summary}")
            lines.append(f"")

        if self.affected_subsystems:
            lines.append(f"### Affected Subsystems ({len(self.affected_subsystems)})")
            for s in self.affected_subsystems:
                icon = "✓" if s.risk_level in (RiskLevel.NONE, RiskLevel.LOW) else "⚠"
                lines.append(f"- {icon} **{s.name}** ({s.impact_type.value})")
                lines.append(f"  - Risk: {s.risk_level.value}, Confidence: {s.confidence:.0%}")
                if s.description:
                    lines.append(f"  - {s.description}")
            lines.append(f"")

        if self.context_selection.selected_files:
            cs = self.context_selection
            lines.append(f"### Context Selection")
            lines.append(f"- Strategy: {cs.selection_strategy}")
            lines.append(f"- Files selected: {cs.files_selected}/{cs.total_files_available}")
            lines.append(f"- Subsystems covered: {cs.subsystems_covered}")
            lines.append(f"- Est. tokens: {cs.estimated_tokens}")
            if cs.rationale:
                lines.append(f"- Rationale: {cs.rationale}")
            lines.append(f"")

        if self.test_selection.recommended_commands:
            lines.append(f"### Test Selection")
            lines.append(f"- Relevant tests found: {self.test_selection.tests_relevant}/{self.test_selection.test_files_found}")
            for cmd in self.test_selection.recommended_commands:
                lines.append(f"- `{cmd}`")
            lines.append(f"")

        if self.plan_steps:
            lines.append(f"### Plan Steps ({len(self.plan_steps)})")
            for i, step in enumerate(self.plan_steps, 1):
                lines.append(f"**Step {i}**: {step.description}")
                lines.append(f"  - Subsystem: {step.subsystem_focus}")
                lines.append(f"  - Effort: {step.estimated_effort}")
                lines.append(f"  - Risk: {step.risk.value}")
                if step.success_criteria:
                    for sc in step.success_criteria:
                        lines.append(f"  - ✓ {sc}")
                lines.append(f"")

        return "\n".join(lines)


@dataclass
class PlannerConfig:
    context_token_budget: int = 8000
    max_affected_subsystems: int = 10
    include_test_selection: bool = True
    include_boundary_checking: bool = True
    include_invariant_checking: bool = True
    baseline_mode: bool = False


class ArchitectureAwarePlanner:
    def __init__(self, repo_path: Optional[Path] = None, config: Optional[PlannerConfig] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        self.config = config or PlannerConfig()
        self._arch_file = self.repo_path / ".lyme" / "architecture.json"

    def plan(self, task_description: str) -> PlanResult:
        start_time = time.time()
        result = PlanResult(task_description=task_description)

        arch = self._load_architecture()
        if arch:
            result.architecture_summary = self._summarize_architecture(arch)
            result.affected_subsystems = self._identify_affected_subsystems(arch, task_description)
            result.impacts = self._analyze_impacts(arch, result.affected_subsystems, task_description)
            result.context_selection = self._select_context(arch, result.affected_subsystems)
            if self.config.include_test_selection:
                result.test_selection = self._select_tests(result.affected_subsystems)
            result.plan_steps = self._generate_plan_steps(arch, result.affected_subsystems, task_description)
            result.overall_risk = self._assess_overall_risk(result.affected_subsystems, result.impacts)
        else:
            result.architecture_summary = "No architecture file found. Run `lyme archfile generate` first."
            result.plan_steps = [
                PlanStep(
                    step_id="1",
                    description=f"Analyze repository structure for: {task_description}",
                    risk=RiskLevel.MEDIUM,
                ),
                PlanStep(
                    step_id="2",
                    description="Examine relevant source files",
                    risk=RiskLevel.MEDIUM,
                ),
            ]

        result.planning_time_ms = (time.time() - start_time) * 1000
        return result

    def _load_architecture(self) -> Optional[Dict[str, Any]]:
        if not self._arch_file.exists():
            return None
        try:
            return json.loads(self._arch_file.read_text())
        except (json.JSONDecodeError, Exception):
            return None

    def _summarize_architecture(self, arch: Dict[str, Any]) -> str:
        subsystems = arch.get("subsystems", [])
        rules = arch.get("boundary_rules", [])
        return (
            f"Repository has {len(subsystems)} subsystems, "
            f"{len(rules)} boundary rules, "
            f"{len(arch.get('invariants', []))} documented invariants, "
            f"{len(arch.get('risk_zones', []))} risk zones."
        )

    def _identify_affected_subsystems(
        self, arch: Dict[str, Any], task: str
    ) -> List[AffectedSubsystem]:
        affected = []
        keywords = task.lower().split()
        task_words = set(w for w in keywords if len(w) > 3)

        for sd in arch.get("subsystems", []):
            name = sd.get("name", "")
            desc = sd.get("description", "").lower()
            resp_names = [r.get("name", "") for r in sd.get("responsibilities", [])]
            owned_files = []
            for r in sd.get("responsibilities", []):
                owned_files.extend(r.get("owned_files", []))

            score = 0
            for word in task_words:
                if word in name.lower():
                    score += 3
                if word in desc:
                    score += 2
                for rn in resp_names:
                    if word in rn.lower():
                        score += 2
                for of in owned_files:
                    if word in of.lower():
                        score += 1

            if score > 0:
                impact = ImpactType.DIRECT if score >= 3 else ImpactType.INDIRECT
                risk = RiskLevel.LOW if score < 3 else (RiskLevel.MEDIUM if score < 6 else RiskLevel.HIGH)
                affected.append(AffectedSubsystem(
                    name=name,
                    impact_type=impact,
                    risk_level=risk,
                    confidence=min(0.9, 0.3 + score * 0.1),
                    description=f"Keyword match score: {score}",
                    relevant_files=owned_files[:5],
                ))

        affected.sort(key=lambda s: s.confidence, reverse=True)
        return affected[:self.config.max_affected_subsystems]

    def _analyze_impacts(
        self, arch: Dict[str, Any],
        affected: List[AffectedSubsystem],
        task: str
    ) -> List[SubsystemImpact]:
        impacts = []
        affected_names = {s.name for s in affected}

        for s in affected:
            sub_impact = SubsystemImpact(
                subsystem=s.name,
                impact_score=s.confidence,
            )

            for rule in arch.get("boundary_rules", []):
                if rule.get("from_subsystem") == s.name and not rule.get("allowed", True):
                    sub_impact.boundary_violations.append(
                        f"Boundary: {s.name} → {rule.get('to_subsystem')} is forbidden"
                    )

            for inv in arch.get("invariants", []):
                if inv.get("scope") == s.name or inv.get("scope") == "global":
                    sub_impact.invariant_violations.append(inv.get("name", ""))

            if s.relevant_files:
                sub_impact.affected_files = s.relevant_files

            impacts.append(sub_impact)

        for s in arch.get("subsystems", []):
            name = s.get("name", "")
            if name in affected_names:
                continue
            for dep in s.get("dependents", []):
                if dep in affected_names:
                    impacts.append(SubsystemImpact(
                        subsystem=name,
                        impact_score=0.3,
                        affected_files=s.get("responsibilities", [{}])[0].get("owned_files", []) if s.get("responsibilities") else [],
                    ))

        return impacts

    def _select_context(
        self, arch: Dict[str, Any],
        affected: List[AffectedSubsystem]
    ) -> ContextSelection:
        selection = ContextSelection()
        selected = set()
        total_files = 0

        top_level_dirs = [d for d in self.repo_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        source_dirs = [d for d in top_level_dirs if d.name in ("src", "lib", "app")]

        for sd in source_dirs:
            for f in sd.rglob("*.py"):
                total_files += 1

        for s in affected:
            for f in s.relevant_files:
                full_path = self.repo_path / f
                if full_path.exists():
                    selected.add(str(full_path))

        for s in arch.get("subsystems", []):
            if s.get("name") in {a.name for a in affected}:
                for r in s.get("responsibilities", []):
                    for f in r.get("owned_files", []):
                        full_path = self.repo_path / f
                        if full_path.exists():
                            selected.add(str(full_path))

        if not selected and source_dirs:
            for sd in source_dirs:
                for f in sorted(sd.rglob("*.py"))[:20]:
                    selected.add(str(f))

        selection.total_files_available = total_files
        selection.files_selected = len(selected)
        selection.selected_files = sorted(selected)
        selection.subsystems_covered = len({s.name for s in affected})
        selection.estimated_tokens = len(selected) * 200
        selection.rationale = (
            f"Selected {len(selected)} files from {len(affected)} affected subsystems "
            f"based on architecture analysis"
        )

        return selection

    def _select_tests(self, affected: List[AffectedSubsystem]) -> TestSelection:
        selection = TestSelection()
        test_files = list(self.repo_path.rglob("test_*.py")) + list(self.repo_path.rglob("*_test.py"))
        selection.test_files_found = len(test_files)

        relevant = set()
        for s in affected:
            for f in s.relevant_files:
                f_path = Path(f)
                for tf in test_files:
                    if f_path.stem in tf.name:
                        relevant.add(tf)

        selection.tests_relevant = len(relevant)
        if relevant:
            selection.recommended_commands.append("pytest")
            for tf in sorted(relevant)[:5]:
                selection.recommended_commands.append(f"pytest {tf}")
            selection.estimated_runtime_s = len(relevant) * 2

        return selection

    def _generate_plan_steps(
        self, arch: Dict[str, Any],
        affected: List[AffectedSubsystem],
        task: str
    ) -> List[PlanStep]:
        steps = []

        for i, s in enumerate(affected, 1):
            risk = RiskLevel.HIGH if s.risk_level == RiskLevel.HIGH else RiskLevel.MEDIUM
            steps.append(PlanStep(
                step_id=str(i),
                description=f"Modify {s.name} subsystem: {s.description}",
                subsystem_focus=s.name,
                estimated_effort="large" if s.risk_level == RiskLevel.HIGH else "medium",
                risk=risk,
                success_criteria=[
                    f"All tests in {s.name} pass",
                    f"No boundary violations in {s.name}",
                ],
            ))

        if not steps:
            steps.append(PlanStep(
                step_id="1",
                description=f"Implement: {task}",
                risk=RiskLevel.MEDIUM,
                success_criteria=["Task requirements met", "Tests pass"],
            ))

        return steps

    def _assess_overall_risk(
        self, affected: List[AffectedSubsystem],
        impacts: List[SubsystemImpact]
    ) -> RiskLevel:
        high_risk_count = sum(1 for s in affected if s.risk_level == RiskLevel.HIGH)
        boundary_violations = sum(len(i.boundary_violations) for i in impacts)

        if high_risk_count >= 3 or boundary_violations >= 3:
            return RiskLevel.HIGH
        if high_risk_count >= 1 or boundary_violations >= 1:
            return RiskLevel.MEDIUM
        if affected:
            return RiskLevel.LOW
        return RiskLevel.NONE


class BaselinePlanner:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()

    def plan(self, task_description: str) -> PlanResult:
        start = time.time()
        result = PlanResult(task_description=task_description)

        result.affected_subsystems = [AffectedSubsystem(
            name="root",
            impact_type=ImpactType.UNKNOWN,
            risk_level=RiskLevel.MEDIUM,
            confidence=0.3,
            description="No architecture data — treating entire repo as affected",
        )]
        result.plan_steps = [PlanStep(
            step_id="1",
            description=f"Implement: {task_description}",
            risk=RiskLevel.MEDIUM,
            success_criteria=["All tests pass"],
        )]
        result.overall_risk = RiskLevel.MEDIUM
        result.planning_time_ms = (time.time() - start) * 1000
        return result
