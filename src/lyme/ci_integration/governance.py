from dataclasses import dataclass, field, asdict
from typing import List, Optional
from enum import Enum


class PolicyAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REQUIRE_REVIEW = "require_review"


@dataclass
class PolicyRule:
    name: str = ""
    description: str = ""
    condition: str = ""
    action: str = PolicyAction.ALLOW
    priority: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PolicyDecision:
    action: str = PolicyAction.ALLOW
    triggered_rules: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class GovernancePolicy:
    def __init__(self):
        self.rules: List[PolicyRule] = self._default_rules()

    def _default_rules(self) -> List[PolicyRule]:
        return [
            PolicyRule(name="high-risk-block",
                       description="Block changes with risk score >= 0.7",
                       condition="risk_score >= 0.7",
                       action=PolicyAction.BLOCK, priority=100),
            PolicyRule(name="security-violation-block",
                       description="Block changes with security violations",
                       condition="security_violation",
                       action=PolicyAction.BLOCK, priority=90),
            PolicyRule(name="critical-invariant-warn",
                       description="Warn on critical invariant violations",
                       condition="critical_invariant",
                       action=PolicyAction.WARN, priority=80),
            PolicyRule(name="no-test-gaps-warn",
                       description="Warn when source changes without tests",
                       condition="test_gaps",
                       action=PolicyAction.WARN, priority=50),
            PolicyRule(name="large-change-review",
                       description="Request review for changes > 200 lines",
                       condition="large_change",
                       action=PolicyAction.REQUIRE_REVIEW, priority=60),
        ]

    def evaluate(self, risk_score: float, violations: List[dict],
                 test_gaps: List[dict], changed_files: List[str]) -> PolicyDecision:
        triggered = []
        action = PolicyAction.ALLOW
        total_lines = 0

        for rule in sorted(self.rules, key=lambda r: -r.priority):
            if rule.condition == "risk_score >= 0.7" and risk_score >= 0.7:
                triggered.append(rule.name)
                action = self._max_action(action, PolicyAction.BLOCK)

            elif rule.condition == "security_violation":
                for v in violations:
                    if v.get("invariant_type") == "security_regression" or "security" in v.get("description", "").lower():
                        triggered.append(rule.name)
                        action = self._max_action(action, PolicyAction.BLOCK)
                        break

            elif rule.condition == "critical_invariant":
                for v in violations:
                    if v.get("severity") in ("high", "critical"):
                        triggered.append(rule.name)
                        action = self._max_action(action, PolicyAction.WARN)
                        break

            elif rule.condition == "test_gaps" and test_gaps:
                triggered.append(rule.name)
                action = self._max_action(action, PolicyAction.WARN)

            elif rule.condition == "large_change":
                total_lines = sum(1 for f in changed_files)
                if total_lines > 200:
                    triggered.append(rule.name)
                    action = self._max_action(action, PolicyAction.REQUIRE_REVIEW)

        return PolicyDecision(
            action=action,
            triggered_rules=triggered,
            reason=f"{action.value}: {len(triggered)} rules triggered ({', '.join(triggered)})"
        )

    def _max_action(self, a: str, b: str) -> str:
        order = {PolicyAction.ALLOW: 0, PolicyAction.WARN: 1,
                 PolicyAction.REQUIRE_REVIEW: 2, PolicyAction.BLOCK: 3}
        return a if order.get(a, 0) >= order.get(b, 0) else b
