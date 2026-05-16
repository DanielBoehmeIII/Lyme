from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import time
import uuid


class AllowedAction(str, Enum):
    READ = "read"
    SUGGEST = "suggest"
    CREATE_PATCH = "create_patch"
    RUN_TESTS = "run_tests"
    MODIFY_FILES = "modify_files"
    OPEN_PR = "open_pr"
    ROLLBACK = "rollback"
    DEPLOY = "deploy"


class ApprovalRequirement(str, Enum):
    NEVER = "never"
    AUTO = "auto"
    REVIEW = "review"
    EXPLICIT = "explicit"
    BLOCKED = "blocked"


@dataclass
class ConstitutionZone:
    path_pattern: str
    allowed_actions: List[AllowedAction]
    approval_required: ApprovalRequirement
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "path_pattern": self.path_pattern,
            "allowed_actions": [a.value for a in self.allowed_actions],
            "approval_required": self.approval_required.value,
            "description": self.description,
        }

    def to_markdown(self) -> str:
        icons = {
            ApprovalRequirement.NEVER: "✅", ApprovalRequirement.AUTO: "⚡",
            ApprovalRequirement.REVIEW: "👀", ApprovalRequirement.EXPLICIT: "👤",
            ApprovalRequirement.BLOCKED: "🚫",
        }
        actions = ", ".join(a.value.replace("_", " ") for a in self.allowed_actions)
        return f"- {icons.get(self.approval_required, '•')} `{self.path_pattern}`: {actions} ({self.approval_required.value})"


@dataclass
class ArchitecturalRule:
    id: str
    description: str
    enforcement: str
    severity: str = "warning"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "enforcement": self.enforcement,
            "severity": self.severity,
        }


@dataclass
class TestingRequirement:
    pattern: str
    min_coverage: float
    required_tests: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "pattern": self.pattern,
            "min_coverage": self.min_coverage,
            "required_tests": self.required_tests,
            "description": self.description,
        }


