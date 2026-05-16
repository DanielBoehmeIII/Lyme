import json, os, tempfile, time


class TestResearchCorpus:
    def test_corpus_imports(self):
        from src.lyme.research_corpus import ResearchCorpus, CorpusEntry, CorpusConfig
        assert ResearchCorpus is not None

    def test_add_entry(self):
        from src.lyme.research_corpus import ResearchCorpus, CorpusEntry, CorpusConfig
        config = CorpusConfig(require_opt_in=False, anonymize=False)
        corpus = ResearchCorpus(config)
        entry = CorpusEntry(
            title="Test trace",
            entry_type="agent_trace",
            data={"events": [{"type": "test"}]},
            tags=["test"],
        )
        eid = corpus.add_entry(entry)
        assert eid is not None
        assert len(corpus.entries) == 1

    def test_privacy_redaction(self):
        from src.lyme.research_corpus import PrivacyRedactor
        redactor = PrivacyRedactor([r'api_key\s*=\s*["\'][^"\']+["\']'])
        result = redactor.redact('api_key = "sk-1234567890abcdef"')
        assert "[REDACTED]" in result
        assert "sk-1234567890abcdef" not in result

    def test_redact_dict_nested(self):
        from src.lyme.research_corpus import PrivacyRedactor
        redactor = PrivacyRedactor([r'ghp_[A-Za-z0-9]{36}'])
        data = {"token": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}
        result = redactor.redact_dict(data)
        assert "[REDACTED]" in result["token"]
        assert "ghp_" not in result["token"]

    def test_citation_format(self):
        from src.lyme.research_corpus import CitationFormatter, CorpusEntry
        entry = CorpusEntry(entry_id="test-001", title="Test Entry", entry_type="agent_trace")
        paper = CitationFormatter.format_for_paper(entry)
        assert "Lyme Research Corpus" in paper
        bibtex = CitationFormatter.format_bibtex(entry)
        assert "@misc" in bibtex

    def test_opt_in_validation(self):
        from src.lyme.research_corpus import ResearchCorpus, CorpusEntry
        corpus = ResearchCorpus()
        entry = CorpusEntry(title="No hash")
        try:
            corpus.add_entry(entry)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "opt-in" in str(e).lower()

    def test_reproducibility_metadata(self):
        from src.lyme.research_corpus import ReproducibilityMetadata
        rm = ReproducibilityMetadata(
            python_version="3.12",
            model_name="claude-3",
            random_seed=42,
        )
        d = rm.to_dict()
        assert d["python_version"] == "3.12"
        assert d["model_name"] == "claude-3"

    def test_summary(self):
        from src.lyme.research_corpus import ResearchCorpus, CorpusEntry, CorpusConfig
        config = CorpusConfig(require_opt_in=False, anonymize=False)
        corpus = ResearchCorpus(config)
        corpus.add_entry(CorpusEntry(entry_id="e1", entry_type="agent_trace", data={}))
        corpus.add_entry(CorpusEntry(entry_id="e2", entry_type="benchmark_run", data={}))
        s = corpus.summary()
        assert s["total_entries"] == 2
        assert s["by_type"]["agent_trace"] == 1


class TestResearchPortal:
    def test_portal_imports(self):
        from src.lyme.research_portal import ResearchPortal, PortalConfig, BenchmarkLeaderboard
        assert ResearchPortal is not None

    def test_leaderboard(self):
        from src.lyme.research_portal import BenchmarkLeaderboard, LeaderboardEntry
        lb = BenchmarkLeaderboard()
        lb.add_entry(LeaderboardEntry(agent_name="A", model="m1", overall_score=0.85, tasks_completed=10, total_tasks=12))
        lb.add_entry(LeaderboardEntry(agent_name="B", model="m2", overall_score=0.72, tasks_completed=8, total_tasks=12))
        lb.add_entry(LeaderboardEntry(agent_name="C", model="m3", overall_score=0.91, tasks_completed=11, total_tasks=12))
        top = lb.top_n(2)
        assert top[0].agent_name == "C"
        assert top[1].agent_name == "A"
        assert len(top) == 2

    def test_failure_taxonomy(self):
        from src.lyme.research_portal import FailureTaxonomy
        ft = FailureTaxonomy()
        assert ft.classify("wrong_root_cause") == "reasoning"
        assert ft.classify("unsafe_operation") == "safety"
        assert ft.classify("unknown_type") is None
        assert ft.severity("unsafe_operation") == "critical"

    def test_research_report(self):
        from src.lyme.research_portal import ResearchReport
        report = ResearchReport(
            report_id="r1", title="Test Report", authors=["Researcher A"],
            abstract="This is a test",
            results={"accuracy": 0.85},
            conclusions=["Finding 1"],
        )
        md = report.to_markdown()
        assert "Test Report" in md
        assert "Researcher A" in md
        assert "Finding 1" in md

    def test_portal_save(self):
        from src.lyme.research_portal import (
            ResearchPortal, PortalConfig, LeaderboardEntry, ResearchReport,
            AblationResult, OpenQuestion, ModelComparison,
        )
        with tempfile.TemporaryDirectory() as tmp:
            config = PortalConfig(output_dir=tmp)
            portal = ResearchPortal(config)
            lb = portal.leaderboard
            lb.add_entry(LeaderboardEntry(agent_name="A", model="m", overall_score=0.9, tasks_completed=10, total_tasks=10))
            portal.add_report(ResearchReport(report_id="r1", title="Report 1"))
            portal.add_ablation(AblationResult(component="memory", full_system_score=0.8, ablated_score=0.5, impact=-0.3))
            portal.add_comparison(ModelComparison(models=["A", "B"], dimension="reasoning", scores={"A": 0.8, "B": 0.7}, winner="A", margin=0.1))
            portal.add_question(OpenQuestion(question="Can agents learn?", category="learning"))
            portal.save_portal()
            assert os.path.exists(os.path.join(tmp, "index.html"))
            assert os.path.exists(os.path.join(tmp, "leaderboard.json"))

    def test_ablation_impact(self):
        from src.lyme.research_portal import AblationResult
        ar = AblationResult(component="trace_compression", full_system_score=0.85, ablated_score=0.62, impact=-0.23)
        assert ar.impact == -0.23

    def test_portal_config_defaults(self):
        from src.lyme.research_portal import PortalConfig
        config = PortalConfig()
        assert "Lyme Research Portal" in config.title
        assert "Lyme Project" in config.maintainers

    def test_model_comparison(self):
        from src.lyme.research_portal import ModelComparison
        mc = ModelComparison(models=["claude-3", "gpt-4"], dimension="causal_reasoning",
                              scores={"claude-3": 0.82, "gpt-4": 0.78}, winner="claude-3", margin=0.04)
        assert mc.winner == "claude-3"


