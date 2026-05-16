from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import statistics
from .trace import CognitiveTrace, ThoughtStep, ThoughtType, DecisionPoint


@dataclass
class ThoughtCluster:
    label: str = ""
    steps: List[ThoughtStep] = field(default_factory=list)
    count: int = 0
    dominant_type: str = ""
    avg_confidence: float = 0.0
    duration_ms: float = 0.0
    themes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "count": self.count,
            "dominant_type": self.dominant_type,
            "avg_confidence": self.avg_confidence,
            "duration_ms": self.duration_ms,
            "themes": self.themes,
        }


class ThoughtAnalyzer:
    def __init__(self):
        self._clusters: List[ThoughtCluster] = []

    def analyze(self, trace: CognitiveTrace) -> dict:
        return {
            "summary": self._summarize(trace),
            "confidence_analysis": self._analyze_confidence(trace),
            "decision_analysis": self._analyze_decisions(trace),
            "exploration_analysis": self._analyze_exploration(trace),
            "pattern_analysis": self._analyze_patterns(trace),
            "cluster_analysis": self._cluster_thoughts(trace),
            "branch_analysis": self._analyze_branches(trace),
        }

    def _summarize(self, trace: CognitiveTrace) -> dict:
        type_counts = Counter(s.type for s in trace.steps)
        return {
            "total_steps": len(trace.steps),
            "total_decisions": len(trace.decisions),
            "type_distribution": dict(type_counts.most_common()),
            "branches_explored": len(trace.branches),
            "total_duration_ms": trace.summary.get("duration_ms", 0),
        }

    def _analyze_confidence(self, trace: CognitiveTrace) -> dict:
        confidences = [s.confidence for s in trace.steps]
        if not confidences:
            return {"avg": 0, "min": 0, "max": 0, "volatility": 0}

        avg = statistics.mean(confidences)
        volatility = statistics.stdev(confidences) if len(confidences) > 1 else 0

        return {
            "avg": avg,
            "min": min(confidences),
            "max": max(confidences),
            "volatility": volatility,
            "low_confidence_count": sum(1 for c in confidences if c < 0.5),
            "high_confidence_count": sum(1 for c in confidences if c > 0.9),
        }

    def _analyze_decisions(self, trace: CognitiveTrace) -> dict:
        if not trace.decisions:
            return {"total": 0}

        outcomes = Counter(d.outcome for d in trace.decisions)
        return {
            "total": len(trace.decisions),
            "outcomes": dict(outcomes),
            "avg_confidence": statistics.mean(d.confidence for d in trace.decisions),
            "unresolved": sum(1 for d in trace.decisions if d.outcome == "pending"),
            "with_alternatives": sum(1 for d in trace.decisions if d.alternatives_explored > 0),
        }

    def _analyze_exploration(self, trace: CognitiveTrace) -> dict:
        explorations = [s for s in trace.steps if s.type == ThoughtType.EXPLORATION]
        abandoned = [s for s in trace.steps if s.type == ThoughtType.ABANDONED]

        return {
            "exploration_count": len(explorations),
            "abandoned_count": len(abandoned),
            "abandonment_rate": len(abandoned) / len(trace.steps) if trace.steps else 0,
        }

    def _analyze_patterns(self, trace: CognitiveTrace) -> dict:
        patterns = []
        steps = trace.steps

        for i in range(len(steps) - 2):
            window = [steps[i].type, steps[i + 1].type, steps[i + 2].type]
            if window == [ThoughtType.ERROR, ThoughtType.RETRY, ThoughtType.ERROR]:
                patterns.append("error_retry_loop")
            elif window == [ThoughtType.EXPLORATION, ThoughtType.ABANDONED, ThoughtType.EXPLORATION]:
                patterns.append("exploration_instability")
            elif window == [ThoughtType.UNCERTAINTY, ThoughtType.DECISION, ThoughtType.UNCERTAINTY]:
                patterns.append("decision_paralysis")

        pattern_counts = Counter(patterns)
        return dict(pattern_counts.most_common())

    def _cluster_thoughts(self, trace: CognitiveTrace) -> List[dict]:
        if not trace.steps:
            return []

        type_groups = defaultdict(list)
        for step in trace.steps:
            type_groups[step.type].append(step)

        clusters = []
        for step_type, steps in type_groups.items():
            cluster = ThoughtCluster(
                label=f"{step_type}_cluster",
                steps=steps,
                count=len(steps),
                dominant_type=step_type,
                avg_confidence=statistics.mean(s.confidence for s in steps),
                duration_ms=sum(s.duration_ms or 0 for s in steps),
            )

            words = []
            for s in steps:
                words.extend(s.content.lower().split())
            word_counts = Counter(words)
            cluster.themes = [w for w, c in word_counts.most_common(5) if len(w) > 3]
            clusters.append(cluster)

        clusters.sort(key=lambda c: c.count, reverse=True)
        return [c.to_dict() for c in clusters]

    def _analyze_branches(self, trace: CognitiveTrace) -> dict:
        branch_info = {}
        for branch, count in trace.branches.items():
            branch_steps = [s for s in trace.steps if s.branch == branch]
            branch_info[branch] = {
                "step_count": count,
                "duration_ms": sum(s.duration_ms or 0 for s in branch_steps),
                "types": list(set(s.type for s in branch_steps)),
            }
        return branch_info
