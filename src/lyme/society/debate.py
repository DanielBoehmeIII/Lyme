from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AgentRole(str, Enum):
    PROPOSER = "proposer"
    CRITIC = "critic"
    VERIFIER = "verifier"
    ADVERSARIAL_REVIEWER = "adversarial_reviewer"
    ARCHITECTURAL_GUARDIAN = "architectural_guardian"


@dataclass
class Evidence:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""
    claim: str = ""
    support_level: float = 0.0  # -1 (contradicts) to 1 (supports)
    relevance: float = 0.0
    citation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "claim": self.claim[:100],
            "support_level": self.support_level,
            "relevance": self.relevance,
            "citation": self.citation[:100],
        }


@dataclass
class DebateProposal:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    proposer_id: str = ""
    title: str = ""
    description: str = ""
    approach: str = ""
    rationale: str = ""
    evidence: List[Evidence] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposer_id": self.proposer_id,
            "title": self.title,
            "description": self.description[:200],
            "approach": self.approach[:200],
            "rationale": self.rationale[:200],
            "evidence": [e.to_dict() for e in self.evidence[:3]],
            "assumptions": self.assumptions[:5],
            "confidence": self.confidence,
        }


@dataclass
class DebateCritique:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    proposal_id: str = ""
    critic_id: str = ""
    critic_role: AgentRole = AgentRole.CRITIC
    hidden_assumptions: List[str] = field(default_factory=list)
    weak_reasoning: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    counter_evidence: List[Evidence] = field(default_factory=list)
    uncertainty_surfaces: List[str] = field(default_factory=list)
    severity: str = "medium"
    verdict: str = "needs_revision"
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "critic_id": self.critic_id,
            "critic_role": self.critic_role.value,
            "hidden_assumptions": self.hidden_assumptions[:5],
            "weak_reasoning": self.weak_reasoning[:5],
            "missing_evidence": self.missing_evidence[:5],
            "verdict": self.verdict,
            "score": self.score,
        }


@dataclass
class DebateVerdict:
    proposal_id: str = ""
    approved: bool = False
    score: float = 0.0
    critiques_addressed: int = 0
    remaining_concerns: List[str] = field(default_factory=list)
    final_confidence: float = 0.0
    consensus: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "approved": self.approved,
            "score": self.score,
            "critiques_addressed": self.critiques_addressed,
            "remaining_concerns": self.remaining_concerns[:5],
            "final_confidence": self.final_confidence,
            "consensus": self.consensus,
        }


@dataclass
class DebateConfig:
    max_rounds: int = 3
    min_critics: int = 2
    require_verification: bool = True
    adversarial_check: bool = True
    architectural_review: bool = True
    consensus_threshold: float = 0.7
    evidence_threshold: float = 0.3


class ProposerAgent:
    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id or f"proposer_{uuid.uuid4().hex[:8]}"

    def propose(self, problem: str, context: Dict[str, Any]) -> DebateProposal:
        return DebateProposal(
            proposer_id=self.agent_id,
            title=f"Proposal for: {problem[:50]}",
            description=f"Proposed approach for: {problem[:200]}",
            approach=self._generate_approach(problem),
            rationale="Proposed based on analysis of context",
            evidence=[],
            assumptions=self._identify_assumptions(context),
            confidence=0.7,
        )

    def _generate_approach(self, problem: str) -> str:
        approaches = [
            f"Incremental refactoring: {problem[:100]}",
            f"Modular extraction: {problem[:100]}",
            f"Abstraction layering: {problem[:100]}",
            f"Pattern-based solution: {problem[:100]}",
        ]
        return approaches[hash(problem) % len(approaches)]

    def _identify_assumptions(self, context: Dict[str, Any]) -> List[str]:
        return [
            "Existing interfaces remain stable",
            "Backward compatibility is required",
            "Current test coverage is adequate",
            "Team is familiar with the codebase",
        ]

    def revise(self, proposal: DebateProposal, critiques: List[DebateCritique]) -> DebateProposal:
        proposal.confidence *= 0.9
        for critique in critiques[:3]:
            if critique.verdict == "rejected":
                proposal.approach += f" (revised based on: {critique.weak_reasoning[0] if critique.weak_reasoning else 'feedback'})"
        return proposal


