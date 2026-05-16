import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class ThoughtType(str, Enum):
    PLAN = "plan"
    DECISION = "decision"
    EXPLORATION = "exploration"
    UNCERTAINTY = "uncertainty"
    RETRY = "retry"
    ERROR = "error"
    HALLUCINATION = "hallucination"
    INSIGHT = "insight"
    REASONING = "reasoning"
    QUESTION = "question"
    CONCLUSION = "conclusion"
    ABANDONED = "abandoned"
    NAVIGATION = "navigation"
    TOOL_SELECTION = "tool_selection"
    CONTEXT_SHIFT = "context_shift"
    STATE_CHECK = "state_check"


@dataclass
class ThoughtStep:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    type: str = ThoughtType.REASONING
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    branch: str = "main"
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    duration_ms: Optional[float] = None
    token_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "branch": self.branch,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "token_count": self.token_count,
        }


@dataclass
class DecisionPoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    timestamp: float = field(default_factory=time.time)
    question: str = ""
    options: List[str] = field(default_factory=list)
    chosen: str = ""
    rationale: str = ""
    confidence: float = 1.0
    outcome: str = "pending"
    alternatives_explored: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "question": self.question,
            "options": self.options,
            "chosen": self.chosen,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "alternatives_explored": self.alternatives_explored,
        }


@dataclass
class CognitiveTrace:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    agent_name: str = ""
    scenario_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    steps: List[ThoughtStep] = field(default_factory=list)
    decisions: List[DecisionPoint] = field(default_factory=list)
    branches: Dict[str, int] = field(default_factory=dict)
    status: str = "recording"
    summary: dict = field(default_factory=dict)

    def add_step(self, step: ThoughtStep):
        self.steps.append(step)
        self.branches[step.branch] = self.branches.get(step.branch, 0) + 1

    def add_decision(self, decision: DecisionPoint):
        self.decisions.append(decision)

    def finish(self, status: str = "completed", metrics: dict = None):
        self.end_time = time.time()
        self.status = status
        total_duration = (self.end_time - self.start_time) * 1000 if self.end_time else 0

        unresolved = sum(1 for d in self.decisions if d.outcome == "pending")
        abandoned = sum(1 for s in self.steps if s.type == ThoughtType.ABANDONED)
        errors = sum(1 for s in self.steps if s.type == ThoughtType.ERROR)
        uncertainties = sum(1 for s in self.steps if s.type == ThoughtType.UNCERTAINTY)

        self.summary = {
            "duration_ms": total_duration,
            "total_steps": len(self.steps),
            "total_decisions": len(self.decisions),
            "branches_explored": len(self.branches),
            "unresolved_decisions": unresolved,
            "abandoned_approaches": abandoned,
            "error_count": errors,
            "uncertainty_count": uncertainties,
            "avg_confidence": sum(s.confidence for s in self.steps) / len(self.steps) if self.steps else 0,
            "status": status,
            **(metrics or {}),
        }

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "scenario_name": self.scenario_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "steps": [s.to_dict() for s in self.steps],
            "decisions": [d.to_dict() for d in self.decisions],
            "branches": self.branches,
            "status": self.status,
            "summary": self.summary,
        }
