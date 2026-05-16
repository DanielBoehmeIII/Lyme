"""Week 138 — Critic Specialist.

Reviews:
- patch plan
- generated patch
- claims
- imports
- affected files
- verification completeness

Output: approve, reject, revise, ask_more_context, require_stronger_model, require_human
"""

from __future__ import annotations
from typing import Dict, List, Optional, Literal
from pathlib import Path
import re
import time

from .interfaces import CriticInput, CriticOutput, AuditTrace, FailureLabel


ISSUE_SEVERITY = Literal["info", "warning", "error", "critical"]


class CriticSpecialist:
    """Critic Specialist — reviews plans, patches, claims, and verification completeness."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._critique_history: List[dict] = []

    def process(self, inp: CriticInput) -> CriticOutput:
        trace = AuditTrace(specialist="critic", trace_id=f"crit-{int(time.time()*1000)}")
        trace.add_step("input_received", {
            "has_plan": inp.patch_plan is not None,
            "has_patch": inp.generated_patch is not None,
            "files": len(inp.affected_files),
            "claims": len(inp.claims),
            "imports": len(inp.imports),
        })

        issues: List[dict] = []
        revision_suggestions: List[str] = []
        missing_verification: List[str] = []

        # Step 1: Review patch plan
        if inp.patch_plan:
            plan_issues, plan_suggestions = self._review_plan(inp.patch_plan)
            issues.extend(plan_issues)
            revision_suggestions.extend(plan_suggestions)
            trace.add_step("plan_reviewed", {
                "issues_found": len(plan_issues),
                "suggestions": len(plan_suggestions),
            })

        # Step 2: Review generated patch
        if inp.generated_patch:
            patch_issues, patch_suggestions = self._review_patch(
                inp.generated_patch, inp.affected_files
            )
            issues.extend(patch_issues)
            revision_suggestions.extend(patch_suggestions)
            trace.add_step("patch_reviewed", {
                "issues_found": len(patch_issues),
            })

        # Step 3: Review claims
        if inp.claims:
            claim_issues = self._review_claims(inp.claims, inp.affected_files)
            issues.extend(claim_issues)
            trace.add_step("claims_reviewed", {
                "issues_found": len(claim_issues),
            })

        # Step 4: Review imports
        if inp.imports:
            import_issues = self._review_imports(inp.imports)
            issues.extend(import_issues)
            trace.add_step("imports_reviewed", {
                "issues_found": len(import_issues),
            })

        # Step 5: Review verification completeness
        if inp.verification_completeness:
            verif_issues, missing = self._review_verification(inp.verification_completeness)
            issues.extend(verif_issues)
            missing_verification.extend(missing)
            trace.add_step("verification_reviewed", {
                "issues_found": len(verif_issues),
                "missing": missing,
            })

        # Step 6: Determine decision
        decision = self._determine_decision(issues)
        trace.add_decision(
            decision,
            f"{len(issues)} issues found, {len(revision_suggestions)} suggestions, {len(missing_verification)} missing verifications",
            ["approve", "reject", "revise", "ask_more_context", "require_stronger_model", "require_human"],
        )

        # Step 7: Compute confidence
        confidence = self._compute_confidence(issues, missing_verification)

        trace.add_step("critique_complete", {
            "decision": decision,
            "total_issues": len(issues),
            "confidence": round(confidence, 3),
        })

        self._critique_history.append({
            "decision": decision,
            "issues": len(issues),
            "confidence": confidence,
        })

        return CriticOutput(
            decision=decision,
            issues=issues,
            revision_suggestions=revision_suggestions[:5],
            missing_verification=missing_verification,
            confidence=confidence,
            trace=trace,
        )

    def _review_plan(self, plan: dict) -> tuple:
        issues = []
        suggestions = []

        affected = plan.get("affected_files", [])
        if not affected:
            issues.append({
                "severity": "error",
                "file": "",
                "line": 0,
                "description": "Patch plan has no affected files",
            })

        intended = plan.get("intended_change", "")
        if not intended:
            issues.append({
                "severity": "error",
                "file": "",
                "line": 0,
                "description": "Patch plan has no intended change description",
            })
        elif len(intended) < 10:
            issues.append({
                "severity": "warning",
                "file": "",
                "line": 0,
                "description": "Intended change description is vague (< 10 chars)",
            })

        verification = plan.get("verification_command", "")
        if not verification:
            issues.append({
                "severity": "error",
                "file": "",
                "line": 0,
                "description": "No verification command in plan",
            })

        rollback = plan.get("rollback_path", "")
        if not rollback:
            issues.append({
                "severity": "warning",
                "file": "",
                "line": 0,
                "description": "No rollback path specified",
            })

        diff_shape = plan.get("expected_diff_shape", "")
        if not diff_shape:
            issues.append({
                "severity": "info",
                "file": "",
                "line": 0,
                "description": "No expected diff shape — cannot estimate patch size",
            })
            suggestions.append("Add expected diff shape (e.g. '+10/-5 lines, 2 functions modified')")

        for f in affected:
            full = Path(self.repo_path) / f
            if not full.exists():
                issues.append({
                    "severity": "error",
                    "file": f,
                    "line": 0,
                    "description": f"File does not exist: {f}",
                })

        return issues, suggestions

    def _review_patch(self, patch: str, affected_files: List[str]) -> tuple:
        issues = []

        if not patch or len(patch.strip()) < 10:
            issues.append({
                "severity": "error",
                "file": "",
                "line": 0,
                "description": "Patch is empty or too small",
            })
            return issues, []

        lines = patch.split("\n")
        has_diff_header = any(l.startswith("---") for l in lines) and any(l.startswith("+++") for l in lines)
        if not has_diff_header:
            issues.append({
                "severity": "warning",
                "file": "",
                "line": 0,
                "description": "Patch does not have standard diff headers (---/+++)",
            })

        added = [l for l in lines if l.startswith("+") and not l.startswith("+++")]
        removed = [l for l in lines if l.startswith("-") and not l.startswith("---")]

        if len(added) > 100:
            issues.append({
                "severity": "warning",
                "file": "",
                "line": 0,
                "description": f"Large patch: +{len(added)} lines — consider splitting",
            })

        if len(removed) > len(added) * 3:
            issues.append({
                "severity": "warning",
                "file": "",
                "line": 0,
                "description": f"High deletion ratio: -{len(removed)}/+{len(added)} — verify correctness",
            })

        for f in affected_files:
            if "test" in f and added:
                has_assert = any("assert" in l for l in added)
                if not has_assert:
                    issues.append({
                        "severity": "info",
                        "file": f,
                        "line": 0,
                        "description": "Modified test file but no new assertions detected",
                    })

        suggestions = []
        if len(issues) > 2:
            suggestions.append("Consider splitting patch into smaller logical changes")
        if not has_diff_header:
            suggestions.append("Add standard diff format headers")

        return issues, suggestions

    def _review_claims(self, claims: List[dict], files: List[str]) -> List[dict]:
        issues = []
        for i, claim in enumerate(claims):
            if isinstance(claim, dict):
                statement = claim.get("statement", "")
                citations = claim.get("citations", [])
                if statement and not citations:
                    issues.append({
                        "severity": "warning",
                        "file": "",
                        "line": 0,
                        "description": f"Claim #{i+1} has no citations: {statement[:60]}",
                    })
                if citations:
                    for c in citations:
                        if isinstance(c, str) and ":" in c:
                            file_part = c.split(":")[0]
                            full = Path(self.repo_path) / file_part
                            if not full.exists():
                                issues.append({
                                    "severity": "error",
                                    "file": file_part,
                                    "line": 0,
                                    "description": f"Citation references non-existent file: {file_part}",
                                })
        return issues

    def _review_imports(self, imports: List[str]) -> List[dict]:
        issues = []
        stdlib_modules = {"os", "sys", "json", "re", "math", "datetime", "pathlib",
                          "typing", "collections", "functools", "itertools", "uuid",
                          "hashlib", "base64", "subprocess", "tempfile", "shutil",
                          "copy", "enum", "dataclasses", "abc", "inspect", "textwrap"}

        for imp in imports:
            base = imp.split(".")[0] if "." in imp else imp
            if base not in stdlib_modules:
                full = Path(self.repo_path) / f"{base}.py"
                if not full.exists():
                    pkg = Path(self.repo_path) / base
                    if not pkg.exists() or not pkg.is_dir():
                        issues.append({
                            "severity": "warning",
                            "file": "",
                            "line": 0,
                            "description": f"Import may not resolve: {imp}",
                        })
        return issues

    def _review_verification(self, completeness: dict) -> tuple:
        issues = []
        missing = []

        required_checks = ["syntax_check", "file_existence", "test_run"]
        for check in required_checks:
            if check not in completeness:
                missing.append(check)
                issues.append({
                    "severity": "warning",
                    "file": "",
                    "line": 0,
                    "description": f"Missing required verification: {check}",
                })

        if completeness.get("planned_verifiers"):
            if len(completeness["planned_verifiers"]) < 2:
                issues.append({
                    "severity": "info",
                    "file": "",
                    "line": 0,
                    "description": "Only 1 verifier planned — consider adding more",
                })

        return issues, missing

    def _determine_decision(self, issues: List[dict]) -> str:
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        error_count = sum(1 for i in issues if i.get("severity") == "error")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        if critical_count > 0:
            return "require_human"
        if error_count >= 3:
            return "reject"
        if error_count > 0:
            return "revise"
        if warning_count >= 5:
            return "ask_more_context"
        if warning_count >= 3:
            return "require_stronger_model"
        return "approve"

    def _compute_confidence(self, issues: List[dict], missing_verification: List[str]) -> float:
        if not issues:
            return 0.92
        base = 0.85
        for i in issues:
            sev = i.get("severity", "info")
            if sev == "critical":
                base -= 0.3
            elif sev == "error":
                base -= 0.15
            elif sev == "warning":
                base -= 0.05
            else:
                base -= 0.02
        base -= len(missing_verification) * 0.05
        return max(0.05, min(0.99, base))

    def get_history(self) -> List[dict]:
        return self._critique_history

    def get_statistics(self) -> dict:
        if not self._critique_history:
            return {"total": 0}
        total = len(self._critique_history)
        approved = sum(1 for h in self._critique_history if h["decision"] == "approve")
        rejected = sum(1 for h in self._critique_history if h["decision"] == "reject")
        return {
            "total_critiques": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": approved / total if total > 0 else 0,
            "avg_issues_per_critique": sum(h["issues"] for h in self._critique_history) / total if total > 0 else 0,
            "avg_confidence": sum(h["confidence"] for h in self._critique_history) / total if total > 0 else 0,
        }


critic = CriticSpecialist()
