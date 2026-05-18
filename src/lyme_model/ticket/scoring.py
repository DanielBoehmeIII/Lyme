"""TicketScorer and RevenueEstimator for paid ticket evaluation."""

from __future__ import annotations
from .models import ClientTicket, TicketDifficulty


class TicketScorer:
    """Score ticket completion quality."""

    def score(self, ticket: ClientTicket, criteria_met: int, hidden_passed: int,
              constraints_violated: list[str], ambiguous_elements_resolved: int) -> dict:
        scores = {}

        ac_score = criteria_met / max(len(ticket.acceptance_criteria), 1)
        scores["acceptance_criteria"] = round(ac_score, 4)

        hidden_score = hidden_passed / max(len(ticket.hidden_tests), 1)
        scores["hidden_tests"] = round(hidden_score, 4)

        total_constraints = len(ticket.architecture_constraints)
        constraints_kept = total_constraints - len(constraints_violated)
        constraints_score = constraints_kept / max(total_constraints, 1)
        scores["constraints"] = round(constraints_score, 4)

        ambiguity_score = ambiguous_elements_resolved / max(len(ticket.ambiguous_elements), 1)
        scores["ambiguity_resolution"] = round(ambiguity_score, 4)

        weights = {"acceptance_criteria": 0.35, "hidden_tests": 0.30,
                    "constraints": 0.20, "ambiguity_resolution": 0.15}
        final = sum(scores[k] * weights[k] for k in weights)
        scores["final"] = round(final, 4)

        return scores


class RevenueEstimator:
    """Estimate revenue for a ticket based on difficulty and complexity."""

    BASE_RATES = {
        TicketDifficulty.EASY: 200,
        TicketDifficulty.MEDIUM: 350,
        TicketDifficulty.HARD: 600,
        TicketDifficulty.EXPERT: 1000,
    }

    def estimate(self, ticket: ClientTicket) -> float:
        base = self.BASE_RATES.get(ticket.difficulty, 300)

        complexity_mult = 1.0 + (len(ticket.acceptance_criteria) * 0.05)
        hidden_mult = 1.0 + (len(ticket.hidden_tests) * 0.08)
        constraint_mult = 1.0 + (len(ticket.architecture_constraints) * 0.10)
        ambiguity_mult = 1.0 + (len(ticket.ambiguous_elements) * 0.05)

        estimated = base * complexity_mult * hidden_mult * constraint_mult * ambiguity_mult
        return round(max(estimated, ticket.estimated_revenue * 0.5), 2)

    def compute_earned(self, ticket: ClientTicket, score: float) -> float:
        estimated = self.estimate(ticket)
        earned = estimated * score
        return round(earned, 2)
