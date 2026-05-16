from dataclasses import dataclass, field
from typing import List


@dataclass
class BenchmarkCategory:
    name: str
    description: str
    metrics: List[str] = field(default_factory=list)
    weight: float = 1.0


LATENCY = BenchmarkCategory(
    name="latency",
    description="Time-to-first-token, total execution time, tool call overhead",
    metrics=["time_to_first_token_ms", "total_duration_ms", "tool_call_latency_ms",
             "tool_call_overhead_ms", "token_generation_speed"],
)

TOKEN_THROUGHPUT = BenchmarkCategory(
    name="token_throughput",
    description="Token generation rates, context utilization, efficiency",
    metrics=["tokens_per_second", "input_tokens", "output_tokens",
             "total_tokens", "context_utilization_pct", "tokens_per_tool_call"],
)

TOOL_CALL_OVERHEAD = BenchmarkCategory(
    name="tool_call_overhead",
    description="Cost and latency of individual tool calls",
    metrics=["tool_call_count", "tool_call_duration_ms", "tool_call_failure_rate",
             "tools_per_task", "tool_selection_time_ms", "tool_result_processing_ms"],
)

CONTEXT_RETENTION = BenchmarkCategory(
    name="context_retention",
    description="Ability to retain and use information across context windows",
    metrics=["context_recall_accuracy", "forgotten_constraints", "contradictory_edits",
             "context_window_count", "context_fragmentation_score",
             "information_retention_rate", "style_consistency"],
)

DIFF_QUALITY = BenchmarkCategory(
    name="diff_quality",
    description="Quality and precision of generated diffs",
    metrics=["diff_accuracy", "diff_precision", "diff_recall", "unnecessary_changes",
             "broken_code_rate", "syntax_error_rate", "diff_apply_success_rate",
             "semantic_correctness", "architectural_consistency"],
)

REPAIR_ABILITY = BenchmarkCategory(
    name="repair_ability",
    description="Ability to detect and fix errors",
    metrics=["repair_success_rate", "repair_attempts", "time_to_repair_ms",
             "self_detected_errors", "error_type_coverage", "regression_rate"],
)

RETRY_BEHAVIOR = BenchmarkCategory(
    name="retry_behavior",
    description="Patterns and effectiveness of retry attempts",
    metrics=["retry_count", "retry_strategy_shifts", "retry_success_rate",
             "retry_explosion_score", "persistence_score", "retry_diversity"],
)

HALLUCINATION = BenchmarkCategory(
    name="hallucination",
    description="Rate and types of hallucinated content",
    metrics=["hallucination_rate", "hallucination_types", "hallucination_severity",
             "fabricated_api_rate", "fabricated_file_rate", "nonsensical_code_rate",
             "hallucination_detection_delay"],
)

FILE_NAVIGATION = BenchmarkCategory(
    name="file_navigation",
    description="Efficiency of navigating repository structure",
    metrics=["files_read_per_task", "files_written_per_task", "navigation_efficiency",
             "redundant_reads", "search_efficiency", "directory_coverage",
             "file_discovery_rate"],
)

REPO_UNDERSTANDING = BenchmarkCategory(
    name="repo_understanding",
    description="Depth of repository comprehension",
    metrics=["architectural_recall", "dependency_understanding", "convention_adherence",
             "api_understanding", "pattern_recognition", "codebase_mapping_accuracy",
             "design_pattern_identification"],
)

LONG_HORIZON = BenchmarkCategory(
    name="long_horizon",
    description="Performance on extended multi-step tasks",
    metrics=["task_completion_rate", "steps_to_completion", "intermediate_coherence",
             "goal_maintenance", "subtask_decomposition_quality",
             "long_range_dependency_handling", "progress_consistency"],
)

MULTI_FILE_EDIT = BenchmarkCategory(
    name="multi_file_edit",
    description="Consistency across edits spanning multiple files",
    metrics=["cross_file_consistency", "interface_contract_preservation",
             "import_accuracy", "type_consistency", "side_effect_awareness",
             "change_propagation_accuracy", "architectural_coherence"],
)


ALL_CATEGORIES = [
    LATENCY, TOKEN_THROUGHPUT, TOOL_CALL_OVERHEAD, CONTEXT_RETENTION,
    DIFF_QUALITY, REPAIR_ABILITY, RETRY_BEHAVIOR, HALLUCINATION,
    FILE_NAVIGATION, REPO_UNDERSTANDING, LONG_HORIZON, MULTI_FILE_EDIT,
]

CATEGORY_MAP = {c.name: c for c in ALL_CATEGORIES}
