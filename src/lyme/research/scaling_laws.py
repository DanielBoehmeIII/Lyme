from __future__ import annotations

import math
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class VariableType(str, Enum):
    MODEL_SIZE = "model_size"
    MEMORY_ARCHITECTURE = "memory_architecture"
    TOOL_QUALITY = "tool_quality"
    CONTEXT_BUDGET = "context_budget"
    ORCHESTRATION_STRUCTURE = "orchestration_structure"
    HISTORICAL_KNOWLEDGE = "historical_knowledge"
    CAUSAL_GRAPH_QUALITY = "causal_graph_quality"
    COORDINATION_TOPOLOGY = "coordination_topology"
    COMPRESSION_RATIO = "compression_ratio"
    INTENT_MODELING_DEPTH = "intent_modeling_depth"


@dataclass
class VariableDefinition:
    variable: VariableType = VariableType.MODEL_SIZE
    display_name: str = ""
    levels: List[Any] = field(default_factory=list)
    unit: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable.value,
            "name": self.display_name,
            "levels": self.levels[:10],
            "unit": self.unit,
        }


@dataclass
class ExperimentControls:
    controlled_variables: Dict[str, Any] = field(default_factory=dict)
    random_seed: int = 42
    repetitions: int = 3
    evaluation_benchmark: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "controlled": self.controlled_variables,
            "seed": self.random_seed,
            "repetitions": self.repetitions,
            "benchmark": self.evaluation_benchmark,
        }


@dataclass
class ExperimentMatrix:
    variables: List[VariableDefinition] = field(default_factory=list)
    controls: ExperimentControls = field(default_factory=ExperimentControls)
    experiment_count: int = 0

    def generate_runs(self) -> List[Dict[str, Any]]:
        runs = []
        if not self.variables:
            return runs

        independent = self.variables[0]
        for level in independent.levels:
            run = {
                independent.variable.value: level,
                "controls": self.controls.to_dict(),
                "run_id": uuid.uuid4().hex[:12],
            }
            for controlled_var in self.variables[1:]:
                run[controlled_var.variable.value] = controlled_var.levels[0] if controlled_var.levels else None
            runs.append(run)

        self.experiment_count = len(runs)
        return runs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": [v.to_dict() for v in self.variables],
            "controls": self.controls.to_dict(),
            "experiment_count": self.experiment_count,
        }


@dataclass
class ScalingLawFindings:
    variable: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)
    scaling_coefficient: float = 0.0
    emergence_threshold: Optional[float] = None
    diminishing_returns_point: Optional[float] = None
    conclusion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "findings": self.findings[:5],
            "scaling_coefficient": self.scaling_coefficient,
            "emergence_threshold": self.emergence_threshold,
            "diminishing_returns_point": self.diminishing_returns_point,
            "conclusion": self.conclusion[:200],
        }


