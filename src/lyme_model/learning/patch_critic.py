"""Week 87 — Patch Critic Model.

Before applying a patch, evaluate:
- syntax risk
- missing imports
- wrong file
- likely test failure
- architectural mismatch
- hallucinated symbols
- over-broad change
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
import ast


@dataclass
class CriticVerdict:
    approved: bool = False
    risks: List[str] = field(default_factory=list)
    blocked_reasons: List[str] = field(default_factory=list)
    confidence: float = 0.0
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "risks": self.risks[:5],
            "blocked_reasons": self.blocked_reasons[:5],
            "confidence": round(self.confidence, 4),
            "latency_ms": round(self.latency_ms, 1),
        }


class PatchCritic:
    """Evaluates patches before application to prevent failures.

    Can be:
    - Local small model (rule-based)
    - Static analyzer
    - Rules engine
    - Hybrid
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.verdicts: List[CriticVerdict] = []
        self.false_rejections = 0
        self.prevented_failures = 0

    def evaluate(self, patch_content: str, target_file: str,
                 context: Optional[dict] = None) -> CriticVerdict:
        """Evaluate a patch and return a verdict."""
        import time
        start = time.time()
        risks = []
        blocked = []
        ctx = context or {}

        # 1. Syntax risk (strip diff prefixes and headers before parsing)
        if target_file.endswith(".py"):
            clean_lines = []
            for line in patch_content.split("\n"):
                stripped = line[1:] if line.startswith(("+", "-")) else line
                if stripped.startswith(("--- ", "+++ ", "@@", "diff ", "index ")):
                    continue
                clean_lines.append(stripped)
            clean_content = "\n".join(clean_lines)
            try:
                ast.parse(clean_content)
            except SyntaxError as e:
                risks.append(f"Syntax risk: {e}")
                blocked.append(f"Patch contains invalid Python syntax: {e}")

        # 2. Missing imports check
        new_imports = re.findall(r'^\+.*(?:import|from)\s+(\w+)', patch_content, re.MULTILINE)
        if new_imports:
            existing_file = self.repo_path / target_file
            if existing_file.exists():
                existing_text = existing_file.read_text(errors="ignore")
                for imp in new_imports:
                    if imp not in existing_text:
                        risks.append(f"New import '{imp}' not found in file context")

        # 3. Wrong file check
        task_files = ctx.get("task_files", [])
        if task_files and target_file not in task_files:
            risks.append(f"Target file '{target_file}' not in expected task files")
            blocked.append(f"Patch targets '{target_file}' but task expects {task_files}")

        # 4. Likely test failure
        test_patterns = ctx.get("test_patterns", {})
        for pattern, expected in test_patterns.items():
            if pattern in patch_content and expected not in patch_content:
                risks.append(f"Patch may break test assertion for '{pattern}'")

        # 5. Architectural mismatch
        arch_rules = ctx.get("architectural_rules", [])
        if arch_rules:
            for rule in arch_rules:
                rule_lower = rule.lower()
                if "never" in rule_lower:
                    # Check if patch violates a "never" rule
                    violation_part = rule.split("never")[-1].strip()
                    if violation_part and violation_part in patch_content.lower():
                        risks.append(f"Architectural: {rule}")

        # 6. Hallucinated symbols
        known_symbols = set(ctx.get("known_symbols", []))
        builtins = {"if", "for", "while", "with", "def", "class",
                     "print", "return", "yield", "assert", "raise", "pass",
                     "break", "continue", "self", "cls", "super", "lambda",
                     "len", "range", "int", "str", "list", "dict", "set",
                     "tuple", "bool", "float", "open", "isinstance", "hasattr",
                     "getattr", "setattr", "type", "is", "in", "not", "and", "or",
                     "True", "False", "None", "Exception", "ValueError", "TypeError",
                     "KeyError", "IndexError", "ImportError", "AttributeError", "OSError",
                     "FileNotFoundError", "RuntimeError", "StopIteration"}
        new_symbols = re.findall(r'^\+.*\b([a-z_][a-z_0-9]*)\s*\(', patch_content, re.MULTILINE)
        for sym in new_symbols:
            if sym not in builtins:
                if known_symbols and sym not in known_symbols:
                    risks.append(f"Unknown symbol '{sym}' — possible hallucination")

        # 7. Over-broad change
        added_lines = len(re.findall(r'^\+', patch_content, re.MULTILINE))
        removed_lines = len(re.findall(r'^-', patch_content, re.MULTILINE))
        if added_lines > 50:
            risks.append(f"Large addition: +{added_lines} lines, consider splitting")
        if removed_lines > 30:
            risks.append(f"Large removal: -{removed_lines} lines, verify intent")

        elapsed = int((time.time() - start) * 1000)
        approved = len(blocked) == 0
        confidence = 0.9 if approved else 0.95

        verdict = CriticVerdict(
            approved=approved,
            risks=risks,
            blocked_reasons=blocked,
            confidence=confidence,
            latency_ms=elapsed,
        )
        self.verdicts.append(verdict)

        if not approved:
            self.prevented_failures += 1
        elif risks:
            pass  # Warned but not blocked
        else:
            pass

        return verdict

    def stats(self) -> Dict:
        total = len(self.verdicts)
        approved = sum(1 for v in self.verdicts if v.approved)
        return {
            "total_evaluations": total,
            "approved": approved,
            "blocked": total - approved,
            "prevented_failures": self.prevented_failures,
            "false_rejections": self.false_rejections,
        }
