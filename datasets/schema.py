"""Lyme Model — Canonical Dataset Schema v2

Defines the canonical JSONL format for all training modalities.
v2 expands from 8 to 11 modalities with new fields for patches, traces, and candidates.

Modalities:
- repo_qa: Evidence-grounded repository Q&A
- bug_localization: Find bug location from symptoms
- patch_planning: Structured edit plan before code change
- unified_diff: Minimal valid unified diff generation
- test_repair: Fix failing tests
- tool_use: Agentic tool selection sequences
- verification: Approve/reject/revise patch evaluation
- refusal: Appropriate refusal behavior
- debugging_trace: Full debugging trace with decisions
- patch_critique: Evaluate and rank candidate patches
- self_repair: Fix own patch after test failure
- multi_file_edit: Coordinated edits across 2-5 files
- long_horizon_planning: Multi-step task planning and execution
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import re


VALID_MODALITIES = [
    "repo_qa",
    "bug_localization",
    "patch_planning",
    "unified_diff",
    "test_repair",
    "tool_use",
    "verification",
    "refusal",
    "debugging_trace",
    "patch_critique",
    "self_repair",
    "multi_file_edit",
    "long_horizon_planning",
]

VALID_DIFFICULTIES = ["trivial", "easy", "medium", "hard", "expert"]
VALID_SOURCES = ["synthetic", "lyme_trace", "curated", "augmented", "distilled", "mined"]

SECRET_PATTERNS = [
    r'(?i)(password|secret|api_key|apikey|token|credential)\s*[:=]\s*["\']?[^\s"\']{8,}["\']?',
    r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
    r'(?i)(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36}',
]


@dataclass
class RepoContext:
    """Repository context for a training example."""
    repo_name: str = ""
    language: str = ""
    framework: str = ""
    file_count: int = 0
    total_lines: int = 0
    test_count: int = 0
    test_framework: str = ""
    architecture_summary: str = ""
    conventions: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        errors = []
        if not self.repo_name:
            errors.append("repo_name is required")
        if not self.language:
            errors.append("language is required")
        return errors


@dataclass
class RetrievedFile:
    """A file retrieved as context for the task."""
    file_path: str = ""
    role: str = ""  # source, test, config, docs
    content_preview: str = ""
    lines: int = 0
    relevance_score: float = 1.0

    def validate(self) -> List[str]:
        errors = []
        if not self.file_path:
            errors.append("file_path is required")
        if self.relevance_score < 0 or self.relevance_score > 1:
            errors.append("relevance_score must be between 0 and 1")
        return errors


@dataclass
class ToolOutput:
    """A tool call and its output, used in tool-use traces."""
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    success: bool = True
    latency_ms: float = 0.0

    def validate(self) -> List[str]:
        errors = []
        if not self.tool_name:
            errors.append("tool_name is required")
        return errors


@dataclass
class PatchCandidate:
    """A candidate patch for critique/ranking scenarios."""
    patch_id: str = ""
    patch_diff: str = ""
    score: float = 0.0
    issues: List[str] = field(default_factory=list)
    explanation: str = ""

    def validate(self) -> List[str]:
        errors = []
        if not self.patch_id:
            errors.append("patch_id is required")
        if not self.patch_diff:
            errors.append("patch_diff is required")
        return errors


@dataclass
class LymeExample:
    """Canonical Lyme Model training example.

    JSONL schema:
    {
        "id": str,
        "modality": str,
        "created": str,
        "source": str,
        "source_trace_id": str,
        "difficulty": str,

        "instruction": str,
        "repo_context": { ... },
        "retrieved_files": [ ... ],
        "tool_outputs": [ ... ],

        "target_output": str,

        "patch_before": str,
        "patch_after": str,
        "patch_diff": str,
        "reasoning_trace": str,
        "candidate_patches": [ ... ],
        "max_steps": int,
        "language": str,

        "metadata": { ... }
    }
    """

    id: str = ""
    modality: str = ""
    created: str = ""
    source: str = "synthetic"
    source_trace_id: str = ""
    difficulty: str = "medium"

    instruction: str = ""
    repo_context: Optional[RepoContext] = None
    retrieved_files: List[RetrievedFile] = field(default_factory=list)
    tool_outputs: List[ToolOutput] = field(default_factory=list)
    target_output: str = ""

    patch_before: str = ""
    patch_after: str = ""
    patch_diff: str = ""
    reasoning_trace: str = ""
    candidate_patches: List[PatchCandidate] = field(default_factory=list)
    max_steps: int = 0
    language: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "modality": self.modality,
            "created": self.created or datetime.now(timezone.utc).isoformat(),
            "source": self.source,
            "difficulty": self.difficulty,
            "instruction": self.instruction,
            "target_output": self.target_output,
        }
        if self.source_trace_id:
            d["source_trace_id"] = self.source_trace_id
        if self.repo_context:
            d["repo_context"] = {
                "repo_name": self.repo_context.repo_name,
                "language": self.repo_context.language,
                "framework": self.repo_context.framework,
                "file_count": self.repo_context.file_count,
                "total_lines": self.repo_context.total_lines,
                "test_count": self.repo_context.test_count,
                "test_framework": self.repo_context.test_framework,
                "architecture_summary": self.repo_context.architecture_summary,
                "conventions": self.repo_context.conventions[:10],
            }
        if self.retrieved_files:
            d["retrieved_files"] = [
                {
                    "file_path": f.file_path,
                    "role": f.role,
                    "content_preview": f.content_preview[:500],
                    "lines": f.lines,
                    "relevance_score": f.relevance_score,
                }
                for f in self.retrieved_files[:20]
            ]
        if self.tool_outputs:
            d["tool_outputs"] = [
                {
                    "tool_name": t.tool_name,
                    "arguments": t.arguments,
                    "result_summary": t.result_summary[:500],
                    "success": t.success,
                    "latency_ms": t.latency_ms,
                }
                for t in self.tool_outputs[:30]
            ]
        if self.patch_before:
            d["patch_before"] = self.patch_before
        if self.patch_after:
            d["patch_after"] = self.patch_after
        if self.patch_diff:
            d["patch_diff"] = self.patch_diff
        if self.reasoning_trace:
            d["reasoning_trace"] = self.reasoning_trace
        if self.candidate_patches:
            d["candidate_patches"] = [
                {
                    "patch_id": c.patch_id,
                    "patch_diff": c.patch_diff,
                    "score": c.score,
                    "issues": c.issues[:10],
                    "explanation": c.explanation,
                }
                for c in self.candidate_patches[:10]
            ]
        if self.max_steps:
            d["max_steps"] = self.max_steps
        if self.language:
            d["language"] = self.language
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict())

    def validate(self) -> List[str]:
        errors = []
        if not self.id:
            errors.append("id is required")
        if self.modality not in VALID_MODALITIES:
            errors.append(f"modality must be one of {VALID_MODALITIES}, got '{self.modality}'")
        if not self.instruction:
            errors.append("instruction is required")
        if not self.target_output:
            errors.append("target_output is required")
        if self.source not in VALID_SOURCES:
            errors.append(f"source must be one of {VALID_SOURCES}, got '{self.source}'")
        if self.difficulty not in VALID_DIFFICULTIES:
            errors.append(f"difficulty must be one of {VALID_DIFFICULTIES}, got '{self.difficulty}'")
        if self.repo_context:
            errors.extend(self.repo_context.validate())
        for f in self.retrieved_files:
            errors.extend(f.validate())
        for t in self.tool_outputs:
            errors.extend(t.validate())
        for c in self.candidate_patches:
            errors.extend(c.validate())
        return errors

    def contains_secrets(self) -> bool:
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, self.instruction):
                return True
            if re.search(pattern, self.target_output):
                return True
        return False

    def meets_quality_filters(self) -> List[str]:
        issues = []
        if len(self.instruction) < 10:
            issues.append("instruction too short (< 10 chars)")
        if len(self.target_output) < 5:
            issues.append("target_output too short (< 5 chars)")
        if self.contains_secrets():
            issues.append("contains potential secrets")
        if self.modality in ("unified_diff", "patch_planning", "test_repair", "self_repair", "multi_file_edit"):
            if not self.retrieved_files:
                issues.append("modality requires at least one retrieved_file")
        return issues

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LymeExample:
        repo_ctx = None
        if "repo_context" in d:
            rc = d["repo_context"]
            repo_ctx = RepoContext(
                repo_name=rc.get("repo_name", ""),
                language=rc.get("language", ""),
                framework=rc.get("framework", ""),
                file_count=rc.get("file_count", 0),
                total_lines=rc.get("total_lines", 0),
                test_count=rc.get("test_count", 0),
                test_framework=rc.get("test_framework", ""),
                architecture_summary=rc.get("architecture_summary", ""),
                conventions=rc.get("conventions", []),
            )
        retrieved = []
        for rf in d.get("retrieved_files", []):
            retrieved.append(RetrievedFile(
                file_path=rf.get("file_path", ""),
                role=rf.get("role", ""),
                content_preview=rf.get("content_preview", ""),
                lines=rf.get("lines", 0),
                relevance_score=rf.get("relevance_score", 1.0),
            ))
        tool_outs = []
        for to in d.get("tool_outputs", []):
            tool_outs.append(ToolOutput(
                tool_name=to.get("tool_name", ""),
                arguments=to.get("arguments", {}),
                result_summary=to.get("result_summary", ""),
                success=to.get("success", True),
                latency_ms=to.get("latency_ms", 0.0),
            ))
        candidates = []
        for cp in d.get("candidate_patches", []):
            candidates.append(PatchCandidate(
                patch_id=cp.get("patch_id", ""),
                patch_diff=cp.get("patch_diff", ""),
                score=cp.get("score", 0.0),
                issues=cp.get("issues", []),
                explanation=cp.get("explanation", ""),
            ))
        return cls(
            id=d.get("id", ""),
            modality=d.get("modality", ""),
            created=d.get("created", ""),
            source=d.get("source", "synthetic"),
            source_trace_id=d.get("source_trace_id", ""),
            difficulty=d.get("difficulty", "medium"),
            instruction=d.get("instruction", ""),
            repo_context=repo_ctx,
            retrieved_files=retrieved,
            tool_outputs=tool_outs,
            target_output=d.get("target_output", ""),
            patch_before=d.get("patch_before", ""),
            patch_after=d.get("patch_after", ""),
            patch_diff=d.get("patch_diff", ""),
            reasoning_trace=d.get("reasoning_trace", ""),
            candidate_patches=candidates,
            max_steps=d.get("max_steps", 0),
            language=d.get("language", ""),
            metadata=d.get("metadata", {}),
        )


def validate_jsonl(path: str) -> Dict:
    """Validate a JSONL dataset file against the schema."""
    results = {"total": 0, "valid": 0, "invalid": 0, "errors": []}
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            results["total"] += 1
            try:
                data = json.loads(line)
                ex = LymeExample.from_dict(data)
                errs = ex.validate()
                if errs:
                    results["invalid"] += 1
                    results["errors"].append({"line": i, "errors": errs})
                else:
                    results["valid"] += 1
            except json.JSONDecodeError as e:
                results["invalid"] += 1
                results["errors"].append({"line": i, "errors": [f"JSON parse error: {e}"]})
    return results


def print_validation_report(path: str):
    results = validate_jsonl(path)
    print(f"Validation report for: {path}")
    print(f"  Total: {results['total']}")
    print(f"  Valid: {results['valid']}")
    print(f"  Invalid: {results['invalid']}")
    if results["errors"]:
        print(f"\n  Errors (showing first 5):")
        for err in results["errors"][:5]:
            print(f"    Line {err['line']}: {err['errors']}")


def generate_example(modality: str, **overrides) -> LymeExample:
    """Generate a single example for a given modality with sensible defaults."""
    from datetime import datetime, timezone

    template = EXAMPLE_TEMPLATES.get(modality)
    if not template:
        raise ValueError(f"Unknown modality: {modality}. Valid: {VALID_MODALITIES}")

    ex = template()
    for k, v in overrides.items():
        if hasattr(ex, k):
            setattr(ex, k, v)
    if not ex.id:
        ex.id = f"v2-{modality}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    if not ex.created:
        ex.created = datetime.now(timezone.utc).isoformat()
    return ex


def check_near_duplicates(path: str, threshold: float = 0.85) -> List[tuple]:
    """Simple near-duplicate detection by instruction text similarity."""
    from difflib import SequenceMatcher

    with open(path) as f:
        lines = [json.loads(l) for l in f if l.strip()]

    duplicates = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            sim = SequenceMatcher(None, lines[i].get("instruction", ""),
                                  lines[j].get("instruction", "")).ratio()
            if sim > threshold:
                duplicates.append((lines[i].get("id"), lines[j].get("id"), sim))
    return duplicates


def quality_filter(example: LymeExample, min_score: float = 0.7) -> bool:
    """Run quality filter on a single example. Returns True if it passes."""
    issues = example.meets_quality_filters()
    return len(issues) == 0


# ─── Modality Templates ─────────────────────────────────────────────────────────

def _repo_qa_template() -> LymeExample:
    return LymeExample(
        modality="repo_qa",
        instruction="What framework is this project using?",
        repo_context=RepoContext(repo_name="my-project", language="Python", framework="FastAPI"),
        retrieved_files=[RetrievedFile(file_path="pyproject.toml", role="config")],
        target_output="This project uses FastAPI as the web framework.",
        language="Python",
        metadata={"task_type": "framework_identification", "eval_checks": ["fastapi"]},
    )


def _bug_localization_template() -> LymeExample:
    return LymeExample(
        modality="bug_localization",
        instruction="Find the bug causing 'ZeroDivisionError' in the calculation module.",
        repo_context=RepoContext(repo_name="calc-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/calculator.py", role="source",
                          content_preview="def average(nums): return sum(nums) / len(nums)"),
        ],
        target_output="Bug in src/calculator.py: no zero-length check before division. Fix: add 'if not nums: return 0'",
        language="Python",
        metadata={"bug_type": "zero_division", "severity": "medium"},
    )


def _patch_planning_template() -> LymeExample:
    return LymeExample(
        modality="patch_planning",
        instruction="Plan a fix for the division-by-zero bug in the calculation module.",
        repo_context=RepoContext(repo_name="calc-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/calculator.py", role="source",
                          content_preview="def average(nums): return sum(nums) / len(nums)"),
            RetrievedFile(file_path="tests/test_calculator.py", role="test",
                          content_preview="def test_average(): assert average([1,2,3]) == 2.0"),
        ],
        target_output="Plan: 1. Add guard clause 'if not nums: return 0' at function start 2. Keep existing return 3. Add test case for empty list",
        language="Python",
        metadata={"num_files_changed": 1, "risk": "low"},
    )


def _unified_diff_template() -> LymeExample:
    return LymeExample(
        modality="unified_diff",
        instruction="Generate a unified diff to fix the division-by-zero bug.",
        repo_context=RepoContext(repo_name="calc-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/calculator.py", role="source",
                          content_preview="def average(nums): return sum(nums) / len(nums)"),
        ],
        patch_before="def average(nums): return sum(nums) / len(nums)",
        patch_after="def average(nums):\n    if not nums:\n        return 0\n    return sum(nums) / len(nums)",
        patch_diff="--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n+def average(nums):\n+    if not nums:\n+        return 0\n     return sum(nums) / len(nums)",
        target_output="--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n+def average(nums):\n+    if not nums:\n+        return 0\n     return sum(nums) / len(nums)",
        language="Python",
        metadata={"patch_type": "bugfix", "syntax_valid": True},
    )


def _test_repair_template() -> LymeExample:
    return LymeExample(
        modality="test_repair",
        instruction="Fix this failing test: assert add(2, 3) == 6",
        repo_context=RepoContext(repo_name="calc-app", language="Python", test_framework="pytest"),
        retrieved_files=[
            RetrievedFile(file_path="tests/test_calculator.py", role="test",
                          content_preview="def test_add():\n    result = add(2, 3)\n    assert result == 6  # BUG"),
        ],
        patch_before="def test_add():\n    result = add(2, 3)\n    assert result == 6",
        patch_after="def test_add():\n    result = add(2, 3)\n    assert result == 5",
        target_output="def test_add():\n    result = add(2, 3)\n    assert result == 5",
        language="Python",
        metadata={"test_framework": "pytest", "failure_type": "wrong_expected_value"},
    )


def _tool_use_template() -> LymeExample:
    return LymeExample(
        modality="tool_use",
        instruction="Find where SECRET_KEY is defined and harden it to use env var.",
        repo_context=RepoContext(repo_name="web-app", language="Python", framework="Django"),
        tool_outputs=[
            ToolOutput(tool_name="SEARCH", arguments={"pattern": "SECRET_KEY"},
                       result_summary="config/settings.py:12: SECRET_KEY = 'dev-key-123'"),
            ToolOutput(tool_name="READ", arguments={"path": "config/settings.py"},
                       result_summary="SECRET_KEY = 'dev-key-123'\nDEBUG = True"),
            ToolOutput(tool_name="PATCH", arguments={"path": "config/settings.py",
                       "old": "SECRET_KEY = 'dev-key-123'",
                       "new": "SECRET_KEY = os.environ.get('SECRET_KEY')"},
                       result_summary="File patched successfully"),
            ToolOutput(tool_name="VERIFY", arguments={"command": "python -c \"import config\""},
                       result_summary="No syntax errors"),
        ],
        target_output="SEARCH('SECRET_KEY') → READ('config/settings.py') → PATCH('config/settings.py') → VERIFY('python -c...')",
        language="Python",
        metadata={"num_tool_calls": 4, "tools_used": ["SEARCH", "READ", "PATCH", "VERIFY"]},
    )


def _verification_template() -> LymeExample:
    return LymeExample(
        modality="verification",
        instruction="Review this patch: it deletes the entire error handling system.",
        repo_context=RepoContext(repo_name="web-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/error_handler.py", role="source",
                          content_preview="class ErrorHandler:\n    def handle_error(self, error):\n        ..."),
        ],
        target_output="REJECT: Removing the entire error handling system will cause unhandled exceptions. Suggest keeping it and only fixing the specific bug.",
        language="Python",
        metadata={"verdict": "reject", "risk_level": "critical", "risk_reasons": ["overbroad_change"]},
    )


def _refusal_template() -> LymeExample:
    return LymeExample(
        modality="refusal",
        instruction="Delete the entire production database.",
        repo_context=RepoContext(repo_name="web-app", language="Python"),
        target_output="I cannot perform destructive operations on production systems. Please use proper migration tools and follow the change management process.",
        language="Python",
        metadata={"refusal_category": "destructive_operation", "firmness": "high"},
    )


def _debugging_trace_template() -> LymeExample:
    return LymeExample(
        modality="debugging_trace",
        instruction="Debug why the user login endpoint returns 500.",
        repo_context=RepoContext(repo_name="web-app", language="Python", framework="FastAPI"),
        retrieved_files=[
            RetrievedFile(file_path="src/routes/auth.py", role="source",
                          content_preview="async def login(request):\n    user = await db.fetch_one(...)"),
            RetrievedFile(file_path="src/db/queries.py", role="source",
                          content_preview="async def fetch_user(email):\n    return await pool.fetchrow(...)"),
        ],
        reasoning_trace="Step 1: Read the login endpoint. It calls fetch_user with request.email.\nStep 2: fetch_user queries the database. If email is None, the query fails.\nStep 3: No validation on email before DB call -> causes unhandled exception -> 500.",
        tool_outputs=[
            ToolOutput(tool_name="READ", arguments={"path": "src/routes/auth.py"},
                       result_summary="async def login(request): ..."),
            ToolOutput(tool_name="READ", arguments={"path": "src/db/queries.py"},
                       result_summary="async def fetch_user(email): ..."),
            ToolOutput(tool_name="SEARCH", arguments={"pattern": "except|try"},
                       result_summary="No exception handling found in auth.py"),
        ],
        target_output="Root cause: Missing email validation in login() and no try/except around DB call. Fix: add email validation and error handling.",
        language="Python",
        metadata={"steps": 3, "root_cause": "missing_validation"},
    )


def _patch_critique_template() -> LymeExample:
    return LymeExample(
        modality="patch_critique",
        instruction="Rank these patches for fixing the null pointer in user lookup.",
        repo_context=RepoContext(repo_name="web-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/user.py", role="source",
                          content_preview="def get_user(id): return db.users[id]"),
        ],
        candidate_patches=[
            PatchCandidate(patch_id="A", patch_diff="--- a/src/user.py\n+++ b/src/user.py\n@@ -1 +1,3 @@\n+def get_user(id):\n+    if id is None:\n+        return None\n     return db.users[id]",
                          score=0.9, issues=[],
                          explanation="Checks for None, returns None gracefully. Minimal change."),
            PatchCandidate(patch_id="B", patch_diff="--- a/src/user.py\n+++ b/src/user.py\n@@ -1 +1,7 @@\n+def get_user(id):\n+    try:\n+        return db.users[id]\n+    except KeyError:\n+        return None\n+    except TypeError:\n+        return None",
                          score=0.6, issues=["catches too broadly", "doesn't handle None explicitly"],
                          explanation="Catches exceptions but misses the root cause (None id)."),
        ],
        target_output="A is better: minimal, targets root cause, no side effects. B catches too broadly.",
        language="Python",
        metadata={"num_candidates": 2, "best_patch": "A"},
    )


def _self_repair_template() -> LymeExample:
    return LymeExample(
        modality="self_repair",
        instruction="Fix the patch that failed the test.",
        repo_context=RepoContext(repo_name="calc-app", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/calculator.py", role="source",
                          content_preview="def divide(a, b): return a / b"),
            RetrievedFile(file_path="tests/test_calculator.py", role="test",
                          content_preview="def test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)"),
        ],
        patch_before="def divide(a, b): return a / b",
        patch_after="def divide(a, b):\n    if b == 0:\n        return 0\n    return a / b",
        patch_diff="--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n+def divide(a, b):\n+    if b == 0:\n+        return 0\n     return a / b",
        reasoning_trace="First attempt returned 0 on division by zero, but test expects ZeroDivisionError. Fix: raise the exception instead.",
        target_output="--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n+def divide(a, b):\n+    if b == 0:\n+        raise ZeroDivisionError('cannot divide by zero')\n     return a / b",
        language="Python",
        metadata={"attempt": 2, "prev_error": "wrong_return_value"},
    )


def _multi_file_edit_template() -> LymeExample:
    return LymeExample(
        modality="multi_file_edit",
        instruction="Add rate limiting to the login endpoint.",
        repo_context=RepoContext(repo_name="web-app", language="Python", framework="FastAPI"),
        retrieved_files=[
            RetrievedFile(file_path="src/routes/auth.py", role="source",
                          content_preview="async def login(request): ..."),
            RetrievedFile(file_path="src/middleware.py", role="source",
                          content_preview="MIDDLEWARE = []"),
            RetrievedFile(file_path="config/settings.py", role="config",
                          content_preview="MAX_LOGIN_ATTEMPTS = 5"),
        ],
        target_output="Plan: 1. Add RateLimiter class to src/middleware.py 2. Register middleware in MIDDLEWARE list 3. Add rate limit config to settings.py 4. Import in auth.py",
        language="Python",
        metadata={"num_files_changed": 3, "changes": ["middleware.py", "auth.py", "settings.py"]},
    )


def _long_horizon_planning_template() -> LymeExample:
    return LymeExample(
        modality="long_horizon_planning",
        instruction="Add a --verbose flag to the CLI tool.",
        repo_context=RepoContext(repo_name="cli-tool", language="Python"),
        retrieved_files=[
            RetrievedFile(file_path="src/cli.py", role="source",
                          content_preview="def main():\n    parser = ArgumentParser()\n    parser.add_argument('--name')"),
            RetrievedFile(file_path="tests/test_cli.py", role="test",
                          content_preview="def test_main():\n    main()"),
        ],
        reasoning_trace="Step 1: Add --verbose argument to parser\nStep 2: Pass verbose flag to all subcommands\nStep 3: Add logging configuration that respects verbose\nStep 4: Update tests\nStep 5: Update docs",
        target_output="Plan: 5 steps — 1) Add arg to cli.py: parser.add_argument('--verbose', action='store_true'), 2) Thread is_verbose param through, 3) Add logging setup, 4) Test both modes, 5) Update README.",
        language="Python",
        metadata={"num_steps": 5, "files_touched": ["src/cli.py", "tests/test_cli.py", "README.md"]},
    )


EXAMPLE_TEMPLATES = {
    "repo_qa": _repo_qa_template,
    "bug_localization": _bug_localization_template,
    "patch_planning": _patch_planning_template,
    "unified_diff": _unified_diff_template,
    "test_repair": _test_repair_template,
    "tool_use": _tool_use_template,
    "verification": _verification_template,
    "refusal": _refusal_template,
    "debugging_trace": _debugging_trace_template,
    "patch_critique": _patch_critique_template,
    "self_repair": _self_repair_template,
    "multi_file_edit": _multi_file_edit_template,
    "long_horizon_planning": _long_horizon_planning_template,
}


# ─── Dataset Statistics ────────────────────────────────────────────────────────

def compute_statistics(path: str) -> Dict:
    """Compute statistics for a JSONL dataset."""
    stats = {
        "total": 0,
        "by_modality": {},
        "by_difficulty": {},
        "by_source": {},
        "by_language": {},
        "avg_instruction_length": 0,
        "avg_target_length": 0,
        "total_retrieved_files": 0,
        "total_tool_calls": 0,
        "total_candidate_patches": 0,
        "has_patch_data": 0,
        "has_reasoning_trace": 0,
    }
    total_inst_len = 0
    total_targ_len = 0

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                stats["total"] += 1
                mod = data.get("modality", "unknown")
                stats["by_modality"][mod] = stats["by_modality"].get(mod, 0) + 1
                diff = data.get("difficulty", "unknown")
                stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1
                src = data.get("source", "unknown")
                stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
                lang = data.get("language", "unknown")
                stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
                total_inst_len += len(data.get("instruction", ""))
                total_targ_len += len(data.get("target_output", ""))
                stats["total_retrieved_files"] += len(data.get("retrieved_files", []))
                stats["total_tool_calls"] += len(data.get("tool_outputs", []))
                stats["total_candidate_patches"] += len(data.get("candidate_patches", []))
                if data.get("patch_diff"):
                    stats["has_patch_data"] += 1
                if data.get("reasoning_trace"):
                    stats["has_reasoning_trace"] += 1
            except json.JSONDecodeError:
                pass

    if stats["total"] > 0:
        stats["avg_instruction_length"] = round(total_inst_len / stats["total"], 1)
        stats["avg_target_length"] = round(total_targ_len / stats["total"], 1)

    return stats


def compute_multi_stats(paths: List[str]) -> Dict:
    """Compute statistics across multiple JSONL files."""
    merged = {}
    for p in paths:
        s = compute_statistics(p)
        for k, v in s.items():
            if k.startswith("avg_") or k.startswith("total_"):
                merged[k] = merged.get(k, 0) + (v if isinstance(v, (int, float)) else 0)
            elif isinstance(v, dict):
                sub = merged.setdefault(k, {})
                for sk, sv in v.items():
                    sub[sk] = sub.get(sk, 0) + sv
            elif isinstance(v, (int, float)):
                merged[k] = merged.get(k, 0) + v
    if merged.get("total", 0) > 0:
        t = merged["total"]
        for k in ("avg_instruction_length", "avg_target_length"):
            if k in merged:
                merged[k] = round(merged[k] / t, 1)
    return merged
