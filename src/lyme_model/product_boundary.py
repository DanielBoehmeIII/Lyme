"""Week 151 — Local Coding Agent Product Boundary.

Define what Lyme Model should and should not do as a product.
"""

from __future__ import annotations
from typing import Dict, List


PRODUCT_BOUNDARY = {
    "version": "0.9.0",
    "theme": "coordinated specialist architecture — product boundary",
    "lyme_audit_status": "untouched",
}

# Strong claims — evidence-supported
STRONG_CLAIMS = {
    "evidence_grounded_repo_qa": {
        "claim": "Answer questions about repository structure, APIs, dependencies, and conventions",
        "evidence": "94% parity on Repo Q&A (Week 113). Hardened slice with 25 benchmark tasks.",
        "limitation": "Structural Q&A only. Cannot evaluate design quality or predict runtime behavior.",
        "all_hardware": True,
    },
    "safe_patch_planning": {
        "claim": "Produce validated edit plans before writing code, reducing hallucinated edits",
        "evidence": "Plan-then-patch strategy prevents edits to wrong files. Validator checks existence, dependencies.",
        "limitation": "Plan quality depends on task clarity. Ambiguous tasks produce weak plans.",
        "all_hardware": True,
    },
    "bounded_small_fixes": {
        "claim": "Generate small, bounded single-file patches with verification and rollback",
        "evidence": "Patch Generator specialist requires validated plan, verification command, rollback path.",
        "limitation": "Max 50 lines per patch. Multi-file or cross-module changes require human review.",
        "all_hardware": False,
        "minimum_hardware": "budget_gpu",
    },
    "test_failure_explanation": {
        "claim": "Explain why a test failure occurs with line-level code evidence",
        "evidence": "92% accuracy in controlled evaluation (Week 114). Uses AST + git history + test output.",
        "limitation": "Requires test output as input. Cannot infer failures from test name alone.",
        "all_hardware": True,
    },
    "semantic_diff_explanation": {
        "claim": "Classify diffs into semantic categories: refactor, behavior change, dependency, cosmetic",
        "evidence": "AST-based diff analysis with pattern classification.",
        "limitation": "Best effort classification. Subtle semantic changes may be misclassified.",
        "all_hardware": True,
    },
}

# Claims requiring proof — not yet ready to assert
REQUIRING_PROOF = {
    "autonomous_coding": {
        "claim": "Autonomous multi-file feature implementation without human guidance",
        "status": "Not proven. Current autonomy loop handles <3 files, <50 lines, with verification.",
        "gap": "Long-horizon context drift, goal forgetting, cascading errors at >4 subtasks.",
    },
    "claude_codex_parity": {
        "claim": "Match Claude Code or Codex on general coding tasks",
        "status": "Not proven. Lyme Model is specialized for narrow tasks, not general coding.",
        "gap": "Model size difference (7B vs 70B+). No general knowledge. Specialized not general.",
    },
    "long_horizon_feature_building": {
        "claim": "Build features requiring 10+ files over 30+ minute coding sessions",
        "status": "Not proven. Maximum safe scope is 3 files, 4 subtasks, 3 edits.",
        "gap": "Context drift begins at subtask 3-4. Goal forgetting at subtask 5+.",
    },
    "self_improvement": {
        "claim": "Improve from own mistakes without human feedback",
        "status": "Not proven. Audit data is collected but not used for automated improvement loops.",
        "gap": "No automated feedback pipeline from audit to training data.",
    },
    "cross_repo_generality": {
        "claim": "Work equally well on any repository in any language",
        "status": "Not proven. Currently optimized for Python/TS repos with standard tooling.",
        "gap": "No language-agnostic compression. No cross-repo memory.",
    },
}

# What Lyme Model should NOT try to do
OUT_OF_SCOPE = [
    "Replace human code review",
    "Make architectural design decisions",
    "Predict runtime performance or security vulnerabilities",
    "Write production-ready code without human verification",
    "Handle sensitive data or credentials",
    "Provide timeline estimates or project management",
    "Replace testing infrastructure",
    "Guarantee zero-bug patches",
]


def get_claim_policy() -> dict:
    return {
        "allowed_strong_claims": list(STRONG_CLAIMS.keys()),
        "claims_requiring_proof": list(REQUIRING_PROOF.keys()),
        "out_of_scope": OUT_OF_SCOPE,
        "policy": (
            "Lyme Model claims must be evidence-grounded, bounded, hardware-aware, and honest. "
            "Every claim must cite the specific week, benchmark, or experiment that supports it. "
            "Claims without supporting evidence are explicitly labeled as 'requiring proof'."
        ),
    }


def get_demo_script() -> list:
    return [
        {"step": 1, "action": "Show Repo Q&A", "example": "Ask 'What framework does this project use?'"},
        {"step": 2, "action": "Show Patch Planning", "example": "Plan a fix for a specific bug with affected files"},
        {"step": 3, "action": "Show Specialist Pipeline", "example": "Run orchestrator on a small fix task"},
        {"step": 4, "action": "Show Verification", "example": "Cheapest verification that would catch the bug"},
        {"step": 5, "action": "Show Tradeoff", "example": "Compare fast vs careful vs specialist mode on same task"},
        {"step": 6, "action": "Show Product Boundary", "example": "Explicitly state what Lyme Model cannot do"},
    ]


boundary = PRODUCT_BOUNDARY
