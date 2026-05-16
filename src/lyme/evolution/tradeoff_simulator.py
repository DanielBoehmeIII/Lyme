from __future__ import annotations

import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .fitness_refactoring import FitnessAssessor, FitnessAssessment, FitnessGuidedRefactorer


class TradeoffDomain(str, Enum):
    REFACTOR_TIMING = "refactor_timing"
    FRAMEWORK_STRATEGY = "framework_strategy"
    MODULE_STRATEGY = "module_strategy"
    TEST_STRATEGY = "test_strategy"
    MODEL_STRATEGY = "model_strategy"
    AUTOMATION_STRATEGY = "automation_strategy"


@dataclass
class TradeoffOption:
    label: str = ""
    description: str = ""
    estimated_cost: float = 0.0
    estimated_risk: float = 0.0
    future_burden: float = 0.0
    reversibility: float = 0.0
    time_horizon_months: int = 6
    assumptions: List[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "description": self.description[:100],
            "estimated_cost": round(self.estimated_cost, 3),
            "estimated_risk": round(self.estimated_risk, 3),
            "future_burden": round(self.future_burden, 3),
            "reversibility": round(self.reversibility, 3),
            "time_horizon_months": self.time_horizon_months,
            "assumptions": self.assumptions[:3],
            "confidence": round(self.confidence, 3),
            "composite_score": round(self.composite_score(), 3),
        }

    def composite_score(self) -> float:
        return (
            -self.estimated_cost * 0.3
            - self.estimated_risk * 0.25
            - self.future_burden * 0.2
            + self.reversibility * 0.15
            + self.confidence * 0.1
        )


@dataclass
class TradeoffAnalysis:
    analysis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    domain: TradeoffDomain = TradeoffDomain.REFACTOR_TIMING
    question: str = ""
    options: List[TradeoffOption] = field(default_factory=list)
    recommended: Optional[str] = None
    explanation: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "domain": self.domain.value,
            "question": self.question,
            "options": [o.to_dict() for o in self.options],
            "recommended": self.recommended,
            "explanation": self.explanation[:200],
        }


