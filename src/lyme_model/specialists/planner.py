"""Week 135 — Planner Specialist.

Input: user task, repo summary, constraints, hardware, available models
Output: task decomposition, affected files, context needs, risk score, model/mode recommendation,
         verification strategy, stop conditions

Benchmark against generic local model planning.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import json

from .interfaces import PlannerInput, PlannerOutput, AuditTrace, FailureLabel, ConfidenceLevel
from ..planning.difficulty_estimator import DifficultyEstimator, TaskType, RiskLevel
from ..planning.mode_selection import ModeSelector, Mode
from ..planning.long_horizon import (
    TaskDecomposer, HierarchicalPlanner, SubtaskType, SubtaskStatus,
)


class PlannerSpecialist:
    """Planner Specialist — decomposes tasks, estimates difficulty, selects mode.

    Wraps: TaskDecomposer, HierarchicalPlanner, DifficultyEstimator, ModeSelector.
    Produces: PlannerOutput with structured plan and recommendations.
    """

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.hierarchical_planner = HierarchicalPlanner()
        self.difficulty_estimator = DifficultyEstimator()
        self.mode_selector = ModeSelector()
        self._plan_history: List[dict] = []

    def process(self, inp: PlannerInput) -> PlannerOutput:
        trace = AuditTrace(specialist="planner", trace_id=f"plan-{int(time.time()*1000)}")
        trace.add_step("input_received", {
            "task": inp.user_task[:100],
            "constraints": inp.relevant_constraints,
            "hardware": inp.hardware_profile,
        })

        # Step 1: Estimate difficulty
        difficulty = self.difficulty_estimator.estimate(
            inp.user_task, hardware_tier=inp.hardware_profile
        )
        trace.add_step("difficulty_estimated", {
            "score": difficulty.difficulty_score,
            "level": difficulty.difficulty_level.value,
            "risk": difficulty.risk.value,
            "task_type": difficulty.task_type.value,
        })

        # Check refusal conditions
        if difficulty.difficulty_score > 0.85 or difficulty.risk == RiskLevel.CRITICAL:
            trace.add_decision(
                "refuse",
                f"Difficulty {difficulty.difficulty_score:.2f} or risk {difficulty.risk.value} too high",
                ["simplify_task", "switch_model", "ask_user"],
            )
            return PlannerOutput(
                task_decomposition=[],
                affected_files=[],
                context_needs=[],
                risk_score={"none": 0, "low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}.get(difficulty.risk.value, 0.5),
                recommended_mode=f"refuse",
                recommended_model=inp.available_models[0] if inp.available_models else "none",
                verification_strategy=["cannot_verify — refused"],
                stop_conditions=["task refused"],
                confidence=0.0,
                failure_label=FailureLabel.RISK_TOO_HIGH,
                trace=trace,
            )

        # Step 2: Select mode
        mode_sel = self.mode_selector.select_mode(
            difficulty.difficulty_score, difficulty.risk.value,
            inp.hardware_profile, 1000, task_type=difficulty.task_type.value
        )
        trace.add_decision(
            f"mode_selected: {mode_sel.selected_mode.value}",
            f"Difficulty {difficulty.difficulty_score:.2f}, risk {difficulty.risk.value}, "
            f"hardware {inp.hardware_profile}",
            [m.value for m in mode_sel.alternatives],
        )

        # Step 3: Decompose task
        plan = self.decomposer.decompose(inp.user_task, repo_size_hint=1000)
        trace.add_step("task_decomposed", {
            "subtask_count": len(plan.subtasks),
            "ordering": plan.ordering,
        })

        # Step 4: Generate hierarchical plan
        hplan_type = "hierarchical_with_critic" if mode_sel.selected_mode in (
            Mode.LOCAL_WITH_CRITIC, Mode.LOCAL_WITH_HUMAN_CHECKPOINT
        ) else "hierarchical"
        hplan = self.hierarchical_planner.plan(inp.user_task, hplan_type)
        trace.add_step("hierarchical_plan_created", {
            "plan_type": hplan_type,
            "root": hplan.root.name,
            "children": len(hplan.root.children),
        })

        # Step 5: Extract affected files and context needs
        affected_files = list(set(
            f for s in plan.subtasks for f in s.expected_files
        ))
        context_needs = self._infer_context_needs(difficulty.task_type, affected_files)

        # Step 6: Build verification strategy
        verification_strategy = self._build_verification_strategy(
            difficulty.task_type, difficulty.risk, mode_sel.selected_mode
        )

        # Step 7: Determine stop conditions
        stop_conditions = self._build_stop_conditions(difficulty, mode_sel.selected_mode)

        # Step 8: Compute confidence
        confidence = self._compute_confidence(difficulty, mode_sel, inp.prior_failures)

        trace.add_step("output_produced", {
            "subtasks": len(plan.subtasks),
            "files": len(affected_files),
            "mode": mode_sel.selected_mode.value,
            "confidence": round(confidence, 3),
        })

        # Build task decomposition list for output
        task_decomp = []
        for s in plan.subtasks:
            task_decomp.append({
                "id": s.id,
                "name": s.name,
                "description": s.description[:100],
                "type": s.type.value,
                "dependencies": s.dependencies,
                "expected_files": s.expected_files,
                "estimated_difficulty": s.estimated_difficulty,
                "verification_command": s.verification_command,
            })

        failure_label = None
        if confidence < 0.3:
            failure_label = FailureLabel.INSUFFICIENT_CONTEXT
        elif difficulty.ambiguity > 0.6:
            failure_label = FailureLabel.AMBIGUOUS_INPUT

        risk_score = {"none": 0, "low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}.get(difficulty.risk.value, 0.5)

        self._plan_history.append({
            "task": inp.user_task[:80],
            "difficulty": difficulty.difficulty_score,
            "mode": mode_sel.selected_mode.value,
            "confidence": confidence,
            "subtasks": len(plan.subtasks),
        })

        return PlannerOutput(
            task_decomposition=task_decomp,
            affected_files=affected_files,
            context_needs=context_needs,
            risk_score=risk_score,
            recommended_mode=mode_sel.selected_mode.value,
            recommended_model=inp.available_models[0] if inp.available_models else "qwen2.5-coder-7b",
            verification_strategy=verification_strategy,
            stop_conditions=stop_conditions,
            confidence=confidence,
            failure_label=failure_label,
            trace=trace,
        )

    def _infer_context_needs(self, task_type: TaskType, files: List[str]) -> List[str]:
        needs = []
        if task_type in (TaskType.REPO_QA, TaskType.BUG_LOCATE):
            needs.append("file_index")
            if task_type == TaskType.BUG_LOCATE:
                needs.append("git_history")
        if task_type in (TaskType.PATCH_PLAN, TaskType.PATCH_APPLY, TaskType.TEST_REPAIR):
            needs.append("file_content")
            needs.append("ast_symbols")
            needs.append("test_results")
        if task_type in (TaskType.REFACTOR, TaskType.DEPENDENCY_MIGRATION):
            needs.append("import_graph")
            needs.append("all_references")
        if task_type == TaskType.CODE_GENERATION:
            needs.append("existing_file_patterns")
            needs.append("framework_docs")
        if task_type == TaskType.UNKNOWN:
            needs.append("repo_structure")
        for f in files:
            needs.append(f"file:{f}")
        return needs

    def _build_verification_strategy(self, task_type: TaskType, risk: RiskLevel, mode: Mode) -> List[str]:
        strategy = []
        if task_type in (TaskType.REPO_QA, TaskType.BUG_LOCATE, TaskType.FAILURE_EXPLAIN):
            strategy.append("claim_verification")
            strategy.append("evidence_citation_check")
        if task_type in (TaskType.PATCH_PLAN, TaskType.PATCH_APPLY, TaskType.TEST_REPAIR):
            strategy.append("syntax_check")
            strategy.append("file_existence_check")
            if mode in (Mode.LOCAL_CAREFUL, Mode.LOCAL_WITH_CRITIC):
                strategy.append("unit_test_run")
                strategy.append("import_resolution_check")
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            strategy.append("human_checkpoint")
            strategy.append("rollback_plan_check")
        if mode == Mode.LOCAL_MULTI_CANDIDATE:
            strategy.append("candidate_ranking")
            strategy.append("similarity_clustering")
        strategy.append("audit_trace_record")
        return strategy if strategy else ["audit_trace_record"]

    def _build_stop_conditions(self, difficulty: DifficultyEstimator, mode: Mode) -> List[str]:
        conditions = ["all_subtasks_completed"]
        if mode in (Mode.LOCAL_WITH_CRITIC, Mode.LOCAL_CAREFUL):
            conditions.append("verification_failed_after_retries")
        if difficulty.risk in ("high", "critical"):
            conditions.append("user_requested_stop")
            conditions.append("risk_threshold_exceeded")
        conditions.append("max_retries_exceeded")
        conditions.append("timeout_reached")
        return conditions

    def _compute_confidence(self, difficulty, mode_sel, prior_failures: List[str]) -> float:
        base = 0.85
        base -= difficulty.difficulty_score * 0.4
        base -= difficulty.ambiguity * 0.2
        if difficulty.risk == RiskLevel.CRITICAL:
            base -= 0.3
        elif difficulty.risk == RiskLevel.HIGH:
            base -= 0.2
        elif difficulty.risk == RiskLevel.MEDIUM:
            base -= 0.1
        if prior_failures:
            base -= min(0.3, len(prior_failures) * 0.1)
        success_rate = mode_sel.previous_success_rate if hasattr(mode_sel, 'previous_success_rate') else 0.5
        base += (success_rate - 0.5) * 0.2
        return max(0.05, min(0.99, base))

    def get_history(self) -> List[dict]:
        return self._plan_history


def benchmark_against_generic():
    """Compare Planner Specialist against generic local model planning."""
    from ..planning.long_horizon import TaskDecomposer
    generic = TaskDecomposer()
    specialist = PlannerSpecialist()

    tasks = [
        "Fix the authentication bug in login handler",
        "Add pagination to all list endpoints",
        "Refactor the database connection module",
        "What language is this project written in?",
        "Update the README with installation instructions",
    ]

    results = []
    for task in tasks:
        inp = PlannerInput(user_task=task, hardware_profile="standard_gpu")
        spec_out = specialist.process(inp)

        generic_plan = generic.decompose(task)

        results.append({
            "task": task[:60],
            "specialist_subtasks": len(spec_out.task_decomposition),
            "generic_subtasks": len(generic_plan.subtasks),
            "specialist_confidence": round(spec_out.confidence, 3),
            "specialist_risk": spec_out.risk_score,
            "specialist_mode": spec_out.recommended_mode,
            "specialist_files": spec_out.affected_files,
        })

    return {
        "benchmark": "planner_vs_generic",
        "total_tasks": len(tasks),
        "results": results,
        "summary": {
            "avg_confidence": round(sum(r["specialist_confidence"] for r in results) / len(results), 3),
            "modes_used": list(set(r["specialist_mode"] for r in results)),
        }
    }


planner = PlannerSpecialist()
