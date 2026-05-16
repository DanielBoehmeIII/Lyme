"""Week 75 — Retrieval Policy Experiment Framework.

Runs retrieval policies against tasks and measures:
- task success, context size, latency
- irrelevant context rate, missing evidence rate, hallucination rate
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import time
import json

from .policies import RetrievalResult, RETRIEVAL_POLICIES


@dataclass
class RetrievalTrial:
    policy_name: str
    task: str
    result: RetrievalResult
    success: bool = False
    ground_truth_files: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def irrelevant_context_rate(self) -> float:
        if not self.result.files:
            return 0.0
        retrieved_paths = {f["path"] for f in self.result.files}
        gt_set = set(self.ground_truth_files)
        if not gt_set:
            return 0.0
        irrelevant = retrieved_paths - gt_set
        return len(irrelevant) / len(retrieved_paths) if retrieved_paths else 0.0

    @property
    def missing_evidence_rate(self) -> float:
        if not self.ground_truth_files:
            return 0.0
        retrieved_paths = {f["path"] for f in self.result.files}
        gt_set = set(self.ground_truth_files)
        missing = gt_set - retrieved_paths
        return len(missing) / len(gt_set) if gt_set else 0.0

    def to_dict(self) -> dict:
        return {
            "policy_name": self.policy_name,
            "task": self.task[:80],
            "success": self.success,
            "result": self.result.to_dict(),
            "ground_truth_files": self.ground_truth_files,
            "irrelevant_context_rate": self.irrelevant_context_rate,
            "missing_evidence_rate": self.missing_evidence_rate,
            "timestamp": self.timestamp,
        }


@dataclass
class ExperimentReport:
    policy_results: Dict[str, Dict] = field(default_factory=dict)
    winner: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "policy_results": self.policy_results,
            "winner": self.winner,
            "summary": self.summary,
        }

    def to_markdown(self) -> str:
        lines = ["# Retrieval Policy Experiment Report", ""]
        lines.append(f"**Winner**: {self.winner}")
        lines.append("")
        lines.append(self.summary)
        lines.append("")
        lines.append("## Per-Policy Results")
        lines.append("")
        for pname, presults in sorted(self.policy_results.items()):
            lines.append(f"### {pname}")
            for k, v in presults.items():
                if isinstance(v, float):
                    lines.append(f"- {k}: {v:.4f}")
                else:
                    lines.append(f"- {k}: {v}")
            lines.append("")
        return "\n".join(lines)


class RetrievalExperiment:
    """Run retrieval policies against a set of tasks and compare results."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.trials: List[RetrievalTrial] = []

    def run_trial(
        self,
        policy: str,
        task: str,
        ground_truth_files: Optional[List[str]] = None,
    ) -> RetrievalTrial:
        """Run a single retrieval trial."""
        for p in RETRIEVAL_POLICIES:
            if p.name == policy:
                result = p.retrieve(task, self.repo_path)
                retrieved_paths = {f["path"] for f in result.files}
                gt = set(ground_truth_files or [])
                success = bool(gt and retrieved_paths & gt)

                trial = RetrievalTrial(
                    policy_name=policy,
                    task=task,
                    result=result,
                    success=success,
                    ground_truth_files=ground_truth_files or [],
                )
                self.trials.append(trial)
                return trial
        raise ValueError(f"Unknown policy: {policy}")

    def run_all_policies(
        self,
        task: str,
        ground_truth_files: Optional[List[str]] = None,
    ) -> List[RetrievalTrial]:
        """Run all policies on the same task."""
        trials = []
        for p in RETRIEVAL_POLICIES:
            trial = self.run_trial(p.name, task, ground_truth_files)
            trials.append(trial)
        return trials

    def report(self) -> ExperimentReport:
        """Generate comparison report across all trials."""
        if not self.trials:
            return ExperimentReport(summary="No trials run.")

        by_policy: Dict[str, List[RetrievalTrial]] = {}
        for t in self.trials:
            by_policy.setdefault(t.policy_name, []).append(t)

        policy_results = {}
        for pname, trials in by_policy.items():
            n = len(trials)
            success_rate = sum(1 for t in trials if t.success) / n if n > 0 else 0
            avg_latency = sum(t.result.latency_ms for t in trials) / n if n > 0 else 0
            avg_context = sum(t.result.context_size_tokens for t in trials) / n if n > 0 else 0
            avg_irrelevant = sum(t.irrelevant_context_rate for t in trials) / n if n > 0 else 0
            avg_missing = sum(t.missing_evidence_rate for t in trials) / n if n > 0 else 0

            policy_results[pname] = {
                "trials": n,
                "success_rate": success_rate,
                "avg_latency_ms": round(avg_latency, 1),
                "avg_context_tokens": round(avg_context, 1),
                "avg_irrelevant_rate": round(avg_irrelevant, 4),
                "avg_missing_evidence_rate": round(avg_missing, 4),
            }

        # Determine winner: highest success rate, then lowest irrelevant rate
        scored = sorted(
            policy_results.items(),
            key=lambda x: (x[1]["success_rate"], -x[1]["avg_irrelevant_rate"]),
            reverse=True,
        )
        winner = scored[0][0] if scored else ""

        lines = [
            f"Compared {len(policy_results)} retrieval policies across {len(self.trials)} trials.",
            f"Winner: {winner} (success rate: {scored[0][1]['success_rate']:.1%}, "
            f"irrelevant rate: {scored[0][1]['avg_irrelevant_rate']:.1%})"
            if scored else "No data.",
        ]

        return ExperimentReport(
            policy_results=policy_results,
            winner=winner,
            summary="\n".join(lines),
        )


def run_comparison(
    repo_path: str,
    tasks: List[str],
    ground_truth_map: Dict[str, List[str]],
) -> ExperimentReport:
    """Convenience: run all policies against multiple tasks and compare."""
    experiment = RetrievalExperiment(repo_path)
    for task in tasks:
        gt = ground_truth_map.get(task, [])
        experiment.run_all_policies(task, gt)
    return experiment.report()
