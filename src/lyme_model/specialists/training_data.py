"""Week 146 — Specialist Training Data.

Generate training data for each specialist.
Each example includes: input, ideal output, evidence, failure traps, verification result.
Trace every dataset item back to Lyme Audit.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
import time
import uuid


@dataclass
class TrainingExample:
    example_id: str
    specialist: str
    input_data: dict
    ideal_output: dict
    evidence: List[str]
    failure_traps: List[str]
    verification_result: dict
    audit_trace_id: str
    difficulty: float = 0.5

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "specialist": self.specialist,
            "input_summary": {k: str(v)[:80] for k, v in self.input_data.items()},
            "ideal_output_summary": {k: str(v)[:80] for k, v in self.ideal_output.items()},
            "evidence_count": len(self.evidence),
            "failure_traps": self.failure_traps,
            "verification_result": self.verification_result,
            "audit_trace_id": self.audit_trace_id,
            "difficulty": self.difficulty,
        }


class TrainingDataGenerator:
    """Generate training data for each specialist."""

    def __init__(self):
        self._examples: List[TrainingExample] = []

    def generate_all(self) -> Dict[str, List[TrainingExample]]:
        return {
            "planner": self._generate_planner_examples(),
            "retriever": self._generate_retriever_examples(),
            "patch_generator": self._generate_patch_examples(),
            "critic": self._generate_critic_examples(),
            "verifier": self._generate_verifier_examples(),
            "router": self._generate_router_examples(),
        }

    def _make_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def _make_trace(self, specialist: str) -> str:
        return f"audit-trace-{specialist}-{int(time.time())}"

    def _generate_planner_examples(self) -> List[TrainingExample]:
        examples = [
            TrainingExample(
                example_id=self._make_id(),
                specialist="planner",
                input_data={
                    "task": "Fix the authentication bug in login handler",
                    "repo_summary": "Python Flask app with JWT auth",
                    "constraints": ["single file change", "must pass existing tests"],
                },
                ideal_output={
                    "task_decomposition": [
                        {"name": "Investigate auth handler", "files": ["src/auth.py"]},
                        {"name": "Plan fix", "dependencies": ["Investigate"]},
                        {"name": "Apply fix", "dependencies": ["Plan fix"]},
                        {"name": "Verify fix", "dependencies": ["Apply fix"]},
                    ],
                    "affected_files": ["src/auth.py", "tests/test_auth.py"],
                    "risk_score": 0.4,
                    "recommended_mode": "local_careful",
                },
                evidence=["Auth bug pattern: missing null check in JWT decode",
                          "Test pattern: test_login_invalid_token fails with AttributeError"],
                failure_traps=["Try to fix all auth bugs at once instead of one",
                               "Edit multiple files without verification"],
                verification_result={"passed": True, "verifiers": ["plan_valid", "file_existence"]},
                audit_trace_id=self._make_trace("planner"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="planner",
                input_data={
                    "task": "Add pagination to list_users endpoint",
                    "constraints": ["multi-file change", "backward compatible"],
                    "hardware": "standard_gpu",
                },
                ideal_output={
                    "task_decomposition": [
                        {"name": "Read current endpoint", "files": ["src/routes.py"]},
                        {"name": "Plan pagination params", "dependencies": ["Read"]},
                        {"name": "Add pagination logic", "dependencies": ["Plan"]},
                        {"name": "Update tests", "dependencies": ["Add"]},
                    ],
                    "affected_files": ["src/routes.py", "src/service.py", "tests/test_routes.py"],
                    "risk_score": 0.5,
                    "recommended_mode": "local_with_critic",
                },
                evidence=["Pagination pattern: existing sort_by and limit params in service layer",
                          "Test pattern: test_list_users_pagination exists but empty"],
                failure_traps=["Forget to add offset validation", "Break existing no-pagination behavior"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("planner"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="planner",
                input_data={
                    "task": "What language is this project written in?",
                    "constraints": [],
                },
                ideal_output={
                    "task_decomposition": [{"name": "Check project files", "files": ["setup.py", "pyproject.toml"]}],
                    "affected_files": ["setup.py", "pyproject.toml"],
                    "risk_score": 0.0,
                    "recommended_mode": "local_fast",
                },
                evidence=["Repo Q&A tasks require minimal effort"],
                failure_traps=["Overcomplicate a simple lookup"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("planner"),
                difficulty=0.1,
            ),
        ]
        self._examples.extend(examples)
        return examples

    def _generate_retriever_examples(self) -> List[TrainingExample]:
        return [
            TrainingExample(
                example_id=self._make_id(),
                specialist="retriever",
                input_data={"task": "Find the login handler function", "target_tokens": 4096},
                ideal_output={
                    "selected_files": [{"path": "src/auth.py", "relevance_score": 0.95}],
                    "selected_symbols": [{"name": "login", "type": "function", "file": "src/auth.py"}],
                    "missing_context_rate": 0.0,
                    "irrelevant_context_rate": 0.0,
                },
                evidence=["login function is in src/auth.py"],
                failure_traps=["Return too many files", "Miss the key file"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("retriever"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="retriever",
                input_data={"task": "How is the database connection configured?", "target_tokens": 4096},
                ideal_output={
                    "selected_files": [{"path": "src/config.py", "relevance_score": 0.9}],
                    "selected_symbols": [{"name": "get_db", "type": "function", "file": "src/database.py"}],
                    "missing_context_rate": 0.0,
                    "irrelevant_context_rate": 0.1,
                },
                evidence=["DB config in src/config.py, connection function in src/database.py"],
                failure_traps=["Only return config file, miss connection function"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("retriever"),
            ),
        ]

    def _generate_patch_examples(self) -> List[TrainingExample]:
        return [
            TrainingExample(
                example_id=self._make_id(),
                specialist="patch_generator",
                input_data={
                    "plan": {"affected_files": ["src/auth.py"], "intended_change": "Add null check to JWT decode"},
                    "verification_command": "pytest tests/test_auth.py",
                    "rollback_path": "git checkout HEAD -- src/auth.py",
                },
                ideal_output={
                    "patch": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -42,6 +42,8 @@\n+if token is None:\n+    return None\n",
                    "patch_size_lines": 3,
                    "confidence": 0.85,
                    "rollback_available": True,
                },
                evidence=["Null token causes AttributeError in line 42"],
                failure_traps=["Return entire file instead of minimal diff", "Forget rollback path"],
                verification_result={"passed": True, "syntax_ok": True},
                audit_trace_id=self._make_trace("patch_generator"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="patch_generator",
                input_data={
                    "plan": {"affected_files": ["src/routes.py"], "intended_change": "Add sort parameter"},
                    "verification_command": "",
                },
                ideal_output={},
                evidence=["Missing verification command is a common failure trap"],
                failure_traps=["Generate patch without verification command"],
                verification_result={"passed": False, "reason": "No verification command"},
                audit_trace_id=self._make_trace("patch_generator"),
                difficulty=0.3,
            ),
        ]

    def _generate_critic_examples(self) -> List[TrainingExample]:
        return [
            TrainingExample(
                example_id=self._make_id(),
                specialist="critic",
                input_data={
                    "patch_plan": {"affected_files": ["src/auth.py"], "intended_change": "Fix auth bug"},
                    "generated_patch": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1 +1 @@\n-fixed",
                    "affected_files": ["src/auth.py"],
                },
                ideal_output={
                    "decision": "revise",
                    "issues": [
                        {"severity": "warning", "description": "Patch has no diff context"},
                        {"severity": "info", "description": "No test references in patch"},
                    ],
                    "revision_suggestions": ["Add proper diff format with line numbers"],
                },
                evidence=["Patch format is incomplete"],
                failure_traps=["Miss patch format issues", "Over-criticize valid patches"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("critic"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="critic",
                input_data={
                    "claims": [{"statement": "The bug is in auth.py", "citations": []}],
                    "imports": ["nonexistent_module"],
                    "affected_files": ["src/auth.py"],
                },
                ideal_output={
                    "decision": "require_more_context",
                    "issues": [
                        {"severity": "warning", "description": "Claim has no citations"},
                        {"severity": "warning", "description": "Import may not resolve: nonexistent_module"},
                    ],
                },
                evidence=["Claims without citations are unreliable"],
                failure_traps=["Ignore unsupported claims"],
                verification_result={"passed": False, "reason": "Unsupported claims found"},
                audit_trace_id=self._make_trace("critic"),
                difficulty=0.6,
            ),
        ]

    def _generate_verifier_examples(self) -> List[TrainingExample]:
        return [
            TrainingExample(
                example_id=self._make_id(),
                specialist="verifier",
                input_data={"files": ["src/main.py"], "max_cost": "medium", "required_confidence": 0.7},
                ideal_output={
                    "selected_verifiers": ["syntax", "file_existence", "type_check", "unit_tests"],
                    "all_passed": True,
                    "cheapest_meaningful": "type_check",
                },
                evidence=["Type check is cheapest verifier that gives >0.5 confidence"],
                failure_traps=["Run full test suite for every change", "Skip type checking"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("verifier"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="verifier",
                input_data={"files": ["src/nonexistent.py"], "max_cost": "cheap"},
                ideal_output={"overall_pass": False},
                evidence=["File existence check catches missing files at low cost"],
                failure_traps=["Skip file existence check"],
                verification_result={"passed": False, "reason": "File not found"},
                audit_trace_id=self._make_trace("verifier"),
                difficulty=0.2,
            ),
        ]

    def _generate_router_examples(self) -> List[TrainingExample]:
        return [
            TrainingExample(
                example_id=self._make_id(),
                specialist="router",
                input_data={"current_phase": "critique", "errors": [], "confidences": {"critic": 0.8}},
                ideal_output={"decision": "continue", "next": "verifier"},
                evidence=["Standard pipeline progression"],
                failure_traps=["Loop unnecessarily", "Skip verification"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("router"),
            ),
            TrainingExample(
                example_id=self._make_id(),
                specialist="router",
                input_data={"current_phase": "generate_patch", "errors": [{"specialist": "patch_generator", "error": "validation failed"}]},
                ideal_output={"decision": "retry", "next": "patch_generator"},
                evidence=["Single failure should trigger retry"],
                failure_traps=["Escalate immediately on first error", "Silently skip failed step"],
                verification_result={"passed": True},
                audit_trace_id=self._make_trace("router"),
                difficulty=0.4,
            ),
        ]

    def save_to_json(self, path: str):
        all_data = self.generate_all()
        output = {}
        for specialist, examples in all_data.items():
            output[specialist] = [e.to_dict() for e in examples]
        import json
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
        return output

    def get_statistics(self) -> dict:
        all_data = self.generate_all()
        total = sum(len(examples) for examples in all_data.values())
        return {
            "total_examples": total,
            "per_specialist": {s: len(e) for s, e in all_data.items()},
            "avg_difficulty": round(
                sum(e.difficulty for examples in all_data.values() for e in examples) / total, 2
            ) if total > 0 else 0,
        }


generator = TrainingDataGenerator()
