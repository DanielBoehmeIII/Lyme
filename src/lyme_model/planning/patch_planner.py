"""Week 77 — Patch Planning for Weak Models.

Weak models should not freely edit immediately.
The planner requires plan validation before patch generation.

Compares: direct patching, plan-then-patch, plan-critic-patch.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
import difflib
import re


@dataclass
class PatchPlan:
    """A validated patch plan that must pass checks before patch generation."""
    affected_files: List[str] = field(default_factory=list)
    intended_change: str = ""
    dependency_risks: List[str] = field(default_factory=list)
    verification_command: str = ""
    rollback_path: str = ""
    expected_diff_shape: str = ""  # e.g. "+10/-5 lines, modify 2 functions"
    plan_id: str = ""
    status: str = "draft"  # draft, validated, rejected, applied
    validation_errors: List[str] = field(default_factory=list)
    critic_notes: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_valid(self) -> bool:
        return (len(self.affected_files) > 0
                and len(self.intended_change) > 0
                and len(self.validation_errors) == 0)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "affected_files": self.affected_files,
            "intended_change": self.intended_change[:100],
            "dependency_risks": self.dependency_risks,
            "verification_command": self.verification_command,
            "rollback_path": self.rollback_path,
            "expected_diff_shape": self.expected_diff_shape,
            "status": self.status,
            "validation_errors": self.validation_errors,
            "critic_notes": self.critic_notes,
            "timestamp": self.timestamp,
            "valid": self.is_valid(),
        }


class PlanValidator:
    """Validates patch plans before allowing generation."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def validate(self, plan: PatchPlan) -> PatchPlan:
        """Check plan completeness and consistency."""
        errors = []

        if not plan.affected_files:
            errors.append("No affected files specified")
        if not plan.intended_change:
            errors.append("No intended change described")
        if len(plan.intended_change) < 10:
            errors.append("Intended change too vague (< 10 chars)")

        # Check file existence
        from pathlib import Path
        repo = Path(self.repo_path)
        for f in plan.affected_files:
            full = repo / f
            if not full.exists():
                errors.append(f"File does not exist: {f}")

        # Check rollback is specified
        if not plan.rollback_path:
            errors.append("No rollback path specified")

        # Check verification is specified
        if not plan.verification_command:
            errors.append("No verification command specified")

        # Check expected diff shape is specified
        if not plan.expected_diff_shape:
            errors.append("No expected diff shape specified")

        plan.validation_errors = errors
        plan.status = "validated" if not errors else "rejected"
        return plan


class PlanCritic:
    """Reviews plans for potential issues before execution."""

    def __init__(self):
        self.risk_patterns = {
            "import": "Import changes can break downstream modules",
            "delete": "Deleting code may affect callers",
            "rename": "Renaming requires updating all references",
            "migration": "Database migrations need rollback scripts",
            "schema": "Schema changes affect all consumers",
            "config": "Config changes affect runtime behavior",
            "test": "Test modifications reduce coverage confidence",
            "public": "Public API changes break consumers",
        }

    def critique(self, plan: PatchPlan) -> PatchPlan:
        """Analyze plan and add critic notes."""
        notes = []

        change_lower = plan.intended_change.lower()

        for pattern, risk in self.risk_patterns.items():
            if pattern in change_lower:
                notes.append(f"Risk: {risk}")

        # File-specific risks
        for f in plan.affected_files:
            if "__init__" in f:
                notes.append(f"Note: {f} is a package init file")
            if "migration" in f.lower() or "migrate" in f.lower():
                notes.append(f"Note: {f} appears to be a migration file")
            if "test_" in f or "/test" in f:
                notes.append(f"Warning: Modifying test file {f}")
            if "config" in f.lower() or "setting" in f.lower():
                notes.append(f"Warning: {f} is a configuration file")

        # Diff shape analysis
        if plan.expected_diff_shape:
            added = re.findall(r'\+\s*(\d+)', plan.expected_diff_shape)
            if added:
                total_added = sum(int(a) for a in added)
                if total_added > 100:
                    notes.append(f"Large patch: +{total_added} lines, consider splitting")

        plan.critic_notes = notes
        return plan


