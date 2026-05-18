"""EditHarmonizer — merges concurrent edits from multiple agents."""
from __future__ import annotations
import difflib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .session import EditOperation
from .conflict import ConflictDetector, EditConflict


class MergeStrategy(Enum):
    HUNK = "hunk"
    LINE = "line"
    AGENT_PREFERENCE = "agent_preference"
    LATEST_WINS = "latest_wins"


@dataclass
class HarmonizationResult:
    merged_content: str = ""
    conflicts: List[EditConflict] = field(default_factory=list)
    strategy_used: MergeStrategy = MergeStrategy.LATEST_WINS
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflicts": len(self.conflicts),
            "strategy": self.strategy_used.value,
            "success": self.success,
        }


class EditHarmonizer:
    def __init__(self, strategy: MergeStrategy = MergeStrategy.HUNK):
        self.strategy = strategy
        self.detector = ConflictDetector()

    def harmonize(self, operations: List[EditOperation]) -> HarmonizationResult:
        if not operations:
            return HarmonizationResult(success=True)

        result = HarmonizationResult(strategy_used=self.strategy)

        # Check for conflicts
        all_conflicts: List[EditConflict] = []
        for i, op in enumerate(operations):
            earlier = operations[:i]
            conflicts = self.detector.detect(op, earlier)
            all_conflicts.extend(conflicts)

        if all_conflicts and self.strategy == MergeStrategy.ABORT:
            result.conflicts = all_conflicts
            result.success = False
            return result

        result.conflicts = all_conflicts

        # Merge by strategy
        if self.strategy == MergeStrategy.LATEST_WINS:
            ops_by_file: Dict[str, List[EditOperation]] = {}
            for op in operations:
                if op.file_path not in ops_by_file:
                    ops_by_file[op.file_path] = []
                ops_by_file[op.file_path].append(op)

            for fp, ops in ops_by_file.items():
                latest = max(ops, key=lambda o: o.timestamp)
                if latest.has_changes:
                    result.merged_content = latest.new_content

        elif self.strategy == MergeStrategy.HUNK:
            ops_by_file: Dict[str, List[EditOperation]] = {}
            for op in operations:
                if op.file_path not in ops_by_file:
                    ops_by_file[op.file_path] = []
                ops_by_file[op.file_path].append(op)

            for fp, ops in ops_by_file.items():
                base = ops[0].original_content if ops else ""
                for op in ops:
                    if op.has_changes:
                        base = self._merge_hunks(base, op.new_content)
                result.merged_content = base

        return result

    def _merge_hunks(self, a: str, b: str) -> str:
        diff = list(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True)))
        if not diff:
            return a
        return b  # Simple: take latest for now
