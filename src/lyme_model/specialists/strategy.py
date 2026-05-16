"""Week 133 — Lyme Model Specialization Strategy.

Do not try to make one local model good at everything.
Identify specialized capabilities, rank them, and select the 3 that matter most.

Every specialist flows through Lyme Audit.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class HardwareTier(Enum):
    MINIMAL = "minimal"        # 4GB RAM, 0GB VRAM
    CPU_ONLY = "cpu_only"      # 8GB RAM, 0GB VRAM
    BUDGET_GPU = "budget_gpu"  # 8GB RAM, 4GB VRAM
    STANDARD_GPU = "standard_gpu"  # 16GB RAM, 8GB VRAM
    HIGH_END = "high_end"      # 32GB RAM, 24GB VRAM


class SpecializationDomain:
    REPO_QA = "repo_qa"
    PATCH_PLANNING = "patch_planning"
    TEST_FAILURE_EXPLANATION = "test_failure_explanation"
    BUG_LOCALIZATION = "bug_localization"
    SAFE_SMALL_EDITS = "safe_small_edits"
    SEMANTIC_DIFF_EXPLANATION = "semantic_diff_explanation"
    TOOL_USE_ROUTING = "tool_use_routing"
    PATCH_CRITICISM = "patch_criticism"
    VERIFICATION_PLANNING = "verification_planning"


@dataclass
class SpecializationSpec:
    domain: str
    required_model_size: str       # e.g. "1.5B", "3B", "7B", "14B"
    required_context_tokens: int
    required_tools: List[str]
    training_data_needs: str
    benchmark_criteria: List[str]
    hardware_cost_tier: HardwareTier
    estimated_quality_at_minimum: float  # 0-1
    estimated_quality_at_standard: float  # 0-1
    exists_currently: bool
    priority_score: int  # 1-100


SPECIALIZATIONS: Dict[str, SpecializationSpec] = {
    SpecializationDomain.REPO_QA: SpecializationSpec(
        domain="Repo Q&A — Answer questions about repository structure, APIs, dependencies",
        required_model_size="1.5B",
        required_context_tokens=4096,
        required_tools=["read_file", "grep_search", "list_directory", "think"],
        training_data_needs="QA pairs from real repos: question + evidence + grounded answer",
        benchmark_criteria=["answer_correctness", "citation_accuracy", "hallucination_rate", "latency"],
        hardware_cost_tier=HardwareTier.CPU_ONLY,
        estimated_quality_at_minimum=0.70,
        estimated_quality_at_standard=0.94,
        exists_currently=True,
        priority_score=95,
    ),
    SpecializationDomain.PATCH_PLANNING: SpecializationSpec(
        domain="Patch Planning — Given a task and repo context, produce a validated edit plan before writing code",
        required_model_size="3B",
        required_context_tokens=8192,
        required_tools=["read_file", "grep_search", "think", "inspect_ast", "verify_change"],
        training_data_needs="Task + repo context → structured plan with affected files, change descriptions, risks",
        benchmark_criteria=["plan_acceptance_rate", "plan_completeness", "missed_dependencies", "false_positives"],
        hardware_cost_tier=HardwareTier.BUDGET_GPU,
        estimated_quality_at_minimum=0.60,
        estimated_quality_at_standard=0.85,
        exists_currently=True,
        priority_score=90,
    ),
    SpecializationDomain.TEST_FAILURE_EXPLANATION: SpecializationSpec(
        domain="Test Failure Explanation — Given a failing test, explain why it fails with code evidence",
        required_model_size="3B",
        required_context_tokens=8192,
        required_tools=["read_file", "grep_search", "git_log", "inspect_ast", "think"],
        training_data_needs="Test output + code context → failure explanation with line-level attribution",
        benchmark_criteria=["explanation_accuracy", "root_cause_precision", "fix_suggestion_quality"],
        hardware_cost_tier=HardwareTier.BUDGET_GPU,
        estimated_quality_at_minimum=0.65,
        estimated_quality_at_standard=0.92,
        exists_currently=False,
        priority_score=80,
    ),
    SpecializationDomain.BUG_LOCALIZATION: SpecializationSpec(
        domain="Bug Localization — Given a bug report, identify the file and line likely causing it",
        required_model_size="7B",
        required_context_tokens=16384,
        required_tools=["read_file", "grep_search", "git_log", "inspect_ast", "run_test"],
        training_data_needs="Bug descriptions mapped to commit-level fixes with file/line annotations",
        benchmark_criteria=["top_1_accuracy", "top_5_accuracy", "mean_reciprocal_rank", "latency"],
        hardware_cost_tier=HardwareTier.STANDARD_GPU,
        estimated_quality_at_minimum=0.40,
        estimated_quality_at_standard=0.70,
        exists_currently=False,
        priority_score=70,
    ),
    SpecializationDomain.SAFE_SMALL_EDITS: SpecializationSpec(
        domain="Safe Small Edits — Generate bounded, verified single-file edits with rollback",
        required_model_size="3B",
        required_context_tokens=8192,
        required_tools=["read_file", "edit_file", "verify_change", "run_test", "think"],
        training_data_needs="Single-file edit tasks with before/after patches and test results",
        benchmark_criteria=["edit_correctness", "syntax_preservation", "test_pass_rate", "rollback_rate"],
        hardware_cost_tier=HardwareTier.BUDGET_GPU,
        estimated_quality_at_minimum=0.55,
        estimated_quality_at_standard=0.80,
        exists_currently=False,
        priority_score=85,
    ),
    SpecializationDomain.SEMANTIC_DIFF_EXPLANATION: SpecializationSpec(
        domain="Semantic Diff Explanation — Given a diff, classify the semantic nature of each change",
        required_model_size="1.5B",
        required_context_tokens=4096,
        required_tools=["read_file", "inspect_ast", "think"],
        training_data_needs="Diff pairs with semantic labels: refactor, behavior, dependency, cosmetic, fix",
        benchmark_criteria=["classification_accuracy", "change_boundary_detection", "false_positive_rate"],
        hardware_cost_tier=HardwareTier.CPU_ONLY,
        estimated_quality_at_minimum=0.65,
        estimated_quality_at_standard=0.88,
        exists_currently=False,
        priority_score=60,
    ),
    SpecializationDomain.TOOL_USE_ROUTING: SpecializationSpec(
        domain="Tool-Use Routing — Given a task state, decide which tool to call next and with what parameters",
        required_model_size="7B",
        required_context_tokens=4096,
        required_tools=["all tools — router decides which to call"],
        training_data_needs="Trajectories: state sequences with correct tool choices at each step",
        benchmark_criteria=["tool_selection_accuracy", "parameter_correctness", "efficiency", "recovery"],
        hardware_cost_tier=HardwareTier.STANDARD_GPU,
        estimated_quality_at_minimum=0.50,
        estimated_quality_at_standard=0.78,
        exists_currently=False,
        priority_score=65,
    ),
    SpecializationDomain.PATCH_CRITICISM: SpecializationSpec(
        domain="Patch Criticism — Given a patch and context, identify issues: correctness, style, edge cases, regressions",
        required_model_size="7B",
        required_context_tokens=16384,
        required_tools=["read_file", "grep_search", "think", "run_test", "inspect_ast"],
        training_data_needs="Patch pairs (good/bad) with annotated issues per patch hunk",
        benchmark_criteria=["issue_detection_rate", "false_positive_rate", "severity_calibration"],
        hardware_cost_tier=HardwareTier.STANDARD_GPU,
        estimated_quality_at_minimum=0.45,
        estimated_quality_at_standard=0.75,
        exists_currently=True,
        priority_score=75,
    ),
    SpecializationDomain.VERIFICATION_PLANNING: SpecializationSpec(
        domain="Verification Planning — Given a change, select the cheapest verification that gives meaningful confidence",
        required_model_size="3B",
        required_context_tokens=4096,
        required_tools=["think", "run_test"],
        training_data_needs="Edit + verification outcome pairs: what verification caught what failure",
        benchmark_criteria=["verification_efficiency", "missed_failures", "cost_vs_confidence_tradeoff"],
        hardware_cost_tier=HardwareTier.BUDGET_GPU,
        estimated_quality_at_minimum=0.60,
        estimated_quality_at_standard=0.82,
        exists_currently=True,
        priority_score=70,
    ),
}


TOP_3_SPECIALIZATIONS = [
    SpecializationDomain.PATCH_PLANNING,
    SpecializationDomain.REPO_QA,
    SpecializationDomain.SAFE_SMALL_EDITS,
]


TOP_3_RATIONALE = """
Top 3 Specializations for Lyme Model:

