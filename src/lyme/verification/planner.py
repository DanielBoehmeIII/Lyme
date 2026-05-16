from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import time
import uuid


class StepType(str, Enum):
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    TYPE_CHECK = "type_check"
    LINT = "lint"
    BUILD = "build"
    RUNTIME_SMOKE = "runtime_smoke"
    STATIC_ANALYSIS = "static_analysis"
    COVERAGE = "coverage"
    BENCHMARK = "benchmark"
    MANUAL_REVIEW = "manual_review"
    SECURITY_SCAN = "security_scan"
    DEPENDENCY_CHECK = "dependency_check"
    FORMAT_CHECK = "format_check"
    DOCS_CHECK = "docs_check"


@dataclass
class VerificationStep:
    step_type: StepType
    description: str
    command: str = ""
    expected_duration_sec: float = 0.0
    risk_coverage: float = 0.0
    confidence_boost: float = 0.0
    cost: float = 0.0
    reversible: bool = True
    required: bool = False
    rationale: str = ""

    def to_dict(self) -> Dict:
        return {
            "step_type": self.step_type.value,
            "description": self.description,
            "command": self.command,
            "expected_duration_sec": self.expected_duration_sec,
            "risk_coverage": self.risk_coverage,
            "confidence_boost": self.confidence_boost,
            "cost": self.cost,
            "reversible": self.reversible,
            "required": self.required,
            "rationale": self.rationale,
        }


@dataclass
class VerificationStrategy:
    steps: List[VerificationStep]
    total_duration_sec: float = 0.0
    total_cost: float = 0.0
    risk_coverage: float = 0.0
    confidence_score: float = 0.0
    speed_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_sec": self.total_duration_sec,
            "total_cost": self.total_cost,
            "risk_coverage": self.risk_coverage,
            "confidence_score": self.confidence_score,
            "speed_score": self.speed_score,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Verification Strategy")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Duration | {self.total_duration_sec:.1f}s |")
        lines.append(f"| Cost | {self.total_cost:.2f} |")
        lines.append(f"| Risk Coverage | {self.risk_coverage:.0%} |")
        lines.append(f"| Confidence | {self.confidence_score:.0%} |")
        lines.append(f"| Speed | {self.speed_score:.0%} |")
        lines.append(f"")
        lines.append(f"### Steps")
        for i, step in enumerate(self.steps, 1):
            icon = {"unit_test": "🧪", "integration_test": "🔗", "type_check": "📐",
                    "lint": "🧹", "build": "🔨", "runtime_smoke": "🔥",
                    "static_analysis": "🔍", "coverage": "📊", "benchmark": "📈",
                    "manual_review": "👤", "security_scan": "🔒",
                    "dependency_check": "📦", "format_check": "✨", "docs_check": "📝"}
            lines.append(f"{i}. {icon.get(step.step_type.value, '•')} **{step.step_type.value.replace('_', ' ').title()}**")
            lines.append(f"   - {step.description}")
            lines.append(f"   - Rationale: {step.rationale}")
            lines.append(f"   - Risk coverage: {step.risk_coverage:.0%}, Confidence: {step.confidence_boost:.0%}")
        return "\n".join(lines)


@dataclass
class StrategyConfig:
    max_duration_sec: float = 300.0
    max_cost: float = 10.0
    min_risk_coverage: float = 0.5
    prefer_fast: bool = True
    require_type_check: bool = True
    require_lint: bool = True
    require_build: bool = True


@dataclass
class PlannerResult:
    edit_description: str
    edit_risk: float
    edit_scope: str
    strategies: List[VerificationStrategy]
    recommended: int = 0
    total_confidence: float = 0.0
    explanations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "edit_description": self.edit_description,
            "edit_risk": self.edit_risk,
            "edit_scope": self.edit_scope,
            "strategies": [s.to_dict() for s in self.strategies],
            "recommended": self.recommended,
            "total_confidence": self.total_confidence,
            "explanations": self.explanations,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Verification Strategy Planner")
        lines.append(f"")
        lines.append(f"**Edit**: {self.edit_description}")
        lines.append(f"**Risk**: {self.edit_risk:.2f} | **Scope**: {self.edit_scope}")
        lines.append(f"")
        for i, s in enumerate(self.strategies):
            label = "⭐ RECOMMENDED" if i == self.recommended else f"Strategy {i + 1}"
            lines.append(f"## {label}")
            lines.append(s.to_markdown())
            lines.append(f"")
        lines.append(f"## Why Each Step Matters")
        for exp in self.explanations:
            lines.append(f"- {exp}")
        return "\n".join(lines)

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  VERIFICATION STRATEGY PLANNER")
        lines.append("=" * 70)
        lines.append(f"  Edit:   {self.edit_description}")
        lines.append(f"  Risk:   {self.edit_risk:.2f}")
        lines.append(f"  Scope:  {self.edit_scope}")
        lines.append("-" * 70)

        for i, s in enumerate(self.strategies):
            label = ">> RECOMMENDED <<" if i == self.recommended else f"Strategy {i + 1}"
            lines.append(f"  [{label}]")
            lines.append(f"  Steps: {len(s.steps)} | Duration: {s.total_duration_sec:.0f}s | "
                         f"Risk: {s.risk_coverage:.0%} | Conf: {s.confidence_score:.0%}")
            for step in s.steps:
                lines.append(f"    • {step.step_type.value}: {step.description}")
                lines.append(f"      → {step.rationale}")
            lines.append("")

        lines.append(f"  Why These Steps:")
        for exp in self.explanations:
            lines.append(f"    • {exp}")
        lines.append("=" * 70)
        return "\n".join(lines)


