"""Tests for Phase 11 Week 3 — Developer Rhythm Modeling."""
from __future__ import annotations
import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_isolated():
    td = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/rhythm")
    os.makedirs(".lyme/analytics/commands")
    os.makedirs(".lyme/session")
    return td, old


def test_analyzer_records_actions():
    from lyme.rhythm.analyzer import RhythmAnalyzer
    td, old = _make_isolated()
    try:
        analyzer = RhythmAnalyzer()
        analyzer.record_action("lyme heal")
        analyzer.record_action("lyme fix")
        seqs = analyzer.common_sequences()
        assert len(seqs) >= 1
    finally:
        os.chdir(old)


def test_analyzer_report():
    from lyme.rhythm.analyzer import RhythmAnalyzer
    td, old = _make_isolated()
    try:
        analyzer = RhythmAnalyzer()
        analyzer.record_action("lyme heal")
        analyzer.record_action("lyme fix")
        report = analyzer.analyze()
        assert report.total_commands >= 0
        assert report.most_used_commands is not None
        md = report.to_markdown()
        assert "Rhythm Report" in md
    finally:
        os.chdir(old)


def test_predictor_basic():
    from lyme.rhythm.predictor import CommandPredictor
    td, old = _make_isolated()
    try:
        predictor = CommandPredictor()
        predictor.record_command("lyme heal")
        predictor.record_command("lyme fix")
        predictor.record_command("lyme heal")
        predictions = predictor.predict_next()
        assert len(predictions) >= 1
    finally:
        os.chdir(old)


def test_predictor_context():
    from lyme.rhythm.predictor import CommandPredictor
    td, old = _make_isolated()
    try:
        predictor = CommandPredictor()
        preds = predictor.predict_for_context(context_hint="test failure")
        assert len(preds) >= 1
        assert "fix-latest" in preds[0].command or "heal" in preds[0].command
        preds2 = predictor.predict_for_context(context_hint="morning")
        assert any("start" in p.command for p in preds2)
    finally:
        os.chdir(old)


def test_predictor_persistence():
    from lyme.rhythm.predictor import CommandPredictor
    td, old = _make_isolated()
    try:
        predictor = CommandPredictor()
        predictor.record_command("lyme heal")
        predictor.record_command("lyme fix")
        # Verify state was saved
        state_path = Path(td) / ".lyme" / "rhythm" / "predictor.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert "transitions" in data
    finally:
        os.chdir(old)


def test_profiler_create():
    from lyme.rhythm.profiler import DeveloperProfiler
    td, old = _make_isolated()
    try:
        profiler = DeveloperProfiler()
        profile = profiler.get_or_create_profile()
        assert profile.persona == "general"
        md = profile.to_markdown()
        assert "Developer Profile" in md
    finally:
        os.chdir(old)


def test_profiler_update_from_report():
    from lyme.rhythm.profiler import DeveloperProfiler
    from lyme.rhythm.analyzer import RhythmReport
    td, old = _make_isolated()
    try:
        report = RhythmReport()
        report.most_used_commands = [("heal", 5), ("fix", 3)]
        report.avg_session_duration_min = 45.0
        report.interruption_rate = 0.1
        report.peak_hour = 14
        report.command_sequences = [("heal", "fix", 3)]
        report.total_commands = 8
        profiler = DeveloperProfiler()
        profile = profiler.update_from_report(report)
        assert profile.persona == "maintainer"
        assert profile.avg_session_length_min == 45.0
    finally:
        os.chdir(old)


def test_profiler_persistence():
    from lyme.rhythm.profiler import DeveloperProfiler
    td, old = _make_isolated()
    try:
        p1 = DeveloperProfiler()
        p1.get_or_create_profile()
        p2 = DeveloperProfiler()
        profile = p2.get_or_create_profile()
        assert profile.persona == "general"
    finally:
        os.chdir(old)


def test_cli_rhythm_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "rhythm", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_rhythm_predict():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "rhythm", "predict"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_rhythm_profile():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "rhythm", "profile"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_rhythm_sequences():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "rhythm", "sequences"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
