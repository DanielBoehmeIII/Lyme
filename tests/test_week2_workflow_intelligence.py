"""Tests for Week 2 — Workflow Intelligence."""


def test_workflow_recorder_empty():
    from lyme.workflow_intelligence import WorkflowRecorder
    wr = WorkflowRecorder()
    report = wr.analyze()
    assert report.total_sessions == 0


def test_workflow_recorder_session():
    from lyme.workflow_intelligence import WorkflowRecorder, ActionType, ActionOutcome
    wr = WorkflowRecorder()
    sid = wr.start_session("Fix bug", "repo", "python")
    assert sid is not None
    wr.record_step(ActionType.READ_FILE, "file.py", ActionOutcome.SUCCESS, 1.0)
    wr.record_step(ActionType.EDIT_FILE, "file.py", ActionOutcome.SUCCESS, 20.0)
    wr.end_session(True)
    report = wr.analyze()
    assert report.total_sessions == 1
    assert report.total_steps == 2


def test_workflow_recorder_pattern():
    from lyme.workflow_intelligence import WorkflowRecorder, ActionType, ActionOutcome
    wr = WorkflowRecorder()
    for i in range(3):
        wr.start_session(f"Task {i}", "repo")
        wr.record_step(ActionType.READ_FILE, "a.py", ActionOutcome.SUCCESS, 1.0)
        wr.record_step(ActionType.EDIT_FILE, "a.py", ActionOutcome.SUCCESS, 10.0)
        wr.record_step(ActionType.VERIFY_TEST, "pytest", ActionOutcome.SUCCESS, 5.0)
        wr.end_session(True)
    report = wr.analyze()
    assert len(report.common_patterns) >= 1


def test_workflow_recorder_cli():
    from lyme.workflow_intelligence import WorkflowRecorder, ActionType, ActionOutcome
    wr = WorkflowRecorder()
    wr.start_session("Test", "repo")
    wr.record_step(ActionType.READ_FILE, "a.py", ActionOutcome.SUCCESS, 1.0)
    wr.end_session(True)
    report = wr.analyze()
    output = report.render_cli()
    assert "WORKFLOW INTELLIGENCE" in output


def test_workflow_recorder_get_pattern():
    from lyme.workflow_intelligence import WorkflowRecorder, ActionType, ActionOutcome
    wr = WorkflowRecorder()
    wr.start_session("Fix login bug", "repo")
    wr.record_step(ActionType.EDIT_FILE, "a.py", ActionOutcome.SUCCESS, 10.0)
    wr.record_step(ActionType.VERIFY_TEST, "test", ActionOutcome.SUCCESS, 5.0)
    wr.end_session(True)
    pattern = wr.get_pattern_for_goal("login")
    assert pattern is not None


def test_pattern_learner_empty():
    from lyme.workflow_intelligence import PatternLearner
    pl = PatternLearner()
    report = pl.analyze()
    assert report.total_patterns == 0


def test_pattern_learner_observe():
    from lyme.workflow_intelligence import PatternLearner
    pl = PatternLearner()
    pl.observe("bug_fix", "Fix a bug", ["read", "edit", "verify"], True, 45.0, ["bug"])
    pl.observe("bug_fix", "Fix a bug", ["read", "edit", "verify"], True, 55.0, ["bug"])
    report = pl.analyze()
    assert report.total_patterns == 1
    assert report.top_patterns[0].frequency == 2


def test_pattern_learner_suggest():
    from lyme.workflow_intelligence import PatternLearner
    pl = PatternLearner()
    pl.observe("bug_fix", "Bug fix", ["read", "edit"], True, 30.0, ["bug", "fix"])
    suggested = pl.suggest(["bug"])
    assert suggested is not None


def test_pattern_learner_cli():
    from lyme.workflow_intelligence import PatternLearner
    pl = PatternLearner()
    pl.observe("test", "Test pattern", ["a", "b"], True, 10.0)
    report = pl.analyze()
    output = report.render_cli()
    assert "PATTERN LEARNER" in output


def test_debugging_learner_empty():
    from lyme.workflow_intelligence import DebuggingSequenceLearner
    dl = DebuggingSequenceLearner()
    report = dl.analyze()
    assert report.total_attempts == 0


def test_debugging_learner_record():
    from lyme.workflow_intelligence import DebuggingSequenceLearner
    dl = DebuggingSequenceLearner()
    dl.record("test_failure", ["test failed"], ["read logs", "fix"], True, 30.0, "bug")
    dl.record("test_failure", ["test failed"], ["read code", "fix"], True, 45.0, "bug")
    report = dl.analyze()
    assert report.total_attempts == 2
    assert len(report.strategies) >= 1


