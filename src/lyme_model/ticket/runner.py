"""TicketRunner — execute paid ticket simulations."""

from __future__ import annotations
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ClientTicket, TicketResult, TicketRun, AcceptanceGrade, TicketDifficulty,
)
from .seeded_tickets import SEEDED_TICKETS, get_seeded_ticket
from .scoring import TicketScorer, RevenueEstimator
from .acceptance import AcceptanceGrader


class TicketRunner:
    """Execute paid ticket simulations and score results."""

    def __init__(self, output_dir: str = ".lyme/tickets", dry_run: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.scorer = TicketScorer()
        self.grader = AcceptanceGrader()
        self.revenue_est = RevenueEstimator()

    def run_ticket(self, ticket_id: str, simulation_mode: bool = True) -> TicketResult:
        try:
            ticket = get_seeded_ticket(ticket_id)
        except KeyError as e:
            return TicketResult(
                ticket_id=ticket_id, title="unknown", success=False,
                acceptance_grade=AcceptanceGrade.REJECTED_MAJOR, score=0.0,
                revenue_earned=0.0, duration_hours=0.0,
                criteria_met=0, criteria_total=0,
                hidden_tests_passed=0, hidden_tests_total=0,
                constraints_violated=[], ambiguity_resolved=False,
                errors=[str(e)],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        estimated = self.revenue_est.estimate(ticket)
        grader_result = self.grader.grade(ticket, simulation=simulation_mode)

        if self.dry_run:
            return TicketResult(
                ticket_id=ticket_id, title=ticket.title,
                success=False, acceptance_grade=None, score=0.0,
                revenue_earned=0.0, duration_hours=0.0,
                criteria_met=0, criteria_total=len(ticket.acceptance_criteria),
                hidden_tests_passed=0, hidden_tests_total=len(ticket.hidden_tests),
                constraints_violated=[], ambiguity_resolved=False,
                timestamp=timestamp,
                details={
                    "dry_run": True,
                    "ticket": ticket.to_dict(),
                    "estimated_revenue": estimated,
                },
            )

        result = TicketResult(
            ticket_id=ticket_id,
            title=ticket.title,
            success=grader_result["success"],
            acceptance_grade=grader_result["grade"],
            score=grader_result["score"],
            revenue_earned=grader_result["revenue_earned"],
            duration_hours=grader_result.get("duration_hours", ticket.estimated_hours),
            criteria_met=grader_result["criteria_met"],
            criteria_total=grader_result["criteria_total"],
            hidden_tests_passed=grader_result["hidden_tests_passed"],
            hidden_tests_total=grader_result["hidden_tests_total"],
            constraints_violated=grader_result["constraints_violated"],
            ambiguity_resolved=grader_result["ambiguity_resolved"],
            timestamp=timestamp,
            details=grader_result.get("details", {}),
        )

        self._save_result(result)
        return result

    def run_all(self) -> TicketRun:
        run_id = uuid.uuid4().hex[:12]
        run = TicketRun(
            run_id=run_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        for ticket in SEEDED_TICKETS:
            result = self.run_ticket(ticket.id, simulation_mode=True)
            run.add_result(result)
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.compute_summary()
        self._save_run(run)
        return run

    def _save_result(self, result: TicketResult) -> None:
        path = self.output_dir / "results" / f"{result.ticket_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2))

    def _save_run(self, run: TicketRun) -> None:
        path = self.output_dir / "runs" / f"run-{run.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "run_id": run.run_id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "summary": run.summary,
            "results": [r.to_dict() for r in run.results],
        }
        path.write_text(json.dumps(data, indent=2))
