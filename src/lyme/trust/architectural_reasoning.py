"""ArchitecturalReasoning — validates architecture decisions against known patterns."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class ArchitecturalDecisionType(str, Enum):
    PATTERN_SELECTION = "pattern_selection"
    DEPENDENCY_CHOICE = "dependency_choice"
    COMPONENT_DECOMPOSITION = "component_decomposition"
    DATA_FLOW = "data_flow"
    API_DESIGN = "api_design"
    DEPLOYMENT_STRATEGY = "deployment_strategy"


class ValidationResult(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class ArchitecturalDecision:
    decision_type: ArchitecturalDecisionType
    description: str
    rationale: str
    alternatives: List[str]
    constraints: List[str]
    consequences: List[str]

    def to_dict(self) -> Dict:
        return {
            "type": self.decision_type.value,
            "description": self.description[:60],
            "alternatives": len(self.alternatives),
            "constraints": len(self.constraints),
        }


@dataclass
class DecisionValidation:
    decision: ArchitecturalDecision
    result: ValidationResult
    evidence: List[str]
    risks_found: List[str]
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision.description[:40],
            "result": self.result.value,
            "risks": len(self.risks_found),
        }


@dataclass
class ArchitectureReasoningReport:
    total_decisions: int
    passed: int
    warnings: int
    failed: int
    validations: List[Dict]
    insights: List[str]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  ARCHITECTURAL REASONING REPORT")
        lines.append("=" * 70)
        lines.append(f"  Decisions: {self.total_decisions} | "
                     f"Passed: {self.passed} | "
                     f"Warnings: {self.warnings} | "
                     f"Failed: {self.failed}")
        lines.append("")
        for v in self.validations[:5]:
            icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}
            lines.append(f"  {icon.get(v['result'], '•')} {v['decision']}: {v['result']}")
            if v.get("risks", 0) > 0:
                lines.append(f"     {v['risks']} risks identified")
        if self.insights:
            lines.append("-" * 70)
            for ins in self.insights:
                lines.append(f"  • {ins}")
        if self.recommendations:
            lines.append("-" * 70)
            for r in self.recommendations:
                lines.append(f"  • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ArchitecturalReasoning:
    def __init__(self):
        self._decisions: List[ArchitecturalDecision] = []
        self._validations: List[DecisionValidation] = []
        self._known_patterns: Dict[str, List[str]] = {
            "microservices": ["decentralized data", "service discovery", "circuit breaker"],
            "monolith": ["shared database", "deployment coupling", "single codebase"],
            "event_driven": ["message broker", "event bus", "async processing"],
            "hexagonal": ["ports and adapters", "core domain", "infrastructure boundaries"],
            "cqrs": ["command model", "query model", "event store"],
        }

    def record_decision(self, decision_type: ArchitecturalDecisionType,
                        description: str, rationale: str,
                        alternatives: Optional[List[str]] = None,
                        constraints: Optional[List[str]] = None,
                        consequences: Optional[List[str]] = None) -> ArchitecturalDecision:
        decision = ArchitecturalDecision(
            decision_type=decision_type,
            description=description,
            rationale=rationale,
            alternatives=alternatives or [],
            constraints=constraints or [],
            consequences=consequences or [],
        )
        self._decisions.append(decision)
        return decision

    def validate(self, decision: ArchitecturalDecision) -> DecisionValidation:
        evidence: List[str] = []
        risks: List[str] = []

        desc_lower = decision.description.lower()
        rationale_lower = decision.rationale.lower()

        for pattern_name, characteristics in self._known_patterns.items():
            if pattern_name in desc_lower or pattern_name in rationale_lower:
                evidence.append(f"Decision relates to {pattern_name} pattern")
                for char in characteristics:
                    if char.lower() in desc_lower or char.lower() in rationale_lower:
                        evidence.append(f"Matches {pattern_name} characteristic: {char}")
                    else:
                        risks.append(f"Missing {pattern_name} characteristic: {char}")

        if decision.alternatives:
            evidence.append(f"Considered {len(decision.alternatives)} alternatives")
        else:
            risks.append("No alternatives considered — possible anchor bias")

        if not decision.constraints:
            risks.append("No constraints documented — decisions may be invalidated later")

        if len(decision.description) < 20:
            risks.append("Description too short — insufficient reasoning documentation")

        if risks:
            result = ValidationResult.FAIL if any(
                "Missing" in r or "No " in r for r in risks
            ) else ValidationResult.WARNING
        else:
            result = ValidationResult.PASS

        if result == ValidationResult.FAIL:
            recommendation = "Address risks before proceeding with this architecture decision"
        elif result == ValidationResult.WARNING:
            recommendation = "Review identified gaps in architectural reasoning"
        else:
            recommendation = "Architecture decision is well-reasoned"

        validation = DecisionValidation(
            decision=decision,
            result=result,
            evidence=evidence,
            risks_found=risks,
            recommendation=recommendation,
        )
        self._validations.append(validation)
        return validation

    def report(self) -> ArchitectureReasoningReport:
        if not self._decisions:
            return ArchitectureReasoningReport(
                total_decisions=0, passed=0, warnings=0, failed=0,
                validations=[], insights=[], recommendations=[
                    "Record architecture decisions to build reasoning transparency"
                ],
            )

        for d in self._decisions:
            if not any(v.decision == d for v in self._validations):
                self.validate(d)

        passed = sum(1 for v in self._validations if v.result == ValidationResult.PASS)
        warnings = sum(1 for v in self._validations if v.result == ValidationResult.WARNING)
        failed = sum(1 for v in self._validations if v.result == ValidationResult.FAIL)

        insights: List[str] = []
        if passed > failed:
            insights.append(f"Most decisions are well-reasoned ({passed}/{len(self._validations)} passed)")
        if failed > 0:
            insights.append(f"{failed} decisions failed validation — need revision")
        if not any(d.alternatives for d in self._decisions):
            insights.append("No alternatives documented — consider ADR (Architecture Decision Record) format")

        recommendations: List[str] = []
        if failed > 0:
            recommendations.append("Revise architecture decisions that failed validation")
        if not self._decisions:
            recommendations.append("Start documenting architecture decisions using ADR format")

        return ArchitectureReasoningReport(
            total_decisions=len(self._decisions),
            passed=passed,
            warnings=warnings,
            failed=failed,
            validations=[v.to_dict() for v in self._validations],
            insights=insights,
            recommendations=recommendations,
        )
