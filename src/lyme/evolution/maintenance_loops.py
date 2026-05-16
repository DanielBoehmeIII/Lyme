from __future__ import annotations

import ast
import difflib
import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .maintenance_detector import MaintenanceDetector, MaintenanceOpportunity, OpportunityCategory
from .maintenance_memory import MaintenanceMemory


class ApprovalStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class LoopOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class MaintenanceTask:
    opportunity: MaintenanceOpportunity
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    patch_content: str = ""
    patch_diff: str = ""
    reverse_diff: str = ""
    verification_result: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    approval_status: ApprovalStatus = ApprovalStatus.AUTO_APPROVED
    outcome: Optional[LoopOutcome] = None
    explanation: str = ""
    duration_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "opportunity": self.opportunity.to_dict(),
            "risk_level": self.risk_level,
            "approval_status": self.approval_status.value,
            "outcome": self.outcome.value if self.outcome else None,
            "explanation": self.explanation[:200],
            "duration_ms": round(self.duration_ms, 1),
            "verified": self.verification_result.get("passed", False) if self.verification_result else False,
        }


class AutonomousMaintenanceLoop:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.detector = MaintenanceDetector(repo_path)
        self.memory = MaintenanceMemory(repo_path)
        self.tasks: List[MaintenanceTask] = []
        self._loop_count = 0

    def run_loop(self, max_tasks: int = 1, require_approval_threshold: str = "high") -> List[MaintenanceTask]:
        self._loop_count += 1
        completed = []

        opportunities = self.detector.detect_all()
        opportunities = self._filter_safe_opportunities(opportunities)

        for opp in opportunities[:max_tasks]:
            task = self._execute_task(opp, require_approval_threshold)
            if task:
                completed.append(task)
                self.tasks.append(task)
                self.memory.remember_maintenance_event(task)

        return completed

    def _filter_safe_opportunities(self, opportunities: List[MaintenanceOpportunity]) -> List[MaintenanceOpportunity]:
        if not self.memory.entries:
            return opportunities

        fragile_files = self.memory.get_fragile_files()
        return [
            opp for opp in opportunities
            if not any(f in fragile_files for f in opp.target_files)
        ][:5]

    def _execute_task(self, opportunity: MaintenanceOpportunity, require_approval_threshold: str) -> Optional[MaintenanceTask]:
        task = MaintenanceTask(opportunity=opportunity)
        start = time.time()

        self._determine_risk(task, opportunity)
        if task.risk_level == require_approval_threshold:
            task.approval_status = ApprovalStatus.PENDING_APPROVAL
            task.outcome = LoopOutcome.REJECTED
            task.completed_at = time.time()
            return task

        task.explanation = self._generate_explanation(opportunity)
        patch = self._generate_patch(opportunity)
        if not patch:
            task.outcome = LoopOutcome.FAILED
            task.completed_at = time.time()
            return task

        task.patch_content = patch["content"]
        task.patch_diff = patch["diff"]
        task.reverse_diff = patch["reverse_diff"]

        applied = self._apply_patch(opportunity.target_files)
        if not applied:
            task.outcome = LoopOutcome.FAILED
            task.completed_at = time.time()
            return task

        verification = self._verify_patch()
        task.verification_result = verification

        if verification.get("passed"):
            self._commit_change(task)
            task.outcome = LoopOutcome.SUCCESS
        else:
            self._rollback(task)
            task.outcome = LoopOutcome.ROLLED_BACK

        task.duration_ms = (time.time() - start) * 1000
        task.completed_at = time.time()
        self._record_trace(task)
        return task

    def _determine_risk(self, task: MaintenanceTask, opportunity: MaintenanceOpportunity):
        if opportunity.risk > 0.3:
            task.risk_level = "high"
        elif opportunity.risk > 0.15:
            task.risk_level = "medium"
        else:
            task.risk_level = "low"

        if opportunity.opportunity_id in self.memory.entries:
            memory = self.memory.entries.get(opportunity.opportunity_id)
            if memory and memory.get("outcome") in ("failed", "rolled_back", "rejected"):
                task.risk_level = "high"

    def _generate_explanation(self, opportunity: MaintenanceOpportunity) -> str:
        parts = [
            f"Maintenance opportunity: {opportunity.title}",
            f"Category: {opportunity.category.value}",
            f"Value: {opportunity.value:.2f}, Risk: {opportunity.risk:.2f}, Effort: {opportunity.effort:.2f}",
            f"Confidence: {opportunity.confidence:.0%}",
            f"Evidence: {opportunity.evidence[:100]}",
        ]
        if opportunity.category == OpportunityCategory.CLEANUP:
            parts.append("Low-risk cleanup — removing clutter improves readability at minimal cost")
        elif opportunity.category == OpportunityCategory.WEAK_TEST:
            parts.append("Strengthening tests increases the safety net for future changes")
        elif opportunity.category == OpportunityCategory.DOCUMENTATION_GAP:
            parts.append("Documentation improvements reduce onboarding friction and clarify intent")
        elif opportunity.category == OpportunityCategory.REPEATED_CODE:
            parts.append("Consolidating repeated code reduces maintenance burden and inconsistency risk")

        return "\n".join(parts)

    def _generate_patch(self, opportunity: MaintenanceOpportunity) -> Optional[Dict[str, str]]:
        for file_path in opportunity.target_files[:1]:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                continue
            try:
                original = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            patched = self._apply_auto_fix(opportunity, original)
            if patched and patched != original:
                diff = "".join(difflib.unified_diff(
                    original.splitlines(keepends=True),
                    patched.splitlines(keepends=True),
                ))
                reverse = "".join(difflib.unified_diff(
                    patched.splitlines(keepends=True),
                    original.splitlines(keepends=True),
                ))
                return {"content": patched, "diff": diff, "reverse_diff": reverse}

        return None

    def _apply_auto_fix(self, opportunity: MaintenanceOpportunity, content: str) -> Optional[str]:
        if opportunity.category == OpportunityCategory.CLEANUP:
            if "Excessive 'pass'" in opportunity.title:
                lines = content.splitlines()
                cleaned = [l for l in lines if l.strip() != "pass" or True]
                return "\n".join(lines)
            if "Excessive blank lines" in opportunity.title:
                lines = content.splitlines()
                result = []
                blank_count = 0
                for l in lines:
                    if not l.strip():
                        blank_count += 1
                        if blank_count <= 2:
                            result.append(l)
                    else:
                        blank_count = 0
                        result.append(l)
                return "\n".join(result)

        if opportunity.category == OpportunityCategory.DOCUMENTATION_GAP:
            try:
                tree = ast.parse(content)
                modified = content
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("_"):
                            continue
                        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                            continue
                        has_doc = any(
                            isinstance(n, ast.Expr) and isinstance(n.value, ast.Str)
                            for n in node.body[:1]
                        )
                        if not has_doc:
                            indent = " " * 4
                            docstring = f'{indent}"""{node.name}"""\n'
                            func_text = ast.get_source_segment(content, node) or ""
                            new_func = func_text.replace(
                                f"def {node.name}(", f"def {node.name}(",
                            )
                            new_func_lines = new_func.splitlines()
                            if len(new_func_lines) >= 1:
                                insertion_line = new_func_lines[0] + "\n" + docstring
                                rest = "\n".join(new_func_lines[1:])
                                modified = modified.replace(func_text, insertion_line + rest)
                            break
                return modified if modified != content else None
            except SyntaxError:
                return None

        return None

    def _apply_patch(self, target_files: List[str]) -> bool:
        for task in reversed(self.tasks):
            if task.outcome == LoopOutcome.SUCCESS and task.patch_content:
                for f in target_files:
                    full_path = self.repo_path / f
                    if full_path.exists():
                        full_path.write_text(task.patch_content, encoding="utf-8")
                        return True
        return False

    def _verify_patch(self) -> Dict[str, Any]:
        result = {"passed": True, "checks": []}
        try:
            proc = subprocess.run(
                ["python", "-m", "py_compile"] + [str(f) for f in self.repo_path.rglob("*.py") if f.is_file() and "test" not in str(f)],
                capture_output=True, text=True, timeout=30,
            )
            syntax_ok = proc.returncode == 0
            result["checks"].append({"name": "syntax_check", "passed": syntax_ok})
            if not syntax_ok:
                result["passed"] = False
                result["errors"] = proc.stderr[-500:]
                return result

            proc = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "--no-header", "-q"],
                capture_output=True, text=True, timeout=60,
                cwd=self.repo_path,
            )
            tests_passed = proc.returncode == 0
            result["checks"].append({"name": "tests", "passed": tests_passed, "output": proc.stdout[-200:]})
            if not tests_passed:
                result["passed"] = False
                result["errors"] = proc.stdout[-500:]
        except Exception as e:
            result["passed"] = False
            result["errors"] = str(e)

        return result

    def _commit_change(self, task: MaintenanceTask):
        try:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            msg = f"lyme(auto-maintain): {task.opportunity.title[:80]}"
            subprocess.run(
                ["git", "commit", "-m", msg, "--no-verify"],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
        except Exception:
            pass

    def _rollback(self, task: MaintenanceTask):
        try:
            if task.reverse_diff:
                for f in task.opportunity.target_files:
                    full_path = self.repo_path / f
                    if full_path.exists():
                        original = full_path.read_text(encoding="utf-8", errors="replace")
                        patched = original
                        full_path.write_text(patched, encoding="utf-8")
            subprocess.run(
                ["git", "checkout", "--"] + task.opportunity.target_files,
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
        except Exception:
            pass

    def _record_trace(self, task: MaintenanceTask):
        trace_dir = self.repo_path / ".lyme" / "maintenance"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / f"{task.task_id}.json"
        path.write_text(json.dumps(task.to_dict(), indent=2, default=str))

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.tasks)
        successful = sum(1 for t in self.tasks if t.outcome == LoopOutcome.SUCCESS)
        failed = sum(1 for t in self.tasks if t.outcome in (LoopOutcome.FAILED, LoopOutcome.ROLLED_BACK))
        rejected = sum(1 for t in self.tasks if t.outcome == LoopOutcome.REJECTED)
        avg_duration = sum(t.duration_ms for t in self.tasks) / max(total, 1)

        return {
            "loop_count": self._loop_count,
            "total_tasks": total,
            "successful": successful,
            "failed": failed,
            "rejected": rejected,
            "success_rate": successful / max(total, 1) * 100,
            "avg_duration_ms": round(avg_duration, 1),
        }
