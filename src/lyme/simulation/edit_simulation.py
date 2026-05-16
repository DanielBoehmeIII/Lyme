from __future__ import annotations

import difflib
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SimulationConfidence(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    SPECULATIVE = "speculative"


class BreakageSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class AffectedSystem:
    name: str = ""
    file_path: str = ""
    subsystem: str = ""
    impact_type: str = "direct"
    confidence: float = 0.0
    breakage_probability: float = 0.0
    estimated_repair_time: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "subsystem": self.subsystem,
            "impact_type": self.impact_type,
            "confidence": self.confidence,
            "breakage_probability": self.breakage_probability,
            "estimated_repair_time": self.estimated_repair_time,
            "description": self.description,
        }


@dataclass
class BreakageEstimate:
    system: str = ""
    file_path: str = ""
    severity: BreakageSeverity = BreakageSeverity.LOW
    probability: float = 0.0
    estimated_tests_failed: int = 0
    estimated_repair_lines: int = 0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "file_path": self.file_path,
            "severity": self.severity.value,
            "probability": self.probability,
            "estimated_tests_failed": self.estimated_tests_failed,
            "estimated_repair_lines": self.estimated_repair_lines,
            "description": self.description,
        }


@dataclass
class InvariantViolation:
    invariant_type: str = ""
    description: str = ""
    file_path: str = ""
    line_number: int = 0
    confidence: float = 0.0
    severity: BreakageSeverity = BreakageSeverity.MEDIUM
    suggested_mitigation: str = ""

    def to_dict(self) -> dict:
        return {
            "invariant_type": self.invariant_type,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "suggested_mitigation": self.suggested_mitigation,
        }


@dataclass
class DependencyPropagation:
    from_file: str = ""
    to_file: str = ""
    chain_length: int = 0
    hop_count: int = 0
    breakage_risk: float = 0.0
    propagation_path: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "from_file": self.from_file,
            "to_file": self.to_file,
            "chain_length": self.chain_length,
            "hop_count": self.hop_count,
            "breakage_risk": self.breakage_risk,
            "propagation_path": self.propagation_path,
        }


@dataclass
class AlternativeEdit:
    description: str = ""
    affected_systems: List[str] = field(default_factory=list)
    risk_reduction: float = 0.0
    effort_estimate: str = "medium"
    confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "affected_systems": self.affected_systems,
            "risk_reduction": self.risk_reduction,
            "effort_estimate": self.effort_estimate,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


@dataclass
class EditHypothesis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    file_path: str = ""
    line_number: int = 0
    original_text: str = ""
    proposed_text: str = ""
    edit_type: str = "modify"
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "original_text": self.original_text,
            "proposed_text": self.proposed_text,
            "edit_type": self.edit_type,
            "rationale": self.rationale,
        }


@dataclass
class EditSimulationResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    edit_hypothesis: EditHypothesis = field(default_factory=EditHypothesis)
    affected_systems: List[AffectedSystem] = field(default_factory=list)
    breakage_estimates: List[BreakageEstimate] = field(default_factory=list)
    invariant_violations: List[InvariantViolation] = field(default_factory=list)
    dependency_propagations: List[DependencyPropagation] = field(default_factory=list)
    alternative_edits: List[AlternativeEdit] = field(default_factory=list)
    overall_risk: float = 0.0
    confidence: SimulationConfidence = SimulationConfidence.LOW
    uncertainty_zones: List[str] = field(default_factory=list)
    summary: str = ""
    simulation_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "edit_hypothesis": self.edit_hypothesis.to_dict(),
            "affected_systems": [s.to_dict() for s in self.affected_systems],
            "breakage_estimates": [b.to_dict() for b in self.breakage_estimates],
            "invariant_violations": [v.to_dict() for v in self.invariant_violations],
            "dependency_propagations": [d.to_dict() for d in self.dependency_propagations],
            "alternative_edits": [a.to_dict() for a in self.alternative_edits],
            "overall_risk": self.overall_risk,
            "confidence": self.confidence.value,
            "uncertainty_zones": self.uncertainty_zones,
            "summary": self.summary,
            "simulation_time_ms": self.simulation_time_ms,
        }


@dataclass
class SimulationConfig:
    max_propagation_depth: int = 5
    min_confidence_threshold: float = 0.3
    consider_test_impact: bool = True
    consider_runtime_traces: bool = True
    consider_historical_repairs: bool = True
    max_alternatives: int = 3
    risk_sensitivity: float = 1.0


