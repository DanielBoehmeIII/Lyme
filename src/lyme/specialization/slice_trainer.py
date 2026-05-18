"""SliceTrainer — manages training of narrow task-specific adapters."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class TrainingStatus(str, Enum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingRun:
    id: str
    slice_type: str
    base_model: str
    dataset_size: int
    epochs: int
    learning_rate: float
    batch_size: int
    status: TrainingStatus
    duration_sec: float
    final_loss: Optional[float]
    eval_score: Optional[float]
    created_at: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "slice_type": self.slice_type,
            "base_model": self.base_model,
            "dataset_size": self.dataset_size,
            "epochs": self.epochs,
            "status": self.status.value,
            "duration_sec": round(self.duration_sec, 1),
            "final_loss": round(self.final_loss, 4) if self.final_loss else None,
            "eval_score": round(self.eval_score, 4) if self.eval_score else None,
        }


@dataclass
class TrainingRecommendation:
    slice_type: str
    priority: str
    dataset_size_needed: int
    expected_improvement: str
    rationale: str

    def to_dict(self) -> Dict:
        return {
            "slice_type": self.slice_type,
            "priority": self.priority,
            "dataset_size_needed": self.dataset_size_needed,
            "expected_improvement": self.expected_improvement,
        }


@dataclass
class SliceTrainerReport:
    total_runs: int
    runs_by_slice: Dict[str, int]
    completed_runs: int
    avg_final_loss: Optional[float]
    avg_eval_score: Optional[float]
    recommendations: List[TrainingRecommendation]
    insights: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  SLICE TRAINER REPORT")
        lines.append("=" * 70)
        lines.append(f"  Training Runs: {self.total_runs} | "
                     f"Completed: {self.completed_runs}")
        if self.avg_eval_score:
            lines.append(f"  Avg Eval Score: {self.avg_eval_score:.4f}")
        if self.avg_final_loss:
            lines.append(f"  Avg Final Loss: {self.avg_final_loss:.4f}")
        lines.append("")
        lines.append("  By Slice:")
        for st, count in sorted(self.runs_by_slice.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 15)
            lines.append(f"    {st}: {count} {bar}")
        if self.recommendations:
            lines.append("")
            lines.append("  Recommendations:")
            for r in self.recommendations:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                lines.append(f"    {priority_icon.get(r.priority, '•')} [{r.priority}] "
                             f"{r.slice_type}: {r.rationale[:60]}")
        if self.insights:
            lines.append("-" * 70)
            for ins in self.insights:
                lines.append(f"  • {ins}")
        lines.append("=" * 70)
        return "\n".join(lines)


class SliceTrainer:
    def __init__(self):
        self._runs: List[TrainingRun] = []
        self._training_fn: Optional[Callable] = None

    def register_trainer(self, trainer_fn: Callable) -> None:
        self._training_fn = trainer_fn

    def recommend_training(self, slice_type: str, current_success_rate: float,
                           total_examples: int) -> Optional[TrainingRecommendation]:
        if total_examples < 100:
            return TrainingRecommendation(
                slice_type=slice_type,
                priority="high",
                dataset_size_needed=500 - total_examples,
                expected_improvement="+15-25% success rate",
                rationale=f"Only {total_examples} examples — minimum 500 needed for reliable training",
            )
        if current_success_rate < 0.6 and total_examples > 200:
            return TrainingRecommendation(
                slice_type=slice_type,
                priority="high",
                dataset_size_needed=200,
                expected_improvement="+10-20% success rate",
                rationale=f"Current success rate {current_success_rate:.0%} well below target",
            )
        if current_success_rate < 0.8 and total_examples > 500:
            return TrainingRecommendation(
                slice_type=slice_type,
                priority="medium",
                dataset_size_needed=500,
                expected_improvement="+5-15% success rate",
                rationale=f"Room for improvement: {current_success_rate:.0%} → 80%+ target",
            )
        return None

    def analyze(self) -> SliceTrainerReport:
        if not self._runs:
            return SliceTrainerReport(
                total_runs=0, runs_by_slice={}, completed_runs=0,
                avg_final_loss=None, avg_eval_score=None,
                recommendations=[], insights=["No training runs recorded"],
            )

        by_slice: Dict[str, int] = {}
        for r in self._runs:
            by_slice[r.slice_type] = by_slice.get(r.slice_type, 0) + 1

        completed = [r for r in self._runs if r.status == TrainingStatus.COMPLETED]
        losses = [r.final_loss for r in completed if r.final_loss is not None]
        scores = [r.eval_score for r in completed if r.eval_score is not None]

        recommendations: List[TrainingRecommendation] = []
        rec = self.recommend_training("bug_localization", 0.7, 300)
        if rec:
            recommendations.append(rec)

        insights: List[str] = []
        if completed:
            best = max(completed, key=lambda r: r.eval_score or 0)
            insights.append(f"Best run: {best.slice_type} "
                           f"(eval={best.eval_score:.4f}, loss={best.final_loss:.4f})")
        running = [r for r in self._runs if r.status == TrainingStatus.RUNNING]
        if running:
            insights.append(f"{len(running)} runs in progress")

        return SliceTrainerReport(
            total_runs=len(self._runs),
            runs_by_slice=by_slice,
            completed_runs=len(completed),
            avg_final_loss=sum(losses) / max(len(losses), 1) if losses else None,
            avg_eval_score=sum(scores) / max(len(scores), 1) if scores else None,
            recommendations=recommendations,
            insights=insights,
        )
