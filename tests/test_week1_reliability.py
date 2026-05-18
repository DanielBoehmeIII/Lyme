"""Tests for Week 1 — Real-world autonomous reliability systems."""


def test_execution_supervisor_healthy():
    """ExecutionSupervisor reports healthy for clean execution."""
    from lyme.reliability.execution_supervisor import ExecutionSupervisor, TaskStatus
    sup = ExecutionSupervisor()
    sup.start_monitoring("task-1", "Fix test", 3)
    sup.record_snapshot("task-1", TaskStatus.COMPLETED, "Investigate", ["a.py"], 1, 100, 0.9, True, 0)
    sup.record_snapshot("task-1", TaskStatus.COMPLETED, "Apply", ["a.py", "b.py"], 2, 300, 0.85, True, 0)
    sup.record_snapshot("task-1", TaskStatus.COMPLETED, "Verify", ["a.py"], 3, 400, 0.95, True, 0)
    report = sup.analyze("task-1", "Fix test", 3)
    assert report.overall_health == "healthy"
    assert report.status == TaskStatus.COMPLETED
    assert report.verification_pass_rate > 0.5


def test_execution_supervisor_drift():
    """ExecutionSupervisor detects context drift."""
    from lyme.reliability.execution_supervisor import ExecutionSupervisor, TaskStatus
    sup = ExecutionSupervisor(drift_threshold=0.1)
    sup.start_monitoring("task-2", "Add big feature", 3)
    sup.record_snapshot("task-2", TaskStatus.RUNNING, "1", ["a.py"], 1, 100, 0.9, True, 0)
    sup.record_snapshot("task-2", TaskStatus.RUNNING, "2", ["a.py","b.py","c.py","d.py","e.py"], 2, 500, 0.7, False, 1)
    sup.record_snapshot("task-2", TaskStatus.RUNNING, "3", ["f.py","g.py","h.py"], 3, 1500, 0.5, False, 3)
    report = sup.analyze("task-2", "Add big feature", 3)
    assert len(report.drift_events) > 0


def test_execution_supervisor_cascading():
    """ExecutionSupervisor detects cascading failures."""
    from lyme.reliability.execution_supervisor import ExecutionSupervisor, TaskStatus
    sup = ExecutionSupervisor(cascade_threshold=2)
    sup.start_monitoring("task-3", "Risky", 3)
    sup.record_snapshot("task-3", TaskStatus.RUNNING, "1", ["a.py"], 1, 100, 0.9, True, 0)
    sup.record_snapshot("task-3", TaskStatus.FAILED, "2", ["b.py"], 2, 200, 0.3, False, 2)
    sup.record_snapshot("task-3", TaskStatus.FAILED, "3", ["c.py"], 3, 300, 0.1, False, 3)
    report = sup.analyze("task-3", "Risky", 3)
    assert report.cascading_detected
    assert report.overall_health == "critical"


def test_execution_supervisor_cli():
    """SupervisionReport CLI renderer works."""
    from lyme.reliability.execution_supervisor import ExecutionSupervisor, TaskStatus
    sup = ExecutionSupervisor()
    sup.start_monitoring("task-4", "Simple", 2)
    sup.record_snapshot("task-4", TaskStatus.COMPLETED, "1", ["a.py"], 1, 100, 0.9, True, 0)
    sup.record_snapshot("task-4", TaskStatus.COMPLETED, "2", ["b.py"], 2, 200, 0.9, True, 0)
    report = sup.analyze("task-4", "Simple", 2)
    output = report.render_cli()
    assert "EXECUTION SUPERVISOR" in output


def test_architectural_sanity_clean():
    """ArchitecturalSanity reports SANE for clean architecture."""
    from lyme.reliability.architectural_sanity import ArchitecturalSanity, SanityVerdict
    san = ArchitecturalSanity()
    report = san.check(
        ["src/main.py", "src/utils.py"],
        {"src/main.py": ["src/utils.py"], "src/utils.py": []},
    )
    assert report.verdict == SanityVerdict.SANE


