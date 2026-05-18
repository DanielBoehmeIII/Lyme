"""ContinuationExplainer — generates 'why Lyme is allowed to continue' explanations.

Produces human-readable justifications for autonomous execution,
building trust by explaining each decision factor.
"""

from __future__ import annotations
from .models import AutonomyLevel, AutonomyConfig, ActionDecision


class ContinuationExplainer:
    """Generate explanations for why Lyme can/cannot continue."""

    def explain_decision(self, decision: ActionDecision, config: AutonomyConfig) -> str:
        lines = []
        lines.append("=" * 55)
        lines.append("  AUTONOMY DECISION EXPLANATION")
        lines.append("=" * 55)
        lines.append(f"  Mode:              {config.level.value}")
        lines.append(f"  Confidence needed: {config.confidence_threshold}")
        lines.append(f"  Max risk allowed:  {config.max_risk_score}")
        lines.append(f"  Safe mode:         {'ON' if config.safe_mode else 'OFF'}")

        lines.append(f"\n  Decision: {'✓ ALLOWED' if decision.allowed else '✗ BLOCKED'}")

        if decision.allowed:
            lines.append(f"  Reason: {decision.reason}")
            lines.append("\n  Why Lyme was allowed to continue:")
            lines.append("  • Action is not blocked at this autonomy level")
            lines.append(f"  • Risk ({config.max_risk_score}) within acceptable range")
            lines.append(f"  • Confidence meets threshold")
        else:
            lines.append(f"  Reason: {decision.reason}")
            if decision.requires_approval:
                lines.append("\n  What needs to happen:")
                lines.append("  • An approval request has been created")
                lines.append("  • Use the approval system to grant or deny")
            if decision.suggested_level:
                lines.append(f"\n  Suggested mode: {decision.suggested_level.value}")
                lines.append("  • Switching to this mode may allow the action")

        if config.safe_mode:
            lines.append("\n  ⚠ Safe mode is ON — certain actions are restricted")
            blocked = [a.value for a in config.block_actions]
            if blocked:
                lines.append(f"  Blocked actions: {', '.join(blocked[:5])}")

        lines.append("\n" + "=" * 55)
        return "\n".join(lines)

    def explain_config(self, config: AutonomyConfig) -> str:
        lines = []
        lines.append("=" * 55)
        lines.append(f"  AUTONOMY CONFIG: {config.level.value}")
        lines.append("=" * 55)
        lines.append(f"  Confidence threshold: {config.confidence_threshold}")
        lines.append(f"  Max risk score:       {config.max_risk_score}")
        lines.append(f"  Safe mode:            {'ON' if config.safe_mode else 'OFF'}")
        lines.append(f"  Max files per action: {config.max_files_per_action}")
        lines.append(f"  Approval timeout:     {config.approval_timeout_s}s")
        lines.append("")

        if config.require_approval_for:
            lines.append("  Requires approval:")
            for a in config.require_approval_for:
                lines.append(f"    • {a.value}")
        if config.block_actions:
            lines.append("  Blocked:")
            for a in config.block_actions:
                lines.append(f"    • {a.value}")
        if config.block_commands:
            lines.append("  Blocked commands:")
            for c in config.block_commands:
                lines.append(f"    • {c}")
        lines.append("")
        lines.append("  Why this mode:")
        lines.append(f"  • {'Minimal risk — only suggestions allowed' if config.level == AutonomyLevel.SUGGEST_ONLY else ''}")
        lines.append(f"  • {'Safe patches with human review' if config.level == AutonomyLevel.PATCH_ONLY else ''}")
        lines.append(f"  • {'Verified patches with automatic test execution' if config.level == AutonomyLevel.PATCH_AND_TEST else ''}")
        lines.append(f"  • {'Trusted patches with automatic commits' if config.level == AutonomyLevel.PATCH_AND_COMMIT else ''}")
        lines.append(f"  • {'Production-ready patches with automatic PRs' if config.level == AutonomyLevel.PATCH_AND_PR else ''}")
        lines.append(f"  • {'Fully autonomous — continuous background operation' if config.level == AutonomyLevel.CONTINUOUS_BACKGROUND else ''}")
        lines.append("=" * 55)
        return "\n".join(lines)
