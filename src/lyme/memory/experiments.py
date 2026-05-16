import math
import random
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict

from .store import MemoryStore, MemoryEntry
from .distillation import MemoryDistillationLoop, ProceduralMemory


@dataclass
class TrialResult:
    trial_num: int = 0
    condition: str = ""
    task_id: str = ""
    success: bool = False
    time_to_completion_ms: float = 0.0
    file_reads: int = 0
    failed_edits: int = 0
    repeated_mistakes: int = 0
    test_passed: bool = False
    memory_hits: int = 0

    def to_dict(self) -> dict:
        return {
            "trial_num": self.trial_num,
            "condition": self.condition,
            "task_id": self.task_id,
            "success": self.success,
            "time_to_completion_ms": self.time_to_completion_ms,
            "file_reads": self.file_reads,
            "failed_edits": self.failed_edits,
            "repeated_mistakes": self.repeated_mistakes,
            "test_passed": self.test_passed,
            "memory_hits": self.memory_hits,
        }


@dataclass
class ComparisonResult:
    with_memory: List[TrialResult] = field(default_factory=list)
    without_memory: List[TrialResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "with_memory": [t.to_dict() for t in self.with_memory],
            "without_memory": [t.to_dict() for t in self.without_memory],
        }


@dataclass
class AggregateMetrics:
    mean: float = 0.0
    median: float = 0.0
    stddev: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    count: int = 0

    @classmethod
    def from_values(cls, values: List[float]) -> "AggregateMetrics":
        if not values:
            return cls()
        return cls(
            mean=statistics.mean(values),
            median=statistics.median(values),
            stddev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min_val=min(values),
            max_val=max(values),
            count=len(values),
        )

    def to_dict(self) -> dict:
        return {
            "mean": self.mean,
            "median": self.median,
            "stddev": self.stddev,
            "min": self.min_val,
            "max": self.max_val,
            "count": self.count,
        }


@dataclass
class ExperimentReport:
    experiment_id: str = ""
    num_trials: int = 0
    task_success_rate: Dict[str, AggregateMetrics] = field(default_factory=dict)
    time_to_completion: Dict[str, AggregateMetrics] = field(default_factory=dict)
    file_reads_reduced: float = 0.0
    failed_edits_reduced: float = 0.0
    repeated_mistakes_reduced: float = 0.0
    test_pass_rate: Dict[str, float] = field(default_factory=dict)
    effect_size: float = 0.0
    p_value: float = 1.0
    significant: bool = False
    raw: ComparisonResult = field(default_factory=ComparisonResult)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "num_trials": self.num_trials,
            "task_success_rate": {k: v.to_dict() for k, v in self.task_success_rate.items()},
            "time_to_completion": {k: v.to_dict() for k, v in self.time_to_completion.items()},
            "file_reads_reduced": self.file_reads_reduced,
            "failed_edits_reduced": self.failed_edits_reduced,
            "repeated_mistakes_reduced": self.repeated_mistakes_reduced,
            "test_pass_rate": self.test_pass_rate,
            "effect_size": self.effect_size,
            "p_value": self.p_value,
            "significant": self.significant,
        }


ModelAdapter = Callable[[str, Optional[dict]], dict]