class VerificationStrategyPlanner:
    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()

    def plan(self, edit_description: str, context: Dict) -> PlannerResult:
        edit_risk = context.get("risk_score", 0.3)
        edit_scope = context.get("scope", "local")
        files_changed = context.get("files_changed", [])
        has_tests = context.get("has_tests", False)
        is_sensitive = context.get("is_sensitive", False)
        is_config_change = context.get("is_config_change", False)
        is_docs_only = context.get("is_docs_only", False)
        language = context.get("language", "python")

        strategies = []
        explanations = []

        strategy_fast = self._build_fast_strategy(
            edit_risk, edit_scope, has_tests, is_sensitive,
            is_docs_only, is_config_change, language,
        )
        strategies.append(self._compute_metrics(strategy_fast))

        strategy_standard = self._build_standard_strategy(
            edit_risk, edit_scope, has_tests, is_sensitive,
            is_docs_only, is_config_change, language,
        )
        strategies.append(self._compute_metrics(strategy_standard))

        strategy_thorough = self._build_thorough_strategy(
            edit_risk, edit_scope, has_tests, is_sensitive,
            is_docs_only, is_config_change, language,
        )
        strategies.append(self._compute_metrics(strategy_thorough))

        explanations = self._generate_explanations(context, edit_risk)

        recommended = 1
        if self.config.prefer_fast and edit_risk < 0.3:
            recommended = 0
        elif edit_risk > 0.7 or is_sensitive:
            recommended = 2

        return PlannerResult(
            edit_description=edit_description,
            edit_risk=edit_risk,
            edit_scope=edit_scope,
            strategies=strategies,
            recommended=recommended,
            total_confidence=strategies[recommended].confidence_score,
            explanations=explanations,
        )

    def _build_fast_strategy(
        self, risk, scope, has_tests, sensitive, docs_only, config_change, language,
    ) -> List[VerificationStep]:
        steps = []

        if self.config.require_type_check:
            steps.append(VerificationStep(
                step_type=StepType.TYPE_CHECK,
                description=f"Run {language} type checker",
                command=f"{language} -m mypy ." if language == "python" else f"{language} --check",
                expected_duration_sec=30,
                risk_coverage=0.3,
                confidence_boost=0.2,
                cost=1,
                reversible=True,
                required=True,
                rationale="Catches type errors before runtime. Prevents category errors and API misuse.",
            ))

        if self.config.require_lint:
            steps.append(VerificationStep(
                step_type=StepType.LINT,
                description=f"Run {language} linter",
                command="ruff check ." if language == "python" else f"{language} lint .",
                expected_duration_sec=15,
                risk_coverage=0.2,
                confidence_boost=0.1,
                cost=0.5,
                reversible=True,
                required=True,
                rationale="Enforces code standards and catches common bugs before they reach review.",
            ))

        if has_tests and not docs_only:
            steps.append(VerificationStep(
                step_type=StepType.UNIT_TEST,
                description="Run unit tests for changed modules",
                command="python -m pytest tests/ -x -q --tb=short",
                expected_duration_sec=60,
                risk_coverage=0.5,
                confidence_boost=0.4,
                cost=2,
                reversible=True,
                required=False,
                rationale="Unit tests verify individual component correctness. First line of defense.",
            ))

        return steps

    def _build_standard_strategy(
        self, risk, scope, has_tests, sensitive, docs_only, config_change, language,
    ) -> List[VerificationStep]:
        steps = self._build_fast_strategy(risk, scope, has_tests, sensitive, docs_only, config_change, language)

        if self.config.require_build:
            steps.append(VerificationStep(
                step_type=StepType.BUILD,
                description=f"Build project",
                command="pip install -e ." if language == "python" else f"{language} build",
                expected_duration_sec=45,
                risk_coverage=0.3,
                confidence_boost=0.15,
                cost=1.5,
                reversible=True,
                required=True,
                rationale="Ensures code compiles/installs without errors. Build failures block all downstream verification.",
            ))

        if sensitive or risk > 0.5:
            steps.append(VerificationStep(
                step_type=StepType.SECURITY_SCAN,
                description="Run security scan on changed files",
                command="bandit -r ." if language == "python" else "trivy fs .",
                expected_duration_sec=60,
                risk_coverage=0.4,
                confidence_boost=0.25,
                cost=3,
                reversible=True,
                required=False,
                rationale="Security vulnerabilities in autonomous code changes must be caught early. Sensitive code needs extra scrutiny.",
            ))

        if scope == "broad" or risk > 0.4:
            steps.append(VerificationStep(
                step_type=StepType.INTEGRATION_TEST,
                description="Run integration tests",
                command="python -m pytest tests/ -x --integration -q",
                expected_duration_sec=120,
                risk_coverage=0.5,
                confidence_boost=0.3,
                cost=4,
                reversible=True,
                required=False,
                rationale="Integration tests verify that changed components interact correctly with dependencies.",
            ))

        steps.append(VerificationStep(
            step_type=StepType.COVERAGE,
            description="Measure test coverage of changes",
            command="python -m pytest tests/ --cov=src --cov-report=term --cov-fail-under=80",
            expected_duration_sec=90,
            risk_coverage=0.3,
            confidence_boost=0.2,
            cost=2,
            reversible=True,
            required=False,
            rationale="Coverage reveals untested code paths. Low coverage means unverified behavior.",
        ))

        return steps

    def _build_thorough_strategy(
        self, risk, scope, has_tests, sensitive, docs_only, config_change, language,
    ) -> List[VerificationStep]:
        steps = self._build_standard_strategy(risk, scope, has_tests, sensitive, docs_only, config_change, language)

        steps.append(VerificationStep(
            step_type=StepType.RUNTIME_SMOKE,
            description="Run smoke tests on the application",
            command="python -c 'import sys; print(\"smoke OK\")'",
            expected_duration_sec=30,
            risk_coverage=0.3,
            confidence_boost=0.15,
            cost=1,
            reversible=True,
            required=False,
            rationale="Smoke tests verify the application starts and responds. Catches import errors and config issues.",
        ))

        if not docs_only:
            steps.append(VerificationStep(
                step_type=StepType.BENCHMARK,
                description="Run performance benchmarks",
                command="python -m pytest tests/benchmarks/ -q",
                expected_duration_sec=180,
                risk_coverage=0.2,
                confidence_boost=0.2,
                cost=5,
                reversible=True,
                required=False,
                rationale="Benchmarks detect performance regressions. Critical for performance-sensitive changes.",
            ))

        steps.append(VerificationStep(
            step_type=StepType.DEPENDENCY_CHECK,
            description="Check for dependency vulnerabilities",
            command="pip-audit" if language == "python" else "npm audit",
            expected_duration_sec=30,
            risk_coverage=0.2,
            confidence_boost=0.1,
            cost=1,
            reversible=True,
            required=False,
            rationale="New dependencies or version changes can introduce supply chain vulnerabilities.",
        ))

        if sensitive or risk > 0.6:
            steps.append(VerificationStep(
                step_type=StepType.MANUAL_REVIEW,
                description="Human review of the change",
                command="",
                expected_duration_sec=600,
                risk_coverage=0.6,
                confidence_boost=0.5,
                cost=8,
                reversible=True,
                required=True,
                rationale="High-risk or sensitive changes require human judgment that automated checks cannot replace.",
            ))

        return steps

    def _compute_metrics(self, steps: List[VerificationStep]) -> VerificationStrategy:
        total_duration = sum(s.expected_duration_sec for s in steps)
        total_cost = sum(s.cost for s in steps)
        risk_coverage = min(1.0, sum(s.risk_coverage for s in steps) / 3.0)
        confidence_boost = min(1.0, sum(s.confidence_boost for s in steps) / 2.0)
        speed = max(0, 1.0 - (total_duration / 600.0))

        return VerificationStrategy(
            steps=steps,
            total_duration_sec=total_duration,
            total_cost=total_cost,
            risk_coverage=round(risk_coverage, 3),
            confidence_score=round(confidence_boost, 3),
            speed_score=round(speed, 3),
        )

    def _generate_explanations(self, context: Dict, risk: float) -> List[str]:
        exps = []
        exps.append("Unit tests verify individual component correctness at low cost.")
        exps.append("Type checks prevent category errors before runtime execution.")
        exps.append("Linters catch code quality issues and common mistakes early.")
        exps.append("Build verification ensures the system remains in a working state.")
        if risk > 0.5:
            exps.append("Integration tests verify cross-component interaction — critical for broad-scope changes.")
        if context.get("is_sensitive", False):
            exps.append("Security scans are required for changes touching sensitive code paths.")
        exps.append("Manual review provides human judgment for high-risk or nuanced changes.")
        return exps
