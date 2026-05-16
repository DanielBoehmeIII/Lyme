from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DriftSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DriftMetricType(str, Enum):
    SUBSYSTEM_EROSION = "subsystem_erosion"
    ABSTRACTION_LEAKAGE = "abstraction_leakage"
    BOUNDARY_VIOLATION = "boundary_violation"
    DEPENDENCY_INFLATION = "dependency_inflation"
    COUPLING_GROWTH = "coupling_growth"
    TEST_FRAGILITY = "test_fragility"
    WORKAROUND_PATTERN = "workaround_pattern"
    ACCIDENTAL_ARCHITECTURE = "accidental_architecture"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    GOD_MODULE = "god_module"


@dataclass
class DriftMetric:
    metric_type: DriftMetricType = DriftMetricType.COUPLING_GROWTH
    name: str = ""
    current_value: float = 0.0
    previous_value: float = 0.0
    threshold: float = 0.5
    severity: DriftSeverity = DriftSeverity.NONE
    delta: float = 0.0
    delta_percent: float = 0.0
    file_path: str = ""
    subsystem: str = ""
    trend_direction: str = "stable"
    description: str = ""
    confidence: float = 1.0
    first_observed: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "metric_type": self.metric_type.value,
            "name": self.name,
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "file_path": self.file_path,
            "subsystem": self.subsystem,
            "trend_direction": self.trend_direction,
            "description": self.description,
            "confidence": self.confidence,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
        }


@dataclass
class DriftTrend:
    metric_type: DriftMetricType = DriftMetricType.COUPLING_GROWTH
    name: str = ""
    subsystem: str = ""
    values: List[Tuple[float, float]] = field(default_factory=list)
    slope: float = 0.0
    acceleration: float = 0.0
    projected_breach_time: Optional[float] = None
    severity: DriftSeverity = DriftSeverity.NONE

    def to_dict(self) -> dict:
        return {
            "metric_type": self.metric_type.value,
            "name": self.name,
            "subsystem": self.subsystem,
            "values": [(t, v) for t, v in self.values],
            "slope": self.slope,
            "acceleration": self.acceleration,
            "projected_breach_time": self.projected_breach_time,
            "severity": self.severity.value,
        }


@dataclass
class StabilizationStrategy:
    name: str = ""
    description: str = ""
    effort: str = "medium"
    impact: str = "medium"
    risk_reduction: float = 0.0
    affected_metrics: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "effort": self.effort,
            "impact": self.impact,
            "risk_reduction": self.risk_reduction,
            "affected_metrics": self.affected_metrics,
            "steps": self.steps,
        }


@dataclass
class DriftReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    repository: str = ""
    branch: str = ""
    commit: str = ""
    timestamp: float = field(default_factory=time.time)
    metrics: List[DriftMetric] = field(default_factory=list)
    trends: List[DriftTrend] = field(default_factory=list)
    overall_drift_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    stabilization_strategies: List[StabilizationStrategy] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "repository": self.repository,
            "branch": self.branch,
            "commit": self.commit,
            "timestamp": self.timestamp,
            "metrics": [m.to_dict() for m in self.metrics],
            "trends": [t.to_dict() for t in self.trends],
            "overall_drift_score": self.overall_drift_score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "stabilization_strategies": [s.to_dict() for s in self.stabilization_strategies],
            "summary": self.summary,
        }