def test_architectural_sanity_circular_deps():
    """ArchitecturalSanity detects circular dependencies."""
    from lyme.reliability.architectural_sanity import ArchitecturalSanity
    san = ArchitecturalSanity()
    report = san.check(
        ["src/a.py", "src/b.py", "src/c.py"],
        {"src/a.py": ["src/b.py"], "src/b.py": ["src/c.py"], "src/c.py": ["src/a.py"]},
    )
    circular = [c for c in report.checks if "circular" in c.description.lower()]
    assert len(circular) > 0


def test_architectural_sanity_forbidden():
    """ArchitecturalSanity detects forbidden patterns."""
    from lyme.reliability.architectural_sanity import ArchitecturalSanity
    san = ArchitecturalSanity()
    san.add_forbidden_pattern("secrets")
    report = san.check(
        ["src/main.py"], {"src/main.py": []},
        changes=[{"file": "src/secrets/key.txt"}],
    )
    assert report.critical_count > 0


def test_architectural_sanity_cli():
    """SanityReport CLI renderer works."""
    from lyme.reliability.architectural_sanity import ArchitecturalSanity
    san = ArchitecturalSanity()
    report = san.check(
        ["src/a.py", "src/b.py", "src/c.py"],
        {"src/a.py": ["src/b.py"], "src/b.py": ["src/c.py"], "src/c.py": ["src/a.py"]},
    )
    output = report.render_cli()
    assert "ARCHITECTURAL SANITY" in output


def test_goal_verifier_parse():
    """GoalVerifier parses requirements from description."""
    from lyme.reliability.goal_verifier import GoalVerifier
    gv = GoalVerifier()
    goal = gv.parse_goal("Implement login: should add endpoint, must validate, add tests")
    assert len(goal.requirements) >= 3


def test_goal_verifier_track():
    """GoalVerifier tracks requirement completion."""
    from lyme.reliability.goal_verifier import GoalVerifier, GoalStatus
    gv = GoalVerifier()
    g = gv.parse_goal("Fix bug and document")
    gv.update_requirement(g.id, g.requirements[0].id, GoalStatus.COMPLETED,
                          evidence=["fixed"], confidence=0.9)
    report = gv.verify(g.id)
    assert report.completion_pct > 0


def test_goal_verifier_deviation():
    """GoalVerifier detects deviations."""
    from lyme.reliability.goal_verifier import GoalVerifier, GoalStatus
    gv = GoalVerifier()
    g = gv.parse_goal("Refactor auth")
    for r in g.requirements:
        gv.update_requirement(g.id, r.id, GoalStatus.DEVIATED, confidence=0.3)
    report = gv.verify(g.id)
    assert report.status == GoalStatus.DEVIATED
    assert len(report.deviations) > 0


def test_goal_verifier_cli():
    """GoalVerificationReport CLI renderer works."""
    from lyme.reliability.goal_verifier import GoalVerifier, GoalStatus
    gv = GoalVerifier()
    g = gv.parse_goal("Test feature")
    for r in g.requirements:
        gv.update_requirement(g.id, r.id, GoalStatus.COMPLETED, confidence=1.0)
    report = gv.verify(g.id)
    output = report.render_cli()
    assert "GOAL VERIFICATION" in output


def test_rollback_intelligence_empty():
    """RollbackIntelligence handles empty state."""
    from lyme.reliability.rollback_intelligence import RollbackIntelligence
    ri = RollbackIntelligence()
    report = ri.analyze()
    assert report.total_rollbacks == 0


