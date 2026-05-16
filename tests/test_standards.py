import json, os, tempfile
from pathlib import Path


class TestAgentTraceStandard:
    def test_schema_imports(self):
        from src.lyme.standards.trace import (
            OpenAgentTrace, TraceHeader, TraceEvent,
            ModelCallEvent, ToolCallEvent, FileReadEvent,
            FileEditEvent, TestRunEvent, FailedAttemptEvent,
            EvidenceClaimEvent, VerificationStepEvent,
            HumanInterventionEvent, ConfidenceChangeEvent,
            RollbackEvent, EventType, SCHEMA_VERSION, SCHEMA_URN,
        )
        assert SCHEMA_VERSION == "0.7.0"
        assert "open-agent-trace" in SCHEMA_URN

    def test_simple_trace_construction(self):
        from src.lyme.standards.trace import OpenAgentTrace, TraceHeader, AgentIdentity
        trace = OpenAgentTrace(
            header=TraceHeader(
                trace_id="test-001",
                agent=AgentIdentity(name="test-agent", model="test-model"),
            )
        )
        assert trace.header.trace_id == "test-001"
        assert trace.header.agent.name == "test-agent"
        assert len(trace.events) == 0

    def test_add_events(self):
        from src.lyme.standards.trace import (
            OpenAgentTrace, ModelCallEvent, FileReadEvent, FileEditEvent,
            TestRunEvent, FailedAttemptEvent,
        )
        trace = OpenAgentTrace()
        trace.add_event(ModelCallEvent(model="gpt-4", total_tokens=100, latency_ms=500.0))
        trace.add_event(FileReadEvent(file_path="/test.py", bytes_read=1000, lines_read=30))
        trace.add_event(FileEditEvent(file_path="/test.py", edit_type="replace", lines_added=5, lines_removed=3))
        trace.add_event(TestRunEvent(command="pytest", tests_passed=10, tests_failed=0, total_tests=10, exit_code=0))
        trace.add_event(FailedAttemptEvent(attempt_number=1, failure_reason="test failure"))
        assert len(trace.events) == 5
        assert trace.events[0]["type"] == "model_call"
        assert trace.events[1]["type"] == "file_read"
        assert trace.events[2]["type"] == "file_edit"
        assert trace.events[3]["type"] == "test_run"

    def test_serialization_roundtrip(self):
        from src.lyme.standards.trace import OpenAgentTrace, ModelCallEvent
        trace = OpenAgentTrace()
        trace.add_event(ModelCallEvent(model="gpt-4", total_tokens=100))
        trace.finalize()
        data = trace.to_dict()
        assert "header" in data
        assert "events" in data
        assert "summary" in data
        assert data["summary"]["totals"]["model_calls"] == 1

        restored = OpenAgentTrace.from_dict(data)
        assert restored.header.trace_id == trace.header.trace_id
        assert len(restored.events) == 1

    def test_to_json_from_json(self):
        from src.lyme.standards.trace import OpenAgentTrace, TraceEvent
        trace = OpenAgentTrace()
        trace.add_event(TraceEvent(type="system", metadata={"test": True}))
        trace.finalize()
        json_str = trace.to_json()
        assert isinstance(json_str, str)
        restored = OpenAgentTrace.from_json(json_str)
        assert restored.header.trace_id == trace.header.trace_id
        assert len(restored.events) == 1

    def test_example_generation(self):
        from src.lyme.standards.trace.examples import (
            generate_simple_fix_trace, generate_complex_refactor_trace,
            generate_failed_attempt_trace,
        )
        t1 = generate_simple_fix_trace()
        assert len(t1.events) > 0
        assert t1.summary["totals"]["model_calls"] >= 1

        t2 = generate_complex_refactor_trace()
        assert len(t2.events) > len(t1.events)
        assert t2.summary["totals"]["file_edits"] >= 4

        t3 = generate_failed_attempt_trace()
        assert t3.summary["totals"]["failed_attempts"] >= 2
        assert t3.summary["totals"]["human_interventions"] >= 1
        assert t3.summary["totals"]["rollbacks"] >= 1

    def test_validator_valid_trace(self):
        from src.lyme.standards.trace.validator import OpenTraceValidator
        from src.lyme.standards.trace.examples import generate_simple_fix_trace
        validator = OpenTraceValidator()
        trace = generate_simple_fix_trace()
        result = validator.validate(trace)
        assert result.valid, f"Trace should be valid, got: {result.errors}"
        assert result.event_count > 0

    def test_validator_empty_trace(self):
        from src.lyme.standards.trace.validator import OpenTraceValidator
        from src.lyme.standards.trace import OpenAgentTrace
        validator = OpenTraceValidator()
        trace = OpenAgentTrace()
        trace.finalize()
        result = validator.validate(trace)
        assert result.valid
        assert result.event_count == 0

    def test_converter_from_cognitive_trace(self):
        from src.lyme.standards.trace.converter import LymeTraceConverter
        converter = LymeTraceConverter()
        ct = {
            "trace_id": "ct-001",
            "agent_name": "test-agent",
            "scenario_name": "test",
            "start_time": 1000.0,
            "status": "completed",
            "steps": [
                {"id": "s1", "type": "plan", "content": "plan step", "timestamp": 1001.0,
                 "branch": "main", "confidence": 0.9},
                {"id": "s2", "type": "error", "content": "something failed", "timestamp": 1002.0,
                 "branch": "main", "confidence": 0.5},
            ],
            "decisions": [
                {"id": "d1", "question": "which fix?", "options": ["A", "B"],
                 "chosen": "A", "outcome": "success"},
            ],
            "branches": {"main": 2},
            "summary": {"duration_ms": 5000},
        }
        oat = converter.convert_cognitive_trace(ct)
        assert oat.header.agent.name == "test-agent"
        assert len(oat.events) >= 3  # 2 steps + 1 decision

    def test_comparison(self):
        from src.lyme.standards.trace.comparison import TraceComparer
        from src.lyme.standards.trace.examples import generate_simple_fix_trace, generate_complex_refactor_trace
        comparer = TraceComparer()
        t1 = generate_simple_fix_trace()
        t2 = generate_complex_refactor_trace()
        report = comparer.compare(t1, t2)
        assert report.trace_a_id == t1.header.trace_id
        assert report.trace_b_id == t2.header.trace_id
        assert report.total_events_a == len(t1.events)
        assert report.total_events_b == len(t2.events)
        assert report.summary != ""
        report_dict = report.to_dict()
        assert "trace_a_id" in report_dict
        assert "trace_b_id" in report_dict

    def test_comparison_same_trace(self):
        from src.lyme.standards.trace.comparison import TraceComparer
        from src.lyme.standards.trace.examples import generate_simple_fix_trace
        comparer = TraceComparer()
        t1 = generate_simple_fix_trace()
        report = comparer.compare(t1, t1)
        assert report.sequence_deviation == 0.0
        assert report.efficiency_ratio == 1.0

    def test_all_event_types(self):
        from src.lyme.standards.trace import EventType
        expected = [
            "model_call", "tool_call", "file_read", "file_edit",
            "test_run", "failed_attempt", "evidence_claim",
            "verification_step", "human_intervention",
            "confidence_change", "rollback", "plan",
            "decision", "search", "metric", "system", "checkpoint",
            "thought", "context_shift",
        ]
        for t in expected:
            assert t in EventType.__members__.values(), f"Missing event type: {t}"


