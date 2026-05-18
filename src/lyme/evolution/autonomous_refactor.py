"""AutonomousRefactor — safe automated refactoring engine."""
from __future__ import annotations
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class RefactorPlan:
    name: str = ""
    description: str = ""
    operations: List[Dict[str, Any]] = field(default_factory=list)
    risk_level: str = "medium"
    estimated_safety: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "operations": len(self.operations),
            "risk_level": self.risk_level,
            "safety": round(self.estimated_safety, 4),
        }


@dataclass
class RefactorResult:
    success: bool = False
    files_changed: List[str] = field(default_factory=list)
    diff: str = ""
    safety_check_passed: bool = False
    tests_passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "files_changed": self.files_changed,
            "safety_check": self.safety_check_passed,
            "tests_passed": self.tests_passed,
            "error": self.error,
        }


class AutonomousRefactor:
    def __init__(self, repo_path: str = ".", test_fn: Optional[Callable] = None):
        self.repo_path = Path(repo_path).resolve()
        self._test_fn = test_fn

    def plan_rename(self, old_name: str, new_name: str, file_path: Optional[str] = None) -> RefactorPlan:
        plan = RefactorPlan(
            name=f"Rename {old_name} -> {new_name}",
            description=f"Rename symbol '{old_name}' to '{new_name}'",
            risk_level="high",
            estimated_safety=0.5,
        )
        plan.operations.append({
            "type": "rename",
            "old_name": old_name,
            "new_name": new_name,
            "file_path": file_path or "",
        })
        return plan

    def plan_extract(self, source_file: str, target_file: str, symbols: List[str]) -> RefactorPlan:
        plan = RefactorPlan(
            name=f"Extract {len(symbols)} symbols",
            description=f"Extract symbols from {source_file} to {target_file}",
            risk_level="high",
            estimated_safety=0.4,
        )
        plan.operations.append({
            "type": "extract",
            "source": source_file,
            "target": target_file,
            "symbols": symbols,
        })
        return plan

    def execute(self, plan: RefactorPlan) -> RefactorResult:
        result = RefactorResult()
        diffs = []

        for op in plan.operations:
            if op.get("type") == "rename":
                r = self._execute_rename(op)
                result.files_changed.extend(r.get("files", []))
                if r.get("diff"):
                    diffs.append(r["diff"])

        result.diff = "\n".join(diffs)
        result.success = len(result.files_changed) > 0
        return result

    def _execute_rename(self, op: Dict[str, Any]) -> Dict[str, Any]:
        old_name = op["old_name"]
        new_name = op["new_name"]
        file_path = op.get("file_path", "")
        files_changed = []
        diffs = []

        search_path = Path(file_path) if file_path else self.repo_path
        pattern = f"*.py" if not file_path else file_path

        for f in self.repo_path.rglob(pattern):
            if not f.is_file() or ".git" in f.parts:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                if old_name in content:
                    new_content = content.replace(old_name, new_name)
                    diff = difflib.unified_diff(
                        content.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=str(f), tofile=str(f),
                    )
                    f.write_text(new_content)
                    files_changed.append(str(f.relative_to(self.repo_path)))
                    diffs.append("".join(diff))
            except Exception:
                continue

        return {"files": files_changed, "diff": "\n".join(diffs)}
