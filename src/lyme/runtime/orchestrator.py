import os
import re
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pathlib import Path


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ToolType(str, Enum):
    SHELL = "shell"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    SEARCH = "search"
    CODE_READ = "code_read"
    TEST = "test"
    DIFF = "diff"
    MODEL_INFERENCE = "model_inference"
    MEMORY_QUERY = "memory_query"
    MEMORY_STORE = "memory_store"


@dataclass
class Step:
    id: str = ""
    action: str = ""
    tool: str = ToolType.SHELL
    params: dict = field(default_factory=dict)
    expected_outcome: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 2
    duration_ms: float = 0.0


@dataclass
class TaskPlan:
    id: str = ""
    goal: str = ""
    steps: List[Step] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    context_budget: int = 128000
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def add_step(self, step: Step) -> None:
        step.id = step.id or uuid.uuid4().hex[:8]
        self.steps.append(step)
        self.updated_at = time.time()

    def current_step(self) -> Optional[Step]:
        for step in self.steps:
            if step.status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.RETRYING):
                return step
        return None

    def is_complete(self) -> bool:
        return all(s.status == StepStatus.SUCCESS for s in self.steps)

    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.SUCCESS)
        return completed / len(self.steps)

    def estimated_tokens(self) -> int:
        total = 0
        total += len(self.goal) * 2
        for step in self.steps:
            total += len(step.action) * 2
            total += len(str(step.params)) * 1
        return total


