"""Week 94 — Lyme Model Canonical Data Format.

The canonical training format for Lyme Model. Every example is traceable
back to a Lyme Audit run. Supports all training modalities:
- SFT (supervised fine-tuning)
- Tool-use imitation
- Patch critic training
- Retrieval ranking
- Verifier training
- Preference data
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import uuid


# ─── Core Data Types ───────────────────────────────────────────────────────────

@dataclass
class RepoState:
    """Snapshot of repository state at task start."""
    repo_name: str = ""
    language: str = ""
    framework: str = ""
    file_count: int = 0
    total_lines: int = 0
    test_count: int = 0
    test_framework: str = ""
    architecture_summary: str = ""
    conventions: List[str] = field(default_factory=list)
    git_head: str = ""
    git_remote: str = ""

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "language": self.language,
            "framework": self.framework,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "test_count": self.test_count,
            "test_framework": self.test_framework,
            "architecture_summary": self.architecture_summary[:200],
            "conventions": self.conventions[:10],
            "git_head": self.git_head,
            "git_remote": self.git_remote,
        }


@dataclass
class RelevantFile:
    file_path: str = ""
    file_role: str = ""  # source, test, config, docs
    lines: int = 0
    content_preview: str = ""
    dependency_of: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_role": self.file_role,
            "lines": self.lines,
            "content_preview": self.content_preview[:200],
            "dependency_of": self.dependency_of[:5],
        }


@dataclass
class ToolCall:
    sequence: int = 0
    tool_name: str = ""
    input_args: Dict = field(default_factory=dict)
    output_summary: str = ""
    observation: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "input_args": self.input_args,
            "output_summary": self.output_summary[:200],
            "observation": self.observation[:200],
            "latency_ms": round(self.latency_ms, 1),
            "success": self.success,
            "error": self.error[:100] if self.error else None,
        }


@dataclass
class PatchPlan:
    plan: str = ""
    affected_files: List[str] = field(default_factory=list)
    intended_change: str = ""
    risk_assessment: str = ""
    verification_command: str = ""
    rollback_plan: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "plan": self.plan[:500],
            "affected_files": self.affected_files[:10],
            "intended_change": self.intended_change[:500],
            "risk_assessment": self.risk_assessment[:200],
            "verification_command": self.verification_command,
            "rollback_plan": self.rollback_plan[:200],
            "confidence": round(self.confidence, 2),
        }


@dataclass
class Patch:
    file_path: str = ""
    old_content: str = ""
    new_content: str = ""
    diff: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    hash: str = ""

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "old_content": self.old_content[:500],
            "new_content": self.new_content[:500],
            "diff": self.diff[:500],
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "hash": self.hash,
        }


@dataclass
class VerificationResult:
    verification_type: str = ""  # test, static_analysis, linter, type_check
    command: str = ""
    passed: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    total_tests: int = 0
    errors: List[str] = field(default_factory=list)
    coverage_percent: Optional[float] = None
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verification_type": self.verification_type,
            "command": self.command,
            "passed": self.passed,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "total_tests": self.total_tests,
            "errors": self.errors[:5],
            "coverage_percent": self.coverage_percent,
            "findings": self.findings[:5],
        }


@dataclass
class FailureRecovery:
    attempt_number: int = 0
    max_attempts: int = 0
    failure_reason: str = ""
    failure_category: str = ""
    strategy_change: str = ""
    retry_strategy: str = ""
    lessons_learned: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0

    def to_dict(self) -> dict:
        return {
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "failure_reason": self.failure_reason[:200],
            "failure_category": self.failure_category,
            "strategy_change": self.strategy_change[:200],
            "retry_strategy": self.retry_strategy,
            "lessons_learned": self.lessons_learned[:200],
            "confidence_before": round(self.confidence_before, 2),
            "confidence_after": round(self.confidence_after, 2),
        }


# ─── Training Examples ────────────────────────────────────────────────────────

@dataclass
class LymeTrainingExample:
    """Canonical Lyme Model training example.

    Every example traces back to a Lyme Audit run.
    All fields are optional — only the relevant modality is populated.
    """
    # Identity
    example_id: str = ""
    source_trace_id: str = ""
    source_audit_id: str = ""
    created_at: str = ""

    # Task
    task_instruction: str = ""
    task_type: str = ""  # qa, locate_bug, explain_failure, plan_patch, apply_patch, verify_patch, recover, refuse
    difficulty: str = "medium"

    # Context
    repo_state: Optional[RepoState] = None
    relevant_files: List[RelevantFile] = field(default_factory=list)
    error_output: str = ""

    # Execution
    tool_calls: List[ToolCall] = field(default_factory=list)
    intermediate_observations: List[str] = field(default_factory=list)

    # Patch
    patch_plan: Optional[PatchPlan] = None
    patches: List[Patch] = field(default_factory=list)

    # Outcome
    verification: Optional[VerificationResult] = None
    failure_recoveries: List[FailureRecovery] = field(default_factory=list)
    final_answer: str = ""

    # Labels
    correct_answer: str = ""
    is_correct: bool = False
    quality_score: float = 0.0

    # Audit trail
    trace_data: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: Dict[str, Any] = {
            "example_id": self.example_id,
            "source_trace_id": self.source_trace_id,
            "source_audit_id": self.source_audit_id,
            "created_at": self.created_at,
            "task_instruction": self.task_instruction,
            "task_type": self.task_type,
            "difficulty": self.difficulty,
            "error_output": self.error_output[:500],
            "intermediate_observations": self.intermediate_observations[:10],
            "final_answer": self.final_answer[:500],
            "correct_answer": self.correct_answer[:500],
            "is_correct": self.is_correct,
            "quality_score": round(self.quality_score, 2),
        }
        if self.repo_state:
            d["repo_state"] = self.repo_state.to_dict()
        if self.relevant_files:
            d["relevant_files"] = [f.to_dict() for f in self.relevant_files[:10]]
        if self.tool_calls:
            d["tool_calls"] = [t.to_dict() for t in self.tool_calls[:20]]
        if self.patch_plan:
            d["patch_plan"] = self.patch_plan.to_dict()
        if self.patches:
            d["patches"] = [p.to_dict() for p in self.patches[:10]]
        if self.verification:
            d["verification"] = self.verification.to_dict()
        if self.failure_recoveries:
            d["failure_recoveries"] = [r.to_dict() for r in self.failure_recoveries[:5]]
        d["source"] = "lyme_audit" if self.source_trace_id else "unknown"
        return d


# ─── Modality-Specific Views ─────────────────────────────────────────────────

@dataclass
class SFTExample:
    """Supervised fine-tuning view: input -> output."""
    instruction: str = ""
    input_context: str = ""
    output: str = ""
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction,
            "input_context": self.input_context,
            "output": self.output,
            "source_example_id": self.source_example_id,
        }

    @classmethod
    def from_lyme_example(cls, ex: LymeTrainingExample) -> SFTExample:
        ctx_parts = []
        if ex.repo_state:
            ctx_parts.append(f"Repo: {ex.repo_state.repo_name} ({ex.repo_state.language})")
        if ex.relevant_files:
            ctx_parts.append(f"Files: {', '.join(f.file_path for f in ex.relevant_files[:5])}")
        if ex.error_output:
            ctx_parts.append(f"Error: {ex.error_output[:200]}")
        ctx = "\n".join(ctx_parts)

        output = ex.correct_answer or ex.final_answer
        if ex.patches:
            patch_strs = []
            for p in ex.patches:
                patch_strs.append(f"--- {p.file_path}\n{p.diff}")
            if patch_strs:
                output = "\n".join(patch_strs)

        return cls(
            instruction=ex.task_instruction,
            input_context=ctx,
            output=output,
            source_example_id=ex.example_id,
        )


@dataclass
class ToolUseExample:
    """Tool-use imitation view: context -> next tool decision."""
    scenario: str = ""
    files_read: List[str] = field(default_factory=list)
    task_remaining: str = ""
    test_failed: bool = False
    has_patch: bool = False
    loop_count: int = 0
    correct_action: str = ""
    correct_args: Dict = field(default_factory=dict)
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario[:200],
            "files_read": self.files_read[:10],
            "task_remaining": self.task_remaining[:200],
            "test_failed": self.test_failed,
            "has_patch": self.has_patch,
            "loop_count": self.loop_count,
            "correct_action": self.correct_action,
            "correct_args": self.correct_args,
            "source_example_id": self.source_example_id,
        }

    @classmethod
    def from_lyme_example(cls, ex: LymeTrainingExample) -> Optional[ToolUseExample]:
        if not ex.tool_calls:
            return None
        scenarios = []
        for i, tc in enumerate(ex.tool_calls):
            remaining_tools = ex.tool_calls[i:]
            scenario = ToolUseExample(
                scenario=f"Step {i}: after {tc.tool_name}({json.dumps(tc.input_args)[:100]})",
                files_read=[f.file_path for f in ex.relevant_files if f.file_role == "source"],
                task_remaining=ex.task_instruction,
                has_patch=bool(ex.patches),
                loop_count=i,
                correct_action=tc.tool_name,
                correct_args=tc.input_args,
                source_example_id=ex.example_id,
            )
            scenarios.append(scenario)
        return scenarios[-1] if scenarios else None


@dataclass
class PatchCriticExample:
    """Patch critic training view: patch + context -> critique."""
    task: str = ""
    patch_diff: str = ""
    target_file: str = ""
    repo_language: str = ""
    known_symbols: List[str] = field(default_factory=list)
    arch_rules: List[str] = field(default_factory=list)
    label_safe: bool = False
    label_issues: List[str] = field(default_factory=list)
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task[:200],
            "patch_diff": self.patch_diff[:500],
            "target_file": self.target_file,
            "repo_language": self.repo_language,
            "known_symbols": self.known_symbols[:20],
            "arch_rules": self.arch_rules[:5],
            "label_safe": self.label_safe,
            "label_issues": self.label_issues[:5],
            "source_example_id": self.source_example_id,
        }

    @classmethod
    def from_lyme_example(cls, ex: LymeTrainingExample) -> Optional[PatchCriticExample]:
        if not ex.patches:
            return None
        p = ex.patches[0]
        known = ex.repo_state.git_head if ex.repo_state else []
        return cls(
            task=ex.task_instruction,
            patch_diff=p.diff,
            target_file=p.file_path,
            repo_language=ex.repo_state.language if ex.repo_state else "",
            known_symbols=[],
            arch_rules=[],
            label_safe=ex.is_correct,
            label_issues=[] if ex.is_correct else ["patch_incorrect"],
            source_example_id=ex.example_id,
        )


@dataclass
class RetrievalRankingExample:
    """Retrieval ranking view: query -> ranked documents."""
    query: str = ""
    relevant_docs: List[str] = field(default_factory=list)
    irrelevant_docs: List[str] = field(default_factory=list)
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query[:200],
            "relevant_docs": self.relevant_docs[:10],
            "irrelevant_docs": self.irrelevant_docs[:10],
            "source_example_id": self.source_example_id,
        }

    @classmethod
    def from_lyme_example(cls, ex: LymeTrainingExample) -> Optional[RetrievalRankingExample]:
        if not ex.relevant_files:
            return None
        relevant = [f.file_path for f in ex.relevant_files[:5]]
        return cls(
            query=ex.task_instruction,
            relevant_docs=relevant,
            irrelevant_docs=[],
            source_example_id=ex.example_id,
        )


@dataclass
class VerifierExample:
    """Verifier training view: solution + verification -> score."""
    task: str = ""
    proposed_solution: str = ""
    patch_diff: str = ""
    verification_result: str = ""
    label_correct: bool = False
    label_issues: List[str] = field(default_factory=list)
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task[:200],
            "proposed_solution": self.proposed_solution[:500],
            "patch_diff": self.patch_diff[:500],
            "verification_result": self.verification_result[:200],
            "label_correct": self.label_correct,
            "label_issues": self.label_issues[:5],
            "source_example_id": self.source_example_id,
        }

    @classmethod
    def from_lyme_example(cls, ex: LymeTrainingExample) -> Optional[VerifierExample]:
        if not ex.verification:
            return None
        patch_diff = ex.patches[0].diff if ex.patches else ""
        return cls(
            task=ex.task_instruction,
            proposed_solution=ex.final_answer or "",
            patch_diff=patch_diff,
            verification_result=str(ex.verification.to_dict()),
            label_correct=ex.verification.passed,
            label_issues=[] if ex.verification.passed else ex.verification.errors[:3],
            source_example_id=ex.example_id,
        )


@dataclass
class PreferenceExample:
    """Preference data view: paired better/worse outputs."""
    task: str = ""
    chosen_output: str = ""
    rejected_output: str = ""
    chosen_patch: str = ""
    rejected_patch: str = ""
    preference_reason: str = ""
    source_example_id: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task[:200],
            "chosen_output": self.chosen_output[:500],
            "rejected_output": self.rejected_output[:500],
            "chosen_patch": self.chosen_patch[:500],
            "rejected_patch": self.rejected_patch[:500],
            "preference_reason": self.preference_reason[:200],
            "source_example_id": self.source_example_id,
        }


# ─── Dataset ──────────────────────────────────────────────────────────────────

@dataclass
class LymeDataset:
    """Complete Lyme Model dataset with all modality views.

    Every example is traceable back to Lyme Audit runs.
    """
    version: str = "0.1"
    created_at: str = ""
    description: str = ""

    examples: List[LymeTrainingExample] = field(default_factory=list)

    sft_examples: List[SFTExample] = field(default_factory=list)
    tool_use_examples: List[ToolUseExample] = field(default_factory=list)
    patch_critic_examples: List[ PatchCriticExample] = field(default_factory=list)
    retrieval_examples: List[RetrievalRankingExample] = field(default_factory=list)
    verifier_examples: List[VerifierExample] = field(default_factory=list)
    preference_examples: List[PreferenceExample] = field(default_factory=list)

    train_ids: List[str] = field(default_factory=list)
    val_ids: List[str] = field(default_factory=list)
    test_ids: List[str] = field(default_factory=list)

    by_task_type: Dict[str, int] = field(default_factory=dict)
    by_difficulty: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "description": self.description,
            "example_count": len(self.examples),
            "sft_count": len(self.sft_examples),
            "tool_use_count": len(self.tool_use_examples),
            "patch_critic_count": len(self.patch_critic_examples),
            "retrieval_count": len(self.retrieval_examples),
            "verifier_count": len(self.verifier_examples),
            "preference_count": len(self.preference_examples),
            "train_count": len(self.train_ids),
            "val_count": len(self.val_ids),
            "test_count": len(self.test_ids),
            "by_task_type": dict(sorted(self.by_task_type.items())),
            "by_difficulty": dict(sorted(self.by_difficulty.items())),
        }

    def to_markdown(self) -> str:
        lines = ["# Lyme Model Dataset", ""]
        lines.append(f"**Version**: {self.version}")
        lines.append(f"**Created**: {self.created_at}")
        lines.append(f"**Description**: {self.description}")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- Total examples: {len(self.examples)}")
        lines.append(f"- Train: {len(self.train_ids)} | Val: {len(self.val_ids)} | Test: {len(self.test_ids)}")
        lines.append("")
        lines.append("## By Modality")
        lines.append("")
        lines.append(f"- SFT: {len(self.sft_examples)}")
        lines.append(f"- Tool-use imitation: {len(self.tool_use_examples)}")
        lines.append(f"- Patch critic: {len(self.patch_critic_examples)}")
        lines.append(f"- Retrieval ranking: {len(self.retrieval_examples)}")
        lines.append(f"- Verifier: {len(self.verifier_examples)}")
        lines.append(f"- Preference: {len(self.preference_examples)}")
        lines.append("")
        lines.append("## By Task Type")
        for t, c in sorted(self.by_task_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {t}: {c}")
        lines.append("")
        lines.append("## By Difficulty")
        for d, c in sorted(self.by_difficulty.items(), key=lambda x: -x[1]):
            lines.append(f"- {d}: {c}")
        return "\n".join(lines)

    def compute_stats(self) -> LymeDataset:
        self.by_task_type = {}
        self.by_difficulty = {}
        for ex in self.examples:
            tt = ex.task_type or "unknown"
            self.by_task_type[tt] = self.by_task_type.get(tt, 0) + 1
            df = ex.difficulty or "medium"
            self.by_difficulty[df] = self.by_difficulty.get(df, 0) + 1
        return self


class LymeDataFormat:
    """Factory for creating Lyme Model datasets and converting between formats."""

    @staticmethod
    def create_example_id() -> str:
        return f"lyme-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def from_trace(trace: dict) -> LymeTrainingExample:
        """Convert an Open Agent Trace (dict) into a LymeTrainingExample."""
        import hashlib

        header = trace.get("header", {})
        events = trace.get("events", [])
        summary = trace.get("summary", {})
        tags = header.get("tags", {})

        ex = LymeTrainingExample(
            example_id=LymeDataFormat.create_example_id(),
            source_trace_id=header.get("trace_id", ""),
            created_at=str(datetime.now(timezone.utc).isoformat()),
            task_instruction=tags.get("task", ""),
            task_type=LymeDataFormat._infer_task_type(tags.get("task", ""), summary.get("status", "")),
            difficulty=tags.get("difficulty", "medium"),
        )

        # Repo state
        sys_info = header.get("system", {})
        if sys_info:
            ex.repo_state = RepoState(
                repo_name=sys_info.get("repo_name", ""),
                language="python",
                git_head=sys_info.get("git_head", ""),
            )

        # Events -> tool calls, patches, verification
        for ev in events:
            ev_type = ev.get("type", "")

            if ev_type == "file_read":
                ex.relevant_files.append(RelevantFile(
                    file_path=ev.get("file_path", ""),
                    file_role="source",
                    lines=ev.get("lines_read", 0),
                ))

            if ev_type == "file_edit":
                ex.patches.append(Patch(
                    file_path=ev.get("file_path", ""),
                    old_content=ev.get("old_text_preview", ""),
                    new_content=ev.get("new_text_preview", ""),
                    lines_added=ev.get("lines_added", 0),
                    lines_removed=ev.get("lines_removed", 0),
                    hash=ev.get("patch_hash", ""),
                ))

            if ev_type in ("file_edit", "file_read", "test_run", "model_call",
                           "human_intervention", "rollback", "search"):
                ex.tool_calls.append(ToolCall(
                    sequence=ev.get("sequence", 0),
                    tool_name=ev_type,
                    output_summary=str(ev.get("metadata", {}))[:200],
                    success=ev.get("status") == "success",
                    error=ev.get("error"),
                ))

            if ev_type == "test_run":
                ex.verification = VerificationResult(
                    verification_type="test",
                    command=ev.get("command", ""),
                    passed=ev.get("tests_failed", 0) == 0,
                    tests_passed=ev.get("tests_passed", 0),
                    tests_failed=ev.get("tests_failed", 0),
                    total_tests=ev.get("total_tests", 0),
                    errors=ev.get("failure_messages", []),
                    coverage_percent=ev.get("coverage_percent"),
                )

            if ev_type == "verification_step":
                if ex.verification is None:
                    ex.verification = VerificationResult(
                        verification_type=ev.get("verification_type", "static"),
                        passed=ev.get("result") == "passed",
                        findings=ev.get("findings", []),
                    )

            if ev_type == "failed_attempt":
                ex.failure_recoveries.append(FailureRecovery(
                    attempt_number=ev.get("attempt_number", 0),
                    max_attempts=ev.get("max_attempts", 0),
                    failure_reason=ev.get("failure_reason", ""),
                    failure_category=ev.get("failure_category", ""),
                    strategy_change=ev.get("strategy_change", ""),
                    retry_strategy=ev.get("retry_strategy", ""),
                    lessons_learned=ev.get("lessons_learned", ""),
                ))

            if ev_type == "confidence_change":
                if ex.failure_recoveries:
                    ex.failure_recoveries[-1].confidence_before = ev.get("prior_confidence", 0.0)
                    ex.failure_recoveries[-1].confidence_after = ev.get("post_confidence", 0.0)

            if ev_type == "evidence_claim":
                ex.intermediate_observations.append(ev.get("claim", ""))

        # Summary
        ex.final_answer = f"Status: {summary.get('status', 'unknown')}"
        ex.is_correct = summary.get("status") == "completed"
        ex.quality_score = 1.0 if ex.is_correct else (
            0.3 if summary.get("status") == "abandoned" else 0.5
        )

        return ex

    @staticmethod
    def _infer_task_type(task: str, status: str) -> str:
        task_lower = task.lower()
        if not task:
            return "unknown"
        if "crash" in task_lower:
            return "explain_failure"
        if "fix" in task_lower or "bug" in task_lower:
            return "apply_patch" if status == "completed" else "plan_patch"
        if "refactor" in task_lower:
            return "plan_patch"
        return "qa"

    @staticmethod
    def build_dataset(examples: List[LymeTrainingExample],
                      val_split: float = 0.1,
                      test_split: float = 0.1) -> LymeDataset:
        import random
        random.seed(42)

        dataset = LymeDataset(
            version="0.1",
            created_at=str(datetime.now(timezone.utc).isoformat()),
            description="Lyme Model training dataset built from audit traces",
            examples=examples,
        )

        # Build modality views
        for ex in examples:
            sft = SFTExample.from_lyme_example(ex)
            if sft:
                dataset.sft_examples.append(sft)

            tool = ToolUseExample.from_lyme_example(ex)
            if tool:
                dataset.tool_use_examples.append(tool)

            critic = PatchCriticExample.from_lyme_example(ex)
            if critic:
                dataset.patch_critic_examples.append(critic)

            ret = RetrievalRankingExample.from_lyme_example(ex)
            if ret:
                dataset.retrieval_examples.append(ret)

            ver = VerifierExample.from_lyme_example(ex)
            if ver:
                dataset.verifier_examples.append(ver)

        # Split
        indices = list(range(len(examples)))
        random.shuffle(indices)
        n = len(indices)
        test_n = int(n * test_split)
        val_n = int(n * val_split)
        test_ids = [examples[i].example_id for i in indices[:test_n]]
        val_ids = [examples[i].example_id for i in indices[test_n:test_n + val_n]]
        train_ids = [examples[i].example_id for i in indices[test_n + val_n:]]

        dataset.test_ids = test_ids
        dataset.val_ids = val_ids
        dataset.train_ids = train_ids
        dataset.compute_stats()

        return dataset

    @staticmethod
    def to_jsonl(examples: list, output_path: str):
        """Write a list of dict-able objects to JSONL."""
        with open(output_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex.to_dict()) + "\n")

    @staticmethod
    def to_json(dataset: LymeDataset, output_path: str):
        """Write complete dataset to JSON."""
        result = dataset.to_dict()
        result["examples"] = [ex.to_dict() for ex in dataset.examples]
        result["sft_examples"] = [ex.to_dict() for ex in dataset.sft_examples]
        result["tool_use_examples"] = [ex.to_dict() for ex in dataset.tool_use_examples]
        result["patch_critic_examples"] = [ex.to_dict() for ex in dataset.patch_critic_examples]
        result["retrieval_examples"] = [ex.to_dict() for ex in dataset.retrieval_examples]
        result["verifier_examples"] = [ex.to_dict() for ex in dataset.verifier_examples]
        result["preference_examples"] = [ex.to_dict() for ex in dataset.preference_examples]
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
