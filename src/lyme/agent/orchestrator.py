"""CodingAgent — unified autonomous coding agent orchestrator."""
from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .planner import TaskPlanner, PlanStep, TaskPlan
from .file_selector import FileSelector, FileSelection
from .patch_generator import PatchGenerator, GeneratedPatch
from .test_runner import TestRunner, TestRun, TestResult
from .memory import ExecutionMemory, ExecutionRecord


class AgentStatus(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    SELECTING_FILES = "selecting_files"
    READING_CONTEXT = "reading_context"
    GENERATING_PATCH = "generating_patch"
    APPLYING_PATCH = "applying_patch"
    RUNNING_TESTS = "running_tests"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class AgentConfig:
    repo_path: str = "."
    max_retries: int = 3
    run_tests: bool = True
    dry_run: bool = False
    verbose: bool = False
    model_fn: Optional[Callable] = None


@dataclass
class AgentResult:
    task: str
    status: AgentStatus = AgentStatus.IDLE
    plan: Optional[TaskPlan] = None
    file_selection: Optional[FileSelection] = None
    patches: List[GeneratedPatch] = field(default_factory=list)
    test_runs: List[TestRun] = field(default_factory=list)
    reasoning_log: List[str] = field(default_factory=list)
    execution_records: List[ExecutionRecord] = field(default_factory=list)
    retries: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "retries": self.retries,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "plan": self.plan.to_dict() if self.plan else None,
            "patches": [p.to_dict() for p in self.patches],
            "test_runs": [tr.to_dict() for tr in self.test_runs],
            "reasoning_log": self.reasoning_log[-20:],
            "file_selection": self.file_selection.to_dict() if self.file_selection else None,
        }


class CodingAgent:
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.planner = TaskPlanner()
        self.file_selector = FileSelector(self.config.repo_path)
        self.patch_generator = PatchGenerator(model_fn=self.config.model_fn)
        self.test_runner = TestRunner(self.config.repo_path)
        self.memory = ExecutionMemory(self.config.repo_path)
        self.status = AgentStatus.IDLE
        self._log: List[str] = []

    def _log_step(self, msg: str) -> None:
        self._log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def execute(self, task: str) -> AgentResult:
        start = time.time()
        agent_id = str(uuid.uuid4())[:8]
        result = AgentResult(task=task, agent_id=agent_id)
        self.status = AgentStatus.PLANNING

        try:
            # 1. Plan
            self.status = AgentStatus.PLANNING
            self._log_step(f"Planning: {task}")
            plan = self.planner.plan(task, self.memory)
            result.plan = plan
            result.reasoning_log = self._log.copy()
            self._log_step(f"Plan: {len(plan.steps)} steps, risk={plan.risk_level}")

            # 2. Select files
            self.status = AgentStatus.SELECTING_FILES
            self._log_step("Selecting relevant files...")
            file_sel = self.file_selector.select(task, plan)
            result.file_selection = file_sel
            self._log_step(f"Selected {len(file_sel.primary_files)} primary files, "
                          f"{len(file_sel.context_files)} context files")

            # 3. Read context
            self.status = AgentStatus.READING_CONTEXT
            self._log_step("Reading file context...")
            context = self._read_file_context(file_sel)

            # 4. Generate patches
            self.status = AgentStatus.GENERATING_PATCH
            self._log_step("Generating patch...")
            patches = self.patch_generator.generate(task, file_sel, context)
            result.patches = patches
            self._log_step(f"Generated {len(patches)} patch(es)")

            if self.config.dry_run:
                self.status = AgentStatus.SUCCESS
                result.duration_ms = (time.time() - start) * 1000
                self._log_step("Dry-run complete")
                result.reasoning_log = self._log.copy()
                return result

            # 5. Apply patches
            self.status = AgentStatus.APPLYING_PATCH
            for patch in patches:
                self._apply_patch(patch)
            self._log_step(f"Applied {len(patches)} patch(es)")

            # 6. Run tests
            retries = 0
            if self.config.run_tests:
                while retries <= self.config.max_retries:
                    self.status = AgentStatus.RUNNING_TESTS
                    self._log_step(f"Running tests (attempt {retries + 1})...")
                    test_run = self.test_runner.run(file_sel.test_files)
                    result.test_runs.append(test_run)
                    self._log_step(f"Tests: {test_run.summary.passed} passed, "
                                  f"{test_run.summary.failed} failed")

                    if test_run.summary.failed == 0:
                        self._log_step("All tests passed")
                        break

                    if retries < self.config.max_retries:
                        self.status = AgentStatus.RETRYING
                        retries += 1
                        result.retries = retries
                        self._log_step(f"Retrying ({retries}/{self.config.max_retries})...")
                        # Rollback failed patches
                        for patch in patches:
                            self._rollback_patch(patch)
                        # Regenerate with failure context
                        patches = self.patch_generator.generate(
                            task, file_sel, context,
                            failure_context=test_run.to_dict(),
                        )
                        result.patches = patches
                        for patch in patches:
                            self._apply_patch(patch)
                    else:
                        break

            # 7. Memorize
            self.status = AgentStatus.SUCCESS
            record = ExecutionRecord(
                task=task,
                status="success" if all(
                    tr.summary.failed == 0 for tr in result.test_runs
                ) else "partial",
                patches=[p.to_dict() for p in patches],
                duration_ms=(time.time() - start) * 1000,
            )
            self.memory.store(record)
            result.execution_records = [record]

        except Exception as e:
            self.status = AgentStatus.FAILED
            result.error = str(e)
            self._log_step(f"Failed: {e}")

        result.duration_ms = (time.time() - start) * 1000
        result.status = self.status
        result.reasoning_log = self._log.copy()

        # Save trace
        trace_path = self._save_trace(result)
        result.trace_path = trace_path

        return result

    def _read_file_context(self, file_sel: FileSelection) -> Dict[str, str]:
        context = {}
        for fp in file_sel.primary_files + file_sel.context_files:
            path = Path(self.config.repo_path) / fp
            if path.exists():
                try:
                    context[fp] = path.read_text(errors="replace")[:10000]
                except Exception:
                    context[fp] = ""
        return context

    def _apply_patch(self, patch: GeneratedPatch) -> bool:
        path = Path(self.config.repo_path) / patch.file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(patch.new_content)
        return True

    def _rollback_patch(self, patch: GeneratedPatch) -> bool:
        if patch.original_content is not None:
            path = Path(self.config.repo_path) / patch.file_path
            path.write_text(patch.original_content)
            return True
        return False

    def _save_trace(self, result: AgentResult) -> str:
        trace_dir = Path(self.config.repo_path) / ".lyme" / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / f"agent_{result.agent_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2, default=str))
        return str(path)

    def get_status(self) -> AgentStatus:
        return self.status
