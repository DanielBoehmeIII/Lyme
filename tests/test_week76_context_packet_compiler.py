"""Tests for Week 76 — Context Packet Compiler."""

import pytest
from src.lyme_model.amplify.compiler import (
    ContextPacketCompiler,
    TaskPacket,
    FilePacket,
    APIPacket,
    DependencyPacket,
    TestPacket,
    ErrorPacket,
    InvariantPacket,
    PatchPacket,
    PACKET_TYPES,
)


class TestPacketTypes:
    def test_has_8_packet_types(self):
        assert len(PACKET_TYPES) == 8

    def test_task_packet(self):
        p = TaskPacket(task_type="bugfix", description="Fix login bug",
                       target_files=["auth.py"])
        text = p.compile()
        assert "TASK: bugfix" in text
        assert "auth.py" in text
        assert p.token_count() > 0

    def test_file_packet(self):
        p = FilePacket(path="src/main.py", purpose="Entry point",
                       classes=["App"], functions=["main", "setup"])
        text = p.compile()
        assert "FILE: src/main.py" in text
        assert "main" in text

    def test_api_packet(self):
        p = APIPacket(module_path="auth")
        p.functions.append({"name": "login", "signature": "login(user, pass)", "doc": "Authenticate"})
        text = p.compile()
        assert "API: auth" in text
        assert "login" in text

    def test_dependency_packet(self):
        p = DependencyPacket(module="app", imports=["os", "sys"])
        text = p.compile()
        assert "DEPS: app" in text
        assert "os" in text

    def test_test_packet(self):
        p = TestPacket(target_module="auth", test_files=["test_auth.py"])
        text = p.compile()
        assert "TESTS: auth" in text

    def test_error_packet(self):
        p = ErrorPacket(error_type="ImportError", message="No module named x",
                        file="main.py", line=10)
        text = p.compile()
        assert "ERROR: ImportError" in text
        assert "main.py" in text

    def test_invariant_packet(self):
        p = InvariantPacket(invariants=[
            {"description": "User must have email", "severity": "must"}
        ])
        text = p.compile()
        assert "INVARIANTS" in text

    def test_patch_packet(self):
        p = PatchPacket(file="auth.py", change_type="modify",
                        summary="Add validation", verification_command="pytest")
        text = p.compile()
        assert "PATCH: auth.py" in text
        assert "Verify:" in text


class TestContextPacketCompiler:
    def test_compiler_initializes(self):
        c = ContextPacketCompiler(max_tokens=2048)
        assert c.max_tokens == 2048
        assert c.packets == {}

    def test_compile_task_packet(self):
        c = ContextPacketCompiler()
        p = c.compile_task("bugfix", "Fix the login bug", ["auth.py"])
        assert isinstance(p, TaskPacket)
        assert p.task_type == "bugfix"

    def test_compile_file_packet(self):
        c = ContextPacketCompiler()
        code = '"""Main module."""\nclass App:\n    pass\ndef main():\n    pass\n'
        p = c.compile_file("main.py", code)
        assert isinstance(p, FilePacket)
        assert "App" in p.classes
        assert "main" in p.functions

    def test_compile_api_packet(self):
        c = ContextPacketCompiler()
        code = 'def login(user, pass):\n    """Authenticate user."""\n    pass\nclass User:\n    def get(self): pass\n'
        p = c.compile_api("auth.py", code)
        assert isinstance(p, APIPacket)
        assert len(p.functions) >= 1
        assert len(p.classes) >= 1

    def test_compile_error_packet(self):
        c = ContextPacketCompiler()
        p = c.compile_error("ValueError", "invalid value for x", "main.py", 42)
        assert isinstance(p, ErrorPacket)
        assert p.line == 42

    def test_compile_invariant_packet(self):
        c = ContextPacketCompiler()
        p = c.compile_invariant([
            {"description": "Must not break tests", "severity": "must"}
        ])
        assert isinstance(p, InvariantPacket)

    def test_compile_patch_packet(self):
        c = ContextPacketCompiler()
        p = c.compile_patch("auth.py", "modify", "Add input validation",
                           "pytest tests/test_auth.py", "git checkout auth.py")
        assert isinstance(p, PatchPacket)
        assert p.verification_command == "pytest tests/test_auth.py"

    def test_compile_test_packet(self):
        c = ContextPacketCompiler()
        p = c.compile_test("auth", ["test_auth.py"], "pytest test_auth.py")
        assert isinstance(p, TestPacket)
        assert p.test_command == "pytest test_auth.py"

    def test_compile_all_empty(self):
        c = ContextPacketCompiler()
        result = c.compile_all({})
        assert isinstance(result, str)

    def test_compile_all_with_packets(self):
        c = ContextPacketCompiler()
        c.compile_task("refactor", "Refactor auth", ["auth.py"])
        c.compile_file("auth.py", "class Auth:\n    pass")
        result = c.compile_all({})
        assert "REFACTOR" in result.upper() or "TASK:" in result

    def test_benchmark_compression(self):
        c = ContextPacketCompiler()
        raw = "def foo():\n    pass\n" * 100
        result = c.benchmark_compression(raw)
        assert "raw_tokens" in result
        assert "packet_tokens" in result
        assert "compression_ratio" in result
