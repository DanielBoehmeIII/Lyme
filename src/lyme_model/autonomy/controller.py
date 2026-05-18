"""AutonomyController — decides whether actions are allowed.

Decides based on:
- current autonomy level
- confidence threshold
- risk score
- action type (blocked, requires-approval, or allowed)
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import (
    AutonomyLevel, AutonomyConfig, Action, ActionDecision,
    ApprovalRequest, ApprovalStatus,
)


class AutonomyController:
    """Gate all agent actions through autonomy levels."""

    def __init__(self, config: Optional[AutonomyConfig] = None):
        self.config = config or AutonomyConfig.for_level(AutonomyLevel.PATCH_ONLY)
        self.approvals: list[ApprovalRequest] = []

    def set_level(self, level: AutonomyLevel) -> None:
        self.config = AutonomyConfig.for_level(level)

    def decide(self, action: Action, description: str, confidence: float,
               risk_score: float, affected_files: list[str]) -> ActionDecision:
        if action in self.config.block_actions:
            return ActionDecision(
                allowed=False,
                reason=f"Action {action.value} is blocked at {self.config.level.value} level",
                requires_approval=False,
            )

        if confidence < self.config.confidence_threshold:
            return ActionDecision(
                allowed=False,
                reason=f"Confidence {confidence:.3f} < threshold {self.config.confidence_threshold}",
                requires_approval=False,
                suggested_level=self._suggest_level_for_confidence(confidence),
            )

        if risk_score > self.config.max_risk_score:
            suggestion = self._demote_for_risk(risk_score)
            return ActionDecision(
                allowed=False,
                reason=f"Risk score {risk_score:.3f} > max {self.config.max_risk_score}",
                requires_approval=False,
                suggested_level=suggestion,
            )

        if len(affected_files) > self.config.max_files_per_action:
            return ActionDecision(
                allowed=False,
                reason=f"Affected files {len(affected_files)} > max {self.config.max_files_per_action}",
                requires_approval=False,
            )

        if action in self.config.require_approval_for:
            approval = self._create_approval(action, description, confidence, risk_score, affected_files)
            return ActionDecision(
                allowed=False,
                reason=f"Action {action.value} requires approval at {self.config.level.value} level",
                requires_approval=True,
                approval=approval,
            )

        for blocked_cmd in self.config.block_commands:
            if blocked_cmd in description.lower():
                return ActionDecision(
                    allowed=False,
                    reason=f"Command blocked by safety policy: '{blocked_cmd}'",
                    requires_approval=False,
                )

        return ActionDecision(
            allowed=True,
            reason=f"Action allowed at {self.config.level.value} level",
            requires_approval=False,
        )

    def approve(self, approval_id: str, decided_by: str = "auto") -> Optional[ActionDecision]:
        for approval in self.approvals:
            if approval.id == approval_id and approval.status == ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.APPROVED
                approval.decided_at = datetime.now(timezone.utc).isoformat()
                approval.decided_by = decided_by
                return ActionDecision(
                    allowed=True,
                    reason=f"Approval granted by {decided_by}",
                    requires_approval=False,
                    approval=approval,
                )
        return None

    def deny(self, approval_id: str, decided_by: str = "auto", notes: str = "") -> Optional[ActionDecision]:
        for approval in self.approvals:
            if approval.id == approval_id and approval.status == ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.DENIED
                approval.decided_at = datetime.now(timezone.utc).isoformat()
                approval.decided_by = decided_by
                approval.notes = notes
                return ActionDecision(
                    allowed=False,
                    reason=f"Approval denied by {decided_by}: {notes}",
                    requires_approval=False,
                    approval=approval,
                )
        return None

    def _create_approval(self, action: Action, description: str, confidence: float,
                         risk_score: float, affected_files: list[str]) -> ApprovalRequest:
        approval = ApprovalRequest(
            id=uuid.uuid4().hex[:12],
            action=action,
            description=description,
            reason=f"Requires approval at {self.config.level.value} level",
            confidence=confidence,
            risk_score=risk_score,
            affected_files=affected_files,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.approvals.append(approval)
        return approval

    def _suggest_level_for_confidence(self, confidence: float) -> AutonomyLevel:
        if confidence >= 0.9:
            return AutonomyLevel.CONTINUOUS_BACKGROUND
        elif confidence >= 0.85:
            return AutonomyLevel.PATCH_AND_PR
        elif confidence >= 0.8:
            return AutonomyLevel.PATCH_AND_COMMIT
        elif confidence >= 0.75:
            return AutonomyLevel.PATCH_AND_TEST
        elif confidence >= 0.7:
            return AutonomyLevel.PATCH_ONLY
        else:
            return AutonomyLevel.SUGGEST_ONLY

    def _demote_for_risk(self, risk_score: float) -> AutonomyLevel:
        if risk_score >= 0.7:
            return AutonomyLevel.SUGGEST_ONLY
        elif risk_score >= 0.5:
            return AutonomyLevel.PATCH_ONLY
        elif risk_score >= 0.3:
            return AutonomyLevel.PATCH_AND_TEST
        else:
            return self.config.level

    def pending_approvals(self) -> list[ApprovalRequest]:
        return [a for a in self.approvals if a.status == ApprovalStatus.PENDING]
