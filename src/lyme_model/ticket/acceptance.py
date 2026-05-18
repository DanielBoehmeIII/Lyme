"""AcceptanceGrader — simulate client acceptance evaluation.

Models how a real client would grade the completed work,
including hidden test detection and constraint compliance.
"""

from __future__ import annotations
import random
from .models import ClientTicket, AcceptanceGrade


class AcceptanceGrader:
    """Grade ticket completion from a client's perspective."""

    def grade(self, ticket: ClientTicket, simulation: bool = True) -> dict:
        if not simulation:
            return self._grade_real(ticket)

        return self._grade_simulated(ticket)

    def _grade_simulated(self, ticket: ClientTicket) -> dict:
        ac_total = len(ticket.acceptance_criteria)
        hidden_total = len(ticket.hidden_tests)

        ac_met = 0
        for criterion in ticket.acceptance_criteria:
            if random.random() > 0.15:
                ac_met += 1

        hidden_passed = 0
        hidden_failures = []
        for test in ticket.hidden_tests:
            if random.random() > 0.20:
                hidden_passed += 1
            else:
                hidden_failures.append(test.description)

        constraints_violated = []
        for constraint in ticket.architecture_constraints:
            if constraint.severity == "hard" and random.random() < 0.15:
                constraints_violated.append(constraint.description)

        ambiguity_resolved = sum(
            1 for _ in ticket.ambiguous_elements if random.random() > 0.10
        )

        ac_score = ac_met / max(ac_total, 1)
        hidden_score = hidden_passed / max(hidden_total, 1)
        constraint_score = 1.0 - (len(constraints_violated) / max(len(ticket.architecture_constraints), 1))
        ambiguity_score = ambiguity_resolved / max(len(ticket.ambiguous_elements), 1)

        weights = {"ac": 0.35, "hidden": 0.30, "constraint": 0.20, "ambiguity": 0.15}
        total_score = (
            ac_score * weights["ac"]
            + hidden_score * weights["hidden"]
            + constraint_score * weights["constraint"]
            + ambiguity_score * weights["ambiguity"]
        )

        if total_score >= 0.85:
            grade = AcceptanceGrade.ACCEPTED
            success = True
        elif total_score >= 0.60:
            grade = AcceptanceGrade.CONDITIONALLY_ACCEPTED
            success = True
        elif total_score >= 0.35:
            grade = AcceptanceGrade.REJECTED_MINOR
            success = False
        else:
            grade = AcceptanceGrade.REJECTED_MAJOR
            success = False

        revenue_earned = ticket.estimated_revenue * total_score

        return {
            "success": success,
            "grade": grade,
            "score": round(total_score, 4),
            "revenue_earned": round(revenue_earned, 2),
            "duration_hours": ticket.estimated_hours,
            "criteria_met": ac_met,
            "criteria_total": ac_total,
            "hidden_tests_passed": hidden_passed,
            "hidden_tests_total": hidden_total,
            "hidden_test_failures": hidden_failures,
            "constraints_violated": constraints_violated,
            "ambiguity_resolved": ambiguity_resolved >= len(ticket.ambiguous_elements) * 0.5,
        }

    def _grade_real(self, ticket: ClientTicket) -> dict:
        return self._grade_simulated(ticket)
