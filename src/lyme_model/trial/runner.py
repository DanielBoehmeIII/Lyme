"""TrialRunner — executes trial tasks against real repos.

Records every step: starting commit, commands run, files changed, failures,
final diff, test results. Produces TrialResult for each task.
"""

from __future__ import annotations
import os
import sys
import json
import time
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    TrialTask, TrialResult, TrialRun, TrialStatus, Verdict,
    CommandRun, FileChange, SeededTask,
)
from .seeded_tasks import SEEDED_TASKS, get_seeded_task
from .recorder import TrialRecorder
from .judge import TrialJudge
from .replay import TrialReplay
from .report import TrialReport


class TrialRunner:
    """Execute trial tasks and record results."""

    def __init__(self, output_dir: str = ".lyme/trials", dry_run: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.recorder = TrialRecorder(self.output_dir)
        self.judge = TrialJudge()
        self.replay = TrialReplay(self.output_dir)

    def list_tasks(self, task_type: Optional[str] = None, difficulty: Optional[str] = None) -> list[dict]:
        tasks = SEEDED_TASKS
        if task_type:
            from .models import TaskType
            tt = TaskType(task_type)
            tasks = [t for t in tasks if t.task_type == tt]
        if difficulty:
            tasks = [t for t in tasks if t.difficulty == difficulty]
        return [t.to_dict() for t in tasks]

    def run_task(self, task_id: str, repo_path: str = ".") -> TrialResult:
        try:
            seeded = get_seeded_task(task_id)
        except KeyError as e:
            return TrialResult(
                trial_id="", task_id=task_id, title="unknown",
                status=TrialStatus.ERROR, verdict=None,
                starting_commit="", task_prompt="",
                files_touched=[], commands_run=[], failures=[str(e)],
                final_diff="", test_results={}, duration_s=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(), error=str(e),
            )

        repo = Path(repo_path).resolve()
        trial_id = uuid.uuid4().hex[:12]
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()
        commands_run: list[CommandRun] = []
        failures: list[str] = []
        files_touched: list[str] = []
        file_changes: list[FileChange] = []
        agent_log: list[str] = []

        starting_commit = self._get_current_commit(repo)
        task_prompt = self._build_prompt(seeded)

        agent_log.append(f"Starting trial {trial_id} for task {task_id}: {seeded.title}")
        agent_log.append(f"Repo: {repo} | Commit: {starting_commit}")

        if self.dry_run:
            return TrialResult(
                trial_id=trial_id, task_id=task_id, title=seeded.title,
                status=TrialStatus.PENDING, verdict=None,
                starting_commit=starting_commit, task_prompt=task_prompt,
                files_touched=[], commands_run=[], failures=[],
                final_diff="", test_results={},
                duration_s=0.0, timestamp=timestamp,
                details={"dry_run": True, "seeded_task": seeded.to_dict()},
            )

        status = TrialStatus.PASSED
        for i, criterion in enumerate(seeded.acceptance_criteria):
            agent_log.append(f"Criterion {i+1}: {criterion}")

        setup_ok = self._run_setup(seeded, repo, commands_run, failures, agent_log)
        if not setup_ok:
            status = TrialStatus.ERROR
            failures.append("Setup failed — aborting trial")

        test_before = self._run_tests(seeded, repo, "before", commands_run, agent_log)

        agent_log.append("--- End Trial (no automated agent execution in harness) ---")

        duration_s = round(time.time() - start_time, 2)
        final_diff = self._get_diff(repo, starting_commit)

        file_changes_list = self._get_file_changes(repo, starting_commit)

        result = TrialResult(
            trial_id=trial_id,
            task_id=task_id,
            title=seeded.title,
            status=status,
            verdict=self.judge.judge(TrialResult(
                trial_id=trial_id, task_id=task_id, title=seeded.title,
                status=status, verdict=None,
                starting_commit=starting_commit, task_prompt=task_prompt,
                files_touched=list(set(files_touched)),
                commands_run=commands_run,
                failures=failures,
                final_diff=final_diff,
                test_results={"test_before": test_before, "test_after": {}},
                duration_s=duration_s,
                timestamp=timestamp,
                file_changes=file_changes_list,
                agent_log=agent_log,
                score=0.0,
            ), seeded),
            starting_commit=starting_commit,
            task_prompt=task_prompt,
            files_touched=list(set(files_touched)),
            commands_run=commands_run,
            failures=failures,
            final_diff=final_diff,
            test_results={"test_before": test_before, "test_after": {}},
            duration_s=duration_s,
            timestamp=timestamp,
            file_changes=file_changes_list,
            agent_log=agent_log,
        )

        result.score = self.judge.compute_score(result, seeded)
        if result.verdict is None:
            result.verdict = self.judge.judge(result, seeded)
            if result.verdict == Verdict.PASS:
                result.status = TrialStatus.PASSED
            else:
                result.status = TrialStatus.FAILED

        self.recorder.save_trial(result)
        return result

    def run_all(self, repo_path: str = ".") -> TrialRun:
        run_id = uuid.uuid4().hex[:12]
        run = TrialRun(
            run_id=run_id,
            config={"repo_path": repo_path, "total_tasks": len(SEEDED_TASKS)},
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        for task in SEEDED_TASKS:
            result = self.run_task(task.id, repo_path)
            run.add_result(result)
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.compute_summary()
        self.recorder.save_run(run)
        return run

    def run_by_type(self, task_type: str, repo_path: str = ".") -> TrialRun:
        from .models import TaskType
        tt = TaskType(task_type)
        run_id = uuid.uuid4().hex[:12]
        run = TrialRun(
            run_id=run_id,
            config={"repo_path": repo_path, "task_type": task_type},
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        for task in SEEDED_TASKS:
            if task.task_type == tt:
                result = self.run_task(task.id, repo_path)
                run.add_result(result)
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.compute_summary()
        self.recorder.save_run(run)
        return run

    def _build_prompt(self, task: SeededTask) -> str:
        criteria = "\n".join(f"- {c}" for c in task.acceptance_criteria)
        hints = "\n".join(f"  Hint: {h}" for h in task.hints)
        hints_section = f"Hints:\n{hints}" if hints else ""
        return (
            f"Task: {task.title}\n\n"
            f"Description: {task.description}\n\n"
            f"Acceptance Criteria:\n{criteria}\n\n"
            f"Expected files: {', '.join(task.expected_files)}\n"
            f"Test command: {task.test_command}\n"
            f"Setup command: {task.setup_command}\n"
            f"Difficulty: {task.difficulty}\n"
            f"Estimated time: {task.estimated_time_minutes} minutes\n"
            f"{hints_section}"
        )

    def _run_setup(self, task: SeededTask, repo: Path, commands: list[CommandRun],
                   failures: list[str], log: list[str]) -> bool:
        if not task.setup_command:
            return True
        log.append(f"Running setup: {task.setup_command}")
        try:
            ts = time.time()
            result = subprocess.run(
                task.setup_command.split(), capture_output=True, text=True,
                timeout=120, cwd=str(repo),
            )
            duration = round(time.time() - ts, 2)
            cmd = CommandRun(
                command=task.setup_command, exit_code=result.returncode,
                stdout=result.stdout or "", stderr=result.stderr or "",
                duration_s=duration,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            commands.append(cmd)
            if result.returncode != 0:
                failures.append(f"Setup failed: {result.stderr[:200]}")
                log.append(f"Setup FAILED (exit {result.returncode})")
                return False
            log.append("Setup OK")
            return True
        except subprocess.TimeoutExpired:
            failures.append("Setup timed out after 120s")
            log.append("Setup TIMEOUT")
            return False
        except Exception as e:
            failures.append(f"Setup error: {e}")
            log.append(f"Setup ERROR: {e}")
            return False

    def _run_tests(self, task: SeededTask, repo: Path, phase: str,
                   commands: list[CommandRun], log: list[str]) -> dict:
        if not task.test_command:
            return {"skipped": True}
        log.append(f"Running tests ({phase}): {task.test_command}")
        try:
            ts = time.time()
            result = subprocess.run(
                task.test_command.split(), capture_output=True, text=True,
                timeout=120, cwd=str(repo),
            )
            duration = round(time.time() - ts, 2)
            cmd = CommandRun(
                command=f"[{phase}] {task.test_command}", exit_code=result.returncode,
                stdout=result.stdout[:2000], stderr=result.stderr[:2000],
                duration_s=duration,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            commands.append(cmd)
            passed = result.returncode == 0
            log.append(f"Tests {phase}: {'PASSED' if passed else 'FAILED'} ({duration}s)")
            return {
                "command": task.test_command,
                "passed": passed,
                "exit_code": result.returncode,
                "stdout_preview": result.stdout[:500],
                "stderr_preview": result.stderr[:500],
                "duration_s": duration,
            }
        except subprocess.TimeoutExpired:
            log.append(f"Tests {phase}: TIMEOUT")
            return {"command": task.test_command, "passed": False, "error": "timeout"}
        except Exception as e:
            log.append(f"Tests {phase}: ERROR {e}")
            return {"command": task.test_command, "passed": False, "error": str(e)}

    def _get_current_commit(self, repo: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=str(repo), timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _get_diff(self, repo: Path, starting_commit: str) -> str:
        if starting_commit == "unknown":
            return ""
        try:
            result = subprocess.run(
                ["git", "diff", starting_commit],
                capture_output=True, text=True, cwd=str(repo), timeout=10,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""

    def _get_file_changes(self, repo: Path, starting_commit: str) -> list[FileChange]:
        if starting_commit == "unknown":
            return []
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat", starting_commit],
                capture_output=True, text=True, cwd=str(repo), timeout=10,
            )
            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    removed = int(parts[1]) if parts[1] != "-" else 0
                    fpath = parts[2]
                    change_type = "modified"
                    changes.append(FileChange(
                        path=fpath, change_type=change_type,
                        diff="", lines_added=added, lines_removed=removed,
                    ))
            return changes
        except Exception:
            return []
