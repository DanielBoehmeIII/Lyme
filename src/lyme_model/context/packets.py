"""Week 14 — Long-context simulation via context packets.

Simulates long-context reasoning without actually having long context windows.
Instead of massive prompts, compile task packets + subtask packets + previous state summaries + evidence chains.

For small models (3-8B) with limited context windows (4K-32K tokens).
"""

from __future__ import annotations
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path


@dataclass
class EvidenceChain:
    claim: str = ""
    source_file: str = ""
    source_line: int = 0
    excerpt: str = ""
    confidence: float = 0.0

    def to_text(self) -> str:
        return f"[{self.source_file}:{self.source_line}] {self.excerpt[:150]}"


@dataclass
class SubtaskPacket:
    subtask_id: str = ""
    name: str = ""
    description: str = ""
    status: str = "pending"
    evidence: List[EvidenceChain] = field(default_factory=list)
    result: str = ""
    error: Optional[str] = None
    tokens_used: int = 0

    def to_text(self) -> str:
        lines = [f"  Subtask: {self.name} [{self.status}]"]
        if self.description:
            lines.append(f"    {self.description}")
        if self.evidence:
            for e in self.evidence:
                lines.append(f"    Evidence: {e.to_text()}")
        if self.result:
            lines.append(f"    Result: {self.result[:200]}")
        if self.error:
            lines.append(f"    Error: {self.error}")
        return "\n".join(lines)


@dataclass
class TaskPacket:
    task_id: str = ""
    goal: str = ""
    subtasks: List[SubtaskPacket] = field(default_factory=list)
    previous_state: str = ""
    accumulated_evidence: List[EvidenceChain] = field(default_factory=list)
    total_tokens_used: int = 0

    def add_subtask(self, name: str, description: str) -> SubtaskPacket:
        sp = SubtaskPacket(
            subtask_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
        )
        self.subtasks.append(sp)
        return sp

    def compile(self) -> str:
        sections = [f"TASK: {self.goal}"]

        if self.previous_state:
            sections.append(f"\nPREVIOUS STATE:\n{self.previous_state[:500]}")

        if self.accumulated_evidence:
            sections.append("\nACCUMULATED EVIDENCE:")
            for e in self.accumulated_evidence[-5:]:
                sections.append(f"  {e.to_text()}")

        if self.subtasks:
            sections.append("\nSUBTASKS:")
            for s in self.subtasks:
                sections.append(s.to_text())

        return "\n".join(sections)

    def estimate_tokens(self) -> int:
        return len(self.compile().split())


class PacketManager:
    """Manages task/subtask packet lifecycle for long-context simulation.

    Flow:
    1. Create TaskPacket for overall goal
    2. Add SubtaskPackets for each unit of work
    3. Each subtask completes with its own evidence and result
    4. Previous subtask results feed into next subtask's context
    5. Accumulated evidence chain preserved throughout
    """

    def __init__(self, max_tokens_per_packet: int = 2000):
        self.max_tokens_per_packet = max_tokens_per_packet
        self.packets: Dict[str, TaskPacket] = {}

    def create_task(self, goal: str) -> TaskPacket:
        packet = TaskPacket(
            task_id=str(uuid.uuid4())[:8],
            goal=goal,
        )
        self.packets[packet.task_id] = packet
        return packet

    def run_subtask(self, packet: TaskPacket, subtask: SubtaskPacket, 
                    result: str, evidence: Optional[List[EvidenceChain]] = None) -> None:
        """Record subtask completion and update accumulated evidence."""
        subtask.status = "completed"
        subtask.result = result
        if evidence:
            subtask.evidence = evidence
            packet.accumulated_evidence.extend(evidence)

        packet.total_tokens_used += subtask.tokens_used
        packet.previous_state = f"Completed {sum(1 for s in packet.subtasks if s.status == 'completed')}/{len(packet.subtasks)} subtasks"

        self._emit_trace(packet, subtask)

    def fail_subtask(self, packet: TaskPacket, subtask: SubtaskPacket, error: str) -> None:
        subtask.status = "failed"
        subtask.error = error

    def compile_for_model(self, packet: TaskPacket) -> str:
        """Compile packet into model-readable text, fitting within budget."""
        text = packet.compile()
        if packet.estimate_tokens() > self.max_tokens_per_packet:
            text = self._truncate(text)
        return text

    def _truncate(self, text: str) -> str:
        words = text.split()
        budget_words = self.max_tokens_per_packet
        if len(words) > budget_words:
            words = words[:budget_words]
            words.append("[TRUNCATED...]")
        return " ".join(words)

    def _emit_trace(self, packet: TaskPacket, subtask: SubtaskPacket) -> None:
        trace = {
            "event": "subtask_completed",
            "packet_id": packet.task_id,
            "subtask_id": subtask.subtask_id,
            "task_goal": packet.goal[:60],
            "subtask_name": subtask.name,
            "status": subtask.status,
            "completed_subtasks": sum(1 for s in packet.subtasks if s.status == "completed"),
            "total_subtasks": len(packet.subtasks),
            "evidence_count": len(packet.accumulated_evidence),
            "tokens_used": packet.total_tokens_used,
        }
        trace_dir = Path(".lyme") / "audit"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"packet-{subtask.subtask_id}.json"
        trace_file.write_text(json.dumps(trace, indent=2))