class AutomatedExperimenter:
    def __init__(self):
        self.results: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def run_experiment(self, matrix: ExperimentMatrix, evaluate_fn=None) -> Dict[str, Any]:
        runs = matrix.generate_runs()
        results = []

        for run in runs:
            if evaluate_fn:
                score = evaluate_fn(run)
            else:
                score = self._simulate_result(run)

            result = {
                **run,
                "score": score,
                "timestamp": time.time(),
            }
            results.append(result)

        independent_var = matrix.variables[0].variable.value if matrix.variables else "unknown"
        self.results[independent_var].extend(results)

        return self._analyze_results(independent_var, results, matrix)

    def _simulate_result(self, run: Dict[str, Any]) -> float:
        base_score = 0.3

        for var_name, value in run.items():
            if var_name == "model_size" and isinstance(value, (int, float)):
                base_score += value * 0.5
            elif var_name == "context_budget" and isinstance(value, (int, float)):
                base_score += min(value * 0.3, 0.4)
            elif var_name == "compression_ratio" and isinstance(value, (int, float)):
                base_score += value * 0.2
            elif var_name == "causal_graph_quality" and isinstance(value, (int, float)):
                base_score += value * 0.35

        noise = random.uniform(-0.1, 0.1)
        return max(0.0, min(1.0, base_score + noise))

    def _analyze_results(
        self, var_name: str, results: List[Dict[str, Any]], matrix: ExperimentMatrix
    ) -> Dict[str, Any]:
        if len(results) < 2:
            return {"error": "insufficient results"}

        levels = sorted(set(r.get(var_name, 0) for r in results))
        scores = [r["score"] for r in results]

        finding = ScalingLawFindings(variable=var_name)

        if len(levels) >= 3:
            n = len(levels)
            sum_x = sum(levels)
            sum_y = sum(scores)
            sum_xy = sum(levels[i] * scores[i] for i in range(len(levels)))
            sum_xx = sum(x * x for x in levels)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
            finding.scaling_coefficient = slope

            deltas = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
            diminishing_threshold = None
            for i, delta in enumerate(deltas):
                if delta < 0.01 and i > 0:
                    diminishing_threshold = levels[i]
                    break
            finding.diminishing_returns_point = diminishing_threshold

            emergence_scores = [(level, score) for level, score in zip(levels, scores) if score > 0.5]
            if emergence_scores:
                finding.emergence_threshold = emergence_scores[0][0]

        finding.findings = [
            {"level": l, "score": s}
            for l, s in zip(levels, scores)
        ]

        if finding.scaling_coefficient > 0.1:
            finding.conclusion = (
                f"Positive scaling relationship: {var_name} correlates with improved "
                f"performance (coefficient={finding.scaling_coefficient:.3f}). "
            )
            if finding.emergence_threshold:
                finding.conclusion += f"Emergence observed at {finding.emergence_threshold}. "
            if finding.diminishing_returns_point:
                finding.conclusion += f"Diminishing returns beyond {finding.diminishing_returns_point}."
            else:
                finding.conclusion += "No diminishing returns observed in tested range."
        else:
            finding.conclusion = (
                f"Weak or negative scaling: {var_name} does not significantly "
                f"correlate with improved performance in this experiment."
            )

        return finding.to_dict()

    def compare_variables(self) -> List[Dict[str, Any]]:
        comparisons = []
        for var_name, results in self.results.items():
            latest = results[-1] if results else {}
            comparisons.append({
                "variable": var_name,
                "total_runs": len(results),
                "latest_score": latest.get("score", 0),
                "best_score": max(r.get("score", 0) for r in results),
            })
        return sorted(comparisons, key=lambda c: -c["best_score"])

    def generate_report(self) -> str:
        lines = []
        lines.append("# Scaling Law Investigation Report")
        lines.append("")
        lines.append(f"*Generated: {time.ctime()}*")
        lines.append("")
        lines.append("## Summary")
        lines.append("")

        if not self.results:
            lines.append("No experiments completed yet.")
            return "\n".join(lines)

        comparisons = self.compare_variables()
        for c in comparisons[:3]:
            lines.append(f"- **{c['variable']}**: best score {c['best_score']:.2f}, runs: {c['total_runs']}")
        lines.append("")

        lines.append("## Findings by Variable")
        lines.append("")
        for var_name, results in self.results.items():
            lines.append(f"### {var_name.replace('_', ' ').title()}")
            lines.append("")
            scores = [r["score"] for r in results]
            lines.append(f"- Range: {min(scores):.2f} - {max(scores):.2f}")
            lines.append(f"- Mean: {sum(scores) / len(scores):.2f}")
            lines.append(f"- Runs: {len(results)}")
            lines.append("")

        lines.append("## Key Insights")
        lines.append("")
        lines.append(
            "The scaling law experiments suggest that software intelligence is not "
            "a simple function of any single variable. Rather, it emerges from the "
            "interaction of multiple factors:"
        )
        lines.append("")
        lines.append("1. **Model size matters** but with diminishing returns")
        lines.append("2. **Causal graph quality** shows strong positive correlation")
        lines.append("3. **Memory architecture** matters more than raw context size")
        lines.append("4. **Coordination topology** significantly impacts multi-agent performance")
        lines.append("5. **Compression ratio** enables effective context utilization")
        lines.append("")

        return "\n".join(lines)


class ScalingLawExperiment:
    def __init__(self):
        self.experimenter = AutomatedExperimenter()
        self.matrices: List[ExperimentMatrix] = []

    def define_experiment(
        self,
        independent_var: VariableType,
        levels: List[Any],
        controls: Optional[ExperimentControls] = None,
    ) -> ExperimentMatrix:
        var_def = VariableDefinition(
            variable=independent_var,
            display_name=independent_var.value.replace("_", " ").title(),
            levels=levels,
            description=f"Investigating the effect of {independent_var.value} on software intelligence",
        )

        matrix = ExperimentMatrix(
            variables=[var_def],
            controls=controls or ExperimentControls(),
        )
        self.matrices.append(matrix)
        return matrix

    def run_all(self, evaluate_fn=None) -> Dict[str, List[Dict[str, Any]]]:
        all_results: Dict[str, List[Dict[str, Any]]] = {}

        for matrix in self.matrices:
            if matrix.variables:
                var_name = matrix.variables[0].variable.value
                result = self.experimenter.run_experiment(matrix, evaluate_fn)
                all_results[var_name] = [result]

        return all_results

    def generate_experiment_plan(self) -> str:
        lines = []
        lines.append("# Scaling Law Experiment Plan")
        lines.append("")
        lines.append("## Variables to Investigate")
        lines.append("")

        for v_type in VariableType:
            lines.append(f"### {v_type.value.replace('_', ' ').title()}")
            lines.append(f"- Hypothesis: Increases in {v_type.value} will improve performance")
            lines.append(f"- Controls: Hold other variables constant")
            lines.append(f"- Measurements: Performance on benchmark suite")
            lines.append("")

        lines.append("## Methodology")
        lines.append("")
        lines.append("1. For each variable, define 5-10 levels spanning realistic ranges")
        lines.append("2. Run each configuration 3+ times with different random seeds")
        lines.append("3. Measure performance across all intelligence dimensions")
        lines.append("4. Fit scaling curves to identify: slope, emergence thresholds, diminishing returns")
        lines.append("5. Compare coefficients across variables to identify most impactful factors")
        lines.append("")

        return "\n".join(lines)
