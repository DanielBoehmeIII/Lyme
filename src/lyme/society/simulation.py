from __future__ import annotations

import math
import random
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class AgentTrait(str, Enum):
    EXPLORATORY = "exploratory"
    CONSERVATIVE = "conservative"
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    ANALYTICAL = "analytical"
    EXPERIMENTAL = "experimental"
    SYSTEMATIC = "systematic"
    OPPORTUNISTIC = "opportunistic"


class SocialRole(str, Enum):
    SPECIALIST = "specialist"
    GENERALIST = "generalist"
    COORDINATOR = "coordinator"
    REVIEWER = "reviewer"
    PIONEER = "pioneer"
    MAINTAINER = "maintainer"


@dataclass
class SimulatedAgent:
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    traits: List[AgentTrait] = field(default_factory=list)
    role: SocialRole = SocialRole.GENERALIST
    skill_level: float = random.uniform(0.3, 0.7)
    specialization: str = ""
    energy: float = 100.0
    hierarchy_level: int = 0
    trust_score: float = 0.5
    task_count: int = 0
    success_count: int = 0
    collaboration_count: int = 0
    communication_volume: int = 0
    reputation: float = 0.5
    created_at: float = field(default_factory=time.time)
    knowledge_breadth: float = random.uniform(0.2, 0.8)
    knowledge_depth: float = random.uniform(0.2, 0.8)
    error_rate: float = random.uniform(0.05, 0.3)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.task_count, 1)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "traits": [t.value for t in self.traits],
            "skill_level": self.skill_level,
            "specialization": self.specialization,
            "hierarchy_level": self.hierarchy_level,
            "trust_score": self.trust_score,
            "reputation": self.reputation,
            "task_count": self.task_count,
            "success_rate": self.success_rate,
            "collaboration_count": self.collaboration_count,
            "knowledge_breadth": self.knowledge_breadth,
            "knowledge_depth": self.knowledge_depth,
            "energy": self.energy,
        }


@dataclass
class SimulationTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    domain: str = ""
    complexity: float = 0.5
    required_breadth: float = 0.0
    required_depth: float = 0.0
    duration_ticks: int = 1
    completed: bool = False
    successful: bool = False
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "complexity": self.complexity,
            "completed": self.completed,
            "successful": self.successful,
            "assigned_agent": self.assigned_agent,
        }


@dataclass
class SimulationConfig:
    num_agents: int = 20
    num_tasks: int = 200
    num_ticks: int = 100
    communication_cost: float = 0.05
    specialization_rate: float = 0.02
    hierarchy_emergence_rate: float = 0.01
    trust_decay: float = 0.005
    energy_recovery_rate: float = 2.0
    task_complexity_range: Tuple[float, float] = (0.1, 0.9)
    collaboration_bonus: float = 0.15
    failure_penalty: float = 0.1
    seed: int = 42

    def to_dict(self) -> dict:
        return {
            "num_agents": self.num_agents,
            "num_tasks": self.num_tasks,
            "num_ticks": self.num_ticks,
            "communication_cost": self.communication_cost,
            "specialization_rate": self.specialization_rate,
            "hierarchy_emergence_rate": self.hierarchy_emergence_rate,
            "trust_decay": self.trust_decay,
        }


@dataclass
class SimulationSnapshot:
    tick: int = 0
    agent_states: List[Dict[str, Any]] = field(default_factory=list)
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_success_rate: float = 0.0
    specialization_level: float = 0.0
    hierarchy_depth: int = 0
    total_communications: int = 0
    trust_avg: float = 0.0
    collaboration_count: int = 0
    roles_distribution: Dict[str, int] = field(default_factory=dict)
    gini_coefficient: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_success_rate": self.avg_success_rate,
            "specialization_level": self.specialization_level,
            "hierarchy_depth": self.hierarchy_depth,
            "total_communications": self.total_communications,
            "trust_avg": self.trust_avg,
            "collaboration_count": self.collaboration_count,
            "roles_distribution": self.roles_distribution,
            "gini_coefficient": self.gini_coefficient,
        }


