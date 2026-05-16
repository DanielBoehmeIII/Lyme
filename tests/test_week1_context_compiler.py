"""Week 1 — Context Compiler tests."""

import json
import tempfile
from pathlib import Path
from lyme_model.context import ContextCompiler, CompiledContext


def test_compiler_imports():
    assert ContextCompiler is not None
    assert CompiledContext is not None


def test_compiler_empty_repo():
    with tempfile.TemporaryDirectory() as tmp:
        cc = ContextCompiler(tmp)
        result = cc.compile()
        assert result.repo_summary != ""
        assert "not found" in result.repo_summary or "Repository:" in result.repo_summary


def test_compiler_python_repo():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "src").mkdir()
        (tmp / "src" / "main.py").write_text("def hello():\n    return 'hello'\n")
        (tmp / "src" / "utils.py").write_text("class Helper:\n    pass\n")
        (tmp / "README.md").write_text("# Test Repo\n")
        (tmp / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        cc = ContextCompiler(str(tmp))
        result = cc.compile("what does this do?")

        assert "Python files: 2" in result.repo_summary
        assert "Has README:" in result.repo_summary
        assert "src/" in result.structure
        assert result.total_tokens > 0
        assert result.compile_time_s > 0
        assert "pip install" in " ".join(result.build_commands)
        assert result.task_context != ""


def test_compiler_to_text():
    ctx = CompiledContext(
        repo_summary="Repo: test (42 files)",
        structure="src/\ntests/",
        api_surface="main.py: hello()",
        build_commands=["pip install -e ."],
        test_commands=["pytest"],
        risks=["config.py (secrets)"],
    )
    text = ctx.to_text()
    assert "REPOSITORY SUMMARY" in text
    assert "Repo: test" in text
    assert "STRUCTURE" in text
    assert "API SURFACE" in text
    assert "BUILD" in text
    assert "TESTS" in text
    assert "RISKS" in text


def test_compiler_to_dict():
    ctx = CompiledContext(repo_summary="Repo: test", total_tokens=100, compile_time_s=0.5)
    d = ctx.to_dict()
    assert d["repo_summary"] == "Repo: test"
    assert d["total_tokens"] == 100
    assert d["compile_time_s"] == 0.5
    assert "text" in d


def test_compiler_extract_commands():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "Makefile").write_text("build:\n\techo build\ntest:\n\techo test\n")
        (tmp / "package.json").write_text('{"scripts": {"build": "echo", "test": "echo"}}\n')

        cc = ContextCompiler(str(tmp))
        # Manually call _extract_commands
        build, test = cc._extract_commands()
        assert "make build" in build
        assert "npm test" in test or "make test" in test


def test_compiler_find_risky_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "config.py").write_text("API_KEY = 'sk-123'\n")
        (tmp / "safe.py").write_text("x = 1\n")

        cc = ContextCompiler(str(tmp))
        risks = cc._find_risky_files()
        risk_names = [r for r in risks if "config.py" in r]
        assert len(risk_names) > 0
        # safe.py should not be flagged
        safe_flagged = [r for r in risks if "safe.py" in r]
        assert len(safe_flagged) == 0


def test_compiler_summarize_repo():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Mini Project\n")
        (tmp / "hello.py").write_text("print('hi')\n")
        (tmp / "test_hello.py").write_text("def test():\n    pass\n")

        cc = ContextCompiler(str(tmp))
        summary = cc._summarize_repo()
        assert "Mini Project" in summary or tmp.name in summary
        assert "README" in summary or "Has README" in summary


def test_compiler_truncation():
    ctx = CompiledContext(
        repo_summary="A" * 5000,
        api_surface="B" * 5000,
        structure="C" * 5000,
        total_tokens=10000,
    )
    cc = ContextCompiler(".")
    truncated = cc._truncate(ctx, 500)
    assert truncated.total_tokens <= 500 or truncated.total_tokens < ctx.total_tokens


def test_compiler_audit_trace():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text("# Audit Test\n")

        cc = ContextCompiler(str(tmp))
        result = cc.compile("test question")

        trace_dir = Path(".lyme") / "audit"
        traces = list(trace_dir.glob("context-*.json"))
        assert len(traces) > 0

        latest = max(traces, key=lambda f: f.stat().st_mtime)
        data = json.loads(latest.read_text())
        assert data["event"] == "context_compiled"
        assert data["total_tokens"] == result.total_tokens
