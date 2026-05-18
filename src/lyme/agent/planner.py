"""TaskPlanner — decomposes NL tasks into ordered edit plans."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .memory import ExecutionMemory


class StepType(Enum):
    SEARCH = "search"
    READ = "read"
    EDIT = "edit"
    CREATE = "create"
    DELETE = "delete"
    REFACTOR = "refactor"
    TEST = "test"
    VERIFY = "verify"


@dataclass
class PlanStep:
    step_type: StepType
    description: str
    target_files: List[str] = field(default_factory=list)
    subsystem: str = ""
    risk_level: str = "low"  # low, medium, high
    success_criteria: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type.value,
            "description": self.description,
            "target_files": self.target_files,
            "subsystem": self.subsystem,
            "risk_level": self.risk_level,
            "success_criteria": self.success_criteria,
        }


@dataclass
class TaskPlan:
    task: str
    steps: List[PlanStep] = field(default_factory=list)
    risk_level: str = "low"
    estimated_effort: str = "small"
    reasoning: str = ""

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "risk_level": self.risk_level,
            "estimated_effort": self.estimated_effort,
            "reasoning": self.reasoning,
        }


class TaskPlanner:
    def __init__(self):
        pass

    def plan(self, task: str, memory: ExecutionMemory) -> TaskPlan:
        task_lower = task.lower()
        plan = TaskPlan(task=task)

        keywords = {
            "add": StepType.CREATE,
            "create": StepType.CREATE,
            "new": StepType.CREATE,
            "implement": StepType.CREATE,
            "fix": StepType.EDIT,
            "repair": StepType.EDIT,
            "bug": StepType.EDIT,
            "issue": StepType.EDIT,
            "broken": StepType.EDIT,
            "refactor": StepType.REFACTOR,
            "clean": StepType.REFACTOR,
            "rename": StepType.REFACTOR,
            "delete": StepType.DELETE,
            "remove": StepType.DELETE,
            "test": StepType.TEST,
            "verify": StepType.VERIFY,
        }

        primary_action = StepType.EDIT
        for kw, action in keywords.items():
            if kw in task_lower:
                primary_action = action
                break

        # Build plan steps
        search_step = PlanStep(
            step_type=StepType.SEARCH,
            description=f"Search repository for files related to: {task}",
            risk_level="low",
            success_criteria="Found relevant files",
        )
        plan.add_step(search_step)

        read_step = PlanStep(
            step_type=StepType.READ,
            description="Read and understand the relevant code",
            risk_level="low",
            success_criteria="Understood code structure and logic",
        )
        plan.add_step(read_step)

        if primary_action == StepType.EDIT:
            edit_step = PlanStep(
                step_type=StepType.EDIT,
                description=f"Apply fix for: {task}",
                risk_level="medium",
                success_criteria="Issue resolved without breaking existing functionality",
            )
            plan.add_step(edit_step)
        elif primary_action == StepType.CREATE:
            create_step = PlanStep(
                step_type=StepType.CREATE,
                description=f"Implement new feature: {task}",
                risk_level="medium",
                success_criteria="New code compiles and passes tests",
            )
            plan.add_step(create_step)
        elif primary_action == StepType.REFACTOR:
            refactor_step = PlanStep(
                step_type=StepType.REFACTOR,
                description=f"Refactor: {task}",
                risk_level="high",
                success_criteria="Same behavior, cleaner code, all tests pass",
            )
            plan.add_step(refactor_step)
        elif primary_action == StepType.DELETE:
            delete_step = PlanStep(
                step_type=StepType.DELETE,
                description=f"Remove: {task}",
                risk_level="high",
                success_criteria="No references remain, tests pass",
            )
            plan.add_step(delete_step)
        elif primary_action == StepType.TEST:
            test_plan_step = PlanStep(
                step_type=StepType.TEST,
                description=f"Add/update tests for: {task}",
                risk_level="low",
                success_criteria="Tests pass",
            )
            plan.add_step(test_plan_step)

        verify_step = PlanStep(
            step_type=StepType.VERIFY,
            description="Verify changes with tests",
            risk_level="low",
            success_criteria="All existing and new tests pass",
        )
        plan.add_step(verify_step)

        # Risk assessment
        high_risk_keywords = ["delete", "refactor", "rename", "migrate", "rewrite"]
        plan.risk_level = "high" if any(kw in task_lower for kw in high_risk_keywords) else "medium"

        # Effort estimation
        effort_keywords = {
            "large": ["large", "complex", "major", "significant", "multiple"],
            "medium": ["update", "change", "modify", "several"],
        }
        plan.estimated_effort = "small"
        for effort, words in effort_keywords.items():
            if any(w in task_lower for w in words):
                plan.estimated_effort = effort
                break

        # Consider past failures from memory
        similar_records = memory.search(task)[:3]
        if similar_records:
            failed = [r for r in similar_records if r.status == "failed"]
            if failed:
                plan.reasoning = f"Previous similar tasks had failures. Adjusting plan."
                plan.risk_level = "high"

        return plan