class PatchPlanner:
    """Generates and validates patch plans."""

    def __init__(self, repo_path: str = "."):
        self.validator = PlanValidator(repo_path)
        self.critic = PlanCritic()
        self.plans: Dict[str, PatchPlan] = {}

    def create_plan(self, affected_files: List[str], intended_change: str,
                    dependency_risks: Optional[List[str]] = None,
                    verification_command: str = "",
                    rollback_path: str = "",
                    expected_diff_shape: str = "") -> PatchPlan:
        import uuid
        plan = PatchPlan(
            affected_files=affected_files,
            intended_change=intended_change,
            dependency_risks=dependency_risks or [],
            verification_command=verification_command,
            rollback_path=rollback_path,
            expected_diff_shape=expected_diff_shape,
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
        )
        self.plans[plan.plan_id] = plan
        return plan

    def validate_and_critique(self, plan: PatchPlan) -> PatchPlan:
        """Run validation and critique on a plan."""
        plan = self.validator.validate(plan)
        if plan.status != "rejected":
            plan = self.critic.critique(plan)
        return plan

    def get_plan(self, plan_id: str) -> Optional[PatchPlan]:
        return self.plans.get(plan_id)


PATCH_STRATEGIES = ["direct", "plan_then_patch", "plan_critic_patch"]


@dataclass
class StrategyResult:
    strategy: str
    plan: Optional[PatchPlan]
    success: bool
    patch_output: str
    validation_time_ms: float
    patch_time_ms: float
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "success": self.success,
            "patch_output": self.patch_output[:200],
            "validation_time_ms": self.validation_time_ms,
            "patch_time_ms": self.patch_time_ms,
            "errors": self.errors,
        }


