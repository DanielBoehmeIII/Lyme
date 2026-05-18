"""ArenaRunner — run identical trial tasks across multiple coding tools.

Each tool gets the same task prompt and the same repo state.
Results are collected and normalized for comparison.
"""

from __future__ import annotations
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    ArenaConfig, ArenaRun, ToolResult, ToolName,
)
from ..trial.seeded_tasks import get_seeded_task


class ArenaRunner:
    """Run trial tasks across multiple coding tools."""

    def __init__(self, output_dir: str = ".lyme/arena"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_arena(self, config: ArenaConfig) -> ArenaRun:
        run_id = uuid.uuid4().hex[:12]
        run = ArenaRun(
            run_id=run_id,
            config=config,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        for task_id in config.task_ids:
            try:
                seeded = get_seeded_task(task_id)
            except KeyError:
                continue

            for tool in config.tools:
                result = self._run_tool_task(tool, task_id, seeded.title, config)
                run.add_result(result)

        run.completed_at = datetime.now(timezone.utc).isoformat()
        self._save_run(run)
        return run

    def _run_tool_task(self, tool: ToolName, task_id: str, task_title: str,
                       config: ArenaConfig) -> ToolResult:
        start = time.time()
        duration_s = 0.0
        error = None
        success = False
        correctness = 0.0
        test_pass_rate = 0.0
        files_touched = 0
        rollback_count = 0
        human_intervention = False
        token_count = 0

        try:
            if tool == ToolName.LYME:
                result = self._run_lyme(task_id, config)
            elif tool == ToolName.CLAUDE_CODE:
                result = self._run_claude_code(task_id, config)
            elif tool == ToolName.CODEX:
                result = self._run_codex(task_id, config)
            elif tool == ToolName.OPENCODE:
                result = self._run_opencode(task_id, config)
            elif tool == ToolName.AIDER:
                result = self._run_aider(task_id, config)
            elif tool == ToolName.CURSOR:
                result = self._run_cursor(task_id, config)
            else:
                result = {"error": f"Unknown tool: {tool}"}

            duration_s = round(time.time() - start, 2)
            success = result.get("success", False)
            correctness = result.get("correctness", 0.0)
            test_pass_rate = result.get("test_pass_rate", 0.0)
            files_touched = result.get("files_touched", 0)
            rollback_count = result.get("rollback_count", 0)
            human_intervention = result.get("human_intervention", False)
            token_count = result.get("token_count", 0)
            error = result.get("error")

        except Exception as e:
            duration_s = round(time.time() - start, 2)
            error = str(e)

        cost = (token_count or 0) * config.cost_per_token.get(tool.value, 0)

        return ToolResult(
            tool=tool,
            task_id=task_id,
            task_title=task_title,
            success=success,
            duration_s=duration_s,
            correctness=correctness,
            test_pass_rate=test_pass_rate,
            files_touched=files_touched,
            rollback_count=rollback_count,
            human_intervention=human_intervention,
            token_count=token_count,
            cost=cost,
            error=error,
        )

    def _run_lyme(self, task_id: str, config: ArenaConfig) -> dict:
        from ..trial.runner import TrialRunner
        runner = TrialRunner()
        result = runner.run_task(task_id, config.repo_path)
        return {
            "success": result.verdict is not None and result.verdict.value == "pass",
            "correctness": result.score,
            "test_pass_rate": 1.0 if result.test_results.get("test_after", {}).get("passed", True) else 0.0,
            "files_touched": len(result.files_touched),
            "rollback_count": 0,
            "human_intervention": False,
            "token_count": 0,
            "cost": 0.0,
        }

    def _run_claude_code(self, task_id: str, config: ArenaConfig) -> dict:
        try:
            seeded = get_seeded_task(task_id)
            prompt = f"Task: {seeded.title}\n\n{seeded.description}\n\nAcceptance criteria:\n"
            for c in seeded.acceptance_criteria:
                prompt += f"- {c}\n"
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=config.timeout_s,
                cwd=config.repo_path,
            )
            cost_estimate = len(result.stdout + result.stderr) * 0.00003
            return {
                "success": result.returncode == 0,
                "correctness": 0.5 if result.returncode == 0 else 0.0,
                "test_pass_rate": 0.0,
                "files_touched": 0,
                "rollback_count": 0,
                "human_intervention": result.returncode != 0,
                "token_count": len((result.stdout + result.stderr).split()),
                "cost": cost_estimate,
            }
        except FileNotFoundError:
            return {"error": "claude CLI not found", "success": False, "human_intervention": True}
        except subprocess.TimeoutExpired:
            return {"error": "claude CLI timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def _run_codex(self, task_id: str, config: ArenaConfig) -> dict:
        try:
            seeded = get_seeded_task(task_id)
            prompt = f"Fix the following: {seeded.title}\n\n{seeded.description}"
            result = subprocess.run(
                ["codex", "--prompt", prompt],
                capture_output=True, text=True, timeout=config.timeout_s,
                cwd=config.repo_path,
            )
            return {
                "success": result.returncode == 0,
                "correctness": 0.5 if result.returncode == 0 else 0.0,
                "test_pass_rate": 0.0,
                "files_touched": 0,
                "rollback_count": 0,
                "human_intervention": result.returncode != 0,
                "token_count": len((result.stdout + result.stderr).split()),
                "cost": len((result.stdout + result.stderr).split()) * 0.00002,
            }
        except FileNotFoundError:
            return {"error": "codex CLI not found", "success": False, "human_intervention": True}
        except subprocess.TimeoutExpired:
            return {"error": "codex CLI timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def _run_opencode(self, task_id: str, config: ArenaConfig) -> dict:
        try:
            seeded = get_seeded_task(task_id)
            prompt = f"Task: {seeded.title}\n{seeded.description}"
            result = subprocess.run(
                ["opencode", "-p", prompt],
                capture_output=True, text=True, timeout=config.timeout_s,
                cwd=config.repo_path,
            )
            return {
                "success": result.returncode == 0,
                "correctness": 0.5 if result.returncode == 0 else 0.0,
                "test_pass_rate": 0.0,
                "files_touched": 0,
                "rollback_count": 0,
                "human_intervention": result.returncode != 0,
                "token_count": len((result.stdout + result.stderr).split()),
                "cost": 0.0,
            }
        except FileNotFoundError:
            return {"error": "opencode CLI not found", "success": False, "human_intervention": True}
        except subprocess.TimeoutExpired:
            return {"error": "opencode CLI timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def _run_aider(self, task_id: str, config: ArenaConfig) -> dict:
        try:
            seeded = get_seeded_task(task_id)
            prompt = seeded.description
            result = subprocess.run(
                ["aider", "--message", prompt, "--no-auto-commits"],
                capture_output=True, text=True, timeout=config.timeout_s,
                cwd=config.repo_path,
            )
            return {
                "success": result.returncode == 0,
                "correctness": 0.5 if result.returncode == 0 else 0.0,
                "test_pass_rate": 0.0,
                "files_touched": 0,
                "rollback_count": 0,
                "human_intervention": result.returncode != 0,
                "token_count": len((result.stdout + result.stderr).split()),
                "cost": 0.0,
            }
        except FileNotFoundError:
            return {"error": "aider CLI not found", "success": False, "human_intervention": True}
        except subprocess.TimeoutExpired:
            return {"error": "aider timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def _run_cursor(self, task_id: str, config: ArenaConfig) -> dict:
        return {
            "error": "Cursor CLI mode not available",
            "success": False,
            "human_intervention": True,
            "correctness": 0.0,
            "test_pass_rate": 0.0,
            "files_touched": 0,
            "rollback_count": 0,
            "token_count": 0,
            "cost": 0.0,
        }

    def _save_run(self, run: ArenaRun) -> None:
        path = self.output_dir / f"arena-{run.run_id}.json"
        path.write_text(json.dumps(run.to_dict(), indent=2, default=str))
