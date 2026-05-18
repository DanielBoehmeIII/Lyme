"""TaskDecompositionMemory — stores and retrieves effective task decompositions."""
from __future__ import annotations
import time
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from pathlib import Path


class DecompositionOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SubtaskRecord:
    name: str
    type: str
    difficulty: float
    result: str
    verification_passed: bool
    duration_sec: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "difficulty": self.difficulty,
            "result": self.result[:80],
            "verification_passed": self.verification_passed,
            "duration_sec": round(self.duration_sec, 1),
        }


@dataclass
class DecompositionMemory:
    id: str
    task_description: str
    task_type: str
    subtask_count: int
    ordering: List[str]
    subtasks: List[SubtaskRecord]
    outcome: DecompositionOutcome
    total_duration_sec: float
    confidence: float
    repo_language: str
    created_at: float

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_description": self.task_description[:80],
            "task_type": self.task_type,
            "subtask_count": self.subtask_count,
            "ordering": self.ordering,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "outcome": self.outcome.value,
            "total_duration_sec": round(self.total_duration_sec, 1),
            "confidence": round(self.confidence, 3),
            "repo_language": self.repo_language,
        }

    @property
    def success_rate(self) -> float:
        if not self.subtasks:
            return 0.0
        return sum(1 for s in self.subtasks if s.verification_passed) / len(self.subtasks)


@dataclass
class DecompositionTemplate:
    task_type: str
    patterns: List[str]
    subtask_types: List[str]
    average_difficulty: float
    success_rate: float
    total_uses: int
    average_subtask_count: float

    def to_dict(self) -> Dict:
        return {
            "task_type": self.task_type,
            "patterns": self.patterns[:5],
            "subtask_types": self.subtask_types,
            "success_rate": round(self.success_rate, 3),
            "total_uses": self.total_uses,
            "average_subtask_count": round(self.average_subtask_count, 1),
        }


