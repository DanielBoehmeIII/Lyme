"""PredictabilityEngine — deterministic, verifiable, stable execution."""
from __future__ import annotations
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class ExecutionStep:
    step_id: str
    description: str
    command: str = ""
    expected_outcome: str = ""
    actual_outcome: str = ""
    status: str = "pending"
    duration_ms: float = 0.0
    error: Optional[str] = None
    hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "command": self.command,
            "expected": self.expected_outcome,
            "actual": self.actual_outcome,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "hash": self.hash[:12],
        }


@dataclass
class ExecutionPlan:
    plan_id: str = ""
    goal: str = ""
    steps: List[ExecutionStep] = field(default_factory=list)
    status: str = "planned"
    reproducibility_hash: str = ""
    plan_hash: str = ""
    created_at: float = field(default_factory=time.time)
    environment: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "reproducibility_hash": self.reproducibility_hash[:16],
            "plan_hash": self.plan_hash[:16],
            "created_at": self.created_at,
            "environment": dict(self.environment),
        }

    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status in ("passed", "skipped"))
        return completed / len(self.steps) * 100


class PredictabilityEngine:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "predictability"
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._current_plan: Optional[ExecutionPlan] = None

    def create_plan(self, goal: str, steps: List[Dict[str, str]]) -> ExecutionPlan:
        plan = ExecutionPlan(
            plan_id=hashlib.md5((goal + str(time.time())).encode()).hexdigest()[:12],
            goal=goal,
            environment=self._capture_environment(),
        )
        for i, s in enumerate(steps, 1):
            plan.steps.append(ExecutionStep(
                step_id=f"step_{i}",
                description=s.get("description", ""),
                command=s.get("command", ""),
                expected_outcome=s.get("expected", ""),
            ))
        plan.plan_hash = self._hash_plan(plan)
        plan.reproducibility_hash = self._hash_plan(plan)
        self._current_plan = plan
        self._save(plan)
        return plan

    def execute_step(self, step_id: str) -> ExecutionStep:
        if not self._current_plan:
            raise ValueError("No active plan")
        step = next((s for s in self._current_plan.steps if s.step_id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")

        start = time.time()
        step.status = "running"
        step.hash = hashlib.sha256(step.command.encode()).hexdigest()

        try:
            if step.command:
                result = subprocess.run(
                    step.command.split(),
                    capture_output=True, text=True, timeout=120,
                    cwd=str(self._repo),
                )
                step.actual_outcome = (result.stdout + result.stderr)[:500]
                if result.returncode == 0:
                    step.status = "passed"
                else:
                    step.status = "failed"
                    step.error = result.stderr[:200]
            else:
                step.status = "passed"
                step.actual_outcome = "No command to execute"
        except subprocess.TimeoutExpired:
            step.status = "failed"
            step.error = "Command timed out"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)

        step.duration_ms = (time.time() - start) * 1000
        self._save(self._current_plan)
        return step

    def execute_all(self) -> ExecutionPlan:
        if not self._current_plan:
            raise ValueError("No active plan")
        for step in self._current_plan.steps:
            if step.status == "pending":
                self.execute_step(step.step_id)
        self._current_plan.status = "completed" if all(
            s.status == "passed" for s in self._current_plan.steps
        ) else "partial"
        self._save(self._current_plan)
        return self._current_plan

    def verify_reproducibility(self, plan_id: str) -> Dict[str, Any]:
        plan = self._load(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        current_env = self._capture_environment()
        env_changed = current_env != plan.environment
        current_hash = self._hash_plan(plan)
        hash_match = current_hash == plan.plan_hash
        return {
            "plan_id": plan_id,
            "reproducible": hash_match and not env_changed,
            "hash_match": hash_match,
            "environment_changed": env_changed,
            "original_env": plan.environment,
            "current_env": current_env,
        }

    def current_plan(self) -> Optional[ExecutionPlan]:
        return self._current_plan

    def plan_status(self) -> Dict[str, Any]:
        if not self._current_plan:
            return {"status": "no_plan"}
        return {
            "plan_id": self._current_plan.plan_id,
            "goal": self._current_plan.goal,
            "progress": self._current_plan.progress(),
            "steps": len(self._current_plan.steps),
            "passed": sum(1 for s in self._current_plan.steps if s.status == "passed"),
            "failed": sum(1 for s in self._current_plan.steps if s.status == "failed"),
            "status": self._current_plan.status,
        }

    def list_plans(self) -> List[Dict[str, Any]]:
        plans = []
        for path in sorted(self._db_path.glob("plan_*.json"), reverse=True)[:20]:
            try:
                data = json.loads(path.read_text())
                plans.append({
                    "plan_id": data.get("plan_id", ""),
                    "goal": data.get("goal", "")[:60],
                    "progress": data.get("progress", 0),
                    "status": data.get("status", "unknown"),
                    "created": data.get("created_at", 0),
                })
            except Exception:
                continue
        return plans

    def _capture_environment(self) -> Dict[str, str]:
        env = {}
        try:
            env["python_version"] = subprocess.run(
                [sys.executable or "python3", "--version"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            env["python_version"] = "unknown"
        try:
            env["git_head"] = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self._repo),
            ).stdout.strip()[:12]
        except Exception:
            env["git_head"] = "unknown"
        return env

    def _hash_plan(self, plan: ExecutionPlan) -> str:
        data = json.dumps(plan.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _save(self, plan: ExecutionPlan) -> None:
        path = self._db_path / f"plan_{plan.plan_id}.json"
        path.write_text(json.dumps(plan.to_dict(), indent=2))

    def _load(self, plan_id: str) -> Optional[ExecutionPlan]:
        path = self._db_path / f"plan_{plan_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            plan = ExecutionPlan(
                plan_id=data.get("plan_id", ""),
                goal=data.get("goal", ""),
                status=data.get("status", ""),
                created_at=data.get("created_at", 0),
                reproducibility_hash=data.get("reproducibility_hash", ""),
                plan_hash=data.get("plan_hash", ""),
                environment=data.get("environment", {}),
            )
            for s in data.get("steps", []):
                plan.steps.append(ExecutionStep(
                    step_id=s.get("step_id", ""),
                    description=s.get("description", ""),
                    command=s.get("command", ""),
                    expected_outcome=s.get("expected", ""),
                    actual_outcome=s.get("actual", ""),
                    status=s.get("status", "pending"),
                    duration_ms=s.get("duration_ms", 0.0),
                    error=s.get("error"),
                    hash=s.get("hash", ""),
                ))
            return plan
        except Exception as e:
            return None


import sys
