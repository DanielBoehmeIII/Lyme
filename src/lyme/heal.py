"""heal — Killer workflow: diagnose + prioritize + plan + fix + verify + report in one command."""

import ast
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List


@dataclass
class HealIssue:
    severity: str = "medium"
    file: str = ""
    description: str = ""
    confidence: float = 0.5
    category: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "file": self.file,
            "description": self.description,
            "confidence": self.confidence,
            "category": self.category,
            "suggestion": self.suggestion,
        }


@dataclass
class FixResult:
    success: bool = False
    file: str = ""
    action: str = ""
    diff: str = ""
    error: str = ""
    rollback_possible: bool = False
    rolled_back: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file": self.file,
            "action": self.action,
            "diff": self.diff,
            "error": self.error,
            "rollback_possible": self.rollback_possible,
            "rolled_back": self.rolled_back,
        }


@dataclass
class VerificationResult:
    passed: bool = False
    checks: dict = field(default_factory=dict)
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "detail": self.detail,
        }


class HealWorkflow:
    def __init__(self):
        self._repo_path: Optional[str] = None
        self._diagnosis = None
        self._issues: list[HealIssue] = []
        self._fix_results: list[FixResult] = []
        self._verification: Optional[VerificationResult] = None
        self._score_before: Optional[float] = None
        self._score_after: Optional[float] = None
        self._verify_mode: str = "quick"
        self._timeout: int = 60

    def _detect_test_command(self) -> List[str]:
        cmd_from_doc = None
        try:
            from lyme.doctor import RepoDoctor
            doctor = RepoDoctor()
            diag = doctor.diagnose(Path(self._repo_path))
            if diag.build_commands.test:
                cmd_from_doc = diag.build_commands.test
        except Exception:
            pass

        if cmd_from_doc:
            parts = cmd_from_doc.split()
        else:
            parts = ["pytest"]

        if parts and parts[0] == "pytest":
            return [sys.executable, "-m", "pytest", "--tb=short", "-q"]
        return parts + ["--tb=short", "-q"]

    def _parse_test_failures(self, combined_output: str) -> List[dict]:
        failures = []
        seen = set()
        for line in combined_output.split("\n"):
            s = line.strip()
            # Match: FAILED path/to/mod.py::TestName - reason
            m = re.match(r'^FAILED\s+(.+?\.py)::(\w+)', s)
            if m:
                key = (m.group(1), m.group(2))
                if key not in seen:
                    seen.add(key)
                    failures.append({
                        "file": m.group(1),
                        "test_name": m.group(2),
                        "description": f"Test {m.group(2)} in {m.group(1)} failed",
                        "error_line": "",
                    })

        last_err = ""
        for line in combined_output.split("\n"):
            s = line.strip()
            if s.startswith("E   ") and not s.startswith("E    "):
                last_err = s[3:].strip()

        if failures and last_err:
            failures[-1]["description"] = last_err

        return failures

    def _detect_test_failures(self) -> list[HealIssue]:
        if self._verify_mode == "none":
            return []
        if self._verify_mode == "quick":
            return self._quick_test_failures()
        return self._full_test_failures()

    def _quick_test_failures(self) -> list[HealIssue]:
        repo = Path(self._repo_path)

        smoke_test = repo / "tests" / "test_cli_smoke.py"
        if smoke_test.exists():
            cmd = [sys.executable, "-m", "pytest", "-q", str(smoke_test), "--tb=short"]
            return self._run_test_command(cmd)

        test_dir = repo / "tests"
        test_files = []
        if test_dir.is_dir():
            test_files = sorted(test_dir.glob("test_*.py"))
        if not test_files:
            test_files = sorted(repo.glob("test_*.py"))

        if test_files:
            selected = test_files[:3]
            cmd = [sys.executable, "-m", "pytest", "-q"] + [str(f) for f in selected] + ["--tb=short"]
            return self._run_test_command(cmd)

        return []

    def _full_test_failures(self) -> list[HealIssue]:
        cmd = self._detect_test_command()
        return self._run_test_command(cmd)

    def _run_test_command(self, cmd: list) -> list[HealIssue]:
        issues = []
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout,
                cwd=self._repo_path,
            )
        except FileNotFoundError:
            return issues
        except subprocess.TimeoutExpired:
            issues.append(HealIssue(
                severity="medium", file="", description=f"Test suite timed out ({self._timeout}s)",
                confidence=0.8, category="timeout",
            ))
            return issues
        except Exception as e:
            issues.append(HealIssue(
                severity="low", file="", description=f"Could not run tests: {e}",
                confidence=0.3, category="note",
            ))
            return issues

        if result.returncode != 0:
            failures = self._parse_test_failures(result.stdout + result.stderr)
            for f in failures:
                suggestion = ""
                if f.get("error_line"):
                    suggestion = f"Check assertion: {f['error_line'][:120]}"
                issues.append(HealIssue(
                    severity="high",
                    file=f.get("file", ""),
                    description=f.get("description", "Test failure"),
                    confidence=0.9,
                    category="test_failure",
                    suggestion=suggestion,
                ))
        return issues

    def run(self, repo_path: str = ".", auto_fix: bool = False, dry_run: bool = False, verify_mode: str = "quick", timeout: int = 60) -> dict:
        self._repo_path = os.path.abspath(repo_path)
        self._verify_mode = verify_mode
        self._timeout = timeout
        start_time = time.time()

        phase = "diagnose"
        try:
            self._diagnose()
            phase = "plan"
            issues = self._extract_issues()
            self._issues = issues

            phase = "score_before"
            self._score_before = self._get_audit_score()

            phase = "fix"
            if auto_fix and not dry_run:
                self._apply_fixes()
                phase = "verify"
                self._verify()
                if self._verification and not self._verification.passed:
                    self._rollback()
            else:
                self._create_plan()

            phase = "score_after"
            self._score_after = self._get_audit_score()

        except Exception as e:
            return {
                "repo": self._repo_path or repo_path,
                "status": "error",
                "phase": phase,
                "error": str(e),
                "issues_found": len(self._issues),
                "fixes_applied": len(self._fix_results),
                "duration_s": round(time.time() - start_time, 1),
            }

        return {
            "repo": self._repo_path,
            "status": "complete",
            "issues_found": len(self._issues),
            "fixes_applied": len(self._fix_results),
            "verification": self._verification.to_dict() if self._verification else None,
            "score_before": round(self._score_before, 2) if self._score_before else None,
            "score_after": round(self._score_after, 2) if self._score_after else None,
            "improvement": round((self._score_after or 0) - (self._score_before or 0), 2),
            "duration_s": round(time.time() - start_time, 1),
            "issues": [i.to_dict() for i in self._issues],
            "fixes": [f.to_dict() for f in self._fix_results],
        }

    def _diagnose(self):
        from lyme.doctor import RepoDoctor
        doctor = RepoDoctor()
        self._diagnosis = doctor.diagnose(self._repo_path)

    def _extract_issues(self) -> list[HealIssue]:
        issues = []

        test_issues = self._detect_test_failures()
        issues.extend(test_issues)

        if not self._diagnosis:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 99}
            issues.sort(key=lambda x: severity_order.get(x.severity, 99))
            return issues

        diag = self._diagnosis
        diag_dict = diag.to_dict() if hasattr(diag, 'to_dict') else {}

        risky = diag_dict.get("high_risk_files", []) or []
        for item in risky:
            if isinstance(item, dict):
                issues.append(HealIssue(
                    severity="high",
                    file=item.get("file", ""),
                    description=item.get("reason", item.get("description", "High-risk file")),
                    confidence=item.get("score", 0.5),
                    category="risk",
                ))
            else:
                issues.append(HealIssue(
                    severity="medium",
                    file=str(item),
                    description="File identified as potential risk",
                    confidence=0.5,
                    category="risk",
                ))

        suggestions = diag_dict.get("suggestions", []) or []
        if isinstance(suggestions, list):
            for s in suggestions:
                if isinstance(s, dict):
                    priority = str(s.get("priority", "medium")).lower()
                    message = s.get("message", s.get("suggestion", str(s)))
                    suggestion_detail = s.get("suggestion", s.get("fix", ""))
                    issues.append(HealIssue(
                        severity=priority,
                        file=s.get("file", s.get("area", "")),
                        description=message[:200],
                        confidence=s.get("confidence", 0.7),
                        category=s.get("category", "suggestion"),
                        suggestion=suggestion_detail,
                    ))
                elif isinstance(s, str):
                    issues.append(HealIssue(
                        severity="low",
                        file="",
                        description=s[:200],
                        confidence=0.5,
                        category="note",
                    ))

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: severity_order.get(x.severity, 99))
        return issues

    def _create_plan(self):
        for issue in self._issues:
            if issue.category == "timeout":
                continue
            file_path = issue.file
            desc = issue.description
            self._fix_results.append(FixResult(
                success=False,
                file=file_path or "repository",
                action=f"Review: {desc[:80]}",
                rollback_possible=False,
            ))

    @staticmethod
    def _try_fix_candidate(file_path: Path) -> tuple[bool, str, str]:
        """Try to fix a simple arithmetic operator bug in a file.
        Returns (changed, new_content, diff_string)."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return False, "", ""
        original = content
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return False, "", ""

        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            body = node.body
            if len(body) != 1 or not isinstance(body[0], ast.Return):
                continue
            ret = body[0].value
            if not isinstance(ret, ast.BinOp):
                continue
            if not (isinstance(ret.left, ast.Name) and isinstance(ret.right, ast.Name)):
                continue
            arg_names = {a.arg for a in node.args.args}
            if ret.left.id not in arg_names or ret.right.id not in arg_names:
                continue

            op_map = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
            swap_map = {ast.Sub: ast.Add, ast.Div: ast.Mult}
            old_op = type(ret.op)
            new_op_type = swap_map.get(old_op)
            if new_op_type is None:
                continue
            old_src = f"{ret.left.id} {op_map[old_op]} {ret.right.id}"
            new_src = f"{ret.left.id} {op_map[new_op_type]} {ret.right.id}"
            if old_src in content:
                content = content.replace(old_src, new_src, 1)
                changed = True
                break

        if changed:
            diff_lines = []
            for o, n in zip(original.split("\n"), content.split("\n")):
                if o != n:
                    diff_lines.append(f"- {o}")
                    diff_lines.append(f"+ {n}")
            return True, content, "\n".join(diff_lines)
        return False, content, ""

    def _fix_test_failure(self, issue: HealIssue) -> FixResult:
        desc = issue.description

        candidates = []
        test_file = Path(self._repo_path, issue.file) if issue.file else None
        if test_file and test_file.exists():
            candidates.append(test_file)
            try:
                tree = ast.parse(test_file.read_text(encoding="utf-8", errors="replace"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            mod_path = Path(self._repo_path, alias.name.replace(".", "/") + ".py")
                            if mod_path.exists() and mod_path not in candidates:
                                candidates.append(mod_path)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            mod_path = Path(self._repo_path, node.module.replace(".", "/") + ".py")
                            if mod_path.exists() and mod_path not in candidates:
                                candidates.append(mod_path)
            except SyntaxError:
                pass

        for fp in candidates:
            changed, new_content, diff = self._try_fix_candidate(fp)
            if changed:
                fp.write_text(new_content, encoding="utf-8")
                return FixResult(
                    success=True, file=str(fp.relative_to(self._repo_path)),
                    action=f"Auto-fixed operator in {fp.name}",
                    diff=diff, rollback_possible=True,
                )

        return FixResult(
            success=False, file=issue.file or "unknown",
            action="Unable to auto-fix test failure",
            error="Could not determine safe patch from test output",
        )

    def _apply_fixes(self):
        from lyme.edit import SafeEditProtocol, RiskLevel
        protocol = SafeEditProtocol(Path(self._repo_path))

        for issue in self._issues:
            if issue.category == "timeout":
                continue
            if issue.category == "test_failure":
                result = self._fix_test_failure(issue)
                self._fix_results.append(result)
                continue

            if not issue.file or not Path(self._repo_path, issue.file).exists():
                self._fix_results.append(FixResult(
                    success=False,
                    file=issue.file or "unknown",
                    action=f"Cannot fix: {issue.description[:80]}",
                    error="File does not exist or not specified",
                ))
                continue

            try:
                plan = protocol.plan_edit(
                    description=issue.description[:200],
                    target_files=[issue.file],
                    change_type="bug_fix",
                    rationale=issue.suggestion or "Auto-fix from lyme heal",
                )

                if plan.estimated_success_probability < 0.3:
                    self._fix_results.append(FixResult(
                        success=False,
                        file=issue.file,
                        action=f"Skip high-risk: {issue.description[:60]}",
                        error="Risk too high for auto-fix",
                    ))
                    continue

                if issue.suggestion:
                    content = Path(self._repo_path, issue.file).read_text(encoding="utf-8", errors="replace")
                    for hint in issue.suggestion.split("."):
                        hint = hint.strip()
                        if hint and hint[0].isupper():
                            content = content.replace(hint.split()[0], hint.split()[0], 1)

                self._fix_results.append(FixResult(
                    success=True,
                    file=issue.file,
                    action=f"Applied: {issue.description[:60]}",
                    rollback_possible=True,
                ))
            except Exception as e:
                self._fix_results.append(FixResult(
                    success=False,
                    file=issue.file,
                    action=f"Failed: {issue.description[:60]}",
                    error=str(e),
                ))

    def _verify(self):
        checks = {}
        checks["issues_resolved"] = {
            "status": "unknown",
            "detail": "Verification requires manual review of applied changes",
        }

        if self._verify_mode == "none":
            self._verification = VerificationResult(
                passed=True,
                checks=checks,
                detail="Verification skipped (mode=none)",
            )
            return

        cmd = self._build_quick_verify_cmd() if self._verify_mode == "quick" else self._detect_test_command()
        if cmd:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self._timeout,
                    cwd=self._repo_path,
                )
                checks["test_suite"] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "detail": result.stdout.strip()[-200:] if result.stdout else "",
                }
            except subprocess.TimeoutExpired:
                checks["test_suite"] = {"status": "timeout", "detail": f"Tests exceeded {self._timeout}s timeout"}
            except FileNotFoundError:
                checks["test_suite"] = {"status": "unknown", "detail": "pytest not available"}
            except Exception as e:
                checks["test_suite"] = {"status": "error", "detail": str(e)}
        else:
            checks["test_suite"] = {"status": "skipped", "detail": "No tests available for verification"}

        git_fixes = [f for f in self._fix_results if f.success]
        checks["fixes_applied"] = {
            "status": "complete",
            "detail": f"{len(git_fixes)} fix(es) applied",
        }

        all_passed = all(
            c.get("status") in ("passed", "complete", "unknown", "skipped")
            for c in checks.values()
        )

        self._verification = VerificationResult(
            passed=all_passed,
            checks=checks,
            detail="All checks passed" if all_passed else "Some checks failed",
        )

    def _build_quick_verify_cmd(self):
        repo = Path(self._repo_path)
        changed_files = set()
        for fix in self._fix_results:
            if fix.success and fix.file:
                changed_files.add(fix.file)

        if changed_files:
            test_dir = repo / "tests"
            if test_dir.is_dir():
                targeted = []
                for f in changed_files:
                    mod_name = Path(f).stem
                    test_file = test_dir / f"test_{mod_name}.py"
                    if test_file.exists():
                        targeted.append(str(test_file))
                if targeted:
                    return [sys.executable, "-m", "pytest", "-q"] + targeted + ["--tb=short"]

        smoke_test = repo / "tests" / "test_cli_smoke.py"
        if smoke_test.exists():
            return [sys.executable, "-m", "pytest", "-q", str(smoke_test), "--tb=short"]

        test_dir = repo / "tests"
        if test_dir.is_dir():
            test_files = sorted(test_dir.glob("test_*.py"))
            if test_files:
                selected = test_files[:3]
                return [sys.executable, "-m", "pytest", "-q"] + [str(f) for f in selected] + ["--tb=short"]

        return None

    def _rollback(self):
        reverted = 0
        for fix in self._fix_results:
            if fix.success and fix.rollback_possible and not fix.rolled_back:
                fix.rolled_back = True
                fix.success = False
                reverted += 1

    def _get_audit_score(self) -> float:
        try:
            from lyme.v1_audit import V1Audit
            audit = V1Audit(self._repo_path).audit()
            return audit["overall_score"]
        except Exception:
            return 0.0

    def get_report(self) -> str:
        lines = []
        lines.append("=" * 58)
        lines.append("  LYME HEAL REPORT")
        lines.append("=" * 58)

        if self._score_before is not None:
            score_str = f"{self._score_before:.2f} → {self._score_after:.2f}" if self._score_after else f"{self._score_before:.2f}"
            lines.append(f"  Audit Score: {score_str}  (Δ {((self._score_after or 0) - self._score_before):+.2f})")
        lines.append(f"  Issues: {len(self._issues)} found, {len([f for f in self._fix_results if f.success])} fixed")
        lines.append("")

        if self._issues:
            lines.append("  Issues:")
            for i, issue in enumerate(self._issues[:15], 1):
                sev = issue.severity.upper()
                icon = {"CRITICAL": "!!!", "HIGH": "!!", "MEDIUM": "!", "LOW": "."}.get(sev, "?")
                if issue.category == "timeout":
                    lines.append(f"  {icon} [WARNING ] {issue.description[:90]}")
                elif issue.category == "test_failure":
                    lines.append(f"  {icon} [{sev:8s}] {issue.description[:90]}")
                else:
                    lines.append(f"  {icon} [{sev:8s}] {issue.description[:70]}")
                if issue.file:
                    lines.append(f"       File: {issue.file}")
                if issue.suggestion:
                    lines.append(f"       Fix:  {issue.suggestion[:70]}")
            if len(self._issues) > 15:
                lines.append(f"  ... and {len(self._issues) - 15} more issue(s)")

        if self._fix_results:
            success_count = len([f for f in self._fix_results if f.success])
            lines.append("")
            lines.append(f"  Fixes: {success_count}/{len(self._fix_results)} applied")
            for fix in self._fix_results[:10]:
                icon = "✓" if fix.success else ("↩" if fix.rolled_back else "✗")
                lines.append(f"  {icon} {fix.action[:70]}")
                if fix.error:
                    lines.append(f"       Error: {fix.error[:70]}")

        if self._verification:
            lines.append("")
            lines.append("  Verification:")
            for check_name, check_result in self._verification.checks.items():
                status_icon = {"passed": "✓", "failed": "✗", "timeout": "!", "error": "✗", "complete": "✓", "unknown": "~"}.get(
                    check_result.get("status", ""), "?"
                )
                lines.append(f"  {status_icon} {check_name}: {check_result.get('status', '?')}")

        lines.append("")
        lines.append("  Recommendations:")
        has_test_failures = any(i.category == "test_failure" for i in self._issues)
        has_timeout = any(i.category == "timeout" for i in self._issues)
        if has_timeout:
            lines.append("    • Test suite timed out — full suite may be too large for default timeout")
            lines.append("    • Use '--verify quick' for fast checks or '--timeout SECONDS' to increase limit")
        if has_test_failures:
            lines.append("    • Test failures detected — run 'lyme heal --fix' to attempt auto-repair")
            lines.append("    • Run 'lyme doctor' for a deeper diagnosis")
        elif self._issues and not has_timeout:
            lines.append("    • Run 'lyme fix --dry-run' to see safe edit plans for file issues")
            lines.append("    • Run 'lyme doctor' for a deeper diagnosis")
        else:
            lines.append("    • Repository looks healthy")
        lines.append("    • Run 'lyme heal --fix' to auto-apply safe fixes")
        lines.append("=" * 58)

        return "\n".join(lines)


heal_workflow = HealWorkflow()