class SocietySimulator:
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.agents: Dict[str, SimulatedAgent] = {}
        self.tasks: List[SimulationTask] = []
        self.snapshots: List[SimulationSnapshot] = []
        self._communication_graph: Dict[str, Set[str]] = defaultdict(set)
        self._hierarchy: Dict[int, List[str]] = defaultdict(list)
        self._domain_expertise: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._tick = 0

        if self.config.seed:
            random.seed(self.config.seed)

    def initialize(self):
        self.agents = {}
        self.tasks = []
        self.snapshots = []
        self._communication_graph.clear()
        self._hierarchy.clear()
        self._domain_expertise.clear()
        self._tick = 0

        domains = ["architecture", "testing", "performance", "security",
                    "data_modeling", "api_design", "debugging", "documentation"]

        for i in range(self.config.num_agents):
            traits = random.sample(
                list(AgentTrait),
                k=random.randint(1, 3),
            )
            role = random.choice(list(SocialRole))
            agent = SimulatedAgent(
                name=f"Agent_{i}",
                traits=traits,
                role=role,
                skill_level=random.uniform(0.3, 0.7),
                specialization=random.choice(domains),
                hierarchy_level=0,
                trust_score=random.uniform(0.3, 0.7),
                energy=100.0,
                knowledge_breadth=random.uniform(0.2, 0.8),
                knowledge_depth=random.uniform(0.2, 0.8),
                error_rate=random.uniform(0.05, 0.3),
            )
            self.agents[agent.agent_id] = agent
            self._hierarchy[0].append(agent.agent_id)
            self._domain_expertise[agent.specialization][agent.agent_id] = agent.skill_level

        for _ in range(self.config.num_tasks):
            task = SimulationTask(
                domain=random.choice(domains),
                complexity=random.uniform(*self.config.task_complexity_range),
                required_breadth=random.uniform(0.1, 0.9),
                required_depth=random.uniform(0.1, 0.9),
                duration_ticks=random.randint(1, 5),
            )
            self.tasks.append(task)

    def step(self) -> SimulationSnapshot:
        self._tick += 1

        pending = [t for t in self.tasks if not t.completed and t.assigned_agent is None]
        active = [t for t in self.tasks if not t.completed and t.assigned_agent is not None]

        for task in pending[:5]:
            agent = self._select_agent(task)
            if agent:
                task.assigned_agent = agent.agent_id
                agent.energy -= task.complexity * 5
                agent.task_count += 1

        for task in active[:]:
            agent = self.agents.get(task.assigned_agent or "")
            if not agent:
                continue

            agent.energy -= task.complexity * 2
            agent.communication_volume += 1

            success_prob = (
                agent.skill_level * 0.4 +
                (1.0 - task.complexity) * 0.3 +
                agent.knowledge_depth * 0.15 +
                agent.knowledge_breadth * 0.15 -
                agent.error_rate * 0.3
            )

            if agent.specialization == task.domain:
                success_prob += 0.15

            if random.random() < success_prob:
                task.completed = True
                task.successful = True
                agent.success_count += 1
                agent.skill_level = min(1.0, agent.skill_level + 0.01)
                agent.trust_score = min(1.0, agent.trust_score + 0.02)
                agent.reputation = min(1.0, agent.reputation + 0.01)

                if agent.specialization == task.domain:
                    self._domain_expertise[task.domain][agent.agent_id] = agent.skill_level
            else:
                if random.random() < agent.error_rate * 2:
                    task.completed = True
                    task.successful = False
                    agent.trust_score = max(0.0, agent.trust_score - 0.05)
                    agent.reputation = max(0.0, agent.reputation - 0.03)

        self._emerge_specialization()
        self._emerge_hierarchy()
        self._simulate_communication()
        self._recover_energy()

        snapshot = self._capture_snapshot()
        self.snapshots.append(snapshot)
        return snapshot

    def _select_agent(self, task: SimulationTask) -> Optional[SimulatedAgent]:
        candidates = [
            a for a in self.agents.values()
            if a.energy > 20.0 and a not in [
                self.agents.get(t.assigned_agent) for t in self.tasks
                if not t.completed and t.assigned_agent
            ]
        ]

        if not candidates:
            candidates = list(self.agents.values())

        scored = []
        for agent in candidates:
            score = agent.skill_level * 0.3
            score += (1.0 - task.complexity) * 0.2
            score += agent.reputation * 0.2
            score += agent.trust_score * 0.15
            score += agent.energy / 100.0 * 0.15

            if agent.specialization == task.domain:
                score *= 1.3
            if SocialRole.SPECIALIST in [SocialRole(r) for r in [agent.role]]:
                score *= 1.1

            scored.append((score, agent))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None

    def _emerge_specialization(self):
        for agent in self.agents.values():
            if random.random() < self.config.specialization_rate:
                if agent.success_rate > 0.7 and agent.task_count > 5:
                    if agent.knowledge_depth < 1.0:
                        agent.knowledge_depth = min(1.0, agent.knowledge_depth + 0.05)
                        agent.knowledge_breadth = max(0.1, agent.knowledge_breadth - 0.02)
                        agent.role = SocialRole.SPECIALIST

    def _emerge_hierarchy(self):
        current_depth = max(self._hierarchy.keys()) if self._hierarchy else 0

        sorted_agents = sorted(
            self.agents.values(),
            key=lambda a: (a.reputation + a.trust_score + a.success_rate) / 3,
            reverse=True,
        )

        if len(sorted_agents) >= 4:
            top = sorted_agents[:max(1, len(sorted_agents) // 5)]
            for agent in top:
                prev_level = agent.hierarchy_level
                new_level = min(current_depth + 1, max(self._hierarchy.keys()) + 1
                                if self._hierarchy else 0)
                if new_level > prev_level:
                    if prev_level in self._hierarchy and agent.agent_id in self._hierarchy[prev_level]:
                        self._hierarchy[prev_level].remove(agent.agent_id)
                    self._hierarchy[new_level].append(agent.agent_id)
                    agent.hierarchy_level = new_level
                    if agent.role != SocialRole.COORDINATOR and new_level > 0:
                        agent.role = SocialRole.COORDINATOR

    def _simulate_communication(self):
        all_ids = list(self.agents.keys())
        for i in range(min(10, len(all_ids))):
            a = random.choice(all_ids)
            b = random.choice([x for x in all_ids if x != a])
            self._communication_graph[a].add(b)
            self._communication_graph[b].add(a)
            self.agents[a].communication_volume += 1
            self.agents[b].communication_volume += 1
            self.agents[a].energy -= self.config.communication_cost
            self.agents[b].energy -= self.config.communication_cost

            if random.random() < self.config.collaboration_bonus:
                self.agents[a].collaboration_count += 1
                self.agents[b].collaboration_count += 1
                self.agents[a].trust_score = min(1.0, self.agents[a].trust_score + 0.01)
                self.agents[b].trust_score = min(1.0, self.agents[b].trust_score + 0.01)

    def _recover_energy(self):
        for agent in self.agents.values():
            agent.energy = min(100.0, agent.energy + self.config.energy_recovery_rate)

    def _capture_snapshot(self) -> SimulationSnapshot:
        completed = sum(1 for t in self.tasks if t.completed and t.successful)
        failed = sum(1 for t in self.tasks if t.completed and not t.successful)

        success_rates = [a.success_rate for a in self.agents.values()]
        avg_success = sum(success_rates) / max(len(success_rates), 1)

        specializations = sum(
            1 for a in self.agents.values()
            if a.success_rate > 0.7 and a.task_count > 3
        )
        specialization_level = specializations / max(len(self.agents), 1)

        hierarchy_depth = max(self._hierarchy.keys()) if self._hierarchy else 0

        total_comms = sum(a.communication_volume for a in self.agents.values())
        trust_avg = sum(a.trust_score for a in self.agents.values()) / max(len(self.agents), 1)

        collaborations = sum(a.collaboration_count for a in self.agents.values())

        role_dist = Counter(a.role.value for a in self.agents.values())

        skill_levels = [a.skill_level for a in self.agents.values()]
        skill_levels.sort()
        gini = self._compute_gini(skill_levels)

        return SimulationSnapshot(
            tick=self._tick,
            agent_states=[a.to_dict() for a in self.agents.values()],
            tasks_completed=completed,
            tasks_failed=failed,
            avg_success_rate=avg_success,
            specialization_level=specialization_level,
            hierarchy_depth=hierarchy_depth,
            total_communications=total_comms,
            trust_avg=trust_avg,
            collaboration_count=collaborations,
            roles_distribution=dict(role_dist),
            gini_coefficient=gini,
        )

    def _compute_gini(self, values: List[float]) -> float:
        if not values or sum(values) == 0:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        cumulative = 0
        for i, v in enumerate(sorted_vals):
            cumulative += (2 * i - n + 1) * v
        return cumulative / (n * sum(sorted_vals))

    def run(self) -> List[SimulationSnapshot]:
        self.initialize()
        for _ in range(self.config.num_ticks):
            self.step()
        return self.snapshots

    def get_summary(self) -> Dict[str, Any]:
        if not self.snapshots:
            return {"error": "no snapshots"}

        first = self.snapshots[0]
        last = self.snapshots[-1]

        roles_emerged = set()
        for s in self.snapshots:
            roles_emerged.update(s.roles_distribution.keys())

        return {
            "ticks": self._tick,
            "agents": len(self.agents),
            "tasks_total": len(self.tasks),
            "tasks_completed": last.tasks_completed,
            "tasks_failed": last.tasks_failed,
            "completion_rate": last.tasks_completed / max(len(self.tasks), 1),
            "specialization_emergence": {
                "initial": first.specialization_level,
                "final": last.specialization_level,
                "delta": last.specialization_level - first.specialization_level,
            },
            "hierarchy_emergence": {
                "initial_depth": first.hierarchy_depth,
                "final_depth": last.hierarchy_depth,
            },
            "trust_evolution": {
                "initial": first.trust_avg,
                "final": last.trust_avg,
            },
            "collaboration_emergence": {
                "initial": first.collaboration_count,
                "final": last.collaboration_count,
            },
            "gini_evolution": {
                "initial": first.gini_coefficient,
                "final": last.gini_coefficient,
            },
            "roles_distribution": last.roles_distribution,
            "roles_emerged": list(roles_emerged),
            "communication_total": last.total_communications,
        }

    def get_agent_analysis(self) -> Dict[str, Any]:
        specializations = defaultdict(list)
        hierarchy = defaultdict(list)
        for agent in self.agents.values():
            specializations[agent.role.value].append(agent.name)
            hierarchy[agent.hierarchy_level].append(agent.name)

        top_agents = sorted(
            self.agents.values(),
            key=lambda a: a.reputation + a.trust_score + a.success_rate,
            reverse=True,
        )[:5]

        return {
            "specialization_clusters": {k: v[:5] for k, v in specializations.items()},
            "hierarchy_structure": {k: v[:5] for k, v in hierarchy.items()},
            "top_agents": [
                {"name": a.name, "role": a.role.value,
                 "reputation": a.reputation, "success_rate": a.success_rate,
                 "hierarchy_level": a.hierarchy_level}
                for a in top_agents
            ],
            "communication_network": {
                "density": self._compute_network_density(),
                "total_edges": sum(len(v) for v in self._communication_graph.values()) // 2,
            },
        }

    def _compute_network_density(self) -> float:
        n = len(self.agents)
        if n < 2:
            return 0.0
        edges = sum(len(v) for v in self._communication_graph.values()) // 2
        possible = n * (n - 1) / 2
        return edges / possible