def test_rollback_intelligence_record():
    """RollbackIntelligence records and analyzes events."""
    from lyme.reliability.rollback_intelligence import RollbackIntelligence, RollbackStrategy, RollbackOutcome
    ri = RollbackIntelligence()
    ri.record("t1", RollbackStrategy.GIT_REVERT, "bad patch", 3, True, 5.0, RollbackOutcome.SUCCESS)
    ri.record("t2", RollbackStrategy.GIT_RESET, "wrong approach", 5, True, 2.0, RollbackOutcome.SUCCESS)
    ri.record("t3", RollbackStrategy.PATCH_REVERT, "partial", 2, False, 10.0, RollbackOutcome.FAILURE)
    report = ri.analyze()
    assert report.total_rollbacks == 3
    assert report.best_strategy is not None


def test_rollback_intelligence_recommend():
    """RollbackIntelligence recommends best strategy."""
    from lyme.reliability.rollback_intelligence import RollbackIntelligence, RollbackStrategy, RollbackOutcome
    ri = RollbackIntelligence()
    for i in range(5):
        ri.record(f"t{i}", RollbackStrategy.GIT_REVERT, f"reason {i}", i, True, 2.0, RollbackOutcome.SUCCESS)
    ri.record("tf", RollbackStrategy.PATCH_REVERT, "failed", 2, False, 10.0, RollbackOutcome.FAILURE)
    rec = ri.recommend({"files_affected": 3})
    assert rec in list(RollbackStrategy)


def test_rollback_intelligence_cli():
    """RollbackIntelligenceReport CLI renderer works."""
    from lyme.reliability.rollback_intelligence import RollbackIntelligence, RollbackStrategy, RollbackOutcome
    ri = RollbackIntelligence()
    ri.record("t1", RollbackStrategy.GIT_REVERT, "test", 1, True, 1.0, RollbackOutcome.SUCCESS)
    report = ri.analyze()
    output = report.render_cli()
    assert "ROLLBACK INTELLIGENCE" in output


def test_task_decomposition_empty():
    """TaskDecompositionMemory handles empty state."""
    from lyme.reliability.task_decomposition_memory import TaskDecompositionMemory
    tdm = TaskDecompositionMemory()
    report = tdm.report()
    assert report.total_memories == 0


def test_task_decomposition_store():
    """TaskDecompositionMemory stores and retrieves memories."""
    from lyme.reliability.task_decomposition_memory import TaskDecompositionMemory, DecompositionOutcome
    tdm = TaskDecompositionMemory()
    tdm.store("Fix login", "bug_fix",
              ["Investigate", "Fix", "Verify"],
              ["investigate", "edit", "verify"],
              [0.2, 0.5, 0.3], [True, True, True],
              [10, 30, 15], DecompositionOutcome.SUCCESS, 55, 0.9)
    tdm.store("Add search", "feature",
              ["Plan", "Impl", "Test"],
              ["plan", "edit", "test"],
              [0.4, 0.6, 0.5], [True, True, False],
              [20, 60, 30], DecompositionOutcome.PARTIAL, 110, 0.7)
    report = tdm.report()
    assert report.total_memories == 2
    assert report.overall_success_rate > 0


def test_task_decomposition_retrieve():
    """TaskDecompositionMemory finds similar decompositions."""
    from lyme.reliability.task_decomposition_memory import TaskDecompositionMemory, DecompositionOutcome
    tdm = TaskDecompositionMemory()
    tdm.store("Fix user login", "bug_fix",
              ["Investigate", "Fix"],
              ["investigate", "edit"],
              [0.2, 0.5], [True, True],
              [10, 20], DecompositionOutcome.SUCCESS, 30, 0.9)
    similar = tdm.retrieve_similar("Implement login", top_k=1)
    assert len(similar) >= 1


def test_task_decomposition_template():
    """TaskDecompositionMemory builds templates."""
    from lyme.reliability.task_decomposition_memory import TaskDecompositionMemory, DecompositionOutcome
    tdm = TaskDecompositionMemory()
    tdm.store("Fix auth bug", "bug_fix",
              ["Investigate", "Fix", "Verify"],
              ["investigate", "edit", "verify"],
              [0.2, 0.5, 0.3], [True, True, True],
              [10, 30, 15], DecompositionOutcome.SUCCESS, 55, 0.9)
    tmpl = tdm.get_template("bug_fix")
    assert tmpl is not None
    assert tmpl.success_rate > 0


