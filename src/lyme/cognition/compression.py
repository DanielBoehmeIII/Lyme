from typing import List, Dict, Any, Optional
from .trace import CognitiveTrace, ThoughtStep, ThoughtType
import json


class TraceCompressor:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def compress(self, trace: CognitiveTrace) -> CognitiveTrace:
        compressed = self._deduplicate_reasoning(trace)
        compressed = self._merge_consecutive(compressed)
        compressed = self._remove_low_value_steps(compressed)
        compressed.steps = self._summarize_branches(compressed.steps)
        return compressed

    def _deduplicate_reasoning(self, trace: CognitiveTrace) -> CognitiveTrace:
        seen = set()
        deduped = []
        for step in trace.steps:
            normalized = self._normalize(step.content)
            if normalized not in seen:
                seen.add(normalized)
                deduped.append(step)
            else:
                candidates = [s for s in deduped if self._normalize(s.content) == normalized]
                if candidates:
                    candidates[-1].metadata["duplicates"] = \
                        candidates[-1].metadata.get("duplicates", 0) + 1
        trace.steps = deduped
        return trace

    def _merge_consecutive(self, trace: CognitiveTrace) -> CognitiveTrace:
        if len(trace.steps) < 2:
            return trace

        merged = [trace.steps[0]]
        for step in trace.steps[1:]:
            prev = merged[-1]
            if (prev.type == step.type == ThoughtType.REASONING and
                    self._content_similarity(prev.content, step.content) > self.similarity_threshold):
                prev.content = f"{prev.content}\n---\n{step.content}"
                prev.metadata["merged_count"] = prev.metadata.get("merged_count", 1) + 1
            else:
                merged.append(step)

        trace.steps = merged
        return trace

    def _remove_low_value_steps(self, trace: CognitiveTrace) -> CognitiveTrace:
        trace.steps = [
            s for s in trace.steps
            if not (s.type == ThoughtType.STATE_CHECK and s.confidence > 0.95)
        ]
        return trace

    def _summarize_branches(self, steps: List[ThoughtStep]) -> List[ThoughtStep]:
        branch_groups: Dict[str, List[ThoughtStep]] = {}
        main_steps = []

        for step in steps:
            if step.branch == "main":
                main_steps.append(step)
            else:
                branch_groups.setdefault(step.branch, []).append(step)

        for branch, branch_steps in branch_groups.items():
            if len(branch_steps) > 3:
                summary = (
                    f"[Compressed] Branch '{branch}': {len(branch_steps)} steps, "
                    f"types: {', '.join(set(s.type for s in branch_steps))}"
                )
                first = branch_steps[0]
                main_steps.append(ThoughtStep(
                    type=ThoughtType.SUMMARY if hasattr(ThoughtType, 'SUMMARY') else ThoughtType.INSIGHT,
                    content=summary,
                    timestamp=first.timestamp,
                    branch=branch,
                    metadata={"compressed": True, "original_count": len(branch_steps)},
                ))
            else:
                main_steps.extend(branch_steps)

        return sorted(main_steps, key=lambda s: s.timestamp)

    def _normalize(self, text: str) -> str:
        return " ".join(text.lower().split()).strip()

    def _content_similarity(self, a: str, b: str) -> float:
        set_a = set(self._normalize(a).split())
        set_b = set(self._normalize(b).split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    def compression_ratio(self, original: CognitiveTrace, compressed: CognitiveTrace) -> float:
        orig_size = len(json.dumps(original.to_dict()))
        comp_size = len(json.dumps(compressed.to_dict()))
        return 1.0 - (comp_size / orig_size) if orig_size > 0 else 0.0