class TestContributionProtocol:
    def test_protocol_imports(self):
        from src.lyme.contribution_protocol import ContributionProtocol, ContributionType, Contribution
        assert ContributionProtocol is not None

    def test_submit_contribution(self):
        from src.lyme.contribution_protocol import ContributionProtocol, Contribution, ContributionType
        protocol = ContributionProtocol()
        c = Contribution(
            contribution_type=ContributionType.BENCHMARK_TASK,
            title="New benchmark task",
            description="Test causal reasoning",
            author="researcher",
            tests=["test_task.py"],
            telemetry_impact={"events": ["model_call"]},
            benchmark_impact={"dimension": "causal_reasoning"},
            failure_modes=["hallucination"],
            documentation="See attached",
        )
        cid = protocol.submit(c)
        assert cid is not None
        assert len(protocol.contributions) == 1
        assert c.ready_for_review()

    def test_ready_for_review_missing_fields(self):
        from src.lyme.contribution_protocol import ContributionProtocol, Contribution
        protocol = ContributionProtocol()
        c = Contribution(title="Incomplete")
        assert not c.ready_for_review()

    def test_review_approve(self):
        from src.lyme.contribution_protocol import (
            ContributionProtocol, Contribution, ContributionReview,
            ContributionType, ContributionStatus,
        )
        protocol = ContributionProtocol()
        c = Contribution(
            contribution_type=ContributionType.BENCHMARK_TASK,
            title="Test",
            author="author",
            tests=["test.py"],
            telemetry_impact={"a": 1},
            benchmark_impact={"b": 2},
            failure_modes=["f1"],
            documentation="docs",
        )
        cid = protocol.submit(c)
        review = ContributionReview(reviewer="reviewer", score=0.85, passed_requirements=["all"])
        result = protocol.review(cid, review)
        assert result is not None
        assert c.status == ContributionStatus.APPROVED

    def test_review_reject(self):
        from src.lyme.contribution_protocol import (
            ContributionProtocol, Contribution, ContributionReview,
            ContributionType, ContributionStatus,
        )
        protocol = ContributionProtocol()
        c = Contribution(
            contribution_type=ContributionType.BENCHMARK_TASK,
            title="Bad",
            author="author",
            tests=["test.py"],
            telemetry_impact={"a": 1},
            benchmark_impact={"b": 2},
            failure_modes=["f1"],
            documentation="docs",
        )
        cid = protocol.submit(c)
        review = ContributionReview(reviewer="reviewer", score=0.2,
                                     failed_requirements=["missing everything"])
        result = protocol.review(cid, review)
        assert c.status == ContributionStatus.REJECTED

    def test_get_guide(self):
        from src.lyme.contribution_protocol import ContributionProtocol
        protocol = ContributionProtocol()
        guide = protocol.get_guide("benchmark_task")
        assert guide is not None
        assert guide.contribution_type == "benchmark_task"

    def test_checklist(self):
        from src.lyme.contribution_protocol import ContributionProtocol
        protocol = ContributionProtocol()
        checklist = protocol.generate_checklist("benchmark_task")
        assert len(checklist) >= 3
        assert "Test coverage" in checklist[1] or "test" in checklist[1].lower()

    def test_summary(self):
        from src.lyme.contribution_protocol import ContributionProtocol, Contribution
        protocol = ContributionProtocol()
        c = Contribution(
            contribution_type="benchmark_task", title="T", author="A",
            tests=["t"], telemetry_impact={"a": 1},
            benchmark_impact={"b": 2}, failure_modes=["f"], documentation="d",
        )
        protocol.submit(c)
        s = protocol.summary()
        assert s["total"] == 1
        assert s["by_type"]["benchmark_task"] == 1
