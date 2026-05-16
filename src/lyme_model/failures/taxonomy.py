"""Week 73 — Local Coding Agent Error Taxonomy.

12 failure categories specific to small local coding models.
Measured via Lyme Audit traces.

Categories:
- missing_context
- wrong_file_selected
- hallucinated_api
- bad_patch
- incomplete_patch
- test_misunderstanding
- command_misuse
- syntax_regression
- architectural_misunderstanding
- excessive_latency
- context_overflow
- tool_loop_failure
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum


class LocalCodingFailureCategory(Enum):
    MISSING_CONTEXT = "missing_context"
    WRONG_FILE_SELECTED = "wrong_file_selected"
    HALLUCINATED_API = "hallucinated_api"
    BAD_PATCH = "bad_patch"
    INCOMPLETE_PATCH = "incomplete_patch"
    TEST_MISUNDERSTANDING = "test_misunderstanding"
    COMMAND_MISUSE = "command_misuse"
    SYNTAX_REGRESSION = "syntax_regression"
    ARCHITECTURAL_MISUNDERSTANDING = "architectural_misunderstanding"
    EXCESSIVE_LATENCY = "excessive_latency"
    CONTEXT_OVERFLOW = "context_overflow"
    TOOL_LOOP_FAILURE = "tool_loop_failure"


LOCAL_CODING_TAXONOMY = {
    LocalCodingFailureCategory.MISSING_CONTEXT: {
        "description": "Model lacked relevant file/repo context to complete the task correctly",
        "root_cause": "Context window too small, retrieval missed key files, or no retrieval used",
        "user_message": "I did not have enough context about the codebase to answer correctly.",
        "mitigation": "Add retrieval step before generation; use context packet compiler",
        "severity": "high",
        "detectable_by": [
            "audit_trace_shows_no_read_before_edit",
            "output_refers_to_stale_or_wrong_code",
            "patch_contradicts_existing_code",
        ],
    },
    LocalCodingFailureCategory.WRONG_FILE_SELECTED: {
        "description": "Model edited or referenced the wrong file",
        "root_cause": "Similar filenames, ambiguous task, or model guessed file location",
        "user_message": "I selected the wrong file. The change should apply to a different location.",
        "mitigation": "Verify file existence and content before editing; require file path confirmation",
        "severity": "high",
        "detectable_by": [
            "audit_shows_edit_in_unexpected_file",
            "file_content_does_not_match_task",
            "test_fails_after_edit_in_wrong_file",
        ],
    },
    LocalCodingFailureCategory.HALLUCINATED_API: {
        "description": "Model referenced a function, class, or API that does not exist in the codebase",
        "root_cause": "Model generalizes from training data instead of reading actual code",
        "user_message": "I referenced something that doesn't exist in this codebase.",
        "mitigation": "Verify symbol existence before use; force AST inspection step",
        "severity": "critical",
        "detectable_by": [
            "import_error_on_generated_code",
            "function_call_matches_no_definition",
            "audit_shows_no_read_for_referenced_symbol",
        ],
    },
    LocalCodingFailureCategory.BAD_PATCH: {
        "description": "Patch was applied but introduced errors, broke functionality, or was syntactically wrong",
        "root_cause": "Model misunderstood the change needed or generated malformed diff",
        "user_message": "The patch I generated contains errors.",
        "mitigation": "Validate patch syntax before apply; run patch dry-run; add patch critic",
        "severity": "high",
        "detectable_by": [
            "patch_fails_to_apply",
            "syntax_error_after_patch",
            "tests_fail_after_patch",
        ],
    },
    LocalCodingFailureCategory.INCOMPLETE_PATCH: {
        "description": "Patch was applied but only partially addressed the issue",
        "root_cause": "Model missed side effects, related files, or edge cases",
        "user_message": "The fix only addresses part of the problem. Additional changes may be needed.",
        "mitigation": "Require impact analysis before patching; add cross-file dependency check",
        "severity": "medium",
        "detectable_by": [
            "test_still_failing_after_patch",
            "related_function_not_updated",
            "import_added_but_not_used",
        ],
    },
    LocalCodingFailureCategory.TEST_MISUNDERSTANDING: {
        "description": "Model misinterpreted test failure output or test intent",
        "root_cause": "Model did not parse test output correctly or lacked understanding of test framework",
        "user_message": "I misunderstood what the test was checking.",
        "mitigation": "Parse test output structurally; show model only relevant test lines",
        "severity": "medium",
        "detectable_by": [
            "fix_does_not_address_test_assertion",
            "model_changed_test_instead_of_code",
            "output_shows_wrong_interpretation_of_test_error",
        ],
    },
    LocalCodingFailureCategory.COMMAND_MISUSE: {
        "description": "Model ran wrong command, wrong flags, or incorrect shell invocation",
        "root_cause": "Model guessed command syntax instead of checking docs or history",
        "user_message": "I used the wrong command or flags.",
        "mitigation": "Cache successful commands; validate command before running; restrict dangerous flags",
        "severity": "medium",
        "detectable_by": [
            "non_zero_exit_code",
            "command_not_found",
            "wrong_flag_error",
        ],
    },
    LocalCodingFailureCategory.SYNTAX_REGRESSION: {
        "description": "Patch introduced syntax errors in an otherwise valid file",
        "root_cause": "Model generated code without checking surrounding syntax context",
        "user_message": "The change introduced a syntax error.",
        "mitigation": "Run syntax check after every edit; provide file AST context before edit",
        "severity": "high",
        "detectable_by": [
            "python_syntax_error",
            "json_decode_error",
            "compiler_error_after_patch",
        ],
    },
    LocalCodingFailureCategory.ARCHITECTURAL_MISUNDERSTANDING: {
        "description": "Model did not understand the codebase's architecture, leading to wrong approach",
        "root_cause": "Model lacked architectural overview or misapplied patterns from training data",
        "user_message": "I didn't understand how this codebase is structured. The approach was wrong.",
        "mitigation": "Provide architectural summary before task; detect architectural patterns automatically",
        "severity": "high",
        "detectable_by": [
            "model_used_wrong_pattern",
            "change_breaks_encapsulation",
            "model_added_code_to_wrong_layer",
        ],
    },
    LocalCodingFailureCategory.EXCESSIVE_LATENCY: {
        "description": "Model response or task completion took too long (>30s on consumer GPU)",
        "root_cause": "Slow model, large context, many tool calls, or inefficient prompt",
        "user_message": "The operation was too slow.",
        "mitigation": "Use smaller model for subtasks; cache aggressively; parallel tool calls",
        "severity": "low",
        "detectable_by": [
            "total_time_exceeds_threshold",
            "model_load_time_high",
            "too_many_sequential_tool_calls",
        ],
    },
    LocalCodingFailureCategory.CONTEXT_OVERFLOW: {
        "description": "Context exceeded model's maximum window, causing truncation or degradation",
        "root_cause": "Too much context provided without prioritization or compression",
        "user_message": "There was too much information. I may have missed important parts.",
        "mitigation": "Compress context packets; prioritize relevant files; use sliding window",
        "severity": "medium",
        "detectable_by": [
            "context_tokens_exceed_limit",
            "output_ignores_late_context",
            "retrieval_returned_too_many_files",
        ],
    },
    LocalCodingFailureCategory.TOOL_LOOP_FAILURE: {
        "description": "Model got stuck in a tool call loop without making progress",
        "root_cause": "Model lacks stopping criteria or keeps retrying the same action",
        "user_message": "I got stuck repeating the same actions without making progress.",
        "mitigation": "Add loop detection; enforce max retries; require progress check after N calls",
        "severity": "high",
        "detectable_by": [
            "same_tool_called_more_than_3_times",
            "no_file_changes_after_N_tool_calls",
            "identical_command_repeated",
        ],
    },
}


@dataclass
class LocalCodingFailureRecord:
    failure_id: str
    category: LocalCodingFailureCategory
    description: str
    severity: str
    trace_ref: Optional[str] = None
    audit_ref: Optional[str] = None
    mitigated_by: Optional[str] = None
    context: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "failure_id": self.failure_id,
            "category": self.category.value,
            "severity": self.severity,
            "description": self.description,
            "trace_ref": self.trace_ref,
            "audit_ref": self.audit_ref,
            "mitigated_by": self.mitigated_by,
            "context": self.context,
            "timestamp": self.timestamp,
        }

    def cli_line(self) -> str:
        icon = {"critical": "XX", "high": "!!", "medium": "!!", "low": "??"}.get(
            self.severity, "!!"
        )
        return (
            f"{icon} [{self.severity.upper():8s}] "
            f"{self.category.value:30s} "
            f"{self.description[:60]}"
        )


@dataclass
class LocalCodingFailureAnalysis:
    failures: List[LocalCodingFailureRecord] = field(default_factory=list)
    total_count: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    mitigation_rate: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "by_category": self.by_category,
            "by_severity": self.by_severity,
            "mitigation_rate": self.mitigation_rate,
            "summary": self.summary,
            "failures": [f.to_dict() for f in self.failures],
        }
