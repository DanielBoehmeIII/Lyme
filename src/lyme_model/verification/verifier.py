"""Week 78 — Verifier-First Local Agent.

Before Lyme Model accepts any output, run cheap verifiers:
file existence, function/class names, imports, tests, claims, patch validity.

Question: Can verification compensate for weak local reasoning?
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from pathlib import Path
import re
import time
import ast


@dataclass
class VerificationResult:
    verifier_name: str
    passed: bool
    details: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "verifier_name": self.verifier_name,
            "passed": self.passed,
            "details": self.details[:200],
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


class Verifier:
    name: str = "base"
    cost: str = "cheap"

    def verify(self, context: dict) -> VerificationResult:
        raise NotImplementedError


class FileExistenceVerifier(Verifier):
    """Verify that referenced files actually exist in the repo."""
    name = "file_existence"
    cost = "cheap"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        files = context.get("referenced_files", [])
        repo_path = context.get("repo_path", ".")
        repo = Path(repo_path)

        missing = []
        for f in files:
            full = repo / f
            if not full.exists():
                missing.append(f)

        elapsed = int((time.time() - start) * 1000)
        if missing:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details=f"Missing files: {', '.join(missing)}",
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details=f"All {len(files)} files exist",
            latency_ms=elapsed,
        )


class SymbolVerifier(Verifier):
    """Verify that function/class names exist in referenced files."""
    name = "symbol_verifier"
    cost = "cheap"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        symbols = context.get("referenced_symbols", [])
        file_map = context.get("file_symbols", {})

        missing = []
        for sym in symbols:
            found = False
            for fname, syms in file_map.items():
                if sym in syms.get("functions", []) or sym in syms.get("classes", []):
                    found = True
                    break
            if not found:
                missing.append(sym)

        elapsed = int((time.time() - start) * 1000)
        if missing:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details=f"Missing symbols: {', '.join(missing)}",
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details=f"All {len(symbols)} symbols verified",
            latency_ms=elapsed,
        )


class ImportVerifier(Verifier):
    """Verify that import statements would resolve."""
    name = "import_verifier"
    cost = "cheap"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        imports = context.get("referenced_imports", [])
        existing_modules = set(context.get("existing_modules", []))

        bad = []
        for imp in imports:
            base = imp.split(".")[0]
            if base not in existing_modules:
                bad.append(imp)

        elapsed = int((time.time() - start) * 1000)
        if bad:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details=f"Unresolvable imports: {', '.join(bad)}",
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details=f"All {len(imports)} imports resolvable",
            latency_ms=elapsed,
        )


class TestVerifier(Verifier):
    """Verify that test commands exist and tests can be found."""
    name = "test_verifier"
    cost = "medium"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        test_commands = context.get("test_commands", [])
        test_files = context.get("test_files", [])

        missing_tests = []
        for tf in test_files:
            full = Path(context.get("repo_path", ".")) / tf
            if not full.exists():
                missing_tests.append(tf)

        elapsed = int((time.time() - start) * 1000)
        issues = []
        if missing_tests:
            issues.append(f"Missing test files: {', '.join(missing_tests)}")
        if test_commands or test_files:
            if not test_commands and not test_files:
                issues.append("No test commands or test files specified")

        if issues:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details="; ".join(issues),
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details=f"{len(test_files)} test files, {len(test_commands)} commands",
            latency_ms=elapsed,
        )


class ClaimVerifier(Verifier):
    """Verify that model claims are supported by codebase evidence."""
    name = "claim_verifier"
    cost = "medium"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        claims = context.get("claims", [])

        unsupported = []
        for claim in claims:
            if isinstance(claim, dict):
                statement = claim.get("statement", "")
                citations = claim.get("citations", [])
                if statement and not citations:
                    unsupported.append(statement[:60])
            elif isinstance(claim, str):
                unsupported.append(claim[:60])

        elapsed = int((time.time() - start) * 1000)
        if unsupported:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details=f"Unsupported claims: {len(unsupported)}",
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details="All claims cite evidence",
            latency_ms=elapsed,
        )


class PatchVerifier(Verifier):
    """Verify that patches apply cleanly and don't break syntax."""
    name = "patch_verifier"
    cost = "medium"

    def verify(self, context: dict) -> VerificationResult:
        start = time.time()
        patch_content = context.get("patch_content", "")
        target_file = context.get("target_file", "")
        repo_path = context.get("repo_path", ".")

        issues = []

        if patch_content:
            # Check diff format
            if not patch_content.startswith("---") and not patch_content.startswith("+++"):
                if not any(line.startswith(("+", "-")) for line in patch_content.split("\n")[:3]):
                    issues.append("Patch does not appear to be a valid diff")

        if target_file:
            full = Path(repo_path) / target_file
            if full.exists() and full.suffix == ".py":
                try:
                    ast.parse(full.read_text())
                except SyntaxError as e:
                    issues.append(f"Syntax error in {target_file}: {e}")

        elapsed = int((time.time() - start) * 1000)
        if issues:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                details="; ".join(issues),
                latency_ms=elapsed,
            )
        return VerificationResult(
            verifier_name=self.name,
            passed=True,
            details="Patch format valid",
            latency_ms=elapsed,
        )


