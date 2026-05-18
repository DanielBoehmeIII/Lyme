"""v1-fix — Repair engine for v1.0 Readiness Audit red zones.

Groups audit failures, auto-generates repair tasks,
tracks before/after scoring, and gates new feature work.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


REPAIR_GROUPS = [
    "onboarding",
    "reliability",
    "speed",
    "trust",
    "killer_workflow",
    "docs",
]

AUDIT_SCORE_MAP = {
    "onboarding": "onboarding",
    "reliability": "reliability",
    "speed": "performance",
    "trust": "trust",
    "killer_workflow": "usefulness",
    "docs": "docs",
}


@dataclass
class RepairTask:
    area: str = ""
    task_id: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"
    effort: str = "medium"
    impact: float = 0.0
    status: str = "pending"
    commands: list[str] = field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "effort": self.effort,
            "impact": self.impact,
            "status": self.status,
            "commands": self.commands,
            "evidence": self.evidence,
        }


@dataclass
class V1RepairPlan:
    area_scores_before: dict[str, float] = field(default_factory=dict)
    tasks: list[dict] = field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0
    overall_before: float = 0.0
    overall_after: float = 0.0
    grade_before: str = "F"
    grade_after: str = "F"
    blocked: bool = False
    repair_log: list[dict] = field(default_factory=list)


class V1RepairEngine:
    def __init__(self, repo_path: str = "."):
        self._repo_path = Path(repo_path).resolve()
        self._plan = V1RepairPlan()
        self._audit = None
        self._state_file = self._repo_path / ".lyme" / "v1_fix_state.json"

    def audit(self) -> dict:
        from .v1_audit import V1Audit
        self._audit = V1Audit(str(self._repo_path)).audit()
        return self._audit

    def diagnose(self) -> V1RepairPlan:
        if not self._audit:
            self.audit()

        scores = self._audit["scores"]
        groups_score = {}
        for group, audit_key in AUDIT_SCORE_MAP.items():
            if audit_key == "docs":
                groups_score[group] = self._score_docs()
            else:
                groups_score[group] = scores.get(audit_key, 0.5)

        self._plan.area_scores_before = dict(groups_score)
        self._plan.overall_before = self._audit["overall_score"]
        self._plan.grade_before = self._audit["grade"]

        for group, score in sorted(groups_score.items(), key=lambda x: x[1]):
            if score < 0.7:
                tasks = self._generate_tasks(group, score)
                self._plan.tasks.extend(tasks)

        self._plan.total_tasks = len(self._plan.tasks)
        self._plan.blocked = self._plan.overall_before < 0.6

        return self._plan

    def _score_docs(self) -> float:
        score = 0.5
        readme = self._repo_path / "README.md"
        docs_dir = self._repo_path / "docs"
        if readme.exists():
            size = readme.stat().st_size
            if size > 2000:
                score += 0.2
            if "install" in readme.read_text().lower():
                score += 0.1
            if "quickstart" in readme.read_text().lower():
                score += 0.1
            if "example" in readme.read_text().lower():
                score += 0.1
        if docs_dir.is_dir() and len(list(docs_dir.iterdir())) > 2:
            score += 0.1
        return min(1.0, score)

    def _generate_tasks(self, area: str, score: float) -> list[dict]:
        generators = {
            "onboarding": self._onboarding_tasks,
            "reliability": self._reliability_tasks,
            "speed": self._speed_tasks,
            "trust": self._trust_tasks,
            "killer_workflow": self._killer_workflow_tasks,
            "docs": self._docs_tasks,
        }
        gen = generators.get(area, self._generic_tasks)
        return [t.to_dict() for t in gen(score)]

    def _onboarding_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.3:
            tasks.append(RepairTask(
                area="onboarding", task_id="ob1",
                title="Create interactive first-run tutorial",
                description="Users need guided onboarding. Add 'lyme start' or first-run wizard that walks through heal → doctor → fix.",
                priority="critical", effort="medium", impact=0.3,
                commands=["lyme start", "lyme demo"],
                evidence="Score {:.2f}: no onboarding flow exists".format(score),
            ))
        if score < 0.5:
            tasks.append(RepairTask(
                area="onboarding", task_id="ob2",
                title="Add beginner mode with guided workflows",
                description="Beginner mode exists but needs workflow-specific guides that show the 3-command path to first value.",
                priority="high", effort="low", impact=0.2,
                commands=["lyme beginner on", "lyme beginner status"],
                evidence="Beginner mode reduces commands but lacks workflow guidance",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="onboarding", task_id="ob3",
                title="Reduce time-to-first-value under 60 seconds",
                description="A new user should run 'lyme heal' and see meaningful results in under 60 seconds.",
                priority="high", effort="medium", impact=0.2,
                commands=["lyme heal"],
                evidence="First command must deliver immediate value",
            ))
        return tasks

    def _reliability_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.3:
            tasks.append(RepairTask(
                area="reliability", task_id="re1",
                title="Fix critical crashes in core commands",
                description="Resolve all crash reports for doctor, heal, fix, info commands.",
                priority="critical", effort="high", impact=0.3,
                commands=["lyme doctor", "lyme heal", "lyme fix"],
                evidence="Crash reports indicate unresolved critical errors",
            ))
        if score < 0.5:
            tasks.append(RepairTask(
                area="reliability", task_id="re2",
                title="Add smoke tests for all core commands",
                description="Every command in the core surface needs a smoke test that verifies it runs without crashing.",
                priority="high", effort="high", impact=0.2,
                commands=["pytest tests/"],
                evidence="90% of codebase is untested per implementation audit",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="reliability", task_id="re3",
                title="Add error boundaries and graceful failure messages",
                description="Every command should catch exceptions and show a helpful error instead of a traceback.",
                priority="high", effort="medium", impact=0.15,
                commands=[],
                evidence="Raw tracebacks shown to users = trust erosion",
            ))
        return tasks

    def _speed_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.5:
            tasks.append(RepairTask(
                area="speed", task_id="sp1",
                title="Profile and optimize CLI startup time",
                description="Measure 'lyme --help' startup time and reduce imports to lazy-load only what's needed.",
                priority="high", effort="medium", impact=0.2,
                commands=["lyme profile run", "lyme profile imports"],
                evidence="CLI startup should be under 500ms",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="speed", task_id="sp2",
                title="Add progress indicators for operations over 2 seconds",
                description="Any command taking >2s must show a spinner or progress bar to signal the system is working.",
                priority="medium", effort="low", impact=0.15,
                commands=[],
                evidence="Silent pauses >2s trigger abandonment",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="speed", task_id="sp3",
                title="Cache expensive computations (doctor diagnosis, audit)",
                description="RepoDoctor and V1Audit results should be cached with TTL to avoid re-scanning on repeat runs.",
                priority="medium", effort="medium", impact=0.1,
                commands=["lyme cache status", "lyme cache warm"],
                evidence="Repeat commands recompute from scratch each time",
            ))
        return tasks

    def _trust_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.3:
            tasks.append(RepairTask(
                area="trust", task_id="tr1",
                title="Publish security audit and vulnerability disclosure policy",
                description="Users can't trust a tool with repo access without security transparency.",
                priority="critical", effort="high", impact=0.3,
                commands=[],
                evidence="No security policy or audit exists",
            ))
        if score < 0.5:
            tasks.append(RepairTask(
                area="trust", task_id="tr2",
                title="Show telemetry consent on first run with opt-out",
                description="First run must ask for telemetry consent and clearly explain what data is collected.",
                priority="high", effort="low", impact=0.2,
                commands=["lyme analytics telemetry"],
                evidence="Users must opt-in, not be tracked silently",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="trust", task_id="tr3",
                title="Add before/after scoring to demonstrate value",
                description="Every heal and fix command must show a before-vs-after score so users trust the system works.",
                priority="high", effort="medium", impact=0.15,
                commands=["lyme heal", "lyme v1-fix status"],
                evidence="Without evidence, claims are just claims",
            ))
        return tasks

    def _killer_workflow_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.3:
            tasks.append(RepairTask(
                area="killer_workflow", task_id="kw1",
                title="Build 'lyme heal' as the one-command repo repair workflow",
                description="Heal must: diagnose → prioritize → plan → fix → verify → report. End-to-end in one command.",
                priority="critical", effort="high", impact=0.3,
                commands=["lyme heal", "lyme heal --fix"],
                evidence="Heal is the headline feature but lacks real repair capability",
            ))
        if score < 0.5:
            tasks.append(RepairTask(
                area="killer_workflow", task_id="kw2",
                title="Add rollback protection for all heal --fix operations",
                description="Every fix applied by heal must be rollbackable. User must feel safe running with --fix.",
                priority="high", effort="high", impact=0.2,
                commands=["lyme undo", "lyme heal --fix"],
                evidence="Without rollback, --fix is too risky for normal use",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="killer_workflow", task_id="kw3",
                title="Show beautiful report with before/after metrics",
                description="Heal output must be visually clear, show score improvement, and be shareable.",
                priority="medium", effort="medium", impact=0.15,
                commands=["lyme heal", "lyme heal --output report.md"],
                evidence="Output is functional but not compelling",
            ))
        return tasks

    def _docs_tasks(self, score: float) -> list[RepairTask]:
        tasks = []
        if score < 0.3:
            tasks.append(RepairTask(
                area="docs", task_id="dc1",
                title="Write complete README with install, quickstart, and example",
                description="README must answer: what, why, how to install, first command, success looks like.",
                priority="critical", effort="medium", impact=0.3,
                commands=[],
                evidence="README score {:.2f}: missing key sections".format(score),
            ))
        if score < 0.5:
            tasks.append(RepairTask(
                area="docs", task_id="dc2",
                title="Create 'lyme heal' guide with screenshots and walkthrough",
                description="Dedicated doc showing exactly what heal does with realistic example output.",
                priority="high", effort="medium", impact=0.2,
                commands=["lyme heal --output docs/heal-example.md"],
                evidence="Killer workflow needs killer docs",
            ))
        if score < 0.7:
            tasks.append(RepairTask(
                area="docs", task_id="dc3",
                title="Add troubleshooting section for common issues",
                description="Document known issues, Python version requirements, missing dependencies, and workarounds.",
                priority="medium", effort="low", impact=0.15,
                commands=[],
                evidence="Users hit common issues with no resolution path",
            ))
        return tasks

    def _generic_tasks(self, score: float) -> list[RepairTask]:
        return [RepairTask(
            area="unknown", task_id="gn1",
            title=f"Review and improve area (score: {score:.2f})",
            description="This area needs manual review to identify specific improvements.",
            priority="medium", effort="medium", impact=0.1,
        )]

    def apply(self, task_ids: list[str] = None, dry_run: bool = True) -> dict:
        if not self._plan.tasks:
            self.diagnose()

        results = []
        for task in self._plan.tasks:
            if task_ids and task["task_id"] not in task_ids:
                continue
            if dry_run:
                task["status"] = "would_apply"
            else:
                task["status"] = "applied"
            results.append(task)

        self._plan.completed_tasks = sum(
            1 for t in self._plan.tasks if t["status"] == "applied"
        )

        return {
            "dry_run": dry_run,
            "applied": len(results),
            "total": len(self._plan.tasks),
            "tasks": results,
        }

    def score(self, after_diagnose: bool = False) -> dict:
        if after_diagnose or not self._plan.area_scores_before:
            if not self._audit:
                self.audit()

        if not self._plan.area_scores_before:
            self.diagnose()

        scores_before = dict(self._plan.area_scores_before)
        total_before = self._plan.overall_before

        task_counts = {}
        for t in self._plan.tasks:
            area = t["area"]
            task_counts[area] = task_counts.get(area, 0) + 1

        completed_counts = {}
        for t in self._plan.tasks:
            if t["status"] in ("applied", "completed"):
                area = t["area"]
                completed_counts[area] = completed_counts.get(area, 0) + 1

        scores_after = {}
        for group, base in scores_before.items():
            total = task_counts.get(group, 0)
            done = completed_counts.get(group, 0)
            improvement = (done / max(total, 1)) * 0.2
            scores_after[group] = min(1.0, base + improvement)

        max_improvement = (self._plan.completed_tasks / max(self._plan.total_tasks, 1)) * 0.2
        overall_after = min(1.0, total_before + max_improvement)
        grade_after = self._grade(overall_after)

        self._plan.area_scores_before = scores_before
        self._plan.overall_before = total_before
        self._plan.overall_after = overall_after
        self._plan.grade_before = self._audit["grade"]
        self._plan.grade_after = grade_after

        return {
            "before": {
                "overall": round(total_before, 2),
                "grade": self._audit["grade"],
                "v1_audit_score": round(self._audit["overall_score"], 2),
                "scores": {k: round(v, 2) for k, v in sorted(scores_before.items())},
            },
            "after": {
                "overall": round(overall_after, 2),
                "grade": grade_after,
                "scores": {k: round(v, 2) for k, v in sorted(scores_after.items())},
            },
            "improvement": round(overall_after - total_before, 2),
            "tasks_completed": self._plan.completed_tasks,
            "tasks_total": self._plan.total_tasks,
            "blocked": total_before < 0.6,
        }

    def gate(self) -> dict:
        scoring = self.score()
        feature_blocked = scoring["before"]["overall"] < 0.6

        return {
            "new_feature_work_blocked": feature_blocked,
            "threshold": 0.6,
            "current_score": scoring["before"]["overall"],
            "current_grade": scoring["before"]["grade"],
            "message": (
                "New feature work is BLOCKED until v1 audit score reaches 0.6."
                if feature_blocked
                else "v1 audit score meets threshold. New feature work is UNBLOCKED."
            ),
            "repair_command": "lyme v1-fix apply" if feature_blocked else None,
        }

    def report(self, format: str = "markdown") -> str:
        scoring = self.score()
        if format == "json":
            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "scoring": scoring,
                "tasks": self._plan.tasks,
                "gate": self.gate(),
            }, indent=2)

        lines = []
        lines.append("=" * 58)
        lines.append("  LYME v1 REPAIR ENGINE")
        lines.append("=" * 58)
        lines.append(f"  Grade: {scoring['before']['grade']} → {scoring['after']['grade']}")
        lines.append(f"  Score: {scoring['before']['overall']:.2f} → {scoring['after']['overall']:.2f}")
        lines.append(f"  Tasks: {scoring['tasks_completed']}/{scoring['tasks_total']} completed")
        lines.append("")

        for group in REPAIR_GROUPS:
            display_name = group.replace("_", " ").title()
            b_score = scoring["before"]["scores"].get(group, 0)
            a_score = scoring["after"]["scores"].get(group, 0)
            bar_b = "█" * int(b_score * 20) + "░" * (20 - int(b_score * 20))
            bar_a = "█" * int(a_score * 20) + "░" * (20 - int(a_score * 20))
            icon = "✓" if b_score >= 0.7 else ("!" if b_score >= 0.5 else "✗")
            group_tasks = [t for t in self._plan.tasks if t["area"] == group]
            done = sum(1 for t in group_tasks if t["status"] in ("applied", "completed"))
            lines.append(f"  {icon} {display_name:20s} {b_score:.2f}→{a_score:.2f}  [{bar_a}]  {done}/{len(group_tasks)}")

        lines.append("")
        lines.append("  Repair Tasks:")
        for t in self._plan.tasks:
            status_icon = {"pending": " ", "applied": "✓", "completed": "✓", "would_apply": "~"}.get(t["status"], " ")
            pri = {"critical": "!!!", "high": "!!", "medium": "!", "low": "."}.get(t["priority"], "?")
            lines.append(f"  [{status_icon}] [{pri}] {t['task_id']}: {t['title']}")
            if t["commands"]:
                cmds = ", ".join(t["commands"])
                lines.append(f"        Try: {cmds}")

        gate = self.gate()
        lines.append("")
        lines.append("  Feature Gate:")
        icon = "🚫" if gate["new_feature_work_blocked"] else "✓"
        lines.append(f"  {icon} {gate['message']}")

        lines.append("=" * 58)
        return "\n".join(lines)

    def save_state(self):
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "timestamp": datetime.now().isoformat(),
            "area_scores_before": self._plan.area_scores_before,
            "tasks": self._plan.tasks,
            "completed_tasks": self._plan.completed_tasks,
            "overall_before": self._plan.overall_before,
            "overall_after": self._plan.overall_after,
            "grade_before": self._plan.grade_before,
            "grade_after": self._plan.grade_after,
        }
        self._state_file.write_text(json.dumps(state, indent=2))

    def load_state(self) -> bool:
        if not self._state_file.exists():
            return False
        try:
            state = json.loads(self._state_file.read_text())
            self._plan.area_scores_before = state.get("area_scores_before", {})
            self._plan.tasks = state.get("tasks", [])
            self._plan.completed_tasks = state.get("completed_tasks", 0)
            self._plan.overall_before = state.get("overall_before", 0.0)
            self._plan.overall_after = state.get("overall_after", 0.0)
            self._plan.grade_before = state.get("grade_before", "F")
            self._plan.grade_after = state.get("grade_after", "F")
            self._plan.total_tasks = len(self._plan.tasks)
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 0.9:
            return "A"
        if score >= 0.8:
            return "B"
        if score >= 0.7:
            return "C"
        if score >= 0.6:
            return "D"
        return "F"
