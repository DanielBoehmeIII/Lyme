from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from pathlib import Path
from enum import Enum
import json
import time
import uuid


class ChangeRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeScope(str, Enum):
    LOCAL = "local"
    MODULE = "module"
    BROAD = "broad"
    CROSS_REPO = "cross_repo"


class ChangeReversibility(str, Enum):
    EASY = "easy"
    MODERATE = "moderate"
    DIFFICULT = "difficult"
    IRREVERSIBLE = "irreversible"


class GovernanceDecision(str, Enum):
    AUTO_APPLY = "auto_apply"
    PATCH_ONLY = "patch_only"
    REQUIRE_REVIEW = "require_review"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


@dataclass
class ChangeClassification:
    risk: ChangeRisk
    risk_score: float
    scope: ChangeScope
    reversibility: ChangeReversibility
    sensitivity: str
    verification_coverage: float
    user_intent: str
    deployment_impact: str
    architectural_impact: str
    files_changed: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "risk": self.risk.value,
            "risk_score": self.risk_score,
            "scope": self.scope.value,
            "reversibility": self.reversibility.value,
            "sensitivity": self.sensitivity,
            "verification_coverage": self.verification_coverage,
            "user_intent": self.user_intent,
            "deployment_impact": self.deployment_impact,
            "architectural_impact": self.architectural_impact,
            "files_changed": self.files_changed,
            "description": self.description,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Change Classification")
        lines.append(f"")
        lines.append(f"| Dimension | Value |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| Risk | {self.risk.value.upper()} ({self.risk_score:.2f}) |")
        lines.append(f"| Scope | {self.scope.value} |")
        lines.append(f"| Reversibility | {self.reversibility.value} |")
        lines.append(f"| Sensitivity | {self.sensitivity} |")
        lines.append(f"| Verification Coverage | {self.verification_coverage:.0%} |")
        lines.append(f"| User Intent | {self.user_intent} |")
        lines.append(f"| Deployment Impact | {self.deployment_impact} |")
        lines.append(f"| Architectural Impact | {self.architectural_impact} |")
        lines.append(f"| Files Changed | {len(self.files_changed)} |")
        return "\n".join(lines)


@dataclass
class GovernancePolicy:
    id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    decision: GovernanceDecision
    priority: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "decision": self.decision.value,
            "priority": self.priority,
        }


