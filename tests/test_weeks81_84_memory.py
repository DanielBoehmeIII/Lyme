"""Tests for Weeks 81-84 — Memory, Corruption, Adaptation, Transfer."""

import pytest
from datetime import datetime, timezone, timedelta
from src.lyme_model.memory.coding_memory import (
    CodingMemory, MemoryEntry, MemoryType, MemoryStore,
)
from src.lyme_model.memory.corruption import CorruptionDetector, MemoryAuditReport
from src.lyme_model.memory.repo_adaptation import RepoAdaptationEngine, RepoProfile
from src.lyme_model.memory.transfer import (
    CrossRepoTransferExperiment, TransferTrial, TRANSFER_POLICIES,
)


class TestWeek81CodingMemory:
    def test_memory_entry_creation(self):
        entry = MemoryEntry(
            memory_id="test_001",
            memory_type=MemoryType.SUCCESSFUL_PATCH,
            content="Fixed login bug",
        )
        assert entry.memory_id == "test_001"
        assert entry.memory_type == MemoryType.SUCCESSFUL_PATCH
        assert entry.confidence == 1.0

    def test_memory_expiry(self):
        entry = MemoryEntry(
            memory_id="test_002",
            memory_type=MemoryType.TEST_COMMAND,
            content="pytest",
            expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        )
        assert entry.is_expired() is True

    def test_memory_not_expired(self):
        entry = MemoryEntry(
            memory_id="test_003",
            memory_type=MemoryType.TEST_COMMAND,
            content="pytest",
            expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        assert entry.is_expired() is False

    def test_memory_no_expiry(self):
        entry = MemoryEntry(
            memory_id="test_004",
            memory_type=MemoryType.TEST_COMMAND,
            content="pytest",
        )
        assert entry.is_expired() is False

    def test_memory_store_add_and_get(self):
        store = MemoryStore()
        entry = MemoryEntry(
            memory_id="test_005",
            memory_type=MemoryType.REPO_CONVENTION,
            content="Use snake_case",
        )
        store.add(entry)
        retrieved = store.get("test_005")
        assert retrieved is not None
        assert retrieved.access_count == 1

    def test_memory_store_query_by_type(self):
        store = MemoryStore()
        store.add(MemoryEntry(memory_id="a", memory_type=MemoryType.TEST_COMMAND, content="pytest"))
        store.add(MemoryEntry(memory_id="b", memory_type=MemoryType.FAILED_PATCH, content="error"))
        results = store.query(memory_type=MemoryType.TEST_COMMAND)
        assert len(results) == 1
        assert results[0].memory_id == "a"

    def test_coding_memory_all_types(self):
        cm = CodingMemory()
        cm.remember_convention("Use snake_case", repo="test-repo")
        cm.remember_successful_patch("main.py", "Added validation")
        cm.remember_failed_patch("auth.py", "ImportError")
        cm.remember_test_command("pytest tests/")
        cm.remember_fragile_file("config.py", "Contains secrets")
        cm.remember_recurring_error("ImportError", "missing module")
        cm.remember_user_preference("Use type hints")
        cm.remember_model_weakness("Hallucinates APIs", model="deepseek-6.7b")
        assert cm.store.count() == 8

    def test_coding_memory_getters(self):
        cm = CodingMemory()
        cm.remember_test_command("pytest", project="my-repo")
        cm.remember_convention("snake_case", repo="my-repo")
        cm.remember_fragile_file("config.py", "sensitive", repo="my-repo")
        assert len(cm.get_test_commands("my-repo")) == 1
        assert len(cm.get_conventions("my-repo")) == 1
        assert len(cm.get_fragile_files("my-repo")) == 1

    def test_memory_summary(self):
        cm = CodingMemory()
        cm.remember_test_command("pytest")
        cm.remember_test_command("ruff")
        summary = cm.summary()
        assert summary["total_entries"] == 2
        assert "test_command" in summary["by_type"]


class TestWeek82Corruption:
    def test_detector_audit_empty(self):
        store = MemoryStore()
        detector = CorruptionDetector(store)
        report = detector.audit()
        assert report.total_entries == 0
        assert report.healthy_ratio == 1.0

    def test_detector_finds_vague(self):
        store = MemoryStore()
        store.add(MemoryEntry(memory_id="v1", memory_type=MemoryType.REPO_CONVENTION, content="it"))
        detector = CorruptionDetector(store)
        report = detector.audit()
        assert report.vague_entries >= 1
        assert report.corrupt_entries >= 1

    def test_detector_finds_expired(self):
        store = MemoryStore()
        store.add(MemoryEntry(
            memory_id="e1", memory_type=MemoryType.TEST_COMMAND, content="pytest",
            expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        ))
        detector = CorruptionDetector(store)
        report = detector.audit()
        assert report.stale_entries >= 1

    def test_detector_finds_overgeneralized(self):
        store = MemoryStore()
        store.add(MemoryEntry(
            memory_id="o1", memory_type=MemoryType.REPO_CONVENTION,
            content="always do it this way",
        ))
        detector = CorruptionDetector(store)
        report = detector.audit()
        assert report.overgeneralized_entries >= 1

    def test_quarantine_removes_entry(self):
        store = MemoryStore()
        store.add(MemoryEntry(memory_id="q1", memory_type=MemoryType.TEST_COMMAND, content="pytest"))
        detector = CorruptionDetector(store)
        entry = store.get("q1")
        assert detector.quarantine(entry) is True
        assert store.count() == 0

    def test_audit_report_dataclass(self):
        report = MemoryAuditReport(total_entries=5, corrupt_entries=2, healthy_ratio=0.6)
        d = report.to_dict()
        assert d["total_entries"] == 5
        assert d["healthy_ratio"] == 0.6


class TestWeek83RepoAdaptation:
    def test_engine_scans_profile(self):
        engine = RepoAdaptationEngine(repo_path=".")
        profile = engine.scan()
        assert isinstance(profile, RepoProfile)
        assert profile.repo_path != ""

    def test_profile_has_fields(self):
        profile = RepoProfile(repo_path="/test", language="python")
        assert profile.language == "python"
        assert profile.profile_version == 0

    def test_profile_to_prompt(self):
        profile = RepoProfile(language="python", test_framework="pytest")
        prompt = profile.to_prompt_section()
        assert "REPO PROFILE" in prompt
        assert "python" in prompt
        assert "pytest" in prompt

    def test_benchmark_improvement(self):
        engine = RepoAdaptationEngine(repo_path=".")
        profile = engine.scan()
        bench = engine.benchmark_improvement(profile)
        assert "conventions_learned" in bench
        assert "estimated_improvement" in bench


class TestWeek84CrossRepoTransfer:
    def test_has_5_policies(self):
        assert len(TRANSFER_POLICIES) == 5

    def test_transfer_trial_dataclass(self):
        trial = TransferTrial(
            source_repo="repo_a",
            target_repo="repo_b",
            policy="global_memory",
            task_success=True,
            negative_transfer=False,
        )
        assert trial.task_success is True
        assert trial.policy == "global_memory"

    def test_experiment_run_trial(self):
        exp = CrossRepoTransferExperiment()

        def task_fn(src, tgt, policy):
            return {"success": True, "negative_transfer": False}

        trial = exp.run_trial("src", "tgt", "global_memory", task_fn)
        assert trial.task_success is True
        assert len(exp.trials) == 1

    def test_experiment_run_failed_trial(self):
        exp = CrossRepoTransferExperiment()

        def task_fn(src, tgt, policy):
            raise ValueError("failed")

        trial = exp.run_trial("src", "tgt", "no_memory", task_fn)
        assert trial.task_success is False
        assert trial.negative_transfer is True

    def test_experiment_summary_no_trials(self):
        exp = CrossRepoTransferExperiment()
        s = exp.summary()
        assert "No trials" in s["message"]

    def test_experiment_summary_with_trials(self):
        exp = CrossRepoTransferExperiment()

        def good_fn(s, t, p):
            return {"success": True, "negative_transfer": False}

        for policy in TRANSFER_POLICIES:
            exp.run_trial("src", "tgt", policy, good_fn)

        s = exp.summary()
        assert s["total_trials"] == 5
        assert "policy_results" in s
        assert len(s["policy_results"]) == 5
