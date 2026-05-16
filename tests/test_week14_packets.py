"""Week 14 — Long-context simulation via context packet tests."""

from lyme_model.context.packets import (
    TaskPacket, SubtaskPacket, EvidenceChain, PacketManager,
)


def test_evidence_chain():
    e = EvidenceChain(claim="framework is flask", source_file="app.py", source_line=1, excerpt="import flask")
    assert e.source_file == "app.py"
    text = e.to_text()
    assert "app.py" in text
    assert "flask" in text


def test_subtask_packet():
    sp = SubtaskPacket(subtask_id="s1", name="Find framework", description="detect framework from imports")
    assert sp.status == "pending"
    sp.status = "completed"
    sp.result = "Flask detected"
    assert sp.to_text() is not None


def test_subtask_with_evidence():
    sp = SubtaskPacket(subtask_id="s1", name="Check config")
    e = EvidenceChain(claim="found config", source_file="config.py", source_line=5, excerpt="DEBUG=True")
    sp.evidence = [e]
    text = sp.to_text()
    assert "config.py" in text


def test_task_packet():
    tp = TaskPacket(task_id="t1", goal="Fix login bug")
    assert tp.goal == "Fix login bug"
    assert len(tp.subtasks) == 0


def test_task_packet_add_subtask():
    tp = TaskPacket(task_id="t1", goal="Fix login")
    sp = tp.add_subtask("Find auth module", "locate auth files")
    assert sp.name == "Find auth module"
    assert len(tp.subtasks) == 1


def test_task_packet_compile():
    tp = TaskPacket(task_id="t1", goal="Fix login bug")
    tp.add_subtask("Check auth", "find auth module")
    tp.previous_state = "Started investigation"
    text = tp.compile()
    assert "Fix login bug" in text
    assert "Check auth" in text


def test_task_packet_estimate_tokens():
    tp = TaskPacket(task_id="t1", goal="Fix bug")
    tp.add_subtask("Step 1", "do thing")
    assert tp.estimate_tokens() > 0


def test_packet_manager_create():
    pm = PacketManager()
    tp = pm.create_task("Fix login")
    assert tp.task_id is not None


def test_packet_manager_run_subtask():
    pm = PacketManager()
    tp = pm.create_task("Fix login")
    sp = tp.add_subtask("Find auth", "locate auth")
    evidence = [EvidenceChain(claim="found auth.py", source_file="auth.py", source_line=1, excerpt="def login")]
    pm.run_subtask(tp, sp, "auth.py found", evidence)
    assert sp.status == "completed"
    assert len(tp.accumulated_evidence) == 1


def test_packet_manager_fail_subtask():
    pm = PacketManager()
    tp = pm.create_task("Fix login")
    sp = tp.add_subtask("Find auth", "locate auth")
    pm.fail_subtask(tp, sp, "File not found")
    assert sp.status == "failed"
    assert sp.error == "File not found"


def test_packet_manager_compile_for_model():
    pm = PacketManager(max_tokens_per_packet=100)
    tp = pm.create_task("Fix login bug " * 100)
    text = pm.compile_for_model(tp)
    assert "TRUNCATED" in text or len(text.split()) <= 100


def test_packet_manager_emits_traces():
    import json
    from pathlib import Path
    pm = PacketManager()
    tp = pm.create_task("Test task")
    sp = tp.add_subtask("Subtask 1", "test")
    pm.run_subtask(tp, sp, "done")
    trace_dir = Path(".lyme") / "audit"
    traces = list(trace_dir.glob("packet-*.json"))
    assert len(traces) > 0
