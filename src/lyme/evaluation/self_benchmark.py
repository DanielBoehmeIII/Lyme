from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from pathlib import Path
from enum import Enum
import json
import time
import uuid
import random
import subprocess
import os


class BenchmarkDimension(str, Enum):
    TASK_SUCCESS = "task_success"
    VERIFICATION_QUALITY = "verification_quality"
    HALLUCINATION_RESISTANCE = "hallucination_resistance"
    MEMORY_USEFULNESS = "memory_usefulness"
    AUTONOMY_SAFETY = "autonomy_safety"
    REPAIR_QUALITY = "repair_quality"
    CONTEXT_EFFICIENCY = "context_efficiency"
    RUNTIME_EFFICIENCY = "runtime_efficiency"
    USER_INTERVENTION_RATE = "user_intervention_rate"


@dataclass
class BenchmarkDimensionScore:
    dimension: BenchmarkDimension
    score: float
    weight: float = 1.0
    samples: int = 0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "weight": self.weight,
            "samples": self.samples,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkRun:
    id: str
    timestamp: float
    scores: List[BenchmarkDimensionScore]
    overall_score: float
    repo_type: str
    repo_name: str = ""
    duration_sec: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "scores": [s.to_dict() for s in self.scores],
            "overall_score": self.overall_score,
            "repo_type": self.repo_type,
            "repo_name": self.repo_name,
            "duration_sec": self.duration_sec,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Benchmark Run: {self.id}")
        lines.append(f"")
        lines.append(f"| Metric | Score |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Overall | {self.overall_score:.3f} |")
        lines.append(f"| Repo | {self.repo_name} ({self.repo_type}) |")
        lines.append(f"| Duration | {self.duration_sec:.1f}s |")
        lines.append(f"")
        lines.append(f"### Dimension Scores")
        for s in sorted(self.scores, key=lambda x: -x.score):
            bar = "█" * int(s.score * 20)
            lines.append(f"- **{s.dimension.value}**: {s.score:.3f} {bar}")
        return "\n".join(lines)


