import json, os, tempfile
from pathlib import Path


class TestPRIntelligence:
    def test_analyzer_imports(self):
        from src.lyme.pr_intelligence import PRAnalyzer, PRIntelligenceReport
        assert PRAnalyzer is not None

    def test_analyze_empty_pr(self):
        from src.lyme.pr_intelligence import PRAnalyzer
        analyzer = PRAnalyzer()
        report = analyzer.analyze({
            "number": 1,
            "title": "Test PR",
            "repository": "test/repo",
            "files": [],
            "diff": "",
        })
        assert report.pr_number == 1
        assert report.pr_title == "Test PR"

    def test_analyze_with_files(self):
        from src.lyme.pr_intelligence import PRAnalyzer
        analyzer = PRAnalyzer()
        report = analyzer.analyze({
            "number": 42,
            "title": "Fix payment bug",
            "repository": "test/repo",
            "files": [
                {"filename": "src/payment/processor.py", "status": "modified",
                 "additions": 120, "deletions": 40,
                 "patch": "Optional[User] could be None here"},
                {"filename": "src/db/migration.py", "status": "deleted",
                 "additions": 0, "deletions": 300,
                 "patch": ""},
                {"filename": "tests/test_payment.py", "status": "modified",
                 "additions": 45, "deletions": 10},
            ],
            "diff": "large diff content",
        })
        assert report.pr_number == 42
        assert len(report.semantic_impact) == 3
        assert len(report.invariant_violations) >= 1
        assert len(report.risk_zones) >= 1
        assert report.risk_score is not None
        assert report.review_summary is not None

    def test_risk_calculation(self):
        from src.lyme.pr_intelligence import PRAnalyzer
        analyzer = PRAnalyzer()
        report = analyzer.analyze({
            "number": 99,
            "title": "Risky change",
            "files": [
                {"filename": "src/db/schema.py", "status": "modified",
                 "additions": 300, "deletions": 100,
                 "patch": "DROP TABLE users"},
            ],
        })
        risk = report.risk_score
        assert risk is not None
        assert risk.get("score", 0) >= 0.3  # should detect high risk

    def test_report_to_dict(self):
        from src.lyme.pr_intelligence import PRAnalyzer
        analyzer = PRAnalyzer()
        report = analyzer.analyze({"number": 1, "title": "Test", "files": [], "diff": ""})
        d = report.to_dict()
        assert "pr_number" in d
        assert "risk_score" in d
        assert "review_summary" in d

    def test_github_client_mock(self):
        from src.lyme.pr_intelligence.github_client import GitHubPRClient
        client = GitHubPRClient()
        pr = client.fetch_pr("test/repo", 1)
        assert pr is not None
        assert pr.number == 1
        assert len(pr.files) == 3

    def test_report_generator_markdown(self):
        from src.lyme.pr_intelligence.report import PRReportGenerator
        generator = PRReportGenerator()
        report = generator.analyze_pr("test/repo", 1)
        assert report is not None
        md = generator.generate_markdown(report)
        assert "PR Intelligence Report" in md
        assert "Verification Checklist" in md
        assert "Rollback Strategy" in md or "Rollback" in md
        assert "Risk Score" in md

    def test_verification_checklist(self):
        from src.lyme.pr_intelligence.analyzer import VerificationChecklist
        vc = VerificationChecklist()
        vc.add_item("Check tests", "done", "All pass")
        vc.add_item("Check security", "pending")
        d = vc.to_dict()
        assert len(d["items"]) == 2
        assert d["items"][0]["check"] == "Check tests"
        assert d["items"][1]["status"] == "pending"


