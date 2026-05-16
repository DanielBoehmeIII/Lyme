import time
import uuid
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from .generator import SyntheticRepoGenerator
from .degradation import ContextDegradationAnalyzer
from ..config import AgentConfig
from ..benchmark import AgentRunner
from ..telemetry import EventLog, EventType, MetricsStore
from ..cognition import ThoughtRecorder


@dataclass
class ExperimentResult:
    experiment_id: str = ""
    name: str = ""
    agent_name: str = ""
    levels: List[dict] = field(default_factory=list)
    success: bool = False
    duration_ms: float = 0.0
    degradation_curves: dict = field(default_factory=dict)
    bottlenecks: List[dict] = field(default_factory=list)
    scaling_laws: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "agent_name": self.agent_name,
            "levels": self.levels,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "degradation_curves": self.degradation_curves,
            "bottlenecks": self.bottlenecks,
            "scaling_laws": self.scaling_laws,
            "error": self.error,
        }


class StressExperiment:
    def __init__(self, name: str, agent_cfg: AgentConfig,
                 work_base_dir: str = "./lyme-experiments"):
        self.name = name
        self.agent_cfg = agent_cfg
        self.work_base_dir = Path(work_base_dir)
        self.generator = SyntheticRepoGenerator()
        self.analyzer = ContextDegradationAnalyzer()
        self.event_log = EventLog()
        self.metrics = MetricsStore()
        self._results: List[ExperimentResult] = []

    def run_repo_size_experiment(self, sizes: List[int] = None,
                                  task: str = "") -> ExperimentResult:
        sizes = sizes or [5, 10, 20, 50, 100]
        result = ExperimentResult(
            experiment_id=uuid.uuid4().hex[:12],
            name=f"{self.name}-repo-size",
            agent_name=self.agent_cfg.name,
        )
        start = time.time()

        for size in sizes:
            level_result = self._run_at_repo_size(size, task)
            result.levels.append(level_result)

            self.analyzer.add_measurement(
                "completion_rate", size,
                level_result.get("completion_rate", 0),
                baseline=1.0,
            )
            self.analyzer.add_measurement(
                "duration_ms", size,
                level_result.get("duration_ms", 0),
            )
            self.analyzer.add_measurement(
                "error_count", size,
                level_result.get("error_count", 0),
            )

        result.degradation_curves = {
            name: curve.to_dict()
            for name, curve in self.analyzer.all_curves().items()
        }
        result.bottlenecks = self.analyzer.identify_bottlenecks()
        result.scaling_laws = {
            name: self.analyzer.scaling_law_estimate(name)
            for name in self.analyzer.all_curves()
        }
        result.success = any(
            l.get("completion_rate", 0) > 0.5 for l in result.levels
        )
        result.duration_ms = (time.time() - start) * 1000
        self._results.append(result)
        return result

    def _run_at_repo_size(self, num_files: int, task: str = "") -> dict:
        work_dir = self.work_base_dir / f"exp-{self.name}-{num_files}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            spec = self.generator.generate(
                target_dir=work_dir,
                num_files=num_files,
                depth=2,
                deps_per_file=min(5, num_files // 2),
            )

            task_prompt = task or (
                f"Refactor this project to add consistent error handling "
                f"across all {num_files} modules. Wrap each function in "
                f"try/except blocks and add proper logging."
            )

            runner = AgentRunner(self.agent_cfg, event_log=self.event_log)

            agent_result = runner.run(
                prompt=task_prompt,
                work_dir=work_dir,
                timeout_s=max(120, num_files * 10),
            )

            current_files = list(work_dir.rglob("*.py"))
            return {
                "level": num_files,
                "completion_rate": 1.0 if agent_result.exit_code == 0 else 0.0,
                "duration_ms": agent_result.duration_ms,
                "error_count": len(self.event_log.get_events(type_="error")),
                "files_after": len(current_files),
                "agent_status": agent_result.status.value,
                "timed_out": agent_result.status == "timeout",
            }

        except Exception as e:
            return {
                "level": num_files,
                "completion_rate": 0.0,
                "duration_ms": 0.0,
                "error_count": 1,
                "files_after": 0,
                "agent_status": "error",
                "timed_out": False,
                "error": str(e),
            }

    def run_hidden_coupling_experiment(self, coupling_levels: List[int] = None) -> ExperimentResult:
        coupling_levels = coupling_levels or [0, 1, 3, 5, 10]
        result = ExperimentResult(
            experiment_id=uuid.uuid4().hex[:12],
            name=f"{self.name}-hidden-coupling",
            agent_name=self.agent_cfg.name,
        )
        start = time.time()

        for count in coupling_levels:
            level_result = self._run_at_coupling_level(count)
            result.levels.append(level_result)

            self.analyzer.add_measurement(
                "consistency_score", count,
                level_result.get("consistency_score", 0),
                baseline=1.0,
            )
            self.analyzer.add_measurement(
                "contradictory_edits", count,
                level_result.get("contradictory_edits", 0),
            )

        result.degradation_curves = {
            name: curve.to_dict()
            for name, curve in self.analyzer.all_curves().items()
        }
        result.bottlenecks = self.analyzer.identify_bottlenecks()
        result.success = True
        result.duration_ms = (time.time() - start) * 1000
        self._results.append(result)
        return result

    def _run_at_coupling_level(self, hidden_count: int) -> dict:
        work_dir = self.work_base_dir / f"exp-coupling-{hidden_count}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            spec = self.generator.generate(
                target_dir=work_dir, num_files=15, deps_per_file=2
            )

            for i in range(hidden_count):
                src = f"module_{i}.py" if False else spec["files"][i % len(spec["files"])]
                tgt = spec["files"][(i + 1) % len(spec["files"])]
                self.generator.add_hidden_coupling(
                    work_dir, src, tgt,
                    coupling_type=["data", "import", "format"][i % 3],
                )

            task_prompt = (
                f"Refactor the src/ directory to use a common BaseProcessor class "
                f"that all modules inherit from. Ensure consistency."
            )

            runner = AgentRunner(self.agent_cfg, event_log=self.event_log)
            agent_result = runner.run(
                prompt=task_prompt, work_dir=work_dir, timeout_s=120
            )

            consistency_score = self._evaluate_consistency(work_dir, hidden_count)

            return {
                "level": hidden_count,
                "consistency_score": consistency_score,
                "contradictory_edits": max(0, hidden_count - int(consistency_score * 10)),
                "duration_ms": agent_result.duration_ms,
                "agent_status": agent_result.status.value,
            }

        except Exception as e:
            return {
                "level": hidden_count,
                "consistency_score": 0.0,
                "contradictory_edits": hidden_count,
                "duration_ms": 0.0,
                "agent_status": "error",
                "error": str(e),
            }

    def _evaluate_consistency(self, work_dir: Path, hidden_count: int) -> float:
        py_files = list(work_dir.rglob("*.py"))
        if not py_files:
            return 0.0

        shared_patterns = ["BaseProcessor", "common", "base"]
        pattern_matches = 0
        for f in py_files:
            content = f.read_text()
            for pat in shared_patterns:
                if pat in content:
                    pattern_matches += 1
                    break

        return pattern_matches / len(py_files) if py_files else 0.0

    def get_results(self) -> List[ExperimentResult]:
        return self._results

    def generate_report(self, result: ExperimentResult) -> str:
        lines = [
            f"# Stress Experiment: {result.name}",
            f"",
            f"- **Agent**: {result.agent_name}",
            f"- **Duration**: {result.duration_ms:.1f}ms",
            f"- **Levels Tested**: {len(result.levels)}",
            f"- **Success**: {result.success}",
            f"",
            f"## Degradation Curves",
            f"",
        ]

        for name, curve in result.degradation_curves.items():
            lines.append(f"### {name}")
            lines.append(f"- Baseline: {curve.get('baseline_value', 'N/A')}")
            lines.append(f"- Collapse Point: {curve.get('collapse_point', 'none')}")
            lines.append(f"- Nonlinearity: {curve.get('nonlinearity_score', 0):.3f}")
            lines.append(f"- Measurements: {len(curve.get('points', []))}")
            lines.append("")

        if result.bottlenecks:
            lines.append("## Bottlenecks Identified")
            lines.append("")
            for b in result.bottlenecks:
                lines.append(f"- **{b['metric']}**: collapsed at level {b['collapse_level']} "
                           f"({b['type']}, nonlinearity={b['nonlinearity']:.2f})")
            lines.append("")

        if result.scaling_laws:
            lines.append("## Scaling Laws")
            lines.append("")
            for name, law in result.scaling_laws.items():
                if law.get("reliable"):
                    lines.append(f"- **{name}**: slope={law['slope']:.4f}, "
                               f"trend={law['trend']}, collapse={law['collapse_point']}")
            lines.append("")

        return "\n".join(lines)
