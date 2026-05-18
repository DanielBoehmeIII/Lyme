"""ImplementationPlanner — build an implementation plan from an issue ticket."""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from .models import IssueTicket, ImplementationPlan, ImplementationStep, RiskReport


class ImplementationPlanner:
    """Parse issue requirements and produce an actionable implementation plan."""

    def plan(self, ticket: IssueTicket) -> ImplementationPlan:
        steps = self._build_steps(ticket)
        files = self._estimate_files(ticket)
        branch = self._generate_branch_name(ticket)
        rollback = self._build_rollback_instructions(steps)

        return ImplementationPlan(
            ticket_id=ticket.id,
            title=ticket.title,
            summary=self._generate_summary(ticket, steps),
            branch_name=branch,
            steps=steps,
            estimated_difficulty=self._estimate_difficulty(ticket),
            estimated_files=files,
            test_strategy=self._build_test_strategy(ticket),
            rollback_instructions=rollback,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def assess_risk(self, ticket: IssueTicket, plan: ImplementationPlan) -> RiskReport:
        risks = []
        mitigations = []
        concerns = []

        for step in plan.steps:
            if step.risk == "high":
                risks.append({"file": step.file, "risk": step.risk,
                              "description": f"{step.action} on {step.file}",
                              "impact": "May require complex changes"})
                mitigations.append(f"Review {step.file} changes carefully before merging")

        if len(plan.steps) > 5:
            risks.append({"file": "multiple", "risk": "medium",
                          "description": f"{len(plan.steps)} implementation steps",
                          "impact": "Higher chance of merge conflicts"})
            mitigations.append("Rebase frequently to minimize conflicts")

        if ticket.labels:
            if "bug" in [l.lower() for l in ticket.labels]:
                concerns.append("Fixing a bug — may have unknown side effects")
                mitigations.append("Add regression tests for the fix")

        file_overlap = self._check_file_overlap(ticket)
        if file_overlap:
            risks.append({"file": file_overlap, "risk": "medium",
                          "description": "Same file edited by multiple steps",
                          "impact": "Risk of conflicting changes"})

        score = self._compute_risk_score(risks, len(plan.steps))
        overall = "low" if score < 0.3 else ("medium" if score < 0.6 else "high")

        return RiskReport(
            overall_risk=overall,
            risk_score=round(score, 3),
            risks=risks,
            mitigations=mitigations,
            concerns=concerns,
        )

    def _build_steps(self, ticket: IssueTicket) -> list[ImplementationStep]:
        steps = []
        order = 1

        # Extract file references and action items from requirements
        files_mentioned = self._extract_files(ticket.body)
        actions = []

        for req in ticket.parsed_requirements:
            actions.append(req)

        for criterion in ticket.acceptance_criteria:
            if "implement" in criterion.description.lower() or "add" in criterion.description.lower():
                target = files_mentioned[0] if files_mentioned else "src/main.py"
                steps.append(ImplementationStep(
                    order=order, action="implement", file=target,
                    description=criterion.description, risk="medium"
                ))
                order += 1
            elif "fix" in criterion.description.lower() or "repair" in criterion.description.lower():
                target = files_mentioned[0] if files_mentioned else "src/main.py"
                steps.append(ImplementationStep(
                    order=order, action="fix", file=target,
                    description=criterion.description, risk="high",
                ))
                order += 1
            elif "test" in criterion.description.lower():
                steps.append(ImplementationStep(
                    order=order, action="test", file="tests/",
                    description=criterion.description, risk="low",
                ))
                order += 1
            elif "doc" in criterion.description.lower() or "readme" in criterion.description.lower():
                steps.append(ImplementationStep(
                    order=order, action="document", file="README.md",
                    description=criterion.description, risk="low",
                ))
                order += 1
            else:
                target = files_mentioned[0] if files_mentioned else "src/main.py"
                steps.append(ImplementationStep(
                    order=order, action="modify", file=target,
                    description=criterion.description, risk="medium",
                ))
                order += 1

        if not steps:
            steps.append(ImplementationStep(
                order=1, action="modify", file="src/main.py",
                description="Implement issue requirements", risk="medium",
            ))

        # Add testing step
        steps.append(ImplementationStep(
            order=order, action="test", file="tests/",
            description="Run tests to verify changes", risk="low",
        ))

        return steps

    def _estimate_files(self, ticket: IssueTicket) -> list[str]:
        files = set()
        for criterion in ticket.acceptance_criteria:
            for f in self._extract_files(criterion.description):
                files.add(f)
        if not files:
            files.add("src/main.py")
        return sorted(files)

    def _generate_branch_name(self, ticket: IssueTicket) -> str:
        clean = re.sub(r'[^a-z0-9]+', '-', ticket.title.lower()).strip('-')[:40]
        return f"fix/{ticket.id}-{clean}"

    def _generate_summary(self, ticket: IssueTicket, steps: list[ImplementationStep]) -> str:
        return (
            f"Implements {len(steps)} steps to address: {ticket.title}\n\n"
            f"Acceptance criteria: {len(ticket.acceptance_criteria)} items\n"
            f"Files to modify: {len(self._estimate_files(ticket))}"
        )

    def _extract_files(self, text: str) -> list[str]:
        patterns = [
            r'`([^`]+\.[a-z]+)`',
            r'file:?\s*([^\s,]+)',
            r'in\s+`([^`]+)`',
        ]
        files = []
        for pattern in patterns:
            files.extend(re.findall(pattern, text))
        return files

    def _build_rollback_instructions(self, steps: list[ImplementationStep]) -> list[str]:
        instructions = [
            f"git checkout main",
            f"git branch -D {self._sanitize_branch(steps)}" if steps else "git branch -D <branch>",
            "Re-assign issue to original state",
        ]
        return instructions

    def _sanitize_branch(self, steps: list[ImplementationStep]) -> str:
        descs = [s.description for s in steps if s.description]
        combined = " ".join(descs) if descs else "feature"
        clean = re.sub(r'[^a-z0-9]+', '-', combined.lower())[:30]
        return f"fix/{clean}"

    def _build_test_strategy(self, ticket: IssueTicket) -> str:
        has_test_ac = any("test" in c.description.lower() for c in ticket.acceptance_criteria)
        if has_test_ac:
            return "Run existing test suite + add new tests for changed functionality"
        return "Run existing test suite to verify no regressions"

    def _estimate_difficulty(self, ticket: IssueTicket) -> str:
        n_criteria = len(ticket.acceptance_criteria)
        if n_criteria > 5:
            return "hard"
        elif n_criteria > 2:
            return "medium"
        return "easy"

    def _compute_risk_score(self, risks: list[dict], step_count: int) -> float:
        base = 0.1
        for r in risks:
            if r["risk"] == "high":
                base += 0.2
            elif r["risk"] == "medium":
                base += 0.1
        base += step_count * 0.03
        return min(base, 1.0)

    def _check_file_overlap(self, ticket: IssueTicket) -> str:
        files = self._extract_files(ticket.body)
        from collections import Counter
        counts = Counter(files)
        for f, c in counts.most_common():
            if c > 1:
                return f
        return ""