@dataclass
class RepoConstitution:
    version: str = "1.0"
    repo_name: str = ""
    description: str = ""
    allowed_agent_actions: List[AllowedAction] = field(default_factory=lambda: list(AllowedAction))
    forbidden_zones: List[str] = field(default_factory=list)
    approval_requirements: Dict[str, ApprovalRequirement] = field(default_factory=dict)
    zones: List[ConstitutionZone] = field(default_factory=list)
    architectural_rules: List[ArchitecturalRule] = field(default_factory=list)
    testing_requirements: List[TestingRequirement] = field(default_factory=list)
    model_restrictions: List[str] = field(default_factory=list)
    privacy_constraints: List[str] = field(default_factory=list)
    deployment_protections: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "repo_name": self.repo_name,
            "description": self.description,
            "allowed_agent_actions": [a.value for a in self.allowed_agent_actions],
            "forbidden_zones": self.forbidden_zones,
            "approval_requirements": {k: v.value if isinstance(v, ApprovalRequirement) else v for k, v in self.approval_requirements.items()},
            "zones": [z.to_dict() for z in self.zones],
            "architectural_rules": [r.to_dict() for r in self.architectural_rules],
            "testing_requirements": [t.to_dict() for t in self.testing_requirements],
            "model_restrictions": self.model_restrictions,
            "privacy_constraints": self.privacy_constraints,
            "deployment_protections": self.deployment_protections,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Repo Constitution: {self.repo_name}")
        lines.append(f"")
        lines.append(f"**Version**: {self.version}")
        lines.append(f"**Description**: {self.description}")
        lines.append(f"")
        lines.append(f"## Allowed Agent Actions")
        for a in self.allowed_agent_actions:
            lines.append(f"- {a.value.replace('_', ' ').title()}")
        lines.append(f"")
        if self.forbidden_zones:
            lines.append(f"## Forbidden Zones")
            for z in self.forbidden_zones:
                lines.append(f"- 🚫 `{z}`")
            lines.append(f"")
        lines.append(f"## Zone Policies")
        for z in self.zones:
            lines.append(z.to_markdown())
        lines.append(f"")
        if self.architectural_rules:
            lines.append(f"## Architectural Rules")
            for r in self.architectural_rules:
                icon = "🔴" if r.severity == "error" else "🟡"
                lines.append(f"- {icon} **{r.id}**: {r.description}")
                lines.append(f"  - Enforcement: {r.enforcement}")
            lines.append(f"")
        if self.testing_requirements:
            lines.append(f"## Testing Requirements")
            for t in self.testing_requirements:
                lines.append(f"- `{t.pattern}`: {t.min_coverage:.0%} coverage")
                if t.required_tests:
                    for rt in t.required_tests:
                        lines.append(f"  - Required test: {rt}")
            lines.append(f"")
        if self.model_restrictions:
            lines.append(f"## Model Restrictions")
            for m in self.model_restrictions:
                lines.append(f"- {m}")
            lines.append(f"")
        if self.privacy_constraints:
            lines.append(f"## Privacy Constraints")
            for p in self.privacy_constraints:
                lines.append(f"- {p}")
            lines.append(f"")
        if self.deployment_protections:
            lines.append(f"## Deployment Protections")
            for d in self.deployment_protections:
                lines.append(f"- {d}")
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> RepoConstitution:
        path = Path(path)
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> RepoConstitution:
        return cls(
            version=data.get("version", "1.0"),
            repo_name=data.get("repo_name", ""),
            description=data.get("description", ""),
            allowed_agent_actions=[AllowedAction(a) for a in data.get("allowed_agent_actions", [])],
            forbidden_zones=data.get("forbidden_zones", []),
            approval_requirements={k: ApprovalRequirement(v) for k, v in data.get("approval_requirements", {}).items()},
            zones=[ConstitutionZone(
                path_pattern=z["path_pattern"],
                allowed_actions=[AllowedAction(a) for a in z["allowed_actions"]],
                approval_required=ApprovalRequirement(z["approval_required"]),
                description=z.get("description", ""),
            ) for z in data.get("zones", [])],
            architectural_rules=[ArchitecturalRule(**r) for r in data.get("architectural_rules", [])],
            testing_requirements=[TestingRequirement(**t) for t in data.get("testing_requirements", [])],
            model_restrictions=data.get("model_restrictions", []),
            privacy_constraints=data.get("privacy_constraints", []),
            deployment_protections=data.get("deployment_protections", []),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )

    @classmethod
    def create_default(cls, repo_name: str = "") -> RepoConstitution:
        return cls(
            repo_name=repo_name,
            description="Default Lyme repo constitution for safe autonomous software change",
            allowed_agent_actions=[
                AllowedAction.READ, AllowedAction.SUGGEST, AllowedAction.CREATE_PATCH,
                AllowedAction.RUN_TESTS, AllowedAction.MODIFY_FILES,
            ],
            forbidden_zones=[
                ".git/", ".env", "credentials.json", "secrets/",
                "node_modules/", "vendor/",
            ],
            approval_requirements={
                "deploy": ApprovalRequirement.EXPLICIT,
                "delete": ApprovalRequirement.EXPLICIT,
                "modify_secrets": ApprovalRequirement.BLOCKED,
                "modify_ci": ApprovalRequirement.REVIEW,
            },
            zones=[
                ConstitutionZone(
                    path_pattern="docs/**", description="Documentation",
                    allowed_actions=[AllowedAction.READ, AllowedAction.SUGGEST,
                                     AllowedAction.CREATE_PATCH, AllowedAction.MODIFY_FILES],
                    approval_required=ApprovalRequirement.AUTO,
                ),
                ConstitutionZone(
                    path_pattern="src/**", description="Source code",
                    allowed_actions=[AllowedAction.READ, AllowedAction.SUGGEST,
                                     AllowedAction.CREATE_PATCH, AllowedAction.RUN_TESTS,
                                     AllowedAction.MODIFY_FILES],
                    approval_required=ApprovalRequirement.AUTO,
                ),
                ConstitutionZone(
                    path_pattern="tests/**", description="Test files",
                    allowed_actions=[AllowedAction.READ, AllowedAction.SUGGEST,
                                     AllowedAction.CREATE_PATCH, AllowedAction.MODIFY_FILES],
                    approval_required=ApprovalRequirement.AUTO,
                ),
                ConstitutionZone(
                    path_pattern="config/**", description="Configuration",
                    allowed_actions=[AllowedAction.READ, AllowedAction.SUGGEST],
                    approval_required=ApprovalRequirement.REVIEW,
                ),
                ConstitutionZone(
                    path_pattern="deploy/**", description="Deployment",
                    allowed_actions=[AllowedAction.READ],
                    approval_required=ApprovalRequirement.EXPLICIT,
                ),
            ],
            architectural_rules=[
                ArchitecturalRule(id="arch_no_cycles", description="No circular dependencies between modules",
                                  enforcement="lint: import-linter", severity="error"),
                ArchitecturalRule(id="arch_test_separation", description="Tests must mirror src structure",
                                  enforcement="script: verify_test_structure.py", severity="warning"),
            ],
            testing_requirements=[
                TestingRequirement(pattern="src/**", min_coverage=0.8,
                                   required_tests=["unit"], description="Source code requires 80% coverage"),
            ],
            model_restrictions=["Do not use proprietary models for code review"],
            privacy_constraints=["Do not send code to external APIs without user consent"],
            deployment_protections=["Deploy requires two-person approval", "Production deploy blocked on test failures"],
            created_at=time.time(),
            updated_at=time.time(),
        )


