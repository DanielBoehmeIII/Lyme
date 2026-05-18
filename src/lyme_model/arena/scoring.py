"""ArenaScorer — normalized scoring across tools.

Produces 0-1 normalized scores for each dimension,
then aggregates into a final score per tool.
"""

from __future__ import annotations
from typing import Dict, List
from .models import ArenaRun, ToolResult, ScoringDimension


class NormalizedScore:
    """Normalized score across dimensions."""

    def __init__(self):
        self.dimensions: Dict[str, float] = {}
        self.final: float = 0.0

    def to_dict(self) -> dict:
        return {
            "dimensions": self.dimensions,
            "final": self.final,
        }


class ArenaScorer:
    """Normalize and score arena results."""

    WEIGHTS = {
        ScoringDimension.CORRECTNESS: 0.30,
        ScoringDimension.TEST_PASS_RATE: 0.25,
        ScoringDimension.TIME: 0.10,
        ScoringDimension.COST: 0.10,
        ScoringDimension.FILES_TOUCHED: 0.05,
        ScoringDimension.ROLLBACK_COUNT: 0.05,
        ScoringDimension.HUMAN_INTERVENTION: 0.15,
    }

    def score_run(self, run: ArenaRun) -> ArenaRun:
        tool_scores: Dict[str, NormalizedScore] = {}

        for tool_key, results in run.results.items():
            score = self._score_tool(tool_key, results, run.results)
            tool_scores[tool_key] = score

        run.scores = {k: v.to_dict() for k, v in tool_scores.items()}
        run.summary = self._build_summary(tool_scores)
        return run

    def _score_tool(self, tool_key: str, results: List[ToolResult],
                    all_results: Dict[str, List[ToolResult]]) -> NormalizedScore:
        ns = NormalizedScore()

        if not results:
            ns.final = 0.0
            return ns

        avg_correctness = sum(r.correctness for r in results) / len(results)
        avg_test_pass = sum(r.test_pass_rate for r in results) / len(results)
        avg_time = sum(r.duration_s for r in results) / len(results)
        avg_cost = sum(r.cost for r in results) / len(results)
        avg_files = sum(r.files_touched for r in results) / len(results)
        avg_rollback = sum(r.rollback_count for r in results) / len(results)
        intervention_ratio = sum(1 for r in results if r.human_intervention) / len(results)

        max_time = max(
            (sum(r.duration_s for r in res) / len(res))
            for res in all_results.values() if res
        ) if all_results else 1.0
        max_cost = max(
            (sum(r.cost for r in res) / len(res))
            for res in all_results.values() if res
        ) if all_results else 1.0
        max_files = max(
            (sum(r.files_touched for r in res) / len(res))
            for res in all_results.values() if res
        ) if all_results else 1.0
        max_rollback = max(
            (sum(r.rollback_count for r in res) / len(res))
            for res in all_results.values() if res
        ) if all_results else 1.0

        cons_time_here = 1.0 - (avg_time / max_time) if max_time > 0 else 1.0
        cost_score = 1.0 - (avg_cost / max_cost) if max_cost > 0 else 1.0
        files_score = 1.0 - (avg_files / max_files) if max_files > 0 else 1.0
        rollback_score = 1.0 - (avg_rollback / max_rollback) if max_rollback > 0 else 1.0
        intervention_score = 1.0 - intervention_ratio

        ns.dimensions = {
            "correctness": round(avg_correctness, 4),
            "test_pass_rate": round(avg_test_pass, 4),
            "time_efficiency": round(cons_time_here, 4),
            "cost_efficiency": round(cost_score, 4),
            "files_efficiency": round(files_score, 4),
            "rollback_avoidance": round(rollback_score, 4),
            "autonomy": round(intervention_score, 4),
        }

        weighted = (
            self.WEIGHTS[ScoringDimension.CORRECTNESS] * avg_correctness
            + self.WEIGHTS[ScoringDimension.TEST_PASS_RATE] * avg_test_pass
            + self.WEIGHTS[ScoringDimension.TIME] * cons_time_here
            + self.WEIGHTS[ScoringDimension.COST] * cost_score
            + self.WEIGHTS[ScoringDimension.FILES_TOUCHED] * files_score
            + self.WEIGHTS[ScoringDimension.ROLLBACK_COUNT] * rollback_score
            + self.WEIGHTS[ScoringDimension.HUMAN_INTERVENTION] * intervention_score
        )
        ns.final = round(weighted, 4)
        return ns

    def _build_summary(self, tool_scores: Dict[str, NormalizedScore]) -> dict:
        ranked = sorted(
            tool_scores.items(),
            key=lambda x: x[1].final,
            reverse=True,
        )
        return {
            "rankings": [
                {"rank": i + 1, "tool": tool, "final_score": score.final,
                 "dimensions": score.dimensions}
                for i, (tool, score) in enumerate(ranked)
            ],
            "tool_count": len(ranked),
            "winner": ranked[0][0] if ranked else None,
            "winner_score": ranked[0][1].final if ranked else 0.0,
        }
