"""AgencyWorkflow — pre-built workflows optimized for different team types."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CostProfile:
    avg_task_cost_cents: float = 0.0
    monthly_savings_vs_cloud: float = 0.0
    tasks_per_developer_day: int = 10
    setup_time_minutes: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_task_cost_cents": self.avg_task_cost_cents,
            "monthly_savings_vs_cloud": self.monthly_savings_vs_cloud,
            "tasks_per_day": self.tasks_per_developer_day,
            "setup_minutes": self.setup_time_minutes,
        }


@dataclass
class WorkflowTemplate:
    name: str = ""
    description: str = ""
    target: str = ""  # dev_shop, startup, freelancer
    steps: List[str] = field(default_factory=list)
    cost: CostProfile = field(default_factory=CostProfile)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "steps": self.steps,
            "cost": self.cost.to_dict(),
        }


DEV_SHOP_TEMPLATE = WorkflowTemplate(
    name="client-project-boost",
    target="dev_shop",
    description="Accelerate client project delivery by 3x",
    steps=[
        "Clone client repo and run lyme init",
        "Run lyme doctor for full architecture analysis",
        "Configure multi-agent pipeline: plan -> code -> review -> test",
        "Execute backlog items in parallel with 3 agents",
        "Generate PRs with auto-generated test suites",
    ],
    cost=CostProfile(
        avg_task_cost_cents=0.5,
        monthly_savings_vs_cloud=5000.0,
        tasks_per_developer_day=25,
    ),
)

STARTUP_TEMPLATE = WorkflowTemplate(
    name="lean-team-multiplier",
    target="startup",
    description="Let a 2-person team ship like a 10-person team",
    steps=[
        "Initialize Lyme on your monorepo",
        "Configure autonomous maintenance daemon",
        "Set up CI integration for PR reviews",
        "Use lyme agent for feature implementation",
        "Run lyme maintain for background tech debt reduction",
    ],
    cost=CostProfile(
        avg_task_cost_cents=0.3,
        monthly_savings_vs_cloud=2000.0,
        tasks_per_developer_day=20,
    ),
)

FREELANCER_TEMPLATE = WorkflowTemplate(
    name="solo-dev-force-multiplier",
    target="freelancer",
    description="Compete with agencies by delivering faster and cleaner",
    steps=[
        "lyme init on any project in under 10 seconds",
        "lyme agent for feature implementation",
        "lyme fix for bug repairs",
        "lyme doctor for client-facing code quality reports",
        "lyme run for benchmark comparisons to justify rates",
    ],
    cost=CostProfile(
        avg_task_cost_cents=0.2,
        monthly_savings_vs_cloud=500.0,
        tasks_per_developer_day=15,
    ),
)

ALL_TEMPLATES = [DEV_SHOP_TEMPLATE, STARTUP_TEMPLATE, FREELANCER_TEMPLATE]


class AgencyWorkflow:
    def __init__(self):
        self._templates = {t.name: t for t in ALL_TEMPLATES}

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        return self._templates.get(name)

    def recommend(self, team_type: str) -> Optional[WorkflowTemplate]:
        for t in ALL_TEMPLATES:
            if t.target == team_type:
                return t
        return None

    def list_templates(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in ALL_TEMPLATES]