@dataclass
class DecompositionMemoryReport:
    total_memories: int
    by_type: Dict[str, int]
    top_templates: List[DecompositionTemplate]
    overall_success_rate: float
    recommendations: List[str]
    insights: List[str]

    def to_dict(self) -> Dict:
        return {
            "total_memories": self.total_memories,
            "by_type": self.by_type,
            "top_templates": [t.to_dict() for t in self.top_templates[:5]],
            "overall_success_rate": round(self.overall_success_rate, 3),
            "recommendations": self.recommendations,
            "insights": self.insights,
        }

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  TASK DECOMPOSITION MEMORY REPORT")
        lines.append("=" * 70)
        lines.append(f"  Total Decompositions: {self.total_memories}")
        lines.append(f"  Overall Success Rate: {self.overall_success_rate:.0%}")
        lines.append(f"")
        lines.append(f"  By Type:")
        for t, c in sorted(self.by_type.items(), key=lambda x: -x[1]):
            pct = c / max(self.total_memories, 1) * 100
            bar = "█" * int(pct / 5)
            lines.append(f"    {t}: {c} ({pct:.0f}%) {bar}")
        if self.top_templates:
            lines.append(f"")
            lines.append(f"  Top Templates:")
            for t in self.top_templates[:3]:
                lines.append(f"    {t.task_type}: {t.success_rate:.0%} success "
                             f"({t.total_uses} uses, ~{t.average_subtask_count:.0f} subtasks)")
        if self.insights:
            lines.append("-" * 70)
            lines.append("  INSIGHTS:")
            for i in self.insights:
                lines.append(f"    • {i}")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class TaskDecompositionMemory:
    def __init__(self, storage_path: Optional[str] = None):
        self._memories: List[DecompositionMemory] = []
        self._storage_path = storage_path
        self._load()

    def store(self, task_description: str, task_type: str,
              subtask_names: List[str], subtask_types: List[str],
              difficulties: List[float], outcomes: List[bool],
              durations: List[float], overall_outcome: DecompositionOutcome,
              total_duration: float, confidence: float,
              repo_language: str = "") -> str:
        subtasks = [
            SubtaskRecord(
                name=n, type=t, difficulty=d, result="",
                verification_passed=o, duration_sec=du,
            )
            for n, t, d, o, du in zip(subtask_names, subtask_types,
                                       difficulties, outcomes, durations)
        ]
        mem_id = str(uuid.uuid4())[:8]
        memory = DecompositionMemory(
            id=mem_id,
            task_description=task_description,
            task_type=task_type,
            subtask_count=len(subtasks),
            ordering=list(range(len(subtasks))),
            subtasks=subtasks,
            outcome=overall_outcome,
            total_duration_sec=total_duration,
            confidence=confidence,
            repo_language=repo_language,
            created_at=time.time(),
        )
        self._memories.append(memory)
        self._save()
        return mem_id

    def retrieve_similar(self, task_description: str, top_k: int = 3) -> List[DecompositionMemory]:
        desc_lower = task_description.lower()
        keywords = set(desc_lower.split())

        scored = []
        for mem in self._memories:
            mem_keywords = set(mem.task_description.lower().split())
            overlap = len(keywords & mem_keywords)
            if overlap > 0:
                score = overlap / max(len(keywords | mem_keywords), 1)
                if mem.outcome == DecompositionOutcome.SUCCESS:
                    score *= 1.5
                scored.append((score, mem))

        scored.sort(key=lambda x: -x[0])
        return [mem for _, mem in scored[:top_k]]

    def get_template(self, task_type: str) -> Optional[DecompositionTemplate]:
        typed = [m for m in self._memories if m.task_type == task_type]
        if not typed:
            return None

        successful = [m for m in typed if m.outcome == DecompositionOutcome.SUCCESS]
        success_rate = len(successful) / max(len(typed), 1)

        all_subtask_types: List[str] = []
        for m in typed:
            for s in m.subtasks:
                all_subtask_types.append(s.type)

        return DecompositionTemplate(
            task_type=task_type,
            patterns=[m.task_description[:60] for m in typed[:3]],
            subtask_types=list(set(all_subtask_types)),
            average_difficulty=sum(
                sum(s.difficulty for s in m.subtasks) / max(len(m.subtasks), 1)
                for m in typed
            ) / max(len(typed), 1),
            success_rate=success_rate,
            total_uses=len(typed),
            average_subtask_count=sum(m.subtask_count for m in typed) / max(len(typed), 1),
        )

    def get_pattern_insights(self) -> List[str]:
        insights: List[str] = []
        if not self._memories:
            return ["No decomposition data yet"]

        successful = [m for m in self._memories if m.outcome == DecompositionOutcome.SUCCESS]
        overall_sr = len(successful) / max(len(self._memories), 1)
        insights.append(f"Overall success rate: {overall_sr:.0%}")

        by_type: Dict[str, List[DecompositionMemory]] = {}
        for m in self._memories:
            if m.task_type not in by_type:
                by_type[m.task_type] = []
            by_type[m.task_type].append(m)

        best_type = max(by_type, key=lambda t: sum(
            1 for m in by_type[t] if m.outcome == DecompositionOutcome.SUCCESS
        ) / max(len(by_type[t]), 1)) if by_type else None
        if best_type:
            best_sr = sum(1 for m in by_type[best_type]
                          if m.outcome == DecompositionOutcome.SUCCESS) / max(len(by_type[best_type]), 1)
            insights.append(f"Best task type: '{best_type}' ({best_sr:.0%} success)")

        avg_subtasks = sum(m.subtask_count for m in self._memories) / max(len(self._memories), 1)
        insights.append(f"Average {avg_subtasks:.1f} subtasks per decomposition")

        best_count = 0
        for m in successful:
            passed = sum(1 for s in m.subtasks if s.verification_passed)
            if passed == m.subtask_count:
                best_count += 1
        perfect_rate = best_count / max(len(successful), 1)
        insights.append(f"Perfect decomposition rate: {perfect_rate:.0%} "
                        f"(all subtasks verified successfully)")

        return insights

    def report(self) -> DecompositionMemoryReport:
        if not self._memories:
            return DecompositionMemoryReport(
                total_memories=0, by_type={}, top_templates=[],
                overall_success_rate=0.0,
                recommendations=["Collect decomposition data to generate insights"],
                insights=["No data yet"],
            )

        by_type: Dict[str, int] = {}
        for m in self._memories:
            by_type[m.task_type] = by_type.get(m.task_type, 0) + 1

        successful = sum(1 for m in self._memories if m.outcome == DecompositionOutcome.SUCCESS)
        overall_sr = successful / max(len(self._memories), 1)

        templates = []
        for task_type in by_type:
            tmpl = self.get_template(task_type)
            if tmpl:
                templates.append(tmpl)
        templates.sort(key=lambda t: -t.success_rate)

        recommendations: List[str] = []
        if overall_sr < 0.5:
            recommendations.append("Low decomposition success rate — consider reducing subtask count")
        for t in templates[:3]:
            if t.success_rate > 0.8 and t.total_uses > 3:
                recommendations.append(f"'{t.task_type}' decompositions are reliable "
                                       f"({t.success_rate:.0%} in {t.total_uses} uses)")
        low_sr = [t for t in templates if t.total_uses > 2 and t.success_rate < 0.4]
        for t in low_sr:
            recommendations.append(f"'{t.task_type}' decompositions need improvement "
                                   f"({t.success_rate:.0%}) — try fewer subtasks")
        if not recommendations:
            recommendations.append("All decomposition templates performing well")

        return DecompositionMemoryReport(
            total_memories=len(self._memories),
            by_type=by_type,
            top_templates=templates,
            overall_success_rate=overall_sr,
            recommendations=recommendations,
            insights=self.get_pattern_insights(),
        )

    def suggest_decomposition(self, task_description: str) -> Optional[List[str]]:
        similar = self.retrieve_similar(task_description, top_k=1)
        if not similar:
            return None
        best = similar[0]
        if best.outcome != DecompositionOutcome.SUCCESS:
            return None
        return best.ordering

    def _save(self) -> None:
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [m.to_dict() for m in self._memories]
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
                subtasks = [SubtaskRecord(**s) for s in d.get("subtasks", [])]
                self._memories.append(DecompositionMemory(
                    id=d["id"],
                    task_description=d["task_description"],
                    task_type=d.get("task_type", "unknown"),
                    subtask_count=d.get("subtask_count", len(subtasks)),
                    ordering=d.get("ordering", []),
                    subtasks=subtasks,
                    outcome=DecompositionOutcome(d.get("outcome", "failed")),
                    total_duration_sec=d.get("total_duration_sec", 0.0),
                    confidence=d.get("confidence", 0.0),
                    repo_language=d.get("repo_language", ""),
                    created_at=d.get("created_at", 0.0),
                ))
        except (json.JSONDecodeError, KeyError):
            pass
