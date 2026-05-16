"""Week 134 — Specialist Model Interfaces.

Each specialist has:
- input schema
- output schema
- confidence score
- failure labels
- allowed tools
- required verification
- audit trace format

All specialist outputs flow into Lyme Audit.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
from datetime import datetime, timezone
import json


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"        # 0.0-0.2: refuse, ask for help
    LOW = "low"                  # 0.2-0.4: require human review
    MEDIUM = "medium"            # 0.4-0.7: require verification
    HIGH = "high"                # 0.7-0.9: accept with verification
    VERY_HIGH = "very_high"      # 0.9-1.0: accept, light verification


class FailureLabel(Enum):
    AMBIGUOUS_INPUT = "ambiguous_input"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    OUT_OF_SCOPE = "out_of_scope"
    HALLUCINATED_EVIDENCE = "hallucinated_evidence"
    MISSING_DEPENDENCY = "missing_dependency"
    VERIFICATION_FAILED = "verification_failed"
    RISK_TOO_HIGH = "risk_too_high"
    MODEL_TOO_WEAK = "model_too_weak"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"
    CONFLICT_DETECTED = "conflict_detected"


class AuditTrace:
    """Standard audit trace for every specialist action."""

    def __init__(self, specialist: str, trace_id: str):
        self.specialist = specialist
        self.trace_id = trace_id
        self.steps: List[dict] = []
        self.decisions: List[dict] = []
        self.start_time = datetime.now(timezone.utc).isoformat()

    def add_step(self, description: str, detail: dict):
        self.steps.append({
            "step": len(self.steps) + 1,
            "description": description,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_decision(self, decision: str, rationale: str, alternatives: List[str]):
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "alternatives": alternatives,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "specialist": self.specialist,
            "trace_id": self.trace_id,
            "steps": self.steps,
            "decisions": self.decisions,
            "start_time": self.start_time,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Planner Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlannerInput:
    user_task: str
    repo_summary: Optional[str] = None
    relevant_constraints: List[str] = field(default_factory=list)
    hardware_profile: str = "standard_gpu"
    available_models: List[str] = field(default_factory=lambda: ["qwen2.5-coder-7b"])
    prior_failures: List[str] = field(default_factory=list)


@dataclass
class PlannerOutput:
    task_decomposition: List[dict]       # [{name, description, files, risk}]
    affected_files: List[str]
    context_needs: List[str]
    risk_score: float                    # 0.0-1.0
    recommended_mode: str                # local_fast, local_careful, etc.
    recommended_model: str
    verification_strategy: List[str]
    stop_conditions: List[str]
    confidence: float
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "planner",
            "task_decomposition": self.task_decomposition,
            "affected_files": self.affected_files,
            "context_needs": self.context_needs,
            "risk_score": self.risk_score,
            "recommended_mode": self.recommended_mode,
            "recommended_model": self.recommended_model,
            "verification_strategy": self.verification_strategy,
            "stop_conditions": self.stop_conditions,
            "confidence": self.confidence,
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


PLANNER_INTERFACE = {
    "name": "Planner",
    "input_schema": "PlannerInput(user_task, repo_summary, constraints, hardware, available_models, prior_failures)",
    "output_schema": "PlannerOutput(task_decomposition, affected_files, context_needs, risk_score, mode, model, verification, stop_conditions, confidence)",
    "confidence": "0.0-1.0 based on task clarity + hardware adequacy + prior success",
    "failure_labels": ["ambiguous_input", "out_of_scope", "risk_too_high", "insufficient_context"],
    "allowed_tools": ["think", "grep_search", "list_directory", "read_file"],
    "required_verification": "Plan validation (files exist, dependencies satisfiable, risk within threshold)",
    "audit_format": "AuditTrace(specialist='planner', steps=[decomposition, risk_assessment, mode_selection], decisions=[mode choice, model choice])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Retriever Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetrieverInput:
    task: str
    affected_files_hint: List[str] = field(default_factory=list)
    target_context_tokens: int = 4096
    retrieval_policy: str = "hybrid"
    repo_path: str = "."


@dataclass
class RetrieverOutput:
    selected_files: List[dict]           # [{path, relevance_score, content_summary}]
    selected_symbols: List[dict]         # [{name, type, file, signature}]
    relevant_tests: List[str]
    git_history: List[str]
    prior_memories: List[dict]
    risk_zones: List[str]
    context_size_tokens: int
    missing_context_rate: float          # 0.0-1.0, 0 = nothing missing
    irrelevant_context_rate: float       # 0.0-1.0, 0 = everything relevant
    confidence: float
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "retriever",
            "selected_files": [{"path": f["path"], "score": round(f.get("relevance_score", 0), 3)} for f in self.selected_files],
            "selected_symbols": self.selected_symbols,
            "context_size_tokens": self.context_size_tokens,
            "missing_context_rate": self.missing_context_rate,
            "irrelevant_context_rate": self.irrelevant_context_rate,
            "confidence": self.confidence,
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


RETRIEVER_INTERFACE = {
    "name": "Retriever",
    "input_schema": "RetrieverInput(task, affected_files_hint, target_context_tokens, retrieval_policy, repo_path)",
    "output_schema": "RetrieverOutput(selected_files, selected_symbols, relevant_tests, git_history, prior_memories, risk_zones, context_size, missing_rate, irrelevant_rate, confidence)",
    "confidence": "0.0-1.0 based on coverage estimate (low missing rate = high confidence)",
    "failure_labels": ["insufficient_context", "ambiguous_input", "timeout"],
    "allowed_tools": ["grep_search", "read_file", "list_directory", "git_log", "inspect_ast"],
    "required_verification": "File existence check, symbol verification, context budget check",
    "audit_format": "AuditTrace(specialist='retriever', steps=[policy_selection, file_search, symbol_extraction, context_budget], decisions=[policy_choice, inclusion_threshold])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Patch Generator Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PatchGeneratorInput:
    validated_plan: dict
    affected_files: List[str]
    context_packet: dict
    verification_command: str
    rollback_path: str
    max_edit_size_lines: int = 50


@dataclass
class PatchGeneratorOutput:
    patch: str                           # unified diff format
    rationale: str
    expected_test_impact: List[str]
    confidence: float
    patch_size_lines: int
    files_modified: List[str]
    rollback_available: bool
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "patch_generator",
            "patch_size_lines": self.patch_size_lines,
            "files_modified": self.files_modified,
            "expected_test_impact": self.expected_test_impact,
            "confidence": self.confidence,
            "rollback_available": self.rollback_available,
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


PATCH_GENERATOR_INTERFACE = {
    "name": "Patch Generator",
    "input_schema": "PatchGeneratorInput(validated_plan, affected_files, context_packet, verification_command, rollback_path, max_edit_size)",
    "output_schema": "PatchGeneratorOutput(patch, rationale, expected_test_impact, confidence, patch_size, files_modified, rollback)",
    "confidence": "0.0-1.0 based on plan quality + context completeness + test coverage",
    "failure_labels": ["verification_failed", "hallucinated_evidence", "risk_too_high", "model_too_weak"],
    "allowed_tools": ["read_file", "edit_file", "inspect_ast", "write_file"],
    "required_verification": "Syntax check, file existence, patch format validity, test pass (if available)",
    "audit_format": "AuditTrace(specialist='patch_generator', steps=[patch_draft, format_check, size_check], decisions=[edit_boundary, rollback_strategy])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Critic Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CriticInput:
    patch_plan: Optional[dict] = None
    generated_patch: Optional[str] = None
    affected_files: List[str] = field(default_factory=list)
    claims: List[dict] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    verification_completeness: dict = field(default_factory=dict)


@dataclass
class CriticOutput:
    decision: Literal["approve", "reject", "revise", "ask_more_context", "require_stronger_model", "require_human"]
    issues: List[dict]                     # [{severity, file, line, description}]
    revision_suggestions: List[str]
    missing_verification: List[str]
    confidence: float
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "critic",
            "decision": self.decision,
            "issue_count": len(self.issues),
            "revision_suggestions": self.revision_suggestions[:3],
            "missing_verification": self.missing_verification,
            "confidence": self.confidence,
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


CRITIC_INTERFACE = {
    "name": "Critic",
    "input_schema": "CriticInput(patch_plan, generated_patch, affected_files, claims, imports, verification_completeness)",
    "output_schema": "CriticOutput(decision, issues, revision_suggestions, missing_verification, confidence)",
    "confidence": "0.0-1.0 based on coverage of review dimensions",
    "failure_labels": ["ambiguous_input", "insufficient_context", "internal_error"],
    "allowed_tools": ["read_file", "grep_search", "think", "inspect_ast", "git_log"],
    "required_verification": "Cross-check each issue against actual file content",
    "audit_format": "AuditTrace(specialist='critic', steps=[plan_review, patch_review, claim_check, import_check, verification_check], decisions=[final_decision])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Verifier Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VerifierInput:
    change: dict
    repo_path: str = "."
    available_verifiers: List[str] = field(default_factory=lambda: ["syntax", "type_check", "unit_tests", "targeted_tests", "full_tests", "static_analysis", "semantic_diff"])
    max_verification_cost: str = "medium"  # cheap, medium, full
    required_confidence: float = 0.8


@dataclass
class VerifierOutput:
    selected_verifiers: List[str]
    results: List[dict]                    # [{verifier, passed, detail, latency_ms, cost}]
    overall_pass: bool
    confidence_after: float
    cheapest_meaningful_verifier: str
    recommended_actions: List[str]
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "verifier",
            "selected_verifiers": self.selected_verifiers,
            "overall_pass": self.overall_pass,
            "confidence_after": self.confidence_after,
            "cheapest": self.cheapest_meaningful_verifier,
            "results": [{"name": r["verifier"], "passed": r["passed"], "latency_ms": r.get("latency_ms", 0)} for r in self.results],
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


VERIFIER_INTERFACE = {
    "name": "Verifier",
    "input_schema": "VerifierInput(change, repo_path, available_verifiers, max_verification_cost, required_confidence)",
    "output_schema": "VerifierOutput(selected_verifiers, results, overall_pass, confidence_after, cheapest_meaningful, recommended_actions)",
    "confidence": "0.0-1.0 based on verification coverage and pass rate",
    "failure_labels": ["verification_failed", "timeout", "internal_error"],
    "allowed_tools": ["run_test", "inspect_ast"],
    "required_verification": "Self-check: did selected verifiers actually run and produce output?",
    "audit_format": "AuditTrace(specialist='verifier', steps=[verifier_selection, execution, result_evaluation], decisions=[which_verifiers, pass/fail threshold])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Summarizer Specialist Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SummarizerInput:
    task: str
    specialist_results: List[dict]       # outputs from each specialist
    verification_results: List[dict]
    audit_traces: List[dict]
    latency_data: dict


@dataclass
class SummarizerOutput:
    summary: str
    success: bool
    key_decisions: List[str]
    confidence: float
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "summarizer",
            "success": self.success,
            "confidence": self.confidence,
            "key_decisions": self.key_decisions[:5],
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


SUMMARIZER_INTERFACE = {
    "name": "Summarizer",
    "input_schema": "SummarizerInput(task, specialist_results, verification_results, audit_traces, latency_data)",
    "output_schema": "SummarizerOutput(summary, success, key_decisions, confidence)",
    "confidence": "0.0-1.0 based on consistency across specialist outputs",
    "failure_labels": ["ambiguous_input", "internal_error"],
    "allowed_tools": ["think"],
    "required_verification": "Cross-check summary against each specialist result for factual accuracy",
    "audit_format": "AuditTrace(specialist='summarizer', steps=[result_aggregation, coherence_check, summary_writing], decisions=[success determination])",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Refusal/Uncertainty Detector Interfaces
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RefusalInput:
    task: str
    planner_output: Optional[PlannerOutput] = None
    retriever_output: Optional[RetrieverOutput] = None
    hardware_profile: str = "standard_gpu"
    model: str = "qwen2.5-coder-7b"
    prior_failure_count: int = 0
    confidence_threshold: float = 0.3


@dataclass
class RefusalOutput:
    should_refuse: bool
    reason: str
    refusal_category: Literal["confidence_too_low", "risk_too_high", "hardware_insufficient", "out_of_scope", "model_too_weak", "prior_failures_exceeded"]
    suggested_action: str               # ask user, switch model, simplify task, etc.
    confidence: float
    failure_label: Optional[FailureLabel] = None
    trace: Optional[AuditTrace] = None

    def to_dict(self) -> dict:
        return {
            "specialist": "refusal_detector",
            "should_refuse": self.should_refuse,
            "reason": self.reason,
            "refusal_category": self.refusal_category,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "failure_label": self.failure_label.value if self.failure_label else None,
        }


REFUSAL_INTERFACE = {
    "name": "Refusal/Uncertainty Detector",
    "input_schema": "RefusalInput(task, planner_output, retriever_output, hardware_profile, model, prior_failure_count, confidence_threshold)",
    "output_schema": "RefusalOutput(should_refuse, reason, refusal_category, suggested_action, confidence)",
    "confidence": "0.0-1.0 based on clarity of risk/confidence signals",
    "failure_labels": ["ambiguous_input"],
    "allowed_tools": ["think"],
    "required_verification": "Check: did refusal grounds match actual input? Check: is suggested action valid?",
    "audit_format": "AuditTrace(specialist='refusal_detector', steps=[risk_eval, confidence_eval, category_check], decisions=[refuse/allow])",
}


ALL_SPECIALIST_INTERFACES = {
    "planner": PLANNER_INTERFACE,
    "retriever": RETRIEVER_INTERFACE,
    "patch_generator": PATCH_GENERATOR_INTERFACE,
    "critic": CRITIC_INTERFACE,
    "verifier": VERIFIER_INTERFACE,
    "summarizer": SUMMARIZER_INTERFACE,
    "refusal_detector": REFUSAL_INTERFACE,
}


def specialist_output_to_audit(interface_name: str, output: dict) -> dict:
    """Format any specialist output into a standardized audit entry."""
    return {
        "specialist": interface_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "v0.8",
        "output": output,
        "audit_format_version": "1.0",
    }
