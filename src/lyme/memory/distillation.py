import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from collections import defaultdict

from .store import MemoryStore, MemoryEntry


@dataclass
class ProceduralMemory:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trigger_conditions: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    expected_outcome: str = ""
    confidence: float = 0.5
    success_rate: float = 1.0
    usage_count: int = 0
    source_traces: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trigger_conditions": self.trigger_conditions,
            "steps": self.steps,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "source_traces": self.source_traces,
            "created_at": self.created_at,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProceduralMemory":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:16]),
            trigger_conditions=data.get("trigger_conditions", []),
            steps=data.get("steps", []),
            expected_outcome=data.get("expected_outcome", ""),
            confidence=data.get("confidence", 0.5),
            success_rate=data.get("success_rate", 1.0),
            usage_count=data.get("usage_count", 0),
            source_traces=data.get("source_traces", []),
            created_at=data.get("created_at", time.time()),
            last_used=data.get("last_used", time.time()),
        )


PATTERN_TYPES = {"success", "failure", "retry", "exploration", "repetition"}


class MemoryDistillationLoop:
    def __init__(self, store: Optional[MemoryStore] = None, min_confidence: float = 0.3):
        self.store = store or MemoryStore()
        self._procedural: dict[str, ProceduralMemory] = {}
        self._trace_cache: list = []
        self.min_confidence = min_confidence
        self._pattern_counts: dict = defaultdict(int)
        self._failure_patterns: dict = defaultdict(int)

    def distill_from_trace(self, trace_data: dict):
        trace_id = trace_data.get("trace_id", uuid.uuid4().hex[:16])
        self._trace_cache.append(trace_data)

        steps = trace_data.get("steps", [])
        decisions = trace_data.get("decisions", [])
        summary = trace_data.get("summary", {})

        for pattern_type in PATTERN_TYPES:
            patterns = self.extract_pattern(trace_data, pattern_type)
            for pat in patterns:
                key = (pattern_type, str(pat.get("signature", "")))
                self._pattern_counts[key] += 1

        if summary.get("status") == "completed" or summary.get("success_rate", 0) > 0.5:
            procedural = self._build_procedural_from_success(trace_data)
            if procedural:
                existing = self._procedural.get(procedural.id)
                if existing:
                    existing.usage_count += 1
                    existing.confidence = min(1.0, existing.confidence + 0.05)
                    if existing.id not in self._procedural:
                        self._procedural[existing.id] = existing
                else:
                    self._procedural[procedural.id] = procedural
                self._store_procedural(procedural)

        failures = self._extract_failure_patterns(trace_data)
        for fail_sig, count in failures.items():
            self._failure_patterns[fail_sig] += count

        self._compress_redundant()

    def extract_pattern(self, trace_data: dict, pattern_type: str) -> List[dict]:
        steps = trace_data.get("steps", [])
        patterns: List[dict] = []

        if pattern_type == "success":
            successful_steps = [s for s in steps if s.get("confidence", 0) > 0.7]
            if successful_steps:
                signatures = [s.get("content", "")[:60] for s in successful_steps[:3]]
                patterns.append({
                    "type": "success",
                    "signature": "|".join(signatures),
                    "step_count": len(successful_steps),
                    "avg_confidence": sum(s.get("confidence", 0) for s in successful_steps) / len(successful_steps),
                })

        elif pattern_type == "failure":
            failed_steps = [
                s for s in steps
                if s.get("type") in ("error", "retry") or s.get("confidence", 1) < 0.3
            ]
            if failed_steps:
                patterns.append({
                    "type": "failure",
                    "signature": failed_steps[0].get("content", "")[:80],
                    "count": len(failed_steps),
                })

        elif pattern_type == "retry":
            retry_steps = [s for s in steps if s.get("type") == "retry"]
            if retry_steps:
                patterns.append({
                    "type": "retry",
                    "signature": f"retry_count={len(retry_steps)}",
                    "count": len(retry_steps),
                })

        elif pattern_type == "exploration":
            branches = trace_data.get("branches", {})
            if len(branches) > 1:
                patterns.append({
                    "type": "exploration",
                    "signature": f"branches={list(branches.keys())}",
                    "branch_count": len(branches),
                })

        elif pattern_type == "repetition":
            contents = [s.get("content", "") for s in steps]
            seen: set = set()
            repeats = 0
            for c in contents:
                sig = c[:80]
                if sig in seen:
                    repeats += 1
                seen.add(sig)
            if repeats:
                patterns.append({
                    "type": "repetition",
                    "signature": f"repeated_steps={repeats}",
                    "count": repeats,
                })

        return patterns

    def get_relevant_memory(self, task_description: str, repo_context: str = "") -> List[ProceduralMemory]:
        combined = f"{task_description} {repo_context}"
        scored: list[tuple[float, ProceduralMemory]] = []

        for pm in self._procedural.values():
            if pm.confidence < self.min_confidence:
                continue
            score = self._match_score(combined, pm)
            scored.append((score, pm))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [pm for _, pm in scored[:5]]

    def apply_memory(self, task_context: dict) -> Optional[dict]:
        task_desc = task_context.get("description", "")
        repo_ctx = task_context.get("repo_context", "")
        relevant = self.get_relevant_memory(task_desc, repo_ctx)
        if not relevant:
            return None

        best = relevant[0]
        best.usage_count += 1
        best.last_used = time.time()

        return {
            "procedural_id": best.id,
            "trigger_conditions": best.trigger_conditions,
            "steps": best.steps,
            "expected_outcome": best.expected_outcome,
            "confidence": best.confidence,
            "success_rate": best.success_rate,
        }

    def update_confidence(self, procedural_id: str, succeeded: bool):
        pm = self._procedural.get(procedural_id)
        if not pm:
            return
        pm.usage_count += 1
        alpha = 0.3
        if succeeded:
            pm.success_rate = pm.success_rate * (1 - alpha) + 1.0 * alpha
            pm.confidence = min(1.0, pm.confidence + 0.1)
        else:
            pm.success_rate = pm.success_rate * (1 - alpha) + 0.0 * alpha
            pm.confidence = max(0.0, pm.confidence * 0.8)
        pm.last_used = time.time()

    def prune_unused(self, max_age_days: int = 60, min_usage: int = 1):
        now = time.time()
        cutoff = now - max_age_days * 86400
        to_remove: list[str] = []
        for pid, pm in self._procedural.items():
            if pm.last_used < cutoff and pm.usage_count < min_usage:
                to_remove.append(pid)
        for pid in to_remove:
            del self._procedural[pid]

    def get_statistics(self) -> dict:
        if not self._procedural:
            return {"procedural_count": 0}
        confidences = [pm.confidence for pm in self._procedural.values()]
        return {
            "procedural_count": len(self._procedural),
            "avg_confidence": sum(confidences) / len(confidences),
            "max_confidence": max(confidences),
            "pattern_types_seen": dict(self._pattern_counts),
            "failure_patterns": dict(self._failure_patterns),
            "trace_cache_size": len(self._trace_cache),
        }

    def _build_procedural_from_success(self, trace_data: dict) -> Optional[ProceduralMemory]:
        steps = trace_data.get("steps", [])
        summary = trace_data.get("summary", {})
        if not steps:
            return None

        decision_keywords = [d.get("chosen", "") for d in trace_data.get("decisions", [])]
        action_descriptions = [
            s.get("content", "")[:120] for s in steps
            if s.get("type") not in ("error", "uncertainty")
        ]
        if not action_descriptions:
            return None

        success_rate = summary.get("success_rate", 1.0)
        if isinstance(success_rate, dict):
            success_rate = success_rate.get("overall", 0.5)

        return ProceduralMemory(
            trigger_conditions=decision_keywords[:5],
            steps=action_descriptions[:10],
            expected_outcome=summary.get("status", "completed"),
            confidence=min(0.9, 0.3 + 0.1 * len(action_descriptions)),
            success_rate=float(success_rate) if isinstance(success_rate, (int, float)) else 0.5,
            source_traces=[trace_data.get("trace_id", "")],
        )

    def _extract_failure_patterns(self, trace_data: dict) -> Dict[str, int]:
        summary = trace_data.get("summary", {})
        failures: Dict[str, int] = {}
        error_count = summary.get("error_count", 0)
        if error_count and int(error_count) > 0:
            failures["generic_error"] = int(error_count)
        abandoned = summary.get("abandoned_approaches", 0)
        if abandoned:
            failures["abandoned_approach"] = int(abandoned)
        return failures

    def _compress_redundant(self):
        ids = list(self._procedural.keys())
        merged: set = set()
        for i in range(len(ids)):
            if ids[i] in merged:
                continue
            for j in range(i + 1, len(ids)):
                if ids[j] in merged:
                    continue
                a = self._procedural[ids[i]]
                b = self._procedural[ids[j]]
                if self._are_similar(a, b):
                    a.usage_count += b.usage_count
                    a.confidence = max(a.confidence, b.confidence)
                    a.success_rate = (a.success_rate + b.success_rate) / 2
                    a.source_traces.extend(b.source_traces)
                    merged.add(ids[j])

        for pid in merged:
            del self._procedural[pid]

    def _are_similar(self, a: ProceduralMemory, b: ProceduralMemory) -> bool:
        a_sigs = set(a.trigger_conditions)
        b_sigs = set(b.trigger_conditions)
        if not a_sigs or not b_sigs:
            return False
        overlap = len(a_sigs & b_sigs)
        return overlap / min(len(a_sigs), len(b_sigs)) > 0.5

    def _match_score(self, text: str, pm: ProceduralMemory) -> float:
        score = 0.0
        text_lower = text.lower()
        for cond in pm.trigger_conditions:
            if cond.lower() in text_lower:
                score += 0.3
        if pm.expected_outcome.lower() in text_lower:
            score += 0.2
        score *= pm.confidence
        score *= min(1.0, pm.success_rate)
        return score

    def _store_procedural(self, pm: ProceduralMemory):
        entry = MemoryEntry(
            type="procedural",
            content=json.dumps(pm.to_dict()),
            source_task=pm.trigger_conditions[0] if pm.trigger_conditions else "distillation",
            importance_score=pm.confidence,
            tags=["procedural"] + pm.trigger_conditions[:3],
        )
        self.store.save(entry)

    def list_procedural(self) -> List[ProceduralMemory]:
        return list(self._procedural.values())


import json