class TestCIIntegration:
    def test_ci_runner_imports(self):
        from src.lyme.ci_integration import CIRunner, CIConfig, CIMode
        assert CIRunner is not None

    def test_ci_runner_advisory(self):
        from src.lyme.ci_integration import CIRunner, CIConfig, CIMode
        config = CIConfig(mode=CIMode.ADVISORY)
        runner = CIRunner(config)
        audit = runner.run("test/repo", "abc123", "main")
        assert audit.run_id.startswith("ci-")
        assert audit.policy_decision in ("allow", "warn", "block")

    def test_ci_runner_blocking(self):
        from src.lyme.ci_integration import CIRunner, CIConfig, CIMode
        config = CIConfig(mode=CIMode.BLOCKING)
        runner = CIRunner(config)
        audit = runner.run("test/repo", "abc123", "main", pr_data={
            "number": 1,
            "files": [{"filename": "high_risk.py", "additions": 500, "deletions": 100}],
        })
        assert audit is not None

    def test_ci_artifact_save(self):
        from src.lyme.ci_integration import CIArtifact
        with tempfile.TemporaryDirectory() as tmp:
            art = CIArtifact(id="test-artifact", type="test", content={"key": "value"})
            path = os.path.join(tmp, "artifact.json")
            art.save(path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["id"] == "test-artifact"
            assert data["content"]["key"] == "value"

    def test_ci_audit_serialization(self):
        from src.lyme.ci_integration import CIRunner
        runner = CIRunner()
        audit = runner.run("test/repo", "abc", "main")
        d = audit.to_dict()
        assert d["run_id"] == audit.run_id
        assert "artifacts" in d
        assert "summary" in d
        js = audit.to_json()
        assert isinstance(js, str)

    def test_governance_policy(self):
        from src.lyme.ci_integration.governance import GovernancePolicy, PolicyAction
        policy = GovernancePolicy()
        decision = policy.evaluate(risk_score=0.8, violations=[], test_gaps=[], changed_files=[])
        assert decision.action == PolicyAction.BLOCK

        decision2 = policy.evaluate(risk_score=0.3, violations=[], test_gaps=[{"area": "src/main.py"}], changed_files=["src/main.py"])
        assert decision2.action == PolicyAction.WARN

        decision3 = policy.evaluate(risk_score=0.1, violations=[], test_gaps=[], changed_files=["a.py"])
        assert decision3.action == PolicyAction.ALLOW

    def test_governance_security_violation(self):
        from src.lyme.ci_integration.governance import GovernancePolicy, PolicyAction
        policy = GovernancePolicy()
        decision = policy.evaluate(
            risk_score=0.3,
            violations=[{"invariant_type": "security_regression", "description": "SQL injection risk"}],
            test_gaps=[],
            changed_files=["db.py"],
        )
        assert decision.action == PolicyAction.BLOCK


class TestIDEBridge:
    def test_bridge_imports(self):
        from src.lyme.ide_bridge import IDEBridge, BridgeResponse, IDEQuery, InsightType
        assert IDEBridge is not None

    def test_connect_disconnect(self):
        from src.lyme.ide_bridge import IDEBridge
        bridge = IDEBridge()
        assert not bridge.is_connected
        bridge.connect()
        assert bridge.is_connected
        bridge.disconnect()
        assert not bridge.is_connected

    def test_query_evidence_answer(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.EVIDENCE_ANSWER,
            query="What does this function do?",
            file_path="/src/main.py",
        ))
        assert response.insight_type == InsightType.EVIDENCE_ANSWER
        assert response.confidence > 0

    def test_query_semantic_diff(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.SEMANTIC_DIFF_PREVIEW,
            file_path="/src/main.py",
        ))
        assert response.insight_type == InsightType.SEMANTIC_DIFF_PREVIEW
        assert response.actionable

    def test_query_architecture_warning(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.ARCHITECTURE_WARNING,
            file_path="/src/main.py",
        ))
        assert "warning" in response.content.lower() or "no architecture" in response.content.lower()

    def test_query_verification_gap(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.VERIFICATION_GAP,
            file_path="/src/main.py",
        ))
        assert response.insight_type == InsightType.VERIFICATION_GAP
        assert "gap" in response.content.lower()

    def test_query_confidence(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.CONFIDENCE_INDICATOR,
        ))
        assert response.insight_type == InsightType.CONFIDENCE_INDICATOR
        assert 0 <= response.confidence <= 1

    def test_query_trace_replay(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.TRACE_REPLAY,
            query="trace-abc-123",
        ))
        assert response.insight_type == InsightType.TRACE_REPLAY

    def test_query_safe_edit(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        response = bridge.query(IDEQuery(
            query_type=InsightType.SAFE_EDIT_SUGGESTION,
            file_path="/src/main.py",
            selection="old_code",
        ))
        assert response.insight_type == InsightType.SAFE_EDIT_SUGGESTION
        assert response.suggestion is not None

    def test_bridge_not_connected(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        response = bridge.query(IDEQuery(query_type=InsightType.EVIDENCE_ANSWER, query="test"))
        assert response.confidence == 0.0
        assert "not connected" in response.content.lower()

    def test_history(self):
        from src.lyme.ide_bridge import IDEBridge, IDEQuery, InsightType
        bridge = IDEBridge()
        bridge.connect()
        bridge.query(IDEQuery(query_type=InsightType.EVIDENCE_ANSWER, query="q1"))
        bridge.query(IDEQuery(query_type=InsightType.SEMANTIC_DIFF_PREVIEW))
        history = bridge.get_history()
        assert len(history) == 2

    def test_lsp_protocol(self):
        from src.lyme.ide_bridge import IDEBridge, BridgeResponse, InsightType
        bridge = IDEBridge()
        response = BridgeResponse(
            insight_type=InsightType.EVIDENCE_ANSWER,
            content="test",
            confidence=0.9,
        )
        lsp = bridge.to_lsp_protocol(response)
        assert lsp["jsonrpc"] == "2.0"
        assert lsp["method"] == "lyme/insight"
        assert lsp["params"]["content"] == "test"
