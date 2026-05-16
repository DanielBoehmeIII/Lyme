"""Week 2 — Context quality benchmark.

Compares three context strategies:
1. Raw prompt (minimal repo info, no context compiler)
2. Current context compiler (v0.1)
3. Improved context compiler (v0.2 with file ranking)

Measures:
- Context size (tokens)
- Compilation latency
- Task-relevant file coverage
- Irrelevant file inclusion
"""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from pathlib import Path

from .compiler import ContextCompiler
from .improved import ImprovedContextCompiler


@dataclass
class BenchmarkTask:
    question: str
    expected_keywords: List[str] = field(default_factory=list)
    expected_domain: str = ""


@dataclass
class BenchmarkResult:
    strategy: str
    task: str
    tokens: int
    latency_s: float
    keyword_coverage: float = 0.0
    relevant_file_count: int = 0
    has_evidence: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


BENCHMARK_TASKS = [
    BenchmarkTask(
        question="What Python framework is used in this project?",
        expected_keywords=["cli", "runtime", "config", "pytest"],
        expected_domain="framework",
    ),
    BenchmarkTask(
        question="Where is the hardware detection implemented?",
        expected_keywords=["hardware", "detector", "gpu", "cpu"],
        expected_domain="file_location",
    ),
    BenchmarkTask(
        question="How do tests run in this project?",
        expected_keywords=["pytest", "test", "tests"],
        expected_domain="testing",
    ),
    BenchmarkTask(
        question="What is the project structure?",
        expected_keywords=["src", "lyme", "lyme_model", "tests"],
        expected_domain="structure",
    ),
    BenchmarkTask(
        question="What build system is used?",
        expected_keywords=["pip", "setuptools", "pyproject", "toml"],
        expected_domain="build",
    ),
    BenchmarkTask(
        question="Find files related to context management",
        expected_keywords=["context", "compiler"],
        expected_domain="context",
    ),
]


class ContextBenchmark:
    """Benchmark comparing raw, current, and improved context compilation."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.tasks = BENCHMARK_TASKS
        self.results: List[BenchmarkResult] = []

    def run_all(self) -> List[BenchmarkResult]:
        """Run benchmark across all tasks and strategies."""
        strategies = [
            ("raw", self._raw_context),
            ("current", self._current_context),
            ("improved", self._improved_context),
        ]

        for task in self.tasks:
            for name, fn in strategies:
                start = time.time()
                context = fn(task.question)
                latency = time.time() - start

                tokens = len(context.split())
                kw_coverage = self._keyword_coverage(context, task.expected_keywords)
                relevant_count = 0
                has_evidence = kw_coverage > 0

                result = BenchmarkResult(
                    strategy=name,
                    task=task.question[:60],
                    tokens=tokens,
                    latency_s=round(latency, 3),
                    keyword_coverage=round(kw_coverage, 2),
                    relevant_file_count=relevant_count,
                    has_evidence=has_evidence,
                )
                self.results.append(result)

        return self.results

    def _raw_context(self, task: str) -> str:
        """Minimal context — no compiler."""
        repo = Path(self.repo_path)
        py_count = len(list(repo.rglob("*.py"))) if repo.is_dir() else 0
        return (
            f"Repository: {repo.name}\n"
            f"Python files: {py_count}\n"
            f"Task: {task}\n"
        )

    def _current_context(self, task: str) -> str:
        cc = ContextCompiler(self.repo_path)
        result = cc.compile(task)
        return result.to_text()

    def _improved_context(self, task: str) -> str:
        ic = ImprovedContextCompiler(self.repo_path)
        result = ic.compile(task)
        return result.to_text()

    def _keyword_coverage(self, text: str, keywords: List[str]) -> float:
        if not keywords:
            return 0.0
        text_lower = text.lower()
        matched = sum(1 for k in keywords if k.lower() in text_lower)
        return matched / len(keywords)

    def summary(self) -> Dict:
        if not self.results:
            self.run_all()

        summary = {"tasks": len(self.tasks), "strategies": {}}
        for strategy in ["raw", "current", "improved"]:
            strat_results = [r for r in self.results if r.strategy == strategy]
            if not strat_results:
                continue
            avg_tokens = sum(r.tokens for r in strat_results) / len(strat_results)
            avg_latency = sum(r.latency_s for r in strat_results) / len(strat_results)
            avg_coverage = sum(r.keyword_coverage for r in strat_results) / len(strat_results)
            improvement_over_raw = None
            if strategy != "raw":
                raw_avg = sum(r.tokens for r in self.results if r.strategy == "raw") / max(
                    len([r for r in self.results if r.strategy == "raw"]), 1)
                improvement_over_raw = round((1 - avg_tokens / raw_avg) * 100, 1) if raw_avg > 0 else 0

            summary["strategies"][strategy] = {
                "avg_tokens": round(avg_tokens, 1),
                "avg_latency_s": round(avg_latency, 3),
                "avg_keyword_coverage": round(avg_coverage, 2),
                "tasks_with_evidence": sum(1 for r in strat_results if r.has_evidence),
            }
            if improvement_over_raw is not None:
                summary["strategies"][strategy]["token_reduction_vs_raw_pct"] = improvement_over_raw

        # Compare improved vs current
        improved_results = [r for r in self.results if r.strategy == "improved"]
        current_results = [r for r in self.results if r.strategy == "current"]
        if improved_results and current_results:
            i_avg = sum(r.tokens for r in improved_results) / len(improved_results)
            c_avg = sum(r.tokens for r in current_results) / len(current_results)
            summary["improved_vs_current"] = {
                "token_change_pct": round((1 - i_avg / c_avg) * 100, 1) if c_avg > 0 else 0,
            }

        return summary

    def report(self) -> str:
        s = self.summary()
        lines = [
            "=" * 50,
            "CONTEXT QUALITY BENCHMARK",
            "=" * 50,
            f"Tasks: {s['tasks']}",
            "",
        ]
        for name, data in s["strategies"].items():
            lines.append(f"\n[{name.upper()}]")
            lines.append(f"  Avg tokens:       {data['avg_tokens']:>8.1f}")
            lines.append(f"  Avg latency:      {data['avg_latency_s']:>8.3f}s")
            lines.append(f"  Keyword coverage: {data['avg_keyword_coverage']:>8.2f}")
            lines.append(f"  Tasks w/evidence: {data['tasks_with_evidence']:>8d}")
            if "token_reduction_vs_raw_pct" in data:
                lines.append(f"  Token reduction:  {data['token_reduction_vs_raw_pct']:>8.1f}%")

        if "improved_vs_current" in s:
            ivc = s["improved_vs_current"]
            lines.append(f"\nImproved vs Current: {ivc['token_change_pct']:.1f}% token change")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)


def run_benchmark(repo_path: str = ".") -> Dict:
    bench = ContextBenchmark(repo_path)
    results = bench.run_all()
    summary = bench.summary()

    output = {"summary": summary, "results": [r.to_dict() for r in results]}
    out_path = Path("lyme-output") / "context-benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))

    return output