class EditSimulator:
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self._dependency_cache: Dict[str, Set[str]] = {}
        self._import_cache: Dict[str, List[str]] = {}

    def simulate(self, edit: EditHypothesis,
                 dependency_graph: Dict[str, Set[str]] = None,
                 source_files: Dict[str, str] = None,
                 test_files: Dict[str, str] = None,
                 historical_repairs: List[Dict[str, Any]] = None,
                 runtime_traces: List[Dict[str, Any]] = None) -> EditSimulationResult:
        start = time.time()
        result = EditSimulationResult(edit_hypothesis=edit)

        affected = self._find_affected_systems(edit, dependency_graph)
        result.affected_systems = affected

        breakages = self._estimate_breakages(edit, affected, dependency_graph,
                                              source_files, test_files)
        result.breakage_estimates = breakages

        violations = self._detect_invariant_violations(edit, source_files)
        result.invariant_violations = violations

        propagations = self._trace_dependency_propagation(edit, dependency_graph)
        result.dependency_propagations = propagations

        alternatives = self._generate_alternatives(edit, affected, breakages,
                                                    dependency_graph, source_files)
        result.alternative_edits = alternatives

        result.overall_risk = self._compute_overall_risk(breakages, violations, propagations)
        result.confidence = self._determine_confidence(result, source_files)
        result.uncertainty_zones = self._identify_uncertainty_zones(
            edit, dependency_graph, source_files
        )
        result.summary = self._generate_summary(result)
        result.simulation_time_ms = (time.time() - start) * 1000

        return result

    def _find_affected_systems(self, edit: EditHypothesis,
                                dependency_graph: Dict[str, Set[str]] = None) -> List[AffectedSystem]:
        affected = []
        if not dependency_graph or edit.file_path not in dependency_graph:
            return affected

        direct = dependency_graph.get(edit.file_path, set())
        for dep in direct:
            affected.append(AffectedSystem(
                name=dep,
                file_path=dep,
                impact_type="direct",
                confidence=0.8,
                breakage_probability=0.3,
                description=f"Direct dependency of {edit.file_path}",
            ))

        visited = {edit.file_path}
        queue = [(dep, 1) for dep in direct]
        while queue:
            node, depth = queue.pop(0)
            if depth > self.config.max_propagation_depth:
                continue
            if node in visited:
                continue
            visited.add(node)
            if dependency_graph.get(node):
                for transitive_dep in dependency_graph[node]:
                    if transitive_dep not in visited:
                        affected.append(AffectedSystem(
                            name=transitive_dep,
                            file_path=transitive_dep,
                            impact_type="transitive",
                            confidence=max(0.3, 0.7 - depth * 0.1),
                            breakage_probability=max(0.1, 0.3 - depth * 0.05),
                            description=f"Transitive dependency (depth={depth}) of {edit.file_path}",
                        ))
                        queue.append((transitive_dep, depth + 1))
        return affected

    def _estimate_breakages(self, edit: EditHypothesis,
                             affected: List[AffectedSystem],
                             dependency_graph: Dict[str, Set[str]] = None,
                             source_files: Dict[str, str] = None,
                             test_files: Dict[str, str] = None) -> List[BreakageEstimate]:
        estimates = []
        for system in affected:
            severity = BreakageSeverity.LOW
            prob = system.breakage_probability
            if prob > 0.5:
                severity = BreakageSeverity.HIGH
            elif prob > 0.3:
                severity = BreakageSeverity.MEDIUM

            test_count = 0
            if test_files:
                test_count = sum(
                    1 for tf in test_files
                    if system.file_path in tf or system.name in tf
                )

            estimates.append(BreakageEstimate(
                system=system.name,
                file_path=system.file_path,
                severity=severity,
                probability=prob,
                estimated_tests_failed=max(1, int(test_count * prob)),
                estimated_repair_lines=max(1, int(10 * prob)),
                description=f"Edit to {edit.file_path} may break {system.name}",
            ))
        return estimates

    def _detect_invariant_violations(self, edit: EditHypothesis,
                                      source_files: Dict[str, str] = None) -> List[InvariantViolation]:
        violations = []
        if not source_files or edit.file_path not in source_files:
            return violations

        original = source_files.get(edit.file_path, "")

        interface_violations = self._check_interface_invariants(edit, original)
        violations.extend(interface_violations)

        type_violations = self._check_type_invariants(edit, original)
        violations.extend(type_violations)

        return violations

    def _check_interface_invariants(self, edit: EditHypothesis,
                                     source: str) -> List[InvariantViolation]:
        violations = []
        import re
        original_text = edit.original_text
        proposed_text = edit.proposed_text

        orig_funcs = set(re.findall(r'def\s+(\w+)\s*\(', original_text))
        prop_funcs = set(re.findall(r'def\s+(\w+)\s*\(', proposed_text))
        removed = orig_funcs - prop_funcs
        for func in removed:
            violations.append(InvariantViolation(
                invariant_type="function_removed",
                description=f"Function '{func}' would be removed by edit",
                file_path=edit.file_path,
                confidence=0.9,
                severity=BreakageSeverity.CRITICAL,
                suggested_mitigation=f"Add deprecation path or update callers of {func}",
            ))

        orig_signatures = set(re.findall(r'def\s+\w+\(([^)]*)\)', original_text))
        prop_signatures = set(re.findall(r'def\s+\w+\(([^)]*)\)', proposed_text))
        if orig_signatures and orig_signatures != prop_signatures:
            violations.append(InvariantViolation(
                invariant_type="signature_changed",
                description="Function signatures modified - may break callers",
                file_path=edit.file_path,
                confidence=0.7,
                severity=BreakageSeverity.HIGH,
                suggested_mitigation="Verify all callers are updated",
            ))

        orig_classes = set(re.findall(r'class\s+(\w+)\s*[\(:]', original_text))
        prop_classes = set(re.findall(r'class\s+(\w+)\s*[\(:]', proposed_text))
        if orig_classes and len(orig_classes) != len(prop_classes):
            violations.append(InvariantViolation(
                invariant_type="class_modified",
                description="Class structure modified by edit",
                file_path=edit.file_path,
                confidence=0.6,
                severity=BreakageSeverity.MEDIUM,
            ))
        return violations

    def _check_type_invariants(self, edit: EditHypothesis,
                                source: str) -> List[InvariantViolation]:
        violations = []
        orig_tname = set()
        prop_tname = set()
        for text, tset in [(edit.original_text, orig_tname), (edit.proposed_text, prop_tname)]:
            for m in __import__('re').finditer(r'(\w+)\s*[=:]\s*(?:\w+\s*<\s*)?(\w+)', text):
                tset.add(m.group(1))
        return violations

    def _trace_dependency_propagation(self, edit: EditHypothesis,
                                       dependency_graph: Dict[str, Set[str]] = None) -> List[DependencyPropagation]:
        propagations = []
        if not dependency_graph or edit.file_path not in dependency_graph:
            return propagations

        visited = {edit.file_path}
        queue: List[Tuple[str, int, List[str]]] = [(edit.file_path, 0, [edit.file_path])]

        while queue:
            node, depth, path = queue.pop(0)
            if depth > self.config.max_propagation_depth:
                continue
            for neighbor in dependency_graph.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    propagations.append(DependencyPropagation(
                        from_file=edit.file_path,
                        to_file=neighbor,
                        chain_length=depth + 1,
                        hop_count=depth + 1,
                        breakage_risk=max(0.1, 0.5 - depth * 0.08),
                        propagation_path=list(new_path),
                    ))
                    queue.append((neighbor, depth + 1, new_path))
        return propagations

    def _generate_alternatives(self, edit: EditHypothesis,
                                affected: List[AffectedSystem],
                                breakages: List[BreakageEstimate],
                                dependency_graph: Dict[str, Set[str]] = None,
                                source_files: Dict[str, str] = None) -> List[AlternativeEdit]:
        alternatives = []
        high_risk = [b for b in breakages if b.severity in (BreakageSeverity.CRITICAL, BreakageSeverity.HIGH)]
        if high_risk:
            alternatives.append(AlternativeEdit(
                description="Add compatibility layer or adapter pattern",
                affected_systems=[b.system for b in high_risk],
                risk_reduction=0.4,
                effort_estimate="medium",
                confidence=0.6,
                rationale="Isolates changes from downstream dependencies",
            ))
        interface_issues = [v for v in self._detect_invariant_violations(edit) if v.severity == BreakageSeverity.CRITICAL]
        if interface_issues:
            alternatives.append(AlternativeEdit(
                description="Preserve original interface and add new function alongside",
                affected_systems=[edit.file_path],
                risk_reduction=0.7,
                effort_estimate="low",
                confidence=0.8,
                rationale="Backward-compatible change preserves all existing callers",
            ))
        if affected and len(affected) > 5:
            alternatives.append(AlternativeEdit(
                description="Split edit into smaller, independent changes",
                affected_systems=[s.name for s in affected[:3]],
                risk_reduction=0.3,
                effort_estimate="high",
                confidence=0.5,
                rationale="Smaller changes are easier to verify and roll back",
            ))
        return alternatives[:self.config.max_alternatives]

    def _compute_overall_risk(self, breakages: List[BreakageEstimate],
                               violations: List[InvariantViolation],
                               propagations: List[DependencyPropagation]) -> float:
        if not breakages and not violations:
            return 0.0
        breakage_risk = sum(
            b.probability * {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1, "none": 0.0}.get(b.severity.value, 0.3)
            for b in breakages
        ) / max(len(breakages), 1)
        violation_risk = sum(
            {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}.get(v.severity.value, 0.3)
            for v in violations
        ) / max(len(violations), 1)
        propagation_count_risk = min(1.0, len(propagations) / 20)
        return (breakage_risk * 0.4 + violation_risk * 0.35 + propagation_count_risk * 0.25) * self.config.risk_sensitivity

    def _determine_confidence(self, result: EditSimulationResult,
                               source_files: Dict[str, str] = None) -> SimulationConfidence:
        if not source_files or result.edit_hypothesis.file_path not in source_files:
            return SimulationConfidence.SPECULATIVE
        if result.overall_risk < 0.2 and len(result.affected_systems) < 3:
            return SimulationConfidence.HIGH
        if result.overall_risk < 0.4:
            return SimulationConfidence.MODERATE
        if result.overall_risk < 0.7:
            return SimulationConfidence.LOW
        return SimulationConfidence.SPECULATIVE

    def _identify_uncertainty_zones(self, edit: EditHypothesis,
                                     dependency_graph: Dict[str, Set[str]] = None,
                                     source_files: Dict[str, str] = None) -> List[str]:
        zones = []
        if not dependency_graph:
            zones.append("no_dependency_graph")
        if edit.file_path and dependency_graph and edit.file_path not in dependency_graph:
            zones.append(f"file_not_in_dependency_graph:{edit.file_path}")
        if source_files and edit.file_path not in source_files:
            zones.append("file_content_unavailable")
        return zones

    def _generate_summary(self, result: EditSimulationResult) -> str:
        parts = [f"Edit to {result.edit_hypothesis.file_path}"]
        parts.append(f"Risk: {result.overall_risk:.1%}")
        parts.append(f"Confidence: {result.confidence.value}")
        if result.affected_systems:
            direct = sum(1 for s in result.affected_systems if s.impact_type == "direct")
            transitive = len(result.affected_systems) - direct
            parts.append(f"Affects {direct} direct + {transitive} transitive")
        if result.breakage_estimates:
            high = sum(1 for b in result.breakage_estimates if b.severity == BreakageSeverity.HIGH)
            if high:
                parts.append(f"{high} high-risk breakages")
        if result.alternative_edits:
            parts.append(f"{len(result.alternative_edits)} alternatives suggested")
        return " | ".join(parts)

    def build_dependency_graph(self, source_files: Dict[str, str]) -> Dict[str, Set[str]]:
        import re
        graph: Dict[str, Set[str]] = {}
        for file_path, content in source_files.items():
            deps: Set[str] = set()
            for m in re.finditer(r'(?:from|import)\s+([\w.]+)', content):
                dep_name = m.group(1).replace(".", "/")
                for candidate in source_files:
                    if dep_name in candidate.replace("/", ".") or dep_name in candidate:
                        deps.add(candidate)
            if file_path in graph:
                graph[file_path].update(deps)
            else:
                graph[file_path] = deps
        return graph

    def simulate_alternative_comparison(self, edits: List[EditHypothesis],
                                         dependency_graph: Dict[str, Set[str]] = None,
                                         source_files: Dict[str, str] = None) -> List[EditSimulationResult]:
        return [
            self.simulate(edit, dependency_graph, source_files)
            for edit in edits
        ]

    def compare_alternatives(self, results: List[EditSimulationResult]) -> Dict[str, Any]:
        if not results:
            return {"best": None, "comparison": []}
        comparison = []
        for r in results:
            comparison.append({
                "edit_id": r.id,
                "file": r.edit_hypothesis.file_path,
                "risk": r.overall_risk,
                "confidence": r.confidence.value,
                "breakages": len(r.breakage_estimates),
                "violations": len(r.invariant_violations),
                "alternatives": len(r.alternative_edits),
            })
        comparison.sort(key=lambda x: x["risk"])
        return {
            "best": comparison[0],
            "comparison": comparison,
            "risk_spread": comparison[-1]["risk"] - comparison[0]["risk"] if len(comparison) > 1 else 0,
        }
