from __future__ import annotations

import math
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class BidStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    OUTBID = "outbid"


class MarketRole(str, Enum):
    PRODUCER = "producer"
    CONSUMER = "consumer"
    VERIFIER = "verifier"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentCapability:
    domain: str = ""
    skill_level: float = 0.5
    reliability: float = 0.5
    speed: float = 0.5
    cost_per_task: float = 1.0

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "skill_level": self.skill_level,
            "reliability": self.reliability,
            "speed": self.speed,
            "cost_per_task": self.cost_per_task,
        }


@dataclass
class TaskBid:
    bid_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    agent_id: str = ""
    bid_amount: float = 0.0
    estimated_quality: float = 0.0
    estimated_duration: float = 0.0
    status: BidStatus = BidStatus.PENDING
    submitted_at: float = field(default_factory=time.time)
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "bid_id": self.bid_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "bid_amount": self.bid_amount,
            "estimated_quality": self.estimated_quality,
            "estimated_duration": self.estimated_duration,
            "status": self.status.value,
            "confidence": self.confidence,
        }


@dataclass
class MarketTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    domain: str = ""
    description: str = ""
    complexity: float = 0.5
    budget: float = 10.0
    required_quality: float = 0.5
    deadline_ticks: int = 10
    bids: List[TaskBid] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    winning_bid: Optional[str] = None
    completed: bool = False
    successful: bool = False
    actual_quality: float = 0.0
    verification_score: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "complexity": self.complexity,
            "budget": self.budget,
            "required_quality": self.required_quality,
            "bid_count": len(self.bids),
            "assigned_agent": self.assigned_agent,
            "completed": self.completed,
            "successful": self.successful,
            "actual_quality": self.actual_quality,
            "verification_score": self.verification_score,
        }


@dataclass
class MarketAgent:
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    role: MarketRole = MarketRole.PRODUCER
    capabilities: Dict[str, AgentCapability] = field(default_factory=dict)
    reputation: float = 0.5
    specialization_score: float = 0.5
    total_earnings: float = 0.0
    total_tasks: int = 0
    successful_tasks: int = 0
    pricing_strategy: str = "competitive"
    uncertainty_threshold: float = 0.3
    collaboration_partners: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successful_tasks / max(self.total_tasks, 1)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "reputation": self.reputation,
            "specialization_score": self.specialization_score,
            "total_earnings": self.total_earnings,
            "total_tasks": self.total_tasks,
            "success_rate": self.success_rate,
            "pricing_strategy": self.pricing_strategy,
        }


@dataclass
class MarketState:
    tick: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_bids: int = 0
    avg_bid_amount: float = 0.0
    avg_quality: float = 0.0
    avg_reputation: float = 0.5
    total_earnings: float = 0.0
    conflict_count: int = 0
    specialization_quality: float = 0.0
    communication_overhead: float = 0.0
    efficiency: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_bids": self.total_bids,
            "avg_bid_amount": self.avg_bid_amount,
            "avg_quality": self.avg_quality,
            "avg_reputation": self.avg_reputation,
            "total_earnings": self.total_earnings,
            "efficiency": self.efficiency,
        }


