from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import uuid
import time


class ReviewRole(str, Enum):
    PROPOSER = "proposer"
    SECURITY_CRITIC = "security_critic"
    ARCHITECTURE_CRITIC = "architecture_critic"
    TEST_CRITIC = "test_critic"
    ROLLBACK_CRITIC = "rollback_critic"
    HUMAN_APPROVER = "human_approver"


class ReviewVerdict(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    REQUIRE_HUMAN = "require_human"


@dataclass
class ReviewCritique:
    role: ReviewRole
    verdict: ReviewVerdict
    reasoning: str
    concerns: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.8
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "role": self.role.value,
            "verdict": self.verdict.value,
            "reasoning": self.reasoning,
            "concerns": self.concerns,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ReviewRequest:
    id: str
    title: str
    description: str
    action_type: str
    files_changed: List[str]
    diff_summary: str
    risk_score: float
    proposer_notes: str = ""
    context: Dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "files_changed": self.files_changed,
            "diff_summary": self.diff_summary,
            "risk_score": self.risk_score,
            "proposer_notes": self.proposer_notes,
            "context": self.context,
            "timestamp": self.timestamp,
        }


@dataclass
class BoardDecision:
    final_verdict: ReviewVerdict
    critiques: Dict[ReviewRole, ReviewCritique]
    majority: str
    human_required: bool
    reasoning: str
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "final_verdict": self.final_verdict.value,
            "critiques": {k.value: v.to_dict() for k, v in self.critiques.items()},
            "majority": self.majority,
            "human_required": self.human_required,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        lines = []
        decision_icon = {
            ReviewVerdict.APPROVE: "✅", ReviewVerdict.REJECT: "❌",
            ReviewVerdict.REVISE: "🔄", ReviewVerdict.REQUIRE_HUMAN: "👤",
        }
        lines.append(f"# Action Review Board Decision")
        lines.append(f"")
        lines.append(f"**Final Verdict**: {decision_icon.get(self.final_verdict, '❓')} {self.final_verdict.value.upper()}")
        lines.append(f"**Majority**: {self.majority}")
        lines.append(f"**Human Required**: {self.human_required}")
        lines.append(f"")
        lines.append(f"## Critiques")
        for role, critique in self.critiques.items():
            v_icon = {ReviewVerdict.APPROVE: "✅", ReviewVerdict.REJECT: "❌",
                      ReviewVerdict.REVISE: "🔄", ReviewVerdict.REQUIRE_HUMAN: "👤"}
            lines.append(f"### {v_icon.get(critique.verdict, '❓')} {role.value.replace('_', ' ').title()}")
            lines.append(f"{critique.reasoning}")
            if critique.concerns:
                for c in critique.concerns:
                    lines.append(f"  - ⚠ {c}")
            if critique.suggestions:
                for s in critique.suggestions:
                    lines.append(f"  - 💡 {s}")
            lines.append(f"")
        lines.append(f"## Reasoning")
        lines.append(self.reasoning)
        return "\n".join(lines)


