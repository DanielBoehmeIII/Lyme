"""WorkflowRecorder — captures operation sequences from real sessions."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import json


class ActionType(str, Enum):
    READ_FILE = "read_file"
    EDIT_FILE = "edit_file"
    RUN_COMMAND = "run_command"
    SEARCH_CODE = "search_code"
    VERIFY_TEST = "verify_test"
    REVIEW_DIFF = "review_diff"
    ASK_QUESTION = "ask_question"
    PLAN_TASK = "plan_task"
    DEBUG_FAILURE = "debug_failure"
    ROLLBACK = "rollback"
    COMMIT = "commit"
    DEPLOY = "deploy"


class ActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    action: ActionType
    target: str
    outcome: ActionOutcome
    duration_sec: float
    timestamp: float
    context: str = ""
    error: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "action": self.action.value,
            "target": self.target[:80],
            "outcome": self.outcome.value,
            "duration_sec": round(self.duration_sec, 2),
            "context": self.context[:100],
            "has_error": bool(self.error),
        }


@dataclass
class WorkflowSession:
    id: str
    goal: str
    steps: List[WorkflowStep]
    total_duration_sec: float
    success: bool
    created_at: float
    repo: str = ""
    language: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal[:80],
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_sec": round(self.total_duration_sec, 1),
            "success": self.success,
            "repo": self.repo,
            "language": self.language,
        }


@dataclass
class WorkflowPattern:
    action_sequence: List[str]
    frequency: int
    avg_duration_sec: float
    success_rate: float
    common_goal_types: List[str]
    avg_step_count: float
    last_seen: float

    def to_dict(self) -> Dict:
        return {
            "action_sequence": self.action_sequence,
            "frequency": self.frequency,
            "avg_duration_sec": round(self.avg_duration_sec, 1),
            "success_rate": round(self.success_rate, 3),
            "common_goal_types": self.common_goal_types[:3],
            "avg_step_count": round(self.avg_step_count, 1),
        }


@dataclass
class WorkflowIntelligenceReport:
    total_sessions: int
    total_steps: int
    common_patterns: List[WorkflowPattern]
    action_frequencies: Dict[str, int]
    success_rate: float
    avg_session_duration: float
    insights: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_sessions": self.total_sessions,
            "total_steps": self.total_steps,
            "common_patterns": [p.to_dict() for p in self.common_patterns[:5]],
            "action_frequencies": dict(sorted(self.action_frequencies.items(), key=lambda x: -x[1])[:10]),
            "success_rate": round(self.success_rate, 3),
            "avg_session_duration": round(self.avg_session_duration, 1),
            "insights": self.insights,
            "recommendations": self.recommendations,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  WORKFLOW INTELLIGENCE REPORT")
        lines.append("=" * 70)
        lines.append(f"  Sessions: {self.total_sessions} | "
                     f"Steps: {self.total_steps} | "
                     f"Success Rate: {self.success_rate:.0%}")
        lines.append(f"  Avg Session Duration: {self.avg_session_duration:.1f}s")
        lines.append("")
        lines.append("  Action Frequencies:")
        for action, count in sorted(self.action_frequencies.items(), key=lambda x: -x[1])[:8]:
            bar = "█" * min(count, 20)
            lines.append(f"    {action}: {count} {bar}")
        if self.common_patterns:
            lines.append("")
            lines.append("  Common Patterns:")
            for p in self.common_patterns[:3]:
                seq = " → ".join(p.action_sequence[:4])
                lines.append(f"    {seq}")
                lines.append(f"      frequency={p.frequency}, sr={p.success_rate:.0%}, "
                             f"avg={p.avg_duration_sec:.0f}s")
        if self.insights:
            lines.append("-" * 70)
            lines.append("  INSIGHTS:")
            for ins in self.insights:
                lines.append(f"    • {ins}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class WorkflowRecorder:
    def __init__(self, storage_path: Optional[str] = None):
        self._sessions: List[WorkflowSession] = []
        self._current_session: Optional[WorkflowSession] = None
        self._storage_path = storage_path
        self._load()

    def start_session(self, goal: str, repo: str = "", language: str = "") -> str:
        session_id = str(uuid.uuid4())[:8]
        self._current_session = WorkflowSession(
            id=session_id,
            goal=goal,
            steps=[],
            total_duration_sec=0.0,
            success=False,
            created_at=time.time(),
            repo=repo,
            language=language,
        )
        return session_id

    def record_step(self, action: ActionType, target: str, outcome: ActionOutcome,
                    duration_sec: float, context: str = "", error: str = "") -> None:
        if not self._current_session:
            return
        step = WorkflowStep(
            action=action,
            target=target,
            outcome=outcome,
            duration_sec=duration_sec,
            timestamp=time.time(),
            context=context,
            error=error,
        )
        self._current_session.steps.append(step)

    def end_session(self, success: bool) -> Optional[str]:
        if not self._current_session:
            return None
        if self._current_session.steps:
            start = self._current_session.steps[0].timestamp
            end = self._current_session.steps[-1].timestamp
            self._current_session.total_duration_sec = end - start
        self._current_session.success = success
        session = self._current_session
        self._sessions.append(session)
        self._current_session = None
        self._save()
        return session.id

    def analyze(self) -> WorkflowIntelligenceReport:
        if not self._sessions:
            return WorkflowIntelligenceReport(
                total_sessions=0, total_steps=0, common_patterns=[],
                action_frequencies={}, success_rate=0.0,
                avg_session_duration=0.0,
                insights=["No workflow data yet"],
                recommendations=["Start recording sessions to generate insights"],
            )

        total_steps = sum(len(s.steps) for s in self._sessions)
        successful = sum(1 for s in self._sessions if s.success)
        success_rate = successful / max(len(self._sessions), 1)
        avg_duration = sum(s.total_duration_sec for s in self._sessions) / max(len(self._sessions), 1)

        action_freq: Dict[str, int] = {}
        for s in self._sessions:
            for step in s.steps:
                action_freq[step.action.value] = action_freq.get(step.action.value, 0) + 1

        patterns = self._discover_patterns()
        insights = self._generate_insights(action_freq, success_rate, patterns)
        recommendations = self._generate_recommendations(success_rate, action_freq, patterns)

        return WorkflowIntelligenceReport(
            total_sessions=len(self._sessions),
            total_steps=total_steps,
            common_patterns=patterns,
            action_frequencies=action_freq,
            success_rate=success_rate,
            avg_session_duration=avg_duration,
            insights=insights,
            recommendations=recommendations,
        )

    def _discover_patterns(self, min_occurrences: int = 2) -> List[WorkflowPattern]:
        if len(self._sessions) < min_occurrences:
            return []

        sequence_map: Dict[tuple, Dict] = {}
        for s in self._sessions:
            if len(s.steps) < 2:
                continue
            actions = tuple(step.action.value for step in s.steps)
            if actions not in sequence_map:
                sequence_map[actions] = {"count": 0, "successes": 0,
                                         "durations": [], "goals": []}
            entry = sequence_map[actions]
            entry["count"] += 1
            if s.success:
                entry["successes"] += 1
            entry["durations"].append(s.total_duration_sec)
            entry["goals"].append(s.goal[:40])

        patterns = []
        for seq, data in sequence_map.items():
            if data["count"] >= min_occurrences:
                patterns.append(WorkflowPattern(
                    action_sequence=list(seq),
                    frequency=data["count"],
                    avg_duration_sec=sum(data["durations"]) / max(len(data["durations"]), 1),
                    success_rate=data["successes"] / max(data["count"], 1),
                    common_goal_types=list(set(data["goals"][:5])),
                    avg_step_count=len(seq),
                    last_seen=time.time(),
                ))

        patterns.sort(key=lambda p: -p.frequency)
        return patterns

    def _generate_insights(self, action_freq: Dict[str, int],
                           success_rate: float,
                           patterns: List[WorkflowPattern]) -> List[str]:
        insights: List[str] = []
        if not action_freq:
            return insights

        most_common = max(action_freq, key=action_freq.get)
        insights.append(f"Most common action: {most_common} ({action_freq[most_common]} uses)")

        if success_rate > 0.8:
            insights.append(f"High overall success rate: {success_rate:.0%}")
        elif success_rate < 0.5:
            insights.append(f"Low success rate ({success_rate:.0%}) — consider revising workflows")

        if patterns:
            best = max(patterns, key=lambda p: p.success_rate)
            insights.append(f"Best pattern: {' → '.join(best.action_sequence[:3])} "
                           f"({best.success_rate:.0%} success in {best.frequency} sessions)")

        edit_count = action_freq.get(ActionType.EDIT_FILE.value, 0)
        verify_count = action_freq.get(ActionType.VERIFY_TEST.value, 0)
        if edit_count > verify_count * 2:
            insights.append(f"Edit-heavy workflow ({edit_count} edits vs {verify_count} verifications)")

        return insights

    def _generate_recommendations(self, success_rate: float,
                                  action_freq: Dict[str, int],
                                  patterns: List[WorkflowPattern]) -> List[str]:
        recs: List[str] = []
        if success_rate < 0.6:
            recs.append("Consider adding verification steps between edit actions")
            recs.append("Review failed sessions for common failure patterns")
        if action_freq.get(ActionType.VERIFY_TEST.value, 0) == 0:
            recs.append("Add test verification steps to improve reliability")
        if patterns:
            best = max(patterns, key=lambda p: p.success_rate)
            recs.append(f"Recommended pattern: {' → '.join(best.action_sequence)}")
        if not recs:
            recs.append("Workflow patterns are healthy — continue current approach")
        return recs

    def get_pattern_for_goal(self, goal_keyword: str) -> Optional[List[str]]:
        desc_lower = goal_keyword.lower()
        matching = []
        for s in self._sessions:
            if desc_lower in s.goal.lower() and s.success and len(s.steps) >= 2:
                actions = [step.action.value for step in s.steps]
                matching.append((len(s.steps), actions))
        if not matching:
            return None
        matching.sort(key=lambda x: -x[0])
        return matching[0][1]

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [s.to_dict() for s in self._sessions]
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                steps = [WorkflowStep(**s) for s in d.get("steps", [])]
                self._sessions.append(WorkflowSession(
                    id=d["id"], goal=d["goal"], steps=steps,
                    total_duration_sec=d.get("total_duration_sec", 0.0),
                    success=d.get("success", False),
                    created_at=d.get("created_at", 0.0),
                    repo=d.get("repo", ""), language=d.get("language", ""),
                ))
        except (json.JSONDecodeError, KeyError):
            pass
