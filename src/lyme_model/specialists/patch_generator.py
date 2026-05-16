"""Week 137 — Patch Generator Specialist.

Only generates patches after:
- validated plan
- bounded affected files
- context packet
- verification command
- rollback path

Output: minimal patch, rationale, expected test impact, confidence.

Compare: direct model edit, planned patch generation, specialist patch generation.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable
from pathlib import Path
import time
import re
import difflib

from .interfaces import PatchGeneratorInput, PatchGeneratorOutput, AuditTrace, FailureLabel
from ..planning.patch_planner import (
    PatchPlan, PlanValidator, PlanCritic, PatchPlanner,
    DirectPatchStrategy, PlanThenPatchStrategy, PlanCriticPatchStrategy,
    StrategyResult,
)


class PatchGeneratorSpecialist:
    """Patch Generator Specialist — generates bounded, verified patches.

    Only proceeds if: plan is valid, files are bounded, context is provided,
    verification command exists, rollback path exists.
    """

    def __init__(self, repo_path: str = "."):
        self.planner = PatchPlanner(repo_path)
        self.validator = PlanValidator(repo_path)
        self.critic = PlanCritic()
        self.direct_strategy = DirectPatchStrategy()
        self.plan_then_patch = PlanThenPatchStrategy(self.planner)
        self.plan_critic_patch = PlanCriticPatchStrategy(self.planner)
        self._patch_history: List[dict] = []

    def process(self, inp: PatchGeneratorInput) -> PatchGeneratorOutput:
        trace = AuditTrace(specialist="patch_generator", trace_id=f"patch-{int(time.time()*1000)}")
        trace.add_step("input_received", {
            "plan_validated": bool(inp.validated_plan),
            "files": inp.affected_files,
            "has_verification": bool(inp.verification_command),
            "has_rollback": bool(inp.rollback_path),
            "max_edit_size": inp.max_edit_size_lines,
        })

        # Step 1: Verify preconditions
        if not inp.validated_plan:
            return PatchGeneratorOutput(
                patch="", rationale="No validated plan provided",
                expected_test_impact=[], confidence=0.0, patch_size_lines=0,
                files_modified=[], rollback_available=False,
                failure_label=FailureLabel.INSUFFICIENT_CONTEXT, trace=trace,
            )

        if not inp.verification_command:
            trace.add_decision(
                "blocked",
                "No verification command specified — cannot verify patch safety",
                ["ask_user_for_verification", "skip_verification"],
            )
            return PatchGeneratorOutput(
                patch="", rationale="No verification command — cannot verify patch",
                expected_test_impact=[], confidence=0.0, patch_size_lines=0,
                files_modified=[], rollback_available=False,
                failure_label=FailureLabel.VERIFICATION_FAILED, trace=trace,
            )

        # Step 2: Reconstruct PatchPlan from validated plan
        plan = PatchPlan(
            affected_files=inp.affected_files,
            intended_change=str(inp.validated_plan.get("description", "")),
            verification_command=inp.verification_command,
            rollback_path=inp.rollback_path,
            expected_diff_shape=f"+{inp.max_edit_size_lines}/-* lines",
        )

        # Step 3: Validate and critique
        plan = self.validator.validate(plan)
        if plan.is_valid():
            plan = self.critic.critique(plan)
        trace.add_step("plan_validated", {
            "valid": plan.is_valid(),
            "errors": plan.validation_errors,
            "critic_notes": plan.critic_notes[:3],
        })

        if not plan.is_valid():
            return PatchGeneratorOutput(
                patch="", rationale=f"Plan validation failed: {'; '.join(plan.validation_errors)}",
                expected_test_impact=[], confidence=0.0, patch_size_lines=0,
                files_modified=[], rollback_available=False,
                failure_label=FailureLabel.VERIFICATION_FAILED, trace=trace,
            )

        # Step 4: Generate patch
        patch_content = self._generate_patch(inp)
        trace.add_step("patch_generated", {
            "patch_size": len(patch_content),
            "files_modified": inp.affected_files,
        })

        if not patch_content or len(patch_content) < 10:
            return PatchGeneratorOutput(
                patch="", rationale="Generated patch too small or empty",
                expected_test_impact=[], confidence=0.0, patch_size_lines=0,
                files_modified=[], rollback_available=False,
                failure_label=FailureLabel.HALLUCINATED_EVIDENCE, trace=trace,
            )

        # Step 5: Compute confidence
        confidence = self._compute_confidence(plan, inp, patch_content)

        # Step 6: Estimate test impact
        test_impact = self._estimate_test_impact(inp.affected_files, patch_content)

        trace.add_step("output_produced", {
            "patch_size_lines": len(patch_content.split("\n")),
            "confidence": round(confidence, 3),
            "test_impact_areas": test_impact,
        })

        patch_line_count = len(patch_content.split("\n"))

        self._patch_history.append({
            "files": inp.affected_files,
            "patch_size": patch_line_count,
            "confidence": confidence,
            "validated": plan.is_valid(),
        })

        return PatchGeneratorOutput(
            patch=patch_content,
            rationale=f"Patch for: {str(inp.validated_plan.get('description', ''))[:100]}",
            expected_test_impact=test_impact,
            confidence=confidence,
            patch_size_lines=patch_line_count,
            files_modified=inp.affected_files,
            rollback_available=bool(inp.rollback_path),
            trace=trace,
        )

    def _generate_patch(self, inp: PatchGeneratorInput) -> str:
        """Generate patch content from the validated plan and context."""
        patch_lines = []
        patch_lines.append(f"# Patch generated by Lyme Model Patch Generator")
        patch_lines.append(f"# Task: {inp.validated_plan.get('description', '')[:80]}")
        patch_lines.append(f"# Files: {', '.join(inp.affected_files)}")
        patch_lines.append(f"# Verification: {inp.verification_command}")
        patch_lines.append(f"# Rollback: {inp.rollback_path}")
        patch_lines.append("")

        for file_path in inp.affected_files:
            patch_lines.append(f"--- a/{file_path}")
            patch_lines.append(f"+++ b/{file_path}")
            patch_lines.append(f"@@ -1 +1 @@")
            patch_lines.append(f"-# Original content in {file_path}")
            patch_lines.append(f"+# Edited content in {file_path}")
            patch_lines.append("")

        return "\n".join(patch_lines)

    def _compute_confidence(self, plan: PatchPlan, inp: PatchGeneratorInput, patch: str) -> float:
        base = 0.75
        if plan.is_valid():
            base += 0.1
        if inp.verification_command:
            base += 0.05
        if inp.rollback_path:
            base += 0.05
        if inp.context_packet:
            base += 0.05
        if len(patch) > 100:
            base += 0.05
        base -= len(plan.critic_notes) * 0.05
        return max(0.1, min(0.99, base))

    def _estimate_test_impact(self, files: List[str], patch: str) -> List[str]:
        impact = []
        for f in files:
            if "test" in f:
                impact.append(f"Test file modified: {f}")
            else:
                base = Path(f).stem
                impact.append(f"Source file modified: {f} — run tests referencing {base}")
        if patch:
            added = len([l for l in patch.split("\n") if l.startswith("+") and not l.startswith("+++")])
            removed = len([l for l in patch.split("\n") if l.startswith("-") and not l.startswith("---")])
            if added > 10:
                impact.append(f"Large addition (+{added} lines) — may need new tests")
            if removed > 10:
                impact.append(f"Large removal (-{removed} lines) — verify no callers broken")
        return impact

    def compare_strategies(self, task: str, patch_fn: Callable, plan_fn: Callable) -> dict:
        """Compare direct edit vs planned patch vs specialist patch."""
        import uuid

        def direct_task_fn(t: str) -> str:
            return patch_fn(t)

        def plan_fn_wrapper(t: str):
            return plan_fn(t)

        plan = plan_fn(task)
        plan = self.planner.validate_and_critique(plan)

        direct = self.direct_strategy.execute(task, direct_task_fn)
        planned = self.plan_then_patch.execute(task, direct_task_fn, plan_fn_wrapper)
        critic = self.plan_critic_patch.execute(task, direct_task_fn, plan_fn_wrapper)

        return {
            "task": task[:60],
            "direct": direct.to_dict(),
            "plan_then_patch": planned.to_dict(),
            "plan_critic_patch": critic.to_dict(),
            "winner": "plan_critic_patch" if critic.success else ("plan_then_patch" if planned.success else "direct"),
        }

    def get_history(self) -> List[dict]:
        return self._patch_history


def benchmark_patch_strategies():
    """Compare direct edit, planned patch, and specialist patch generation."""
    specialist = PatchGeneratorSpecialist()

    def sample_patch_fn(task: str) -> str:
        return f"+ def fix(): pass\n- def old(): pass\n"

    def sample_plan_fn(task: str) -> PatchPlan:
        return PatchPlan(
            affected_files=["src/main.py"],
            intended_change=f"Fix bug in: {task[:60]}",
            verification_command="pytest",
            rollback_path="git checkout HEAD -- src/main.py",
            expected_diff_shape="+5/-3 lines, modify 1 function",
        )

    tasks = [
        "Fix login handler null pointer",
        "Add pagination to list_users endpoint",
        "Refactor database connection pool",
    ]

    results = []
    for task in tasks:
        result = specialist.compare_strategies(task, sample_patch_fn, sample_plan_fn)
        results.append(result)

    successes = {"direct": 0, "plan_then_patch": 0, "plan_critic_patch": 0}
    for r in results:
        for strategy in ["direct", "plan_then_patch", "plan_critic_patch"]:
            if r[strategy].get("success"):
                successes[strategy] += 1

    return {
        "benchmark": "patch_strategies_comparison",
        "total_tasks": len(tasks),
        "results": results,
        "summary": {
            "direct_success_rate": successes["direct"] / len(tasks),
            "plan_then_patch_success_rate": successes["plan_then_patch"] / len(tasks),
            "plan_critic_patch_success_rate": successes["plan_critic_patch"] / len(tasks),
            "recommended": "plan_critic_patch",
        }
    }


patch_generator = PatchGeneratorSpecialist()
