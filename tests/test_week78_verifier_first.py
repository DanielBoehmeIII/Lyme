"""Tests for Week 78 — Verifier-First Local Agent."""

import pytest
from src.lyme_model.verification.verifier import (
    VerificationResult,
    VerifierFirstAgent,
    FileExistenceVerifier,
    SymbolVerifier,
    ImportVerifier,
    TestVerifier,
    ClaimVerifier,
    PatchVerifier,
    VERIFIERS,
)


class TestVerifiers:
    def test_has_6_verifiers(self):
        assert len(VERIFIERS) == 6

    def test_file_existence_passes(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        v = FileExistenceVerifier()
        result = v.verify({"referenced_files": ["test.py"], "repo_path": str(tmp_path)})
        assert result.passed is True

    def test_file_existence_fails(self, tmp_path):
        v = FileExistenceVerifier()
        result = v.verify({"referenced_files": ["nonexistent.py"], "repo_path": str(tmp_path)})
        assert result.passed is False

    def test_symbol_verifier_passes(self):
        v = SymbolVerifier()
        result = v.verify({
            "referenced_symbols": ["main"],
            "file_symbols": {"test.py": {"functions": ["main"], "classes": []}},
        })
        assert result.passed is True

    def test_symbol_verifier_fails(self):
        v = SymbolVerifier()
        result = v.verify({
            "referenced_symbols": ["nonexistent"],
            "file_symbols": {"test.py": {"functions": ["main"], "classes": []}},
        })
        assert result.passed is False

    def test_import_verifier_passes(self):
        v = ImportVerifier()
        result = v.verify({
            "referenced_imports": ["os"],
            "existing_modules": ["os", "sys"],
        })
        assert result.passed is True

    def test_import_verifier_fails(self):
        v = ImportVerifier()
        result = v.verify({
            "referenced_imports": ["nonexistent_module"],
            "existing_modules": ["os", "sys"],
        })
        assert result.passed is False

    def test_claim_verifier_with_citations(self):
        v = ClaimVerifier()
        result = v.verify({
            "claims": [
                {"statement": "This function exists", "citations": ["file.py:10"]}
            ]
        })
        assert result.passed is True

    def test_claim_verifier_without_citations(self):
        v = ClaimVerifier()
        result = v.verify({
            "claims": [
                {"statement": "This function exists", "citations": []}
            ]
        })
        assert result.passed is False


class TestVerifierFirstAgent:
    def test_agent_initializes(self):
        agent = VerifierFirstAgent()
        assert len(agent._verifiers) == 6

    def test_verify_all_passes(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        results = agent.verify_all({
            "referenced_files": ["test.py"],
            "referenced_symbols": [],
            "file_symbols": {},
            "referenced_imports": [],
            "existing_modules": ["os"],
            "claims": [],
        })
        assert agent.all_passed() is True

    def test_verify_all_fails_on_missing_file(self, tmp_path):
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        results = agent.verify_all({
            "referenced_files": ["nonexistent.py"],
            "referenced_symbols": [],
            "file_symbols": {},
            "referenced_imports": [],
            "existing_modules": [],
            "claims": [],
        })
        assert agent.all_passed() is False
        assert len(results) > 0

    def test_failed_verifiers(self, tmp_path):
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        agent.verify_all({
            "referenced_files": ["missing.py"],
        })
        failed = agent.failed_verifiers()
        assert len(failed) >= 1

    def test_summary(self, tmp_path):
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        agent.verify_all({"referenced_files": ["missing.py"]})
        s = agent.summary()
        assert "total_verifiers" in s
        assert "passed" in s
        assert "failed" in s

    def test_compensate_accepts(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        result = agent.compensate(
            {"referenced_files": ["test.py"]},
            "model output",
        )
        assert result["accepted"] is True
        assert result["output"] == "model output"

    def test_compensate_rejects_missing_file(self, tmp_path):
        agent = VerifierFirstAgent(repo_path=str(tmp_path))
        result = agent.compensate(
            {"referenced_files": ["missing.py"]},
            "model output",
        )
        assert result["accepted"] is False
        assert result["output"] == ""
        assert result["compensation_applied"] is not None


class TestVerificationResult:
    def test_result_dataclass(self):
        r = VerificationResult(
            verifier_name="test",
            passed=True,
            details="All ok",
            latency_ms=1.0,
        )
        assert r.passed is True
        assert r.verifier_name == "test"

    def test_result_to_dict(self):
        r = VerificationResult(
            verifier_name="test", passed=False, details="fail", latency_ms=5.0,
        )
        d = r.to_dict()
        assert d["verifier_name"] == "test"
        assert d["passed"] is False
