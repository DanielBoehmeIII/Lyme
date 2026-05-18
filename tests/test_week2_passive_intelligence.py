"""Tests for Phase 11 Week 2 — Passive Intelligence."""
from __future__ import annotations
import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_test_repo():
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/intel")
    os.makedirs(".lyme/session")
    subprocess.run(["git", "init"], capture_output=True, cwd=td)
    subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True, cwd=td)
    subprocess.run(["git", "config", "user.name", "Test"], capture_output=True, cwd=td)
    return td, old


# ── Architecture Drift ──

def test_drift_no_arch_file():
    from lyme.intelligence.drift import ArchitectureDriftDetector
    td, old = _make_test_repo()
    try:
        detector = ArchitectureDriftDetector()
        report = detector.detect()
        assert report.total_drift == 0
    finally:
        os.chdir(old)


def test_drift_missing_file():
    from lyme.intelligence.drift import ArchitectureDriftDetector
    td, old = _make_test_repo()
    try:
        arch = {
            "subsystems": [{
                "name": "core",
                "responsibilities": [{"owned_files": ["src/core/missing.py"]}],
            }],
            "boundary_rules": [],
            "invariants": [],
        }
        (Path(td) / ".lyme" / "architecture.json").write_text(json.dumps(arch))
        detector = ArchitectureDriftDetector()
        report = detector.detect()
        assert report.total_drift >= 1
        assert report.warning_count >= 1
        assert any("missing" in f.description for f in report.findings)
    finally:
        os.chdir(old)


def test_drift_report_format():
    from lyme.intelligence.drift import DriftReport, DriftFinding
    report = DriftReport()
    report.findings.append(DriftFinding(
        subsystem="test", drift_type="test", severity="critical",
        description="Test finding", expected="X", actual="Y",
    ))
    report.total_drift = 1
    report.critical_count = 1
    md = report.to_markdown()
    assert "Test finding" in md


# ── Technical Debt ──

def test_debt_todo_detection():
    from lyme.intelligence.debt import TechnicalDebtAnalyzer
    td, old = _make_test_repo()
    try:
        src = Path(td) / "src"
        src.mkdir()
        (src / "example.py").write_text(
            "# TODO: fix this later\n"
            "def foo():\n"
            "    pass\n"
            "# FIXME: this is broken\n"
            "def bar():\n"
            "    pass\n"
        )
        analyzer = TechnicalDebtAnalyzer()
        report = analyzer.analyze(file_patterns=["src/*.py"])
        assert report.total_debt >= 2
        types = report.debt_types
        assert any("TODO" in k for k in types) or any("FIXME" in k for k in types)
    finally:
        os.chdir(old)


def test_debt_large_function():
    from lyme.intelligence.debt import TechnicalDebtAnalyzer
    td, old = _make_test_repo()
    try:
        src = Path(td) / "src"
        src.mkdir()
        lines = ["def huge_function():"]
        for i in range(100):
            lines.append(f"    x = {i}")
        (src / "bigfunc.py").write_text("\n".join(lines))
        analyzer = TechnicalDebtAnalyzer()
        report = analyzer.analyze(file_patterns=["src/*.py"])
        assert report.total_debt >= 1
        assert any("huge_function" in f.description for f in report.findings)
    finally:
        os.chdir(old)


def test_debt_complex_function():
    from lyme.intelligence.debt import TechnicalDebtAnalyzer
    td, old = _make_test_repo()
    try:
        src = Path(td) / "src"
        src.mkdir()
        code = """def complex_func(x):
    if x > 0:
        for i in range(10):
            if i % 2 == 0:
                while i < 5:
                    try:
                        if x > 100:
                            pass
                    except:
                        pass
        return True
    return False
"""
        (src / "complex.py").write_text(code)
        analyzer = TechnicalDebtAnalyzer()
        report = analyzer.analyze(file_patterns=["src/*.py"])
        assert report.total_debt >= 0  # just verify it doesn't crash
    finally:
        os.chdir(old)


# ── Suspicious Commits ──

def test_suspicious_empty_repo():
    from lyme.intelligence.suspicious import SuspiciousCommitDetector
    td, old = _make_test_repo()
    try:
        detector = SuspiciousCommitDetector()
        report = detector.analyze(since_commits=10)
        assert report.commits_analyzed >= 0
        assert report.suspicious_count >= 0
    finally:
        os.chdir(old)


def test_suspicious_keyword_detection():
    from lyme.intelligence.suspicious import SuspiciousCommitDetector
    td, old = _make_test_repo()
    try:
        (Path(td) / "test.py").write_text("x = 1")
        subprocess.run(["git", "add", "."], capture_output=True, cwd=td)
        subprocess.run(["git", "commit", "-m", "TODO: fix this later"], capture_output=True, cwd=td)
        detector = SuspiciousCommitDetector()
        report = detector.analyze(since_commits=10)
        assert report.commits_analyzed >= 1
        has_keyword = any(f.finding_type == "suspicious_keyword" for f in report.findings)
        assert has_keyword
    finally:
        os.chdir(old)


# ── Flaky Tests ──

def test_flaky_no_tests():
    from lyme.intelligence.flaky import FlakyTestDetector
    td, old = _make_test_repo()
    try:
        detector = FlakyTestDetector()
        report = detector.analyze_existing()
        assert report.total_tests >= 0
    finally:
        os.chdir(old)


def test_flaky_report_format():
    from lyme.intelligence.flaky import FlakyTestResult
    r = FlakyTestResult(
        test_name="test_foo", file_path="test_foo.py",
        runs=10, passes=7, failures=3, flake_rate=0.3,
    )
    assert r.is_flaky()
    r2 = FlakyTestResult(
        test_name="test_bar", file_path="test_bar.py",
        runs=10, passes=10, failures=0,
    )
    assert not r2.is_flaky()


# ── Intelligence Engine ──

def test_intel_engine_all():
    from lyme.intelligence.engine import IntelligenceEngine
    td, old = _make_test_repo()
    try:
        engine = IntelligenceEngine()
        report = engine.run_all()
        assert report is not None
        assert report.warning_count >= 0
    finally:
        os.chdir(old)


def test_intel_engine_fast():
    from lyme.intelligence.engine import IntelligenceEngine
    td, old = _make_test_repo()
    try:
        engine = IntelligenceEngine()
        report = engine.run_fast()
        assert report is not None
    finally:
        os.chdir(old)


def test_intel_report_persistence():
    from lyme.intelligence.engine import IntelligenceEngine
    td, old = _make_test_repo()
    try:
        engine = IntelligenceEngine()
        engine.run_all()
        latest = engine.latest_report()
        assert latest is not None
        assert latest.warning_count >= 0
    finally:
        os.chdir(old)


# ── CLI commands ──

def test_cli_intel_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "intel", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "drift" in result.stdout or "all" in result.stdout


def test_cli_intel_status():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "intel", "status"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_intel_drift():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "intel", "drift"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
