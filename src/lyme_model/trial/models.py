"""Data models for the trial harness."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path


class TaskType(Enum):
    FIX_FAILING_TEST = "fix_failing_test"
    IMPLEMENT_FEATURE = "implement_feature"
    REFACTOR_MODULE = "refactor_module"
    UPDATE_DEPENDENCY = "update_dependency"
    ADD_DOCS = "add_docs"


class TrialStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class Verdict(Enum):
    PASS = "pass"
    FAIL = "fail"
    AMBIGUOUS = "ambiguous"


@dataclass
class SeededTask:
    id: str
    title: str
    repo_url: str
    repo_path: str
    task_type: TaskType
    difficulty: str
    description: str
    acceptance_criteria: list[str]
    estimated_time_minutes: int
    expected_files: list[str]
    setup_command: str
    test_command: str
    hints: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "repo_url": self.repo_url,
            "repo_path": self.repo_path,
            "task_type": self.task_type.value,
            "difficulty": self.difficulty,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "estimated_time_minutes": self.estimated_time_minutes,
            "expected_files": self.expected_files,
            "setup_command": self.setup_command,
            "test_command": self.test_command,
            "hints": self.hints,
            "tags": self.tags,
        }


@dataclass
class TrialTask:
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    repo_url: str
    repo_path: str
    task_type: TaskType


@dataclass
class CommandRun:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timestamp: str


@dataclass
class FileChange:
    path: str
    change_type: str
    diff: str
    lines_added: int
    lines_removed: int


@dataclass
class TrialResult:
    trial_id: str
    task_id: str
    title: str
    status: TrialStatus
    verdict: Optional[Verdict]
    starting_commit: str
    task_prompt: str
    files_touched: list[str]
    commands_run: list[CommandRun]
    failures: list[str]
    final_diff: str
    test_results: dict
    duration_s: float
    timestamp: str
    error: Optional[str] = None
    file_changes: list[FileChange] = field(default_factory=list)
    agent_log: list[str] = field(default_factory=list)
    score: float = 0.0
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status.value,
            "verdict": self.verdict.value if self.verdict else None,
            "starting_commit": self.starting_commit,
            "task_prompt": self.task_prompt,
            "files_touched": self.files_touched,
            "commands_run": [
                {"command": c.command, "exit_code": c.exit_code,
                 "stdout_preview": c.stdout[:200], "stderr_preview": c.stderr[:200],
                 "duration_s": c.duration_s, "timestamp": c.timestamp}
                for c in self.commands_run
            ],
            "failures": self.failures,
            "final_diff": self.final_diff,
            "test_results": self.test_results,
            "duration_s": self.duration_s,
            "timestamp": self.timestamp,
            "error": self.error,
            "score": self.score,
            "file_changes": [
                {"path": fc.path, "change_type": fc.change_type,
                 "lines_added": fc.lines_added, "lines_removed": fc.lines_removed}
                for fc in self.file_changes
            ],
            "details": self.details,
        }


@dataclass
class TrialRun:
    run_id: str
    config: dict
    started_at: str
    completed_at: Optional[str] = None
    results: list[TrialResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def add_result(self, result: TrialResult) -> None:
        self.results.append(result)

    def compute_summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.verdict == Verdict.PASS)
        failed = sum(1 for r in self.results if r.verdict == Verdict.FAIL)
        ambiguous = sum(1 for r in self.results if r.verdict == Verdict.AMBIGUOUS)
        total_duration = sum(r.duration_s for r in self.results)
        avg_score = (sum(r.score for r in self.results) / total) if total > 0 else 0.0

        by_type: dict[str, dict] = {}
        for r in self.results:
            task_type = "unknown"
            for t in SEEDED_TASKS:
                if t.id == r.task_id:
                    task_type = t.task_type.value
                    break
            if task_type not in by_type:
                by_type[task_type] = {"total": 0, "passed": 0}
            by_type[task_type]["total"] += 1
            if r.verdict == Verdict.PASS:
                by_type[task_type]["passed"] += 1

        self.summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "ambiguous": ambiguous,
            "pass_rate": round(passed / max(total, 1), 3),
            "avg_score": round(avg_score, 3),
            "total_duration_s": round(total_duration, 1),
            "by_type": by_type,
            "completed_at": self.completed_at,
        }
        return self.summary


from .seeded_tasks import SEEDED_TASKS
