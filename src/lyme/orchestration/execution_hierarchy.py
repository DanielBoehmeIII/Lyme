"""ExecutionHierarchy — layered decision-making with escalation paths."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class Level(str, Enum):
    L1_STRATEGIC = "l1_strategic"
    L2_TACTICAL = "l2_tactical"
    L3_OPERATIONAL = "l3_operational"
    L4_EXECUTION = "l4_execution"


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    DEFERRED = "deferred"


@dataclass
class Decision:
    id: str
    level: Level
    description: str
    outcome: Optional[DecisionOutcome] = None
    rationale: str = ""
    escalated_from: Optional[str] = None
    handled_by: str = ""
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "level": self.level.value,
            "description": self.description[:60],
            "outcome": self.outcome.value if self.outcome else "pending",
            "rationale": self.rationale[:80] if self.rationale else "",
            "handled_by": self.handled_by,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class HierarchyLevel:
    level: Level
    name: str
    handlers: List[Callable]
    escalation_threshold: float
    decisions: List[Decision] = field(default_factory=list)

    def can_handle(self, confidence: float) -> bool:
        return confidence >= self.escalation_threshold


class ExecutionHierarchy:
    def __init__(self):
        self._levels: Dict[Level, HierarchyLevel] = {
            Level.L4_EXECUTION: HierarchyLevel(
                level=Level.L4_EXECUTION, name="Execution Agents",
                handlers=[], escalation_threshold=0.9,
            ),
            Level.L3_OPERATIONAL: HierarchyLevel(
                level=Level.L3_OPERATIONAL, name="Operational Agents",
                handlers=[], escalation_threshold=0.7,
            ),
            Level.L2_TACTICAL: HierarchyLevel(
                level=Level.L2_TACTICAL, name="Tactic Agents",
                handlers=[], escalation_threshold=0.5,
            ),
            Level.L1_STRATEGIC: HierarchyLevel(
                level=Level.L1_STRATEGIC, name="Strategic Agents",
                handlers=[], escalation_threshold=0.0,
            ),
        }
        self._decisions: List[Decision] = []

    def register_handler(self, level: Level, handler: Callable) -> None:
        self._levels[level].handlers.append(handler)

    def decide(self, description: str, data: Any,
               start_level: Level = Level.L4_EXECUTION,
               decider_id: str = "") -> Decision:
        decision = Decision(
            id=f"dec-{len(self._decisions)}",
            level=start_level,
            description=description,
            handled_by=decider_id or start_level.value,
        )

        current_level = start_level
        levels_order = [Level.L4_EXECUTION, Level.L3_OPERATIONAL,
                       Level.L2_TACTICAL, Level.L1_STRATEGIC]
        start_idx = levels_order.index(start_level)

        for idx in range(start_idx, len(levels_order)):
            level_obj = self._levels[levels_order[idx]]

            handlers = level_obj.handlers
            if not handlers:
                confidence = 1.0 - (idx - start_idx) * 0.25
            else:
                confidence = 0.0
                for handler in handlers:
                    try:
                        result = handler(description, data)
                        if isinstance(result, (int, float)):
                            confidence = max(confidence, result)
                    except Exception:
                        confidence = max(confidence, 0.0)
                if not handlers:
                    confidence = 1.0 - (idx - start_idx) * 0.25

            can_escalate = idx < len(levels_order) - 1

            if confidence >= level_obj.escalation_threshold or not can_escalate:
                decision.outcome = DecisionOutcome.APPROVED
                decision.level = levels_order[idx]
                decision.handled_by = f"{level_obj.name}"
                decision.rationale = f"Handled at {levels_order[idx].value} with confidence {confidence:.2f}"
                decision.confidence = confidence
                decision.metadata["handling_level"] = levels_order[idx].value
                break
            else:
                if can_escalate:
                    decision.escalated_from = levels_order[idx].value

        if decision.outcome is None:
            decision.outcome = DecisionOutcome.ESCALATED
            decision.rationale = "Escalated through all levels without resolution"
            decision.confidence = 0.0

        self._decisions.append(decision)
        self._levels[decision.level].decisions.append(decision)
        return decision

    def report(self) -> Dict:
        level_counts: Dict[str, int] = {}
        outcome_counts: Dict[str, int] = {}
        for d in self._decisions:
            level_counts[d.level.value] = level_counts.get(d.level.value, 0) + 1
            if d.outcome:
                outcome_counts[d.outcome.value] = outcome_counts.get(d.outcome.value, 0) + 1

        return {
            "total_decisions": len(self._decisions),
            "by_level": level_counts,
            "by_outcome": outcome_counts,
            "levels": {
                lv.value: {
                    "name": level.name,
                    "escalation_threshold": level.escalation_threshold,
                    "handler_count": len(level.handlers),
                    "decisions_handled": len(level.decisions),
                }
                for lv, level in self._levels.items()
            },
        }

    def render_cli(self) -> str:
        report = self.report()
        lines = []
        lines.append("=" * 70)
        lines.append("  EXECUTION HIERARCHY")
        lines.append("=" * 70)
        lines.append(f"  Total Decisions: {report['total_decisions']}")
        lines.append("")
        lines.append("  Levels:")
        for lv_key, lv_data in sorted(report["levels"].items()):
            bar = "█" * min(lv_data["decisions_handled"], 20)
            lines.append(f"    {lv_key}: {lv_data['decisions_handled']} decisions {bar}")
            lines.append(f"      threshold={lv_data['escalation_threshold']}, "
                         f"handlers={lv_data['handler_count']}")
        lines.append("")
        lines.append("  By Outcome:")
        for outcome, count in sorted(report["by_outcome"].items(), key=lambda x: -x[1]):
            lines.append(f"    {outcome}: {count}")
        lines.append("=" * 70)
        return "\n".join(lines)
