"""DelegationGraph — task distribution across agents with dependency tracking."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum


class NodeType(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    REPAIRER = "repairer"
    ANALYZER = "analyzer"
    COORDINATOR = "coordinator"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class DelegationNode:
    id: str
    name: str
    agent_id: str
    node_type: NodeType
    task: str
    status: NodeStatus = NodeStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    confidence: float = 1.0
    duration_sec: float = 0.0
    retry_count: int = 0
    max_retries: int = 2
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "agent_id": self.agent_id,
            "node_type": self.node_type.value,
            "task": self.task[:80],
            "status": self.status.value,
            "dependencies": self.dependencies,
            "has_result": self.result is not None,
            "error": self.error[:80] if self.error else None,
            "confidence": round(self.confidence, 3),
            "duration_sec": round(self.duration_sec, 1),
            "retry_count": self.retry_count,
        }


@dataclass
class DelegationGraph:
    goal: str
    nodes: List[DelegationNode]
    created_at: float
    context: Dict = field(default_factory=dict)

    def ready_nodes(self) -> List[DelegationNode]:
        completed = {n.id for n in self.nodes if n.status == NodeStatus.COMPLETED}
        ready = []
        for n in self.nodes:
            if n.status != NodeStatus.PENDING:
                continue
            if all(d in completed for d in n.dependencies):
                ready.append(n)
        return ready

    def failed_nodes(self) -> List[DelegationNode]:
        return [n for n in self.nodes if n.status == NodeStatus.FAILED]

    def blocked_nodes(self) -> List[DelegationNode]:
        failed = {n.id for n in self.nodes if n.status == NodeStatus.FAILED}
        blocked = []
        for n in self.nodes:
            if n.status != NodeStatus.PENDING:
                continue
            if any(d in failed for d in n.dependencies):
                blocked.append(n)
        return blocked

    def completion_pct(self) -> float:
        if not self.nodes:
            return 0.0
        completed = sum(1 for n in self.nodes if n.status == NodeStatus.COMPLETED)
        return completed / len(self.nodes)

    def to_dict(self) -> Dict:
        return {
            "goal": self.goal[:80],
            "nodes": [n.to_dict() for n in self.nodes],
            "ready": len(self.ready_nodes()),
            "completed_pct": round(self.completion_pct(), 3),
        }


@dataclass
class DelegationResult:
    graph: DelegationGraph
    all_succeeded: bool
    completion_pct: float
    failed_count: int
    total_duration_sec: float
    bottlenecks: List[str]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  DELEGATION GRAPH RESULT")
        lines.append("=" * 70)
        lines.append(f"  Goal: {self.graph.goal[:60]}")
        lines.append(f"  Status: {'✅ All succeeded' if self.all_succeeded else '❌ Some failed'}")
        lines.append(f"  Completion: {self.completion_pct:.0%} | "
                     f"Failed: {self.failed_count}")
        lines.append(f"  Duration: {self.total_duration_sec:.1f}s")
        lines.append("")
        lines.append("  Nodes:")
        for n in self.graph.nodes:
            icons = {NodeStatus.COMPLETED: "✅", NodeStatus.FAILED: "❌",
                     NodeStatus.RUNNING: "🔄", NodeStatus.PENDING: "⏳",
                     NodeStatus.BLOCKED: "🚫", NodeStatus.SKIPPED: "⏭️"}
            icon = icons.get(n.status, "•")
            lines.append(f"    {icon} {n.name} [{n.node_type.value}] → {n.task[:40]}")
            if n.error:
                lines.append(f"       Error: {n.error[:60]}")
        if self.bottlenecks:
            lines.append("-" * 70)
            lines.append("  Bottlenecks:")
            for b in self.bottlenecks:
                lines.append(f"    • {b}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  Recommendations:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class DelegationGraphBuilder:
    def build(self, goal: str, tasks: List[Dict],
              context: Optional[Dict] = None) -> DelegationGraph:
        nodes: List[DelegationNode] = []
        for i, task_def in enumerate(tasks):
            node_id = f"node-{uuid.uuid4().hex[:8]}"
            nodes.append(DelegationNode(
                id=node_id,
                name=task_def.get("name", f"Step {i+1}"),
                agent_id=task_def.get("agent_id", ""),
                node_type=NodeType(task_def.get("type", "executor")),
                task=task_def.get("description", ""),
                dependencies=task_def.get("dependencies", []),
                max_retries=task_def.get("max_retries", 2),
            ))
        return DelegationGraph(
            goal=goal,
            nodes=nodes,
            created_at=time.time(),
            context=context or {},
        )

    def build_from_decomposition(self, goal: str, subtask_names: List[str],
                                  subtask_types: List[str],
                                  agents: List[str]) -> DelegationGraph:
        nodes: List[DelegationNode] = []
        prev_id = None
        for i, (name, stype) in enumerate(zip(subtask_names, subtask_types)):
            node_id = f"node-{uuid.uuid4().hex[:8]}"
            deps = [prev_id] if prev_id else []
            nodes.append(DelegationNode(
                id=node_id,
                name=name,
                agent_id=agents[i] if i < len(agents) else "",
                node_type=NodeType(stype),
                task=name,
                dependencies=deps,
            ))
            prev_id = node_id
        return DelegationGraph(
            goal=goal,
            nodes=nodes,
            created_at=time.time(),
        )


class DelegationGraphExecutor:
    def __init__(self, agent_executor_map: Optional[Dict[str, Any]] = None):
        self._executors = agent_executor_map or {}

    def register_executor(self, agent_id: str, executor_fn: Any) -> None:
        self._executors[agent_id] = executor_fn

    def execute(self, graph: DelegationGraph) -> DelegationResult:
        start = time.time()
        bottlenecks: List[str] = []
        max_iterations = len(graph.nodes) * 2
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            ready = graph.ready_nodes()
            if not ready:
                break

            long_waiting = [n for n in graph.nodes
                            if n.status == NodeStatus.PENDING
                            and n.dependencies
                            and not any(d in {rn.id for rn in ready}
                                        for d in n.dependencies)]
            if len(ready) <= 1 and len(long_waiting) > 2:
                bottlenecks.append(
                    f"Chain blocked: {len(long_waiting)} nodes waiting on single-track path"
                )

            for node in ready:
                node.status = NodeStatus.RUNNING
                node_start = time.time()
                executor = self._executors.get(node.agent_id)
                if executor:
                    try:
                        node.result = executor(node.task, node.metadata)
                        node.status = NodeStatus.COMPLETED
                        node.confidence = 0.9
                    except Exception as e:
                        node.error = str(e)
                        node.retry_count += 1
                        if node.retry_count >= node.max_retries:
                            node.status = NodeStatus.FAILED
                            bottlenecks.append(
                                f"Node '{node.name}' failed after {node.retry_count} retries: {str(e)[:50]}"
                            )
                        else:
                            node.status = NodeStatus.PENDING
                else:
                    node.status = NodeStatus.COMPLETED
                    node.result = f"Simulated: {node.task[:40]}"
                    node.confidence = 0.7
                node.duration_sec = time.time() - node_start

        total_duration = time.time() - start
        failed = [n for n in graph.nodes if n.status == NodeStatus.FAILED]
        all_succeeded = len(failed) == 0

        recommendations: List[str] = []
        if failed:
            recommendations.append("Reassign failed tasks to backup agents")
            recommendations.append("Verify agent capabilities match task requirements")
        if bottlenecks:
            recommendations.append("Restructure dependency chain to parallelize independent tasks")
        if not recommendations:
            recommendations.append("Delegation completed successfully")

        return DelegationResult(
            graph=graph,
            all_succeeded=all_succeeded,
            completion_pct=graph.completion_pct(),
            failed_count=len(failed),
            total_duration_sec=total_duration,
            bottlenecks=list(set(bottlenecks)),
            recommendations=recommendations,
        )
