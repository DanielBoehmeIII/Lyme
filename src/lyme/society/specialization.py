from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DomainExpertise(str, Enum):
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DATA_MODELING = "data_modeling"
    API_DESIGN = "api_design"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"


@dataclass
class CompetencyScore:
    domain: DomainExpertise = DomainExpertise.ARCHITECTURE
    score: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0
    last_demonstrated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
        }


@dataclass
class ReputationRecord:
    agent_id: str = ""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_quality_score: float = 0.0
    reliability: float = 0.0
    peer_ratings: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successful_tasks / max(self.total_tasks, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "total_tasks": self.total_tasks,
            "success_rate": self.success_rate,
            "avg_quality_score": self.avg_quality_score,
            "reliability": self.reliability,
        }


@dataclass
class AgentProfile:
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    competencies: Dict[str, CompetencyScore] = field(default_factory=dict)
    reputation: ReputationRecord = field(default_factory=ReputationRecord)
    collaboration_history: List[str] = field(default_factory=list)
    preferred_domains: List[DomainExpertise] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    total_collaborations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "competencies": {
                k: v.to_dict() for k, v in self.competencies.items()
            },
            "reputation": self.reputation.to_dict(),
            "preferred_domains": [d.value for d in self.preferred_domains],
            "total_collaborations": self.total_collaborations,
        }

    def get_top_competency(self) -> Optional[str]:
        if not self.competencies:
            return None
        return max(self.competencies, key=lambda k: self.competencies[k].score)

    def record_success(self, domain: str, quality: float = 0.8):
        self.reputation.total_tasks += 1
        self.reputation.successful_tasks += 1
        self.reputation.avg_quality_score = (
            (self.reputation.avg_quality_score * (self.reputation.total_tasks - 1) + quality)
            / self.reputation.total_tasks
        )
        self.reputation.reliability = self.reputation.success_rate

        if domain in self.competencies:
            comp = self.competencies[domain]
            comp.score = min(1.0, comp.score + 0.05)
            comp.evidence_count += 1
            comp.last_demonstrated = time.time()

    def record_failure(self, domain: str):
        self.reputation.total_tasks += 1
        self.reputation.failed_tasks += 1
        self.reputation.reliability = self.reputation.success_rate

        if domain in self.competencies:
            comp = self.competencies[domain]
            comp.score = max(0, comp.score - 0.1)


class DomainMemory:
    def __init__(self):
        self._domain_experts: Dict[str, List[str]] = defaultdict(list)
        self._task_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def register_expertise(self, agent_id: str, domain: str, score: float):
        self._domain_experts[domain].append(agent_id)
        self._domain_experts[domain] = sorted(
            self._domain_experts[domain],
            key=lambda aid: 0,
        )

    def get_experts(self, domain: str, min_score: float = 0.3) -> List[str]:
        return self._domain_experts.get(domain, [])

    def record_task(self, agent_id: str, domain: str, outcome: str):
        self._task_history[domain].append({
            "agent_id": agent_id,
            "outcome": outcome,
            "timestamp": time.time(),
        })

    def get_domain_activity(self, domain: str) -> int:
        return len(self._task_history.get(domain, []))


class ExpertRouter:
    def __init__(self):
        self._routing_history: Dict[str, List[str]] = defaultdict(list)

    def route(self, task_domain: str, profiles: List[AgentProfile]) -> List[AgentProfile]:
        scored = []
        for profile in profiles:
            score = 0.0
            if task_domain in profile.competencies:
                comp = profile.competencies[task_domain]
                score = comp.score * 0.5 + profile.reputation.reliability * 0.3

            if task_domain in [d.value for d in profile.preferred_domains]:
                score += 0.2

            scored.append((score, profile))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored]

    def record_routing(self, task_id: str, agent_id: str):
        self._routing_history[task_id].append(agent_id)