def test_debugging_learner_suggest():
    from lyme.workflow_intelligence import DebuggingSequenceLearner
    dl = DebuggingSequenceLearner()
    dl.record("test_failure", ["failed"], ["read logs", "fix code"], True, 30.0, "import error")
    actions = dl.suggest_actions("test_failure")
    assert actions is not None
    assert len(actions) > 0


def test_debugging_learner_cli():
    from lyme.workflow_intelligence import DebuggingSequenceLearner
    dl = DebuggingSequenceLearner()
    dl.record("err", ["e"], ["fix"], True, 10.0, "cause")
    report = dl.analyze()
    output = report.render_cli()
    assert "DEBUGGING SEQUENCE" in output


def test_evolution_tracker_empty():
    from lyme.workflow_intelligence import ArchitectureEvolutionTracker
    et = ArchitectureEvolutionTracker()
    report = et.analyze()
    assert report.total_snapshots == 0


def test_evolution_tracker_record():
    from lyme.workflow_intelligence import ArchitectureEvolutionTracker
    et = ArchitectureEvolutionTracker()
    et.record(10, 0.2, 0.3, 0.5, ["api", "core"])
    et.record(12, 0.25, 0.35, 0.55, ["api", "core", "services"])
    report = et.analyze()
    assert report.total_snapshots == 2
    assert len(report.trends) > 0


def test_evolution_tracker_cli():
    from lyme.workflow_intelligence import ArchitectureEvolutionTracker
    et = ArchitectureEvolutionTracker()
    et.record(5, 0.1, 0.2, 0.3, ["main"])
    report = et.analyze()
    output = report.render_cli()
    assert "EVOLUTION" in output


def test_recovery_learner_empty():
    from lyme.workflow_intelligence import RecoveryBehaviorLearner
    rl = RecoveryBehaviorLearner()
    report = rl.analyze()
    assert report.total_attempts == 0


def test_recovery_learner_record():
    from lyme.workflow_intelligence import RecoveryBehaviorLearner
    rl = RecoveryBehaviorLearner()
    rl.record("test_fail", "git_revert", "bad patch", True, 5.0)
    rl.record("test_fail", "git_revert", "wrong approach", True, 3.0)
    rl.record("build_fail", "manual_fix", "config", True, 30.0)
    report = rl.analyze()
    assert report.total_attempts == 3
    assert report.overall_success_rate > 0


def test_recovery_learner_suggest():
    from lyme.workflow_intelligence import RecoveryBehaviorLearner
    rl = RecoveryBehaviorLearner()
    rl.record("test_fail", "git_revert", "bad", True, 5.0)
    rl.record("test_fail", "patch_revert", "bad", False, 10.0)
    action = rl.suggest("test_fail")
    assert action == "git_revert"


def test_recovery_learner_cli():
    from lyme.workflow_intelligence import RecoveryBehaviorLearner
    rl = RecoveryBehaviorLearner()
    rl.record("test", "revert", "reason", True, 5.0)
    report = rl.analyze()
    output = report.render_cli()
    assert "RECOVERY" in output


def test_pr_review_analyzer_empty():
    from lyme.workflow_intelligence import PRReviewAnalyzer
    pa = PRReviewAnalyzer()
    report = pa.analyze()
    assert report.total_prs == 0


def test_pr_review_analyzer_record():
    from lyme.workflow_intelligence import PRReviewAnalyzer
    pa = PRReviewAnalyzer()
    pa.record("PR-1", "alice", 5, 100, 20, 200, 3, 4.0, True, True, False, ["bob"])
    pa.record("PR-2", "bob", 3, 50, 10, 150, 1, 2.0, True, False, True, ["alice"])
    report = pa.analyze()
    assert report.total_prs == 2
    assert report.profile.approval_rate == 1.0


def test_pr_review_analyzer_insights():
    from lyme.workflow_intelligence import PRReviewAnalyzer
    pa = PRReviewAnalyzer()
    pa.record("PR-1", "alice", 20, 500, 100, 50, 0, 72.0, False, False, False, ["bob"])
    pa.record("PR-2", "bob", 15, 400, 80, 40, 0, 96.0, False, False, False, ["alice"])
    report = pa.analyze()
    assert len(report.insights) > 0


def test_pr_review_analyzer_cli():
    from lyme.workflow_intelligence import PRReviewAnalyzer
    pa = PRReviewAnalyzer()
    pa.record("PR-1", "alice", 3, 50, 10, 100, 2, 2.0, True, True, False, ["bob"])
    report = pa.analyze()
    output = report.render_cli()
    assert "PR REVIEW" in output
