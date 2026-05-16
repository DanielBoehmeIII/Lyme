import time
import uuid
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class DiffType(str, Enum):
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    REFACTOR = "refactor"
    MOVE = "move"
    RENAME = "rename"
    SEMANTIC_CHANGE = "semantic_change"


class IntentType(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE_ADDITION = "feature_addition"
    REFACTORING = "refactoring"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class InvariantType(str, Enum):
    TYPE_CONTRACT = "type_contract"
    DATA_INVARIANT = "data_invariant"
    BUSINESS_RULE = "business_rule"
    INTERFACE_CONTRACT = "interface_contract"
    PERFORMANCE_CONSTRAINT = "performance_constraint"
    SECURITY_POLICY = "security_policy"
    DEPENDENCY_RULE = "dependency_rule"
    ARCHITECTURAL_CONSTRAINT = "architectural_constraint"
    CONCURRENCY_SAFETY = "concurrency_safety"
    ERROR_CONTRACT = "error_contract"


class ImpactLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class RollbackStrategy(str, Enum):
    GIT_REVERT = "git_revert"
    PATCH_INVERSE = "patch_inverse"
    STATE_RESTORE = "state_restore"
    SEMANTIC_ROLLBACK = "semantic_rollback"
    FULL_CHECKPOINT = "full_checkpoint"
    NONE = "none"


@dataclass
class SyntacticChange:
    file_path: str = ""
    diff_type: str = DiffType.MODIFICATION
    lines_added: int = 0
    lines_removed: int = 0
    hunks: int = 0
    old_code_preview: str = ""
    new_code_preview: str = ""
    language: str = ""
    change_scope: str = ""  # function, class, module, config, test, doc
    function_name: Optional[str] = None
    class_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BehavioralIntent:
    intent_type: str = IntentType.UNKNOWN
    description: str = ""
    motivation: str = ""
    expected_behavior: str = ""
    previous_behavior: str = ""
    affected_interfaces: List[str] = field(default_factory=list)
    user_facing_change: bool = False
    backward_compatible: bool = True
    migration_required: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AffectedInvariant:
    invariant_type: str = InvariantType.TYPE_CONTRACT
    description: str = ""
    location: str = ""
    status: str = "preserved"
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArchitecturalImpact:
    impact_level: str = ImpactLevel.NONE
    affected_subsystems: List[str] = field(default_factory=list)
    dependency_changes: List[str] = field(default_factory=list)
    interface_changes: List[str] = field(default_factory=list)
    coupling_change: float = 0.0
    cohesion_change: float = 0.0
    complexity_delta: int = 0
    architecture_description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskScore:
    overall: str = RiskLevel.LOW
    regression_risk: str = RiskLevel.LOW
    security_risk: str = RiskLevel.NONE
    performance_risk: str = RiskLevel.NONE
    compatibility_risk: str = RiskLevel.LOW
    deploy_risk: str = RiskLevel.LOW
    rollback_difficulty: str = RiskLevel.LOW
    risk_factors: List[str] = field(default_factory=list)
    risk_score_numeric: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationResult:
    status: str = VerificationStatus.UNVERIFIED
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_percent: Optional[float] = None
    static_analysis_passed: bool = True
    type_checks_passed: bool = True
    lint_passed: bool = True
    verification_gaps: List[str] = field(default_factory=list)
    verification_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RollbackStrategy:
    strategy: str = RollbackStrategy.NONE
    complexity: str = "simple"
    estimated_time_minutes: int = 0
    steps: List[str] = field(default_factory=list)
    data_loss_risk: str = RiskLevel.NONE

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiffHeader:
    diff_id: str = field(default_factory=lambda: f"sd-{uuid.uuid4().hex[:16]}")
    schema_version: str = "0.7.0"
    schema_urn: str = "urn:lyme:standard:semantic-diff:v1"
    source_commit: str = ""
    target_commit: str = ""
    branch: str = ""
    repository: str = ""
    author: str = ""
    created_at: float = field(default_factory=time.time)
    pr_url: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SemanticDiff:
    header: DiffHeader = field(default_factory=DiffHeader)
    syntactic_changes: List[dict] = field(default_factory=list)
    behavioral_intent: Optional[dict] = None
    affected_invariants: List[dict] = field(default_factory=list)
    architectural_impact: Optional[dict] = None
    risk: Optional[dict] = None
    verification: Optional[dict] = None
    rollback: Optional[dict] = None
    confidence: float = 1.0
    summary: str = ""

    def add_syntactic_change(self, change: SyntacticChange):
        self.syntactic_changes.append(change.to_dict())

    def set_intent(self, intent: BehavioralIntent):
        self.behavioral_intent = intent.to_dict()

    def add_invariant(self, invariant: AffectedInvariant):
        self.affected_invariants.append(invariant.to_dict())

    def set_architectural_impact(self, impact: ArchitecturalImpact):
        self.architectural_impact = impact.to_dict()

    def set_risk(self, risk: RiskScore):
        self.risk = risk.to_dict()

    def set_verification(self, verification: VerificationResult):
        self.verification = verification.to_dict()

    def set_rollback(self, rollback: RollbackStrategy):
        self.rollback = rollback.to_dict()

    def finalize(self):
        total_added = sum(c.get("lines_added", 0) for c in self.syntactic_changes)
        total_removed = sum(c.get("lines_removed", 0) for c in self.syntactic_changes)
        total_files = len(self.syntactic_changes)
        intent_desc = self.behavioral_intent.get("description", "") if self.behavioral_intent else ""
        risk_level = self.risk.get("overall", "unknown") if self.risk else "unknown"

        self.summary = (
            f"SemanticDiff v{self.header.schema_version} | "
            f"{total_files} files | +{total_added} -{total_removed} lines | "
            f"Risk: {risk_level} | "
            f"Intent: {intent_desc[:80] if intent_desc else 'Not specified'}"
        )

    def to_dict(self) -> dict:
        self.finalize()
        return {
            "header": self.header.to_dict(),
            "syntactic_changes": self.syntactic_changes,
            "behavioral_intent": self.behavioral_intent,
            "affected_invariants": self.affected_invariants,
            "architectural_impact": self.architectural_impact,
            "risk": self.risk,
            "verification": self.verification,
            "rollback": self.rollback,
            "confidence": self.confidence,
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticDiff":
        sd = cls.__new__(cls)
        hdr = d.get("header", {})
        sd.header = DiffHeader(**{
            k: v for k, v in hdr.items()
            if k in DiffHeader.__dataclass_fields__
        })
        sd.syntactic_changes = d.get("syntactic_changes", [])
        sd.behavioral_intent = d.get("behavioral_intent")
        sd.affected_invariants = d.get("affected_invariants", [])
        sd.architectural_impact = d.get("architectural_impact")
        sd.risk = d.get("risk")
        sd.verification = d.get("verification")
        sd.rollback = d.get("rollback")
        sd.confidence = d.get("confidence", 1.0)
        sd.summary = d.get("summary", "")
        return sd

    @classmethod
    def from_json(cls, s: str) -> "SemanticDiff":
        return cls.from_dict(json.loads(s))


@dataclass
class DiffReport:
    semantic_diff: SemanticDiff = field(default_factory=SemanticDiff)
    agent_notes: str = ""
    review_checklist: List[str] = field(default_factory=list)
    suggested_reviewers: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    recommended_action: str = "review"
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "semantic_diff": self.semantic_diff.to_dict(),
            "agent_notes": self.agent_notes,
            "review_checklist": self.review_checklist,
            "suggested_reviewers": self.suggested_reviewers,
            "blocking_issues": self.blocking_issues,
            "recommended_action": self.recommended_action,
            "generated_at": self.generated_at,
        }
