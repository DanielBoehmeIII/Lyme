"""Skill Transfer Across Repositories.

Investigate whether Lyme can transfer skills between repositories.
Examples:
- fixing failing tests
- refactoring API routes
- updating dependencies
- migrating components
- debugging build errors

The system should:
- identify when a skill applies
- adapt it to a new repo
- estimate mismatch risk
- avoid overgeneralization
- learn transfer failures
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import json
import uuid
from pathlib import Path


class TransferRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TransferOutcome(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    NOT_ATTEMPTED = "not_attempted"


@dataclass
class MismatchRisk:
    category: str = ""
    description: str = ""
    severity: TransferRisk = TransferRisk.LOW
    source_value: str = ""
    target_value: str = ""
    mitigation: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "mitigation": self.mitigation,
        }


@dataclass
class TransferResult:
    skill_id: str = ""
    skill_name: str = ""
    source_repo: str = ""
    target_repo: str = ""
    outcome: TransferOutcome = TransferOutcome.NOT_ATTEMPTED
    risks: List[MismatchRisk] = field(default_factory=list)
    adaptations_made: List[str] = field(default_factory=list)
    success_score: float = 0.0
    confidence: float = 0.0
    error_message: str = ""
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "outcome": self.outcome.value,
            "risks": [r.to_dict() for r in self.risks],
            "adaptations_made": self.adaptations_made,
            "success_score": self.success_score,
            "confidence": self.confidence,
            "error_message": self.error_message,
            "completed_at": self.completed_at,
        }


@dataclass
class TransferReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_repo: str = ""
    target_repo: str = ""
    transfer_results: List[TransferResult] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    failure_insights: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "generated_at": self.generated_at,
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "transfer_results": [r.to_dict() for r in self.transfer_results],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "failure_insights": self.failure_insights,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Skill Transfer Report")
        lines.append(f"")
        lines.append(f"**Source**: {self.source_repo}")
        lines.append(f"**Target**: {self.target_repo}")
        lines.append(f"**Generated**: {self.generated_at}")
        lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"{self.summary}")
        lines.append(f"")

        if self.transfer_results:
            successes = sum(1 for r in self.transfer_results if r.outcome == TransferOutcome.SUCCESS)
            failures = sum(1 for r in self.transfer_results if r.outcome == TransferOutcome.FAILURE)
            lines.append(f"**Transfers**: {successes} success, {failures} failure / {len(self.transfer_results)} total")
            lines.append(f"")

            for r in self.transfer_results:
                icon = {
                    TransferOutcome.SUCCESS: "✓",
                    TransferOutcome.PARTIAL: "~",
                    TransferOutcome.FAILURE: "✗",
                    TransferOutcome.NOT_ATTEMPTED: "○",
                }.get(r.outcome, "?")

                high_risks = [x for x in r.risks if x.severity in (TransferRisk.HIGH, TransferRisk.VERY_HIGH)]
                risk_str = f" ({len(high_risks)} high risks)" if high_risks else ""

                lines.append(f"- {icon} **{r.skill_name}**{risk_str}")
                lines.append(f"  - Score: {r.success_score:.2f}, Confidence: {r.confidence:.0%}")
                if r.adaptations_made:
                    for a in r.adaptations_made[:3]:
                        lines.append(f"  - Adapted: {a}")
                if r.error_message:
                    lines.append(f"  - Error: {r.error_message}")
            lines.append(f"")

        if self.recommendations:
            lines.append(f"## Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
            lines.append(f"")

        if self.failure_insights:
            lines.append(f"## Failure Insights")
            for f in self.failure_insights:
                lines.append(f"- {f}")
            lines.append(f"")

        return "\n".join(lines)


class SkillTransferEngine:
    def __init__(self, skills_library_path: Optional[Path] = None):
        self.skills_path = skills_library_path or Path.cwd() / ".lyme" / "skills"

    def estimate_transfer_risk(
        self, skill: Any, source_repo: Path, target_repo: Path
    ) -> Tuple[List[MismatchRisk], TransferRisk]:
        risks = []

        source_pyproject = source_repo / "pyproject.toml"
        target_pyproject = target_repo / "pyproject.toml"
        if source_pyproject.exists() and target_pyproject.exists():
            try:
                src_python = self._read_python_version(source_pyproject)
                tgt_python = self._read_python_version(target_pyproject)
                if src_python and tgt_python and src_python != tgt_python:
                    risks.append(MismatchRisk(
                        category="python_version",
                        description=f"Python version mismatch: {src_python} vs {tgt_python}",
                        severity=TransferRisk.MEDIUM,
                        source_value=src_python,
                        target_value=tgt_python,
                        mitigation="Check for version-specific syntax or API changes",
                    ))
            except Exception:
                pass

        source_tests = list(source_repo.rglob("test_*.py")) + list(source_repo.rglob("*_test.py"))
        target_tests = list(target_repo.rglob("test_*.py")) + list(target_repo.rglob("*_test.py"))
        if len(source_tests) > 0 and len(target_tests) == 0:
            risks.append(MismatchRisk(
                category="test_framework",
                description="Target repo has no test files",
                severity=TransferRisk.HIGH,
                source_value=f"{len(source_tests)} test files",
                target_value="0 test files",
                mitigation="Skill may need adaptation to target's test framework",
            ))

        source_extensions = self._get_file_extensions(source_repo)
        target_extensions = self._get_file_extensions(target_repo)
        if source_extensions and target_extensions:
            common = source_extensions & target_extensions
            if len(common) < len(source_extensions) / 2:
                risks.append(MismatchRisk(
                    category="language_mismatch",
                    description="Significant language/tech stack mismatch",
                    severity=TransferRisk.VERY_HIGH,
                    source_value=str(sorted(source_extensions)[:5]),
                    target_value=str(sorted(target_extensions)[:5]),
                    mitigation="Skill is unlikely to transfer directly",
                ))

        overall_risk = TransferRisk.LOW
        if risks:
            highest = max(r.severity for r in risks)
            severity_order = [TransferRisk.LOW, TransferRisk.MEDIUM, TransferRisk.HIGH, TransferRisk.VERY_HIGH]
            overall_risk = highest

        return risks, overall_risk

    def transfer_skill(
        self, skill: Any, target_repo: Path,
        auto_adapt: bool = True
    ) -> TransferResult:
        from ..skills.skill_library import Skill as SkillObj
        source_repo = Path(getattr(skill, 'source_repo', '.'))

        result = TransferResult(
            skill_id=skill.id,
            skill_name=skill.name,
            source_repo=str(source_repo),
            target_repo=str(target_repo),
        )

        risks, overall_risk = self.estimate_transfer_risk(skill, source_repo, target_repo)
        result.risks = risks

        if overall_risk in (TransferRisk.VERY_HIGH, TransferRisk.HIGH) and not auto_adapt:
            result.outcome = TransferOutcome.NOT_ATTEMPTED
            result.error_message = f"Transfer risk too high ({overall_risk.value}) and auto_adapt disabled"
            result.confidence = 0.1
            return result

        if overall_risk == TransferRisk.VERY_HIGH:
            result.outcome = TransferOutcome.FAILURE
            result.error_message = "Language/stack mismatch prevents transfer"
            result.confidence = 0.05
            result.success_score = 0.0
            return result

        adaptations = []
        if isinstance(skill, SkillObj):
            for step in skill.workflow_steps:
                adapted = False
                step_dir = target_repo / "src"
                if "src" in step.action and step_dir.exists():
                    adapted = True
                if adapted:
                    adaptations.append(f"Adapted step {step.step_id}: {step.description}")

        result.adaptations_made = adaptations

        num_high_risks = sum(1 for r in risks if r.severity in (TransferRisk.HIGH, TransferRisk.VERY_HIGH))
        if num_high_risks > 0:
            result.success_score = 0.3
            result.confidence = 0.3
            result.outcome = TransferOutcome.PARTIAL
        else:
            result.success_score = 0.8
            result.confidence = 0.7
            result.outcome = TransferOutcome.SUCCESS

        return result

    def transfer_multiple(
        self, skills: List[Any], target_repo: Path
    ) -> TransferReport:
        target_name = target_repo.name if target_repo else "unknown"
        report = TransferReport(
            source_repo="(multiple)",
            target_repo=str(target_repo),
        )

        results = []
        for skill in skills:
            result = self.transfer_skill(skill, target_repo)
            results.append(result)
        report.transfer_results = results

        successes = sum(1 for r in results if r.outcome == TransferOutcome.SUCCESS)
        total = len(results)
        report.summary = f"Transferred {successes}/{total} skills to {target_name}"

        for r in results:
            if r.outcome == TransferOutcome.FAILURE:
                report.failure_insights.append(
                    f"Skill '{r.skill_name}' failed: {r.error_message}"
                )

        successful_transfers = [r for r in results if r.outcome == TransferOutcome.SUCCESS]
        if successful_transfers:
            report.recommendations.append(
                f"Skills with highest transfer confidence can be applied immediately"
            )
        partial = [r for r in results if r.outcome == TransferOutcome.PARTIAL]
        if partial:
            for p in partial:
                report.recommendations.append(
                    f"Skill '{p.skill_name}' needs adaptation before full transfer"
                )

        return report

    def learn_transfer_failure(self, result: TransferResult, notes: str = ""):
        failure_path = self.skills_path / "transfer_failures.jsonl"
        self.skills_path.mkdir(parents=True, exist_ok=True)
        with open(failure_path, "a") as f:
            entry = result.to_dict()
            entry["notes"] = notes
            f.write(json.dumps(entry) + "\n")

    def _read_python_version(self, pyproject_path: Path) -> Optional[str]:
        import re
        content = pyproject_path.read_text()
        m = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
        return m.group(1) if m else None

    def _get_file_extensions(self, repo_path: Path) -> set:
        extensions = set()
        for f in repo_path.rglob("*"):
            if f.is_file() and f.suffix:
                extensions.add(f.suffix.lower())
        return extensions


class TransferExperiment:
    def __init__(self, engine: SkillTransferEngine):
        self.engine = engine

    def run_cross_repo_experiment(
        self, source_repo: Path, target_repo: Path
    ) -> TransferReport:
        from ..skills.skill_library import SkillLibrary
        lib = SkillLibrary(self.engine.skills_path)
        skills = lib.list_by_type()
        if not skills:
            skills = self._generate_demo_skills(source_repo)
            for s in skills:
                lib.add(s)
        return self.engine.transfer_multiple(skills, target_repo)

    def _generate_demo_skills(self, repo: Path) -> list:
        from ..skills.skill_library import Skill, SkillType, WorkflowStep, Precondition
        skills = []

        s1 = Skill(
            name="fix_failing_tests",
            description="Fix failing tests by examining error output and applying targeted fixes",
            skill_type=SkillType.TEST_FIXING,
            task_type="test_fixing",
            source_repo=str(repo),
        )
        s1.preconditions.append(Precondition(name="tests_exist", description="Test files exist", check_type="file_exists", target="tests"))
        s1.workflow_steps.append(WorkflowStep(step_id="1", description="Run tests to find failures", action="pytest", tool="pytest", expected_output="test_report"))
        s1.workflow_steps.append(WorkflowStep(step_id="2", description="Analyze failure output", action="analyze", tool="lyme", expected_output="failure_analysis"))
        s1.workflow_steps.append(WorkflowStep(step_id="3", description="Apply fix to test or source", action="fix", tool="lyme", expected_output="patch"))
        s1.workflow_steps.append(WorkflowStep(step_id="4", description="Verify fix", action="pytest", tool="pytest", expected_output="passing"))
        skills.append(s1)

        s2 = Skill(
            name="refactor_api_routes",
            description="Refactor API route definitions to new pattern",
            skill_type=SkillType.API_REFACTORING,
            task_type="api_refactoring",
            source_repo=str(repo),
        )
        s2.preconditions.append(Precondition(name="api_files", description="API route files exist", check_type="file_exists", target="src/api"))
        s2.workflow_steps.append(WorkflowStep(step_id="1", description="Identify current route patterns", action="grep", tool="grep", expected_output="route_list"))
        s2.workflow_steps.append(WorkflowStep(step_id="2", description="Create new route structure", action="refactor", tool="lyme", expected_output="new_routes"))
        s2.workflow_steps.append(WorkflowStep(step_id="3", description="Update imports and references", action="update", tool="lyme", expected_output="updated_imports"))
        skills.append(s2)

        return skills
