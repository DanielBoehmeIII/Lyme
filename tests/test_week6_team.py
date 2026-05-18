"""Tests for Phase 11 Week 6 — Team Presence."""
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
    os.makedirs(".lyme/team")
    return td, old


def test_knowledge_store_retrieve():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.store("test_key", "test_value")
        assert kb.get("test_key") == "test_value"
    finally:
        os.chdir(old)


def test_knowledge_conventions():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.record_convention("naming", "snake_case", "Use snake_case for variables")
        convs = kb.conventions()
        assert len(convs) == 1
        assert convs[0]["name"] == "naming"
    finally:
        os.chdir(old)


def test_knowledge_standards():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.record_standard("layered_arch", "Strict layer separation", ["src/layers/"])
        stds = kb.standards()
        assert len(stds) == 1
        assert stds[0]["name"] == "layered_arch"
    finally:
        os.chdir(old)


def test_knowledge_facts():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.record_fact("ci", "Uses GitHub Actions for CI")
        facts = kb.facts()
        assert "ci" in facts
    finally:
        os.chdir(old)


def test_knowledge_list_keys():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.store("a", 1)
        kb.store("b", 2)
        keys = kb.list_keys()
        assert "a" in keys
        assert "b" in keys
    finally:
        os.chdir(old)


def test_knowledge_get_all():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb = TeamKnowledgeBase()
        kb.store("x", 10)
        all_data = kb.get_all()
        assert "x" in all_data
        assert all_data["x"] == 10
    finally:
        os.chdir(old)


def test_knowledge_persistence():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        kb1 = TeamKnowledgeBase()
        kb1.store("persist", "yes")
        kb2 = TeamKnowledgeBase()
        assert kb2.get("persist") == "yes"
    finally:
        os.chdir(old)


def test_onboarding_generates():
    from lyme.team.onboarding import RepoOnboarding
    td, old = _isolate()
    try:
        onboarding = RepoOnboarding()
        summary = onboarding.generate()
        assert summary.repo_name == Path(td).name
        assert len(summary.first_steps) >= 3
        md = summary.to_markdown()
        assert "Onboarding" in md
    finally:
        os.chdir(old)


def test_conventions_manager():
    from lyme.team.conventions import TeamConventions
    td, old = _isolate()
    try:
        conv = TeamConventions()
        conv.add_convention("testing", "pytest", "Use pytest for all tests")
        conv.add_standard("api", "RESTful API design", ["src/api/"])
        conv.add_fact("deploy", "Deploys via GitHub Actions")
        report = conv.report()
        assert "testing" in report
        assert "api" in report
        assert "deploy" in report
    finally:
        os.chdir(old)


def test_generate_summary():
    from lyme.team.knowledge import TeamKnowledgeBase
    td, old = _isolate()
    try:
        subprocess.run(["git", "init"], capture_output=True, cwd=td)
        subprocess.run(["git", "config", "user.email", "t@t.com"], capture_output=True, cwd=td)
        subprocess.run(["git", "config", "user.name", "T"], capture_output=True, cwd=td)
        Path(td, "README.md").write_text("# Test Repo")
        Path(td, "main.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], capture_output=True, cwd=td)
        subprocess.run(["git", "commit", "-m", "init"], capture_output=True, cwd=td)
        kb = TeamKnowledgeBase()
        summary = kb.generate_summary()
        assert summary.name == Path(td).name
        assert summary.total_files >= 2
    finally:
        os.chdir(old)


def test_cli_team_help():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "team", "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_team_summary():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "team", "summary"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0


def test_cli_team_onboard():
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "team", "onboard"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
