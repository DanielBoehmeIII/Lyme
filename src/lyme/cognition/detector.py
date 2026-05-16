from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from .trace import CognitiveTrace, ThoughtStep, ThoughtType


@dataclass
class Anomaly:
    type: str = ""
    severity: float = 0.0
    description: str = ""
    location: str = ""
    evidence: List[str] = field(default_factory=list)
    steps_involved: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "location": self.location,
            "evidence": self.evidence,
            "steps_involved": self.steps_involved,
        }


class AnomalyDetector:
    def __init__(self):
        self.recursive_loop_threshold = 5
        self.panic_threshold = 3
        self.context_fragmentation_window = 10
        self.hallucination_confidence_threshold = 0.3

    def detect_all(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        anomalies.extend(self._detect_recursive_loops(trace))
        anomalies.extend(self._detect_panic_states(trace))
        anomalies.extend(self._detect_context_fragmentation(trace))
        anomalies.extend(self._detect_hallucination_onset(trace))
        anomalies.extend(self._detect_confidence_collapse(trace))
        anomalies.extend(self._detect_retry_explosion(trace))
        anomalies.extend(self._detect_decision_paralysis(trace))
        anomalies.extend(self._detect_branch_explosion(trace))
        anomalies.extend(self._detect_contradictory_reasoning(trace))
        anomalies.sort(key=lambda a: a.severity, reverse=True)
        return anomalies

    def _detect_recursive_loops(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        steps = trace.steps
        if len(steps) < 4:
            return anomalies

        patterns = defaultdict(list)
        for i in range(len(steps) - 3):
            for window in [3, 4, 5]:
                if i + window <= len(steps):
                    seq = tuple(
                        f"{steps[j].type}-{steps[j].content[:50]}"
                        for j in range(i, i + window)
                    )
                    patterns[seq].append(i)

        for seq, positions in patterns.items():
            if len(positions) >= 3:
                step_ids = [steps[p].id for p in positions[:5]]
                anomalies.append(Anomaly(
                    type="recursive_loop",
                    severity=min(1.0, len(positions) / 10),
                    description=f"Agent repeated same reasoning pattern {len(positions)} times",
                    location=f"steps {positions[0]}-{positions[-1]}",
                    evidence=[f"Pattern repeated at positions {p}" for p in positions[:5]],
                    steps_involved=step_ids,
                ))
                break

        return anomalies

    def _detect_panic_states(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        steps = trace.steps
        if len(steps) < self.panic_threshold:
            return anomalies

        consecutive_errors = 0
        panic_start = -1
        for i, step in enumerate(steps):
            if step.type in (ThoughtType.ERROR, ThoughtType.RETRY) and step.confidence < 0.3:
                if consecutive_errors == 0:
                    panic_start = i
                consecutive_errors += 1
                if consecutive_errors >= self.panic_threshold:
                    step_ids = [steps[j].id for j in range(panic_start, i + 1)]
                    anomalies.append(Anomaly(
                        type="panic_state",
                        severity=min(1.0, consecutive_errors / 8),
                        description=f"Agent entered panic state: {consecutive_errors} consecutive errors/retries",
                        location=f"steps {panic_start}-{i}",
                        evidence=[f"Step {j}: {steps[j].content[:100]}" for j in range(panic_start, i + 1)],
                        steps_involved=step_ids,
                    ))
                    break
            else:
                consecutive_errors = 0

        return anomalies

    def _detect_context_fragmentation(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        steps = trace.steps
        if len(steps) < self.context_fragmentation_window:
            return anomalies

        context_shifts = [s for s in steps if s.type == ThoughtType.CONTEXT_SHIFT]
        if len(context_shifts) > len(steps) * 0.3:
            step_ids = [s.id for s in context_shifts[:10]]
            anomalies.append(Anomaly(
                type="context_fragmentation",
                severity=min(1.0, len(context_shifts) / self.context_fragmentation_window),
                description=f"Excessive context switching: {len(context_shifts)} shifts in {len(steps)} steps",
                location="throughout trace",
                evidence=[f"Context shift: {s.content[:100]}" for s in context_shifts[:5]],
                steps_involved=step_ids,
            ))

        return anomalies

    def _detect_hallucination_onset(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        steps = trace.steps

        hallucination_markers = [
            "i think", "probably", "maybe", "must be", "assume",
            "not sure", "i believe", "it seems", "likely",
        ]

        hallucination_steps = []
        for step in steps:
            content_lower = step.content.lower()
            marker_count = sum(1 for m in hallucination_markers if m in content_lower)
            if marker_count >= 2 and step.confidence < self.hallucination_confidence_threshold:
                hallucination_steps.append(step)

        if hallucination_steps:
            step_ids = [s.id for s in hallucination_steps]
            anomalies.append(Anomaly(
                type="hallucination_onset",
                severity=min(1.0, len(hallucination_steps) / 5),
                description=f"Possible hallucination detected in {len(hallucination_steps)} steps",
                location=f"steps with low confidence + uncertainty markers",
                evidence=[s.content[:150] for s in hallucination_steps[:3]],
                steps_involved=step_ids,
            ))

        return anomalies

    def _detect_confidence_collapse(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        confidences = [s.confidence for s in trace.steps]
        if len(confidences) < 5:
            return anomalies

        window_size = 5
        for i in range(len(confidences) - window_size + 1):
            window = confidences[i:i + window_size]
            if all(c < 0.3 for c in window):
                step_ids = [trace.steps[i + j].id for j in range(window_size)]
                anomalies.append(Anomaly(
                    type="confidence_collapse",
                    severity=0.8,
                    description=f"Confidence collapsed below 0.3 for {window_size} consecutive steps",
                    location=f"steps {i}-{i + window_size - 1}",
                    evidence=[f"Confidence values: {window}"],
                    steps_involved=step_ids,
                ))
                break

        return anomalies

    def _detect_retry_explosion(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        retries = [s for s in trace.steps if s.type == ThoughtType.RETRY]

        if len(retries) >= self.recursive_loop_threshold:
            step_ids = [s.id for s in retries]
            anomalies.append(Anomaly(
                type="retry_explosion",
                severity=min(1.0, len(retries) / 10),
                description=f"Retry explosion: {len(retries)} retry attempts",
                location="throughout trace",
                evidence=[s.content[:100] for s in retries[:5]],
                steps_involved=step_ids,
            ))

        strategy_shifts = len(set(s.metadata.get("strategy", "") for s in retries))
        if len(retries) >= 4 and strategy_shifts >= 3:
            anomalies.append(Anomaly(
                type="retry_strategy_instability",
                severity=0.6,
                description=f"Frequent strategy changes across {len(retries)} retries",
                location="retry sequence",
                evidence=[f"Strategy: {s.metadata.get('strategy', 'unknown')}" for s in retries],
            ))

        return anomalies

    def _detect_decision_paralysis(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        decisions = trace.decisions
        if len(decisions) < 3:
            return anomalies

        consecutive_high_uncertainty = 0
        for d in decisions:
            if d.confidence < 0.5:
                consecutive_high_uncertainty += 1
                if consecutive_high_uncertainty >= 3:
                    anomalies.append(Anomaly(
                        type="decision_paralysis",
                        severity=0.7,
                        description=f"Multiple low-confidence decisions: {consecutive_high_uncertainty} in a row",
                        location=f"decisions with confidence < 0.5",
                        evidence=[
                            f"Decision: {d.question[:100]} (confidence: {d.confidence})"
                            for d in decisions[-3:]
                        ],
                        steps_involved=[d.id for d in decisions[-3:]],
                    ))
                    break
            else:
                consecutive_high_uncertainty = 0

        return anomalies

    def _detect_branch_explosion(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        branches = trace.branches
        if len(branches) <= 1:
            return anomalies

        if len(branches) >= 5 and max(branches.values()) <= 2:
            anomalies.append(Anomaly(
                type="branch_explosion",
                severity=0.5,
                description=f"Too many shallow branches: {len(branches)} branches, each < 3 steps",
                location="exploration pattern",
                evidence=[f"Branch '{b}': {c} steps" for b, c in branches.items()],
            ))

        return anomalies

    def _detect_contradictory_reasoning(self, trace: CognitiveTrace) -> List[Anomaly]:
        anomalies = []
        steps = trace.steps

        contradictions = [
            ("add", "remove"),
            ("create", "delete"),
            ("increase", "decrease"),
            ("enable", "disable"),
            ("start", "stop"),
        ]

        for a_word, b_word in contradictions:
            a_positions = [i for i, s in enumerate(steps) if a_word in s.content.lower()]
            b_positions = [i for i, s in enumerate(steps) if b_word in s.content.lower()]

            for a_pos in a_positions:
                for b_pos in b_positions:
                    if abs(a_pos - b_pos) <= 3 and a_pos != b_pos:
                        anomalies.append(Anomaly(
                            type="contradictory_reasoning",
                            severity=0.4,
                            description=f"Contradictory statements about '{a_word}' and '{b_word}' within 3 steps",
                            location=f"steps {a_pos}, {b_pos}",
                            evidence=[
                                f"Step {a_pos}: {steps[a_pos].content[:100]}",
                                f"Step {b_pos}: {steps[b_pos].content[:100]}",
                            ],
                            steps_involved=[steps[a_pos].id, steps[b_pos].id],
                        ))

        return anomalies