class CollaborationGraph:
    def __init__(self):
        self._edges: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._interaction_count: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_interaction(self, agent_a: str, agent_b: str, quality: float = 0.5):
        self._edges[agent_a][agent_b] = quality
        self._edges[agent_b][agent_a] = quality
        self._interaction_count[agent_a][agent_b] += 1
        self._interaction_count[agent_b][agent_a] += 1

    def get_collaborators(self, agent_id: str, min_quality: float = 0.3) -> List[str]:
        return [
            collaborator for collaborator, quality in self._edges.get(agent_id, {}).items()
            if quality >= min_quality
        ]

    def get_team_cohesion(self, agent_ids: List[str]) -> float:
        if len(agent_ids) < 2:
            return 1.0

        total_interactions = 0
        possible = len(agent_ids) * (len(agent_ids) - 1) / 2

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                if agent_ids[j] in self._edges.get(agent_ids[i], {}):
                    total_interactions += 1

        return total_interactions / max(possible, 1)

    def find_clusters(self, min_interactions: int = 3) -> List[List[str]]:
        visited: Set[str] = set()
        clusters: List[List[str]] = []

        for agent in list(self._edges.keys()):
            if agent in visited:
                continue

            cluster = []
            stack = [agent]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)

                for neighbor in self._edges.get(current, {}):
                    if self._interaction_count[current].get(neighbor, 0) >= min_interactions:
                        if neighbor not in visited:
                            stack.append(neighbor)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters


class SpecializationEngine:
    def __init__(self):
        self.profiles: Dict[str, AgentProfile] = {}
        self.domain_memory = DomainMemory()
        self.router = ExpertRouter()
        self.collaboration = CollaborationGraph()

    def create_agent(self, name: str, domains: List[DomainExpertise] = None) -> AgentProfile:
        profile = AgentProfile(name=name, preferred_domains=domains or [])
        initial_score = 0.3
        for domain in profile.preferred_domains:
            profile.competencies[domain.value] = CompetencyScore(
                domain=domain, score=initial_score, confidence=0.3, evidence_count=0
            )
            self.domain_memory.register_expertise(profile.agent_id, domain.value, initial_score)
        self.profiles[profile.agent_id] = profile
        return profile

    def assign_task(self, domain: str, task_id: str) -> Optional[AgentProfile]:
        candidates = self.router.route(domain, list(self.profiles.values()))
        if not candidates:
            return None
        selected = candidates[0]
        self.router.record_routing(task_id, selected.agent_id)
        return selected

    def record_outcome(self, agent_id: str, domain: str, success: bool, quality: float = 0.5):
        profile = self.profiles.get(agent_id)
        if not profile:
            return

        if success:
            profile.record_success(domain, quality)
        else:
            profile.record_failure(domain)

        self.domain_memory.record_task(agent_id, domain, "success" if success else "failure")
        self.domain_memory.register_expertise(
            agent_id, domain,
            profile.competencies[domain].score if domain in profile.competencies else 0.3
        )

    def record_collaboration(self, agent_a: str, agent_b: str, quality: float = 0.5):
        self.collaboration.record_interaction(agent_a, agent_b, quality)
        profile_a = self.profiles.get(agent_a)
        profile_b = self.profiles.get(agent_b)
        if profile_a:
            profile_a.total_collaborations += 1
            profile_a.collaboration_history.append(agent_b)
        if profile_b:
            profile_b.total_collaborations += 1
            profile_b.collaboration_history.append(agent_a)

    def measure_specialization_emergence(self) -> Dict[str, Any]:
        if not self.profiles:
            return {"error": "no agents"}

        domain_concentration: Dict[str, float] = {}
        for domain in DomainExpertise:
            experts = self.domain_memory.get_experts(domain.value)
            if experts:
                scores = [
                    self.profiles[eid].competencies.get(domain.value, CompetencyScore()).score
                    for eid in experts if eid in self.profiles
                ]
                domain_concentration[domain.value] = sum(scores) / max(len(scores), 1) if scores else 0

        top_domains = sorted(domain_concentration.items(), key=lambda x: -x[1])[:5]

        clusters = self.collaboration.find_clusters()

        return {
            "agent_count": len(self.profiles),
            "specialization_level": sum(1 for p in self.profiles.values() if p.get_top_competency() and p.competencies[p.get_top_competency()].score > 0.6) / max(len(self.profiles), 1),
            "top_specializations": top_domains,
            "collaboration_clusters": len(clusters),
            "total_collaborations": sum(p.total_collaborations for p in self.profiles.values()) // 2,
        }