class TradeoffSimulator:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.fitness = FitnessAssessor(repo_path)
        self.analyses: List[TradeoffAnalysis] = []

    def compare(self, domain: TradeoffDomain, question: str, custom_options: Optional[List[Dict[str, Any]]] = None) -> TradeoffAnalysis:
        options = custom_options if custom_options else self._generate_default_options(domain)
        parsed_options = []
        for opt in options:
            if isinstance(opt, dict):
                parsed_options.append(TradeoffOption(**opt))
            elif isinstance(opt, TradeoffOption):
                parsed_options.append(opt)
            else:
                raise ValueError(f"Invalid option type: {type(opt)}")

        analysis = TradeoffAnalysis(
            domain=domain,
            question=question,
            options=parsed_options,
        )

        best = max(parsed_options, key=lambda o: o.composite_score())
        analysis.recommended = best.label
        analysis.explanation = self._generate_explanation(domain, best, parsed_options)

        self.analyses.append(analysis)
        return analysis

    def _generate_default_options(self, domain: TradeoffDomain) -> List[Dict[str, Any]]:
        defaults = {
            TradeoffDomain.REFACTOR_TIMING: [
                {
                    "label": "Refactor now",
                    "description": "Address architectural issues immediately before adding new features",
                    "estimated_cost": 0.7, "estimated_risk": 0.3, "future_burden": 0.1,
                    "reversibility": 0.6, "confidence": 0.7,
                    "assumptions": ["Team has capacity for refactoring", "Current features can wait"],
                },
                {
                    "label": "Refactor later",
                    "description": "Defer refactoring until after next feature milestone",
                    "estimated_cost": 0.2, "estimated_risk": 0.2, "future_burden": 0.7,
                    "reversibility": 0.8, "confidence": 0.5,
                    "assumptions": ["Technical debt won't block feature work", "Refactoring cost won't grow faster than expected"],
                },
            ],
            TradeoffDomain.FRAMEWORK_STRATEGY: [
                {
                    "label": "Upgrade framework now",
                    "description": "Upgrade to latest framework version with migration guide",
                    "estimated_cost": 0.6, "estimated_risk": 0.4, "future_burden": 0.2,
                    "reversibility": 0.3, "confidence": 0.6,
                    "assumptions": ["Migration guide covers all breaking changes", "Dependencies are compatible"],
                },
                {
                    "label": "Freeze current version",
                    "description": "Stay on current version, only apply security patches",
                    "estimated_cost": 0.1, "estimated_risk": 0.5, "future_burden": 0.8,
                    "reversibility": 0.9, "confidence": 0.7,
                    "assumptions": ["Security patches will be backported", "No feature requires new framework APIs"],
                },
            ],
            TradeoffDomain.MODULE_STRATEGY: [
                {
                    "label": "Split module",
                    "description": "Extract cohesive subsets into focused modules",
                    "estimated_cost": 0.5, "estimated_risk": 0.3, "future_burden": 0.2,
                    "reversibility": 0.5, "confidence": 0.65,
                    "assumptions": ["Module boundaries are well-understood", "Dependency graph supports clean split"],
                },
                {
                    "label": "Keep monolith",
                    "description": "Maintain single module with internal organization",
                    "estimated_cost": 0.1, "estimated_risk": 0.4, "future_burden": 0.7,
                    "reversibility": 0.8, "confidence": 0.6,
                    "assumptions": ["Team can manage single module complexity", "No scalability requirements"],
                },
            ],
            TradeoffDomain.TEST_STRATEGY: [
                {
                    "label": "Add tests before shipping feature",
                    "description": "Ensure test coverage meets threshold before feature release",
                    "estimated_cost": 0.5, "estimated_risk": 0.1, "future_burden": 0.1,
                    "reversibility": 0.9, "confidence": 0.8,
                    "assumptions": ["Test infrastructure is adequate", "Team has testing expertise"],
                },
                {
                    "label": "Ship feature, add tests later",
                    "description": "Prioritize feature delivery, defer test coverage",
                    "estimated_cost": 0.1, "estimated_risk": 0.6, "future_burden": 0.5,
                    "reversibility": 0.7, "confidence": 0.5,
                    "assumptions": ["Feature can be manually verified", "Test debt is manageable"],
                },
            ],
            TradeoffDomain.MODEL_STRATEGY: [
                {
                    "label": "Local model",
                    "description": "Run models locally for privacy and latency",
                    "estimated_cost": 0.6, "estimated_risk": 0.2, "future_burden": 0.3,
                    "reversibility": 0.7, "time_horizon_months": 12, "confidence": 0.6,
                    "assumptions": ["Local hardware is sufficient", "Model quality meets requirements"],
                },
                {
                    "label": "Frontier model API",
                    "description": "Use cloud API for best-in-class model capability",
                    "estimated_cost": 0.3, "estimated_risk": 0.4, "future_burden": 0.5,
                    "reversibility": 0.6, "time_horizon_months": 12, "confidence": 0.5,
                    "assumptions": ["API costs are sustainable", "Latency and privacy requirements are met"],
                },
            ],
            TradeoffDomain.AUTOMATION_STRATEGY: [
                {
                    "label": "Automate review",
                    "description": "Build automated review pipelines for code quality",
                    "estimated_cost": 0.5, "estimated_risk": 0.2, "future_burden": 0.1,
                    "reversibility": 0.8, "confidence": 0.7,
                    "assumptions": ["Review rules can be codified", "False positive rate is acceptable"],
                },
                {
                    "label": "Human review",
                    "description": "Maintain human code review process",
                    "estimated_cost": 0.3, "estimated_risk": 0.3, "future_burden": 0.5,
                    "reversibility": 0.9, "confidence": 0.8,
                    "assumptions": ["Team has review bandwidth", "Review quality is consistent"],
                },
            ],
        }
        return defaults.get(domain, defaults[TradeoffDomain.REFACTOR_TIMING])

    def _generate_explanation(self, domain: TradeoffDomain, best: TradeoffOption, all_options: List[TradeoffOption]) -> str:
        parts = [f"Recommended: {best.label}"]
        parts.append(f"Composite score: {best.composite_score():.3f}")
        parts.append("")
        parts.append(f"Cost: {best.estimated_cost:.2f}, Risk: {best.estimated_risk:.2f}")
        parts.append(f"Future burden: {best.future_burden:.2f}, Reversibility: {best.reversibility:.2f}")
        parts.append("")
        parts.append("Comparison:")
        for opt in all_options:
            marker = "→" if opt.label == best.label else " "
            parts.append(f"  {marker} {opt.label}: score={opt.composite_score():.3f} (cost={opt.estimated_cost:.2f}, risk={opt.estimated_risk:.2f}, burden={opt.future_burden:.2f})")
        parts.append("")
        if best.assumptions:
            parts.append("Key assumptions:")
            for a in best.assumptions:
                parts.append(f"  • {a}")
        return "\n".join(parts)

    def simulate_scenario(self, domain: TradeoffDomain, options: List[Dict[str, Any]]) -> TradeoffAnalysis:
        return self.compare(domain, f"Tradeoff analysis: {domain.value}", options)

    def batch_analyze(self) -> List[TradeoffAnalysis]:
        results = []
        for domain in TradeoffDomain:
            question = f"Should we {domain.value.replace('_', ' ')}?"
            analysis = self.compare(domain, question)
            results.append(analysis)
        return results

    def get_history(self) -> List[TradeoffAnalysis]:
        return list(self.analyses)