class TestSemanticDiffStandard:
    def test_schema_imports(self):
        from src.lyme.standards.semantic_diff import SemanticDiff, DiffHeader, SCHEMA_VERSION
        assert SCHEMA_VERSION == "0.7.0"

    def test_basic_diff_construction(self):
        from src.lyme.standards.semantic_diff import SemanticDiff, DiffHeader
        sd = SemanticDiff(header=DiffHeader(diff_id="test-001", repository="test-repo"))
        assert sd.header.diff_id == "test-001"
        assert sd.header.repository == "test-repo"

    def test_add_syntactic_change(self):
        from src.lyme.standards.semantic_diff import SemanticDiff, SyntacticChange
        sd = SemanticDiff()
        sd.add_syntactic_change(SyntacticChange(
            file_path="/src/main.py", diff_type="modification",
            lines_added=5, lines_removed=3,
        ))
        assert len(sd.syntactic_changes) == 1
        assert sd.syntactic_changes[0]["file_path"] == "/src/main.py"

    def test_set_intent_and_risk(self):
        from src.lyme.standards.semantic_diff import SemanticDiff, BehavioralIntent, RiskScore
        sd = SemanticDiff()
        sd.set_intent(BehavioralIntent(
            intent_type="bug_fix",
            description="Fix pagination bug",
            backward_compatible=True,
        ))
        sd.set_risk(RiskScore(overall="low", risk_score_numeric=0.1))
        assert sd.behavioral_intent["intent_type"] == "bug_fix"
        assert sd.risk["overall"] == "low"

    def test_invariants_and_arch(self):
        from src.lyme.standards.semantic_diff import (
            SemanticDiff, AffectedInvariant, ArchitecturalImpact,
        )
        sd = SemanticDiff()
        sd.add_invariant(AffectedInvariant(
            invariant_type="data_invariant",
            description="Sort order preserved",
            status="preserved",
        ))
        sd.set_architectural_impact(ArchitecturalImpact(
            impact_level="low", complexity_delta=-5,
        ))
        assert len(sd.affected_invariants) == 1
        assert sd.architectural_impact["complexity_delta"] == -5

    def test_full_semantic_diff_examples(self):
        from src.lyme.standards.semantic_diff.examples import (
            generate_bug_fix_diff, generate_risky_refactor_diff,
            generate_security_fix_diff,
        )
        bf = generate_bug_fix_diff()
        assert bf.header.diff_id == "sd-bugfix-001"
        assert len(bf.syntactic_changes) >= 1
        assert bf.confidence >= 0.9

        rr = generate_risky_refactor_diff()
        assert rr.risk["overall"] == "medium"

        sf = generate_security_fix_diff()
        assert sf.behavioral_intent["intent_type"] == "security"

    def test_serialization_roundtrip(self):
        from src.lyme.standards.semantic_diff import SemanticDiff, SyntacticChange
        from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
        sd = generate_bug_fix_diff()
        data = sd.to_dict()
        assert "header" in data
        assert "syntactic_changes" in data
        assert "risk" in data

        restored = SemanticDiff.from_dict(data)
        assert restored.header.diff_id == sd.header.diff_id
        assert len(restored.syntactic_changes) == len(sd.syntactic_changes)

    def test_renderers(self):
        from src.lyme.standards.semantic_diff.renderer import (
            MarkdownRenderer, JSONRenderer, HTMLRenderer, SemanticDiffRenderer,
        )
        from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
        sd = generate_bug_fix_diff()

        md = MarkdownRenderer().render_semantic_diff(sd)
        assert "Semantic Diff" in md
        assert sd.header.diff_id in md

        js = JSONRenderer().render_semantic_diff(sd)
        assert sd.header.diff_id in js

        html = HTMLRenderer().render_semantic_diff(sd)
        assert "<html>" in html
        assert "Semantic Diff" in html

        sr = SemanticDiffRenderer("markdown")
        assert "Semantic Diff" in sr.render(sd)

    def test_cli_exporter(self):
        from src.lyme.standards.semantic_diff.cli_export import DiffCLIExporter
        from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
        sd = generate_bug_fix_diff()

        exporter = DiffCLIExporter("console")
        output = exporter.export(sd)
        assert output is not None
        assert sd.header.diff_id in output
        assert "Bug fix" in output or "bug" in output.lower() or "Pagination" in output

    def test_export_to_file(self):
        from src.lyme.standards.semantic_diff.cli_export import DiffCLIExporter
        from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
        sd = generate_bug_fix_diff()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            exporter = DiffCLIExporter("json")
            exporter.export(sd, output_path=f.name)
            with open(f.name) as f2:
                data = json.load(f2)
            assert "header" in data
            os.unlink(f.name)

    def test_different_formats_export(self):
        from src.lyme.standards.semantic_diff.cli_export import DiffCLIExporter, ExportFormat
        for fmt in ["json", "markdown", "html"]:
            exporter = DiffCLIExporter(fmt)
            assert exporter.format == fmt

    def test_diff_report(self):
        from src.lyme.standards.semantic_diff import DiffReport, SemanticDiff
        sd = SemanticDiff()
        report = DiffReport(
            semantic_diff=sd,
            agent_notes="Review needed",
            review_checklist=["Check tests", "Verify API"],
            blocking_issues=["Security concern"],
            recommended_action="block",
        )
        d = report.to_dict()
        assert d["recommended_action"] == "block"
        assert d["agent_notes"] == "Review needed"


