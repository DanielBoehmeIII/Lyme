"""Tests for Phase 11 Week 7 — Personal ROI Engine."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_impact_engine_calculates():
    from lyme.impact.engine import ImpactEngine
    td, old = _temp_isolate()
    try:
        engine = ImpactEngine()
        metrics = engine.calculate()
        assert metrics.commands_run >= 0
        assert metrics.estimated_time_saved_min >= 0
        assert metrics.estimated_cost_saved >= 0
    finally:
        os.chdir(old)


def test_impact_engine_generates_report():
    from lyme.impact.engine import ImpactEngine
    td, old = _temp_isolate()
    try:
        engine = ImpactEngine()
        report = engine.generate_report()
        assert report.metrics is not None
        assert report.generated_at > 0
    finally:
        os.chdir(old)


def test_impact_report_format():
    from lyme.impact.engine import ImpactEngine
    td, old = _temp_isolate()
    try:
        engine = ImpactEngine()
        report = engine.generate_report()
        md = report.to_markdown()
        assert "Impact Report" in md
        assert "ROI" in md or "Savings" in md
        assert "Lyme" in md
    finally:
        os.chdir(old)


def test_impact_metrics_values():
    from lyme.impact.engine import PersonalMetrics
    m = PersonalMetrics(
        total_commands=100,
        commands_automated=30,
        sessions_completed=5,
        goals_completed=3,
        total_warnings_generated=10,
        suspicious_commits_caught=2,
        estimated_time_saved_min=120,
        estimated_cost_saved=200.0,
        commands_run=100,
        uptime_days=7.0,
    )
    d = m.to_dict()
    assert d["total_commands"] == 100
    assert d["estimated_time_saved_min"] == 120
    assert d["estimated_cost_saved"] == 200.0


def test_cli_impact():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "impact"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def _temp_isolate():
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/intel/reports", exist_ok=True)
    os.makedirs(".lyme/rhythm", exist_ok=True)
    os.makedirs(".lyme/session", exist_ok=True)
    return td, old
