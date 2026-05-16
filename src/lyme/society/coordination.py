from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TopologyType(str, Enum):
    STAR = "star"
    RING = "ring"
    MESH = "mesh"
    TREE = "tree"
    LINE = "line"
    FULLY_CONNECTED = "fully_connected"


@dataclass
class IntentPacket:
    agent_id: str = ""
    intent: str = ""
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    uncertainty: float = 0.0
    token_budget: int = 0
    timestamp: float = field(default_factory=time.time)
    compressed: bool = False
    original_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "intent": self.intent[:100],
            "priority": self.priority,
            "dependencies": self.dependencies[:5],
            "uncertainty": self.uncertainty,
            "token_budget": self.token_budget,
            "compressed": self.compressed,
            "original_length": self.original_length,
        }


@dataclass
class DependencySummary:
    agent_id: str = ""
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    critical_path: bool = False
    blocking_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "depends_on": self.depends_on[:5],
            "depended_by": self.depended_by[:5],
            "critical_path": self.critical_path,
            "blocking_count": self.blocking_count,
        }


@dataclass
class PartialState:
    agent_id: str = ""
    state_type: str = ""
    data_summary: str = ""
    version: int = 0
    timestamp: float = field(default_factory=time.time)
    checksum: str = ""
    compressed_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state_type": self.state_type,
            "data_summary": self.data_summary[:100],
            "version": self.version,
            "compressed_size": self.compressed_size,
        }


@dataclass
class CompressedPacket:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender_id: str = ""
    recipient_id: str = ""
    intent: IntentPacket = field(default_factory=IntentPacket)
    dependency: Optional[DependencySummary] = None
    state: Optional[PartialState] = None
    compression_ratio: float = 0.0
    information_loss: float = 0.0
    size_bytes: int = 0
    original_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "intent": self.intent.to_dict(),
            "dependency": self.dependency.to_dict() if self.dependency else None,
            "compression_ratio": self.compression_ratio,
            "information_loss": self.information_loss,
            "size_bytes": self.size_bytes,
            "original_size_bytes": self.original_size_bytes,
        }


@dataclass
class SynchronizationRule:
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    condition: str = ""
    sync_type: str = ""
    priority: int = 0
    requires_ack: bool = True
    timeout_ms: int = 5000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "condition": self.condition,
            "sync_type": self.sync_type,
            "priority": self.priority,
            "requires_ack": self.requires_ack,
        }


@dataclass
class CoordinationBenchmark:
    scenario: str = ""
    agent_count: int = 0
    coordination_rounds: int = 0
    total_messages: int = 0
    total_bytes: int = 0
    compression_savings: float = 0.0
    information_loss: float = 0.0
    coordination_overhead_ms: float = 0.0
    tasks_completed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "agent_count": self.agent_count,
            "coordination_rounds": self.coordination_rounds,
            "total_messages": self.total_messages,
            "total_bytes": self.total_bytes,
            "compression_savings": self.compression_savings,
            "information_loss": self.information_loss,
            "coordination_overhead_ms": self.coordination_overhead_ms,
            "tasks_completed": self.tasks_completed,
        }


