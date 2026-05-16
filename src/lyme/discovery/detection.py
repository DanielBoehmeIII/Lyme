from __future__ import annotations

import ast
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .invariant import (
    Invariant, InvariantSet, InvariantType, InvariantSeverity,
    Violation, Contradiction,
)


class ViolationDetector:
    def detect(self, repo_path: Path, inv_set: InvariantSet) -> List[Violation]:
        violations: List[Violation] = []

        for inv in inv_set._invariants.values():
            if inv.invariant_type == InvariantType.LAYER_VIOLATION:
                violations.extend(self._check_layer_violation(repo_path, inv))
            elif inv.invariant_type == InvariantType.AUTH_REQUIRED:
                violations.extend(self._check_auth_required(repo_path, inv))
            elif inv.invariant_type == InvariantType.RESOURCE_CLEANUP:
                violations.extend(self._check_resource_cleanup(repo_path, inv))
            elif inv.invariant_type == InvariantType.STATELESS_REQUIREMENT:
                violations.extend(self._check_stateless(repo_path, inv))
            elif inv.invariant_type == InvariantType.API_CONTRACT:
                violations.extend(self._check_api_contract(repo_path, inv))
            elif inv.invariant_type == InvariantType.CONFIG_SCHEMA:
                violations.extend(self._check_config_schema(repo_path, inv))
            elif inv.invariant_type == InvariantType.ERROR_HANDLING:
                violations.extend(self._check_error_handling(repo_path, inv))

        return violations

    def _check_layer_violation(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except Exception:
            return violations

        forbidden_imports = []
        if "controllers" in inv.scope and "models" in inv.rule:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "models" in node.module:
                    forbidden_imports.append(node.module)
        elif "services" in inv.scope and "controllers" in inv.rule:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "controllers" in node.module:
                    forbidden_imports.append(node.module)

        for imp in forbidden_imports[:5]:
            violations.append(Violation(
                invariant_id=inv.id,
                invariant_name=inv.name,
                file_path=inv.scope,
                description=f"Layer violation: imports '{imp}'",
                severity=InvariantSeverity.MEDIUM,
                confidence=0.6,
                context=f"import {imp} in {inv.scope}",
            ))
        return violations

    def _check_auth_required(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except Exception:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_auth = False
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    if dec_name in ("login_required", "permission_required", "authenticated"):
                        has_auth = True
                        break
                if not has_auth and not node.name.startswith("_") and node.name != "__init__":
                    if any(kw in node.name.lower() for kw in ("admin", "delete", "update", "create", "post")):
                        violations.append(Violation(
                            invariant_id=inv.id,
                            invariant_name=inv.name,
                            file_path=inv.scope,
                            line_number=node.lineno or 0,
                            description=f"Missing auth decorator on '{node.name}'",
                            severity=InvariantSeverity.HIGH,
                            confidence=0.4,
                            context=f"function {node.name} at {inv.scope}:{node.lineno}",
                        ))
        return violations[:10]

    def _check_resource_cleanup(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return violations

        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "open(" in line and "with" not in line:
                violations.append(Violation(
                    invariant_id=inv.id,
                    invariant_name=inv.name,
                    file_path=inv.scope,
                    line_number=i + 1,
                    description="File opened without context manager",
                    severity=InvariantSeverity.HIGH,
                    confidence=0.4,
                    context=line.strip()[:80],
                ))
        return violations[:5]

    def _check_stateless(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except Exception:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for sub in ast.walk(item):
                            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                                if sub.value.id == "self" and sub.attr not in ("__init__", "config", "logger"):
                                    violations.append(Violation(
                                        invariant_id=inv.id,
                                        invariant_name=inv.name,
                                        file_path=inv.scope,
                                        line_number=item.lineno or 0,
                                        description=f"State mutation detected: self.{sub.attr}",
                                        severity=InvariantSeverity.LOW,
                                        confidence=0.3,
                                        context=f"self.{sub.attr} in {item.name}",
                                    ))
        return violations[:10]

    def _check_api_contract(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        return violations

    def _check_config_schema(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return violations

        urls = re.findall(r'https?://[^\s"\'\)]+', text)
        for url in urls[:5]:
            if "localhost" in url or "127.0.0.1" in url:
                continue
            if "{" not in url and "%s" not in url:
                violations.append(Violation(
                    invariant_id=inv.id,
                    invariant_name=inv.name,
                    file_path=inv.scope,
                    description=f"Hardcoded URL detected: {url[:60]}",
                    severity=InvariantSeverity.MEDIUM,
                    confidence=0.6,
                    context=url[:80],
                ))
        return violations[:5]

    def _check_error_handling(self, repo_path: Path, inv: Invariant) -> List[Violation]:
        violations = []
        if not inv.scope:
            return violations
        f_path = repo_path / inv.scope
        if not f_path.exists():
            return violations
        try:
            text = f_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except Exception:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        violations.append(Violation(
                            invariant_id=inv.id,
                            invariant_name=inv.name,
                            file_path=inv.scope,
                            line_number=handler.lineno or 0,
                            description="Bare except clause",
                            severity=InvariantSeverity.MEDIUM,
                            confidence=0.7,
                            context="except: without exception type",
                        ))
        return violations[:5]


class ContradictionDetector:
    def detect(self, inv_set: InvariantSet) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        invariants = list(inv_set._invariants.values())

        for i in range(len(invariants)):
            for j in range(i + 1, len(invariants)):
                a = invariants[i]
                b = invariants[j]

                if a.scope == b.scope:
                    if a.invariant_type == InvariantType.STATELESS_REQUIREMENT and \
                       b.invariant_type == InvariantType.TRANSACTION_BOUNDARY:
                        contradictions.append(Contradiction(
                            invariant_a_id=a.id,
                            invariant_a_name=a.name,
                            invariant_b_id=b.id,
                            invariant_b_name=b.name,
                            description=f"'{a.name}' requires stateless but '{b.name}' requires transaction state",
                            conflict_type="stateful_vs_stateless",
                            severity=InvariantSeverity.MEDIUM,
                        ))

                    if a.invariant_type == InvariantType.RESOURCE_CLEANUP and \
                       b.invariant_type == InvariantType.PERFORMANCE_BUDGET:
                        if "sleep" in b.description and a.severity == InvariantSeverity.HIGH:
                            pass

                keywords_a = set(a.name.lower().split())
                keywords_b = set(b.name.lower().split())
                shared = keywords_a & keywords_b
                contradictions_found = self._check_semantic_contradiction(a, b)
                contradictions.extend(contradictions_found)

        return contradictions[:20]

    def _check_semantic_contradiction(
        self, a: Invariant, b: Invariant
    ) -> List[Contradiction]:
        contradictions = []

        opposite_pairs = [
            ("must be stateless", "requires state"),
            ("should not", "must"),
            ("avoid", "requires"),
            ("read-only", "write"),
            ("immutable", "mutable"),
        ]

        a_lower = a.description.lower()
        b_lower = b.description.lower()

        for opp_a, opp_b in opposite_pairs:
            if (opp_a in a_lower and opp_b in b_lower) or \
               (opp_b in a_lower and opp_a in b_lower):
                contradictions.append(Contradiction(
                    invariant_a_id=a.id,
                    invariant_a_name=a.name,
                    invariant_b_id=b.id,
                    invariant_b_name=b.name,
                    description=f"Semantic contradiction: '{a.name}' conflicts with '{b.name}'",
                    conflict_type="semantic_opposition",
                    severity=InvariantSeverity.HIGH,
                    resolution="Review both invariants and determine which takes priority",
                ))
                break

        return contradictions


class EvolutionTracker:
    def __init__(self):
        self._snapshots: List[Dict[str, Any]] = []

    def snapshot(self, inv_set: InvariantSet) -> Dict[str, Any]:
        snap = {
            "timestamp": time.time(),
            "total_invariants": len(inv_set._invariants),
            "total_violations": len(inv_set._violations),
            "by_type": {
                t.value: len(inv_set.get_by_type(t))
                for t in InvariantType
            },
            "by_severity": {
                s.value: len(inv_set.get_by_severity(s))
                for s in InvariantSeverity
            },
            "high_severity_violations": sum(
                1 for v in inv_set._violations.values()
                if v.severity in (InvariantSeverity.CRITICAL, InvariantSeverity.HIGH)
            ),
        }
        self._snapshots.append(snap)
        return snap

    def get_trend(self, metric: str = "total_violations") -> List[float]:
        return [s.get(metric, 0) for s in self._snapshots]

    def estimate_fragility(self, inv_set: InvariantSet) -> Dict[str, float]:
        if not inv_set._invariants:
            return {"fragility_score": 0.0}

        high_severity = len(inv_set.get_by_severity(InvariantSeverity.CRITICAL)) + \
                        len(inv_set.get_by_severity(InvariantSeverity.HIGH))
        contradictions = len(inv_set._contradictions)
        violations = len(
            [v for v in inv_set._violations.values()
             if v.severity in (InvariantSeverity.CRITICAL, InvariantSeverity.HIGH)]
        )

        total = len(inv_set._invariants)
        fragility = (
            (high_severity / max(total, 1)) * 0.3 +
            min(1.0, contradictions / max(total, 1)) * 0.3 +
            min(1.0, violations / max(total * 2, 1)) * 0.4
        )

        return {
            "fragility_score": min(1.0, fragility),
            "high_severity_ratio": high_severity / max(total, 1),
            "contradiction_ratio": contradictions / max(total, 1),
            "violation_ratio": violations / max(total, 1),
        }