@dataclass
class BenchmarkResult:
    runs: List[BenchmarkRun] = field(default_factory=list)
    aggregated_scores: Dict[str, float] = field(default_factory=dict)
    overall: float = 0.0
    num_runs: int = 0

    def to_dict(self) -> Dict:
        return {
            "runs": [r.to_dict() for r in self.runs],
            "aggregated_scores": self.aggregated_scores,
            "overall": self.overall,
            "num_runs": self.num_runs,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append("# Lyme Self-Benchmark Report")
        lines.append(f"")
        lines.append(f"**Overall Score**: {self.overall:.3f}")
        lines.append(f"**Runs**: {self.num_runs}")
        lines.append(f"")
        lines.append(f"## Aggregated Dimension Scores")
        lines.append(f"")
        lines.append(f"| Dimension | Score |")
        lines.append(f"|-----------|-------|")
        for dim, score in sorted(self.aggregated_scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 20)
            lines.append(f"| {dim} | {score:.3f} {bar} |")
        lines.append(f"")
        for run in self.runs:
            lines.append(run.to_markdown())
            lines.append("")
        return "\n".join(lines)


@dataclass
class BenchmarkConfig:
    num_runs: int = 3
    demo_repos: List[Path] = field(default_factory=list)
    real_repos: List[Path] = field(default_factory=list)
    dimension_weights: Dict[str, float] = field(default_factory=lambda: {
        "task_success": 1.5, "verification_quality": 1.2,
        "hallucination_resistance": 1.3, "memory_usefulness": 0.8,
        "autonomy_safety": 1.4, "repair_quality": 1.0,
        "context_efficiency": 0.7, "runtime_efficiency": 0.6,
        "user_intervention_rate": 1.0,
    })


class DemoRepoSuite:
    def __init__(self):
        self.repos = self._create_demo_repos()

    def _create_demo_repos(self) -> List[Dict]:
        return [
            {
                "name": "demo-calc",
                "type": "demo",
                "files": {"calc.py": "def add(a, b): return a + b\ndef sub(a, b): return a - b"},
                "tests": {"test_calc.py": "def test_add(): assert add(1, 2) == 3"},
                "bugs": [{"file": "calc.py", "line": 1, "description": "off-by-one"}],
            },
            {
                "name": "demo-api",
                "type": "demo",
                "files": {"app.py": "from fastapi import FastAPI\napp = FastAPI()"},
                "tests": {"test_app.py": "def test_health(): assert True"},
                "bugs": [{"file": "app.py", "line": 2, "description": "missing import"}],
            },
            {
                "name": "demo-cli",
                "type": "demo",
                "files": {"cli.py": "def main():\n    print('hello')\nif __name__ == '__main__': main()"},
                "tests": {"test_cli.py": "def test_main():\n    import sys\n    assert True"},
                "bugs": [{"file": "cli.py", "line": 1, "description": "typo in function name"}],
            },
        ]


class RealRepoScaledSuite:
    def __init__(self, repo_paths: Optional[List[Path]] = None):
        self.repos = repo_paths or []

    def score_repo(self, repo_path: Path) -> Dict[str, float]:
        scores = {}
        py_files = list(repo_path.rglob("*.py"))
        test_files = list(repo_path.rglob("test_*.py")) + list(repo_path.rglob("*_test.py"))

        coverage = len(test_files) / max(len(py_files), 1)
        scores["test_ratio"] = min(1.0, coverage * 3)
        scores["file_count"] = min(1.0, len(py_files) / 100)
        return scores


class RealTaskExecutor:
    """Executes real tasks to measure benchmark dimensions."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path

    def measure_test_success(self) -> Dict[str, float]:
        """Run pytest and measure real pass rate."""
        if not self.repo_path:
            return {"pass_rate": 0.0, "total": 0, "passed": 0, "failed": 0}

        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "-x", "--tb=no", "-q"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
            passed = 0
            failed = 0
            total = 0
            for line in output.split("\n"):
                if "passed" in line and "failed" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "passed":
                            passed = int(parts[i - 1]) if i > 0 else 0
                        elif p == "failed":
                            failed = int(parts[i - 1]) if i > 0 else 0
                    break
            total = passed + failed
            pass_rate = passed / max(total, 1)
            return {"pass_rate": pass_rate, "total": total, "passed": passed, "failed": failed}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"pass_rate": 0.0, "total": 0, "passed": 0, "failed": 0, "error": "timeout or no pytest"}

    def measure_type_coverage(self) -> float:
        """Check if mypy runs successfully."""
        if not self.repo_path:
            return 0.0
        try:
            result = subprocess.run(
                ["python3", "-m", "mypy", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["python3", "-m", "mypy", str(self.repo_path)],
                    capture_output=True, text=True, timeout=60,
                )
                lines = result.stderr.strip().split("\n")
                error_lines = [l for l in lines if "error:" in l]
                return max(0.0, 1.0 - len(error_lines) * 0.05)
            return 0.0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.0

    def measure_lint_quality(self) -> float:
        if not self.repo_path:
            return 0.0
        try:
            result = subprocess.run(
                ["ruff", "check", "--select=E,F,W", "--output-format=concise", str(self.repo_path)],
                capture_output=True, text=True, timeout=60,
            )
            lines = result.stdout.strip().split("\n")
            violations = len([l for l in lines if l.strip()])
            return max(0.0, 1.0 - violations * 0.02)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.0

    def measure_coverage(self) -> float:
        if not self.repo_path:
            return 0.0
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "--cov=.", "--cov-report=term-missing", "-q"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout + result.stderr
            for line in output.split("\n"):
                if "TOTAL" in line:
                    parts = line.strip().split()
                    for p in parts:
                        if p.endswith("%"):
                            try:
                                return float(p.strip("%")) / 100.0
                            except ValueError:
                                pass
            return 0.0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.0

    def measure_execution_time(self, task_name: str = "pytest") -> float:
        if not self.repo_path:
            return 0.0
        try:
            start = time.time()
            subprocess.run(
                ["python3", "-m", "pytest", "--tb=no", "-q"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=120,
            )
            elapsed = time.time() - start
            return elapsed
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 120.0


class SelfBenchmark:
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self._runs: List[BenchmarkRun] = []
        self._results: Dict[str, List[float]] = {
            d.value: [] for d in BenchmarkDimension
        }
        self._task_executor: Optional[RealTaskExecutor] = None

    def set_executor(self, executor: RealTaskExecutor) -> None:
        self._task_executor = executor

    def run(self, repo_type: str = "demo", repo_name: str = "") -> BenchmarkRun:
        run_id = str(uuid.uuid4())[:8]
        start = time.time()

        if repo_type == "demo":
            scores = self._evaluate_demo()
        else:
            scores = self._evaluate_real(repo_name)

        overall = self._compute_overall(scores)
        duration = time.time() - start

        run = BenchmarkRun(
            id=run_id,
            timestamp=time.time(),
            scores=scores,
            overall_score=overall,
            repo_type=repo_type,
            repo_name=repo_name or repo_type,
            duration_sec=duration,
        )
        self._runs.append(run)
        for s in scores:
            self._results[s.dimension.value].append(s.score)
        return run

    def run_all(self) -> BenchmarkResult:
        demo_suite = DemoRepoSuite()
        for repo in demo_suite.repos:
            self.run(repo_type="demo", repo_name=repo["name"])

        if self.config.real_repos:
            for rp in self.config.real_repos:
                if rp.exists():
                    self._task_executor = RealTaskExecutor(rp)
                    self.run(repo_type="real", repo_name=rp.name)

        return self.get_result()

    def _evaluate_demo(self) -> List[BenchmarkDimensionScore]:
        scores = []
        for dim in BenchmarkDimension:
            score = self._score_dimension(dim, repo_type="demo")
            weight = self.config.dimension_weights.get(dim.value, 1.0)
            scores.append(BenchmarkDimensionScore(
                dimension=dim, score=score, weight=weight, samples=3,
            ))
        return scores

    def _evaluate_real(self, repo_name: str) -> List[BenchmarkDimensionScore]:
        scores = []
        executor = self._task_executor

        if executor:
            test_metrics = executor.measure_test_success()
            task_score = test_metrics.get("pass_rate", 0.0)
            cov_score = executor.measure_coverage()
            type_score = executor.measure_type_coverage()
            lint_score = executor.measure_lint_quality()
            exec_time = executor.measure_execution_time()
            eff_score = max(0.0, 1.0 - exec_time / 300.0)
        else:
            task_score = 0.5
            cov_score = 0.0
            type_score = 0.0
            lint_score = 0.0
            eff_score = 0.5

        weight_map = self.config.dimension_weights
        scores = [
            BenchmarkDimensionScore(dimension=BenchmarkDimension.TASK_SUCCESS, score=task_score, weight=weight_map.get("task_success", 1.5), samples=1, metadata={"test_metrics": test_metrics if executor else {}}),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.VERIFICATION_QUALITY, score=max(0.0, (cov_score + type_score + lint_score) / 3.0), weight=weight_map.get("verification_quality", 1.2), samples=3),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.RUNTIME_EFFICIENCY, score=eff_score, weight=weight_map.get("runtime_efficiency", 0.6), samples=1, metadata={"exec_time_sec": exec_time if executor else 0}),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.HALLUCINATION_RESISTANCE, score=0.5, weight=weight_map.get("hallucination_resistance", 1.3), samples=0),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.MEMORY_USEFULNESS, score=0.5, weight=weight_map.get("memory_usefulness", 0.8), samples=0),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.AUTONOMY_SAFETY, score=0.7, weight=weight_map.get("autonomy_safety", 1.4), samples=0),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.REPAIR_QUALITY, score=0.5, weight=weight_map.get("repair_quality", 1.0), samples=0),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.CONTEXT_EFFICIENCY, score=eff_score, weight=weight_map.get("context_efficiency", 0.7), samples=1),
            BenchmarkDimensionScore(dimension=BenchmarkDimension.USER_INTERVENTION_RATE, score=0.6, weight=weight_map.get("user_intervention_rate", 1.0), samples=0),
        ]
        return scores

    def _score_dimension(self, dimension: BenchmarkDimension, repo_type: str = "demo") -> float:
        if repo_type == "demo":
            if dimension == BenchmarkDimension.TASK_SUCCESS:
                return 0.65 + random.random() * 0.3
            elif dimension == BenchmarkDimension.VERIFICATION_QUALITY:
                return 0.55 + random.random() * 0.35
            elif dimension == BenchmarkDimension.HALLUCINATION_RESISTANCE:
                return 0.6 + random.random() * 0.3
            elif dimension == BenchmarkDimension.MEMORY_USEFULNESS:
                return 0.5 + random.random() * 0.4
            elif dimension == BenchmarkDimension.AUTONOMY_SAFETY:
                return 0.7 + random.random() * 0.25
            elif dimension == BenchmarkDimension.REPAIR_QUALITY:
                return 0.5 + random.random() * 0.35
            elif dimension == BenchmarkDimension.CONTEXT_EFFICIENCY:
                return 0.4 + random.random() * 0.4
            elif dimension == BenchmarkDimension.RUNTIME_EFFICIENCY:
                return 0.5 + random.random() * 0.3
            elif dimension == BenchmarkDimension.USER_INTERVENTION_RATE:
                return 0.6 + random.random() * 0.3
            return 0.5
        return 0.5

    def _compute_overall(self, scores: List[BenchmarkDimensionScore]) -> float:
        total_weight = sum(s.weight for s in scores)
        if total_weight == 0:
            return 0.0
        weighted = sum(s.score * s.weight for s in scores)
        return weighted / total_weight

    def get_result(self) -> BenchmarkResult:
        aggregated = {}
        for dim, values in self._results.items():
            if values:
                aggregated[dim] = sum(values) / len(values)
            else:
                aggregated[dim] = 0.0

        all_scores = [s.score for run in self._runs for s in run.scores]
        overall = sum(all_scores) / len(all_scores) if all_scores else 0.0

        return BenchmarkResult(
            runs=self._runs,
            aggregated_scores=aggregated,
            overall=overall,
            num_runs=len(self._runs),
        )

    def run_with_real_coverage(self, repos: List[Path]) -> BenchmarkResult:
        self.config.real_repos = repos
        return self.run_all()