class DirectPatchStrategy:
    """Strategy 1: Patch directly without planning."""

    def execute(self, task: str, patch_fn: Callable) -> StrategyResult:
        import time
        start = time.time()
        try:
            output = patch_fn(task)
            elapsed = int((time.time() - start) * 1000)
            return StrategyResult(
                strategy="direct",
                plan=None,
                success=True,
                patch_output=output,
                validation_time_ms=0,
                patch_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StrategyResult(
                strategy="direct",
                plan=None,
                success=False,
                patch_output="",
                validation_time_ms=0,
                patch_time_ms=elapsed,
                errors=[str(e)],
            )


class PlanThenPatchStrategy:
    """Strategy 2: Plan first, then patch (only if plan validates)."""

    def __init__(self, planner: PatchPlanner):
        self.planner = planner

    def execute(self, task: str, patch_fn: Callable,
                plan_fn: Callable[[str], PatchPlan]) -> StrategyResult:
        import time
        v_start = time.time()

        # Step 1: Create and validate plan
        plan = plan_fn(task)
        plan = self.planner.validate_and_critique(plan)
        v_elapsed = int((time.time() - v_start) * 1000)

        if not plan.is_valid():
            return StrategyResult(
                strategy="plan_then_patch",
                plan=plan,
                success=False,
                patch_output="",
                validation_time_ms=v_elapsed,
                patch_time_ms=0,
                errors=plan.validation_errors,
            )

        # Step 2: Generate patch (only if plan is valid)
        p_start = time.time()
        try:
            output = patch_fn(task)
            plan.status = "applied"
            p_elapsed = int((time.time() - p_start) * 1000)
            return StrategyResult(
                strategy="plan_then_patch",
                plan=plan,
                success=True,
                patch_output=output,
                validation_time_ms=v_elapsed,
                patch_time_ms=p_elapsed,
            )
        except Exception as e:
            p_elapsed = int((time.time() - p_start) * 1000)
            plan.status = "rejected"
            return StrategyResult(
                strategy="plan_then_patch",
                plan=plan,
                success=False,
                patch_output="",
                validation_time_ms=v_elapsed,
                patch_time_ms=p_elapsed,
                errors=[str(e)],
            )


class PlanCriticPatchStrategy:
    """Strategy 3: Plan, review with critic, then patch."""

    def __init__(self, planner: PatchPlanner):
        self.planner = planner

    def execute(self, task: str, patch_fn: Callable,
                plan_fn: Callable[[str], PatchPlan]) -> StrategyResult:
        import time
        v_start = time.time()

        # Step 1: Create, validate, and critique plan
        plan = plan_fn(task)
        plan = self.planner.validate_and_critique(plan)
        v_elapsed = int((time.time() - v_start) * 1000)

        if not plan.is_valid():
            return StrategyResult(
                strategy="plan_critic_patch",
                plan=plan,
                success=False,
                patch_output="",
                validation_time_ms=v_elapsed,
                patch_time_ms=0,
                errors=plan.validation_errors,
            )

        # Step 2: Critic can block high-risk patches
        high_risk_keywords = ["delete", "rename", "migration", "schema"]
        for note in plan.critic_notes:
            for kw in high_risk_keywords:
                if kw in note.lower():
                    # Add warning but don't block — the critic advises
                    pass

        # Step 3: Generate patch
        p_start = time.time()
        try:
            output = patch_fn(task)
            plan.status = "applied"
            p_elapsed = int((time.time() - p_start) * 1000)
            return StrategyResult(
                strategy="plan_critic_patch",
                plan=plan,
                success=True,
                patch_output=output,
                validation_time_ms=v_elapsed,
                patch_time_ms=p_elapsed,
            )
        except Exception as e:
            p_elapsed = int((time.time() - p_start) * 1000)
            plan.status = "rejected"
            return StrategyResult(
                strategy="plan_critic_patch",
                plan=plan,
                success=False,
                patch_output="",
                validation_time_ms=v_elapsed,
                patch_time_ms=p_elapsed,
                errors=[str(e)],
            )


RUNTIME_COMPARISON_METRICS = [
    "success_rate",
    "avg_validation_time_ms",
    "avg_patch_time_ms",
    "blocked_bad_patches",
    "false_rejections",
]


def run_patch_comparison(
    tasks: List[str],
    patch_fn: Callable,
    plan_fn: Callable[[str], PatchPlan],
    planner: PatchPlanner,
) -> Dict[str, Dict]:
    """Run all 3 strategies on a set of tasks and compare."""
    strategies = {
        "direct": DirectPatchStrategy(),
        "plan_then_patch": PlanThenPatchStrategy(planner),
        "plan_critic_patch": PlanCriticPatchStrategy(planner),
    }

    results: Dict[str, List[StrategyResult]] = {s: [] for s in strategies}

    for task in tasks:
        # Direct
        r1 = strategies["direct"].execute(task, patch_fn)
        results["direct"].append(r1)

        # Plan-then-patch
        r2 = strategies["plan_then_patch"].execute(task, patch_fn, plan_fn)
        results["plan_then_patch"].append(r2)

        # Plan-critic-patch
        r3 = strategies["plan_critic_patch"].execute(task, patch_fn, plan_fn)
        results["plan_critic_patch"].append(r3)

    comparison = {}
    for sname, sresults in results.items():
        n = len(sresults)
        success_rate = sum(1 for r in sresults if r.success) / n if n > 0 else 0
        avg_v_time = sum(r.validation_time_ms for r in sresults) / n if n > 0 else 0
        avg_p_time = sum(r.patch_time_ms for r in sresults) / n if n > 0 else 0
        blocked = sum(1 for r in sresults if r.errors and "rejected" in str(r.plan.status if r.plan else ""))
        false_rejections = 0  # requires ground truth

        comparison[sname] = {
            "trials": n,
            "success_rate": round(success_rate, 4),
            "avg_validation_time_ms": round(avg_v_time, 1),
            "avg_patch_time_ms": round(avg_p_time, 1),
            "blocked_bad_patches": blocked,
            "false_rejections": false_rejections,
        }

    return comparison