1. Patch Planning (score: 90)
   - Why: Planning before acting prevents the most common failure of weak local models
     (hallucinated edits, wrong files, cascading errors). Every coding task benefits
     from planning. Existing PatchPlanner provides foundation.
   - Required: 3B model, 8K context, budget GPU
   - Benchmark: plan acceptance rate, missed dependencies

2. Repo Q&A (score: 95)
   - Why: Already hardened at 94% parity (Week 113). Lowest barrier to entry, highest
     reliability. Foundation that all other specialists depend on for context gathering.
   - Required: 1.5B model, 4K context, CPU-only possible
   - Benchmark: answer correctness, hallucination rate

3. Safe Small Edits (score: 85)
   - Why: The most concrete deliverable — bounded single-file edits with verification
     and rollback. Directly useful, low risk, high value. Complements Patch Planning.
   - Required: 3B model, 8K context, budget GPU
   - Benchmark: edit correctness, test pass rate
"""


SPECIALIZATION_STRATEGY = {
    "principle": "Do not make one local model good at everything. Build specialists that excel at narrow capabilities.",
    "rationale": (
        "Local models (1.5B–7B) lack the capacity for generalist coding. "
        "Specialization trades generality for reliability within a bounded domain. "
        "Each specialist has a narrow input schema, bounded output, cheap verification, "
        "and clear failure mode. Specialists coordinate via a shared blackboard state."
    ),
    "specializations": {
        s.domain: {
            "model_size": s.required_model_size,
            "context": s.required_context_tokens,
            "tier": s.hardware_cost_tier.value,
            "quality_min": s.estimated_quality_at_minimum,
            "quality_std": s.estimated_quality_at_standard,
            "exists": s.exists_currently,
        }
        for s in SPECIALIZATIONS.values()
    },
    "top_3": [s.domain for s in [SPECIALIZATIONS[d] for d in TOP_3_SPECIALIZATIONS]],
    "top_3_rationale": TOP_3_RATIONALE.strip(),
    "lyme_audit_status": "untouched",
    "recommendations": [
        "Build Planner, Retriever, Patch Generator, Critic, Verifier specialists (Weeks 135-139)",
        "Route all specialist outputs through Lyme Audit for traceability",
        "Do NOT merge specialists — keep them as independent modules that coordinate",
        "Start with prompt-based specialists, adapt with data later (Weeks 146-147)",
        "The 3 most important specialists are: Planner, Retriever, Patch Generator",
    ],
}
