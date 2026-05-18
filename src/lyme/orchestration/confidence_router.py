"""ConfidenceRouter — routes tasks to the right agent based on confidence scores."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import time


class RoutingStrategy(str, Enum):
    HIGHEST_CONFIDENCE = "highest_confidence"
    FASTEST = "fastest"
    MOST_SPECIALIZED = "most_specialized"
    ROUND_ROBIN = "round_robin"
    FALLBACK_CHAIN = "fallback_chain"


@dataclass
class AgentCapability:
    agent_id: str
    task_types: List[str]
    confidence_scores: Dict[str, float]
    avg_latency_sec: float
    total_tasks: int
    success_rate: float

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "task_types": self.task_types,
            "avg_confidence": round(sum(self.confidence_scores.values()) / max(len(self.confidence_scores), 1), 3),
            "avg_latency_sec": round(self.avg_latency_sec, 2),
            "total_tasks": self.total_tasks,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class RoutingDecision:
    task_type: str
    task_description: str
    selected_agent: str
    confidence: float
    strategy_used: RoutingStrategy
    alternatives: List[str]
    rationale: str

    def to_dict(self) -> Dict:
        return {
            "task_type": self.task_type,
            "task_description": self.task_description[:60],
            "selected_agent": self.selected_agent,
            "confidence": round(self.confidence, 3),
            "strategy": self.strategy_used.value,
            "alternatives": self.alternatives[:3],
        }


@dataclass
class RouterReport:
    total_routes: int
    agents: List[AgentCapability]
    strategy_usage: Dict[str, int]
    most_routed_task: str
    avg_confidence: float
    insights: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  CONFIDENCE ROUTER")
        lines.append("=" * 70)
        lines.append(f"  Total Routes: {self.total_routes}")
        lines.append(f"  Avg Confidence: {self.avg_confidence:.0%}")
        lines.append(f"  Most Routed: {self.most_routed_task}")
        lines.append("")
        lines.append("  Agents:")
        for a in sorted(self.agents, key=lambda x: -x.success_rate):
            lines.append(f"    {a.agent_id}: {a.success_rate:.0%} success "
                         f"({a.total_tasks} tasks, {a.avg_latency_sec:.1f}s)")
        lines.append("")
        lines.append("  Strategy Usage:")
        for strat, count in sorted(self.strategy_usage.items(), key=lambda x: -x[1]):
            lines.append(f"    {strat}: {count}")
        if self.insights:
            lines.append("-" * 70)
            for ins in self.insights:
                lines.append(f"  • {ins}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ConfidenceRouter:
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.HIGHEST_CONFIDENCE):
        self._strategy = strategy
        self._agents: Dict[str, AgentCapability] = {}
        self._routing_history: List[RoutingDecision] = []
        self._fallback_chains: Dict[str, List[str]] = {}

    def register_agent(self, agent_id: str, task_types: List[str],
                       confidence_scores: Optional[Dict[str, float]] = None) -> None:
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentCapability(
                agent_id=agent_id,
                task_types=task_types,
                confidence_scores=confidence_scores or {},
                avg_latency_sec=0.0,
                total_tasks=0,
                success_rate=1.0,
            )

    def set_fallback_chain(self, task_type: str, agent_chain: List[str]) -> None:
        self._fallback_chains[task_type] = agent_chain

    def record_outcome(self, agent_id: str, task_type: str, success: bool,
                       latency_sec: float) -> None:
        agent = self._agents.get(agent_id)
        if not agent:
            return
        agent.total_tasks += 1
        agent.avg_latency_sec = (
            (agent.avg_latency_sec * (agent.total_tasks - 1) + latency_sec) / agent.total_tasks
        )
        if task_type not in agent.confidence_scores:
            agent.confidence_scores[task_type] = 0.5
        old_score = agent.confidence_scores[task_type]
        adjustment = 0.1 if success else -0.15
        agent.confidence_scores[task_type] = max(0.0, min(1.0, old_score + adjustment))
        agent.success_rate = (
            (agent.success_rate * (agent.total_tasks - 1) + (1.0 if success else 0.0))
            / agent.total_tasks
        )

    def route(self, task_type: str, task_description: str,
              required_confidence: float = 0.0) -> RoutingDecision:
        strategy = self._strategy

        if task_type in self._fallback_chains:
            strategy = RoutingStrategy.FALLBACK_CHAIN

        if strategy == RoutingStrategy.HIGHEST_CONFIDENCE:
            return self._route_by_confidence(task_type, task_description, required_confidence)
        elif strategy == RoutingStrategy.FALLBACK_CHAIN:
            return self._route_by_fallback(task_type, task_description, required_confidence)
        elif strategy == RoutingStrategy.FASTEST:
            return self._route_by_speed(task_type, task_description)
        elif strategy == RoutingStrategy.MOST_SPECIALIZED:
            return self._route_by_specialization(task_type, task_description)
        else:
            return self._route_by_confidence(task_type, task_description, required_confidence)

    def _route_by_confidence(self, task_type: str, description: str,
                             required_conf: float) -> RoutingDecision:
        candidates = []
        for aid, agent in self._agents.items():
            if task_type not in agent.task_types:
                continue
            conf = agent.confidence_scores.get(task_type, 0.5)
            if conf >= required_conf:
                candidates.append((conf, aid))

        candidates.sort(key=lambda x: -x[0])
        alternatives = [aid for _, aid in candidates[1:4]]

        if candidates:
            conf, selected = candidates[0]
        else:
            selected = list(self._agents.keys())[0] if self._agents else "no_agent"
            conf = 0.0

        decision = RoutingDecision(
            task_type=task_type,
            task_description=description,
            selected_agent=selected,
            confidence=conf,
            strategy_used=RoutingStrategy.HIGHEST_CONFIDENCE,
            alternatives=alternatives,
            rationale=f"Selected {selected} with confidence {conf:.2f} for {task_type}",
        )
        self._routing_history.append(decision)
        return decision

    def _route_by_fallback(self, task_type: str, description: str,
                           required_conf: float) -> RoutingDecision:
        chain = self._fallback_chains.get(task_type, list(self._agents.keys()))
        alternatives: List[str] = []
        for i, agent_id in enumerate(chain):
            agent = self._agents.get(agent_id)
            if not agent:
                continue
            conf = agent.confidence_scores.get(task_type, 0.5)
            if conf >= required_conf:
                decision = RoutingDecision(
                    task_type=task_type,
                    task_description=description,
                    selected_agent=agent_id,
                    confidence=conf,
                    strategy_used=RoutingStrategy.FALLBACK_CHAIN,
                    alternatives=chain[i + 1:],
                    rationale=f"Fallback chain: {agent_id} (position {i}, conf {conf:.2f})",
                )
                self._routing_history.append(decision)
                return decision
            alternatives.append(agent_id)

        last = chain[-1] if chain else "no_agent"
        decision = RoutingDecision(
            task_type=task_type,
            task_description=description,
            selected_agent=last,
            confidence=self._agents.get(last, AgentCapability(last, [], {}, 0, 0, 0)).confidence_scores.get(task_type, 0.0),
            strategy_used=RoutingStrategy.FALLBACK_CHAIN,
            alternatives=[],
            rationale=f"End of fallback chain: {last}",
        )
        self._routing_history.append(decision)
        return decision

    def _route_by_speed(self, task_type: str, description: str) -> RoutingDecision:
        eligible = [(a.avg_latency_sec, a.agent_id)
                    for a in self._agents.values()
                    if task_type in a.task_types]
        eligible.sort(key=lambda x: x[0])

        if eligible:
            _, selected = eligible[0]
            alternatives = [aid for _, aid in eligible[1:4]]
            conf = self._agents[selected].confidence_scores.get(task_type, 0.5)
        else:
            selected = list(self._agents.keys())[0] if self._agents else "no_agent"
            alternatives = []
            conf = 0.0

        decision = RoutingDecision(
            task_type=task_type, task_description=description,
            selected_agent=selected, confidence=conf,
            strategy_used=RoutingStrategy.FASTEST,
            alternatives=alternatives,
            rationale=f"Fastest agent: {selected}",
        )
        self._routing_history.append(decision)
        return decision

    def _route_by_specialization(self, task_type: str, description: str) -> RoutingDecision:
        candidates = []
        for aid, agent in self._agents.items():
            if task_type in agent.task_types:
                if aid not in agent.confidence_scores:
                    agent.confidence_scores[aid] = 0.5
                candidates.append((agent.confidence_scores.get(task_type, 0.5), aid))
        candidates.sort(key=lambda x: -x[0])

        if candidates:
            conf, selected = candidates[0]
            alternatives = [aid for _, aid in candidates[1:4]]
        else:
            selected = list(self._agents.keys())[0] if self._agents else "no_agent"
            alternatives = []
            conf = 0.0

        decision = RoutingDecision(
            task_type=task_type, task_description=description,
            selected_agent=selected, confidence=conf,
            strategy_used=RoutingStrategy.MOST_SPECIALIZED,
            alternatives=alternatives,
            rationale=f"Most specialized: {selected} for {task_type}",
        )
        self._routing_history.append(decision)
        return decision

    def report(self) -> RouterReport:
        agents_list = list(self._agents.values())

        strategy_usage: Dict[str, int] = {}
        for d in self._routing_history:
            strategy_usage[d.strategy_used.value] = strategy_usage.get(d.strategy_used.value, 0) + 1

        type_counts: Dict[str, int] = {}
        for d in self._routing_history:
            type_counts[d.task_type] = type_counts.get(d.task_type, 0) + 1
        most_routed = max(type_counts, key=type_counts.get) if type_counts else "none"

        avg_confidence = sum(d.confidence for d in self._routing_history) / max(len(self._routing_history), 1)

        insights: List[str] = []
        high_sr = [a for a in agents_list if a.success_rate > 0.8 and a.total_tasks > 3]
        if high_sr:
            insights.append(f"{len(high_sr)} highly reliable agents (>80% success)")
        low_conf = [a for a in agents_list if a.total_tasks > 3 and a.success_rate < 0.5]
        if low_conf:
            insights.append(f"{len(low_conf)} agents need improvement or replacement")

        return RouterReport(
            total_routes=len(self._routing_history),
            agents=agents_list,
            strategy_usage=strategy_usage,
            most_routed_task=most_routed,
            avg_confidence=avg_confidence,
            insights=insights,
        )
