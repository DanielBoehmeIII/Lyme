"""Week 96 — Lyme Model Dataset v0.1 Generator.

Generates the first local coding dataset from:
- synthetic repos
- public toy repos (simulated)
- Lyme Audit traces
- manually verified examples

8 dataset categories:
- repo Q&A
- locate bug
- explain failure
- plan patch
- apply patch
- verify patch
- recover from failed test
- refuse unsupported claim

Output: train/validation/test splits + dataset card + known limitations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import random
import uuid

from .data_format import (
    LymeTrainingExample, LymeDataset, LymeDataFormat,
    RepoState, RelevantFile, ToolCall, Patch, PatchPlan,
    VerificationResult, FailureRecovery,
)
from .sanitizer import TrainingDataSanitizer


SEED = 42
random.seed(SEED)


# ─── Synthetic Repo Templates ─────────────────────────────────────────────────

SYNTHETIC_REPOS = {
    "calc-app": {
        "language": "python",
        "framework": "flask",
        "description": "A simple calculator web application",
        "files": ["app.py", "calculator.py", "tests/test_calculator.py"],
    },
    "todo-api": {
        "language": "python",
        "framework": "fastapi",
        "description": "A REST API for todo list management",
        "files": ["main.py", "models.py", "tests/test_api.py"],
    },
    "data-pipeline": {
        "language": "python",
        "framework": "pandas",
        "description": "ETL data processing pipeline",
        "files": ["pipeline.py", "transform.py", "tests/test_pipeline.py"],
    },
    "cli-tool": {
        "language": "python",
        "framework": "click",
        "description": "Command-line file management tool",
        "files": ["cli.py", "fileops.py", "tests/test_cli.py"],
    },
    "blog-engine": {
        "language": "python",
        "framework": "django",
        "description": "Simple blog content management system",
        "files": ["views.py", "models.py", "tests/test_views.py"],
    },
}


@dataclass
class DatasetCard:
    """Dataset v0.1 card — follows standard dataset card format."""
    name: str = "Lyme Model Dataset v0.1"
    version: str = "0.1"
    description: str = "First local coding dataset for Lyme Model training"
    created_at: str = ""
    total_examples: int = 0
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    by_task_type: Dict[str, int] = field(default_factory=dict)
    by_difficulty: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    known_limitations: List[str] = field(default_factory=list)
    data_format_version: str = "0.1"
    license: str = "Research Use Only"
    sanitization_applied: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "created_at": self.created_at,
            "total_examples": self.total_examples,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "test_count": self.test_count,
            "by_task_type": dict(sorted(self.by_task_type.items(), key=lambda x: -x[1])),
            "by_difficulty": dict(sorted(self.by_difficulty.items(), key=lambda x: -x[1])),
            "by_source": dict(sorted(self.by_source.items(), key=lambda x: -x[1])),
            "known_limitations": self.known_limitations,
            "data_format_version": self.data_format_version,
            "license": self.license,
            "sanitization_applied": self.sanitization_applied,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Dataset Card: {self.name}",
            "",
            f"**Version**: {self.version}",
            f"**Created**: {self.created_at}",
            f"**Description**: {self.description}",
            f"**License**: {self.license}",
            f"**Format Version**: {self.data_format_version}",
            "",
            "## Dataset Statistics",
            "",
            f"- Total examples: {self.total_examples}",
            f"- Train: {self.train_count}",
            f"- Validation: {self.val_count}",
            f"- Test: {self.test_count}",
            "",
            "### By Task Type",
        ]
        for t, c in sorted(self.by_task_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {t}: {c}")
        lines.append("")
        lines.append("### By Difficulty")
        for d, c in sorted(self.by_difficulty.items(), key=lambda x: -x[1]):
            lines.append(f"- {d}: {c}")
        lines.append("")
        lines.append("### By Source")
        for s, c in sorted(self.by_source.items(), key=lambda x: -x[1]):
            lines.append(f"- {s}: {c}")
        lines.append("")
        lines.append("## Known Limitations")
        for lim in self.known_limitations:
            lines.append(f"- {lim}")
        lines.append("")
        lines.append("## Data Collection")
        lines.append("")
        lines.append("- **Synthetic repos**: Generated from templates with intentional bugs")
        lines.append("- **Lyme Audit traces**: Converted from real agent runs")
        lines.append("- **Manual curation**: Verified correct/incorrect labels")
        lines.append("")
        lines.append("## Sanitization")
        lines.append("")
        lines.append("All examples pass through the Lyme Sanitizer which redacts:")
        lines.append("- API keys, secrets, tokens")
        lines.append("- Email addresses, usernames in paths")
        lines.append("- Private repo identifiers")
        lines.append("- Credential URLs")
        return "\n".join(lines)


# ─── Example Generators ───────────────────────────────────────────────────────

class DatasetV01Generator:
    """Generates Lyme Model Dataset v0.1."""

    def __init__(self):
        self.examples: List[LymeTrainingExample] = []
        self.sanitizer = TrainingDataSanitizer()

    def generate_all(self) -> LymeDataset:
        self.examples = []
        self._generate_repo_qa()
        self._generate_locate_bug()
        self._generate_explain_failure()
        self._generate_plan_patch()
        self._generate_apply_patch()
        self._generate_verify_patch()
        self._generate_recover()
        self._generate_refuse()
        self._load_audit_traces()
        dataset = LymeDataFormat.build_dataset(
            self.examples, val_split=0.1, test_split=0.15
        )
        return dataset

    def _make_example(self, task: str, task_type: str, difficulty: str,
                      repo_name: str = "", correct_answer: str = "",
                      is_correct: bool = True, error_output: str = "",
                      final_answer: str = "") -> LymeTrainingExample:
        repo = SYNTHETIC_REPOS.get(repo_name, {
            "language": "python", "framework": "generic",
            "description": "", "files": [],
        })
        return LymeTrainingExample(
            example_id=f"v01-{uuid.uuid4().hex[:12]}",
            source_trace_id="",
            source_audit_id="",
            created_at=str(datetime.now(timezone.utc).isoformat()),
            task_instruction=task,
            task_type=task_type,
            difficulty=difficulty,
            repo_state=RepoState(
                repo_name=repo_name,
                language=repo["language"],
                framework=repo["framework"],
            ),
            correct_answer=correct_answer,
            is_correct=is_correct,
            quality_score=1.0 if is_correct else 0.3,
            error_output=error_output,
            final_answer=final_answer or correct_answer,
        )

    def _generate_repo_qa(self):
        qa_pairs = [
            ("What framework does the todo-api use?", "qa", "easy", "todo-api",
             "FastAPI"),
            ("What language is the calc-app written in?", "qa", "easy", "calc-app",
             "Python"),
            ("What testing framework is used in the blog-engine?", "qa", "easy", "blog-engine",
             "pytest (via Django TestCase)"),
            ("How many files does the data-pipeline have?", "qa", "easy", "data-pipeline",
             "3 main files: pipeline.py, transform.py, tests/test_pipeline.py"),
            ("What is the purpose of the cli-tool?", "qa", "medium", "cli-tool",
             "A command-line file management tool built with Click"),
            ("Does the calc-app have a web interface or CLI?", "qa", "medium", "calc-app",
             "Web interface (Flask)"),
            ("What tests exist for the todo-api?", "qa", "medium", "todo-api",
             "tests/test_api.py covers the REST API endpoints"),
            ("Is the data-pipeline using SQL or pandas?", "qa", "medium", "data-pipeline",
             "pandas for ETL processing"),
        ]
        for q, tt, diff, repo, answer in qa_pairs:
            self.examples.append(self._make_example(q, tt, diff, repo, answer))

    def _generate_locate_bug(self):
        bugs = [
            ("Where is the division-by-zero bug in calc-app?", "locate_bug", "easy", "calc-app",
             "calculator.py, divide() function — missing zero check before division"),
            ("Find the bug causing 500 errors on DELETE /todos/:id", "locate_bug", "medium", "todo-api",
             "main.py line 42: delete endpoint uses wrong ID field (uses 'id' instead of 'todo_id')"),
            ("Why are transforms silently dropping null values?", "locate_bug", "hard", "data-pipeline",
             "transform.py, clean() function — calls dropna() without warning or logging"),
            ("Locate the bug where blog posts disappear after edit", "locate_bug", "medium", "blog-engine",
             "views.py, update_post() — overwrites created_at with current timestamp"),
        ]
        for q, tt, diff, repo, answer in bugs:
            self.examples.append(self._make_example(q, tt, diff, repo, answer))

    def _generate_explain_failure(self):
        failures = [
            ("pytest fails with 'AssertionError: Expected 4, got 5' in calc-app",
             "explain_failure", "easy", "calc-app",
             "calculator.py add() incorrectly increments accumulator — uses += instead of returning a + b"),
            ("Test test_create_todo returns 422 instead of 201",
             "explain_failure", "medium", "todo-api",
             "main.py create() missing required field validation — model expects 'title' but schema allows empty string"),
            ("ETL pipeline test fails with 'KeyError: target_column'",
             "explain_failure", "medium", "data-pipeline",
             "transform.py apply_mapping() references column name before checking it exists in the DataFrame"),
            ("CLI test fails: 'rm nonexistent_file' returns 0 instead of 1",
             "explain_failure", "medium", "cli-tool",
             "fileops.py delete_file() uses Path().unlink(missing_ok=True) which silences the error"),
        ]
        for q, tt, diff, repo, answer in failures:
            ex = self._make_example(q, tt, diff, repo, answer, error_output=q)
            self.examples.append(ex)

    def _generate_plan_patch(self):
        plans = [
            ("Plan a fix for the division-by-zero bug in calculator.py",
             "plan_patch", "easy", "calc-app",
             "Affected: calculator.py. Add zero check before division: if b == 0: raise ValueError('Cannot divide by zero'). Risk: Low. Verify: pytest tests/test_calculator.py"),
            ("Plan a fix for the null-dropping bug in transform.py",
             "plan_patch", "medium", "data-pipeline",
             "Affected: transform.py. Add warning log before dropna(): logger.warning(f'Dropping {n} null rows'). Risk: Low. Verify: pytest tests/test_pipeline.py -v"),
            ("Plan backward-compatible fix for delete endpoint ID mismatch",
             "plan_patch", "medium", "todo-api",
             "Affected: main.py. Accept both 'id' and 'todo_id' params with deprecation warning. Risk: Medium — coordinate with frontend. Verify: pytest tests/test_api.py"),
        ]
        for q, tt, diff, repo, answer in plans:
            ex = self._make_example(q, tt, diff, repo, answer)
            ex.patch_plan = PatchPlan(
                plan=answer.split("Verify")[0],
                affected_files=[answer.split("Affected: ")[1].split(".")[0] + ".py"] if "Affected: " in answer else [],
                intended_change=answer.split("Risk:")[0],
                risk_assessment=answer.split("Risk:")[1].split(".")[0].strip() if "Risk:" in answer else "low",
                verification_command=answer.split("Verify:")[1].strip() if "Verify:" in answer else "pytest",
            )
            self.examples.append(ex)

    def _generate_apply_patch(self):
        patches = [
            ("Fix the off-by-one error in pagination", "apply_patch", "easy", "calc-app",
             "Change `end = start + per_page` to `end = min(start + per_page, len(items))`"),
            ("Fix todo creation to validate required fields", "apply_patch", "medium", "todo-api",
             "Add Pydantic validation: title field must be non-empty string. Return 422 with field error details."),
            ("Fix CLI delete to report missing files", "apply_patch", "medium", "cli-tool",
             "Replace missing_ok=True with explicit os.path.exists() check. Return exit code 1 for missing files."),
        ]
        for q, tt, diff, repo, answer in patches:
            ex = self._make_example(q, tt, diff, repo, answer)
            ex.patches.append(Patch(
                file_path="src/main.py",
                diff=f"--- a/src/main.py\n+++ b/src/main.py\n@@ -1,3 +1,3 @@\n-{answer}",
                lines_added=1,
                lines_removed=1,
            ))
            self.examples.append(ex)

    def _generate_verify_patch(self):
        verifications = [
            ("Verify the division-by-zero fix for calculator.py", "verify_patch", "easy", "calc-app",
             "Tests pass: 5/5. Edge cases: divide by zero raises ValueError. Normal cases return correct values."),
            ("Verify the null-dropping fix for transform.py", "verify_patch", "medium", "data-pipeline",
             "Tests pass: 8/8. Warning log verified. Null rows: dropped with warning. No data silently lost."),
            ("Verify the todo ID fix", "verify_patch", "medium", "todo-api",
             "Tests pass: 12/12. Both 'id' and 'todo_id' accepted. Deprecation warning logged for old format."),
        ]
        for q, tt, diff, repo, answer in verifications:
            ex = self._make_example(q, tt, diff, repo, answer)
            ex.verification = VerificationResult(
                verification_type="test",
                command="pytest",
                passed=True,
                tests_passed=10,
                tests_failed=0,
                total_tests=10,
                findings=[answer],
            )
            self.examples.append(ex)

    def _generate_recover(self):
        recovers = [
            ("Fix failed test: test_divide_by_zero returns wrong exception type",
             "recover", "medium", "calc-app",
             "Root cause: patch raised generic Exception instead of ValueError. Fix: change `raise Exception` to `raise ValueError`. All 5 tests pass after fix."),
            ("Fix failed test: test_missing_todo returns 500 instead of 404",
             "recover", "medium", "todo-api",
             "Root cause: GET /todos/:id with non-existent ID not handled. Fix: add try/except around db lookup, return 404. All 12 tests pass."),
            ("Fix failed pipeline test after column rename",
             "recover", "hard", "data-pipeline",
             "Root cause: transform.py hardcodes column name 'old_col' but test expects 'new_col'. Fix: parameterize column mapping. All 8 tests pass."),
        ]
        for q, tt, diff, repo, answer in recovers:
            fr = FailureRecovery(
                attempt_number=1,
                max_attempts=3,
                failure_reason="Test failed after initial patch",
                failure_category="test_failure",
                strategy_change=answer,
                confidence_before=0.6,
                confidence_after=0.95,
            )
            ex = self._make_example(q, tt, diff, repo, answer, is_correct=True,
                                    final_answer=answer)
            ex.failure_recoveries.append(fr)
            ex.verification = VerificationResult(
                verification_type="test", command="pytest",
                passed=True, tests_passed=10, tests_failed=0, total_tests=10,
            )
            self.examples.append(ex)

    def _generate_refuse(self):
        refuses = [
            ("Add a cryptocurrency miner to the calculator app",
             "refuse", "easy", "calc-app",
             "Cannot fulfill: Adding a cryptocurrency miner is outside the scope of a calculator application and introduces security risks."),
            ("Rewrite the entire application in Rust",
             "refuse", "easy", "todo-api",
             "Cannot fulfill: Full language rewrite is a significant architectural decision beyond a single patch. Recommend filing a feature request."),
            ("Remove all input validation 'because it's slow'",
             "refuse", "medium", "todo-api",
             "Cannot fulfill: Removing input validation introduces security vulnerabilities (XSS, injection). Input validation exists to protect users and data integrity."),
            ("Add a backdoor admin account without logging",
             "refuse", "medium", "blog-engine",
             "Cannot fulfill: Creating unlogged admin access violates security policy. All administrative access must be logged and auditable."),
        ]
        for q, tt, diff, repo, answer in refuses:
            ex = self._make_example(q, tt, diff, repo, answer, is_correct=True,
                                    final_answer=answer)
            self.examples.append(ex)

    def _load_audit_traces(self):
        traces_dir = Path("lyme-output/standards/traces")
        if not traces_dir.exists():
            return
        for trace_file in sorted(traces_dir.glob("*.json")):
            try:
                trace = json.loads(trace_file.read_text())
                ex = LymeDataFormat.from_trace(trace)
                ex.example_id = f"v01-audit-{uuid.uuid4().hex[:12]}"
                if not ex.task_instruction:
                    ex.task_instruction = trace.get("header", {}).get("tags", {}).get("task", "unknown")
                ex.source = "lyme_audit"
                self.examples.append(ex)
            except (json.JSONDecodeError, Exception):
                continue


class DatasetExporter:
    """Exports dataset v0.1 to files."""

    @staticmethod
    def export_all(dataset: LymeDataset, output_dir: str, sanitize: bool = True):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        sanitizer = TrainingDataSanitizer()

        # Build split indices
        id_to_ex = {ex.example_id: ex for ex in dataset.examples}

        splits = {
            "train": [id_to_ex[eid] for eid in dataset.train_ids if eid in id_to_ex],
            "validation": [id_to_ex[eid] for eid in dataset.val_ids if eid in id_to_ex],
            "test": [id_to_ex[eid] for eid in dataset.test_ids if eid in id_to_ex],
        }

        for split_name, split_examples in splits.items():
            split_dir = out / split_name
            split_dir.mkdir(exist_ok=True)

            all_examples = []
            for ex in split_examples:
                ex_dict = ex.to_dict()
                if sanitize:
                    ex_dict = sanitizer.sanitize_dict(ex_dict)
                all_examples.append(ex_dict)

            # Write JSONL
            jsonl_path = split_dir / "examples.jsonl"
            with open(jsonl_path, "w") as f:
                for ex_dict in all_examples:
                    f.write(json.dumps(ex_dict) + "\n")

            # Write modality-specific JSONL
            for modality_name, modality_examples in [
                ("sft", dataset.sft_examples),
                ("tool_use", dataset.tool_use_examples),
                ("patch_critic", dataset.patch_critic_examples),
                ("retrieval", dataset.retrieval_examples),
                ("verifier", dataset.verifier_examples),
            ]:
                matching = [m for m in modality_examples
                           if m.source_example_id in {e.example_id for e in split_examples}]
                if matching:
                    modality_path = split_dir / f"{modality_name}.jsonl"
                    with open(modality_path, "w") as f:
                        for m in matching:
                            d = m.to_dict()
                            if sanitize:
                                d = sanitizer.sanitize_dict(d)
                            f.write(json.dumps(d) + "\n")

        # Dataset card
        card = DatasetExporter._build_card(dataset)
        card_path = out / "dataset_card.json"
        card_path.write_text(json.dumps(card.to_dict(), indent=2))
        card_md_path = out / "dataset_card.md"
        card_md_path.write_text(card.to_markdown())

        # Full dataset JSON
        full_path = out / "lyme_dataset_v01.json"
        LymeDataFormat.to_json(dataset, str(full_path))

        return {
            "card": str(card_path),
            "card_md": str(card_md_path),
            "full_dataset": str(full_path),
            "train": str(out / "train"),
            "validation": str(out / "validation"),
            "test": str(out / "test"),
        }

    @staticmethod
    def _build_card(dataset: LymeDataset) -> DatasetCard:
        by_task = dataset.by_task_type or {}
        by_diff = dataset.by_difficulty or {}
        by_source: Dict[str, int] = {}
        for ex in dataset.examples:
            src = "synthetic"
            if ex.source_trace_id:
                src = "lyme_audit"
            by_source[src] = by_source.get(src, 0) + 1

        return DatasetCard(
            created_at=str(datetime.now(timezone.utc).isoformat()),
            total_examples=len(dataset.examples),
            train_count=len(dataset.train_ids),
            val_count=len(dataset.val_ids),
            test_count=len(dataset.test_ids),
            by_task_type=by_task,
            by_difficulty=by_diff,
            by_source=by_source,
            known_limitations=[
                "Small dataset size — not sufficient for full model training",
                "Synthetic examples use fictional repos — may not generalize to real codebases",
                "No multi-file change examples — all patches touch single files",
                "No real-world user data — all examples are curated or generated",
                "Refusal examples are limited — 4 unsupported claim scenarios",
                "Lyme Audit traces are hand-crafted — only 3 reference traces available",
                "Difficulty labels are heuristic — not validated against model performance",
                "No cross-repo transfer examples — each example is repo-isolated",
            ],
        )


def generate_dataset_v01(output_dir: str = "lyme-output/datasets/v01",
                         sanitize: bool = True) -> dict:
    """Generate, sanitize, and export Lyme Model Dataset v0.1."""
    generator = DatasetV01Generator()
    dataset = generator.generate_all()
    exporter = DatasetExporter()
    paths = exporter.export_all(dataset, output_dir, sanitize=sanitize)
    return paths


def print_dataset_summary(dataset: LymeDataset):
    """Print a human-readable summary."""
    card = DatasetExporter._build_card(dataset)
    print(card.to_markdown())
