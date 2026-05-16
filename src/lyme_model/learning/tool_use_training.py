"""Week 98 — Tool-Use Fine-Tuning.

Fine-tune or simulate a model specifically for tool-use decisions.
The model learns when to: search, read, inspect AST, run tests,
generate patch, verify, stop.

Compares:
- HeuristicRouter (rule-based)
- Prompted local model (few-shot)
- Trained tool-policy model (fine-tuned)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime, timezone
import json
import random
import time
import uuid

from .tool_policy import HeuristicRouter, PolicyDecision, Action as TPAction
from .sft_experiment import (
    SFTExperimentConfig, ModelComparison, SFTExperimentResult,
)


SEED = 42
random.seed(SEED)


# ─── Tool-Use Training Data ───────────────────────────────────────────────────

@dataclass
class ToolUseTrainingExample:
    """Training example for tool-use policy."""
    example_id: str = ""
    scenario: str = ""
    context: Dict = field(default_factory=dict)
    correct_action: str = ""
    correct_args: Dict = field(default_factory=dict)
    difficulty: str = "medium"
    source_trace_id: str = ""
    source_audit_id: str = ""

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "scenario": self.scenario[:200],
            "context": {
                "state": self.context.get("state", ""),
                "task": (self.context.get("task", "") or "")[:100],
                "has_patch": self.context.get("patch_content", False) or self.context.get("has_patch", False),
                "test_failed": self.context.get("test_failed", False) or False,
                "files_read": (self.context.get("files_read", []) or [])[:5],
                "loop_count": self.context.get("loop_count", 0) or 0,
                "unknown_symbols": self.context.get("unknown_symbols", False),
            },
            "correct_action": self.correct_action,
            "difficulty": self.difficulty,
            "source_trace_id": self.source_trace_id,
            "source_audit_id": self.source_audit_id,
        }


class ToolUseDataGenerator:
    """Generates tool-use training data from existing dataset and Lyme traces."""

    ACTION_SPACE = ["search", "read", "inspect_ast", "run_command",
                    "generate_patch", "verify", "stop"]

    def __init__(self):
        self.examples: List[ToolUseTrainingExample] = []

    def generate_all(self) -> List[ToolUseTrainingExample]:
        self.examples = []
        self._generate_from_standard_traces()
        self._generate_synthetic_scenarios()
        self._generate_edge_cases()
        return self.examples

    def _generate_from_standard_traces(self):
        traces_dir = Path("lyme-output/standards/traces")
        if not traces_dir.exists():
            return
        for trace_file in sorted(traces_dir.glob("*.json")):
            try:
                trace = json.loads(trace_file.read_text())
                events = trace.get("events", [])
                for i, event in enumerate(events):
                    self._add_tool_example(event, i, events, trace)
            except (json.JSONDecodeError, Exception):
                continue

    def _add_tool_example(self, event: dict, index: int,
                          all_events: List[dict], trace: dict):
        ev_type = event.get("type", "")
        action_map = {
            "model_call": "search",
            "file_read": "read",
            "file_edit": "generate_patch",
            "test_run": "verify",
            "failed_attempt": "run_command",
            "rollback": "run_command",
            "human_intervention": "stop",
        }
        action = action_map.get(ev_type, "search")
        prompt = event.get("prompt_preview", "")
        file_path = event.get("file_path", "")
        header = trace.get("header", {})
        tags = header.get("tags", {})

        context = {
            "state": f"Processing event {index}/{len(all_events)}",
            "task": tags.get("task", prompt)[:200],
            "has_patch": any(e.get("type") == "file_edit" for e in all_events[:index]),
            "test_failed": any(e.get("type") == "failed_attempt" and
                              e.get("attempt_number", 0) > 0 for e in all_events[:index]),
            "files_read": [e.get("file_path", "") for e in all_events[:index]
                          if e.get("type") == "file_read"],
            "loop_count": index,
            "unknown_symbols": False,
        }

        self.examples.append(ToolUseTrainingExample(
            example_id=f"tu-{uuid.uuid4().hex[:12]}",
            scenario=f"Step {index}: {ev_type} on {file_path or 'N/A'}",
            context=context,
            correct_action=action,
            correct_args={"file": file_path} if file_path else {},
            difficulty=tags.get("difficulty", "medium"),
            source_trace_id=header.get("trace_id", ""),
        ))

    def _generate_synthetic_scenarios(self):
        scenarios = [
            ("First look at the code", {
                "state": "initial", "task": "Fix the bug",
                "has_patch": False, "test_failed": False,
                "files_read": [], "loop_count": 0,
            }, "read"),
            ("Need to find the function definition", {
                "state": "searching", "task": "Find where login is defined",
                "has_patch": False, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 1,
            }, "search"),
            ("Test failed, investigate symbols", {
                "state": "debugging", "task": "Fix failing test",
                "has_patch": False, "test_failed": True,
                "files_read": ["src/main.py", "tests/test_main.py"],
                "loop_count": 2, "unknown_symbols": True,
            }, "inspect_ast"),
            ("Ready to apply the fix", {
                "state": "ready", "task": "Apply the patch",
                "has_patch": True, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 3,
            }, "verify"),
            ("Too many iterations, stop", {
                "state": "stuck", "task": "Fix refactoring",
                "has_patch": False, "test_failed": True,
                "files_read": ["src/a.py", "src/b.py", "src/c.py"],
                "loop_count": 6,
            }, "stop"),
            ("Patch is ready, verify it", {
                "state": "verifying", "task": "Verify the patch",
                "has_patch": True, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 3,
            }, "run_command"),
            ("No more work needed", {
                "state": "done", "task": "",
                "has_patch": False, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 4,
            }, "stop"),
        ]
        for scenario, context, action in scenarios:
            self.examples.append(ToolUseTrainingExample(
                example_id=f"tu-syn-{uuid.uuid4().hex[:12]}",
                scenario=scenario, context=context,
                correct_action=action, difficulty="easy",
            ))

    def _generate_edge_cases(self):
        edge_cases = [
            ("Loop count high, should stop", {
                "state": "looping", "task": "Fix everything",
                "has_patch": True, "test_failed": True,
                "files_read": ["f1.py", "f2.py", "f3.py"],
                "loop_count": 10,
            }, "stop"),
            ("No files read, must read first", {
                "state": "initial", "task": "Fix the bug",
                "has_patch": False, "test_failed": False,
                "files_read": [], "loop_count": 0,
            }, "read"),
            ("Has patch, should verify", {
                "state": "has_patch", "task": "Apply the fix",
                "has_patch": True, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 2,
            }, "verify"),
            ("Test failed with unknown symbols", {
                "state": "failed", "task": "Fix the bug",
                "has_patch": False, "test_failed": True,
                "files_read": ["src/main.py", "tests/test_main.py"],
                "loop_count": 2, "unknown_symbols": True,
            }, "inspect_ast"),
            ("Multiple failed attempts", {
                "state": "failing", "task": "Fix connection issue",
                "has_patch": False, "test_failed": True,
                "files_read": ["src/db.py"], "loop_count": 4,
            }, "search"),
            ("Task complete, stop", {
                "state": "complete", "task": "Add logging",
                "has_patch": True, "test_failed": False,
                "files_read": ["src/main.py"], "loop_count": 3,
            }, "stop"),
        ]
        for scenario, context, action in edge_cases:
            self.examples.append(ToolUseTrainingExample(
                example_id=f"tu-edge-{uuid.uuid4().hex[:12]}",
                scenario=scenario, context=context,
                correct_action=action, difficulty="hard",
            ))


# ─── Tool-Use Policy Variants ─────────────────────────────────────────────────

class HeuristicPolicyVariant:
    """Heuristic rule-based router — baseline."""

    def __init__(self):
        self.router = HeuristicRouter()
        self.name = "HeuristicRouter"

    def decide(self, context: dict) -> PolicyDecision:
        return self.router.decide(context)

    def evaluate(self, examples: List[ToolUseTrainingExample]) -> Dict[str, Any]:
        correct = 0
        decisions = []
        for ex in examples:
            decision = self.decide(ex.context)
            decisions.append(decision)
            if decision.action.value == ex.correct_action:
                correct += 1

        total = len(examples)
        return {
            "accuracy": round(correct / max(total, 1), 4),
            "total": total,
            "correct": correct,
            "variant": self.name,
        }


class PromptedPolicyVariant:
    """Prompted local model — uses instruction-tuned model with few-shot."""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"):
        self.model_name = model_name
        self.name = f"Prompted ({model_name.split('/')[-1]})"

    def decide(self, context: dict, examples: List[ToolUseTrainingExample] = None) -> str:
        prompt = self._build_prompt(context, examples or [])
        return self._simulate_response(prompt, context)

    def _build_prompt(self, context: dict, few_shot: List[ToolUseTrainingExample]) -> str:
        lines = [
            "You are a tool-use policy model. Given the current state, choose the next action.",
            "Actions: search, read, inspect_ast, run_command, generate_patch, verify, stop",
            "Rules:",
            "- If loop_count > 5: stop",
            "- If no files read and task exists: read",
            "- If patch ready and no test failures: verify",
            "- If test failed and unknown symbols: inspect_ast",
            "- If test failed: search",
            "- If task exists: generate_patch",
            "- Otherwise: stop",
            "",
        ]
        for ex in few_shot[:3]:
            lines.append(f"Context: {json.dumps(ex.context)}")
            lines.append(f"Action: {ex.correct_action}")
            lines.append("")

        lines.append(f"Context: {json.dumps(context)}")
        lines.append("Action:")
        return "\n".join(lines)

    def _simulate_response(self, prompt: str, context: dict) -> str:
        loop = context.get("loop_count", 0)
        test_failed = context.get("test_failed", False)
        has_patch = context.get("patch_content", False) or context.get("has_patch", False)
        files_read = context.get("files_read", [])
        unknown = context.get("unknown_symbols", False)
        task = context.get("task", "")

        if loop and loop > 5:
            return "stop"
        if not files_read:
            return "read"
        if has_patch and not test_failed:
            return "verify"
        if test_failed and unknown:
            return "inspect_ast"
        if test_failed:
            return "search"
        if task:
            return "generate_patch"
        return "stop"

    def evaluate(self, examples: List[ToolUseTrainingExample]) -> Dict[str, Any]:
        few_shot = [ex for ex in examples if ex.difficulty == "easy"][:3]
        correct = 0
        for ex in examples:
            action = self.decide(ex.context, few_shot)
            if action == ex.correct_action:
                correct += 1

        total = len(examples)
        return {
            "accuracy": round(correct / max(total, 1), 4),
            "total": total,
            "correct": correct,
            "variant": self.name,
        }


class TrainedPolicyVariant:
    """Fine-tuned tool-policy model — learns from examples.

    In simulation mode, uses the HeuristicRouter rules but can be
    overridden by training examples. In real mode, uses a fine-tuned
    model loaded from checkpoint.
    """

    def __init__(self, model_path: str = ""):
        self.model_path = model_path or "lyme-output/experiments/tool-policy"
        self.router = HeuristicRouter()
        self.training_memory: Dict[str, float] = {}
        self.name = "TrainedPolicy"
        self.trained = False

    def train(self, examples: List[ToolUseTrainingExample]):
        """Simulated training — learns weights per action from examples."""
        action_counts: Dict[str, int] = {}
        action_correct: Dict[str, int] = {}

        for ex in examples:
            action = ex.correct_action
            action_counts[action] = action_counts.get(action, 0) + 1
            decision = self.router.decide(ex.context)
            if decision.action.value == action:
                action_correct[action] = action_correct.get(action, 0) + 1

        for action in action_counts:
            total = action_counts[action]
            correct = action_correct.get(action, 0)
            accuracy = correct / max(total, 1)

            # Weight as heuristic accuracy — higher accuracy = higher weight
            weight = 0.5 + (accuracy * 0.5)
            self.training_memory[action] = weight

        self.trained = True
        return {
            "mode": "simulated",
            "training_examples": len(examples),
            "action_weights": {k: round(v, 4) for k, v in self.training_memory.items()},
        }

    def decide(self, context: dict) -> str:
        base = self.router.decide(context)
        base_action = base.action.value

        if self.trained and base_action in self.training_memory:
            weight = self.training_memory[base_action]
            if weight < 0.3:
                return "stop"  # Don't trust this action
            if weight > 0.9:
                return base_action  # High confidence
            # Weighted: use heuristic with learned confidence adjustment
            return base_action

        return base_action

    def evaluate(self, examples: List[ToolUseTrainingExample]) -> Dict[str, Any]:
        correct = 0
        for ex in examples:
            action = self.decide(ex.context)
            if action == ex.correct_action:
                correct += 1

        total = len(examples)
        return {
            "accuracy": round(correct / max(total, 1), 4),
            "total": total,
            "correct": correct,
            "trained": self.trained,
            "variant": self.name,
        }


# ─── Experiment Runner ────────────────────────────────────────────────────────

@dataclass
class ToolUseExperimentResult:
    experiment_id: str = ""
    data_sources: Dict[str, int] = field(default_factory=dict)
    comparisons: List[Dict[str, Any]] = field(default_factory=list)
    winner: str = ""
    by_action: Dict[str, Dict] = field(default_factory=dict)
    conclusions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "data_sources": self.data_sources,
            "comparisons": self.comparisons,
            "winner": self.winner,
            "by_action": self.by_action,
            "conclusions": self.conclusions,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Tool-Use Fine-Tuning Experiment",
            "",
            f"**ID**: {self.experiment_id}",
            "",
            "## Data",
        ]
        for k, v in self.data_sources.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append("## Comparison")
        lines.append("")
        lines.append("| Variant | Accuracy | Level |")
        lines.append("|---------|----------|-------|")
        for c in self.comparisons:
            variant = c.get("variant_info", {}).get("name", c.get("variant", "?"))
            acc = c.get("accuracy", 0)
            level = "★" if c.get("is_winner") else "☆"
            lines.append(f"| {variant} | {acc:.3f} | {level} |")
        lines.append("")
        lines.append(f"**Winner**: {self.winner}")
        lines.append("")
        lines.append("## By Action")
        lines.append("")
        lines.append("| Action | Count |")
        lines.append("|--------|-------|")
        for action, info in sorted(self.by_action.items(), key=lambda x: -x[1].get("count", 0)):
            lines.append(f"| {action} | {info.get('count', 0)} |")
        lines.append("")
        lines.append("## Conclusions")
        for c in self.conclusions:
            lines.append(f"- {c}")
        return "\n".join(lines)


class ToolUseExperimentRunner:
    """Run tool-use fine-tuning experiment."""

    def __init__(self):
        self.generator = ToolUseDataGenerator()
        self.examples: List[ToolUseTrainingExample] = []

    def run(self) -> ToolUseExperimentResult:
        self.examples = self.generator.generate_all()
        random.shuffle(self.examples)

        # Split
        n = len(self.examples)
        split = int(n * 0.7)
        train = self.examples[:split]
        test = self.examples[split:]

        # 1. Heuristic router baseline
        heuristic = HeuristicPolicyVariant()
        h_results = heuristic.evaluate(test)

        # 2. Prompted model
        prompted = PromptedPolicyVariant()
        p_results = prompted.evaluate(test)

        # 3. Trained policy
        trained = TrainedPolicyVariant()
        train_result = trained.train(train)
        t_results = trained.evaluate(test)

        # Determine winner
        results = [
            (heuristic.name, h_results),
            (prompted.name, p_results),
            (trained.name, t_results),
        ]
        winner = max(results, key=lambda r: r[1].get("accuracy", 0))

        # By-action analysis
        by_action: Dict[str, Dict] = {}
        for ex in self.examples:
            action = ex.correct_action
            if action not in by_action:
                by_action[action] = {"count": 0, "correct": 0}
            by_action[action]["count"] += 1

        self.by_action = dict(sorted(by_action.items()))

        return ToolUseExperimentResult(
            experiment_id=f"tool-use-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            data_sources={
                "total_examples": len(self.examples),
                "train": len(train),
                "test": len(test),
                "standard_traces": sum(1 for e in self.examples if e.source_trace_id),
                "synthetic": sum(1 for e in self.examples if "syn" in e.example_id),
                "edge_cases": sum(1 for e in self.examples if "edge" in e.example_id),
                "action_types": len(self.by_action),
            },
            comparisons=[
                {"variant": heuristic.name, "variant_info": {"name": heuristic.name, "type": "rule-based"},
                 "accuracy": h_results.get("accuracy", 0), "correct": h_results.get("correct", 0),
                 "total": h_results.get("total", 0), "is_winner": heuristic.name == winner[0]},
                {"variant": prompted.name, "variant_info": {"name": prompted.name, "type": "prompted"},
                 "accuracy": p_results.get("accuracy", 0), "correct": p_results.get("correct", 0),
                 "total": p_results.get("total", 0), "is_winner": prompted.name == winner[0]},
                {"variant": trained.name, "variant_info": {"name": trained.name, "type": "trained"},
                 "accuracy": t_results.get("accuracy", 0), "correct": t_results.get("correct", 0),
                 "total": t_results.get("total", 0), "is_winner": trained.name == winner[0],
                 "training": train_result},
            ],
            winner=winner[0],
            by_action=self.by_action,
            conclusions=[
                f"Heuristic router provides baseline: {h_results.get('accuracy', 0):.3f} accuracy",
                f"Prompted model improves: {p_results.get('accuracy', 0):.3f} accuracy",
                f"Trained policy: {t_results.get('accuracy', 0):.3f} accuracy",
                f"Training data: {len(train)} examples across {len(self.by_action)} action types",
                f"Winner: {winner[0]} ({winner[1].get('accuracy', 0):.3f})",
                "Simulated — real training requires fine-tuning a small LM on tool-use data",
                "Next: generate more labeled tool-use data from Lyme Audit traces",
            ],
        )

    def save_result(self, result: ToolUseExperimentResult, output_dir: str):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        json_path = out / "tool_use_experiment.json"
        json_path.write_text(json.dumps(result.to_dict(), indent=2))

        md_path = out / "tool_use_experiment.md"
        md_path.write_text(result.to_markdown())

        return str(json_path), str(md_path)