def test_task_decomposition_cli():
    """DecompositionMemoryReport CLI renderer works."""
    from lyme.reliability.task_decomposition_memory import TaskDecompositionMemory, DecompositionOutcome
    tdm = TaskDecompositionMemory()
    tdm.store("Test task", "test", ["Step1"], ["test"], [0.5], [True], [5.0], DecompositionOutcome.SUCCESS, 5, 1.0)
    report = tdm.report()
    output = report.render_cli()
    assert "DECOMPOSITION MEMORY" in output


def test_real_task_executor_no_repo():
    """RealTaskExecutor handles missing repo gracefully."""
    from lyme.evaluation.self_benchmark import RealTaskExecutor
    executor = RealTaskExecutor(repo_path=None)
    result = executor.measure_test_success()
    assert result["pass_rate"] == 0.0


def test_verification_planner_execute_empty():
    """VerificationStrategyPlanner execute handles no-command steps."""
    from lyme.verification.planner import (
        VerificationStrategyPlanner, VerificationStrategy, VerificationStep, StepType,
    )
    planner = VerificationStrategyPlanner()
    strategy = VerificationStrategy(
        steps=[
            VerificationStep(
                step_type=StepType.MANUAL_REVIEW, description="Human review",
                command="", expected_duration_sec=0, risk_coverage=0, confidence_boost=0,
                cost=0, reversible=True, required=True, rationale="",
            ),
        ],
    )
    result = planner.execute_strategy(strategy)
    assert result.all_passed
    assert len(result.step_results) == 1


def test_self_benchmark_demo():
    """SelfBenchmark still works in demo mode."""
    from lyme.evaluation.self_benchmark import SelfBenchmark
    bench = SelfBenchmark()
    run = bench.run(repo_type="demo", repo_name="test")
    assert len(run.scores) == 9
    assert 0 <= run.overall_score <= 1


