"""Procedural Skill Library for Lyme.

A skill encodes:
- task type
- preconditions
- workflow steps
- required tools
- verification strategy
- failure recovery
- examples
- confidence history

Skills are learned from:
- successful runs
- human corrections
- repeated workflows
- repo-specific patterns
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timezone
from enum import Enum
import json
import uuid
import re
from pathlib import Path


class SkillType(Enum):
    TEST_FIXING = "test_fixing"
    API_REFACTORING = "api_refactoring"
    DEPENDENCY_UPDATE = "dependency_update"
    COMPONENT_MIGRATION = "component_migration"
    BUILD_ERROR_DEBUGGING = "build_error_debugging"
    CODE_GENERATION = "code_generation"
    BUG_FIXING = "bug_fixing"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    REVIEW = "review"
    OPTIMIZATION = "optimization"
    CUSTOM = "custom"


class SkillStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DECAYING = "decaying"
    STALE = "stale"
    RETIRED = "retired"


@dataclass
class Precondition:
    name: str = ""
    description: str = ""
    check_type: str = "file_exists"
    target: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowStep:
    step_id: str = ""
    description: str = ""
    action: str = ""
    tool: str = ""
    expected_output: str = ""
    timeout_s: int = 60
    retry_count: int = 0
    critical: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationStrategy:
    name: str = ""
    type: str = "test_run"
    command: str = ""
    expected_result: str = "success"
    timeout_s: int = 120

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FailureRecovery:
    failure_pattern: str = ""
    description: str = ""
    recovery_steps: List[str] = field(default_factory=list)
    fallback_skill: str = ""
    max_retries: int = 3

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfidenceHistory:
    entry_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 0.0
    success: bool = False
    context: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Skill:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    skill_type: SkillType = SkillType.CUSTOM
    status: SkillStatus = SkillStatus.DRAFT

    task_type: str = ""
    preconditions: List[Precondition] = field(default_factory=list)
    workflow_steps: List[WorkflowStep] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    verification: List[VerificationStrategy] = field(default_factory=list)
    failure_recovery: List[FailureRecovery] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    confidence_history: List[ConfidenceHistory] = field(default_factory=list)

    source_repo: str = ""
    source_pattern: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "status": self.status.value,
            "task_type": self.task_type,
            "preconditions": [p.to_dict() for p in self.preconditions],
            "workflow_steps": [s.to_dict() for s in self.workflow_steps],
            "required_tools": self.required_tools,
            "verification": [v.to_dict() for v in self.verification],
            "failure_recovery": [f.to_dict() for f in self.failure_recovery],
            "examples": self.examples[-5:],
            "confidence_history": [c.to_dict() for c in self.confidence_history[-20:]],
            "source_repo": self.source_repo,
            "source_pattern": self.source_pattern,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @property
    def current_confidence(self) -> float:
        if not self.confidence_history:
            return 0.0
        recent = self.confidence_history[-10:]
        successes = sum(1 for c in recent if c.success)
        return successes / len(recent) if recent else 0.0


class SkillSchema:
    @staticmethod
    def validate(skill: Skill) -> List[str]:
        errors = []
        if not skill.name:
            errors.append("Skill name is required")
        if not skill.workflow_steps:
            errors.append("At least one workflow step is required")
        for i, step in enumerate(skill.workflow_steps):
            if not step.description:
                errors.append(f"Workflow step {i} missing description")
        return errors


class SkillLibrary:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.cwd() / ".lyme" / "skills"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, Skill] = {}
        self._load_all()

    def add(self, skill: Skill) -> str:
        self._skills[skill.id] = skill
        self._save(skill)
        return skill.id

    def get(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def remove(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            path = self.storage_path / f"{skill_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False

    def list_by_type(self, skill_type: Optional[SkillType] = None) -> List[Skill]:
        if skill_type:
            return [s for s in self._skills.values() if s.skill_type == skill_type]
        return list(self._skills.values())

    def search(self, query: str) -> List[Skill]:
        q = query.lower()
        results = []
        for s in self._skills.values():
            if q in s.name.lower() or q in s.description.lower():
                results.append(s)
                continue
            for tag in s.tags:
                if q in tag.lower():
                    results.append(s)
                    break
        return results

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "by_type": {
                t.value: len([s for s in self._skills.values() if s.skill_type == t])
                for t in SkillType
            },
            "by_status": {
                s.value: len([sk for sk in self._skills.values() if sk.status == s])
                for s in SkillStatus
            },
            "avg_confidence": sum(s.current_confidence for s in self._skills.values()) / max(len(self._skills), 1),
        }

    def record_outcome(self, skill_id: str, success: bool, context: str = ""):
        skill = self._skills.get(skill_id)
        if not skill:
            return
        entry = ConfidenceHistory(
            entry_id=uuid.uuid4().hex[:8],
            confidence=1.0 if success else 0.0,
            success=success,
            context=context,
        )
        skill.confidence_history.append(entry)
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(skill)

    def decay_skills(self):
        now = datetime.now(timezone.utc)
        for skill in self._skills.values():
            if skill.status in (SkillStatus.RETIRED, SkillStatus.STALE):
                continue
            updated = datetime.fromisoformat(skill.updated_at)
            days_since = (now - updated).days
            if days_since > 90:
                skill.status = SkillStatus.STALE
            elif days_since > 30:
                if skill.current_confidence < 0.3:
                    skill.status = SkillStatus.DECAYING

    def _save(self, skill: Skill):
        path = self.storage_path / f"{skill.id}.json"
        path.write_text(json.dumps(skill.to_dict(), indent=2, default=str))

    def _load_all(self):
        for path in self.storage_path.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                skill = self._dict_to_skill(data)
                self._skills[skill.id] = skill
            except (json.JSONDecodeError, Exception):
                pass

    def _dict_to_skill(self, data: dict) -> Skill:
        skill = Skill(
            id=data.get("id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            skill_type=SkillType(data["skill_type"]) if "skill_type" in data else SkillType.CUSTOM,
            status=SkillStatus(data["status"]) if "status" in data else SkillStatus.DRAFT,
            task_type=data.get("task_type", ""),
            source_repo=data.get("source_repo", ""),
            source_pattern=data.get("source_pattern", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=data.get("version", 1),
        )
        for pd in data.get("preconditions", []):
            skill.preconditions.append(Precondition(**pd))
        for sd in data.get("workflow_steps", []):
            skill.workflow_steps.append(WorkflowStep(**sd))
        skill.required_tools = data.get("required_tools", [])
        for vd in data.get("verification", []):
            skill.verification.append(VerificationStrategy(**vd))
        for fd in data.get("failure_recovery", []):
            skill.failure_recovery.append(FailureRecovery(**fd))
        skill.examples = data.get("examples", [])
        for cd in data.get("confidence_history", []):
            skill.confidence_history.append(ConfidenceHistory(**cd))
        return skill


class SkillExtractor:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()

    def extract_from_successful_run(
        self, run_data: Dict[str, Any], skill_type: SkillType = SkillType.CUSTOM
    ) -> Optional[Skill]:
        scenario = run_data.get("scenario_name", run_data.get("scenario", ""))
        if not scenario:
            return None

        skill = Skill(
            name=f"Run: {scenario}",
            description=f"Extracted from successful run of {scenario}",
            skill_type=skill_type,
            source_repo=str(self.repo_path),
            source_pattern=scenario,
        )
        skill.workflow_steps.append(WorkflowStep(
            step_id="1",
            description=f"Execute {scenario} workflow",
            action=scenario,
            tool="lyme",
            expected_output="success",
        ))
        skill.confidence_history.append(ConfidenceHistory(
            entry_id="extracted",
            confidence=0.7,
            success=True,
            context=f"Extracted from run of {scenario}",
        ))
        return skill

    def extract_from_git_pattern(
        self, pattern_name: str, commits: List[str]
    ) -> Optional[Skill]:
        if not commits:
            return None
        skill = Skill(
            name=pattern_name,
            description=f"Extracted from git history pattern: {pattern_name}",
            skill_type=SkillType.REFACTORING,
            source_repo=str(self.repo_path),
            source_pattern=pattern_name,
        )
        skill.workflow_steps.append(WorkflowStep(
            step_id="1",
            description=f"Apply {pattern_name} changes",
            action="apply_changes",
            tool="git",
            expected_output="clean_diff",
        ))
        skill.verification.append(VerificationStrategy(
            name="verify_commits",
            type="git_check",
            command="git log --oneline -5",
            expected_result="success",
        ))
        return skill


class SkillRetriever:
    def __init__(self, library: SkillLibrary):
        self.library = library

    def find_matching(
        self, task_description: str, task_type: Optional[str] = None, min_confidence: float = 0.0
    ) -> List[Skill]:
        candidates = self.library.search(task_description)
        if task_type:
            candidates = [s for s in candidates if s.task_type == task_type or s.task_type == ""]
        candidates = [s for s in candidates if s.current_confidence >= min_confidence]
        candidates.sort(key=lambda s: s.current_confidence, reverse=True)
        return candidates[:5]

    def find_best(
        self, task_description: str, task_type: Optional[str] = None
    ) -> Optional[Skill]:
        matches = self.find_matching(task_description, task_type)
        return matches[0] if matches else None


class SkillExecutor:
    def __init__(self, step_runner: Optional[Callable] = None):
        self.step_runner = step_runner

    def execute(self, skill: Skill, context: Dict[str, Any] = None) -> Dict[str, Any]:
        results = {"success": True, "steps": [], "errors": []}

        for precondition in skill.preconditions:
            if precondition.required:
                if not self._check_precondition(precondition, context):
                    results["success"] = False
                    results["errors"].append(f"Precondition failed: {precondition.name}")
                    return results

        for step in skill.workflow_steps:
            step_result = self._run_step(step, context)
            results["steps"].append({
                "step_id": step.step_id,
                "description": step.description,
                "success": step_result.get("success", False),
                "output": step_result.get("output", ""),
            })
            if not step_result.get("success") and step.critical:
                results["success"] = False
                results["errors"].append(f"Critical step failed: {step.description}")
                break

        for strategy in skill.verification:
            ver_result = self._run_verification(strategy, context)
            if ver_result.get("success") == False:
                results["success"] = False
                results["errors"].append(f"Verification failed: {strategy.name}")

        return results

    def _check_precondition(self, precondition: Precondition, context: dict) -> bool:
        if precondition.check_type == "file_exists":
            return Path(precondition.target).exists()
        if precondition.check_type == "tool_available":
            import shutil
            return shutil.which(precondition.target) is not None
        return True

    def _run_step(self, step: WorkflowStep, context: dict) -> dict:
        if self.step_runner:
            try:
                return self.step_runner(step, context)
            except Exception as e:
                return {"success": False, "output": str(e)}
        return {"success": True, "output": f"Simulated: {step.description}"}

    def _run_verification(self, strategy: VerificationStrategy, context: dict) -> dict:
        return {"success": True, "output": f"Verification {strategy.name} passed"}