class CriticAgent:
    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id or f"critic_{uuid.uuid4().hex[:8]}"

    def critique(self, proposal: DebateProposal) -> DebateCritique:
        return DebateCritique(
            proposal_id=proposal.id,
            critic_id=self.agent_id,
            critic_role=AgentRole.CRITIC,
            hidden_assumptions=self._find_hidden_assumptions(proposal),
            weak_reasoning=self._find_weak_reasoning(proposal),
            missing_evidence=self._find_missing_evidence(proposal),
            counter_evidence=[],
            uncertainty_surfaces=self._find_uncertainty(proposal),
            severity="medium",
            verdict="needs_revision" if proposal.confidence < 0.8 else "acceptable",
            score=0.5 + proposal.confidence * 0.3,
        )

    def _find_hidden_assumptions(self, proposal: DebateProposal) -> List[str]:
        return [
            "Assumes no breaking API changes",
            "Assumes current abstractions are correct",
            "Assumes team capacity for refactoring",
        ]

    def _find_weak_reasoning(self, proposal: DebateProposal) -> List[str]:
        weaknesses = []
        if not proposal.evidence:
            weaknesses.append("No evidence provided to support approach")
        if not proposal.assumptions:
            weaknesses.append("Assumptions not explicitly stated")
        return weaknesses

    def _find_missing_evidence(self, proposal: DebateProposal) -> List[str]:
        return [
            "No test coverage data cited",
            "No historical precedent referenced",
            "No performance impact analysis",
        ]

    def _find_uncertainty(self, proposal: DebateProposal) -> List[str]:
        return [
            "Impact on dependent modules unknown",
            "Migration effort unclear",
            "Rollback strategy not specified",
        ]


class VerifierAgent:
    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id or f"verifier_{uuid.uuid4().hex[:8]}"

    def verify(self, proposal: DebateProposal, critiques: List[DebateCritique]) -> DebateCritique:
        return DebateCritique(
            proposal_id=proposal.id,
            critic_id=self.agent_id,
            critic_role=AgentRole.VERIFIER,
            weak_reasoning=self._check_verification(proposal, critiques),
            missing_evidence=self._check_evidence_grounding(proposal),
            verdict="verified" if proposal.confidence >= 0.5 else "unverified",
            score=proposal.confidence * 0.8,
        )

    def _check_verification(self, proposal: DebateProposal, critiques: List[DebateCritique]) -> List[str]:
        issues = []
        addressed_count = sum(1 for c in critiques if c.verdict in ("acceptable", "verified"))
        if addressed_count < 2:
            issues.append("Insufficient critical review (less than 2 approvals)")
        return issues

    def _check_evidence_grounding(self, proposal: DebateProposal) -> List[str]:
        gaps = []
        if not proposal.evidence:
            gaps.append("Proposal lacks empirical evidence")
        return gaps


class AdversarialReviewer:
    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id or f"adversarial_{uuid.uuid4().hex[:8]}"

    def review(self, proposal: DebateProposal) -> DebateCritique:
        return DebateCritique(
            proposal_id=proposal.id,
            critic_id=self.agent_id,
            critic_role=AgentRole.ADVERSARIAL_REVIEWER,
            hidden_assumptions=self._attack_assumptions(proposal),
            weak_reasoning=self._attack_reasoning(proposal),
            missing_evidence=["No worst-case analysis provided"],
            uncertainty_surfaces=["System behavior under failure not modeled"],
            severity="high",
            verdict="challenged",
            score=max(0, 1.0 - proposal.confidence),
        )

    def _attack_assumptions(self, proposal: DebateProposal) -> List[str]:
        return [
            f"What if {assumption} is false?" for assumption in proposal.assumptions[:3]
        ]

    def _attack_reasoning(self, proposal: DebateProposal) -> List[str]:
        return [
            f"Alternative approach not adequately considered",
            "Edge cases not addressed in proposal",
        ]


class ArchitecturalGuardian:
    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id or f"guardian_{uuid.uuid4().hex[:8]}"

    def review(self, proposal: DebateProposal) -> DebateCritique:
        return DebateCritique(
            proposal_id=proposal.id,
            critic_id=self.agent_id,
            critic_role=AgentRole.ARCHITECTURAL_GUARDIAN,
            hidden_assumptions=self._check_architectural_fit(proposal),
            weak_reasoning=self._check_architectural_impact(proposal),
            uncertainty_surfaces=self._check_long_term_implications(proposal),
            severity="high",
            verdict="needs_architectural_review",
            score=0.5,
        )

    def _check_architectural_fit(self, proposal: DebateProposal) -> List[str]:
        return [
            "May violate existing architectural boundaries",
            "Could introduce unwanted coupling",
        ]

    def _check_architectural_impact(self, proposal: DebateProposal) -> List[str]:
        return [
            "Impact on subsystem boundaries not assessed",
            "Interface stability implications unclear",
        ]

    def _check_long_term_implications(self, proposal: DebateProposal) -> List[str]:
        return [
            "Technical debt implications not analyzed",
            "Future migration path unclear",
        ]