class MarketCoordinationEngine:
    def __init__(self):
        self.agents: Dict[str, MarketAgent] = {}
        self.tasks: List[MarketTask] = []
        self._bids: Dict[str, TaskBid] = {}
        self._state_history: List[MarketState] = []
        self._tick = 0
        self._total_earnings = 0.0

    def create_agent(self, name: str, role: MarketRole = MarketRole.PRODUCER,
                      domains: Optional[List[str]] = None) -> MarketAgent:
        agent = MarketAgent(
            name=name,
            role=role,
            reputation=random.uniform(0.3, 0.7),
            specialization_score=random.uniform(0.2, 0.6),
        )
        domains = domains or ["general"]
        for domain in domains:
            agent.capabilities[domain] = AgentCapability(
                domain=domain,
                skill_level=random.uniform(0.3, 0.8),
                reliability=random.uniform(0.3, 0.8),
                speed=random.uniform(0.3, 0.8),
                cost_per_task=random.uniform(0.5, 2.0),
            )
        self.agents[agent.agent_id] = agent
        return agent

    def create_task(self, domain: str, complexity: float, budget: float,
                     required_quality: float = 0.5) -> MarketTask:
        task = MarketTask(
            domain=domain,
            complexity=complexity,
            budget=budget,
            required_quality=required_quality,
            deadline_ticks=random.randint(5, 15),
        )
        self.tasks.append(task)
        return task

    def submit_bid(self, task_id: str, agent_id: str) -> Optional[TaskBid]:
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        agent = self.agents.get(agent_id)
        if not task or not agent:
            return None

        capability = agent.capabilities.get(task.domain)
        if not capability:
            capability = agent.capabilities.get("general",
                          AgentCapability(skill_level=0.3, cost_per_task=1.0))

        base_bid = capability.cost_per_task * task.complexity
        reputation_multiplier = 1.0 + (agent.reputation - 0.5) * 0.5
        specialization_multiplier = 1.0 - (agent.specialization_score * 0.2)

        if agent.pricing_strategy == "aggressive":
            bid_amount = base_bid * 0.8
        elif agent.pricing_strategy == "premium":
            bid_amount = base_bid * 1.3 + (1.0 - agent.reputation) * 0.5
        else:
            bid_amount = base_bid * reputation_multiplier * specialization_multiplier

        estimated_quality = (
            capability.skill_level * 0.4 +
            capability.reliability * 0.3 +
            agent.reputation * 0.2 +
            agent.specialization_score * 0.1
        )

        estimated_duration = task.complexity * 5 / max(capability.speed, 0.1)
        confidence = agent.reputation * 0.5 + capability.skill_level * 0.3 + 0.2

        bid = TaskBid(
            task_id=task_id,
            agent_id=agent_id,
            bid_amount=bid_amount,
            estimated_quality=estimated_quality,
            estimated_duration=estimated_duration,
            confidence=confidence,
        )
        task.bids.append(bid)
        self._bids[bid.bid_id] = bid
        return bid

    def auction_round(self) -> List[MarketTask]:
        awarded: List[MarketTask] = []
        pending_tasks = [t for t in self.tasks if not t.assigned_agent]

        for task in pending_tasks:
            if not task.bids:
                continue

            scored_bids = []
            for bid in task.bids:
                if bid.status != BidStatus.PENDING:
                    continue

                quality_score = bid.estimated_quality * 3.0
                cost_score = (1.0 - bid.bid_amount / max(task.budget, 0.1)) * 2.0
                speed_score = (1.0 / max(bid.estimated_duration, 0.1)) * 1.0
                trust_score = self.agents.get(bid.agent_id, MarketAgent()).reputation * 1.0

                if self.agents.get(bid.agent_id, MarketAgent()).specialization_score > 0.6:
                    trust_score *= 1.2

                total_score = quality_score + cost_score + speed_score + trust_score
                scored_bids.append((total_score, bid))

            if not scored_bids:
                continue

            scored_bids.sort(key=lambda x: -x[0])
            winning_bid = scored_bids[0][1]
            winning_bid.status = BidStatus.ACCEPTED
            task.assigned_agent = winning_bid.agent_id
            task.winning_bid = winning_bid.bid_id

            for _, bid in scored_bids[1:]:
                bid.status = BidStatus.OUTBID

            awarded.append(task)

        return awarded

    def verify_completion(self, task: MarketTask) -> bool:
        agent = self.agents.get(task.assigned_agent or "")
        if not agent:
            return False

        capability = agent.capabilities.get(task.domain)
        if not capability:
            capability = next(iter(agent.capabilities.values()))

        base_quality = (
            capability.skill_level * 0.4 +
            capability.reliability * 0.3 +
            agent.reputation * 0.2 +
            agent.specialization_score * 0.1
        )

        noise = random.uniform(-0.1, 0.1)
        task.actual_quality = max(0.0, min(1.0, base_quality + noise))
        task.verification_score = random.uniform(
            task.actual_quality - 0.1, task.actual_quality + 0.1
        )

        task.completed = True
        task.successful = task.actual_quality >= task.required_quality

        if task.successful:
            payment = task.budget * (task.actual_quality / max(task.required_quality, 0.1))
            payment = min(payment, task.budget * 1.2)
            agent.total_earnings += payment
            agent.total_tasks += 1
            agent.successful_tasks += 1
            agent.reputation = min(1.0, agent.reputation + 0.03)

            if capability.skill_level < 1.0:
                capability.skill_level = min(1.0, capability.skill_level + 0.02)
        else:
            agent.total_tasks += 1
            agent.reputation = max(0.0, agent.reputation - 0.05)

            if capability.skill_level > 0.0:
                capability.skill_level = max(0.0, capability.skill_level - 0.02)

        self._total_earnings += (
            task.budget if task.successful else 0
        )

        return task.successful

    def update_specialization(self):
        for agent in self.agents.values():
            if agent.total_tasks >= 3:
                best_domain = max(
                    agent.capabilities.keys(),
                    key=lambda d: agent.capabilities[d].skill_level,
                )
                best_cap = agent.capabilities[best_domain]
                others = [c for d, c in agent.capabilities.items() if d != best_domain]

                if best_cap.skill_level > 0.6:
                    agent.specialization_score = min(
                        1.0, agent.specialization_score + 0.02
                    )
                    for cap in others:
                        cap.skill_level = max(0.0, cap.skill_level - 0.005)
                else:
                    agent.specialization_score = max(
                        0.0, agent.specialization_score - 0.01
                    )

    def run_epoch(self) -> MarketState:
        self._tick += 1

        for agent in self.agents.values():
            domains = list(agent.capabilities.keys())
            if random.random() < 0.1:
                self.submit_bid(
                    random.choice([t.task_id for t in self.tasks
                                   if not t.assigned_agent]) if any(
                        not t.assigned_agent for t in self.tasks
                    ) else "",
                    agent.agent_id,
                )

        awarded = self.auction_round()

        for task in awarded:
            self.verify_completion(task)

        self.update_specialization()

        pending_count = sum(1 for t in self.tasks if not t.completed)
        completed_count = sum(1 for t in self.tasks if t.completed and t.successful)
        failed_count = sum(1 for t in self.tasks if t.completed and not t.successful)
        total_bids = sum(len(t.bids) for t in self.tasks)

        completed_tasks = [t for t in self.tasks if t.completed]
        avg_quality = (
            sum(t.actual_quality for t in completed_tasks) / max(len(completed_tasks), 1)
        ) if completed_tasks else 0.0

        avg_reputation = (
            sum(a.reputation for a in self.agents.values()) / max(len(self.agents), 1)
        )
        avg_bid = (
            sum(b.bid_amount for b in self._bids.values()) / max(len(self._bids), 1)
        ) if self._bids else 0.0

        efficiency = completed_count / max(self._tick, 1)

        state = MarketState(
            tick=self._tick,
            active_tasks=pending_count,
            completed_tasks=completed_count,
            failed_tasks=failed_count,
            total_bids=total_bids,
            avg_bid_amount=avg_bid,
            avg_quality=avg_quality,
            avg_reputation=avg_reputation,
            total_earnings=self._total_earnings,
            efficiency=efficiency,
        )
        self._state_history.append(state)
        return state

    def run_simulation(self, num_epochs: int = 50) -> List[MarketState]:
        for _ in range(num_epochs):
            pending = [t for t in self.tasks if not t.assigned_agent and not t.completed]
            if pending and random.random() < 0.3:
                for agent in self.agents.values():
                    task = random.choice(pending)
                    self.submit_bid(task.task_id, agent.agent_id)
            self.run_epoch()
        return self._state_history

    def compare_with_orchestration(self) -> Dict[str, Any]:
        if not self._state_history:
            return {"error": "no simulation data"}

        last = self._state_history[-1]
        first = self._state_history[0]

        return {
            "market_efficiency": {
                "final": last.efficiency,
                "tasks_completed": last.completed_tasks,
                "avg_quality": last.avg_quality,
            },
            "specialization_quality": {
                "avg_specialization": sum(
                    a.specialization_score for a in self.agents.values()
                ) / max(len(self.agents), 1),
                "top_agents": sorted(
                    [
                        {"name": a.name, "specialization": a.specialization_score,
                         "reputation": a.reputation, "earnings": a.total_earnings}
                        for a in self.agents.values()
                    ],
                    key=lambda x: -x["specialization"],
                )[:5],
            },
            "reputation_landscape": {
                "avg": last.avg_reputation,
                "distribution": {
                    "high": sum(1 for a in self.agents.values() if a.reputation > 0.7),
                    "medium": sum(1 for a in self.agents.values() if 0.3 <= a.reputation <= 0.7),
                    "low": sum(1 for a in self.agents.values() if a.reputation < 0.3),
                },
            },
            "conflict_reduction": {
                "conflict_count": last.conflict_count,
                "bid_competition": last.total_bids / max(last.tick, 1),
            },
            "communication_overhead": last.communication_overhead,
            "state_history": [s.to_dict() for s in self._state_history[-10:]],
        }
