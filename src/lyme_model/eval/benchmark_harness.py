"""Week 5 — Model Benchmark Harness v0.

Measures model performance across:
- Repo identification
- Build/test command discovery
- Risky file identification
- Bug localization
- File explanation

Metrics: correctness, evidence usage, hallucinations, latency, tool calls, context size
Integrates with Lyme Audit reports.
"""

from __future__ import annotations
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path
from collections import Counter

from lyme_model.context.improved import ImprovedContextCompiler
from lyme_model.slices.qa_engine import QAEngine


@dataclass
class BenchmarkTask:
    name: str
    category: str
    prompt: str
    expected_keywords: List[str] = field(default_factory=list)
    expected_files: List[str] = field(default_factory=list)
    difficulty: str = "medium"


@dataclass
class TaskResult:
    task_name: str
    category: str
    success: bool = False
    latency_s: float = 0.0
    evidence_count: int = 0
    keyword_match: float = 0.0
    output_preview: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkReport:
    run_id: str
    timestamp: str
    total_tasks: int = 0
    passed: int = 0
    failed: int = 0
    avg_latency_s: float = 0.0
    avg_evidence: float = 0.0
    avg_keyword_match: float = 0.0
    categories: Dict = field(default_factory=dict)
    results: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


BENCHMARK_TASKS = [
    BenchmarkTask("repo_language", "repo_id", "What language is this project?", ["python", "javascript", "typescript"]),
    BenchmarkTask("repo_framework", "repo_id", "What framework is used?", ["flask", "django", "fastapi", "react", "pytest"]),
    BenchmarkTask("build_command", "commands", "How is this project built?", ["pip", "npm", "make", "build"]),
    BenchmarkTask("test_command", "commands", "How are tests run?", ["pytest", "test", "npm test"]),
    BenchmarkTask("risky_files", "risk", "What risky or sensitive files exist?", ["secret", "password", "token", "auth", "key"]),
    BenchmarkTask("entry_points", "repo_id", "What are the entry points?", ["main", "cli", "app"]),
    BenchmarkTask("file_structure", "repo_id", "Describe the file structure", ["src", "tests", "config", "docs"]),
    BenchmarkTask("recent_changes", "repo_id", "What recent changes were made?", ["fix", "add", "update", "merge"]),
]

REGRESSION_TASKS = [
    BenchmarkTask("function_lookup", "bug_localization", "Find where function X is defined", ["def"], difficulty="hard"),
    BenchmarkTask("class_location", "bug_localization", "Find where class Y is defined", ["class"], difficulty="hard"),
    BenchmarkTask("import_chain", "bug_localization", "Trace the imports for module Z", ["import", "from"], difficulty="hard"),
]


class ModelBenchmarkHarness:
    """General benchmark harness for model capabilities."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.qa = QAEngine(str(self.repo_path))
        self.compiler = ImprovedContextCompiler(str(self.repo_path))

    def run_benchmark(self, tasks: Optional[List[BenchmarkTask]] = None) -> BenchmarkReport:
        """Run benchmark on given tasks (default: standard suite)."""
        if tasks is None:
            tasks = BENCHMARK_TASKS

        start = time.time()
        run_id = str(uuid.uuid4())[:8]
        report = BenchmarkReport(
            run_id=run_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            total_tasks=len(tasks),
        )

        category_results: Dict[str, List[float]] = {}

        for task in tasks:
            task_start = time.time()
            try:
                result = self._evaluate_task(task)
                result.latency_s = round(time.time() - task_start, 3)
            except Exception as e:
                result = TaskResult(task_name=task.name, category=task.category, error=str(e))

            report.results.append(result.to_dict())

            if result.success:
                report.passed += 1
            else:
                report.failed += 1

            category_results.setdefault(task.category, []).append(1.0 if result.success else 0.0)

            report.avg_latency_s += result.latency_s
            report.avg_evidence += result.evidence_count
            report.avg_keyword_match += result.keyword_match

        if report.total_tasks > 0:
            report.avg_latency_s = round(report.avg_latency_s / report.total_tasks, 3)
            report.avg_evidence = round(report.avg_evidence / report.total_tasks, 1)
            report.avg_keyword_match = round(report.avg_keyword_match / report.total_tasks, 2)

        report.categories = {
            cat: {"success_rate": round(sum(scores) / len(scores), 2), "count": len(scores)}
            for cat, scores in category_results.items()
        }

        self._save_report(report)
        return report

    def _evaluate_task(self, task: BenchmarkTask) -> TaskResult:
        """Evaluate a single benchmark task."""
        qa_result = self.qa.answer(task.prompt)

        result = TaskResult(task_name=task.name, category=task.category)
        result.evidence_count = len(qa_result.evidence)

        if qa_result.refused:
            result.success = False
            result.error = qa_result.refusal_reason
            return result

        combined = qa_result.answer.lower()
        if task.expected_keywords:
            matches = sum(1 for kw in task.expected_keywords if kw.lower() in combined)
            result.keyword_match = round(matches / len(task.expected_keywords), 2)

        result.success = result.keyword_match >= 0.2 or not task.expected_keywords
        result.output_preview = qa_result.answer[:200]

        return result

    def run_regression(self) -> BenchmarkReport:
        """Run regression detection (harder tasks)."""
        return self.run_benchmark(REGRESSION_TASKS)

    def run_all(self) -> Dict:
        """Run all benchmarks and produce summary."""
        standard = self.run_benchmark(BENCHMARK_TASKS)
        regression = self.run_regression()

        return {
            "standard": standard.to_dict(),
            "regression": regression.to_dict(),
            "combined": {
                "total_tasks": standard.total_tasks + regression.total_tasks,
                "passed": standard.passed + regression.passed,
                "failed": standard.failed + regression.failed,
                "avg_latency_s": round(
                    (standard.avg_latency_s * standard.total_tasks + regression.avg_latency_s * regression.total_tasks)
                    / max(standard.total_tasks + regression.total_tasks, 1), 3
                ),
            },
        }

    def _save_report(self, report: BenchmarkReport) -> None:
        """Save benchmark report to disk and emit audit trace."""
        out_path = Path("lyme-output") / "benchmarks" / f"harness-{report.run_id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report.to_dict(), indent=2))

        trace = {
            "event": "benchmark_completed",
            "run_id": report.run_id,
            "total_tasks": report.total_tasks,
            "passed": report.passed,
            "failed": report.failed,
            "avg_latency_s": report.avg_latency_s,
            "avg_evidence": report.avg_evidence,
            "categories": report.categories,
        }
        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"benchmark-{report.run_id}.json"
        trace_file.write_text(json.dumps(trace, indent=2))


def run_model_benchmark(repo_path: str = ".") -> Dict:
    """Run full model benchmark and return results."""
    harness = ModelBenchmarkHarness(repo_path)
    return harness.run_all()