class DistillationExperiment:
    def __init__(self, store: Optional[MemoryStore] = None,
                 distillation: Optional[MemoryDistillationLoop] = None,
                 num_trials: int = 5):
        self.store = store or MemoryStore()
        self.distillation = distillation or MemoryDistillationLoop(store=self.store)
        self.num_trials = num_trials
        self._results: List[ExperimentReport] = []

    def run_comparison(self, task_set: List[Dict[str, Any]],
                       model_adapter: ModelAdapter) -> ExperimentReport:
        experiment_id = uuid.uuid4().hex[:12]
        comparison = ComparisonResult()

        for task in task_set:
            task_desc = task.get("description", "")
            task_id = task.get("id", uuid.uuid4().hex[:8])

            for trial_num in range(self.num_trials):
                without = self._run_trial(
                    trial_num=trial_num,
                    task=task,
                    model_adapter=model_adapter,
                    use_memory=False,
                )
                comparison.without_memory.append(without)

            for trial_num in range(self.num_trials):
                relevant = self.distillation.get_relevant_memory(task_desc)
                context = {"memory_hints": [pm.to_dict() for pm in relevant]} if relevant else None
                trial_context = {"description": task_desc, "repo_context": task.get("repo", "")}
                applied = self.distillation.apply_memory(trial_context) if relevant else None

                with_memory = self._run_trial(
                    trial_num=trial_num,
                    task=task,
                    model_adapter=model_adapter,
                    use_memory=True,
                    memory_context=context,
                )
                comparison.with_memory.append(with_memory)

                if applied and with_memory.success:
                    self.distillation.update_confidence(applied["procedural_id"], True)
                elif applied:
                    self.distillation.update_confidence(applied["procedural_id"], False)

            trace_data = self._build_trace_data(task, comparison)
            self.distillation.distill_from_trace(trace_data)

        report = self.generate_report(comparison)
        report.experiment_id = experiment_id
        report.num_trials = self.num_trials
        self._results.append(report)
        return report

    def _run_trial(self, trial_num: int, task: dict,
                   model_adapter: ModelAdapter,
                   use_memory: bool,
                   memory_context: Optional[dict] = None) -> TrialResult:
        condition = "with_memory" if use_memory else "without_memory"
        task_id = task.get("id", uuid.uuid4().hex[:8])
        task_desc = task.get("description", "")

        start = time.time()
        try:
            result = model_adapter(task_desc, memory_context)
            duration = (time.time() - start) * 1000
        except Exception:
            return TrialResult(
                trial_num=trial_num, condition=condition, task_id=task_id,
                success=False, time_to_completion_ms=(time.time() - start) * 1000,
                file_reads=0, failed_edits=1, repeated_mistakes=0, test_passed=False,
            )

        return TrialResult(
            trial_num=trial_num,
            condition=condition,
            task_id=task_id,
            success=result.get("success", False),
            time_to_completion_ms=result.get("duration_ms", duration),
            file_reads=result.get("file_reads", 0),
            failed_edits=result.get("failed_edits", 0),
            repeated_mistakes=result.get("repeated_mistakes", 0),
            test_passed=result.get("test_passed", False),
            memory_hits=result.get("memory_hits", 0) if use_memory else 0,
        )

    def generate_report(self, results: ComparisonResult) -> ExperimentReport:
        report = ExperimentReport(raw=results)

        for condition, label in [(results.with_memory, "with_memory"),
                                  (results.without_memory, "without_memory")]:
            success_vals = [1.0 if t.success else 0.0 for t in condition]
            time_vals = [t.time_to_completion_ms for t in condition]
            pass_vals = [1.0 if t.test_passed else 0.0 for t in condition]

            report.task_success_rate[label] = AggregateMetrics.from_values(success_vals)
            report.time_to_completion[label] = AggregateMetrics.from_values(time_vals)
            report.test_pass_rate[label] = statistics.mean(pass_vals) if pass_vals else 0.0

        wm = results.with_memory
        wo = results.without_memory

        if wm and wo:
            avg_reads_with = statistics.mean([t.file_reads for t in wm])
            avg_reads_without = statistics.mean([t.file_reads for t in wo])
            report.file_reads_reduced = (
                (avg_reads_without - avg_reads_with) / avg_reads_without
                if avg_reads_without > 0 else 0.0
            )

            avg_edits_with = statistics.mean([t.failed_edits for t in wm])
            avg_edits_without = statistics.mean([t.failed_edits for t in wo])
            report.failed_edits_reduced = (
                (avg_edits_without - avg_edits_with) / avg_edits_without
                if avg_edits_without > 0 else 0.0
            )

            avg_mistakes_with = statistics.mean([t.repeated_mistakes for t in wm])
            avg_mistakes_without = statistics.mean([t.repeated_mistakes for t in wo])
            report.repeated_mistakes_reduced = (
                (avg_mistakes_without - avg_mistakes_with) / avg_mistakes_without
                if avg_mistakes_without > 0 else 0.0
            )

        hypothesis = self.produce_hypothesis_test(results)
        report.effect_size = hypothesis.get("cohens_d", 0.0)
        report.p_value = hypothesis.get("p_value", 1.0)
        report.significant = hypothesis.get("significant", False)

        return report

    def produce_hypothesis_test(self, results: ComparisonResult) -> dict:
        wm_success = [1.0 if t.success else 0.0 for t in results.with_memory]
        wo_success = [1.0 if t.success else 0.0 for t in results.without_memory]

        if len(wm_success) < 2 or len(wo_success) < 2:
            return {"cohens_d": 0.0, "p_value": 1.0, "significant": False, "note": "insufficient_trials"}

        mean_wm = statistics.mean(wm_success)
        mean_wo = statistics.mean(wo_success)

        var_wm = statistics.variance(wm_success) if len(wm_success) > 1 else 0
        var_wo = statistics.variance(wo_success) if len(wo_success) > 1 else 0

        pooled = math.sqrt(((len(wm_success) - 1) * var_wm + (len(wo_success) - 1) * var_wo)
                           / (len(wm_success) + len(wo_success) - 2))
        cohens_d = (mean_wm - mean_wo) / pooled if pooled > 0 else 0.0

        se = math.sqrt(var_wm / len(wm_success) + var_wo / len(wo_success))
        t_stat = (mean_wm - mean_wo) / se if se > 0 else 0.0
        df = len(wm_success) + len(wo_success) - 2
        p_value = self._approximate_p_value(t_stat, df)

        return {
            "cohens_d": cohens_d,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "t_statistic": t_stat,
            "degrees_of_freedom": df,
            "mean_with_memory": mean_wm,
            "mean_without_memory": mean_wo,
        }

    def _approximate_p_value(self, t_stat: float, df: int) -> float:
        x = df / (df + t_stat * t_stat)
        if df % 2 == 0:
            p = 1 - x
            for k in range(1, df // 2):
                p += (math.comb(df // 2 - 1, k) * ((-x) ** k)) / (2 * k - 1)
            p *= 0.5 * math.sqrt(x)
        else:
            p = math.atanh(math.sqrt(x))
            for k in range(1, (df - 1) // 2 + 1):
                p += (x ** k) / (2 * k - 1)
            p *= 2 * math.sqrt(1 - x) / math.pi
        return min(1.0, abs(p) + 0.01)

    def get_results(self) -> List[ExperimentReport]:
        return self._results

    def generate_summary(self, report: ExperimentReport) -> str:
        lines = [
            f"# Distillation Experiment: {report.experiment_id}",
            f"",
            f"- **Trials per condition**: {report.num_trials}",
            f"- **Effect size (Cohen's d)**: {report.effect_size:.3f}",
            f"- **p-value**: {report.p_value:.4f}",
            f"- **Statistically significant**: {report.significant}",
            f"",
            f"## Task Success Rate",
            f"",
            f"| Condition | Mean | Median | StdDev |",
            f"|-----------|------|--------|--------|",
        ]
        for label in ("with_memory", "without_memory"):
            m = report.task_success_rate.get(label, AggregateMetrics())
            lines.append(f"| {label} | {m.mean:.3f} | {m.median:.3f} | {m.stddev:.3f} |")

        lines.extend([
            f"",
            f"## Time to Completion",
            f"",
            f"| Condition | Mean (ms) | Median (ms) | StdDev |",
            f"|-----------|-----------|-------------|--------|",
        ])
        for label in ("with_memory", "without_memory"):
            m = report.time_to_completion.get(label, AggregateMetrics())
            lines.append(f"| {label} | {m.mean:.1f} | {m.median:.1f} | {m.stddev:.1f} |")

        lines.extend([
            f"",
            f"## Improvement Metrics",
            f"",
            f"- **File reads reduced**: {report.file_reads_reduced:.1%}",
            f"- **Failed edits reduced**: {report.failed_edits_reduced:.1%}",
            f"- **Repeated mistakes reduced**: {report.repeated_mistakes_reduced:.1%}",
            f"",
            f"## Test Pass Rate",
            f"",
        ])
        for label in ("with_memory", "without_memory"):
            rate = report.test_pass_rate.get(label, 0.0)
            lines.append(f"- **{label}**: {rate:.1%}")

        return "\n".join(lines)

    def _build_trace_data(self, task: dict, comparison: ComparisonResult) -> dict:
        all_trials = comparison.with_memory + comparison.without_memory
        successes = sum(1 for t in all_trials if t.success)
        total = len(all_trials) or 1
        return {
            "trace_id": uuid.uuid4().hex[:16],
            "scenario_name": task.get("id", "unknown"),
            "start_time": time.time(),
            "steps": [{"type": "decision", "content": t.task_id, "confidence": 1.0 if t.success else 0.3}
                      for t in all_trials],
            "decisions": [{"chosen": t.condition, "outcome": "success" if t.success else "failure"}
                          for t in all_trials],
            "summary": {
                "status": "completed",
                "success_rate": successes / total,
                "error_count": total - successes,
                "total_steps": total,
            },
        }
