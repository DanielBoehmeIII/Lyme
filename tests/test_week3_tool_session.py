"""Week 3 — Local Tool Use v0 tests."""

import json
import tempfile
from pathlib import Path
from lyme_model.tools import (
    ToolSession, ToolCallParser, ToolCall,
    SafetyMode,
)


def test_tool_call_parser_simple():
    text = "TOOL: read_file(path=src/main.py)"
    calls = ToolCallParser.parse(text)
    assert len(calls) == 1
    assert calls[0].tool_name == "read_file"
    assert calls[0].params["path"] == "src/main.py"


def test_tool_call_parser_multiple():
    text = "First I will read the file.\nTOOL: read_file(path=src/main.py)\nThen search.\nTOOL: grep_search(pattern=def hello)"
    calls = ToolCallParser.parse(text)
    assert len(calls) == 2
    assert calls[0].tool_name == "read_file"
    assert calls[1].tool_name == "grep_search"


def test_tool_call_parser_variations():
    text = "tool: list_directory(path=.)\nTool: read_file(path=test.py)\nTOOL: git_log(path=.)"
    calls = ToolCallParser.parse(text)
    assert len(calls) == 3


def test_tool_call_parser_no_calls():
    assert ToolCallParser.parse("Just some text without tool calls") == []


def test_tool_call_parser_empty():
    assert ToolCallParser.parse("") == []


def test_tool_call_dataclass():
    tc = ToolCall(tool_name="read_file", params={"path": "test.py"}, raw_line="TOOL: read_file(path=test.py)")
    assert tc.tool_name == "read_file"
    assert tc.params["path"] == "test.py"
    d = tc.to_dict()
    assert d["tool"] == "read_file"


def test_tool_session_readonly_blocks_edit():
    session = ToolSession(repo_path=".", safety_mode="readonly")
    text = "TOOL: edit_file(path=test.py, content=test)"
    traces = session.execute_model_tool_calls(text)
    assert len(traces) == 1
    assert traces[0].result is not None
    assert not traces[0].result.success
    assert "readonly" in (traces[0].error or "").lower()


def test_tool_session_readonly_allows_read():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "test.py").write_text("x = 1")
        session = ToolSession(repo_path=str(tmp), safety_mode="readonly")
        text = "TOOL: read_file(path=test.py)"
        traces = session.execute_model_tool_calls(text)
        assert len(traces) == 1
        assert traces[0].result.success
        assert traces[0].result.output == "x = 1"


def test_tool_session_list_directory():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "file1.py").write_text("")
        (tmp / "file2.py").write_text("")
        session = ToolSession(repo_path=str(tmp), safety_mode="readonly")
        text = "TOOL: list_directory(path=.)"
        traces = session.execute_model_tool_calls(text)
        assert len(traces) == 1
        assert traces[0].result.success
        assert "file1.py" in traces[0].result.output


def test_tool_session_grep_search():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "code.py").write_text("def hello():\n    pass\n")
        session = ToolSession(repo_path=str(tmp), safety_mode="readonly")
        text = "TOOL: grep_search(pattern=hello)"
        traces = session.execute_model_tool_calls(text)
        assert len(traces) == 1
        assert traces[0].result.success
        assert "hello" in traces[0].result.output


def test_tool_session_tracks_latency():
    session = ToolSession(repo_path=".", safety_mode="readonly")
    text = "TOOL: grep_search(pattern=import)"
    traces = session.execute_model_tool_calls(text)
    assert len(traces) == 1
    assert traces[0].latency_ms > 0


def test_tool_session_emits_traces():
    session = ToolSession(repo_path=".", safety_mode="readonly")
    text = "TOOL: grep_search(pattern=import)"
    session.execute_model_tool_calls(text)
    trace_dir = Path(".lyme") / "audit"
    traces_files = list(trace_dir.glob("tool-*.json"))
    assert len(traces_files) > 0


def test_tool_session_max_calls():
    session = ToolSession(repo_path=".", safety_mode="readonly", max_tool_calls=2)
    text = "TOOL: list_directory(path=.)\nTOOL: list_directory(path=.)\nTOOL: list_directory(path=.)"
    traces = session.execute_model_tool_calls(text)
    assert len(traces) <= 2


def test_tool_session_stats():
    session = ToolSession(repo_path=".", safety_mode="readonly")
    assert session.get_stats()["tool_calls"] == 0
    text = "TOOL: git_log(path=.)"
    session.execute_model_tool_calls(text)
    stats = session.get_stats()
    assert stats["tool_calls"] == 1


def test_tool_session_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "data.py").write_text("VERSION = '1.0'")
        session = ToolSession(repo_path=str(tmp), safety_mode="readonly")
        text = "TOOL: read_file(path=data.py)"
        session.execute_model_tool_calls(text)
        evidence = session.get_evidence_summary()
        assert len(evidence) > 0
        assert "read_file" in evidence[0]


def test_safety_mode_enum():
    assert SafetyMode.READONLY.value == "readonly"
    assert SafetyMode.CAREFUL.value == "careful"
    assert SafetyMode.FULL.value == "full"


def test_tool_session_accepts_string_safety():
    session = ToolSession(repo_path=".", safety_mode="readonly")
    assert session.safety_mode == SafetyMode.READONLY
    session2 = ToolSession(repo_path=".", safety_mode="careful")
    assert session2.safety_mode == SafetyMode.CAREFUL
