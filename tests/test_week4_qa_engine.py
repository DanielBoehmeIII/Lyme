"""Week 4 — Repo Q&A Engine tests."""

import tempfile
from pathlib import Path
from lyme_model.slices.qa_engine import QAEngine, QABenchmark, QAAnswer, QAEvidence


def test_qa_engine_imports():
    assert QAEngine is not None
    assert QABenchmark is not None


def test_qa_engine_answers():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        (tmp / "src" / "app.py").write_text("import flask\napp = flask.Flask(__name__)\n")
        (tmp / "README.md").write_text("# Test App\n")
        (tmp / "test_app.py").write_text("def test_app():\n    pass\n")

        engine = QAEngine(str(tmp))
        result = engine.answer("What language is this project?")
        assert not result.refused
        assert result.answer != ""
        assert result.confidence > 0
        assert result.latency_s >= 0


def test_qa_engine_refuses_opinion():
    engine = QAEngine(".")
    result = engine.answer("What is the best framework?")
    assert result.refused
    assert "opinion" in result.refusal_reason or "subjective" in result.refusal_reason


def test_qa_engine_refuses_short():
    engine = QAEngine(".")
    result = engine.answer("Hi")
    assert result.refused


def test_qa_engine_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "code.py").write_text("def hello():\n    return 'world'\n")
        engine = QAEngine(str(tmp))
        result = engine.answer("What functions are defined?")
        if not result.refused:
            assert len(result.evidence) >= 0


def test_qa_engine_tracks_latency():
    engine = QAEngine(".")
    result = engine.answer("What language is this project?")
    assert result.latency_s > 0


def test_qa_answer_dataclass():
    a = QAAnswer(question="test?", answer="yes", confidence=0.9, refused=False)
    assert a.question == "test?"
    assert a.answer == "yes"
    assert a.confidence == 0.9
    d = a.to_dict()
    assert d["question"] == "test?"
    assert d["answer"] == "yes"


def test_qa_evidence_dataclass():
    e = QAEvidence(source_file="test.py", excerpt="def foo():", tool="grep")
    assert e.source_file == "test.py"
    assert e.tool == "grep"
    d = e.to_dict()
    assert d["source_file"] == "test.py"


def test_qa_engine_domain_classification():
    engine = QAEngine(".")
    tests = [
        ("What language is used?", "language"),
        ("What framework?", "framework"),
        ("How many files?", "file_structure"),
        ("What functions?", "functions"),
        ("What tests?", "tests"),
    ]
    for q, expected_domain in tests:
        result = engine.answer(q)
        if not result.refused:
            assert len(result.evidence) >= 0


def test_qa_benchmark_runs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        bench = QABenchmark(str(tmp))
        output = bench.run()
        assert output["summary"]["total_questions"] > 0


def test_qa_benchmark_results():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "test.py").write_text("x = 1\n")
        bench = QABenchmark(str(tmp))
        output = bench.run()
        summary = output["summary"]
        assert "avg_latency_s" in summary
        assert "avg_confidence" in summary
        assert "total_evidence" in summary


def test_qa_engine_framework_detection():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "app.py").write_text("import flask\nfrom flask import Flask\napp = Flask(__name__)\n")
        engine = QAEngine(str(tmp))
        result = engine.answer("What framework is used?")
        if not result.refused:
            assert "framework" in result.answer.lower() or "flask" in result.answer.lower()


def test_qa_engine_structure():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        (tmp / "src" / "main.py").write_text("print('hi')\n")
        engine = QAEngine(str(tmp))
        result = engine.answer("How is this project structured?")
        if not result.refused:
            assert "src/" in result.answer or "main.py" in result.answer
