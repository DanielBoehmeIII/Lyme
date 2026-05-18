from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import json
from pathlib import Path


@dataclass
class MetricPoint:
    name: str
    value: float
    unit: str
    category: str
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "category": self.category,
            "timestamp": self.timestamp,
        }


@dataclass
class ProductivityMetrics:
    repo: str
    total_lyme_time_s: float
    total_manual_estimate_s: float
    ratio: float
    commands_run: int
    successful_commands: int
    failures: int
    avg_response_s: float
    task_completion_rate: float
    metrics: List[MetricPoint] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "total_lyme_time_s": round(self.total_lyme_time_s, 2),
            "total_manual_estimate_s": round(self.total_manual_estimate_s, 2),
            "productivity_ratio": round(self.ratio, 2),
            "commands_run": self.commands_run,
            "successful_commands": self.successful_commands,
            "failures": self.failures,
            "avg_response_s": round(self.avg_response_s, 2),
            "task_completion_rate": round(self.task_completion_rate, 2),
            "metrics": [m.to_dict() for m in self.metrics],
        }


@dataclass
class BeforeAfterComparison:
    repo: str
    before_time_s: float
    after_time_s: float
    speedup_x: float
    before_accuracy: float
    after_accuracy: float
    accuracy_change: float
    human_time_for_task: float

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "before_time_s": round(self.before_time_s, 2),
            "after_time_s": round(self.after_time_s, 2),
            "speedup_x": round(self.speedup_x, 2),
            "before_accuracy": round(self.before_accuracy, 2),
            "after_accuracy": round(self.after_accuracy, 2),
            "accuracy_change": round(self.accuracy_change, 2),
            "human_time_for_task": round(self.human_time_for_task, 2),
        }


class MetricsCollector:
    def __init__(self):
        self.metrics: List[MetricPoint] = []

    def record(self, name: str, value: float, unit: str = "", category: str = "general"):
        self.metrics.append(MetricPoint(
            name=name, value=value, unit=unit,
            category=category, timestamp=time.time(),
        ))

    def compute_productivity(
        self, repo: str, lyme_time_s: float,
        manual_estimate_s: float,
        total_commands: int, successful: int,
    ) -> ProductivityMetrics:
        ratio = manual_estimate_s / lyme_time_s if lyme_time_s > 0 else 0.0
        all_metrics = self.metrics + [
            MetricPoint("lyme_time_s", lyme_time_s, "s", "productivity", time.time()),
            MetricPoint("manual_estimate_s", manual_estimate_s, "s", "productivity", time.time()),
            MetricPoint("productivity_ratio", ratio, "x", "productivity", time.time()),
            MetricPoint("task_completion_rate", successful / total_commands if total_commands > 0 else 0.0, "rate", "quality", time.time()),
        ]
        return ProductivityMetrics(
            repo=repo,
            total_lyme_time_s=lyme_time_s,
            total_manual_estimate_s=manual_estimate_s,
            ratio=ratio,
            commands_run=total_commands,
            successful_commands=successful,
            failures=total_commands - successful,
            avg_response_s=lyme_time_s / total_commands if total_commands > 0 else 0.0,
            task_completion_rate=successful / total_commands if total_commands > 0 else 0.0,
            metrics=all_metrics,
        )

    def compare_before_after(
        self, repo: str, task_description: str,
        human_minutes: float, lyme_seconds: float,
        manual_accuracy: float, lyme_accuracy: float,
    ) -> BeforeAfterComparison:
        human_seconds = human_minutes * 60
        speedup = human_seconds / lyme_seconds if lyme_seconds > 0 else 0.0
        return BeforeAfterComparison(
            repo=repo,
            before_time_s=human_seconds,
            after_time_s=lyme_seconds,
            speedup_x=speedup,
            before_accuracy=manual_accuracy,
            after_accuracy=lyme_accuracy,
            accuracy_change=lyme_accuracy - manual_accuracy,
            human_time_for_task=human_seconds,
        )

    def export_json(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "metrics": [m.to_dict() for m in self.metrics],
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        path.write_text(json.dumps(data, indent=2))

    def print_dashboard(self):
        print(f"{'='*60}")
        print(f"  METRICS DASHBOARD")
        print(f"{'='*60}")
        categories = {}
        for m in self.metrics:
            categories.setdefault(m.category, []).append(m)
        for cat, items in categories.items():
            print(f"\n  [{cat}]")
            for m in items:
                unit_str = f" {m.unit}" if m.unit else ""
                print(f"    {m.name:30s} {m.value:>10.2f}{unit_str}")


metrics_collector = MetricsCollector()
