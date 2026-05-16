"""Week 2 — Improved Context Compiler tests."""

import json
import tempfile
from pathlib import Path
from lyme_model.context import ImprovedContextCompiler, ContextBenchmark
from lyme_model.context.improved import RankedFile, FrameworkInfo


def test_improved_compiler_imports():
    assert ImprovedContextCompiler is not None
    assert RankedFile is not None
    assert FrameworkInfo is not None


def test_improved_compiler_empty_repo():
    with tempfile.TemporaryDirectory() as tmp:
        cc = ImprovedContextCompiler(tmp)
        result = cc.compile("test task")
        assert result.total_tokens >= 0


def test_improved_compiler_python_repo():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        (tmp / "src" / "main.py").write_text(
            "import flask\nfrom flask import Flask\n\ndef create_app():\n    return Flask(__name__)\n"
        )
        (tmp / "README.md").write_text("# My Flask App\n")
        (tmp / "pyproject.toml").write_text("[project]\nname = 'flask-app'\ndependencies = ['flask']\n")
        (tmp / "src" / "hardware.py").write_text(
            "def detect_cpu():\n    return 'x86_64'\ndef detect_gpu():\n    return 'nvidia'\n"
        )

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("Where is hardware detection?")

        assert len(result.ranked_files) > 0
        assert result.total_analyzed_files > 0
        ranked_paths = [r.path for r in result.ranked_files]
        assert any("hardware" in p for p in ranked_paths)


def test_improved_compiler_ranked_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "detect.py").write_text("def detect_gpu():\n    pass\ndef detect_cpu():\n    pass\n")
        (tmp / "utils.py").write_text("def format_string():\n    pass\n")

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("Find GPU detection code")

        ranked = result.ranked_files
        assert len(ranked) > 0
        highest = ranked[0]
        assert highest.relevance > 0
        assert "detect" in highest.path or "detect" in highest.functions[0] if highest.functions else True


def test_improved_compiler_framework_detection():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "app.py").write_text(
            "import flask\nfrom flask import Flask\napp = Flask(__name__)\n"
        )

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("test")

        fw_names = [f.name for f in result.frameworks]
        assert "flask" in fw_names


def test_improved_compiler_entry_points():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "main.py").write_text("if __name__ == '__main__':\n    print('hi')\n")
        (tmp / "app.py").write_text("x = 1\n")

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("test")

        assert any("main" in ep for ep in result.entry_points)


def test_improved_compiler_no_task():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile()

        assert result.ranked_files == []
        assert result.repo_summary != ""


def test_improved_compiler_tokens_tracked():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "code.py").write_text("def f():\n    return 1\n")

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("What function?")
        assert result.total_tokens > 0
        assert result.compile_time_s >= 0


def test_improved_compiler_audit_trace():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Audit Test\n")

        cc = ImprovedContextCompiler(str(tmp))
        result = cc.compile("test question")

        trace_dir = Path(".lyme") / "audit"
        traces = list(trace_dir.glob("context-improved-*.json"))
        assert len(traces) > 0

        latest = max(traces, key=lambda f: f.stat().st_mtime)
        data = json.loads(latest.read_text())
        assert data["event"] == "context_compiled_improved"


def test_benchmark_imports():
    assert ContextBenchmark is not None


def test_benchmark_runs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Test\n")
        (tmp / "code.py").write_text("def f():\n    pass\n")

        bench = ContextBenchmark(str(tmp))
        results = bench.run_all()
        strategies = set(r.strategy for r in results)
        assert "raw" in strategies
        assert "current" in strategies
        assert "improved" in strategies
        assert len(results) > 0
        summary = bench.summary()
        assert "strategies" in summary
        assert "improved_vs_current" in summary


def test_ranked_file_dataclass():
    rf = RankedFile(path="test.py", relevance=0.85, reason="keyword match", classes=["Foo"], functions=["bar"])
    assert rf.path == "test.py"
    assert rf.relevance == 0.85
    assert "Foo" in rf.classes
    assert "bar" in rf.functions


def test_framework_info_dataclass():
    fw = FrameworkInfo(name="flask", files=["app.py"], version="2.0")
    assert fw.name == "flask"
    assert fw.files == ["app.py"]
