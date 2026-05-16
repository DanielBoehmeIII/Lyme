"""Week 102 — Local Reward Model / Critic.

A local reward model or critic that scores:
- plan quality
- evidence grounding
- patch safety
- verification completeness
- hallucination risk
- edit minimality
- likely test success
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import time
import re


@dataclass
class RewardScore:
    plan_quality: float = 0.0
    evidence_grounding: float = 0.0
    patch_safety: float = 0.0
    verification_completeness: float = 0.0
    hallucination_risk: float = 0.0
    edit_minimality: float = 0.0
    likely_test_success: float = 0.0
    overall: float = 0.0
    latency_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan_quality": round(self.plan_quality, 4),
            "evidence_grounding": round(self.evidence_grounding, 4),
            "patch_safety": round(self.patch_safety, 4),
            "verification_completeness": round(self.verification_completeness, 4),
            "hallucination_risk": round(self.hallucination_risk, 4),
            "edit_minimality": round(self.edit_minimality, 4),
            "likely_test_success": round(self.likely_test_success, 4),
            "overall": round(self.overall, 4),
            "latency_ms": round(self.latency_ms, 1),
            "warnings": self.warnings[:5],
        }


class LocalRewardModel:
    """Scores patches and plans across 7 dimensions.

    Hybrid: rules + pattern matching + (future) trained classifier.
    """

    WEIGHTS = {
        "plan_quality": 0.20,
        "evidence_grounding": 0.15,
        "patch_safety": 0.20,
        "verification_completeness": 0.15,
        "hallucination_risk": 0.10,
        "edit_minimality": 0.10,
        "likely_test_success": 0.10,
    }

    SAFE_PATTERNS = [
        r"raise\s+\w+Error", r"try:", r"except", r"if.*is None",
        r"if.*not", r"validate", r"check", r"assert",
        r"logger\.", r"logging\.", r"warnings\.", r"deprecated",
    ]

    RISK_PATTERNS = [
        r"exec\(", r"eval\(", r"__import__\(", r"subprocess\.",
        r"os\.system", r"pickle\.loads", r"rm\s+-rf",
        r"DELETE\s+FROM", r"DROP\s+TABLE",
        r"password\s*=", r"secret_key\s*=",
    ]

    HALLUCINATION_PATTERNS = [
        r"from\s+\w+\s+import\s+\w+",  # Check if import is realistic
    ]

    def score_patch(self, patch: str, context: Optional[dict] = None) -> RewardScore:
        ctx = context or {}
        start = time.time()

        score = RewardScore(
            plan_quality=self._score_plan_quality(patch, ctx),
            evidence_grounding=self._score_evidence_grounding(patch, ctx),
            patch_safety=self._score_patch_safety(patch),
            verification_completeness=self._score_verification(patch, ctx),
            hallucination_risk=self._score_hallucination_risk(patch, ctx),
            edit_minimality=self._score_edit_minimality(patch),
            likely_test_success=self._score_test_success(patch, ctx),
        )

        score.overall = sum(
            getattr(score, dim) * weight
            for dim, weight in self.WEIGHTS.items()
        )

        # Collect warnings
        if score.patch_safety < 0.5:
            score.warnings.append("Low safety score — review for security issues")
        if score.hallucination_risk > 0.5:
            score.warnings.append("High hallucination risk — verify symbol existence")
        if score.verification_completeness < 0.3:
            score.warnings.append("Low verification completeness — add test coverage")
        if score.edit_minimality < 0.3:
            score.warnings.append("Overbroad change — consider splitting")

        score.latency_ms = (time.time() - start) * 1000
        return score

    def _score_plan_quality(self, patch: str, ctx: dict) -> float:
        if not patch:
            return 0.0
        score = 0.5
        if any(p in patch for p in ["Affected:", "File:", "Risk:"]):
            score += 0.2
        if any(p in patch for p in ["step", "first", "then", "finally"]):
            score += 0.15
        if any(p in patch for p in ["verify", "test", "check"]):
            score += 0.15
        return min(score, 1.0)

    def _score_evidence_grounding(self, patch: str, ctx: dict) -> float:
        known_symbols = set(ctx.get("known_symbols", []))
        file_refs = set(ctx.get("file_refs", []))
        if not patch:
            return 0.0
        score = 0.5
        symbols_in_patch = set(re.findall(r'\b([a-z_][a-z_0-9]*)\s*\(', patch))
        if symbols_in_patch and known_symbols:
            match = len(symbols_in_patch & known_symbols) / max(len(symbols_in_patch), 1)
            score += match * 0.3
        for f in file_refs:
            if f in patch:
                score += 0.1
        return min(score, 1.0)

    def _score_patch_safety(self, patch: str) -> float:
        if not patch:
            return 0.5
        score = 0.7
        for safe in self.SAFE_PATTERNS:
            if re.search(safe, patch):
                score += 0.05
        for risk in self.RISK_PATTERNS:
            if re.search(risk, patch):
                score -= 0.2
        return max(0.0, min(score, 1.0))

    def _score_verification(self, patch: str, ctx: dict) -> float:
        score = 0.3
        verify_cmds = ctx.get("verification_commands", [])
        if verify_cmds:
            score += 0.3
        if any(v in patch for v in ["pytest", "tests", "coverage"]):
            score += 0.2
        if "verify" in ctx or "verify" in patch:
            score += 0.2
        return min(score, 1.0)

    def _score_hallucination_risk(self, patch: str, ctx: dict) -> float:
        if not patch:
            return 0.5
        risk = 0.2
        known = set(ctx.get("known_symbols", []))
        builtins = {"if", "for", "while", "def", "class", "return", "print",
                    "len", "range", "int", "str", "list", "dict", "set", "True",
                    "False", "None", "Exception", "ValueError", "TypeError"}
        symbols = set(re.findall(r'\b([a-z_][a-z_0-9]*)\s*\(', patch))
        unknown = symbols - known - builtins
        if unknown and known:
            risk += len(unknown) / max(len(symbols), 1) * 0.5
        return min(risk, 1.0)

    def _score_edit_minimality(self, patch: str) -> float:
        if not patch:
            return 0.0
        added = len(re.findall(r'^\+[^+]', patch, re.MULTILINE))
        removed = len(re.findall(r'^-[^-]', patch, re.MULTILINE))
        total = added + removed
        if total == 0:
            return 0.5
        if total <= 3:
            return 0.9
        if total <= 10:
            return 0.7
        if total <= 30:
            return 0.4
        return 0.1

    def _score_test_success(self, patch: str, ctx: dict) -> float:
        score = 0.5
        if "test" in patch or any("test" in str(v) for v in ctx.values()):
            score += 0.2
        if ctx.get("tests_passed") is not None:
            passed = ctx.get("tests_passed", 0)
            total = ctx.get("total_tests", 1)
            score += (passed / max(total, 1)) * 0.3
        return min(score, 1.0)

    def evaluate_dataset(self, pairs: List[tuple]) -> Dict:
        results = []
        for patch, ctx in pairs:
            score = self.score_patch(patch, ctx)
            results.append(score)
        avg = {
            dim: sum(getattr(r, dim) for r in results) / max(len(results), 1)
            for dim in self.WEIGHTS
        }
        avg["overall"] = sum(getattr(r, "overall") for r in results) / max(len(results), 1)
        avg["total_evaluated"] = len(results)
        avg["total_warnings"] = sum(len(r.warnings) for r in results)
        return avg