@dataclass
class GovernanceResult:
    classification: ChangeClassification
    decision: GovernanceDecision
    matching_policy: Optional[str] = None
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)
    suggested_remediation: List[str] = field(default_factory=list)
    override_available: bool = False

    def to_dict(self) -> Dict:
        return {
            "classification": self.classification.to_dict(),
            "decision": self.decision.value,
            "matching_policy": self.matching_policy,
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "required_approvals": self.required_approvals,
            "suggested_remediation": self.suggested_remediation,
            "override_available": self.override_available,
        }

    def to_markdown(self) -> str:
        icons = {
            GovernanceDecision.AUTO_APPLY: "✅",
            GovernanceDecision.PATCH_ONLY: "📝",
            GovernanceDecision.REQUIRE_REVIEW: "👀",
            GovernanceDecision.REQUIRE_APPROVAL: "👤",
            GovernanceDecision.BLOCK: "🚫",
        }
        lines = []
        lines.append(f"# Governance Decision")
        lines.append(f"")
        lines.append(f"**{icons.get(self.decision, '❓')} Decision**: {self.decision.value.upper()}")
        lines.append(f"")
        if self.matching_policy:
            lines.append(f"**Matched Policy**: {self.matching_policy}")
        lines.append(f"")
        lines.append(self.classification.to_markdown())
        lines.append(f"")
        if self.reasoning:
            lines.append(f"## Reasoning")
            for r in self.reasoning:
                lines.append(f"- {r}")
            lines.append(f"")
        if self.warnings:
            lines.append(f"## Warnings")
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")
            lines.append(f"")
        if self.required_approvals:
            lines.append(f"## Required Approvals")
            for a in self.required_approvals:
                lines.append(f"- {a}")
            lines.append(f"")
        if self.suggested_remediation:
            lines.append(f"## Suggested Remediation")
            for s in self.suggested_remediation:
                lines.append(f"- 💡 {s}")
            lines.append(f"")
        if self.override_available:
            lines.append(f"**Override available**: Use --force to override this decision")
        return "\n".join(lines)

    def render_cli(self) -> str:
        icons = {
            GovernanceDecision.AUTO_APPLY: "✅",
            GovernanceDecision.PATCH_ONLY: "📝",
            GovernanceDecision.REQUIRE_REVIEW: "👀",
            GovernanceDecision.REQUIRE_APPROVAL: "👤",
            GovernanceDecision.BLOCK: "🚫",
        }
        lines = []
        lines.append("=" * 70)
        lines.append(f"  CHANGE GOVERNANCE ENGINE")
        lines.append("=" * 70)
        lines.append(f"  Decision: {icons.get(self.decision, '•')} {self.decision.value.upper()}")
        if self.matching_policy:
            lines.append(f"  Policy:   {self.matching_policy}")
        lines.append(f"  Risk:     {self.classification.risk.value.upper()} ({self.classification.risk_score:.2f})")
        lines.append(f"  Scope:    {self.classification.scope.value}")
        lines.append(f"  Reversible: {self.classification.reversibility.value}")
        lines.append("-" * 70)
        if self.reasoning:
            lines.append("  Reasoning:")
            for r in self.reasoning:
                lines.append(f"    • {r}")
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings:
                lines.append(f"    ⚠ {w}")
        if self.required_approvals:
            lines.append("  Required Approvals:")
            for a in self.required_approvals:
                lines.append(f"    • {a}")
        if self.suggested_remediation:
            lines.append("  Suggested Remediation:")
            for s in self.suggested_remediation:
                lines.append(f"    • {s}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ChangeGovernanceEngine:
    def __init__(self):
        self._policies: List[GovernancePolicy] = self._build_default_policies()
        self._history: List[GovernanceResult] = []

    def _build_default_policies(self) -> List[GovernancePolicy]:
        return [
            GovernancePolicy(
                id="pol_docs", name="Documentation Changes",
                description="Auto-apply documentation-only changes",
                conditions={"scope": "local", "risk": "none", "sensitivity": "none",
                            "files_match": ["*.md", "*.rst", "*.txt"]},
                decision=GovernanceDecision.AUTO_APPLY, priority=1,
            ),
            GovernancePolicy(
                id="pol_refactor_local", name="Local Refactoring",
                description="Apply local refactoring with patch mode",
                conditions={"scope": "local", "risk_max": 0.3, "max_files": 3},
                decision=GovernanceDecision.PATCH_ONLY, priority=2,
            ),
            GovernancePolicy(
                id="pol_feature_module", name="Module-Level Feature",
                description="Module-scope features require review",
                conditions={"scope": "module", "risk_max": 0.5},
                decision=GovernanceDecision.REQUIRE_REVIEW, priority=3,
            ),
            GovernancePolicy(
                id="pol_broad_change", name="Broad-Scope Change",
                description="Broad-scope changes require explicit approval",
                conditions={"scope": "broad"},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=4,
            ),
            GovernancePolicy(
                id="pol_cross_repo", name="Cross-Repository Change",
                description="Cross-repo changes always require approval",
                conditions={"scope": "cross_repo"},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=5,
            ),
            GovernancePolicy(
                id="pol_high_risk", name="High Risk Change",
                description="High-risk changes require explicit approval",
                conditions={"risk_min": 0.7},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=5,
            ),
            GovernancePolicy(
                id="pol_critical_risk", name="Critical Risk Change",
                description="Critical-risk changes are blocked",
                conditions={"risk_min": 0.9},
                decision=GovernanceDecision.BLOCK, priority=6,
            ),
            GovernancePolicy(
                id="pol_irreversible", name="Irreversible Change",
                description="Irreversible changes require explicit approval",
                conditions={"reversibility": "irreversible"},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=4,
            ),
            GovernancePolicy(
                id="pol_sensitive_security", name="Security-Sensitive Change",
                description="Security-sensitive changes require review",
                conditions={"sensitivity": "security"},
                decision=GovernanceDecision.REQUIRE_REVIEW, priority=3,
            ),
            GovernancePolicy(
                id="pol_sensitive_critical", name="Critical Sensitivity",
                description="Critical sensitivity changes require approval",
                conditions={"sensitivity": "critical"},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=5,
            ),
            GovernancePolicy(
                id="pol_deployment", name="Deployment Change",
                description="Deployment-impacting changes require approval",
                conditions={"deployment_impact": "production"},
                decision=GovernanceDecision.REQUIRE_APPROVAL, priority=5,
            ),
            GovernancePolicy(
                id="pol_architectural", name="Architectural Change",
                description="Architecture-impacting changes require review",
                conditions={"architectural_impact": "significant"},
                decision=GovernanceDecision.REQUIRE_REVIEW, priority=3,
            ),
            GovernancePolicy(
                id="pol_low_risk_safe", name="Low Risk Safe Change",
                description="Low-risk changes with verification can auto-apply",
                conditions={"risk_max": 0.2, "verification_min": 0.7, "max_files": 5},
                decision=GovernanceDecision.AUTO_APPLY, priority=1,
            ),
        ]

    def classify(self, context: Dict) -> ChangeClassification:
        risk_score = context.get("risk_score", 0.0)
        files = context.get("files_changed", [])

        if risk_score >= 0.9:
            risk = ChangeRisk.CRITICAL
        elif risk_score >= 0.7:
            risk = ChangeRisk.HIGH
        elif risk_score >= 0.4:
            risk = ChangeRisk.MEDIUM
        elif risk_score >= 0.1:
            risk = ChangeRisk.LOW
        else:
            risk = ChangeRisk.NONE

        scope_str = context.get("scope", "local")
        scope_map = {"local": ChangeScope.LOCAL, "module": ChangeScope.MODULE,
                     "broad": ChangeScope.BROAD, "cross_repo": ChangeScope.CROSS_REPO}
        scope = scope_map.get(scope_str, ChangeScope.LOCAL)

        rev_str = context.get("reversibility", "easy")
        rev_map = {"easy": ChangeReversibility.EASY, "moderate": ChangeReversibility.MODERATE,
                   "difficult": ChangeReversibility.DIFFICULT, "irreversible": ChangeReversibility.IRREVERSIBLE}
        reversibility = rev_map.get(rev_str, ChangeReversibility.EASY)

        return ChangeClassification(
            risk=risk,
            risk_score=risk_score,
            scope=scope,
            reversibility=reversibility,
            sensitivity=context.get("sensitivity", "none"),
            verification_coverage=context.get("verification_coverage", 0.0),
            user_intent=context.get("user_intent", "unknown"),
            deployment_impact=context.get("deployment_impact", "none"),
            architectural_impact=context.get("architectural_impact", "none"),
            files_changed=files,
            description=context.get("description", ""),
        )

    def evaluate(self, context: Dict) -> GovernanceResult:
        classification = self.classify(context)
        reasoning: List[str] = []
        warnings: List[str] = []
        required_approvals: List[str] = []
        remediation: List[str] = []

        sorted_policies = sorted(self._policies, key=lambda p: -p.priority)
        matched_policy = None
        decision = GovernanceDecision.AUTO_APPLY

        for policy in sorted_policies:
            if self._policy_matches(policy, classification, context):
                matched_policy = policy
                decision = policy.decision
                reasoning.append(f"Matched policy '{policy.name}': {policy.description}")
                break

        if decision == GovernanceDecision.BLOCK:
            reasoning.append(f"Change blocked by policy '{matched_policy.name}'")
            warnings.append(f"This change is too risky to apply automatically")
            remediation.append("Reduce risk score below 0.9")
            remediation.append("Split change into smaller, reversible steps")

        elif decision == GovernanceDecision.REQUIRE_APPROVAL:
            reasoning.append("Change requires explicit human approval")
            required_approvals.append("Human operator approval via --approve flag")
            if classification.reversibility == ChangeReversibility.IRREVERSIBLE:
                required_approvals.append("Rollback plan must be reviewed")
            if classification.risk == ChangeRisk.HIGH:
                warnings.append("High-risk change: ensure tests and verification are complete")
                remediation.append("Add comprehensive tests before applying")

        elif decision == GovernanceDecision.REQUIRE_REVIEW:
            reasoning.append("Change requires peer review before application")
            required_approvals.append("Code review via review board")

        elif decision == GovernanceDecision.PATCH_ONLY:
            reasoning.append("Change can be applied as a patch for inspection")
            if classification.verification_coverage < 0.5:
                warnings.append("Low verification coverage for this change")
                remediation.append("Increase test coverage before final application")

        elif decision == GovernanceDecision.AUTO_APPLY:
            reasoning.append("Change is safe for automatic application")
            if classification.risk_score > 0:
                reasoning.append(f"Risk score ({classification.risk_score:.2f}) within auto-apply threshold")

        if classification.verification_coverage < 0.3 and decision != GovernanceDecision.BLOCK:
            warnings.append(f"Verification coverage is low ({classification.verification_coverage:.0%})")
            remediation.append("Improve verification coverage before significant changes")

        result = GovernanceResult(
            classification=classification,
            decision=decision,
            matching_policy=matched_policy.name if matched_policy else None,
            reasoning=reasoning,
            warnings=warnings,
            required_approvals=required_approvals,
            suggested_remediation=remediation,
            override_available=decision not in (GovernanceDecision.BLOCK,),
        )

        self._history.append(result)
        return result

    def _policy_matches(self, policy: GovernancePolicy, classification: ChangeClassification, context: Dict) -> bool:
        cond = policy.conditions

        if "scope" in cond:
            if classification.scope.value != cond["scope"]:
                return False

        if "risk" in cond:
            if classification.risk.value != cond["risk"]:
                return False

        if "risk_max" in cond:
            if classification.risk_score > cond["risk_max"]:
                return False

        if "risk_min" in cond:
            if classification.risk_score < cond["risk_min"]:
                return False

        if "sensitivity" in cond:
            if classification.sensitivity != cond["sensitivity"]:
                return False

        if "reversibility" in cond:
            if classification.reversibility.value != cond["reversibility"]:
                return False

        if "max_files" in cond:
            if len(classification.files_changed) > cond["max_files"]:
                return False

        if "deployment_impact" in cond:
            if classification.deployment_impact != cond["deployment_impact"]:
                return False

        if "architectural_impact" in cond:
            if classification.architectural_impact != cond["architectural_impact"]:
                return False

        if "verification_min" in cond:
            if classification.verification_coverage < cond["verification_min"]:
                return False

        if "files_match" in cond:
            patterns = cond["files_match"]
            if not classification.files_changed:
                return False
            import fnmatch
            for f in classification.files_changed:
                if not any(fnmatch.fnmatch(f, p) for p in patterns):
                    return False

        return True

    def get_history(self) -> List[GovernanceResult]:
        return self._history

    def override_decision(self, result: GovernanceResult, reason: str) -> GovernanceResult:
        if not result.override_available:
            return result
        result.decision = GovernanceDecision.AUTO_APPLY
        result.reasoning.append(f"OVERRIDE: {reason}")
        result.suggested_remediation = []
        return result

    def to_dict(self) -> Dict:
        return {
            "policies": [p.to_dict() for p in self._policies],
            "history": [r.to_dict() for r in self._history],
        }

    @property
    def policies(self) -> List[GovernancePolicy]:
        return self._policies