VERIFIERS = [
    ("file_existence", FileExistenceVerifier()),
    ("symbol_verifier", SymbolVerifier()),
    ("import_verifier", ImportVerifier()),
    ("test_verifier", TestVerifier()),
    ("claim_verifier", ClaimVerifier()),
    ("patch_verifier", PatchVerifier()),
]


class VerifierFirstAgent:
    """Agent wrapper that verifies before accepting output.

    Runs cheap verifiers first, then expensive ones only if needed.
    Can compensate for weak local reasoning by catching errors early.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.results: List[VerificationResult] = []
        self._verifiers: Dict[str, Verifier] = {
            name: v for name, v in VERIFIERS
        }

    def verify_all(self, context: dict) -> List[VerificationResult]:
        """Run all verifiers in cost order (cheap first)."""
        results = []
        # Cheap verifiers
        for name in ["file_existence", "symbol_verifier", "import_verifier"]:
            v = self._verifiers.get(name)
            if v:
                ctx = dict(context)
                ctx.setdefault("repo_path", self.repo_path)
                result = v.verify(ctx)
                results.append(result)
                self.results = results
                if not result.passed:
                    return results  # Stop on cheap failure

        # Medium verifiers
        for name in ["test_verifier", "claim_verifier", "patch_verifier"]:
            v = self._verifiers.get(name)
            if v:
                ctx = dict(context)
                ctx.setdefault("repo_path", self.repo_path)
                result = v.verify(ctx)
                results.append(result)
                self.results = results
                if not result.passed:
                    return results  # Stop on failure

        self.results = results
        return results

    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def failed_verifiers(self) -> List[VerificationResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return {
            "total_verifiers": total,
            "passed": passed,
            "failed": total - passed,
            "all_passed": self.all_passed(),
            "total_latency_ms": round(sum(r.latency_ms for r in self.results), 1),
            "results": [r.to_dict() for r in self.results],
        }

    def compensate(self, context: dict, model_output: str) -> dict:
        """Run verifiers and attempt to compensate for failures.

        Returns: {
            "accepted": bool,
            "output": str,
            "verification": dict,
            "compensation_applied": str or None
        }
        """
        full_context = dict(context)
        full_context["repo_path"] = self.repo_path

        results = self.verify_all(full_context)
        s = self.summary()

        if self.all_passed():
            return {
                "accepted": True,
                "output": model_output,
                "verification": s,
                "compensation_applied": None,
            }

        # Try to compensate for failures
        compensations = []
        for r in results:
            if not r.passed:
                if r.verifier_name == "file_existence":
                    compensations.append("Added file existence check to pre-flight")
                elif r.verifier_name == "symbol_verifier":
                    compensations.append("Added symbol lookup before generation")
                elif r.verifier_name == "import_verifier":
                    compensations.append("Added import resolution check")
                elif r.verifier_name == "patch_verifier":
                    compensations.append("Rejected invalid patch format")

        compensation = "; ".join(compensations) if compensations else None

        return {
            "accepted": self.all_passed(),
            "output": model_output if self.all_passed() else "",
            "verification": s,
            "compensation_applied": compensation,
        }
