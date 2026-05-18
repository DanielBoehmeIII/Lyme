"""Data models for the trust-gated autonomy system."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AutonomyLevel(Enum):
    SUGGEST_ONLY = "suggest_only"
    PATCH_ONLY = "patch_only"
    PATCH_AND_TEST = "patch_and_test"
    PATCH_AND_COMMIT = "patch_and_commit"
    PATCH_AND_PR = "patch_and_pr"
    CONTINUOUS_BACKGROUND = "continuous_background"


class Action(Enum):
    READ_FILE = "read_file"
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    RUN_COMMAND = "run_command"
    INSTALL_DEPENDENCY = "install_dependency"
    CREATE_BRANCH = "create_branch"
    COMMIT = "commit"
    PUSH = "push"
    CREATE_PR = "create_pr"
    MERGE = "merge"
    RUN_TESTS = "run_tests"
    EXECUTE_CODE = "execute_code"
    MODIFY_CONFIG = "modify_config"
    MODIFY_CI = "modify_ci"
    ACCESS_SECRETS = "access_secrets"
    NETWORK_ACCESS = "network_access"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    id: str
    action: Action
    description: str
    reason: str
    confidence: float
    risk_score: float
    affected_files: list[str]
    status: ApprovalStatus
    created_at: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action.value,
            "description": self.description,
            "reason": self.reason,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "affected_files": self.affected_files,
            "status": self.status.value,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "notes": self.notes,
        }


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    autonomy_level: AutonomyLevel
    action: Action
    description: str
    confidence: float
    risk_score: float
    approved: bool
    result: str
    duration_ms: float
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    approval_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "autonomy_level": self.autonomy_level.value,
            "action": self.action.value,
            "description": self.description,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "approved": self.approved,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "files_changed": self.files_changed,
            "commands_run": self.commands_run,
            "approval_id": self.approval_id,
            "error": self.error,
        }


@dataclass
class AutonomyConfig:
    level: AutonomyLevel
    confidence_threshold: float
    max_risk_score: float
    require_approval_for: list[Action]
    block_actions: list[Action]
    safe_mode: bool
    max_files_per_action: int
    allowed_commands: list[str]
    block_commands: list[str]
    audit_log_path: str
    approval_timeout_s: int

    DEFAULTS = {
        AutonomyLevel.SUGGEST_ONLY: {
            "confidence_threshold": 0.0,
            "max_risk_score": 0.0,
            "require_approval_for": None,
            "block_actions": [a for a in Action],
            "safe_mode": True,
            "max_files_per_action": 0,
        },
        AutonomyLevel.PATCH_ONLY: {
            "confidence_threshold": 0.7,
            "max_risk_score": 0.3,
            "require_approval_for": [Action.DELETE_FILE, Action.CREATE_FILE, Action.MODIFY_CONFIG],
            "block_actions": [Action.PUSH, Action.MERGE, Action.CREATE_PR, Action.COMMIT],
            "safe_mode": True,
            "max_files_per_action": 5,
        },
        AutonomyLevel.PATCH_AND_TEST: {
            "confidence_threshold": 0.75,
            "max_risk_score": 0.4,
            "require_approval_for": [Action.DELETE_FILE, Action.MODIFY_CI, Action.MODIFY_CONFIG],
            "block_actions": [Action.PUSH, Action.MERGE, Action.CREATE_PR],
            "safe_mode": True,
            "max_files_per_action": 10,
        },
        AutonomyLevel.PATCH_AND_COMMIT: {
            "confidence_threshold": 0.8,
            "max_risk_score": 0.5,
            "require_approval_for": [Action.DELETE_FILE, Action.MODIFY_CI, Action.MODIFY_CONFIG, Action.PUSH],
            "block_actions": [Action.MERGE],
            "safe_mode": False,
            "max_files_per_action": 20,
        },
        AutonomyLevel.PATCH_AND_PR: {
            "confidence_threshold": 0.85,
            "max_risk_score": 0.6,
            "require_approval_for": [Action.MERGE, Action.MODIFY_CI],
            "block_actions": [Action.MERGE],
            "safe_mode": False,
            "max_files_per_action": 50,
        },
        AutonomyLevel.CONTINUOUS_BACKGROUND: {
            "confidence_threshold": 0.9,
            "max_risk_score": 0.7,
            "require_approval_for": [Action.MERGE, Action.MODIFY_CI, Action.DELETE_FILE],
            "block_actions": [],
            "safe_mode": False,
            "max_files_per_action": 100,
        },
    }

    @classmethod
    def for_level(cls, level: AutonomyLevel) -> AutonomyConfig:
        defaults = cls.DEFAULTS[level]
        return cls(
            level=level,
            confidence_threshold=defaults["confidence_threshold"],
            max_risk_score=defaults["max_risk_score"],
            require_approval_for=defaults.get("require_approval_for", []) or [],
            block_actions=defaults.get("block_actions", []) or [],
            safe_mode=defaults["safe_mode"],
            max_files_per_action=defaults["max_files_per_action"],
            allowed_commands=["pip", "npm", "pytest", "git", "python", "node", "cargo", "go", "make"],
            block_commands=["rm -rf", "sudo", "chmod", "dd", ":(){:|:&};:"],
            audit_log_path=".lyme/autonomy/audit.json",
            approval_timeout_s=3600,
        )

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "confidence_threshold": self.confidence_threshold,
            "max_risk_score": self.max_risk_score,
            "require_approval_for": [a.value for a in self.require_approval_for],
            "block_actions": [a.value for a in self.block_actions],
            "safe_mode": self.safe_mode,
            "max_files_per_action": self.max_files_per_action,
            "allowed_commands": self.allowed_commands,
            "block_commands": self.block_commands,
            "approval_timeout_s": self.approval_timeout_s,
        }


@dataclass
class ActionDecision:
    allowed: bool
    reason: str
    requires_approval: bool
    approval: Optional[ApprovalRequest] = None
    suggested_level: Optional[AutonomyLevel] = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "approval": self.approval.to_dict() if self.approval else None,
            "suggested_level": self.suggested_level.value if self.suggested_level else None,
        }
