"""Tests for Phase 11 Week 1 — Session Continuity."""
from __future__ import annotations
import json
import os
import time
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_isolated_session():
    import tempfile, os
    td = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    return td, old_cwd


def test_session_context_create():
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        sid = ctx.start(branch="main")
        assert sid is not None
        assert ctx.is_active()
        assert ctx.current_branch() == "main"
        summary = ctx.continuity_summary()
        assert summary["has_session"]
        assert summary["session_id"] == sid
        ctx.end()
    finally:
        os.chdir(old)


def test_session_context_goals():
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        ctx.start(branch="feature-x")
        goal = ctx.create_goal(
            description="Implement login feature",
            steps=["Create login form", "Add validation", "Connect to API"],
            branch="feature-x",
        )
        assert goal.id is not None
        assert goal.progress_pct() == 0.0
        assert ctx.active_goal() is not None
        ctx.complete_step("Create login form")
        assert ctx.active_goal().progress_pct() == 33.33333333333333
        ctx.complete_step("Add validation")
        assert ctx.active_goal().progress_pct() == 66.66666666666666
        ctx.complete_step("Connect to API")
        assert ctx.active_goal().progress_pct() == 100.0
        assert ctx.active_goal().status == "completed"
        ctx.end()
    finally:
        os.chdir(old)


def test_session_context_unfinished_goals():
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        ctx.start(branch="bugfix")
        ctx.create_goal("Fix memory leak", steps=["Reproduce", "Identify", "Fix"])
        ctx.complete_step("Reproduce")
        unfinished = ctx.unfinished_goals()
        assert len(unfinished) == 1
        assert unfinished[0].is_unfinished()
        ctx.end()
    finally:
        os.chdir(old)


def test_session_context_command_tracking():
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        ctx.start()
        ctx.record_command("lyme heal", duration_ms=1500, success=True)
        ctx.record_command("lyme test", duration_ms=800, success=False)
        recent = ctx.recent_commands(5)
        assert len(recent) == 2
        assert recent[0]["command"] == "lyme heal"
        assert recent[0]["success"] is True
        assert recent[1]["command"] == "lyme test"
        assert recent[1]["success"] is False
        ctx.end()
    finally:
        os.chdir(old)


def test_session_context_persistence():
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        ctx.start(branch="persist-test")
        ctx.create_goal("Persistent goal", steps=["Step 1"])
        ctx.complete_step("Step 1")
        # New instance should load same data
        ctx2 = SessionContext()
        assert ctx2.is_active()
        assert ctx2.current_branch() == "persist-test"
        goals = ctx2.all_goals()
        assert len(goals) == 1
        assert goals[0].status == "completed"
        ctx2.end()
    finally:
        os.chdir(old)


def test_session_recovery_detection():
    from lyme.session.context import SessionContext
    from lyme.session.recovery import SessionRecovery
    import tempfile
    import os
    td = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    try:
        ctx = SessionContext()
        ctx.start(branch="recovery-test")
        ctx.create_goal("Recoverable goal", steps=["Step A", "Step B"])
        ctx.complete_step("Step A")
        # Manually set updated_at to simulate idle time
        goal = ctx.active_goal()
        goal.updated_at = time.time() - 3600  # 1 hour ago
        ctx._session.goals = [g if g.id != goal.id else goal for g in ctx._session.goals]
        ctx._save_goal(goal)
        ctx._save()
        # Recovery detection
        recovery = SessionRecovery()
        interruption = recovery.detect_interruption()
        assert interruption is not None
        assert interruption["interrupted"] is True
        assert interruption["idle_minutes"] >= 59
        assert interruption["goal"]["description"] == "Recoverable goal"
        ctx.end()
    finally:
        os.chdir(old_cwd)


def test_session_timeline_events():
    from lyme.session.timeline import RepoTimeline
    import tempfile
    import os
    td = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    try:
        timeline = RepoTimeline()
        timeline.record_session_start(branch="main")
        timeline.record_goal_created("Test goal", branch="main")
        timeline.record_goal_completed("Test goal", branch="main")
        timeline.record_command("lyme test", branch="main")
        events = timeline.recent(10)
        assert len(events) == 4
        assert events[-4].event_type == "session_start"
        assert events[-3].event_type == "goal_created"
        summary = timeline.summary()
        assert summary["total_events"] == 4
        assert summary["goals_created"] == 1
        assert summary["goals_completed"] == 1
    finally:
        os.chdir(old_cwd)


def test_session_timeline_git_sync():
    from lyme.session.timeline import RepoTimeline
    import os
    td, old = _make_isolated_session()
    try:
        timeline = RepoTimeline()
        synced = timeline.sync_from_git()
        assert synced >= 0
    finally:
        os.chdir(old)


def test_session_timeline_filtering():
    from lyme.session.timeline import RepoTimeline
    import os
    td, old = _make_isolated_session()
    try:
        timeline = RepoTimeline()
        timeline.record_session_start(branch="main")
        timeline.record_session_start(branch="feature")
        main_events = timeline.events_on_branch("main")
        assert len(main_events) == 1
        assert all(e.branch == "main" for e in main_events)
    finally:
        os.chdir(old)


def test_continuer_detects_no_session():
    from lyme.dev_workflow.continuer import TaskContinuer
    from lyme.session.context import SessionContext
    import tempfile
    import os
    td = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(td)
    os.makedirs(".lyme/session")
    try:
        c = TaskContinuer()
        result = c.resume()
        assert result is not None
        assert "No active session" in result
    finally:
        os.chdir(old_cwd)


def test_continuer_resume_with_goal():
    from lyme.dev_workflow.continuer import TaskContinuer
    from lyme.session.context import SessionContext
    import os
    td, old = _make_isolated_session()
    try:
        ctx = SessionContext()
        ctx.start(branch="continue-test")
        ctx.create_goal("Continue test goal", steps=["Do X", "Do Y"])
        ctx.complete_step("Do X")
        c = TaskContinuer()
        result = c.resume()
        assert result is not None
        assert "Continue test goal" in result
        assert "Do Y" in result
        ctx.end()
    finally:
        os.chdir(old)


def test_cli_continue_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "continue", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "resume" in result.stdout or "--resume" in result.stdout


def test_cli_session_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "session", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "status" in result.stdout
    assert "start" in result.stdout
    assert "goal" in result.stdout
    assert "timeline" in result.stdout


def test_cli_session_start_end():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "session", "start"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "Session started" in result.stdout
    result2 = subprocess.run(
        [sys.executable, "-m", "lyme", "session", "end"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result2.returncode == 0
    assert "Session ended" in result2.stdout
