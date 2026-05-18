"""ConfidenceScorer — scores edit quality and likelihood of success."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class EditConfidence:
    syntax_validity: float = 0.5
    import_validity: float = 0.5
    test_impact: float = 0.5
    scope_appropriateness: float = 0.5
    historical_success: float = 0.5
    overall: float = 0.5

    @property
    def level(self) -> ConfidenceLevel:
        if self.overall >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.overall >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.overall >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.overall >= 0.3:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 4),
            "level": self.level.value,
            "syntax_validity": round(self.syntax_validity, 4),
            "import_validity": round(self.import_validity, 4),
            "test_impact": round(self.test_impact, 4),
            "scope_appropriateness": round(self.scope_appropriateness, 4),
            "historical_success": round(self.historical_success, 4),
        }


class ConfidenceScorer:
    def score_edit(self, context: Dict[str, Any]) -> EditConfidence:
        conf = EditConfidence()

        # Syntax validity
        error = (context.get("error") or context.get("stderr") or "").lower()
        if any(kw in error for kw in ("syntaxerror", "invalid syntax")):
            conf.syntax_validity = 0.1
        elif any(kw in error for kw in ("warning", "deprecated")):
            conf.syntax_validity = 0.6
        else:
            conf.syntax_validity = 0.9

        # Import validity
        if any(kw in error for kw in ("importerror", "modulenotfound")):
            conf.import_validity = 0.1
        elif any(kw in error for kw in ("importerror", "modulenotfound")):
            conf.import_validity = 0.1
        else:
            conf.import_validity = 0.8

        # Test impact
        test_results = context.get("test_results", {})
        if isinstance(test_results, dict):
            failed = test_results.get("failed", 0) if isinstance(test_results.get("failed"), (int, float)) else 0
            total = test_results.get("total", 1) or 1
            if isinstance(total, (int, float)) and total > 0:
                conf.test_impact = 1.0 - (failed / total)

        # Scope appropriateness
        patches = context.get("patches", [])
        files_changed = len(patches) if isinstance(patches, list) else 0
        if files_changed == 0:
            conf.scope_appropriateness = 0.3
        elif files_changed <= 3:
            conf.scope_appropriateness = 0.8
        elif files_changed <= 10:
            conf.scope_appropriateness = 0.5
        else:
            conf.scope_appropriateness = 0.2

        # Historical success
        past_successes = context.get("past_successes", 0.5)
        conf.historical_success = min(1.0, max(0.0, float(past_successes)))

        # Overall
        conf.overall = (
            conf.syntax_validity * 0.25 +
            conf.import_validity * 0.15 +
            conf.test_impact * 0.30 +
            conf.scope_appropriateness * 0.15 +
            conf.historical_success * 0.15
        )

        return conf
