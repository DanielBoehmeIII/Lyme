from __future__ import annotations

import ast
import math
import re
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class MetricCategory(str, Enum):
    STRUCTURAL = "structural"
    DYNAMIC = "dynamic"
    QUALITY = "quality"
    COORDINATION = "coordination"
    COGNITIVE = "cognitive"


@dataclass
class MetricDefinition:
    name: str
    category: MetricCategory
    formal_meaning: str
    observable_proxies: List[str]
    failure_cases: List[str]
    normalization_methods: List[str]
    visualization_approaches: List[str]
    unit: str = ""
    range_low: float = 0.0
    range_high: float = 1.0
    higher_is_better: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "formal_meaning": self.formal_meaning,
            "observable_proxies": self.observable_proxies,
            "failure_cases": self.failure_cases,
            "normalization_methods": self.normalization_methods,
            "visualization_approaches": self.visualization_approaches,
            "unit": self.unit,
            "range": [self.range_low, self.range_high],
            "higher_is_better": self.higher_is_better,
        }


@dataclass
class MetricObservation:
    metric_name: str
    value: float
    normalized_value: float
    timestamp: float
    subsystem: str = ""
    file_path: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "timestamp": self.timestamp,
            "subsystem": self.subsystem,
            "file_path": self.file_path,
            "confidence": self.confidence,
            "metadata": {k: str(v) for k, v in self.metadata.items()},
        }


@dataclass
class MetricTimeSeries:
    metric_name: str
    observations: List[MetricObservation] = field(default_factory=list)
    definition: Optional[MetricDefinition] = None

    def add(self, obs: MetricObservation):
        self.observations.append(obs)

    def values(self) -> List[float]:
        return [o.value for o in self.observations]

    def normalized_values(self) -> List[float]:
        return [o.normalized_value for o in self.observations]

    def timestamps(self) -> List[float]:
        return [o.timestamp for o in self.observations]

    def latest(self) -> Optional[float]:
        return self.observations[-1].value if self.observations else None

    def trend_slope(self) -> float:
        vals = self.values()
        if len(vals) < 2:
            return 0.0
        n = len(vals)
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(vals) / n
        num = sum((xs[i] - x_mean) * (vals[i] - y_mean) for i in range(n))
        den = sum((x - x_mean) ** 2 for x in xs)
        return num / den if den != 0 else 0.0

    def volatility(self) -> float:
        vals = self.normalized_values()
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        return math.sqrt(variance)

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "observation_count": len(self.observations),
            "latest_value": self.latest(),
            "trend_slope": self.trend_slope(),
            "volatility": self.volatility(),
            "observations": [o.to_dict() for o in self.observations[-20:]],
        }


