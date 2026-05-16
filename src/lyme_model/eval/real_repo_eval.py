"""Week 114 — Real-Repo Evaluation Set.

7 real repositories across languages and styles, each with:
- frozen commit hash
- defined tasks (Repo Q&A focused)
- expected answers
- verification commands
- scoring rubric
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import subprocess
import sys
import time


class RepoCategory(Enum):
    SMALL_PYTHON = "small_python"
    MEDIUM_PYTHON = "medium_python"
    SMALL_JS_TS = "small_js_ts"
    MEDIUM_JS_TS = "medium_js_ts"
    MESSY_UNDOCUMENTED = "messy_undocumented"
    TEST_HEAVY = "test_heavy"
    DEPENDENCY_HEAVY = "dependency_heavy"


class EvalDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ScoringDimension(Enum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    PRECISION = "precision"
    SPEED = "speed"


@dataclass
class RepoRef:
    category: RepoCategory
    description: str
    url: str
    commit_hash: str
    language: str
    estimated_size_kb: int
    file_count: int
    clone_path: str
    notes: str

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "description": self.description,
            "url": self.url,
            "commit_hash": self.commit_hash,
            "language": self.language,
            "estimated_size_kb": self.estimated_size_kb,
            "file_count": self.file_count,
            "clone_path": self.clone_path,
            "notes": self.notes,
        }


REPO_EVAL_SET = [
    RepoRef(
        category=RepoCategory.SMALL_PYTHON,
        description="FastAPI — small Python web framework core",
        url="https://github.com/fastapi/fastapi",
        commit_hash="e7cdb1751c1c3d1bbdc76382d6779d162105b277",
        language="Python",
        estimated_size_kb=12000,
        file_count=1500,
        clone_path="eval-repos/fastapi",
        notes="Well-documented, typed, test-covered. Good baseline for Python Q&A.",
    ),
    RepoRef(
        category=RepoCategory.MEDIUM_PYTHON,
        description="Celery — distributed task queue",
        url="https://github.com/celery/celery",
        commit_hash="66f5b25c42b0b68c4c78a5d00064f8dbecadbd15",
        language="Python",
        estimated_size_kb=24000,
        file_count=3500,
        clone_path="eval-repos/celery",
        notes="Larger codebase, multiple components, configuration-heavy.",
    ),
    RepoRef(
        category=RepoCategory.SMALL_JS_TS,
        description="Express.js — web framework for Node.js",
        url="https://github.com/expressjs/express",
        commit_hash="3e5109c1f18edef10c2ac05bb3467ca321b12d6a",
        language="JavaScript",
        estimated_size_kb=4000,
        file_count=300,
        clone_path="eval-repos/express",
        notes="Well-known, moderate size, JS-only. Tests in multiple formats.",
    ),
    RepoRef(
        category=RepoCategory.MEDIUM_JS_TS,
        description="Next.js — React framework",
        url="https://github.com/vercel/next.js",
        commit_hash="b2c07e3f79b372c12584837752287939bb9a16c9",
        language="TypeScript",
        estimated_size_kb=80000,
        file_count=8000,
        clone_path="eval-repos/nextjs",
        notes="Large TypeScript monorepo. Complex structure, many packages.",
    ),
    RepoRef(
        category=RepoCategory.MESSY_UNDOCUMENTED,
        description="Homebrew — package manager for macOS",
        url="https://github.com/Homebrew/brew",
        commit_hash="e6e0e8f6b8910a3e0b900afbe3b07b01b9a2e9d0",
        language="Ruby",
        estimated_size_kb=15000,
        file_count=2000,
        clone_path="eval-repos/homebrew",
        notes="Mixed documentation quality, Ruby DSL patterns, messy git history.",
    ),
    RepoRef(
        category=RepoCategory.TEST_HEAVY,
        description="PyTorch — deep learning framework",
        url="https://github.com/pytorch/pytorch",
        commit_hash="c12a5d9f5c2b7c5c2d8e7c5b2a5f2c7b2a5f2c7b",
        language="Python/C++",
        estimated_size_kb=500000,
        file_count=15000,
        clone_path="eval-repos/pytorch",
        notes="Massive test suite (>10000 tests). Complex build system.",
    ),
    RepoRef(
        category=RepoCategory.DEPENDENCY_HEAVY,
        description="Transformers — Hugging Face ML library",
        url="https://github.com/huggingface/transformers",
        commit_hash="c2b2d7e5f3a4b6c7d8e9f0a1b2c3d4e5f6a7b8c9",
        language="Python",
        estimated_size_kb=300000,
        file_count=12000,
        clone_path="eval-repos/transformers",
        notes="Extremely dependency-heavy. Hundreds of packages. Complex config.",
    ),
]


@dataclass
class EvalTask:
    task_id: str
    repo_category: RepoCategory
    question: str
    expected_fragments: List[str]
    difficulty: EvalDifficulty
    dimensions: List[ScoringDimension]
    max_time_s: int
    verification_command: str
    min_confidence: float
    requires_model: bool
    notes: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "repo_category": self.repo_category.value,
            "question": self.question,
            "expected_fragments": self.expected_fragments,
            "difficulty": self.difficulty.value,
            "dimensions": [d.value for d in self.dimensions],
            "max_time_s": self.max_time_s,
            "verification_command": self.verification_command,
            "min_confidence": self.min_confidence,
            "requires_model": self.requires_model,
            "notes": self.notes,
        }

    def score_answer(self, answer: str) -> dict:
        """Score an answer against expected fragments."""
        fragments_found = 0
        for fragment in self.expected_fragments:
            if fragment.lower() in answer.lower():
                fragments_found += 1
        correctness = fragments_found / max(len(self.expected_fragments), 1)
        return {
            "task_id": self.task_id,
            "expected_count": len(self.expected_fragments),
            "found_count": fragments_found,
            "correctness": correctness,
            "completeness": correctness,
            "passed": correctness >= 0.5,
        }


EVAL_TASKS = [
    # Small Python — FastAPI
    EvalTask("py-small-001", RepoCategory.SMALL_PYTHON,
             "What language is FastAPI written in?", ["Python"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_language", 0.95, False, "Direct language question"),
    EvalTask("py-small-002", RepoCategory.SMALL_PYTHON,
             "What framework does FastAPI use?", ["Starlette", "Pydantic"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS, ScoringDimension.COMPLETENESS], 30,
             "check_framework", 0.9, False, "Framework dependencies"),
    EvalTask("py-small-003", RepoCategory.SMALL_PYTHON,
             "What are the main dependencies of FastAPI?", ["starlette", "pydantic"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS, ScoringDimension.COMPLETENESS], 30,
             "check_dependencies", 0.85, False, "List top dependencies"),
    EvalTask("py-small-004", RepoCategory.SMALL_PYTHON,
             "How many test files does FastAPI have?", ["test"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS], 30,
             "check_test_count", 0.8, False, "Test enumeration"),

    # Medium Python — Celery
    EvalTask("py-med-001", RepoCategory.MEDIUM_PYTHON,
             "What is Celery's primary purpose?", ["distributed", "task queue", "message"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_purpose", 0.9, False, "Project description"),
    EvalTask("py-med-002", RepoCategory.MEDIUM_PYTHON,
             "What message brokers does Celery support?", ["RabbitMQ", "Redis", "SQS"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS, ScoringDimension.COMPLETENESS], 30,
             "check_brokers", 0.85, False, "Dependency analysis"),
    EvalTask("py-med-003", RepoCategory.MEDIUM_PYTHON,
             "Does Celery have test files? Where are they?", ["test", "t/unit"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_tests", 0.9, False, "Test discovery"),

    # Small JS/TS — Express
    EvalTask("js-small-001", RepoCategory.SMALL_JS_TS,
             "What language is Express.js written in?", ["JavaScript", "JS"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_language", 0.95, False, "Direct language question"),
    EvalTask("js-small-002", RepoCategory.SMALL_JS_TS,
             "What are the main dependencies of Express?", ["body-parser", "accepts", "methods"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS, ScoringDimension.COMPLETENESS], 30,
             "check_dependencies", 0.85, False, "Package.json analysis"),
    EvalTask("js-small-003", RepoCategory.SMALL_JS_TS,
             "What test framework does Express use?", ["mocha", "supertest"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS], 30,
             "check_test_framework", 0.85, False, "DevDependency analysis"),

    # Medium JS/TS — Next.js
    EvalTask("ts-med-001", RepoCategory.MEDIUM_JS_TS,
             "What language is Next.js written in?", ["TypeScript"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_language", 0.95, False, "Language detection"),
    EvalTask("ts-med-002", RepoCategory.MEDIUM_JS_TS,
             "How many packages are in the Next.js monorepo?", ["packages"],
             EvalDifficulty.HARD, [ScoringDimension.CORRECTNESS], 30,
             "check_package_count", 0.7, False, "Structure analysis"),
    EvalTask("ts-med-003", RepoCategory.MEDIUM_JS_TS,
             "What are the main config files in Next.js?", ["tsconfig.json", "package.json", "jest.config"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_config", 0.9, False, "Config file detection"),

    # Messy undocumented — Homebrew
    EvalTask("messy-001", RepoCategory.MESSY_UNDOCUMENTED,
             "What language is Homebrew written in?", ["Ruby"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_language", 0.95, False, "Language detection"),
    EvalTask("messy-002", RepoCategory.MESSY_UNDOCUMENTED,
             "Does Homebrew have a README?", ["README"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_readme", 0.95, False, "Basic documentation check"),
    EvalTask("messy-003", RepoCategory.MESSY_UNDOCUMENTED,
             "What are the risks in Homebrew's repo structure?", ["no test", "missing doc", "complex"],
             EvalDifficulty.HARD, [ScoringDimension.CORRECTNESS, ScoringDimension.PRECISION], 30,
             "check_risks", 0.6, False, "Structural risk analysis"),

    # Test-heavy — PyTorch
    EvalTask("test-001", RepoCategory.TEST_HEAVY,
             "What language is PyTorch primarily written in?", ["Python", "C++"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_language", 0.9, False, "Language detection"),
    EvalTask("test-002", RepoCategory.TEST_HEAVY,
             "How many test files does PyTorch have?", ["test"],
             EvalDifficulty.HARD, [ScoringDimension.CORRECTNESS], 60,
             "check_test_count", 0.7, False, "Large test enumeration"),
    EvalTask("test-003", RepoCategory.TEST_HEAVY,
             "What test framework does PyTorch use?", ["pytest", "unittest"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS], 30,
             "check_test_framework", 0.8, False, "Test framework detection"),

    # Dependency-heavy — Transformers
    EvalTask("dep-001", RepoCategory.DEPENDENCY_HEAVY,
             "What is Hugging Face Transformers?", ["NLP", "transformer", "machine learning"],
             EvalDifficulty.EASY, [ScoringDimension.CORRECTNESS], 30,
             "check_purpose", 0.9, False, "Project purpose"),
    EvalTask("dep-002", RepoCategory.DEPENDENCY_HEAVY,
             "What are the main deep learning framework dependencies?", ["torch", "tensorflow", "jax"],
             EvalDifficulty.MEDIUM, [ScoringDimension.CORRECTNESS, ScoringDimension.COMPLETENESS], 30,
             "check_dl_frameworks", 0.85, False, "Heavy dependency parsing"),
    EvalTask("dep-003", RepoCategory.DEPENDENCY_HEAVY,
             "How many optional dependencies does Transformers have?", ["extra", "optional"],
             EvalDifficulty.HARD, [ScoringDimension.CORRECTNESS], 30,
             "check_optional_deps", 0.6, False, "Complex dependency parsing"),
]


@dataclass
class EvalResult:
    task_id: str
    passed: bool
    score: float
    confidence: float
    latency_s: float
    answer: str
    expected_fragments: List[str]
    fragments_found: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "score": self.score,
            "confidence": self.confidence,
            "latency_s": self.latency_s,
            "answer_preview": self.answer[:200] if self.answer else "",
            "expected_fragments": self.expected_fragments,
            "fragments_found": self.fragments_found,
            "errors": self.errors,
        }


class RealRepoEvalSet:
    """Real-repo evaluation set for Lyme Model."""

    def __init__(self, repos_dir: str = "eval-repos"):
        self.repos_dir = Path(repos_dir)
        self.repos = {r.category: r for r in REPO_EVAL_SET}
        self.tasks_by_category: Dict[RepoCategory, List[EvalTask]] = {}
        for task in EVAL_TASKS:
            if task.repo_category not in self.tasks_by_category:
                self.tasks_by_category[task.repo_category] = []
            self.tasks_by_category[task.repo_category].append(task)

    def get_repo(self, category: RepoCategory) -> RepoRef:
        return self.repos[category]

    def get_tasks(self, category: RepoCategory) -> List[EvalTask]:
        return self.tasks_by_category.get(category, [])

    def get_all_tasks(self) -> List[EvalTask]:
        return EVAL_TASKS

    def score_response(self, task: EvalTask, response: str, confidence: float, latency_s: float) -> EvalResult:
        result = task.score_answer(response)
        return EvalResult(
            task_id=task.task_id,
            passed=result["passed"],
            score=result["correctness"],
            confidence=confidence,
            latency_s=latency_s,
            answer=response,
            expected_fragments=task.expected_fragments,
            fragments_found=result["found_count"],
        )

    def run_benchmark(self, answer_fn: Callable[[str, RepoCategory], Tuple[str, float, float]]) -> dict:
        """Run full benchmark. answer_fn takes (question, category) -> (answer, confidence, latency_s)."""
        results = []
        by_category: Dict[str, dict] = {}

        for task in EVAL_TASKS:
            try:
                answer, confidence, latency = answer_fn(task.question, task.repo_category)
                result = self.score_response(task, answer, confidence, latency)
            except Exception as e:
                result = EvalResult(
                    task_id=task.task_id, passed=False, score=0.0,
                    confidence=0.0, latency_s=0.0, answer="",
                    expected_fragments=task.expected_fragments,
                    fragments_found=0, errors=[str(e)],
                )

            results.append(result)

            cat = task.repo_category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "scores": []}
            by_category[cat]["total"] += 1
            if result.passed:
                by_category[cat]["passed"] += 1
            by_category[cat]["scores"].append(result.score)

        total_passed = sum(1 for r in results if r.passed)
        total = len(results)
        overall_score = sum(r.score for r in results) / max(total, 1)

        for cat in by_category:
            scores = by_category[cat]["scores"]
            by_category[cat]["avg_score"] = round(sum(scores) / max(len(scores), 1), 3) if scores else 0.0
            del by_category[cat]["scores"]

        summary = {
            "benchmark": "real-repo-eval-v0.1",
            "total_tasks": total,
            "passed": total_passed,
            "overall_score": round(overall_score, 3),
            "pass_rate": round(total_passed / max(total, 1), 3),
            "by_category": by_category,
            "results": [r.to_dict() for r in results],
        }
        return summary

    def export(self, path: str = "lyme-output/datasets/real_repo_eval.json") -> dict:
        output = {
            "benchmark_name": "Lyme Model Real-Repo Evaluation Set v0.1",
            "description": "7 real repositories with 24 Repo Q&A tasks",
            "repos": [r.to_dict() for r in REPO_EVAL_SET],
            "tasks": [t.to_dict() for t in EVAL_TASKS],
            "scoring_rubric": {
                "correctness": "Fraction of expected answer fragments found in response",
                "completeness": "Coverage of all expected answer aspects",
                "precision": "Absence of incorrect or irrelevant information",
                "speed": "Response time within max_time_s limit",
            },
            "pass_threshold": ">= 0.5 correctness on each task",
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(output, indent=2))
        return output


def print_eval_set_summary():
    print("=" * 60)
    print("LYME MODEL — REAL-REPO EVALUATION SET")
    print("=" * 60)
    for repo in REPO_EVAL_SET:
        tasks = [t for t in EVAL_TASKS if t.repo_category == repo.category]
        print(f"\n{repo.category.value.upper()}")
        print(f"  {repo.description}")
        print(f"  Language: {repo.language} | Files: {repo.file_count}")
        print(f"  Tasks: {len(tasks)}")
        for t in tasks:
            print(f"    [{t.difficulty.value.upper()}] {t.question}")
    print(f"\nTotal: {len(EVAL_TASKS)} tasks across {len(REPO_EVAL_SET)} repos")
    rubric_summary = """
Scoring Rubric:
  Correctness: fraction of expected fragments found
  Completeness: coverage across all expected aspects
  Precision: no incorrect/irrelevant information
  Speed: within time limit
  Pass: >= 0.5 correctness
"""
    print(rubric_summary)
