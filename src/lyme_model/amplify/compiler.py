"""Week 76 — Context Packet Compiler.

Compiles repo information into small, model-readable packets.
8 specialized packet types optimized for small models and low context windows.

Builds on the existing SmallModelContextAssembler in assembler.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import re


@dataclass
class TaskPacket:
    """What the model needs to do — minimal, unambiguous."""
    task_type: str = ""
    description: str = ""
    target_files: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    expected_output_shape: str = ""

    def compile(self) -> str:
        parts = [f"TASK: {self.task_type}"]
        if self.description:
            parts.append(f"  {self.description}")
        if self.target_files:
            parts.append(f"  Files: {', '.join(self.target_files)}")
        if self.constraints:
            for c in self.constraints:
                parts.append(f"  Constraint: {c}")
        if self.expected_output_shape:
            parts.append(f"  Expected: {self.expected_output_shape}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class FilePacket:
    """Single file summary — path, purpose, key symbols, length."""
    path: str = ""
    purpose: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    loc: int = 0

    def compile(self) -> str:
        parts = [f"FILE: {self.path}"]
        if self.purpose:
            parts.append(f"  Purpose: {self.purpose}")
        if self.classes:
            parts.append(f"  Classes: {', '.join(self.classes[:8])}")
        if self.functions:
            parts.append(f"  Functions: {', '.join(self.functions[:12])}")
        if self.exports:
            parts.append(f"  Exports: {', '.join(self.exports[:8])}")
        if self.dependencies:
            parts.append(f"  Depends: {', '.join(self.dependencies[:8])}")
        parts.append(f"  LOC: {self.loc}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class APIPacket:
    """Public API surface — what's available, how to call it."""
    module_path: str = ""
    functions: List[Dict[str, str]] = field(default_factory=list)
    classes: List[Dict[str, str]] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)

    def compile(self) -> str:
        parts = [f"API: {self.module_path}"]
        for fn in self.functions[:15]:
            sig = fn.get("signature", fn.get("name", "?"))
            doc = fn.get("doc", "")[:60]
            parts.append(f"  def {sig}")
            if doc:
                parts.append(f"    {doc}")
        for cls in self.classes[:8]:
            name = cls.get("name", "?")
            methods = cls.get("methods", [])
            parts.append(f"  class {name}")
            for m in methods[:6]:
                parts.append(f"    .{m}")
        if self.constants:
            parts.append(f"  Constants: {', '.join(self.constants[:10])}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class DependencyPacket:
    """Dependency relationships — who imports what."""
    module: str = ""
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    external_deps: List[str] = field(default_factory=list)
    circular_deps: List[str] = field(default_factory=list)

    def compile(self) -> str:
        parts = [f"DEPS: {self.module}"]
        if self.imports:
            parts.append(f"  Imports: {', '.join(self.imports[:12])}")
        if self.imported_by:
            parts.append(f"  Imported by: {', '.join(self.imported_by[:8])}")
        if self.external_deps:
            parts.append(f"  External: {', '.join(self.external_deps[:8])}")
        if self.circular_deps:
            parts.append(f"  CIRCULAR: {', '.join(self.circular_deps)}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class TestPacket:
    """Test coverage — what's tested, what's not, how to run."""
    target_module: str = ""
    test_files: List[str] = field(default_factory=list)
    test_functions: List[str] = field(default_factory=list)
    test_command: str = ""
    last_result: str = ""
    coverage_gaps: List[str] = field(default_factory=list)

    def compile(self) -> str:
        parts = [f"TESTS: {self.target_module}"]
        if self.test_files:
            parts.append(f"  Files: {', '.join(self.test_files)}")
        if self.test_functions:
            parts.append(f"  Tests: {', '.join(self.test_functions[:10])}")
        if self.test_command:
            parts.append(f"  Run: {self.test_command}")
        if self.last_result:
            parts.append(f"  Last: {self.last_result[:80]}")
        if self.coverage_gaps:
            parts.append(f"  Untested: {', '.join(self.coverage_gaps[:6])}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class ErrorPacket:
    """Error/failure context — what went wrong, stack trace, affected area."""
    error_type: str = ""
    message: str = ""
    file: str = ""
    line: int = 0
    stack_summary: List[str] = field(default_factory=list)
    affected_symbols: List[str] = field(default_factory=list)
    reproduction_steps: str = ""

    def compile(self) -> str:
        parts = [f"ERROR: {self.error_type}"]
        if self.message:
            parts.append(f"  {self.message[:120]}")
        if self.file:
            location = f"{self.file}"
            if self.line:
                location += f":{self.line}"
            parts.append(f"  At: {location}")
        if self.stack_summary:
            parts.append(f"  Stack:")
            for s in self.stack_summary[:5]:
                parts.append(f"    {s}")
        if self.affected_symbols:
            parts.append(f"  Affects: {', '.join(self.affected_symbols[:6])}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class InvariantPacket:
    """Invariants the codebase depends on — must not break."""
    invariants: List[Dict[str, str]] = field(default_factory=list)

    def compile(self) -> str:
        if not self.invariants:
            return "INVARIANTS: none"
        parts = ["INVARIANTS:"]
        for inv in self.invariants[:10]:
            desc = inv.get("description", str(inv)[:100])
            severity = inv.get("severity", "must")
            parts.append(f"  [{severity}] {desc}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


@dataclass
class PatchPacket:
    """Patch plan — what changed, what's the expected effect."""
    file: str = ""
    change_type: str = ""  # add, modify, delete, rename
    summary: str = ""
    added_lines: int = 0
    removed_lines: int = 0
    affected_symbols: List[str] = field(default_factory=list)
    verification_command: str = ""
    rollback_command: str = ""

    def compile(self) -> str:
        parts = [f"PATCH: {self.file}"]
        if self.change_type:
            parts.append(f"  Type: {self.change_type}")
        if self.summary:
            parts.append(f"  {self.summary[:120]}")
        if self.added_lines or self.removed_lines:
            parts.append(f"  +{self.added_lines} / -{self.removed_lines} lines")
        if self.affected_symbols:
            parts.append(f"  Affects: {', '.join(self.affected_symbols[:8])}")
        if self.verification_command:
            parts.append(f"  Verify: {self.verification_command}")
        if self.rollback_command:
            parts.append(f"  Rollback: {self.rollback_command}")
        return "\n".join(parts)

    def token_count(self) -> int:
        return len(self.compile().split())


PACKET_TYPES = {
    "task": TaskPacket,
    "file": FilePacket,
    "api": APIPacket,
    "dependency": DependencyPacket,
    "test": TestPacket,
    "error": ErrorPacket,
    "invariant": InvariantPacket,
    "patch": PatchPacket,
}


class ContextPacketCompiler:
    """Compiles repo information into model-readable packets.

    Optimizes for:
    - small models (3-8B)
    - low context windows (2K-8K)
    - minimal ambiguity
    - high evidence density
    - stable formatting
    """

    def __init__(self, max_tokens: int = 2048):
        self.max_tokens = max_tokens
        self.packets: Dict[str, Any] = {}

    def compile_task(self, task_type: str, description: str,
                     target_files: Optional[List[str]] = None,
                     constraints: Optional[List[str]] = None) -> TaskPacket:
        p = TaskPacket(
            task_type=task_type,
            description=description,
            target_files=target_files or [],
            constraints=constraints or [],
        )
        self.packets["task"] = p
        return p

    def compile_file(self, path: str, text: str) -> FilePacket:
        p = FilePacket(path=path)
        p.classes = re.findall(r'^class\s+(\w+)', text, re.MULTILINE)
        p.functions = re.findall(r'^def\s+(\w+)', text, re.MULTILINE)
        p.exports = re.findall(r'^__all__\s*=\s*\[([^\]]+)', text, re.MULTILINE)
        if p.exports:
            p.exports = [e.strip().strip("'\"") for e in p.exports[0].split(",")]
        p.dependencies = re.findall(r'^(?:from|import)\s+([\w.]+)', text, re.MULTILINE)
        p.dependencies = list(set(p.dependencies))[:12]
        # Extract docstring as purpose
        doc_match = re.search(r'"""(.*?)"""', text, re.DOTALL)
        if doc_match:
            p.purpose = doc_match.group(1).strip()[:120]
        p.loc = len(text.split("\n"))
        self.packets["file"] = p
        return p

    def compile_api(self, module_path: str, text: str) -> APIPacket:
        p = APIPacket(module_path=module_path)
        for m in re.finditer(r'^def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?\s*:', text, re.MULTILINE):
            fn = {"name": m.group(1), "signature": f"{m.group(1)}({m.group(2)})"}
            if m.group(3):
                fn["signature"] += f" -> {m.group(3)}"
            # Get docstring
            pos = m.end()
            doc_match = re.search(r'"""(.*?)"""', text[pos:pos+200], re.DOTALL)
            if doc_match:
                fn["doc"] = doc_match.group(1).strip()[:60]
            p.functions.append(fn)
        for m in re.finditer(r'^class\s+(\w+)', text, re.MULTILINE):
            cls = {"name": m.group(1), "methods": []}
            cls_pos = m.end()
            cls_text = text[cls_pos:cls_pos+500]
            cls["methods"] = re.findall(r'^    def\s+(\w+)', cls_text, re.MULTILINE)
            p.classes.append(cls)
        self.packets["api"] = p
        return p

    def compile_dependency(self, module: str, files: List[str]) -> DependencyPacket:
        p = DependencyPacket(module=module)
        all_imports = []
        imported_by_map: Dict[str, List[str]] = {}
        for f in files:
            try:
                text = Path(f).read_text(errors="ignore")
                imports = re.findall(r'^(?:from|import)\s+([\w.]+)', text, re.MULTILINE)
                all_imports.extend(imports)
                rel = Path(f).name
                for imp in imports:
                    imported_by_map.setdefault(imp, []).append(rel)
            except Exception:
                pass
        p.imports = list(set(all_imports))[:12]
        # Check for circular deps
        for imp in p.imports:
            if imp in [f.name.replace(".py", "") for f in Path(module).parent.rglob("*.py")]:
                for f2 in files:
                    if imp in Path(f2).read_text(errors="ignore"):
                        p.circular_deps.append(f"{module} <-> {imp}")
        self.packets["dependency"] = p
        return p

    def compile_test(self, target: str, test_files: List[str],
                     test_command: str = "") -> TestPacket:
        p = TestPacket(
            target_module=target,
            test_files=test_files,
            test_command=test_command,
        )
        for tf in test_files:
            try:
                text = Path(tf).read_text(errors="ignore")
                tests = re.findall(r'^def\s+(test_\w+)', text, re.MULTILINE)
                p.test_functions.extend(tests)
            except Exception:
                pass
        self.packets["test"] = p
        return p

    def compile_error(self, error_type: str, message: str, file: str = "",
                      line: int = 0) -> ErrorPacket:
        p = ErrorPacket(
            error_type=error_type,
            message=message,
            file=file,
            line=line,
        )
        # Parse stack summary from message
        stack_lines = re.findall(r'^\s*File\s+"([^"]+)",\s+line\s+(\d+)', message, re.MULTILINE)
        for sf, sl in stack_lines[:5]:
            p.stack_summary.append(f"{sf}:{sl}")
        # Extract affected symbols
        symbols = re.findall(r'(?:NameError|AttributeError|ImportError):\s*(?:\'([^\']+)\')', message)
        p.affected_symbols = symbols
        self.packets["error"] = p
        return p

    def compile_invariant(self, invariants: List[Dict[str, str]]) -> InvariantPacket:
        p = InvariantPacket(invariants=invariants)
        self.packets["invariant"] = p
        return p

    def compile_patch(self, file: str, change_type: str, summary: str,
                      verification: str = "", rollback: str = "") -> PatchPacket:
        p = PatchPacket(
            file=file,
            change_type=change_type,
            summary=summary,
            verification_command=verification,
            rollback_command=rollback,
        )
        self.packets["patch"] = p
        return p

    def compile_all(self, repo_info: Dict) -> str:
        """Compile all available packets into a single context string."""
        sections = []
        total_tokens = 0
        budget_per_packet = self.max_tokens // 8

        for ptype in ["task", "file", "api", "dependency", "test",
                       "error", "invariant", "patch"]:
            packet = self.packets.get(ptype)
            if packet is None:
                continue
            content = packet.compile()
            tokens = packet.token_count()
            if tokens > budget_per_packet:
                continue
            sections.append(content)
            total_tokens += tokens
            if total_tokens >= self.max_tokens:
                break

        return "\n\n".join(sections)

    def benchmark_compression(self, raw_text: str) -> Dict:
        """Compare packet format vs raw text size."""
        compiled = self.compile_all({})
        return {
            "raw_tokens": len(raw_text.split()),
            "packet_tokens": len(compiled.split()),
            "compression_ratio": len(compiled.split()) / max(len(raw_text.split()), 1),
            "packets_compiled": len(self.packets),
        }
