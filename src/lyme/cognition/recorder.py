import time
from typing import Optional, List, Dict, Any
from .trace import CognitiveTrace, ThoughtStep, ThoughtType, DecisionPoint
from ..telemetry import MetricsStore


class ThoughtRecorder:
    def __init__(self, store: MetricsStore = None):
        self._current_trace: Optional[CognitiveTrace] = None
        self._traces: Dict[str, CognitiveTrace] = {}
        self._store = store or MetricsStore()
        self._step_stack: List[str] = []
        self._step_start_times: Dict[str, float] = {}

    def begin_trace(self, trace_id: str = "", agent_name: str = "",
                    scenario_name: str = "") -> CognitiveTrace:
        kwargs = {"agent_name": agent_name, "scenario_name": scenario_name}
        if trace_id:
            kwargs["trace_id"] = trace_id
        trace = CognitiveTrace(**kwargs)
        self._current_trace = trace
        self._traces[trace.trace_id] = trace
        return trace

    def record_plan(self, plan: str, context: dict = None) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.PLAN,
            content=plan,
            metadata={"context": context or {}},
        )

    def record_decision(self, question: str, options: list, chosen: str,
                        rationale: str = "", confidence: float = 1.0,
                        outcome: str = "pending") -> DecisionPoint:
        decision = DecisionPoint(
            question=question,
            options=options,
            chosen=chosen,
            rationale=rationale,
            confidence=confidence,
            outcome=outcome,
        )
        if self._current_trace:
            self._current_trace.add_decision(decision)

        self._add_step(
            type_=ThoughtType.DECISION,
            content=f"Decision: {question} -> {chosen}",
            confidence=confidence,
            metadata={
                "question": question,
                "options": options,
                "chosen": chosen,
                "rationale": rationale,
                "decision_id": decision.id,
            },
        )

        if self._store:
            self._store.record("cognition.decision_confidence", confidence)

        return decision

    def record_exploration(self, approach: str, branch: str = "") -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.EXPLORATION,
            content=approach,
            branch=branch or f"explore_{time.time():.0f}",
        )

    def record_uncertainty(self, description: str, confidence: float = 0.3) -> ThoughtStep:
        step = self._add_step(
            type_=ThoughtType.UNCERTAINTY,
            content=description,
            confidence=confidence,
        )
        if self._store:
            self._store.record("cognition.uncertainty", confidence)
            self._store.record("cognition.confidence", confidence, tags={"type": "uncertainty"})
        return step

    def record_retry(self, attempt: int, reason: str, strategy: str = "") -> ThoughtStep:
        step = self._add_step(
            type_=ThoughtType.RETRY,
            content=f"Retry #{attempt}: {reason}",
            confidence=max(0.1, 1.0 - (attempt * 0.15)),
            metadata={"attempt": attempt, "reason": reason, "strategy": strategy},
        )
        if self._store:
            self._store.record("cognition.retry_attempt", float(attempt))
        return step

    def record_error(self, error: str, context: dict = None) -> ThoughtStep:
        step = self._add_step(
            type_=ThoughtType.ERROR,
            content=error,
            confidence=0.0,
            metadata={"error_context": context or {}},
        )
        if self._store:
            self._store.record("cognition.error", 1.0)
        return step

    def record_hallucination(self, description: str, severity: float = 0.5) -> ThoughtStep:
        step = self._add_step(
            type_=ThoughtType.HALLUCINATION,
            content=description,
            confidence=max(0, 1.0 - severity),
            metadata={"severity": severity},
        )
        if self._store:
            self._store.record("cognition.hallucination_severity", severity)
        return step

    def record_navigation(self, action: str, target: str) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.NAVIGATION,
            content=f"{action}: {target}",
            metadata={"action": action, "target": target},
        )

    def record_tool_selection(self, tool: str, rationale: str, alternatives: list = None) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.TOOL_SELECTION,
            content=f"Tool: {tool}",
            metadata={
                "tool": tool,
                "rationale": rationale,
                "alternatives": alternatives or [],
            },
        )

    def record_insight(self, insight: str, confidence: float = 0.8) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.INSIGHT,
            content=insight,
            confidence=confidence,
        )

    def record_reasoning(self, reasoning: str, confidence: float = 0.9) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.REASONING,
            content=reasoning,
            confidence=confidence,
        )

    def record_abandoned(self, approach: str, reason: str) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.ABANDONED,
            content=f"Abandoned: {approach} ({reason})",
            confidence=0.0,
            metadata={"approach": approach, "reason": reason},
        )

    def record_context_shift(self, from_context: str, to_context: str) -> ThoughtStep:
        return self._add_step(
            type_=ThoughtType.CONTEXT_SHIFT,
            content=f"Context shift: {from_context} -> {to_context}",
            metadata={"from": from_context, "to": to_context},
        )

    def _add_step(self, type_: ThoughtType, content: str,
                  branch: str = "", confidence: float = 1.0,
                  metadata: dict = None) -> Optional[ThoughtStep]:
        if not self._current_trace:
            return None

        step = ThoughtStep(
            type=type_,
            content=content,
            parent_id=self._step_stack[-1] if self._step_stack else None,
            branch=branch or "main",
            confidence=confidence,
            metadata=metadata or {},
        )
        self._current_trace.add_step(step)
        self._step_stack.append(step.id)
        self._step_start_times[step.id] = step.timestamp
        return step

    def finish_step(self, step_id: str = ""):
        if step_id:
            if step_id in self._step_stack:
                self._step_stack.remove(step_id)
                start = self._step_start_times.get(step_id, 0)
                for step in self._current_trace.steps:
                    if step.id == step_id:
                        step.duration_ms = (time.time() - start) * 1000
                        break
        elif self._step_stack:
            last = self._step_stack.pop()
            start = self._step_start_times.get(last, 0)
            for step in self._current_trace.steps:
                if step.id == last:
                    step.duration_ms = (time.time() - start) * 1000
                    break

    def finish_trace(self, status: str = "completed", metrics: dict = None):
        if self._current_trace:
            self._current_trace.finish(status, metrics)
            self._step_stack.clear()
            self._step_start_times.clear()
            self._current_trace = None

    def get_current_trace(self) -> Optional[CognitiveTrace]:
        return self._current_trace

    def get_trace(self, trace_id: str) -> Optional[CognitiveTrace]:
        return self._traces.get(trace_id)

    def export_trace(self, trace_id: str = "") -> Optional[dict]:
        trace = self._traces.get(trace_id) if trace_id else self._current_trace
        if trace:
            return trace.to_dict()
        return None

    def export_all(self) -> List[dict]:
        return [t.to_dict() for t in self._traces.values()]

    def clear(self):
        self._current_trace = None
        self._traces.clear()
        self._step_stack.clear()
        self._step_start_times.clear()