class SoftwareEvolutionMetricsEngine:
    def __init__(self):
        self._metric_definitions: Dict[str, MetricDefinition] = self._define_metrics()
        self._series: Dict[str, MetricTimeSeries] = {}
        for name in self._metric_definitions:
            self._series[name] = MetricTimeSeries(
                metric_name=name, definition=self._metric_definitions[name]
            )

    def _define_metrics(self) -> Dict[str, MetricDefinition]:
        return {
            "architectural_stability": MetricDefinition(
                name="Architectural Stability",
                category=MetricCategory.STRUCTURAL,
                formal_meaning="Degree to which subsystem boundaries, dependency topology, and module assignments remain invariant over time.",
                observable_proxies=[
                    "Rate of module boundary changes",
                    "Variance in dependency directionality",
                    "Frequency of subsystem reassignment",
                    "Package rename/edit frequency",
                ],
                failure_cases=[
                    "Frequent module boundary shifts indicate instability",
                    "Dependency direction flips signal architectural confusion",
                    "High subsystem reassignment suggests poor initial decomposition",
                ],
                normalization_methods=[
                    "Z-score against repo history baseline",
                    "Min-max scaling per time window",
                    "Ratio of changed boundaries to total boundaries",
                ],
                visualization_approaches=[
                    "Rolling boundary-change heatmap over time",
                    "Annotated architecture diff timeline",
                    "Stability contour map over module graph",
                ],
                range_high=1.0,
                higher_is_better=True,
            ),
            "subsystem_entropy": MetricDefinition(
                name="Subsystem Entropy",
                category=MetricCategory.STRUCTURAL,
                formal_meaning="Information-theoretic measure of disorder in subsystem-module assignments, measuring how scattered or focused module ownership is.",
                observable_proxies=[
                    "Shannon entropy over file-to-subsystem distribution",
                    "Cross-subsystem file count variance",
                    "Module ownership concentration ratio",
                ],
                failure_cases=[
                    "High entropy = subsystem boundaries have no coherent purpose",
                    "Rising entropy over time indicates architectural degradation",
                    "Sudden entropy drops may indicate over-consolidation",
                ],
                normalization_methods=[
                    "Divide by log(N) for N subsystems to bound [0,1]",
                    "Entropy ratio compared to ideal modular decomposition",
                ],
                visualization_approaches=[
                    "Entropy trajectory with annotated refactor events",
                    "Per-subsystem entropy contribution stacked area",
                    "Arc diagram of cross-subsystem file scattering",
                ],
                range_high=1.0,
                higher_is_better=False,
            ),
            "abstraction_health": MetricDefinition(
                name="Abstraction Health",
                category=MetricCategory.STRUCTURAL,
                formal_meaning="Quality and consistency of abstraction layers, measured by dependency inversion adherence, interface stability, and layer isolation.",
                observable_proxies=[
                    "Dependency inversion principle violations",
                    "Interface change frequency",
                    "Layer-skip dependency count",
                    "Abstract-to-concrete ratio",
                ],
                failure_cases=[
                    "High layer-skip frequency indicates leaking abstractions",
                    "Frequent interface changes indicate unstable foundations",
                    "Low abstract-to-concrete ratio indicates under-abstraction",
                ],
                normalization_methods=[
                    "Ratio of layer-compliant to total dependencies",
                    "Interface stability index (SI = 1 - changes / total methods)",
                ],
                visualization_approaches=[
                    "Layer-violation chord diagram",
                    "Interface stability gauge over time",
                    "Abstraction pyramid heatmap",
                ],
                range_high=1.0,
                higher_is_better=True,
            ),
            "dependency_inflation": MetricDefinition(
                name="Dependency Inflation",
                category=MetricCategory.STRUCTURAL,
                formal_meaning="Rate at which dependency count grows relative to codebase size, indicating dependency bloat.",
                observable_proxies=[
                    "Dependencies per file ratio",
                    "Unique dependency growth rate",
                    "Transitive dependency fan-out",
                    "Dependency depth distribution",
                ],
                failure_cases=[
                    "Super-linear dependency growth relative to file count",
                    "Deep dependency chains indicate excessive coupling",
                    "High transitive fan-out makes change impact unpredictable",
                ],
                normalization_methods=[
                    "Divide by file count for density metric",
                    "Compare against language-typical dependency benchmarks",
                ],
                visualization_approaches=[
                    "Dependency density scatter over time",
                    "Dependency tree depth histogram evolution",
                    "Inflation rate sparkline with threshold zones",
                ],
                range_high=2.0,
                higher_is_better=False,
            ),
            "coupling_pressure": MetricDefinition(
                name="Coupling Pressure",
                category=MetricCategory.STRUCTURAL,
                formal_meaning="Degree to which modules are constrained by their dependencies, measuring how changes propagate through the system.",
                observable_proxies=[
                    "Afferent coupling (fan-in) per module",
                    "Efferent coupling (fan-out) per module",
                    "Change propagation probability",
                    "Instability metric (Ce / (Ce + Ca))",
                ],
                failure_cases=[
                    "High fan-in modules become single points of failure",
                    "High fan-out modules indicate excessive knowledge of system",
                    "Instability > 0.7 combined with high fan-in = fragile hub",
                ],
                normalization_methods=[
                    "Scale by module size in LOC",
                    "Normalize against median coupling of comparable systems",
                ],
                visualization_approaches=[
                    "Coupling pressure map with bubble chart",
                    "Instability vs. abstractness scatter (Martin's metrics)",
                    "Change-propagation Sankey diagram",
                ],
                range_high=1.0,
                higher_is_better=False,
            ),
            "invariant_fragility": MetricDefinition(
                name="Invariant Fragility",
                category=MetricCategory.QUALITY,
                formal_meaning="How frequently architectural invariants (patterns, conventions, constraints) are violated or contradicted over time.",
                observable_proxies=[
                    "Invariant violation rate per commit",
                    "Contradiction density per subsystem",
                    "Recovery time after invariant breakage",
                    "Permanently suppressed invariant count",
                ],
                failure_cases=[
                    "High violation rate indicates invariants don't match reality",
                    "Slow recovery indicates invariant enforcement is ineffective",
                    "Permanently suppressed invariants are dead rules",
                ],
                normalization_methods=[
                    "Violations per 1000 lines of code",
                    "Weighted by invariant severity tier",
                ],
                visualization_approaches=[
                    "Invariant violation timeline with severity stacking",
                    "Invariant survival curve (Kaplan-Meier style)",
                    "Violation heatmap across subsystems",
                ],
                range_high=1.0,
                higher_is_better=False,
            ),
            "repair_velocity": MetricDefinition(
                name="Repair Velocity",
                category=MetricCategory.DYNAMIC,
                formal_meaning="Speed and effectiveness of bug resolution, measured from introduction to fix, including recurrence patterns.",
                observable_proxies=[
                    "Mean time to repair (MTTR)",
                    "Bug introduction-to-fix latency",
                    "Fix recurrence rate per module",
                    "Fix distribution across authors",
                ],
                failure_cases=[
                    "Increasing MTTR signals growing system complexity",
                    "High recurrence in same module indicates incomplete fixes",
                    "Fix concentration in few authors indicates bus-factor risk",
                ],
                normalization_methods=[
                    "Log-transform MTTR for comparability",
                    "Normalize by file complexity score",
                ],
                visualization_approaches=[
                    "MTTR trend with percentile bands",
                    "Bug lifecycle swimlane diagram",
                    "Fix recurrence chord diagram per module",
                ],
                range_low=0.0,
                range_high=100.0,
                higher_is_better=True,
            ),
            "coordination_complexity": MetricDefinition(
                name="Coordination Complexity",
                category=MetricCategory.COORDINATION,
                formal_meaning="Overhead required to coordinate changes across the system, measured by cross-module change frequency and author coupling.",
                observable_proxies=[
                    "Cross-module commit ratio",
                    "Author touch-concentration per file",
                    "Simultaneous modification probability",
                    "Coordination event frequency",
                ],
                failure_cases=[
                    "High cross-module ratio indicates poor separation of concerns",
                    "Single files edited by many authors indicates ownership gaps",
                    "Rising coordination events signal growing integration costs",
                ],
                normalization_methods=[
                    "Divide by total commits for normalized coordination load",
                    "Shannon entropy over author-file distribution",
                ],
                visualization_approaches=[
                    "Coordination network graph over time",
                    "Author-file touch matrix heatmap",
                    "Coordination cost accumulation curve",
                ],
                range_high=1.0,
                higher_is_better=False,
            ),
            "cognitive_load": MetricDefinition(
                name="Cognitive Load",
                category=MetricCategory.COGNITIVE,
                formal_meaning="Estimated mental effort required to understand and modify the codebase, inferred from structural complexity proxies.",
                observable_proxies=[
                    "Average function length",
                    "Nesting depth distribution",
                    "Identifier name entropy",
                    "Conditional complexity (McCabe)",
                    "Comment-to-code ratio trend",
                ],
                failure_cases=[
                    "Deeply nested code increases working memory demand",
                    "Cryptic identifiers force frequent context-switching",
                    "Declining comment ratio with rising complexity masks intent",
                ],
                normalization_methods=[
                    "McCabe cyclomatic complexity per 100 LOC",
                    "Halstead effort metric normalized by module",
                ],
                visualization_approaches=[
                    "Cognitive load surface map over file structure",
                    "Complexity cliff annotation on timeline",
                    "Per-file cognitive load radar chart",
                ],
                range_high=100.0,
                higher_is_better=False,
            ),
            "technical_debt_acceleration": MetricDefinition(
                name="Technical Debt Acceleration",
                category=MetricCategory.QUALITY,
                formal_meaning="Second derivative of estimated technical debt accumulation, measuring whether debt is accelerating, stable, or being repaid.",
                observable_proxies=[
                    "TODO/FIXME accumulation rate",
                    "Workaround frequency growth",
                    "Test skip accumulation",
                    "Deprecation warning volume",
                    "Linting suppression growth",
                ],
                failure_cases=[
                    "Accelerating TODO density indicates deferral culture",
                    "Growing workaround count indicates architectural friction",
                    "Flat or declining debt with rising complexity = hidden debt",
                ],
                normalization_methods=[
                    "TODO density per 1000 LOC",
                    "Debt acceleration as second derivative of proxy sum",
                    "Industry benchmark percentile",
                ],
                visualization_approaches=[
                    "Debt acceleration gauge (positive/negative)",
                    "TODO/FIXME stacked trend with annotations",
                    "Debt repayment/accrual waterfall chart",
                ],
                range_high=1.0,
                higher_is_better=False,
            ),
        }

    def get_definitions(self) -> Dict[str, MetricDefinition]:
        return dict(self._metric_definitions)

    def get_series(self, metric_name: str) -> Optional[MetricTimeSeries]:
        return self._series.get(metric_name)

    def all_series(self) -> Dict[str, MetricTimeSeries]:
        return dict(self._series)

    def measure(self, repo_path: Path) -> Dict[str, MetricObservation]:
        repo_path = Path(repo_path).resolve()
        observations: Dict[str, MetricObservation] = {}
        ts = time.time()

        files_data = self._scan_files(repo_path)
        dep_graph = self._build_dependency_graph(repo_path, files_data)
        git_events = self._extract_git_events(repo_path)
        subsystems = self._detect_subsystems(repo_path)
        file_subsystem_map = self._map_files_to_subsystems(files_data, subsystems)

        obs = self._measure_architectural_stability(dep_graph, git_events, file_subsystem_map, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_subsystem_entropy(file_subsystem_map, subsystems, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_abstraction_health(dep_graph, files_data, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_dependency_inflation(dep_graph, files_data, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_coupling_pressure(dep_graph, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_invariant_fragility(repo_path, git_events, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_repair_velocity(git_events, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_coordination_complexity(git_events, repo_path, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_cognitive_load(files_data, ts)
        if obs:
            observations[obs.metric_name] = obs

        obs = self._measure_technical_debt_acceleration(files_data, git_events, repo_path, ts)
        if obs:
            observations[obs.metric_name] = obs

        for obs in observations.values():
            series = self._series.get(obs.metric_name)
            if series:
                series.add(obs)

        return observations

    def _scan_files(self, repo_path: Path) -> List[Dict[str, Any]]:
        files = []
        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                tree = ast.parse(text)
                funcs = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef))
                classes = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                imports = sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.Import, ast.ImportFrom)))
                max_nesting = self._max_nesting_depth(tree)
                comments = sum(1 for l in lines if l.strip().startswith("#"))
                todos = sum(1 for l in lines if "TODO" in l or "FIXME" in l or "HACK" in l or "XXX" in l)
                files.append({
                    "path": str(f.relative_to(repo_path)),
                    "lines": len(lines),
                    "functions": funcs,
                    "classes": classes,
                    "imports": imports,
                    "max_nesting": max_nesting,
                    "comments": comments,
                    "todos": todos,
                })
            except Exception:
                pass
        return files

    def _max_nesting_depth(self, node, current_depth=0) -> int:
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)):
                depth = self._max_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, depth)
            else:
                depth = self._max_nesting_depth(child, current_depth)
                max_depth = max(max_depth, depth)
        return max_depth

    def _build_dependency_graph(self, repo_path: Path, files_data: List[dict]) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {}
        for f in files_data:
            fpath = Path(f["path"])
            deps = set()
            try:
                text = (repo_path / fpath).read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            deps.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            deps.add(node.module.split(".")[0])
            except Exception:
                pass
            local_deps = {d for d in deps if any(
                f["path"].startswith(d.replace(".", "/")) or
                (repo_path / d.replace(".", "/").replace(".", "/")).exists()
                for f in files_data
            )}
            graph[f["path"]] = {d for d in local_deps if d != f["path"]}
        return graph

    def _extract_git_events(self, repo_path: Path) -> List[Dict[str, Any]]:
        events = []
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s",
                 "--numstat", "-500"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return events

            lines = result.stdout.splitlines()
            current = {}
            current_files = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^[a-f0-9]{40}$", line.split("|")[0] if "|" in line else ""):
                    if current and current_files:
                        current["files"] = current_files
                        events.append(current)
                    parts = line.split("|", 3)
                    current = {
                        "hash": parts[0],
                        "author": parts[1],
                        "timestamp": float(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
                        "message": parts[3] if len(parts) > 3 else "",
                    }
                    current_files = []
                elif re.match(r"^\d+\s+\d+\s+", line):
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        current_files.append({
                            "file": parts[2],
                            "added": int(parts[0]) if parts[0] != "-" else 0,
                            "removed": int(parts[1]) if parts[1] != "-" else 0,
                        })
            if current and current_files:
                current["files"] = current_files
                events.append(current)
        except Exception:
            pass
        return events

    def _detect_subsystems(self, repo_path: Path) -> List[str]:
        subsystems = set()
        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = f.relative_to(repo_path)
            parts = rel.parts
            if len(parts) > 1:
                subsystems.add(parts[0])
            else:
                subsystems.add("root")
        return sorted(subsystems)

    def _map_files_to_subsystems(self, files_data: List[dict], subsystems: List[str]) -> Dict[str, str]:
        mapping = {}
        for f in files_data:
            parts = Path(f["path"]).parts
            if len(parts) > 1:
                mapping[f["path"]] = parts[0]
            else:
                mapping[f["path"]] = "root"
        return mapping

    def _normalize(self, value: float, low: float, high: float, inverse: bool = False) -> float:
        if high == low:
            return 0.5
        clamped = max(low, min(high, value))
        normalized = (clamped - low) / (high - low)
        return 1.0 - normalized if inverse else normalized

    def _ns(self, value: float, series: MetricTimeSeries) -> float:
        if not series.definition:
            return 0.5
        return self._normalize(
            value,
            series.definition.range_low,
            series.definition.range_high,
            not series.definition.higher_is_better,
        )

    def _measure_architectural_stability(self, dep_graph: Dict[str, Set[str]],
                                          git_events: List[dict],
                                          file_sub_map: Dict[str, str],
                                          ts: float) -> Optional[MetricObservation]:
        if not git_events or len(git_events) < 2:
            return None

        recent = git_events[-min(50, len(git_events)):]
        boundary_changes = 0
        total_files = len(file_sub_map)

        for ev in recent:
            for f in ev.get("files", []):
                fp = f["file"]
                if fp in file_sub_map:
                    boundary_changes += 1

        stability = 1.0 - (boundary_changes / max(total_files * len(recent), 1))
        series = self._series.get("architectural_stability")
        norm = self._ns(stability, series) if series else stability
        return MetricObservation(
            metric_name="architectural_stability", value=stability,
            normalized_value=norm, timestamp=ts,
            metadata={"boundary_changes": boundary_changes, "total_files": total_files},
        )

    def _measure_subsystem_entropy(self, file_subsystem_map: Dict[str, str],
                                    subsystems: List[str],
                                    ts: float) -> Optional[MetricObservation]:
        if not subsystems:
            return None

        counts = Counter(file_subsystem_map.values())
        total = sum(counts.values())
        if total == 0:
            return None

        entropy = 0.0
        for sub in subsystems:
            p = counts.get(sub, 0) / total
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(subsystems)) if len(subsystems) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        series = self._series.get("subsystem_entropy")
        norm = self._ns(normalized_entropy, series) if series else normalized_entropy
        return MetricObservation(
            metric_name="subsystem_entropy", value=normalized_entropy,
            normalized_value=norm, timestamp=ts,
            metadata={"entropy": entropy, "max_entropy": max_entropy, "subsystem_count": len(subsystems)},
        )

    def _measure_abstraction_health(self, dep_graph: Dict[str, Set[str]],
                                     files_data: List[dict],
                                     ts: float) -> Optional[MetricObservation]:
        if not files_data:
            return None

        layer_violations = 0
        total_deps = 0
        for src, deps in dep_graph.items():
            src_parts = Path(src).parts
            for dep in deps:
                total_deps += 1
                dep_parts = Path(dep).parts if "/" in dep else (dep,)
                if len(src_parts) > 1 and len(dep_parts) > 1 and src_parts[0] != dep_parts[0]:
                    layer_violations += 1

        health = 1.0 - (layer_violations / max(total_deps, 1)) if total_deps > 0 else 1.0
        series = self._series.get("abstraction_health")
        norm = self._ns(health, series) if series else health
        return MetricObservation(
            metric_name="abstraction_health", value=health,
            normalized_value=norm, timestamp=ts,
            metadata={"layer_violations": layer_violations, "total_deps": total_deps},
        )

    def _measure_dependency_inflation(self, dep_graph: Dict[str, Set[str]],
                                       files_data: List[dict],
                                       ts: float) -> Optional[MetricObservation]:
        if not files_data:
            return None

        total_deps = sum(len(d) for d in dep_graph.values())
        file_count = len(files_data)
        density = total_deps / max(file_count, 1)

        threshold = 5.0
        inflation = min(2.0, density / threshold)

        series = self._series.get("dependency_inflation")
        norm = self._ns(inflation, series) if series else inflation
        return MetricObservation(
            metric_name="dependency_inflation", value=inflation,
            normalized_value=norm, timestamp=ts,
            metadata={"density": density, "total_deps": total_deps, "file_count": file_count},
        )

    def _measure_coupling_pressure(self, dep_graph: Dict[str, Set[str]],
                                    ts: float) -> Optional[MetricObservation]:
        if not dep_graph:
            return None

        fan_in: Counter = Counter()
        fan_out: Dict[str, int] = {}

        for src, deps in dep_graph.items():
            fan_out[src] = len(deps)
            for dep in deps:
                fan_in[dep] += 1

        if not fan_out:
            return None

        instabilities = []
        for node in dep_graph:
            ce = fan_out.get(node, 0)
            ca = fan_in.get(node, 0)
            if ce + ca > 0:
                instabilities.append(ce / (ce + ca))

        avg_pressure = sum(instabilities) / len(instabilities) if instabilities else 0.0

        series = self._series.get("coupling_pressure")
        norm = self._ns(avg_pressure, series) if series else avg_pressure
        return MetricObservation(
            metric_name="coupling_pressure", value=avg_pressure,
            normalized_value=norm, timestamp=ts,
            metadata={"avg_instability": avg_pressure, "nodes": len(instabilities)},
        )

    def _measure_invariant_fragility(self, repo_path: Path,
                                      git_events: List[dict],
                                      ts: float) -> Optional[MetricObservation]:
        if not git_events:
            return None

        today = time.time()
        month_ago = today - 86400 * 30
        recent = [e for e in git_events if e.get("timestamp", 0) > month_ago]

        violation_proxy = sum(
            1 for e in recent
            if any(kw in e.get("message", "").lower() for kw in ("violation", "break", "suppress", "disable"))
        )

        total_recent = len(recent)
        fragility = violation_proxy / max(total_recent, 1)

        series = self._series.get("invariant_fragility")
        norm = self._ns(fragility, series) if series else fragility
        return MetricObservation(
            metric_name="invariant_fragility", value=fragility,
            normalized_value=norm, timestamp=ts,
            metadata={"violations": violation_proxy, "total_commits": total_recent},
        )

    def _measure_repair_velocity(self, git_events: List[dict],
                                  ts: float) -> Optional[MetricObservation]:
        if not git_events:
            return None

        fix_events = []
        for e in git_events:
            msg = e.get("message", "").lower()
            if any(kw in msg for kw in ("fix", "bug", "hotfix", "patch", "resolve")):
                fix_events.append(e)

        if not fix_events:
            return None

        now = time.time()
        total_time = now - fix_events[0].get("timestamp", now)
        mttr = total_time / len(fix_events) if fix_events else 0

        mttr_days = mttr / 86400
        velocity = max(0, min(100, 30 / max(mttr_days, 1)))

        series = self._series.get("repair_velocity")
        norm = self._ns(velocity, series) if series else velocity / 100.0
        return MetricObservation(
            metric_name="repair_velocity", value=velocity,
            normalized_value=norm, timestamp=ts,
            metadata={"mttr_days": mttr_days, "fix_count": len(fix_events)},
        )

    def _measure_coordination_complexity(self, git_events: List[dict],
                                          repo_path: Path,
                                          ts: float) -> Optional[MetricObservation]:
        if not git_events:
            return None

        cross_module = 0
        total_commits_analyzed = 0
        for e in git_events:
            files = e.get("files", [])
            subsystems_in_commit = set()
            for f in files:
                parts = Path(f["file"]).parts
                if len(parts) > 1:
                    subsystems_in_commit.add(parts[0])
                else:
                    subsystems_in_commit.add("root")
            if len(subsystems_in_commit) > 1:
                cross_module += 1
            total_commits_analyzed += 1

        complexity = cross_module / max(total_commits_analyzed, 1)

        series = self._series.get("coordination_complexity")
        norm = self._ns(complexity, series) if series else complexity
        return MetricObservation(
            metric_name="coordination_complexity", value=complexity,
            normalized_value=norm, timestamp=ts,
            metadata={"cross_module": cross_module, "total": total_commits_analyzed},
        )

    def _measure_cognitive_load(self, files_data: List[dict],
                                 ts: float) -> Optional[MetricObservation]:
        if not files_data:
            return None

        if not files_data:
            return None

        avg_nesting = sum(f["max_nesting"] for f in files_data) / len(files_data)
        avg_func_len = sum(
            f["lines"] / max(f["functions"], 1) for f in files_data
        ) / len(files_data)

        load = avg_nesting * 10 + avg_func_len * 0.5

        series = self._series.get("cognitive_load")
        norm = self._ns(load, series) if series else min(1.0, load / 100.0)
        return MetricObservation(
            metric_name="cognitive_load", value=load,
            normalized_value=norm, timestamp=ts,
            metadata={"avg_nesting": avg_nesting, "avg_func_len": avg_func_len},
        )

    def _measure_technical_debt_acceleration(self, files_data: List[dict],
                                              git_events: List[dict],
                                              repo_path: Path,
                                              ts: float) -> Optional[MetricObservation]:
        if not files_data:
            return None

        total_todos = sum(f["todos"] for f in files_data)
        total_lines = sum(f["lines"] for f in files_data)
        todo_density = total_todos / max(total_lines, 1) * 1000

        if len(git_events) >= 10:
            mid = len(git_events) // 2
            early = git_events[:mid]
            late = git_events[mid:]

            early_todos = sum(
                1 for e in early
                if any(kw in e.get("message", "").lower() for kw in ("todo", "fixme", "hack"))
            )
            late_todos = sum(
                1 for e in late
                if any(kw in e.get("message", "").lower() for kw in ("todo", "fixme", "hack"))
            )
            acceleration = (late_todos - early_todos) / max(mid, 1)
        else:
            acceleration = 0.0

        debt = max(0, min(1, todo_density * 0.1 + acceleration * 0.1))

        series = self._series.get("technical_debt_acceleration")
        norm = self._ns(debt, series) if series else debt
        return MetricObservation(
            metric_name="technical_debt_acceleration", value=debt,
            normalized_value=norm, timestamp=ts,
            metadata={"todo_density": todo_density, "acceleration": acceleration},
        )

    def generate_report(self, repo_path: Optional[Path] = None) -> Dict[str, Any]:
        if repo_path:
            self.measure(repo_path)

        report = {
            "generated_at": time.time(),
            "metrics": {},
        }

        for name, series in self._series.items():
            defn = self._metric_definitions.get(name)
            obs = series.observations
            report["metrics"][name] = {
                "definition": defn.to_dict() if defn else {},
                "latest_value": series.latest(),
                "latest_normalized": obs[-1].normalized_value if obs else None,
                "trend_slope": series.trend_slope(),
                "volatility": series.volatility(),
                "observation_count": len(obs),
                "latest_observation": obs[-1].to_dict() if obs else None,
            }

        return report

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definitions": {
                name: defn.to_dict() for name, defn in self._metric_definitions.items()
            },
            "series": {name: s.to_dict() for name, s in self._series.items()},
        }