class TestHealDetectsPytestFailure:
    """Regression: heal must detect a failing pytest in the current working repo."""

    REPO_CALC = b"def add(a, b): return a - b\n"
    REPO_TEST = b"from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

    def _make_broken_repo(self, tmp_path):
        (tmp_path / "calc.py").write_bytes(self.REPO_CALC)
        (tmp_path / "test_calc.py").write_bytes(self.REPO_TEST)
        return tmp_path

    def test_heal_detects_failure(self, tmp_path):
        repo = self._make_broken_repo(tmp_path)
        import subprocess, sys, json
        result = subprocess.run(
            [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json"],
            capture_output=True, text=True, timeout=60,
            cwd=str(repo),
        )
        data = json.loads(result.stdout)
        assert data.get("status") == "complete", f"heal failed: {result.stderr}"
        assert data.get("issues_found", 0) > 0, (
            f"heal should detect at least one issue, got: {result.stdout}"
        )
        has_test_issue = any(
            i.get("category") == "test_failure" for i in data.get("issues", [])
        )
        assert has_test_issue, f"no test_failure issue found in {result.stdout}"

    def test_heal_report_not_healthy(self, tmp_path):
        repo = self._make_broken_repo(tmp_path)
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-m", "lyme", "heal", "--dry-run"],
            capture_output=True, text=True, timeout=60,
            cwd=str(repo),
        )
        output = result.stdout
        assert "Repository looks healthy" not in output, (
            f"heal must not report healthy when tests fail:\n{output}"
        )
        assert "Test failure" in output or "FAILED" in output or "test_failure" in output, (
            f"heal output should mention test failure:\n{output}"
        )

    def test_heal_fix_attempt(self, tmp_path):
        repo = self._make_broken_repo(tmp_path)
        import subprocess, sys, json
        result = subprocess.run(
            [sys.executable, "-m", "lyme", "heal", "--fix", "--json"],
            capture_output=True, text=True, timeout=60,
            cwd=str(repo),
        )
        data = json.loads(result.stdout)
        fixes = data.get("fixes", [])
        if any(f.get("success") for f in fixes):
            import importlib.util
            spec = importlib.util.spec_from_file_location("calc", str(repo / "calc.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            assert mod.add(2, 3) == 5, "calc.add(2,3) should return 5 after fix"
        else:
            fix_errors = [f.get("error", "no error") for f in fixes]
            assert any("unable" in e.lower() for e in fix_errors) or not fixes, (
                f"fix must either succeed or honestly report inability: {fix_errors}"
            )


def test_heal_quick_mode_no_full_suite(tmp_path):
    """Quick mode does not run full test suite by default."""
    import subprocess, sys, json
    (tmp_path / "calc.py").write_text("def add(a, b): return a + b\n")
    (tmp_path / "test_calc.py").write_text("from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json", "--verify", "quick", "--timeout", "30"],
        capture_output=True, text=True, timeout=60,
        cwd=str(tmp_path),
    )
    data = json.loads(result.stdout)
    assert data.get("status") == "complete"
    timeout_issues = [i for i in data.get("issues", []) if i.get("category") == "timeout"]
    assert len(timeout_issues) == 0, "quick mode should not timeout on a small repo"


def test_heal_full_mode_timeout_honest(tmp_path):
    """Full mode can timeout honestly and reports it as a warning, not a fix."""
    import subprocess, sys, json
    (tmp_path / "test_slow.py").write_text("import time\ndef test_slow():\n    time.sleep(5)\n    assert True\n")
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json", "--verify", "full", "--timeout", "1"],
        capture_output=True, text=True, timeout=30,
        cwd=str(tmp_path),
    )
    data = json.loads(result.stdout)
    assert data.get("status") == "complete"
    timeout_issues = [i for i in data.get("issues", []) if i.get("category") == "timeout"]
    assert len(timeout_issues) > 0, "full mode with --timeout 1 should produce a timeout issue"


def test_heal_timeout_not_a_fix(tmp_path):
    """Timeout does not count as a fix applied."""
    import subprocess, sys, json
    (tmp_path / "test_slow.py").write_text("import time\ndef test_slow():\n    time.sleep(5)\n    assert True\n")
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json", "--verify", "full", "--timeout", "1"],
        capture_output=True, text=True, timeout=30,
        cwd=str(tmp_path),
    )
    data = json.loads(result.stdout)
    assert data.get("fixes_applied", -1) == 0, "timeout should not increment fixes_applied"


def test_heal_none_mode_skips_verification(tmp_path):
    """None mode skips all test verification."""
    import subprocess, sys, json
    (tmp_path / "test_fail.py").write_text("def test_fail():\n    assert False\n")
    result = subprocess.run(
        [sys.executable, "-m", "lyme", "heal", "--dry-run", "--json", "--verify", "none"],
        capture_output=True, text=True, timeout=30,
        cwd=str(tmp_path),
    )
    data = json.loads(result.stdout)
    assert data.get("status") == "complete"
    assert data.get("fixes_applied", -1) == 0
    has_test_issue = any(i.get("category") == "test_failure" for i in data.get("issues", []))
    assert not has_test_issue, "none mode should not detect test failures"


def test_gate_uses_quick_verification():
    """Reliability gate should pass heal check when heal completes with quick mode."""
    from lyme.reliability_gate import ReliabilityGate
    gate = ReliabilityGate(repo_path=".")
    result = gate.check()
    heal_result = result["checks"].get("heal_succeeds", {})
    assert "passed" in heal_result, "gate heal check should have a pass/fail result"
    assert heal_result.get("detail", ""), "gate heal check should have a detail message"
