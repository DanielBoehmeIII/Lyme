from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import uuid


class ActionType(str, Enum):
    READ_ONLY = "read_only"
    SUGGEST_PATCH = "suggest_patch"
    CREATE_PATCH = "create_patch"
    RUN_TESTS = "run_tests"
    MODIFY_FILES = "modify_files"
    OPEN_PR = "open_pr"
    ROLLBACK = "rollback"
    DEPLOY = "deploy"
    DELETE_FILES = "delete_files"
    MODIFY_CONFIG = "modify_config"
    MODIFY_SECRETS = "modify_secrets"
    MODIFY_CI = "modify_ci"
    EXECUTE_COMMANDS = "execute_commands"


class AutonomyLevel(str, Enum):
    NONE = "none"
    READ_ONLY = "read_only"
    SUGGEST_ONLY = "suggest_only"
    VERIFIED_AUTO = "verified_auto"
    FULL_AUTO = "full_auto"


@dataclass
class PolicyRule:
    id: str
    action: ActionType
    allowed_levels: List[AutonomyLevel]
    conditions: List[str] = field(default_factory=list)
    requires_approval: bool = False
    requires_audit: bool = True
    max_risk_score: float = 1.0
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "action": self.action.value,
            "allowed_levels": [l.value for l in self.allowed_levels],
            "conditions": self.conditions,
            "requires_approval": self.requires_approval,
            "requires_audit": self.requires_audit,
            "max_risk_score": self.max_risk_score,
            "description": self.description,
        }


@dataclass
class PolicyEvaluation:
    rule_id: str
    action: ActionType
    allowed: bool
    autonomy_level: AutonomyLevel
    reason: str
    risk_score: float
    requires_approval: bool
    override_available: bool = False

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "action": self.action.value,
            "allowed": self.allowed,
            "autonomy_level": self.autonomy_level.value,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "requires_approval": self.requires_approval,
            "override_available": self.override_available,
        }


@dataclass
class PolicyConfig:
    default_level: AutonomyLevel = AutonomyLevel.SUGGEST_ONLY
    max_level: AutonomyLevel = AutonomyLevel.VERIFIED_AUTO
    require_approval_for: List[ActionType] = field(default_factory=lambda: [
        ActionType.DEPLOY, ActionType.DELETE_FILES, ActionType.MODIFY_SECRETS,
    ])
    audit_all_modifications: bool = True
    max_risk_threshold: float = 0.7
    enable_override: bool = True

    def to_dict(self) -> Dict:
        return {
            "default_level": self.default_level.value,
            "max_level": self.max_level.value,
            "require_approval_for": [a.value for a in self.require_approval_for],
            "audit_all_modifications": self.audit_all_modifications,
            "max_risk_threshold": self.max_risk_threshold,
            "enable_override": self.enable_override,
        }


@dataclass
class PolicyExplainability:
    rule_id: str
    action: ActionType
    decision: str
    factors: List[Dict]
    override_path: str = ""

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Policy Decision: {self.action.value}")
        lines.append(f"**Rule**: {self.rule_id}")
        lines.append(f"**Decision**: {self.decision}")
        lines.append(f"")
        lines.append(f"### Factors Considered")
        for factor in self.factors:
            lines.append(f"- **{factor['name']}**: {factor['value']} (weight: {factor['weight']})")
        if self.override_path:
            lines.append(f"")
            lines.append(f"**Override Path**: {self.override_path}")
        return "\n".join(lines)