class CoordinationCompressor:
    def __init__(self):
        self._packets: List[CompressedPacket] = []
        self._compression_stats: Dict[str, float] = defaultdict(float)

    def compress_intent(self, intent: str, max_tokens: int = 50) -> IntentPacket:
        original_length = len(intent)
        words = intent.split()
        compressed_words = words[:max_tokens] if len(words) > max_tokens else words

        key_phrases = []
        for phrase in ["need to", "should", "must", "requires", "depends on", "after"]:
            if phrase in intent.lower():
                key_phrases.append(phrase)

        summary_words = []
        if key_phrases:
            for kw in key_phrases:
                idx = intent.lower().find(kw)
                if idx >= 0:
                    summary_words.append(intent[idx:idx + 60])

        compressed_text = " ".join(summary_words) if summary_words else " ".join(compressed_words[:10])

        is_compressed = len(compressed_words) < len(words)
        return IntentPacket(
            intent=compressed_text or intent[:50],
            compressed=is_compressed,
            original_length=original_length,
        )

    def compress_dependency(self, dependencies: List[str]) -> DependencySummary:
        return DependencySummary(
            depends_on=dependencies[:5],
            depended_by=[],
            critical_path=False,
            blocking_count=0,
        )

    def compress_state(self, agent_id: str, state_data: Dict[str, Any]) -> PartialState:
        keys = list(state_data.keys())
        return PartialState(
            agent_id=agent_id,
            state_type=",".join(keys[:5]) if keys else "unknown",
            data_summary=f"State with {len(keys)} keys, versions: {len(state_data)}",
            version=1,
            compressed_size=len(str(state_data)) // 3,
        )

    def create_packet(
        self, sender: str, recipient: str, intent: str,
        dependencies: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> CompressedPacket:
        intent_packet = self.compress_intent(intent)
        dep_summary = self.compress_dependency(dependencies) if dependencies else None
        partial_state = self.compress_state(sender, state) if state else None

        original_size = len(intent) + (len(str(dependencies)) if dependencies else 0) + (len(str(state)) if state else 0)
        compressed_size = len(intent_packet.intent) + (50 if dep_summary else 0) + (100 if partial_state else 0)

        ratio = compressed_size / max(original_size, 1)
        loss = 1.0 - ratio if original_size > 0 else 0.0

        packet = CompressedPacket(
            sender_id=sender,
            recipient_id=recipient,
            intent=intent_packet,
            dependency=dep_summary,
            state=partial_state,
            compression_ratio=1.0 - ratio,
            information_loss=loss * 0.3,
            size_bytes=compressed_size,
            original_size_bytes=original_size,
        )
        self._packets.append(packet)
        return packet

    def get_stats(self) -> Dict[str, float]:
        if not self._packets:
            return {"avg_compression_ratio": 0, "avg_information_loss": 0, "total_packets": 0}

        return {
            "avg_compression_ratio": sum(p.compression_ratio for p in self._packets) / len(self._packets),
            "avg_information_loss": sum(p.information_loss for p in self._packets) / len(self._packets),
            "total_packets": len(self._packets),
            "total_bytes_saved": sum(p.original_size_bytes - p.size_bytes for p in self._packets),
        }


class TopologyExperiment:
    def __init__(self):
        self.results: List[CoordinationBenchmark] = []

    def simulate(self, topology: TopologyType, agent_count: int, task_count: int) -> CoordinationBenchmark:
        compressor = CoordinationCompressor()
        total_messages = 0
        total_bytes = 0

        agents = [f"agent_{i}" for i in range(agent_count)]
        connections = self._build_topology(topology, agents)

        for task in range(task_count):
            for sender in agents:
                recipients = connections.get(sender, [])
                for recipient in recipients:
                    if sender != recipient:
                        packet = compressor.create_packet(
                            sender, recipient,
                            f"Task {task}: coordinate on subtask {hash(task) % 5}",
                            dependencies=[a for a in agents if a != sender][:3],
                            state={"task_id": task, "status": "in_progress"},
                        )
                        total_messages += 1
                        total_bytes += packet.size_bytes

        benchmark = CoordinationBenchmark(
            scenario=f"{topology.value}_{agent_count}agents_{task_count}tasks",
            agent_count=agent_count,
            coordination_rounds=task_count,
            total_messages=total_messages,
            total_bytes=total_bytes,
            compression_savings=compressor.get_stats().get("avg_compression_ratio", 0),
            information_loss=compressor.get_stats().get("avg_information_loss", 0),
            coordination_overhead_ms=total_messages * 5,
            tasks_completed=task_count,
        )
        self.results.append(benchmark)
        return benchmark

    def _build_topology(self, topology: TopologyType, agents: List[str]) -> Dict[str, List[str]]:
        connections: Dict[str, List[str]] = {a: [] for a in agents}

        if topology == TopologyType.FULLY_CONNECTED:
            for a in agents:
                connections[a] = [b for b in agents if b != a]

        elif topology == TopologyType.STAR:
            hub = agents[0]
            for a in agents:
                if a != hub:
                    connections[hub].append(a)
                    connections[a].append(hub)

        elif topology == TopologyType.RING:
            for i, a in enumerate(agents):
                connections[a].append(agents[(i + 1) % len(agents)])
                connections[a].append(agents[(i - 1) % len(agents)])

        elif topology == TopologyType.TREE:
            for i, a in enumerate(agents):
                if i > 0:
                    parent = agents[(i - 1) // 2]
                    connections[parent].append(a)
                    connections[a].append(parent)

        elif topology == TopologyType.LINE:
            for i, a in enumerate(agents):
                if i > 0:
                    connections[a].append(agents[i - 1])
                if i < len(agents) - 1:
                    connections[a].append(agents[i + 1])

        elif topology == TopologyType.MESH:
            for i, a in enumerate(agents):
                for j in range(max(0, i - 2), min(len(agents), i + 3)):
                    if i != j:
                        connections[a].append(agents[j])

        return connections

    def compare_topologies(self) -> List[Dict[str, Any]]:
        comparisons = []
        for result in self.results:
            comparisons.append({
                "scenario": result.scenario,
                "messages": result.total_messages,
                "bytes": result.total_bytes,
                "compression": result.compression_savings,
                "overhead_ms": result.coordination_overhead_ms,
                "efficiency": result.tasks_completed / max(result.total_messages, 1),
            })
        return sorted(comparisons, key=lambda c: -c["efficiency"])
