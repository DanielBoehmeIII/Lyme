"""Week 85 — Toolformer-Style Data Generation.

Generate training data for tool use from Lyme Audit traces.
Examples show when to: search, read, run tests, inspect git, stop, ask, reject.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import random


@dataclass
class ToolExample:
    trace_id: str = ""
    situation: str = ""
    action_taken: str = ""
    action_correct: bool = False
    context_before: Dict = field(default_factory=dict)
    context_after: Dict = field(default_factory=dict)
    quality_score: float = 0.0
    difficulty: str = "medium"
    source: str = ""  # audit_trace, synthetic, curated

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "situation": self.situation[:200],
            "action_taken": self.action_taken,
            "action_correct": self.action_correct,
            "quality_score": self.quality_score,
            "difficulty": self.difficulty,
            "source": self.source,
        }


@dataclass
class DatasetSchema:
    version: str = "1.0"
    total_examples: int = 0
    train_count: int = 0
    val_count: int = 0
    by_action: Dict[str, int] = field(default_factory=dict)
    by_difficulty: Dict[str, int] = field(default_factory=dict)
    quality_filters: List[str] = field(default_factory=list)
    examples: List[ToolExample] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "total_examples": self.total_examples,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "by_action": self.by_action,
            "by_difficulty": self.by_difficulty,
            "quality_filters": self.quality_filters,
        }

    def to_markdown(self) -> str:
        lines = ["# Tool-Use Dataset", ""]
        lines.append(f"**Version**: {self.version}")
        lines.append(f"**Total**: {self.total_examples}")
        lines.append(f"**Train**: {self.train_count} | **Val**: {self.val_count}")
        lines.append("")
        lines.append("## By Action")
        for action, count in sorted(self.by_action.items(), key=lambda x: -x[1]):
            lines.append(f"- {action}: {count}")
        lines.append("")
        lines.append("## By Difficulty")
        for diff, count in sorted(self.by_difficulty.items(), key=lambda x: -x[1]):
            lines.append(f"- {diff}: {count}")
        lines.append("")
        if self.quality_filters:
            lines.append("## Quality Filters")
            for f in self.quality_filters:
                lines.append(f"- {f}")
        return "\n".join(lines)


class DataGenerator:
    """Generates tool-use training data from Lyme Audit traces."""

    ACTION_TYPES = [
        "search", "read", "run_test", "inspect_git",
        "stop", "ask_user", "reject_claim",
    ]

    QUALITY_FILTERS = [
        "Minimum 3 tool calls in trace",
        "Action must be clearly identifiable",
        "No ambiguous or mixed intents",
        "Trace duration < 120 seconds",
        "Not an infinite loop",
        "Outcome must be known (success/failure)",
    ]

    def __init__(self, val_split: float = 0.2):
        self.val_split = val_split
        self.examples: List[ToolExample] = []
        self.seed = 42

    def from_audit_trace(self, trace: dict) -> Optional[ToolExample]:
        """Convert a single audit trace to a training example."""
        tool_calls = trace.get("tool_calls", [])
        if len(tool_calls) < 3:
            return None

        task = trace.get("task", "")
        output = trace.get("output", "")
        success = trace.get("success", False)

        # Determine the action taken
        if tool_calls:
            first_tool = tool_calls[0].get("tool", "")
            action_map = {
                "grep_search": "search",
                "read_file": "read",
                "run_test": "run_test",
                "git_log": "inspect_git",
                "ask_for_help": "ask_user",
            }
            action = action_map.get(first_tool, "read")
        else:
            action = "read"

        example = ToolExample(
            trace_id=trace.get("trace_id", "unknown"),
            situation=task[:200],
            action_taken=action,
            action_correct=success,
            context_before={
                "tool_calls_before": len(tool_calls),
                "task_length": len(task),
            },
            context_after={
                "success": success,
                "output_length": len(output),
            },
            quality_score=1.0 if success else 0.3,
            difficulty="easy" if success else "hard",
            source="audit_trace",
        )
        return example

    def generate_synthetic(self, count: int = 50) -> List[ToolExample]:
        """Generate synthetic training examples for coverage."""
        situations = {
            "search": [
                "Find where the login function is defined",
                "Search for all usages of the User model",
                "Find unit tests related to authentication",
            ],
            "read": [
                "Look at the implementation of handle_request",
                "Read the database schema definition",
                "Inspect the test configuration file",
            ],
            "run_test": [
                "Check if all tests pass after the change",
                "Run only the auth-related tests",
                "Verify the fix doesn't break existing tests",
            ],
            "inspect_git": [
                "Check what changed in the last commit",
                "Find when this bug was introduced",
                "See who modified this file last",
            ],
            "stop": [
                "Task is complete, all tests pass",
                "No changes needed, code is correct",
                "Changes verified, no further action needed",
            ],
            "ask_user": [
                "Unclear what the expected behavior should be",
                "Multiple possible interpretations of the bug report",
                "Missing information about the environment",
            ],
            "reject_claim": [
                "The requested API does not exist in this codebase",
                "Cannot verify the claim without more evidence",
                "The model does not have enough information",
            ],
        }

        examples = []
        random.seed(self.seed)
        for action, sit_list in situations.items():
            for sit in sit_list:
                correct = random.random() > 0.2
                examples.append(ToolExample(
                    trace_id=f"syn_{len(examples)}",
                    situation=sit,
                    action_taken=action,
                    action_correct=correct,
                    quality_score=0.8 if correct else 0.4,
                    difficulty="easy" if correct else "hard",
                    source="synthetic",
                ))

        random.shuffle(examples)
        self.examples = examples[:count]
        return self.examples

    def build_dataset(self) -> DatasetSchema:
        """Build a complete dataset with train/val split."""
        by_action: Dict[str, int] = {}
        by_difficulty: Dict[str, int] = {}

        for ex in self.examples:
            by_action[ex.action_taken] = by_action.get(ex.action_taken, 0) + 1
            by_difficulty[ex.difficulty] = by_difficulty.get(ex.difficulty, 0) + 1

        random.seed(self.seed)
        indices = list(range(len(self.examples)))
        random.shuffle(indices)
        split = int(len(indices) * (1 - self.val_split))

        return DatasetSchema(
            version="1.0",
            total_examples=len(self.examples),
            train_count=split,
            val_count=len(self.examples) - split,
            by_action=by_action,
            by_difficulty=by_difficulty,
            quality_filters=list(self.QUALITY_FILTERS),
            examples=list(self.examples),
        )

    def baseline_comparison(self) -> Dict:
        """Compare dataset against a heuristic baseline."""
        if not self.examples:
            return {"error": "No examples to compare"}
        correct = sum(1 for e in self.examples if e.action_correct)
        return {
            "total": len(self.examples),
            "heuristic_accuracy": round(correct / len(self.examples), 4),
            "above_baseline": "Dataset quality depends on trace quality",
        }
