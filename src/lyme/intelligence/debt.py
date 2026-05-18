from __future__ import annotations
import ast
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class DebtFinding:
    file_path: str
    line: int
    debt_type: str
    severity: str
    description: str
    code_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "debt_type": self.debt_type,
            "severity": self.severity,
            "description": self.description,
            "code_snippet": self.code_snippet[:200],
        }


@dataclass
class DebtReport:
    findings: List[DebtFinding] = field(default_factory=list)
    total_debt: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    debt_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "total_debt": self.total_debt,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "debt_types": dict(self.debt_types),
        }

    def to_markdown(self) -> str:
        if not self.findings:
            return "No technical debt detected."
        lines = [f"## Technical Debt Report\n"]
        lines.append(f"Found {self.total_debt} items ({self.critical_count} critical, {self.warning_count} warnings):\n")
        for dtype, count in sorted(self.debt_types.items(), key=lambda x: -x[1]):
            lines.append(f"- **{dtype}**: {count}")
        lines.append("")
        lines.append("### Top Items\n")
        for f in sorted(self.findings, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity, 3))[:10]:
            icon = "🔴" if f.severity == "critical" else "🟡" if f.severity == "warning" else "ℹ️"
            lines.append(f"{icon} {f.file_path}:{f.line} — {f.description}")
        return "\n".join(lines)


class TechnicalDebtAnalyzer:
    TODO_PATTERN = re.compile(r"(#|//|<!--)\s*(TODO|FIXME|HACK|XXX|TEMP|WORKAROUND)", re.IGNORECASE)
    LARGE_FUNCTION_THRESHOLD = 80
    HIGH_COMPLEXITY_THRESHOLD = 15

    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()

    def analyze(self, file_patterns: Optional[List[str]] = None) -> DebtReport:
        report = DebtReport()
        findings = []

        if file_patterns:
            files = []
            for pattern in file_patterns:
                files.extend(self._repo.rglob(pattern))
        else:
            files = list(self._repo.rglob("*.py"))
            files = [f for f in files if ".lyme" not in str(f) and ".git" not in str(f)
                     and "node_modules" not in str(f) and "__pycache__" not in str(f)]

        for f in files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            findings.extend(self._find_todos(f, content))
            findings.extend(self._find_large_functions(f, content))
            findings.extend(self._find_complex_functions(f, content))
            findings.extend(self._find_duplicate_code(f, content))
            findings.extend(self._find_missing_docs(f, content))

        report.findings = findings
        report.total_debt = len(findings)
        report.critical_count = sum(1 for f in findings if f.severity == "critical")
        report.warning_count = sum(1 for f in findings if f.severity == "warning")
        report.info_count = sum(1 for f in findings if f.severity == "info")
        debt_type_counts: Dict[str, int] = {}
        for f in findings:
            debt_type_counts[f.debt_type] = debt_type_counts.get(f.debt_type, 0) + 1
        report.debt_types = debt_type_counts
        return report

    def _find_todos(self, f: Path, content: str) -> List[DebtFinding]:
        findings = []
        for i, line in enumerate(content.splitlines(), 1):
            m = self.TODO_PATTERN.search(line)
            if m:
                keyword = m.group(2).upper()
                severity = "critical" if keyword in ("FIXME", "HACK") else "warning" if keyword == "TODO" else "info"
                findings.append(DebtFinding(
                    file_path=str(f),
                    line=i,
                    debt_type=f"{keyword}_comment",
                    severity=severity,
                    description=f"{keyword} comment: {line.strip()[:100]}",
                    code_snippet=line.strip(),
                ))
        return findings

    def _find_large_functions(self, f: Path, content: str) -> List[DebtFinding]:
        findings = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    line_count = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if line_count > self.LARGE_FUNCTION_THRESHOLD:
                        findings.append(DebtFinding(
                            file_path=str(f),
                            line=node.lineno,
                            debt_type="large_function",
                            severity="warning",
                            description=f"Large function '{node.name}' ({line_count} lines)",
                        ))
        except SyntaxError:
            pass
        return findings

    def _find_complex_functions(self, f: Path, content: str) -> List[DebtFinding]:
        findings = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._count_branches(node)
                    if complexity > self.HIGH_COMPLEXITY_THRESHOLD:
                        findings.append(DebtFinding(
                            file_path=str(f),
                            line=node.lineno,
                            debt_type="high_complexity",
                            severity="warning",
                            description=f"Complex function '{node.name}' (cyclomatic complexity: {complexity})",
                        ))
        except SyntaxError:
            pass
        return findings

    def _count_branches(self, node: ast.AST) -> int:
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try,
                                  ast.ExceptHandler, ast.With, ast.AsyncWith,
                                  ast.Assert, ast.BoolOp)):
                if isinstance(child, ast.BoolOp):
                    count += len(child.values) - 1
                else:
                    count += 1
        return count

    def _find_duplicate_code(self, f: Path, content: str) -> List[DebtFinding]:
        findings = []
        lines = content.splitlines()
        seen_blocks: Dict[str, int] = {}
        for i in range(len(lines) - 4):
            block = "\n".join(lines[i:i+5])
            if len(block.strip()) < 20:
                continue
            block_key = block.strip()[:80]
            if block_key in seen_blocks:
                if seen_blocks[block_key] != i:
                    findings.append(DebtFinding(
                        file_path=str(f),
                        line=i + 1,
                        debt_type="duplicate_code",
                        severity="info",
                        description=f"Possible duplicate (similar to line {seen_blocks[block_key] + 1})",
                        code_snippet=lines[i].strip()[:80],
                    ))
            else:
                seen_blocks[block_key] = i
        return findings

    def _find_missing_docs(self, f: Path, content: str) -> List[DebtFinding]:
        findings = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    has_docstring = (isinstance(node.body[0], ast.Expr)
                                     and isinstance(node.body[0].value, ast.Constant)
                                     and isinstance(node.body[0].value.value, str))
                    if node.name.startswith("test_") or node.name.startswith("_"):
                        continue
                    if not has_docstring and node.end_lineno - node.lineno > 20:
                        kind = "class" if isinstance(node, ast.ClassDef) else "function"
                        findings.append(DebtFinding(
                            file_path=str(f),
                            line=node.lineno,
                            debt_type="missing_docstring",
                            severity="info",
                            description=f"{kind.capitalize()} '{node.name}' missing docstring",
                        ))
        except SyntaxError:
            pass
        return findings