class AutonomyPolicyEngine:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()
        self._rules = self._build_default_rules()
        self._risk_weights = self._default_risk_weights()

    def _build_default_rules(self) -> List[PolicyRule]:
        return [
            PolicyRule(
                id="rule_read", action=ActionType.READ_ONLY,
                allowed_levels=[AutonomyLevel.NONE, AutonomyLevel.READ_ONLY, AutonomyLevel.SUGGEST_ONLY,
                                AutonomyLevel.VERIFIED_AUTO, AutonomyLevel.FULL_AUTO],
                description="Reading files is always allowed",
            ),
            PolicyRule(
                id="rule_suggest", action=ActionType.SUGGEST_PATCH,
                allowed_levels=[AutonomyLevel.SUGGEST_ONLY, AutonomyLevel.VERIFIED_AUTO,
                                AutonomyLevel.FULL_AUTO],
                requires_approval=False,
                description="Suggesting patches requires suggest+ autonomy",
            ),
            PolicyRule(
                id="rule_create_patch", action=ActionType.CREATE_PATCH,
                allowed_levels=[AutonomyLevel.VERIFIED_AUTO, AutonomyLevel.FULL_AUTO],
                requires_approval=False,
                description="Creating patches requires verified_auto+",
            ),
            PolicyRule(
                id="rule_run_tests", action=ActionType.RUN_TESTS,
                allowed_levels=[AutonomyLevel.SUGGEST_ONLY, AutonomyLevel.VERIFIED_AUTO,
                                AutonomyLevel.FULL_AUTO],
                requires_approval=False,
                description="Running tests is allowed at suggest+",
            ),
            PolicyRule(
                id="rule_modify_files", action=ActionType.MODIFY_FILES,
                allowed_levels=[AutonomyLevel.VERIFIED_AUTO, AutonomyLevel.FULL_AUTO],
                requires_approval=False, requires_audit=True,
                conditions=["test_coverage > 0.3", "edit_size < 50_lines"],
                description="File modification requires verification",
            ),
            PolicyRule(
                id="rule_open_pr", action=ActionType.OPEN_PR,
                allowed_levels=[AutonomyLevel.FULL_AUTO],
                requires_approval=True, requires_audit=True,
                conditions=["tests_passing", "review_passed"],
                description="Opening PRs requires full auto + approval",
            ),
            PolicyRule(
                id="rule_rollback", action=ActionType.ROLLBACK,
                allowed_levels=[AutonomyLevel.VERIFIED_AUTO, AutonomyLevel.FULL_AUTO],
                requires_approval=True, requires_audit=True,
                conditions=["backup_verified"],
                description="Rollback requires approval",
            ),
            PolicyRule(
                id="rule_deploy", action=ActionType.DEPLOY,
                allowed_levels=[AutonomyLevel.FULL_AUTO],
                requires_approval=True, requires_audit=True,
                max_risk_score=0.3,
                description="Deployment always requires approval",
            ),
            PolicyRule(
                id="rule_delete", action=ActionType.DELETE_FILES,
                allowed_levels=[AutonomyLevel.FULL_AUTO],
                requires_approval=True, requires_audit=True,
                max_risk_score=0.2,
                description="File deletion requires approval",
            ),
            PolicyRule(
                id="rule_modify_secrets", action=ActionType.MODIFY_SECRETS,
                allowed_levels=[AutonomyLevel.NONE],
                requires_approval=True, requires_audit=True,
                max_risk_score=0.0,
                description="Secret modification is never automatic",
            ),
            PolicyRule(
                id="rule_modify_ci", action=ActionType.MODIFY_CI,
                allowed_levels=[AutonomyLevel.VERIFIED_AUTO, AutonomyLevel.FULL_AUTO],
                requires_approval=True,
                description="CI modification requires approval",
            ),
            PolicyRule(
                id="rule_execute_commands", action=ActionType.EXECUTE_COMMANDS,
                allowed_levels=[AutonomyLevel.FULL_AUTO],
                requires_approval=True, requires_audit=True,
                max_risk_score=0.4,
                description="Command execution requires approval",
            ),
        ]

    def _default_risk_weights(self) -> Dict[str, float]:
        return {
            "repo_risk": 0.25,
            "edit_size": 0.20,
            "test_coverage": 0.15,
            "confidence": 0.15,
            "sensitive_zone": 0.15,
            "historical_failure": 0.10,
        }

    def evaluate(self, action: ActionType, context: Dict) -> PolicyEvaluation:
        rule = self._find_rule(action)
        if not rule:
            return PolicyEvaluation(
                rule_id="unknown", action=action, allowed=False,
                autonomy_level=self.config.default_level,
                reason=f"No policy rule defined for {action.value}",
                risk_score=1.0, requires_approval=True,
            )

        current_level = self._determine_current_level(context)
        risk_score = self._compute_risk_score(action, context)

        if action in self.config.require_approval_for:
            requires_approval = True
        else:
            requires_approval = rule.requires_approval

        if current_level not in rule.allowed_levels:
            return PolicyEvaluation(
                rule_id=rule.id, action=action, allowed=False,
                autonomy_level=current_level,
                reason=f"Autonomy level {current_level.value} insufficient for {action.value}. Requires {[l.value for l in rule.allowed_levels]}",
                risk_score=risk_score, requires_approval=True,
                override_available=self.config.enable_override,
            )

        if risk_score > rule.max_risk_score:
            if risk_score > self.config.max_risk_threshold:
                return PolicyEvaluation(
                    rule_id=rule.id, action=action, allowed=False,
                    autonomy_level=current_level,
                    reason=f"Risk score {risk_score:.2f} exceeds max threshold {rule.max_risk_score}",
                    risk_score=risk_score, requires_approval=True,
                    override_available=self.config.enable_override,
                )

        conditions_met = all(self._evaluate_condition(c, context) for c in rule.conditions)
        if rule.conditions and not conditions_met:
            return PolicyEvaluation(
                rule_id=rule.id, action=action, allowed=False,
                autonomy_level=current_level,
                reason=f"Policy conditions not met: {rule.conditions}",
                risk_score=risk_score, requires_approval=requires_approval,
            )

        return PolicyEvaluation(
            rule_id=rule.id, action=action, allowed=True,
            autonomy_level=current_level,
            reason=f"Action {action.value} permitted at {current_level.value} level (risk: {risk_score:.2f})",
            risk_score=risk_score, requires_approval=requires_approval,
        )

    def explain(self, evaluation: PolicyEvaluation) -> PolicyExplainability:
        factors = [
            {"name": "Autonomy Level", "value": evaluation.autonomy_level.value, "weight": 0.25},
            {"name": "Risk Score", "value": f"{evaluation.risk_score:.2f}", "weight": 0.25},
            {"name": "Requires Approval", "value": str(evaluation.requires_approval), "weight": 0.20},
            {"name": "Override Available", "value": str(evaluation.override_available), "weight": 0.15},
            {"name": "Action Type", "value": evaluation.action.value, "weight": 0.15},
        ]

        return PolicyExplainability(
            rule_id=evaluation.rule_id,
            action=evaluation.action,
            decision="ALLOWED" if evaluation.allowed else "DENIED",
            factors=factors,
            override_path="Override via --force flag or policy config change" if evaluation.override_available else "",
        )

    def _find_rule(self, action: ActionType) -> Optional[PolicyRule]:
        for rule in self._rules:
            if rule.action == action:
                return rule
        return None

    def _determine_current_level(self, context: Dict) -> AutonomyLevel:
        return AutonomyLevel(context.get("autonomy_level", self.config.default_level.value))

    def _compute_risk_score(self, action: ActionType, context: Dict) -> float:
        risk_scores = {
            ActionType.READ_ONLY: 0.05,
            ActionType.SUGGEST_PATCH: 0.15,
            ActionType.CREATE_PATCH: 0.25,
            ActionType.RUN_TESTS: 0.10,
            ActionType.MODIFY_FILES: 0.40,
            ActionType.OPEN_PR: 0.50,
            ActionType.ROLLBACK: 0.30,
            ActionType.DEPLOY: 0.80,
            ActionType.DELETE_FILES: 0.70,
            ActionType.MODIFY_CONFIG: 0.45,
            ActionType.MODIFY_SECRETS: 0.95,
            ActionType.MODIFY_CI: 0.60,
            ActionType.EXECUTE_COMMANDS: 0.75,
        }

        base = risk_scores.get(action, 0.5)
        modifiers = []

        if "test_coverage" in context:
            tc = context["test_coverage"]
            if tc < 0.3:
                modifiers.append(0.15)

        if "edit_size" in context:
            es = context["edit_size"]
            if es > 100:
                modifiers.append(0.20)
            elif es > 50:
                modifiers.append(0.10)

        if "confidence" in context:
            conf = context["confidence"]
            if conf < 0.5:
                modifiers.append(0.15)

        if "historical_failure_rate" in context:
            hfr = context["historical_failure_rate"]
            modifiers.append(hfr * 0.20)

        if "sensitive_zone" in context and context["sensitive_zone"]:
            modifiers.append(0.20)

        if "repo_risk" in context:
            modifiers.append(context["repo_risk"] * 0.15)

        total = base + sum(modifiers)
        return min(1.0, total)

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        if "<" in condition:
            parts = condition.split("<")
            if len(parts) == 2:
                key = parts[0].strip()
                val_str = parts[1].strip().replace("_lines", "").replace("%", "").strip()
                try:
                    val = float(val_str)
                    ctx_val = float(context.get(key, 0))
                    return ctx_val < val
                except (ValueError, TypeError):
                    return True
        if ">" in condition:
            parts = condition.split(">")
            if len(parts) == 2:
                key = parts[0].strip()
                val_str = parts[1].strip().replace("_lines", "").replace("%", "").strip()
                try:
                    val = float(val_str)
                    ctx_val = float(context.get(key, 0))
                    return ctx_val > val
                except (ValueError, TypeError):
                    return True
        if "==" in condition:
            parts = condition.split("==")
            if len(parts) == 2:
                return context.get(parts[0].strip()) == parts[1].strip()
        if "_passing" in condition or "_verified" in condition or "_passed" in condition:
            return context.get(condition.strip(), False)
        return True

    def override(self, evaluation: PolicyEvaluation, reason: str) -> PolicyEvaluation:
        if not evaluation.override_available:
            return evaluation
        return PolicyEvaluation(
            rule_id=evaluation.rule_id,
            action=evaluation.action,
            allowed=True,
            autonomy_level=evaluation.autonomy_level,
            reason=f"OVERRIDE: {reason}",
            risk_score=evaluation.risk_score,
            requires_approval=False,
            override_available=True,
        )

    def audit_trail(self, evaluations: List[PolicyEvaluation]) -> str:
        lines = []
        lines.append("# Autonomy Policy Audit Trail")
        lines.append("")
        for ev in evaluations:
            status = "✅ ALLOWED" if ev.allowed else "❌ DENIED"
            lines.append(f"## {ev.action.value}: {status}")
            lines.append(f"- Rule: {ev.rule_id}")
            lines.append(f"- Reason: {ev.reason}")
            lines.append(f"- Risk Score: {ev.risk_score:.2f}")
            lines.append(f"- Approval Required: {ev.requires_approval}")
            lines.append("")
        return "\n".join(lines)

    @property
    def rules(self) -> List[PolicyRule]:
        return self._rules