class LocalOrchestrator:
    def __init__(self, max_retries: int = 2, context_budget: int = 128000):
        self.max_retries = max_retries
        self.context_budget = context_budget
        self._plans: Dict[str, TaskPlan] = {}
        self._active_plan: Optional[TaskPlan] = None
        self._tool_registry: Dict[str, Callable] = {}
        self._logger = logging.getLogger("lyme.orchestrator")

    def plan_task(self, goal: str, context: Optional[str] = None,
                  metadata: Optional[dict] = None) -> TaskPlan:
        plan_id = uuid.uuid4().hex[:12]
        plan = TaskPlan(
            id=plan_id,
            goal=goal,
            status=TaskStatus.PENDING,
            context_budget=self.context_budget,
            created_at=time.time(),
            updated_at=time.time(),
            metadata=metadata or {},
        )

        subtasks = self._decompose(goal, context or "")

        for i, subtask in enumerate(subtasks):
            tool = self._select_tool(subtask)
            step = Step(
                id=f"{plan_id}_{i:04d}",
                action=subtask["description"],
                tool=tool,
                params=subtask.get("params", {}),
                expected_outcome=subtask.get("expected_outcome", ""),
                max_retries=self.max_retries,
            )
            plan.add_step(step)

        plan.context_budget = self._estimate_context_budget(plan)

        self._plans[plan_id] = plan
        self._active_plan = plan
        return plan

    def _decompose(self, goal: str, context: str) -> List[dict]:
        subtasks: List[dict] = []

        patterns = {
            "read": r"(read|open|show|display|view|cat|print)\s+(file|code|source|content)",
            "edit": r"(edit|change|update|modify|rewrite|refactor)\s+(file|code|function|class)",
            "search": r"(search|find|grep|locate|look\s+up)\s+",
            "test": r"(test|run\s+test|check|verify|validate)",
            "shell": r"(run|execute|install|build|compile|start|deploy)",
            "diff": r"(diff|compare|changes|what\s+changed)",
            "write": r"(write|create|generate|make|new)\s+(file|script|module|test|doc)",
        }

        matched = False
        for tool_type, pattern in patterns.items():
            if re.search(pattern, goal, re.IGNORECASE):
                matched = True
                subtasks.append(self._build_subtask(tool_type, goal, context))

        if not matched:
            subtasks.append(self._build_subtask("default", goal, context))

        return subtasks

    def _build_subtask(self, tool_type: str, goal: str, context: str) -> dict:
        base: Dict[str, Any] = {
            "description": goal,
            "tool": tool_type,
            "params": {"goal": goal},
            "expected_outcome": "Completed successfully",
        }

        if tool_type == "read":
            base["params"]["path"] = self._extract_path(goal)
            base["expected_outcome"] = "File contents retrieved"
        elif tool_type == "edit":
            base["params"]["path"] = self._extract_path(goal)
            base["expected_outcome"] = "File edited successfully"
        elif tool_type == "write":
            base["params"]["path"] = self._extract_path(goal) or "new_file"
            base["expected_outcome"] = "File created successfully"
        elif tool_type == "search":
            query = goal.replace("search", "").replace("find", "").replace("grep", "").strip()
            base["params"]["query"] = query
            base["expected_outcome"] = "Search results returned"
        elif tool_type == "test":
            base["params"]["pattern"] = self._extract_test_pattern(goal)
            base["expected_outcome"] = "Tests executed with results"
        elif tool_type == "diff":
            base["expected_outcome"] = "Differences computed"
        elif tool_type == "shell":
            base["expected_outcome"] = "Command executed successfully"

        if context and len(context) < self.context_budget:
            base["params"]["context"] = context[:self.context_budget]

        return base

    def _extract_path(self, text: str) -> str:
        path_match = re.search(r'["\']([^"\']+)["\']', text)
        if path_match:
            return path_match.group(1)
        word_match = re.search(r'(?:file|path|script)\s+(\S+)', text, re.IGNORECASE)
        if word_match:
            return word_match.group(1)
        return ""

    def _extract_test_pattern(self, text: str) -> str:
        pattern_match = re.search(r'(?:pattern|test|suite)[=:\s]+(\S+)', text, re.IGNORECASE)
        return pattern_match.group(1) if pattern_match else "test_*.py"

    def _select_tool(self, subtask: dict) -> str:
        tool_map = {
            "read": ToolType.FILE_READ,
            "edit": ToolType.FILE_EDIT,
            "search": ToolType.SEARCH,
            "test": ToolType.TEST,
            "shell": ToolType.SHELL,
            "diff": ToolType.DIFF,
            "write": ToolType.FILE_WRITE,
            "code_read": ToolType.CODE_READ,
            "default": ToolType.MODEL_INFERENCE,
        }
        return tool_map.get(subtask.get("tool", "default"), ToolType.SHELL)

    def _estimate_context_budget(self, plan: TaskPlan) -> int:
        estimated = plan.estimated_tokens()
        return min(max(estimated + 4096, 8192), self.context_budget)

    def execute_step(self, plan_id: str, step_index: int,
                     tool_executor: Callable[[Step], Dict[str, Any]]) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        if step_index < 0 or step_index >= len(plan.steps):
            raise IndexError(f"Step index {step_index} out of range")

        step = plan.steps[step_index]
        step.status = StepStatus.RUNNING
        plan.status = TaskStatus.RUNNING
        plan.updated_at = time.time()

        start = time.time()
        try:
            result = tool_executor(step)
            step.duration_ms = (time.time() - start) * 1000
            step.result = result
            step.status = StepStatus.SUCCESS
            plan.updated_at = time.time()
            return result
        except Exception as e:
            step.duration_ms = (time.time() - start) * 1000
            step.error = str(e)

            if step.retries < step.max_retries:
                step.retries += 1
                step.status = StepStatus.RETRYING
                self._logger.info(f"Retrying step {step.id} ({step.retries}/{step.max_retries})")
                return self.execute_step(plan_id, step_index, tool_executor)
            else:
                step.status = StepStatus.FAILED
                plan.status = TaskStatus.FAILED
                plan.updated_at = time.time()
                raise

    def execute_plan(self, plan_id: str,
                     tool_executor: Callable[[Step], Dict[str, Any]]) -> TaskPlan:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        plan.status = TaskStatus.RUNNING
        self._active_plan = plan

        for i, step in enumerate(plan.steps):
            if step.status == StepStatus.SUCCESS:
                continue

            if i > 0:
                prev = plan.steps[i - 1]
                if prev.status == StepStatus.FAILED and not prev.retries < prev.max_retries:
                    step.status = StepStatus.SKIPPED
                    continue

            self.execute_step(plan_id, i, tool_executor)

        plan.status = TaskStatus.SUCCESS if plan.is_complete() else TaskStatus.FAILED
        plan.updated_at = time.time()
        self._active_plan = None
        return plan

    def register_tool(self, name: str, executor: Callable) -> None:
        self._tool_registry[name] = executor

    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        return self._plans.get(plan_id)

    def get_active_plan(self) -> Optional[TaskPlan]:
        return self._active_plan

    def list_plans(self, status: Optional[TaskStatus] = None) -> List[TaskPlan]:
        if status:
            return [p for p in self._plans.values() if p.status == status]
        return list(self._plans.values())

    def abandon_plan(self, plan_id: str) -> None:
        plan = self._plans.get(plan_id)
        if plan:
            plan.status = TaskStatus.ABANDONED
            for step in plan.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.SKIPPED
            plan.updated_at = time.time()
            if self._active_plan and self._active_plan.id == plan_id:
                self._active_plan = None

    def create_plan_from_template(self, template: Dict[str, Any]) -> TaskPlan:
        plan = TaskPlan(
            id=uuid.uuid4().hex[:12],
            goal=template.get("goal", ""),
            context_budget=template.get("context_budget", self.context_budget),
            created_at=time.time(),
            updated_at=time.time(),
            metadata=template.get("metadata", {}),
        )
        for tstep in template.get("steps", []):
            step = Step(
                action=tstep.get("action", ""),
                tool=tstep.get("tool", ToolType.SHELL),
                params=tstep.get("params", {}),
                expected_outcome=tstep.get("expected_outcome", ""),
                max_retries=tstep.get("max_retries", self.max_retries),
            )
            plan.add_step(step)
        self._plans[plan.id] = plan
        return plan