class ActionReviewBoard:
    def __init__(self):
        self._history: List[BoardDecision] = []

    def submit_request(self, request: ReviewRequest) -> BoardDecision:
        critiques: Dict[ReviewRole, ReviewCritique] = {}

        proposer = self._proposer_review(request)
        security = self._security_review(request)
        architecture = self._architecture_review(request)
        test_review = self._test_review(request)
        rollback = self._rollback_review(request)

        critiques[ReviewRole.PROPOSER] = proposer
        critiques[ReviewRole.SECURITY_CRITIC] = security
        critiques[ReviewRole.ARCHITECTURE_CRITIC] = architecture
        critiques[ReviewRole.TEST_CRITIC] = test_review
        critiques[ReviewRole.ROLLBACK_CRITIC] = rollback

        verdict_counts: Dict[ReviewVerdict, int] = {}
        for critique in critiques.values():
            verdict_counts[critique.verdict] = verdict_counts.get(critique.verdict, 0) + 1

        approve = verdict_counts.get(ReviewVerdict.APPROVE, 0)
        reject = verdict_counts.get(ReviewVerdict.REJECT, 0)
        revise = verdict_counts.get(ReviewVerdict.REVISE, 0)
        require_human = verdict_counts.get(ReviewVerdict.REQUIRE_HUMAN, 0)

        total = len(critiques)
        majority = "approve" if approve > total / 2 else "reject" if reject > total / 2 else "mixed"

        if require_human >= 2 or request.risk_score > 0.8:
            final_verdict = ReviewVerdict.REQUIRE_HUMAN
        elif reject >= 3:
            final_verdict = ReviewVerdict.REJECT
        elif revise >= 3:
            final_verdict = ReviewVerdict.REVISE
        elif approve >= 3:
            final_verdict = ReviewVerdict.APPROVE
        else:
            final_verdict = ReviewVerdict.REQUIRE_HUMAN

        reasoning = self._build_reasoning(final_verdict, critiques)

        decision = BoardDecision(
            final_verdict=final_verdict,
            critiques=critiques,
            majority=majority,
            human_required=final_verdict == ReviewVerdict.REQUIRE_HUMAN,
            reasoning=reasoning,
            timestamp=time.time(),
        )
        self._history.append(decision)
        return decision

    def _proposer_review(self, request: ReviewRequest) -> ReviewCritique:
        concerns = []
        suggestions = []

        if not request.proposer_notes:
            concerns.append("No proposer notes provided - unclear rationale")
        if request.risk_score > 0.7:
            concerns.append(f"High risk score ({request.risk_score:.2f}) - proceed with caution")
        if len(request.files_changed) > 10:
            concerns.append(f"Large change set ({len(request.files_changed)} files) - consider splitting")

        suggestions.append("Ensure all edge cases are documented")
        if request.diff_summary:
            suggestions.append("Include test plan for changes")

        risk = request.risk_score
        if risk < 0.3:
            verdict = ReviewVerdict.APPROVE
        elif risk < 0.6:
            verdict = ReviewVerdict.REVISE
        else:
            verdict = ReviewVerdict.REQUIRE_HUMAN

        return ReviewCritique(
            role=ReviewRole.PROPOSER, verdict=verdict,
            reasoning=f"Proposer assessment based on risk {risk:.2f} and {len(request.files_changed)} files changed",
            concerns=concerns, suggestions=suggestions, confidence=0.85,
        )

    def _security_review(self, request: ReviewRequest) -> ReviewCritique:
        concerns = []
        suggestions = []
        security_keywords = [
            "auth", "password", "token", "secret", "key", "credential",
            "sql", "injection", "xss", "csrf", "encrypt", "decrypt",
            "ssl", "tls", "certificate", "permission", "role",
        ]

        security_hit = 0
        for kw in security_keywords:
            if kw in request.diff_summary.lower() or any(kw in f.lower() for f in request.files_changed):
                security_hit += 1

        for f in request.files_changed:
            if any(kw in f.lower() for kw in ["auth", "secret", "password", "key", "token"]):
                concerns.append(f"Security-sensitive file: {f}")
            if any(kw in f.lower() for kw in ["payment", "billing", "checkout"]):
                concerns.append(f"Financial logic in: {f}")

        if security_hit >= 2:
            concerns.append("Multiple security-related keywords in change set")
        if request.risk_score > 0.5:
            concerns.append("Risk score exceeds security threshold")

        suggestions.append("Run security-focused static analysis")
        suggestions.append("Verify input validation for all new endpoints")

        if concerns:
            verdict = ReviewVerdict.REVISE if len(concerns) <= 2 else ReviewVerdict.REJECT
        else:
            verdict = ReviewVerdict.APPROVE

        return ReviewCritique(
            role=ReviewRole.SECURITY_CRITIC, verdict=verdict,
            reasoning=f"Security review found {len(concerns)} concern(s) across {security_hit} security-related patterns",
            concerns=concerns, suggestions=suggestions, confidence=0.80,
        )

    def _architecture_review(self, request: ReviewRequest) -> ReviewCritique:
        concerns = []
        suggestions = []

        arch_patterns = {
            "circular": "circular dependency", "god": "god class/object",
            "coupling": "high coupling", "leak": "abstraction leak",
            "bypass": "layer bypass", "singleton": "global state",
        }

        for pattern, desc in arch_patterns.items():
            if pattern in request.diff_summary.lower():
                concerns.append(f"Potential {desc} detected")

        for f in request.files_changed:
            parts = Path(f).parts
            if len(parts) > 5:
                concerns.append(f"Deeply nested file path: {f}")

        if request.files_changed:
            dirs = set(Path(f).parent for f in request.files_changed)
            if len(dirs) > 5:
                concerns.append(f"Change spans {len(dirs)} directories - possible architectural boundary violation")

        suggestions.append("Verify change aligns with established architectural patterns")
        suggestions.append("Check for implicit coupling with unchanged modules")

        if len(concerns) > 2:
            verdict = ReviewVerdict.REJECT
        elif concerns:
            verdict = ReviewVerdict.REVISE
        else:
            verdict = ReviewVerdict.APPROVE

        return ReviewCritique(
            role=ReviewRole.ARCHITECTURE_CRITIC, verdict=verdict,
            reasoning=f"Architecture review: {len(concerns)} concern(s), {len(request.files_changed)} files across {len(set(Path(f).parent for f in request.files_changed))} directories",
            concerns=concerns, suggestions=suggestions, confidence=0.75,
        )

    def _test_review(self, request: ReviewRequest) -> ReviewCritique:
        concerns = []
        suggestions = []

        has_tests = any("test" in f.lower() or "spec" in f.lower() or "__test" in f.lower() for f in request.files_changed)
        test_files_in_change = [f for f in request.files_changed if "test" in f.lower()]

        source_without_test = [f for f in request.files_changed if "test" not in f.lower() and f.endswith((".py", ".ts", ".js", ".rs", ".go", ".java"))]

        if source_without_test and not has_tests:
            concerns.append(f"Source changes ({len(source_without_test)} files) without corresponding test changes")
        if source_without_test and not test_files_in_change:
            suggestions.append("Add unit tests for new/modified functionality")

        test_coverage = len(test_files_in_change) / max(len(source_without_test + test_files_in_change), 1)
        if test_coverage < 0.3 and source_without_test:
            concerns.append(f"Low test coverage ratio ({test_coverage:.0%})")

        suggestions.append("Ensure all error paths are tested")
        suggestions.append("Verify edge cases in modified logic")

        if not concerns:
            if has_tests:
                verdict = ReviewVerdict.APPROVE
            else:
                verdict = ReviewVerdict.APPROVE
        elif len(concerns) == 1:
            verdict = ReviewVerdict.REVISE
        else:
            verdict = ReviewVerdict.REVISE

        return ReviewCritique(
            role=ReviewRole.TEST_CRITIC, verdict=verdict,
            reasoning=f"Test review: {len(test_files_in_change)} test files, {len(source_without_test)} source files ({test_coverage:.0%} coverage ratio)",
            concerns=concerns, suggestions=suggestions, confidence=0.80,
        )

    def _rollback_review(self, request: ReviewRequest) -> ReviewCritique:
        concerns = []
        suggestions = []

        destructive_keywords = ["delete", "remove", "drop", "truncate", "override", "replace"]
        for kw in destructive_keywords:
            if kw in request.diff_summary.lower():
                concerns.append(f"Destructive operation detected: {kw}")

        if request.files_changed:
            sensitive_dirs = ["migrations", "deploy", "scripts", "ci"]
            for d in sensitive_dirs:
                matching = [f for f in request.files_changed if d in Path(f).parts]
                if matching:
                    concerns.append(f"Changes in {d}/ directory - rollback may be non-trivial")

        if len(request.files_changed) > 15:
            concerns.append(f"Large change ({len(request.files_changed)} files) makes rollback complex")

        suggestions.append("Verify git state before applying change")
        suggestions.append("Create backup point before modification")
        suggestions.append("Test rollback procedure on staging first")

        rollback_concern = len(concerns)
        if rollback_concern > 2:
            verdict = ReviewVerdict.REJECT
        elif rollback_concern > 0:
            verdict = ReviewVerdict.REVISE
        else:
            verdict = ReviewVerdict.APPROVE

        return ReviewCritique(
            role=ReviewRole.ROLLBACK_CRITIC, verdict=verdict,
            reasoning=f"Rollback review: {rollback_concern} concern(s) about reversibility",
            concerns=concerns, suggestions=suggestions, confidence=0.75,
        )

    def _build_reasoning(self, verdict: ReviewVerdict, critiques: Dict[ReviewRole, ReviewCritique]) -> str:
        if verdict == ReviewVerdict.APPROVE:
            approvers = [r.value for r, c in critiques.items() if c.verdict == ReviewVerdict.APPROVE]
            return f"Approved by {len(approvers)}/{len(critiques)} reviewers: {', '.join(a.replace('_', ' ').title() for a in approvers)}"
        elif verdict == ReviewVerdict.REJECT:
            rejectors = [r.value for r, c in critiques.items() if c.verdict == ReviewVerdict.REJECT]
            concerns = []
            for c in critiques.values():
                concerns.extend(c.concerns)
            return f"Rejected by {len(rejectors)}/{len(critiques)} reviewers. Concerns: {'; '.join(concerns[:5])}"
        elif verdict == ReviewVerdict.REVISE:
            revisers = [r.value for r, c in critiques.items() if c.verdict == ReviewVerdict.REVISE]
            suggestions = []
            for c in critiques.values():
                suggestions.extend(c.suggestions[:2])
            return f"Revision requested by {len(revisers)}/{len(critiques)} reviewers. Suggestions: {'; '.join(suggestions[:5])}"
        else:
            return f"Human approval required due to risk profile or dissenting opinions"

    def get_history(self) -> List[BoardDecision]:
        return self._history

    def summary(self) -> str:
        lines = []
        lines.append(f"# Action Review Board History")
        lines.append(f"")
        lines.append(f"Total Reviews: {len(self._history)}")
        approved = sum(1 for d in self._history if d.final_verdict == ReviewVerdict.APPROVE)
        rejected = sum(1 for d in self._history if d.final_verdict == ReviewVerdict.REJECT)
        revised = sum(1 for d in self._history if d.final_verdict == ReviewVerdict.REVISE)
        human = sum(1 for d in self._history if d.final_verdict == ReviewVerdict.REQUIRE_HUMAN)
        lines.append(f"- Approved: {approved}")
        lines.append(f"- Rejected: {rejected}")
        lines.append(f"- Revision: {revised}")
        lines.append(f"- Human Required: {human}")
        return "\n".join(lines)