class DriftDetector:
    def __init__(self):
        self._thresholds: Dict[DriftMetricType, float] = {
            DriftMetricType.SUBSYSTEM_EROSION: 0.4,
            DriftMetricType.ABSTRACTION_LEAKAGE: 0.3,
            DriftMetricType.BOUNDARY_VIOLATION: 0.5,
            DriftMetricType.DEPENDENCY_INFLATION: 0.6,
            DriftMetricType.COUPLING_GROWTH: 0.5,
            DriftMetricType.TEST_FRAGILITY: 0.4,
            DriftMetricType.WORKAROUND_PATTERN: 0.3,
            DriftMetricType.ACCIDENTAL_ARCHITECTURE: 0.4,
            DriftMetricType.CIRCULAR_DEPENDENCY: 0.7,
            DriftMetricType.GOD_MODULE: 0.5,
        }

    def analyze(self, file_structure: Dict[str, Any],
                dependency_graph: Dict[str, Set[str]] = None,
                source_files: Dict[str, str] = None,
                test_files: Dict[str, str] = None,
                git_history: List[Dict[str, Any]] = None,
                previous_report: DriftReport = None) -> DriftReport:
        report = DriftReport()
        metrics = []

        if file_structure:
            metrics.extend(self._measure_subsystem_erosion(file_structure))
            metrics.extend(self._measure_god_modules(file_structure, source_files))

        if dependency_graph:
            metrics.extend(self._measure_dependency_inflation(dependency_graph))
            metrics.extend(self._measure_coupling_growth(dependency_graph))
            metrics.extend(self._detect_circular_dependencies(dependency_graph))
            metrics.extend(self._detect_boundary_violations(dependency_graph, file_structure))

        if source_files:
            metrics.extend(self._detect_abstraction_leakage(source_files))

        if test_files and source_files:
            metrics.extend(self._measure_test_fragility(test_files, source_files))

        if git_history:
            metrics.extend(self._detect_workaround_patterns(git_history))

        report.metrics = metrics
        report.critical_count = sum(1 for m in metrics if m.severity == DriftSeverity.CRITICAL)
        report.high_count = sum(1 for m in metrics if m.severity == DriftSeverity.HIGH)
        report.medium_count = sum(1 for m in metrics if m.severity == DriftSeverity.MEDIUM)

        if previous_report:
            report.trends = self._compute_trends(metrics, previous_report)

        report.overall_drift_score = self._compute_overall_drift(metrics)
        report.stabilization_strategies = self._generate_strategies(metrics)
        report.summary = self._generate_summary(report)

        return report

    def _measure_subsystem_erosion(self, file_structure: Dict[str, Any]) -> List[DriftMetric]:
        metrics = []
        if "subsystems" not in file_structure:
            return metrics
        subsystems = file_structure["subsystems"]
        for name, files in subsystems.items():
            cross_subsystem_refs = len([
                f for f in files
                if isinstance(f, dict) and f.get("cross_subsystem", False)
            ])
            total = len(files)
            if total == 0:
                continue
            erosion = cross_subsystem_refs / total
            metrics.append(DriftMetric(
                metric_type=DriftMetricType.SUBSYSTEM_EROSION,
                name=f"subsystem:{name}",
                current_value=erosion,
                threshold=self._thresholds[DriftMetricType.SUBSYSTEM_EROSION],
                severity=self._severity_from_value(erosion, DriftMetricType.SUBSYSTEM_EROSION),
                subsystem=name,
                delta=erosion,
                description=f"{cross_subsystem_refs}/{total} files cross subsystem boundaries",
            ))
        return metrics

    def _measure_god_modules(self, file_structure: Dict[str, Any],
                              source_files: Dict[str, str] = None) -> List[DriftMetric]:
        metrics = []
        if not source_files:
            return metrics
        for file_path, content in source_files.items():
            lines = content.split("\n")
            func_count = content.count("def ") + content.count("function ")
            class_count = content.count("class ")
            if len(lines) > 500 or func_count > 20 or class_count > 10:
                god_score = min(1.0, (len(lines) / 2000) * 0.5 + (func_count / 50) * 0.3 + (class_count / 20) * 0.2)
                metrics.append(DriftMetric(
                    metric_type=DriftMetricType.GOD_MODULE,
                    name=f"god_module:{file_path}",
                    current_value=god_score,
                    threshold=self._thresholds[DriftMetricType.GOD_MODULE],
                    severity=self._severity_from_value(god_score, DriftMetricType.GOD_MODULE),
                    file_path=file_path,
                    description=f"{len(lines)} lines, {func_count} functions, {class_count} classes",
                ))
        return metrics

    def _measure_dependency_inflation(self, dependency_graph: Dict[str, Set[str]]) -> List[DriftMetric]:
        metrics = []
        for file_path, deps in dependency_graph.items():
            dep_count = len(deps)
            inflation = min(1.0, dep_count / 30)
            if inflation > 0.3:
                metrics.append(DriftMetric(
                    metric_type=DriftMetricType.DEPENDENCY_INFLATION,
                    name=f"deps:{file_path}",
                    current_value=inflation,
                    threshold=self._thresholds[DriftMetricType.DEPENDENCY_INFLATION],
                    severity=self._severity_from_value(inflation, DriftMetricType.DEPENDENCY_INFLATION),
                    file_path=file_path,
                    description=f"{dep_count} direct dependencies",
                ))
        return metrics

    def _measure_coupling_growth(self, dependency_graph: Dict[str, Set[str]]) -> List[DriftMetric]:
        metrics = []
        reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        for src, targets in dependency_graph.items():
            for tgt in targets:
                reverse_deps[tgt].add(src)

        for file_path, dependents in reverse_deps.items():
            coupling = len(dependents)
            fan_in_ratio = min(1.0, coupling / 20)
            if fan_in_ratio > 0.3:
                metrics.append(DriftMetric(
                    metric_type=DriftMetricType.COUPLING_GROWTH,
                    name=f"coupling:{file_path}",
                    current_value=fan_in_ratio,
                    threshold=self._thresholds[DriftMetricType.COUPLING_GROWTH],
                    severity=self._severity_from_value(fan_in_ratio, DriftMetricType.COUPLING_GROWTH),
                    file_path=file_path,
                    description=f"{coupling} dependents (fan-in)",
                ))
        return metrics

    def _detect_circular_dependencies(self, dependency_graph: Dict[str, Set[str]]) -> List[DriftMetric]:
        metrics = []
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str):
            if node in path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                metrics.append(DriftMetric(
                    metric_type=DriftMetricType.CIRCULAR_DEPENDENCY,
                    name=f"cycle:{'->'.join(cycle[:5])}",
                    current_value=1.0,
                    threshold=self._thresholds[DriftMetricType.CIRCULAR_DEPENDENCY],
                    severity=DriftSeverity.HIGH,
                    file_path=node,
                    description=f"Circular dependency: {' -> '.join(cycle)}",
                ))
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for neighbor in dependency_graph.get(node, set()):
                dfs(neighbor)
            path.pop()

        for node in dependency_graph:
            dfs(node)
        return metrics

    def _detect_boundary_violations(self, dependency_graph: Dict[str, Set[str]],
                                     file_structure: Dict[str, Any]) -> List[DriftMetric]:
        metrics = []
        if "subsystems" not in file_structure:
            return metrics
        subsystem_files: Dict[str, Set[str]] = {}
        for sub_name, files in file_structure["subsystems"].items():
            subsystem_files[sub_name] = set()
            for f in files:
                if isinstance(f, str):
                    subsystem_files[sub_name].add(f)
                elif isinstance(f, dict):
                    subsystem_files[sub_name].add(f.get("path", ""))

        for sub_a, files_a in subsystem_files.items():
            for sub_b, files_b in subsystem_files.items():
                if sub_a >= sub_b:
                    continue
                violations = 0
                for fa in files_a:
                    for fb in files_b:
                        if fb in dependency_graph.get(fa, set()):
                            violations += 1
                if violations > 2:
                    metrics.append(DriftMetric(
                        metric_type=DriftMetricType.BOUNDARY_VIOLATION,
                        name=f"boundary:{sub_a}->{sub_b}",
                        current_value=min(1.0, violations / 10),
                        threshold=self._thresholds[DriftMetricType.BOUNDARY_VIOLATION],
                        severity=self._severity_from_value(min(1.0, violations / 10), DriftMetricType.BOUNDARY_VIOLATION),
                        description=f"{violations} illegal cross-boundary references from {sub_a} to {sub_b}",
                    ))
        return metrics

    def _detect_abstraction_leakage(self, source_files: Dict[str, str]) -> List[DriftMetric]:
        import re
        metrics = []
        leak_patterns = [
            (r'\.\./\.\./', "excessive_upward_reference"),
            (r'os\.environ', "environment_leak"),
            (r'global\s+\w+', "global_state_leak"),
            (r'sys\.path', "sys_path_manipulation"),
            (r'__import__', "dynamic_import"),
        ]
        for file_path, content in source_files.items():
            leak_count = 0
            for pattern, name in leak_patterns:
                matches = re.findall(pattern, content)
                leak_count += len(matches)
            if leak_count > 0:
                leakage = min(1.0, leak_count / 10)
                metrics.append(DriftMetric(
                    metric_type=DriftMetricType.ABSTRACTION_LEAKAGE,
                    name=f"leak:{file_path}",
                    current_value=leakage,
                    threshold=self._thresholds[DriftMetricType.ABSTRACTION_LEAKAGE],
                    severity=self._severity_from_value(leakage, DriftMetricType.ABSTRACTION_LEAKAGE),
                    file_path=file_path,
                    description=f"{leak_count} abstraction leaks detected",
                ))
        return metrics

    def _measure_test_fragility(self, test_files: Dict[str, str],
                                 source_files: Dict[str, str]) -> List[DriftMetric]:
        metrics = []
        test_to_source_ratio = len(test_files) / max(len(source_files), 1)
        if test_to_source_ratio < 0.1:
            metrics.append(DriftMetric(
                metric_type=DriftMetricType.TEST_FRAGILITY,
                name="test_coverage",
                current_value=1.0 - test_to_source_ratio,
                threshold=self._thresholds[DriftMetricType.TEST_FRAGILITY],
                severity=DriftSeverity.HIGH,
                description=f"Low test-to-source ratio: {test_to_source_ratio:.2%}",
            ))
        large_tests = sum(1 for t in test_files.values() if len(t.split("\n")) > 200)
        if large_tests > 0:
            fragility = min(1.0, large_tests / len(test_files))
            metrics.append(DriftMetric(
                metric_type=DriftMetricType.TEST_FRAGILITY,
                name="large_tests",
                current_value=fragility,
                threshold=self._thresholds[DriftMetricType.TEST_FRAGILITY],
                severity=self._severity_from_value(fragility, DriftMetricType.TEST_FRAGILITY),
                description=f"{large_tests} overly large test files",
            ))
        return metrics

    def _detect_workaround_patterns(self, git_history: List[Dict[str, Any]]) -> List[DriftMetric]:
        metrics = []
        workaround_keywords = ["workaround", "hack", "temporary", "TODO", "FIXME",
                               "hacky", "patch", "quickfix", "hotfix"]
        keyword_counts: Dict[str, int] = defaultdict(int)
        for commit in git_history:
            message = commit.get("message", "").lower()
            for kw in workaround_keywords:
                if kw in message:
                    keyword_counts[kw] += 1
        total_workarounds = sum(keyword_counts.values())
        if total_workarounds > 0:
            workaround_score = min(1.0, total_workarounds / 50)
            metrics.append(DriftMetric(
                metric_type=DriftMetricType.WORKAROUND_PATTERN,
                name="workaround_frequency",
                current_value=workaround_score,
                threshold=self._thresholds[DriftMetricType.WORKAROUND_PATTERN],
                severity=self._severity_from_value(workaround_score, DriftMetricType.WORKAROUND_PATTERN),
                description=f"{total_workarounds} workaround/hack references in git history",
            ))
        return metrics

    def _compute_trends(self, current_metrics: List[DriftMetric],
                         previous_report: DriftReport) -> List[DriftTrend]:
        trends = []
        prev_metrics = {m.name: m for m in previous_report.metrics}
        for cur in current_metrics:
            prev = prev_metrics.get(cur.name)
            if prev:
                delta = cur.current_value - prev.current_value
                trend = DriftTrend(
                    metric_type=cur.metric_type,
                    name=cur.name,
                    subsystem=cur.subsystem,
                    values=[(prev.last_observed, prev.current_value), (cur.last_observed, cur.current_value)],
                    slope=delta / max(cur.last_observed - prev.last_observed, 1),
                    severity=self._severity_from_trend(delta, cur),
                )
                if delta > 0.1:
                    if cur.current_value >= cur.threshold:
                        time_to_breach = max(
                            0,
                            (1.0 - cur.current_value) / max(trend.slope, 0.001)
                        )
                        trend.projected_breach_time = time.time() + time_to_breach
                trends.append(trend)
        return trends

    def _compute_overall_drift(self, metrics: List[DriftMetric]) -> float:
        if not metrics:
            return 0.0
        weights = {
            DriftSeverity.CRITICAL: 1.0,
            DriftSeverity.HIGH: 0.7,
            DriftSeverity.MEDIUM: 0.4,
            DriftSeverity.LOW: 0.2,
            DriftSeverity.NONE: 0.0,
        }
        total_weight = sum(weights.get(m.severity, 0) for m in metrics)
        return min(1.0, total_weight / max(len(metrics), 1))

    def _generate_strategies(self, metrics: List[DriftMetric]) -> List[StabilizationStrategy]:
        strategies = []
        high_severity = [m for m in metrics if m.severity in (DriftSeverity.CRITICAL, DriftSeverity.HIGH)]
        if not high_severity:
            return strategies

        if any(m.metric_type == DriftMetricType.CIRCULAR_DEPENDENCY for m in high_severity):
            strategies.append(StabilizationStrategy(
                name="Break Circular Dependencies",
                description="Extract shared dependencies into a common module",
                effort="high",
                impact="high",
                risk_reduction=0.7,
                affected_metrics=[m.name for m in high_severity if m.metric_type == DriftMetricType.CIRCULAR_DEPENDENCY],
                steps=["Identify cycle roots", "Create shared interface module", "Refactor participants"],
            ))
        if any(m.metric_type == DriftMetricType.GOD_MODULE for m in high_severity):
            strategies.append(StabilizationStrategy(
                name="Split God Modules",
                description="Decompose oversized modules by responsibility",
                effort="medium",
                impact="high",
                risk_reduction=0.6,
                affected_metrics=[m.name for m in high_severity if m.metric_type == DriftMetricType.GOD_MODULE],
                steps=["Extract cohesive subsets", "Create focused modules", "Update imports"],
            ))
        if any(m.metric_type == DriftMetricType.BOUNDARY_VIOLATION for m in high_severity):
            strategies.append(StabilizationStrategy(
                name="Enforce Subsystem Boundaries",
                description="Establish and enforce architectural boundaries",
                effort="high",
                impact="medium",
                risk_reduction=0.5,
                affected_metrics=[m.name for m in high_severity if m.metric_type == DriftMetricType.BOUNDARY_VIOLATION],
                steps=["Define allowed dependency directions", "Add architectural tests", "Refactor violations"],
            ))
        return strategies[:5]

    def _generate_summary(self, report: DriftReport) -> str:
        parts = []
        parts.append(f"Overall drift: {report.overall_drift_score:.1%}")
        if report.critical_count:
            parts.append(f"{report.critical_count} critical")
        if report.high_count:
            parts.append(f"{report.high_count} high")
        if report.medium_count:
            parts.append(f"{report.medium_count} medium")
        type_counts = defaultdict(int)
        for m in report.metrics:
            type_counts[m.metric_type.value] += 1
        types = sorted(type_counts.items(), key=lambda x: -x[1])[:3]
        parts.append("top: " + ", ".join(f"{t}={c}" for t, c in types))
        return " | ".join(parts)

    def _severity_from_value(self, value: float, metric_type: DriftMetricType) -> DriftSeverity:
        threshold = self._thresholds.get(metric_type, 0.5)
        if value >= threshold * 1.8:
            return DriftSeverity.CRITICAL
        elif value >= threshold * 1.3:
            return DriftSeverity.HIGH
        elif value >= threshold:
            return DriftSeverity.MEDIUM
        elif value >= threshold * 0.5:
            return DriftSeverity.LOW
        return DriftSeverity.NONE

    def _severity_from_trend(self, delta: float, metric: DriftMetric) -> DriftSeverity:
        if delta > 0.2:
            return DriftSeverity.HIGH
        elif delta > 0.1:
            return DriftSeverity.MEDIUM
        elif delta > 0.05:
            return DriftSeverity.LOW
        return DriftSeverity.NONE
