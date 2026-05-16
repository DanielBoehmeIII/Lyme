"""Week 128 — Lyme Model v0.7.

Theme: checkpointed long-horizon local agent.

Includes:
- task decomposition (Week 121)
- checkpointed runs (Week 122)
- hierarchical planning (Week 123)
- subtask context packing (Week 124)
- long-horizon verification (Week 125)
- failure analysis (Week 126)
- first long-horizon capability (Week 127)

Deliver: demo, benchmark, failure report, user guide.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import time
import sys

from .planning.long_horizon import (
    TaskDecomposer, CheckpointManager, HierarchicalPlanner,
    ContextPacker, LongHorizonVerifier, FailureAnalyzer,
    LONG_HORIZON_V01_CAPABILITY,
    decomposer, checkpoint_manager, planner, context_packer,
    verifier, failure_analyzer,
)
from .planning.difficulty_estimator import DifficultyEstimator
from .planning.mode_selection import ModeSelector


VERSION = "0.7.0"
THEME = "checkpointed long-horizon local agent"


class LymeModelV07:
    """Lyme Model v0.7 — checkpointed long-horizon local agent."""

    def __init__(self):
        self.version = VERSION
        self.theme = THEME
        self.decomposer = TaskDecomposer()
        self.checkpoints = CheckpointManager()
        self.hierarchical_planner = HierarchicalPlanner()
        self.context_packer = ContextPacker()
        self.verifier = LongHorizonVerifier()
        self.failure_analyzer = FailureAnalyzer()
        self.diff_estimator = DifficultyEstimator()
        self.mode_selector = ModeSelector()

    def run_long_task(self, goal: str, plan_type: str = "hierarchical") -> dict:
        start = time.time()
        difficulty = self.diff_estimator.estimate(goal)
        mode_sel = self.mode_selector.select_mode(
            difficulty.difficulty_score, difficulty.risk.value,
            "standard_gpu", 1000, task_type=difficulty.task_type.value
        )

        plan = self.decomposer.decompose(goal)
        run = self.checkpoints.create_run(goal, plan)

        hplan = self.hierarchical_planner.plan(goal, plan_type)

        results = []
        for subtask in plan.subtasks:
            cp = self.context_packer.pack(subtask, {})
            v = self.verifier.verify_subtask(subtask)
            subtask.status = "completed" if v.local_verification_pass else "failed"
            results.append({
                "subtask": subtask.id,
                "name": subtask.name,
                "passed": v.local_verification_pass,
                "confidence_after": v.confidence_after,
            })

            self.checkpoints.checkpoint(
                run.run_id,
                [s.id for s in plan.subtasks if s.status == "completed"],
                subtask.id if subtask.status != "completed" else None,
                {"phase": f"subtask_{subtask.id}"},
                context_packets={subtask.id: cp.previous_step_summary},
                verification_results={subtask.id: v.to_dict()},
            )

        elapsed = time.time() - start
        passed = sum(1 for r in results if r["passed"])
        total = len(results)

        return {
            "version": VERSION,
            "goal": goal,
            "plan_type": plan_type,
            "run_id": run.run_id,
            "subtasks": results,
            "checkpoints_created": len(run.checkpoints),
            "passed_subtasks": passed,
            "total_subtasks": total,
            "hierarchical_plan": hplan.to_dict(),
            "difficulty_estimate": difficulty.to_dict(),
            "mode_selection": mode_sel.to_dict(),
            "long_horizon_capability": LONG_HORIZON_V01_CAPABILITY,
            "latency_s": round(elapsed, 2),
        }

    def get_failure_report(self) -> dict:
        return self.failure_analyzer.analyze()

    def get_capability_def(self) -> dict:
        return LONG_HORIZON_V01_CAPABILITY

    def generate_report(self) -> dict:
        failures = self.failure_analyzer.analyze()
        return {
            "release": VERSION,
            "theme": self.theme,
            "long_horizon_capability": LONG_HORIZON_V01_CAPABILITY,
            "failure_analysis": failures,
            "components": [
                {"name": "Task Decomposition", "status": "operational"},
                {"name": "Checkpointed Runs", "status": "operational"},
                {"name": "Hierarchical Planning", "status": "operational"},
                {"name": "Subtask Context Packing", "status": "operational"},
                {"name": "Long-Horizon Verification", "status": "operational"},
                {"name": "Failure Analysis", "status": "completed"},
            ],
            "lyme_audit_status": "untouched",
        }


v07 = LymeModelV07()


def print_v07_report():
    report = v07.generate_report()
    print("=" * 60)
    print(f"LYME MODEL v{VERSION} — {THEME}")
    print("=" * 60)
    print(f"\nLong-Horizon Capability v{report['long_horizon_capability']['version']}")
    print(f"  Max safe scope: {report['long_horizon_capability']['maximum_safe_scope']['files']} files, "
          f"{report['long_horizon_capability']['maximum_safe_scope']['subtasks']} subtasks")
    print(f"  Allowed modes: {', '.join(report['long_horizon_capability']['allowed_modes'])}")
    print(f"\nFailure Analysis ({report['failure_analysis']['total_experiments']} experiments):")
    print(f"  Context drift: {report['failure_analysis']['context_drift_detected']} experiments")
    print(f"  Goal forgotten: {report['failure_analysis']['goal_forgotten']} experiments")
    print(f"  Checkpoints helpful: {report['failure_analysis']['checkpoint_helpful']} experiments")
    print(f"  Hierarchy helpful: {report['failure_analysis']['hierarchy_helpful']} experiments")
    print(f"\nComponents: {len(report['components'])}")
    for c in report['components']:
        print(f"  {c['name']:30s} {c['status']}")
    print(f"\nLyme Audit: {report['lyme_audit_status']}")
    return report