class ConstitutionValidator:
    def __init__(self, constitution: RepoConstitution):
        self.constitution = constitution

    def validate(self) -> List[str]:
        issues: List[str] = []

        if not self.constitution.repo_name:
            issues.append("Constitution must specify a repo_name")

        if not self.constitution.allowed_agent_actions:
            issues.append("Constitution must define at least one allowed agent action")

        if self.constitution.version != "1.0":
            issues.append(f"Unknown constitution version: {self.constitution.version}")

        zone_patterns = [z.path_pattern for z in self.constitution.zones]
        if len(zone_patterns) != len(set(zone_patterns)):
            issues.append("Duplicate zone path patterns found")

        for z in self.constitution.zones:
            if not z.allowed_actions:
                issues.append(f"Zone '{z.path_pattern}' has no allowed actions")

        for ar in self.constitution.architectural_rules:
            if not ar.enforcement:
                issues.append(f"Architectural rule '{ar.id}' has no enforcement mechanism")

        for tr in self.constitution.testing_requirements:
            if not 0 <= tr.min_coverage <= 1:
                issues.append(f"Invalid coverage threshold for '{tr.pattern}': {tr.min_coverage}")

        if self.constitution.forbidden_zones:
            for z in self.constitution.forbidden_zones:
                if not z.endswith("/") and "." not in z:
                    issues.append(f"Forbidden zone '{z}' should be a path pattern (use trailing / for dirs)")

        return issues

    def validate_action(self, file_path: str, action: AllowedAction) -> Tuple[bool, str]:
        import fnmatch
        matching_zones = []
        for zone in self.constitution.zones:
            if fnmatch.fnmatch(file_path, zone.path_pattern):
                matching_zones.append(zone)

        if not matching_zones:
            return False, f"No zone matches path '{file_path}'. File may be in a forbidden area."

        for zone in matching_zones:
            if action not in zone.allowed_actions:
                return False, f"Action '{action.value}' not allowed in zone '{zone.path_pattern}'"

        for forbidden in self.constitution.forbidden_zones:
            if fnmatch.fnmatch(file_path, forbidden):
                return False, f"Path '{file_path}' is in a forbidden zone"

        return True, "Action permitted by constitution"

    def check_approval_needed(self, file_path: str) -> Optional[ApprovalRequirement]:
        import fnmatch
        for zone in sorted(self.constitution.zones, key=lambda z: -len(z.path_pattern)):
            if fnmatch.fnmatch(file_path, zone.path_pattern):
                return zone.approval_required
        return None

    def violation_report(self, file_paths: List[str], action: AllowedAction) -> List[Dict]:
        violations = []
        for fp in file_paths:
            allowed, reason = self.validate_action(fp, action)
            approval = self.check_approval_needed(fp)
            violations.append({
                "file_path": fp,
                "action": action.value,
                "allowed": allowed,
                "reason": reason,
                "approval_required": approval.value if approval else "unknown",
                "severity": "error" if not allowed else "info",
            })
        return violations


class ConstitutionEditor:
    def __init__(self, constitution: RepoConstitution):
        self.constitution = constitution

    def add_forbidden_zone(self, pattern: str) -> None:
        if pattern not in self.constitution.forbidden_zones:
            self.constitution.forbidden_zones.append(pattern)
            self.constitution.updated_at = time.time()

    def remove_forbidden_zone(self, pattern: str) -> bool:
        if pattern in self.constitution.forbidden_zones:
            self.constitution.forbidden_zones.remove(pattern)
            self.constitution.updated_at = time.time()
            return True
        return False

    def add_zone(self, zone: ConstitutionZone) -> None:
        self.constitution.zones = [z for z in self.constitution.zones if z.path_pattern != zone.path_pattern]
        self.constitution.zones.append(zone)
        self.constitution.updated_at = time.time()

    def remove_zone(self, path_pattern: str) -> bool:
        initial = len(self.constitution.zones)
        self.constitution.zones = [z for z in self.constitution.zones if z.path_pattern != path_pattern]
        self.constitution.updated_at = time.time()
        return len(self.constitution.zones) < initial

    def set_approval(self, action: str, level: ApprovalRequirement) -> None:
        self.constitution.approval_requirements[action] = level
        self.constitution.updated_at = time.time()

    def add_architectural_rule(self, rule: ArchitecturalRule) -> None:
        self.constitution.architectural_rules.append(rule)
        self.constitution.updated_at = time.time()

    def add_testing_requirement(self, req: TestingRequirement) -> None:
        self.constitution.testing_requirements.append(req)
        self.constitution.updated_at = time.time()

    def to_cli_output(self) -> str:
        lines = []
        lines.append("Repository Constitution Editor")
        lines.append("=" * 50)
        lines.append(f"Repo: {self.constitution.repo_name}")
        lines.append(f"Version: {self.constitution.version}")
        lines.append("")
        lines.append("Commands:")
        lines.append("  add-zone <pattern> <actions> <approval>  - Add/modify zone")
        lines.append("  remove-zone <pattern>                    - Remove zone")
        lines.append("  add-forbidden <pattern>                  - Add forbidden zone")
        lines.append("  remove-forbidden <pattern>               - Remove forbidden zone")
        lines.append("  set-approval <action> <level>            - Set approval requirement")
        lines.append("  add-rule <id> <desc> <enforcement>       - Add architectural rule")
        lines.append("  validate                                 - Validate constitution")
        lines.append("  view                                     - View constitution")
        lines.append("  save <path>                              - Save to file")
        lines.append("  help                                     - Show this help")
        return "\n".join(lines)