class DebateEngine:
    def __init__(self, config: Optional[DebateConfig] = None):
        self.config = config or DebateConfig()
        self.proposer = ProposerAgent()
        self.critics = [CriticAgent() for _ in range(self.config.min_critics)]
        self.verifier = VerifierAgent() if self.config.require_verification else None
        self.adversarial = AdversarialReviewer() if self.config.adversarial_check else None
        self.guardian = ArchitecturalGuardian() if self.config.architectural_review else None
        self.debates: Dict[str, Dict[str, Any]] = {}

    def debate(self, problem: str, context: Dict[str, Any] = None) -> DebateVerdict:
        context = context or {}
        debate_id = uuid.uuid4().hex[:12]
        self.debates[debate_id] = {"rounds": [], "status": "in_progress"}

        proposal = self.proposer.propose(problem, context)

        for round_num in range(self.config.max_rounds):
            round_critiques: List[DebateCritique] = []

            for critic in self.critics:
                critique = critic.critique(proposal)
                round_critiques.append(critique)

            if self.adversarial:
                adv_critique = self.adversarial.review(proposal)
                round_critiques.append(adv_critique)

            if self.guardian:
                arch_critique = self.guardian.review(proposal)
                round_critiques.append(arch_critique)

            if self.verifier:
                ver_critique = self.verifier.verify(proposal, round_critiques)
                round_critiques.append(ver_critique)

            self.debates[debate_id]["rounds"].append({
                "round": round_num + 1,
                "proposal": proposal.to_dict(),
                "critiques": [c.to_dict() for c in round_critiques],
            })

            avg_score = sum(c.score for c in round_critiques) / max(len(round_critiques), 1)
            all_approved = all(c.verdict in ("acceptable", "verified") for c in round_critiques)

            if all_approved or avg_score >= self.config.consensus_threshold:
                break

            if round_num < self.config.max_rounds - 1:
                proposal = self.proposer.revise(proposal, round_critiques)

        verdict = self._compute_verdict(debate_id)
        self.debates[debate_id]["status"] = "completed"
        self.debates[debate_id]["verdict"] = verdict.to_dict()
        return verdict

    def _compute_verdict(self, debate_id: str) -> DebateVerdict:
        debate = self.debates.get(debate_id, {})
        rounds = debate.get("rounds", [])
        if not rounds:
            return DebateVerdict(approved=False, score=0.0, consensus="no_rounds")

        final_round = rounds[-1]
        critiques = final_round.get("critiques", [])
        if not critiques:
            return DebateVerdict(approved=False, score=0.0, consensus="no_critiques")

        avg_score = sum(c.get("score", 0) for c in critiques) / len(critiques)
        approvals = sum(1 for c in critiques if c.get("verdict") in ("acceptable", "verified"))
        rejections = sum(1 for c in critiques if c.get("verdict") == "rejected")

        remaining = []
        for c in critiques:
            remaining.extend(c.get("hidden_assumptions", [])[:2])
            remaining.extend(c.get("weak_reasoning", [])[:2])

        return DebateVerdict(
            proposal_id=final_round.get("proposal", {}).get("id", ""),
            approved=approvals > rejections and avg_score >= self.config.consensus_threshold,
            score=avg_score,
            critiques_addressed=len(critiques),
            remaining_concerns=remaining[:5],
            final_confidence=max(0.1, avg_score),
            consensus="approved" if approvals > rejections else "rejected",
        )

    def get_debate_summary(self, debate_id: str) -> Dict[str, Any]:
        debate = self.debates.get(debate_id, {})
        if not debate:
            return {"error": "debate not found"}
        return {
            "debate_id": debate_id,
            "status": debate.get("status"),
            "rounds": len(debate.get("rounds", [])),
            "verdict": debate.get("verdict"),
        }
