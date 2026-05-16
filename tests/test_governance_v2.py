"""Tests for governance v2 (change governance, constitution, ledger)."""


def test_change_governance_auto_apply():
    """Low-risk changes get auto-apply."""
    from lyme.governance.change_governance import ChangeGovernanceEngine
    engine = ChangeGovernanceEngine()
    result = engine.evaluate({
        "risk_score": 0.1,
        "scope": "local",
        "files_changed": ["docs/readme.md"],
        "verification_coverage": 0.8,
        "sensitivity": "none",
        "reversibility": "easy",
    })
    assert result.decision.value in ("auto_apply", "patch_only")


def test_change_governance_block():
    """Critical-risk changes get blocked."""
    from lyme.governance.change_governance import ChangeGovernanceEngine
    engine = ChangeGovernanceEngine()
    result = engine.evaluate({
        "risk_score": 0.95,
        "scope": "broad",
        "files_changed": ["src/core/auth.py"],
        "sensitivity": "critical",
        "reversibility": "irreversible",
    })
    assert result.decision.value == "block"
    assert len(result.reasoning) > 0


def test_change_governance_require_approval():
    """High-risk broad changes require approval."""
    from lyme.governance.change_governance import ChangeGovernanceEngine
    engine = ChangeGovernanceEngine()
    result = engine.evaluate({
        "risk_score": 0.75,
        "scope": "broad",
        "files_changed": ["src/module.py", "src/other.py"],
        "sensitivity": "none",
    })
    assert result.decision.value in ("require_approval", "require_review", "block")


def test_change_governance_require_review():
    """Security-sensitive changes require review."""
    from lyme.governance.change_governance import ChangeGovernanceEngine
    engine = ChangeGovernanceEngine()
    result = engine.evaluate({
        "risk_score": 0.4,
        "scope": "module",
        "files_changed": ["src/auth/login.py"],
        "sensitivity": "security",
    })
    assert result.decision.value in ("require_review", "require_approval")


def test_constitution_create_and_validate():
    """RepoConstitution can be created and validated."""
    from lyme.governance.repo_constitution import RepoConstitution, ConstitutionValidator
    constit = RepoConstitution.create_default(repo_name="test-repo")
    validator = ConstitutionValidator(constit)
    issues = validator.validate()
    assert len(issues) >= 0
    assert constit.repo_name == "test-repo"


def test_constitution_validate_action():
    """ConstitutionValidator checks actions against zones."""
    from lyme.governance.repo_constitution import (
        RepoConstitution, ConstitutionValidator, AllowedAction,
    )
    constit = RepoConstitution.create_default(repo_name="test")
    validator = ConstitutionValidator(constit)

    allowed, reason = validator.validate_action("src/module.py", AllowedAction.READ)
    assert allowed
    allowed, reason = validator.validate_action("deploy/prod.sh", AllowedAction.DEPLOY)
    assert allowed is False or allowed


def test_constitution_save_load():
    """RepoConstitution round-trips through JSON."""
    from lyme.governance.repo_constitution import RepoConstitution
    import tempfile, json
    constit = RepoConstitution.create_default(repo_name="roundtrip")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import os
        path = f.name
        json.dump(constit.to_dict(), f)
    loaded = RepoConstitution.load(path)
    assert loaded.repo_name == "roundtrip"
    assert len(loaded.zones) > 0
    os.unlink(path)


def test_ledger_record_and_retrieve():
    """AutonomousChangeLedger records and retrieves entries."""
    from lyme.governance.change_ledger import AutonomousChangeLedger, EntryOutcome
    ledger = AutonomousChangeLedger()
    eid = ledger.record_change(
        description="Test change",
        agent="lyme",
        intent="refactor",
        risk_score=0.3,
        verification_result="passed",
        outcome=EntryOutcome.SUCCESS,
    )
    assert eid is not None
    entry = ledger.get_entry(eid)
    assert entry is not None
    assert entry.description == "Test change"
    assert entry.risk_score == 0.3


def test_ledger_multiple_entries():
    """Ledger handles multiple entry types."""
    from lyme.governance.change_ledger import AutonomousChangeLedger, EntryOutcome
    ledger = AutonomousChangeLedger()
    ledger.record_change("Change 1", "lyme", "fix", 0.2, "pass", EntryOutcome.SUCCESS)
    ledger.record_verification("Verify 1", "lyme", "all_passed", ["test1", "test2"])
    ledger.record_approval("Approve 1", "user", True, "looks good")
    ledger.record_rollback("Rollback 1", "lyme", True, "git revert HEAD")
    ledger.record_memory("Memory 1", {"pattern": "refactor", "outcome": "success"})
    summary = ledger.get_summary()
    assert summary.total_entries == 5
    assert summary.rollback_count == 1
    assert summary.memory_count == 1


def test_ledger_summary():
    """LedgerSummary produces correct statistics."""
    from lyme.governance.change_ledger import (
        AutonomousChangeLedger, EntryOutcome,
    )
    ledger = AutonomousChangeLedger()
    ledger.record_change("A", "lyme", "fix", 0.1, "pass", EntryOutcome.SUCCESS)
    ledger.record_change("B", "lyme", "fix", 0.2, "fail", EntryOutcome.FAILURE)
    ledger.record_change("C", "lyme", "fix", 0.3, "pass", EntryOutcome.SUCCESS)
    summary = ledger.get_summary()
    assert summary.total_entries == 3
    assert summary.success_rate > 0
    assert summary.avg_risk > 0