class TestCognitionBenchmarkSpec:
    def test_spec_imports(self):
        from src.lyme.standards.benchmark_spec import SCHEMA_VERSION
        assert SCHEMA_VERSION == "0.7.0"

    def test_build_default_spec(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        spec = build_default_spec()
        assert spec.name == "Lyme Software Cognition Benchmark"
        assert len(spec.dimensions) == 8
        assert len(spec.tasks) >= 8  # at least 1 per dimension

    def test_tasks_per_dimension(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        spec = build_default_spec()
        dim_categories = {d.name: [] for d in spec.dimensions}
        cat_to_dim = {
            "causal_reasoning": "Causal Reasoning",
            "invariant_preservation": "Invariant Preservation",
            "temporal_reasoning": "Temporal Reasoning",
            "architecture_aware_planning": "Architecture-Aware Planning",
            "evidence_grounding": "Evidence Grounding",
            "safe_autonomy": "Safe Autonomy",
            "memory_usefulness": "Memory Usefulness",
            "verification_quality": "Verification Quality",
        }
        for task_dict in spec.tasks:
            dim_name = cat_to_dim.get(task_dict["category"], "Unknown")
            if dim_name in dim_categories:
                dim_categories[dim_name].append(task_dict["id"])

        for dim_name, task_ids in dim_categories.items():
            assert len(task_ids) >= 1, f"Dimension '{dim_name}' has no tasks"
            print(f"  {dim_name}: {len(task_ids)} tasks ({', '.join(task_ids)})")

    def test_task_format_validation(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        spec = build_default_spec()
        for task_dict in spec.tasks:
            assert "id" in task_dict
            assert "category" in task_dict
            assert "format" in task_dict
            assert "name" in task_dict
            assert "description" in task_dict
            assert "prompt" in task_dict
            assert "scoring" in task_dict
            assert "estimated_difficulty" in task_dict

    def test_scoring_methods(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        spec = build_default_spec()
        for task_dict in spec.tasks:
            scoring = task_dict["scoring"]
            assert "metric" in scoring
            assert scoring["metric"] in ("pass_fail", "binary_score", "continuous_01", "multi_criteria", "comparative", "latency", "efficiency", "accuracy")

    def test_anti_gaming_rules(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        spec = build_default_spec()
        for task_dict in spec.tasks:
            ag = task_dict.get("anti_gaming", {})
            assert "forbidden_patterns" in ag
            assert "max_attempts" in ag

    def test_serialization(self):
        from src.lyme.standards.benchmark_spec.registry import build_default_spec
        from src.lyme.standards.benchmark_spec import CognitionBenchmarkSpec
        spec = build_default_spec()
        data = spec.to_dict()
        assert data["name"] == spec.name
        assert len(data["dimensions"]) == 8
        assert len(data["tasks"]) >= 8

        restored = CognitionBenchmarkSpec.from_dict(data)
        assert restored.name == spec.name
        assert len(restored.dimensions) == 8
        assert len(restored.tasks) >= 8


class TestIntegration:
    def test_all_standards_have_schema_version(self):
        from src.lyme.standards.trace import SCHEMA_VERSION as tv
        from src.lyme.standards.semantic_diff import SCHEMA_VERSION as sv
        from src.lyme.standards.benchmark_spec import SCHEMA_VERSION as bv
        assert tv == sv == bv == "0.7.0"

    def test_trace_conversion_to_semantic_diff(self):
        """Verify trace events can provide data for semantic diffs"""
        from src.lyme.standards.trace.examples import generate_complex_refactor_trace
        trace = generate_complex_refactor_trace()
        file_edits = [e for e in trace.events if e.get("type") == "file_edit"]
        test_runs = [e for e in trace.events if e.get("type") == "test_run"]
        assert len(file_edits) >= 4
        assert len(test_runs) >= 1

    def test_generated_outputs_are_valid(self):
        from src.lyme.standards.trace.examples import generate_simple_fix_trace
        from src.lyme.standards.trace.validator import OpenTraceValidator
        from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
        from src.lyme.standards.semantic_diff import SemanticDiff

        validator = OpenTraceValidator()
        trace = generate_simple_fix_trace()
        assert validator.validate(trace).valid

        sd = generate_bug_fix_diff()
        assert sd.to_dict()["header"]["diff_id"] == "sd-bugfix-001"
        d2 = SemanticDiff.from_dict(sd.to_dict())
        assert d2.header.diff_id == "sd-bugfix-001"

    def test_comparison_output_is_deterministic(self):
        from src.lyme.standards.trace.comparison import TraceComparer
        from src.lyme.standards.trace.examples import generate_simple_fix_trace, generate_complex_refactor_trace
        comparer = TraceComparer()
        t1 = generate_simple_fix_trace()
        t2 = generate_complex_refactor_trace()
        r1 = comparer.compare(t1, t2)
        r2 = comparer.compare(t1, t2)
        assert r1.sequence_deviation == r2.sequence_deviation
        assert r1.efficiency_ratio == r2.efficiency_ratio
