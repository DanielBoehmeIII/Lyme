"""PlanningEngine — multi-step planning with dependency reasoning and milestone decomposition."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MilestoneStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class Milestone:
    id: str = ""
    name: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.PENDING
    estimated_effort: str = "medium"
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "effort": self.estimated_effort,
            "files": self.files[:5],
        }


@dataclass
class ExecutionGraph:
    milestones: List[Milestone] = field(default_factory=list)
    edges: List[tuple[str, str]] = field(default_factory=list)

    def add_milestone(self, m: Milestone) -> None:
        self.milestones.append(m)
        for dep in m.dependencies:
            self.edges.append((dep, m.id))

    def critical_path(self) -> List[Milestone]:
        if not self.milestones:
            return []
        return sorted(self.milestones, key=lambda m: len(m.dependencies))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestones": len(self.milestones),
            "edges": len(self.edges),
            "critical_path": [m.name for m in self.critical_path()],
        }


class PlanningEngine:
    def __init__(self):
        self._graphs: Dict[str, ExecutionGraph] = {}

    def decompose(self, task: str, milestones: List[Milestone]) -> ExecutionGraph:
        graph = ExecutionGraph()
        for m in milestones:
            graph.add_milestone(m)
        self._graphs[task] = graph
        return graph

    def auto_decompose(self, task: str, files: List[str]) -> ExecutionGraph:
        task_lower = task.lower()
        graph = ExecutionGraph()

        # Phase 1: Understanding
        understand = Milestone(
            id="understand", name="Understand the codebase",
            description=f"Read and understand files related to: {task}",
            files=files[:5], estimated_effort="small",
        )
        graph.add_milestone(understand)

        # Phase 2: Planning
        plan = Milestone(
            id="plan", name="Plan the changes",
            description="Create detailed change plan based on understanding",
            dependencies=["understand"],
            estimated_effort="small",
        )
        graph.add_milestone(plan)

        # Phase 3: Implementation
        if "test" in task_lower or "add test" in task_lower:
            impl = Milestone(
                id="implement", name="Write tests",
                description="Write test cases for the functionality",
                dependencies=["plan"],
                files=files[:5], estimated_effort="medium",
            )
        elif "refactor" in task_lower:
            impl = Milestone(
                id="implement", name="Refactor code",
                description="Apply refactoring changes",
                dependencies=["plan"],
                files=files, estimated_effort="large",
            )
        else:
            impl = Milestone(
                id="implement", name="Implement changes",
                description="Apply code changes",
                dependencies=["plan"],
                files=files[:3], estimated_effort="medium",
            )
        graph.add_milestone(impl)

        # Phase 4: Verification
        verify = Milestone(
            id="verify", name="Verify changes",
            description="Run tests and verify correctness",
            dependencies=["implement"],
            estimated_effort="small",
        )
        graph.add_milestone(verify)

        self._graphs[task] = graph
        return graph

    def get_graph(self, task: str) -> Optional[ExecutionGraph]:
        return self._graphs.get(task)

    def update_status(self, task: str, milestone_id: str, status: MilestoneStatus) -> None:
        graph = self._graphs.get(task)
        if graph:
            for m in graph.milestones:
                if m.id == milestone_id:
                    m.status = status
                    break
