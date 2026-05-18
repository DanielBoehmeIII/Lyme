"""Tests for Phase 11 Week 8 — Dependence Test."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _isolate():
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/intel/reports", exist_ok=True)
    os.makedirs(".lyme/rhythm", exist_ok=True)
    os.makedirs(".lyme/session", exist_ok=True)
    os.makedirs(".lyme/analytics/commands", exist_ok=True)
    return td, old


def test_dependence_analyzer_runs():
    from lyme.dependence.analyzer import DependenceAnalyzer
    td, old = _isolate()
    try:
        analyzer = DependenceAnalyzer()
        report = analyzer.analyze()
        assert report.total_commands >= 0
        assert report.habit_score >= 0
    finally:
        os.chdir(old)


def test_dependence_analyzer_empty():
    from lyme.dependence.analyzer import DependenceAnalyzer
    td, old = _isolate()
    try:
        analyzer = DependenceAnalyzer()
        report = analyzer.analyze()
        assert report.total_commands == 0
        assert isinstance(report.sticky_features, list)
        assert isinstance(report.dependence_signals, list)
    finally:
        os.chdir(old)


def test_stickiness_report_format():
    from lyme.dependence.report import StickinessReport
    report = StickinessReport(
        total_commands=50,
        total_sessions=5,
        daily_active_users=10,
        commands_per_session=10.0,
        repeat_workflows=3,
        sessions_this_week=3,
        sessions_this_month=10,
        avg_session_length=30.0,
        return_rate=75.0,
        goal_completion_rate=80.0,
        unprompted_commands=8,
        habit_score=0.65,
    )
    d = report.to_dict()
    assert d["total_commands"] == 50
    assert d["habit_score"] == 0.65
    md = report.to_markdown()
    assert "Habit Score" in md
    assert "Verdict" in md
    assert "Roadmap" in md


def test_stickiness_report_low_score():
    from lyme.dependence.report import StickinessReport
    report = StickinessReport(habit_score=0.1)
    md = report.to_markdown()
    assert "Getting started" in md


def test_stickiness_report_high_score():
    from lyme.dependence.report import StickinessReport
    report = StickinessReport(
        habit_score=0.85,
        daily_active_users=50,
        sessions_this_week=7,
        sessions_this_month=30,
        repeat_workflows=15,
        unprompted_commands=25,
        total_commands=500,
    )
    md = report.to_markdown()
    assert "habit-forming" in md or "cognition" in md


def test_stickiness_habit_score_calculation():
    from lyme.dependence.report import StickinessReport
    report = StickinessReport(
        daily_active_users=100,
        repeat_workflows=20,
        return_rate=90.0,
        goal_completion_rate=80.0,
        sessions_this_week=7,
        sessions_this_month=30,
        unprompted_commands=30,
    )
    report.sticky_features = [
        {"feature": "heal", "usage_count": 10, "category": "repair", "stickiness": "high"},
        {"feature": "start", "usage_count": 8, "category": "workflow", "stickiness": "high"},
        {"feature": "session", "usage_count": 6, "category": "workflow", "stickiness": "high"},
    ]
    from lyme.dependence.analyzer import DependenceAnalyzer
    analyzer = DependenceAnalyzer()
    score = analyzer._calculate_habit_score(report)
    assert score > 0
    assert score <= 1.0


def test_cli_stickiness():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "stickiness"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "Habit Score" in result.stdout or "stickiness" in result.stdout
