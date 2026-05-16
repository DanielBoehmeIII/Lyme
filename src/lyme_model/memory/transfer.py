"""Week 84 — Cross-Repo Transfer Revisited.

Test whether learned skills transfer safely across repos.
Compare: no memory, repo-only memory, global memory, global + critic, global + verification gate.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable


@dataclass
class TransferTrial:
    source_repo: str = ""
    target_repo: str = ""
    policy: str = ""
    task_success: bool = False
    negative_transfer: bool = False
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "policy": self.policy,
            "task_success": self.task_success,
            "negative_transfer": self.negative_transfer,
            "details": self.details[:200],
        }


TRANSFER_POLICIES = [
    "no_memory",
    "repo_only",
    "global_memory",
    "global_memory_with_critic",
    "global_memory_with_verification_gate",
]


class CrossRepoTransferExperiment:
    """Tests whether cross-repo transfer helps or harms local models."""

    def __init__(self):
        self.trials: List[TransferTrial] = []

    def run_trial(self, source: str, target: str, policy: str,
                  task_fn: Callable) -> TransferTrial:
        """Run a single transfer trial."""
        try:
            result = task_fn(source, target, policy)
            success = result.get("success", False)
            negative = result.get("negative_transfer", False)
        except Exception:
            success = False
            negative = True

        trial = TransferTrial(
            source_repo=source,
            target_repo=target,
            policy=policy,
            task_success=success,
            negative_transfer=negative,
        )
        self.trials.append(trial)
        return trial

    def summary(self) -> Dict:
        if not self.trials:
            return {"message": "No trials run", "policy_results": {}}

        by_policy: Dict[str, List[TransferTrial]] = {}
        for t in self.trials:
            by_policy.setdefault(t.policy, []).append(t)

        results = {}
        for policy, trials in by_policy.items():
            n = len(trials)
            success_rate = sum(1 for t in trials if t.task_success) / n if n > 0 else 0
            negative_rate = sum(1 for t in trials if t.negative_transfer) / n if n > 0 else 0
            results[policy] = {
                "trials": n,
                "success_rate": round(success_rate, 4),
                "negative_transfer_rate": round(negative_rate, 4),
            }

        return {
            "policy_results": results,
            "total_trials": len(self.trials),
            "recommendation": self._recommend(results),
        }

    def _recommend(self, results: Dict) -> str:
        best_policy = ""
        best_score = -1
        for policy, r in results.items():
            score = r["success_rate"] - r["negative_transfer_rate"]
            if score > best_score:
                best_score = score
                best_policy = policy
        if best_policy:
            return f"Best policy: {best_policy} (score: {best_score:.2f})"
        return "Insufficient data for recommendation"
