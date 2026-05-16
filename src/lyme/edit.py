"""Lyme Safe Edit Protocol — Trustworthy, auditable, reversible code edits.

Before editing: explain, identify, estimate risk, capture state, create patch.
After editing: show diff, run checks, report confidence, record trace.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import difflib
import json
import uuid
import os


class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EditIntent:
    description: str
    target_files: List[str]
    change_type: str
    estimated_risk: str = RiskLevel.MEDIUM
    rationale: str = ""
    affected_subsystems: List[str] = field(default_factory=list)
    required_tests: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "target_files": self.target_files,
            "change_type": self.change_type,
            "estimated_risk": self.estimated_risk,
            "rationale": self.rationale,
            "affected_subsystems": self.affected_subsystems,
            "required_tests": self.required_tests,
        }


@dataclass
class GitState:
    commit_hash: str
    branch: str
    has_uncommitted: bool
    dirty_files: List[str] = field(default_factory=list)
    diff_stat: str = ""

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit_hash,
            "branch": self.branch,
            "has_uncommitted": self.has_uncommitted,
            "dirty_files": self.dirty_files,
            "diff_stat": self.diff_stat,
        }


@dataclass
class ReversiblePatch:
    patch_id: str
    file_path: str
    original_content: str
    new_content: str
    patch_diff: str
    reverse_diff: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "patch_id": self.patch_id,
            "file_path": self.file_path,
            "original_content_length": len(self.original_content),
            "new_content_length": len(self.new_content),
            "patch_diff_length": len(self.patch_diff),
            "reverse_diff_length": len(self.reverse_diff),
            "created_at": self.created_at,
        }


@dataclass
class EditResult:
    success: bool
    applied_patches: List[ReversiblePatch] = field(default_factory=list)
    semantic_diff: dict = field(default_factory=dict)
    test_results: dict = field(default_factory=dict)
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    rollback_available: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "applied_patches": [p.to_dict() for p in self.applied_patches],
            "semantic_diff": self.semantic_diff,
            "test_results": self.test_results,
            "confidence": self.confidence,
            "errors": self.errors,
            "trace_id": self.trace_id,
            "warnings": self.warnings,
            "rollback_available": self.rollback_available,
        }


@dataclass
class SafeEditPlan:
    intent: EditIntent
    git_state: GitState
    patches: List[ReversiblePatch]
    pre_edit_checks: dict = field(default_factory=dict)
    test_strategy: List[str] = field(default_factory=list)
    rollback_path: str = ""
    estimated_success_probability: float = 0.0

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.to_dict(),
            "git_state": self.git_state.to_dict(),
            "patches": [p.to_dict() for p in self.patches],
            "pre_edit_checks": self.pre_edit_checks,
            "test_strategy": self.test_strategy,
            "rollback_path": self.rollback_path,
            "estimated_success_probability": self.estimated_success_probability,
        }


CHANGE_TYPES = [
    "bug_fix",
    "refactor",
    "feature_add",
    "dependency_update",
    "configuration_change",
    "documentation",
    "test_addition",
    "test_fix",
    "performance_optimization",
    "security_fix",
]

RISK_RULES = {
    "critical": [
        lambda f: f.endswith("auth.py") or f.endswith("security.py"),
        lambda f: f.endswith("config.py") or f.endswith("settings.py"),
        lambda f: "migration" in f or "schema" in f,
    ],
    "high": [
        lambda f: f.endswith("main.py") or f.endswith("app.py") or f.endswith("cli.py"),
        lambda f: "api" in f or "route" in f,
        lambda f: f.endswith("__init__.py"),
    ],
    "medium": [
        lambda f: f.endswith(".py") or f.endswith(".js") or f.endswith(".ts"),
        lambda f: "test" in f or "spec" in f,
    ],
    "low": [
        lambda f: f.endswith(".md") or f.endswith(".txt") or f.endswith(".rst"),
        lambda f: f.endswith(".json") or f.endswith(".yaml") or f.endswith(".yml"),
    ],
}


class SafeEditProtocol:
    """Safe, auditable, reversible code editing protocol."""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self._trace_id: Optional[str] = None

    def plan_edit(self, description: str, target_files: List[str],
                  change_type: str = "bug_fix",
                  rationale: str = "") -> SafeEditPlan:
        intent = EditIntent(
            description=description,
            target_files=target_files,
            change_type=change_type,
            rationale=rationale,
        )

        git_state = self._capture_git_state()

        risk = self._estimate_risk(target_files, change_type)
        intent.estimated_risk = risk

        patches = self._create_patches(target_files)

        affected = self._find_affected_subsystems(target_files)
        intent.affected_subsystems = affected

        test_strategy = self._decide_test_strategy(target_files, change_type)

        checks = self._pre_edit_checks(target_files, patches)

        success_prob = self._estimate_success(risk, git_state, len(patches))

        plan = SafeEditPlan(
            intent=intent,
            git_state=git_state,
            patches=patches,
            pre_edit_checks=checks,
            test_strategy=test_strategy,
            rollback_path=f"git checkout -- {' '.join(target_files)}",
            estimated_success_probability=success_prob,
        )

        return plan

    def _capture_git_state(self) -> GitState:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            commit_hash = result.stdout.strip()

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            branch = result.stdout.strip()

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            dirty_files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            has_uncommitted = len(dirty_files) > 0

            result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5,
            )
            diff_stat = result.stdout.strip()

            return GitState(
                commit_hash=commit_hash,
                branch=branch,
                has_uncommitted=has_uncommitted,
                dirty_files=dirty_files,
                diff_stat=diff_stat,
            )
        except Exception as e:
            return GitState(
                commit_hash="unknown",
                branch="unknown",
                has_uncommitted=False,
                dirty_files=[],
                diff_stat=f"Git unavailable: {e}",
            )

    def _estimate_risk(self, target_files: List[str],
                       change_type: str) -> str:
        for rule_list in [RISK_RULES["critical"], RISK_RULES["high"],
                          RISK_RULES["medium"]]:
            for rule in rule_list:
                for f in target_files:
                    if rule(f):
                        return RISK_RULES["critical"].index(rule) if rule in RISK_RULES["critical"] else \
                               RISK_RULES["high"].index(rule) if rule in RISK_RULES["high"] else \
                               RISK_RULES["medium"].index(rule) if rule in RISK_RULES["medium"] else None

        if change_type in ("security_fix", "dependency_update"):
            return RiskLevel.HIGH
        if change_type in ("bug_fix", "feature_add"):
            return RiskLevel.MEDIUM
        if change_type in ("documentation",):
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _estimate_risk(self, target_files: List[str],
                       change_type: str) -> str:
        for risk_level, rules in [
            (RiskLevel.CRITICAL, RISK_RULES["critical"]),
            (RiskLevel.HIGH, RISK_RULES["high"]),
            (RiskLevel.MEDIUM, RISK_RULES["medium"]),
        ]:
            for rule in rules:
                for f in target_files:
                    if rule(f):
                        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                            return risk_level

        if change_type in ("security_fix", "dependency_update"):
            return RiskLevel.HIGH
        if change_type in ("bug_fix", "feature_add"):
            return RiskLevel.MEDIUM
        if change_type in ("documentation",):
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _create_patches(self, target_files: List[str]) -> List[ReversiblePatch]:
        patches = []
        for file_path in target_files:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                continue
            try:
                original = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                original = ""

            patch = ReversiblePatch(
                patch_id=str(uuid.uuid4()),
                file_path=file_path,
                original_content=original,
                new_content=original,
                patch_diff="",
                reverse_diff="",
            )
            patches.append(patch)
        return patches

    def _find_affected_subsystems(self, target_files: List[str]) -> List[str]:
        subsystems = set()
        for f in target_files:
            parts = Path(f).parts
            if len(parts) > 1:
                subsystems.add(parts[0])
        return list(subsystems)

    def _decide_test_strategy(self, target_files: List[str],
                              change_type: str) -> List[str]:
        strategy = []
        if change_type in ("bug_fix", "security_fix", "feature_add"):
            strategy.append("Run tests for affected modules")
            strategy.append("Check type hints / static analysis")
        if change_type == "refactor":
            strategy.append("Run full test suite")
            strategy.append("Check for behavioral equivalence")
        if change_type == "dependency_update":
            strategy.append("Check import resolution")
            strategy.append("Run minimal smoke test")

        test_patterns = ["test", "spec", "tests"]
        for f in target_files:
            for pattern in test_patterns:
                if pattern in f:
                    strategy.append(f"Run tests in {f}")
                    break

        return strategy

    def _pre_edit_checks(self, target_files: List[str],
                         patches: List[ReversiblePatch]) -> dict:
        checks = {}
        for file_path in target_files:
            full_path = self.repo_path / file_path
            checks[file_path] = {
                "exists": full_path.exists(),
                "writable": os.access(full_path, os.W_OK) if full_path.exists() else False,
                "size_bytes": full_path.stat().st_size if full_path.exists() else 0,
            }
        return checks

    def _estimate_success(self, risk: str, git_state: GitState,
                          patch_count: int) -> float:
        base = 0.9
        if risk == RiskLevel.CRITICAL:
            base -= 0.3
        elif risk == RiskLevel.HIGH:
            base -= 0.15
        if git_state.has_uncommitted:
            base -= 0.1
        if patch_count > 3:
            base -= 0.05 * (patch_count - 3)
        return max(0.1, min(0.99, base))

    def apply_patch(self, plan: SafeEditPlan, file_path: str,
                    new_content: str) -> ReversiblePatch:
        for patch in plan.patches:
            if patch.file_path == file_path:
                old = patch.original_content
                patch.new_content = new_content
                patch.patch_diff = self._compute_diff(old, new_content)
                patch.reverse_diff = self._compute_diff(new_content, old)

                full_path = self.repo_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(new_content, encoding="utf-8")
                return patch
        raise ValueError(f"File {file_path} not in plan")

    def _compute_diff(self, old: str, new: str) -> str:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
        )
        return "".join(diff)

    def execute_edit(self, plan: SafeEditPlan,
                     file_patches: Dict[str, str]) -> EditResult:
        result = EditResult()
        result.trace_id = self._trace_id or str(uuid.uuid4())
        self._trace_id = result.trace_id

        errors = []

        for file_path, new_content in file_patches.items():
            try:
                patch = self.apply_patch(plan, file_path, new_content)
                result.applied_patches.append(patch)
            except Exception as e:
                errors.append(f"Failed to apply {file_path}: {e}")

        if errors:
            result.success = False
            result.errors = errors
            result.rollback_available = True
            return result

        result.semantic_diff = self._compute_semantic_diff(plan)

        result.test_results = self._run_relevant_checks(plan)

        result.success = len(result.errors) == 0
        result.rollback_available = all(
            p.reverse_diff for p in result.applied_patches
        )

        self._record_trace(plan, result)

        if result.success:
            self._store_memory(plan, result)

        return result

    def _compute_semantic_diff(self, plan: SafeEditPlan) -> dict:
        categories = {}
        for patch in plan.patches:
            if patch.patch_diff:
                lines_added = patch.patch_diff.count("\n+")
                lines_removed = patch.patch_diff.count("\n-")
                categories[patch.file_path] = {
                    "lines_added": lines_added,
                    "lines_removed": lines_removed,
                    "net_change": lines_added - lines_removed,
                    "patch_size": len(patch.patch_diff),
                }
        return {
            "total_files": len(categories),
            "total_added": sum(c["lines_added"] for c in categories.values()),
            "total_removed": sum(c["lines_removed"] for c in categories.values()),
            "files": categories,
        }

    def _run_relevant_checks(self, plan: SafeEditPlan) -> dict:
        results = {}
        for strategy in plan.test_strategy:
            results[strategy] = {"status": "pending", "note": "Manual review recommended"}

        if plan.intent.estimated_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            results["risk_review"] = {
                "status": "required",
                "note": f"High/critical risk edit requires human review",
            }

        return results

    def _record_trace(self, plan: SafeEditPlan, result: EditResult):
        trace = {
            "trace_id": result.trace_id,
            "action": "edit",
            "intent": plan.intent.to_dict(),
            "result": result.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        trace_dir = self.repo_path / ".lyme" / "edits"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"{result.trace_id}.json"
        trace_path.write_text(json.dumps(trace, indent=2, default=str))

    def _store_memory(self, plan: SafeEditPlan, result: EditResult):
        memory_dir = self.repo_path / ".lyme" / "memories"
        memory_dir.mkdir(parents=True, exist_ok=True)

        memory = {
            "type": "successful_edit",
            "description": plan.intent.description,
            "change_type": plan.intent.change_type,
            "files_changed": [p.file_path for p in result.applied_patches],
            "risk_level": plan.intent.estimated_risk,
            "confidence": result.confidence,
            "trace_id": result.trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        memory_path = memory_dir / f"{result.trace_id}.json"
        memory_path.write_text(json.dumps(memory, indent=2))

    def rollback(self, patch: ReversiblePatch) -> bool:
        try:
            full_path = self.repo_path / patch.file_path
            full_path.write_text(patch.original_content, encoding="utf-8")
            return True
        except Exception:
            return False

    def show_plan_summary(self, plan: SafeEditPlan) -> str:
        lines = []
        lines.append("═" * 50)
        lines.append(" SAFE EDIT PLAN")
        lines.append("═" * 50)
        lines.append(f"  Intent: {plan.intent.description}")
        lines.append(f"  Change type: {plan.intent.change_type}")
        lines.append(f"  Risk: {plan.intent.estimated_risk.upper()}")
        lines.append(f"  Success probability: {plan.estimated_success_probability:.0%}")
        lines.append("")
        lines.append("  Files:")
        for f in plan.intent.target_files:
            check = plan.pre_edit_checks.get(f, {})
            status = "✓" if check.get("exists") else "✗"
            lines.append(f"    {status} {f}")
        lines.append("")
        if plan.intent.affected_subsystems:
            lines.append(f"  Affected subsystems: {', '.join(plan.intent.affected_subsystems)}")
            lines.append("")
        lines.append("  Test strategy:")
        for s in plan.test_strategy:
            lines.append(f"    • {s}")
        lines.append("")
        lines.append(f"  Git state: {plan.git_state.branch} @ {plan.git_state.commit_hash[:8]}")
        if plan.git_state.has_uncommitted:
            lines.append(f"  ⚠ {len(plan.git_state.dirty_files)} uncommitted change(s)")
        lines.append("")
        lines.append(f"  Rollback: {plan.rollback_path}")
        lines.append("═" * 50)
        return "\n".join(lines)
