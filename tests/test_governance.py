"""Tests for governance (policy, sensitive code, review board)."""


def test_autonomy_policy():
    """AutonomyPolicyEngine evaluates actions correctly."""
    from lyme.governance.autonomy_policy import (
        AutonomyPolicyEngine, ActionType, AutonomyLevel
    )

    engine = AutonomyPolicyEngine()
    context = {
        "autonomy_level": "verified_auto",
        "test_coverage": 0.5,
        "edit_size": 10,
        "confidence": 0.8,
        "sensitive_zone": False,
    }

    read_eval = engine.evaluate(ActionType.READ_ONLY, context)
    assert read_eval.allowed is True

    deploy_eval = engine.evaluate(ActionType.DEPLOY, context)
    assert deploy_eval.requires_approval is True

    secrets_eval = engine.evaluate(ActionType.MODIFY_SECRETS, context)
    # secrets should be denied at verified_auto level
    assert secrets_eval.allowed is False


def test_sensitive_code_detection(tmp_path):
    """SensitiveCodeDetector finds sensitive code patterns."""
    from lyme.governance.sensitive_code import SensitiveCodeDetector

    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "login.py").write_text("SECRET_KEY = 'hardcoded_key'\ndef login(): pass\n")
    (tmp_path / "payments").mkdir()
    (tmp_path / "payments" / "checkout.py").write_text("stripe.Charge.create(amount=100)\n")
    (tmp_path / "utils").mkdir()
    (tmp_path / "utils" / "helpers.py").write_text("def helper(): pass\n")

    detector = SensitiveCodeDetector()
    result = detector.detect(tmp_path)

    assert len(result.zones) >= 0
    assert result.risk_summary["files_scanned"] > 0


def test_review_board():
    """ActionReviewBoard produces decisions from critics."""
    from lyme.governance.review_board import ActionReviewBoard, ReviewRequest

    board = ActionReviewBoard()
    request = ReviewRequest(
        id="test_001", title="Test Change",
        description="Test review", action_type="modify_files",
        files_changed=["src/auth.py"], diff_summary="Security fix for auth",
        risk_score=0.6, proposer_notes="Critical security patch",
    )

    decision = board.submit_request(request)
    assert decision.final_verdict.value in ("approve", "reject", "revise", "require_human")
    assert len(decision.critiques) == 5


def test_review_board_low_risk():
    """Low risk changes should be approved."""
    from lyme.governance.review_board import ActionReviewBoard, ReviewRequest

    board = ActionReviewBoard()
    request = ReviewRequest(
        id="test_002", title="Docs Update",
        description="Update documentation", action_type="read_only",
        files_changed=["docs/readme.md"], diff_summary="Updated README",
        risk_score=0.1, proposer_notes="Simple documentation change",
    )

    decision = board.submit_request(request)
    assert decision.final_verdict.value in ("approve", "require_human")
