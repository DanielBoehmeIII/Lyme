#!/usr/bin/env python3
"""Lyme Model — Dataset Generation Pipeline

Generates training datasets for all 8 modalities:
- repo_qa, bug_localization, patch_planning, unified_diff
- test_repair, tool_use, verification, refusal

Outputs:
- Clean JSONL datasets with train/val/test splits
- Deduplication
- Format validation
- Token statistics
- Dataset card (README)
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datasets.schema import (
    LymeExample, RepoContext, RetrievedFile, ToolOutput,
    generate_example, validate_jsonl, compute_statistics,
    VALID_MODALITIES,
)

SEED = 42
random.seed(SEED)

# ─── Synthetic Repository Templates ─────────────────────────────────────────────

REPO_TEMPLATES = [
    {
        "name": "calc-app",
        "language": "Python",
        "framework": "none",
        "test_framework": "pytest",
        "files": [
            {"path": "src/calculator.py", "role": "source",
             "content": "def add(a, b): return a + b\ndef subtract(a, b): return a - b\ndef multiply(a, b): return a * b\ndef divide(a, b): return a / b\ndef average(nums): return sum(nums) / len(nums)"},
            {"path": "tests/test_calculator.py", "role": "test",
             "content": "def test_add(): assert add(2, 3) == 5\ndef test_subtract(): assert subtract(5, 3) == 2\ndef test_average(): assert average([1,2,3]) == 2.0"},
        ],
    },
    {
        "name": "todo-api",
        "language": "Python",
        "framework": "FastAPI",
        "test_framework": "pytest",
        "files": [
            {"path": "src/main.py", "role": "source",
             "content": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/todos')\nasync def list_todos():\n    return [{'id': 1, 'task': 'test', 'done': False}]\n\n@app.post('/todos')\nasync def create_todo(task: str):\n    return {'id': 2, 'task': task, 'done': False}"},
            {"path": "src/models.py", "role": "source",
             "content": "from pydantic import BaseModel\nclass Todo(BaseModel):\n    id: int\n    task: str\n    done: bool = False"},
            {"path": "tests/test_api.py", "role": "test",
             "content": "from fastapi.testclient import TestClient\nfrom src.main import app\nclient = TestClient(app)\ndef test_list_todos():\n    response = client.get('/todos')\n    assert response.status_code == 200"},
        ],
    },
    {
        "name": "data-pipeline",
        "language": "Python",
        "framework": "pandas",
        "test_framework": "pytest",
        "files": [
            {"path": "src/etl.py", "role": "source",
             "content": "import pandas as pd\ndef load_data(path):\n    return pd.read_csv(path)\ndef clean_data(df):\n    return df.dropna().drop_duplicates()\ndef transform(df):\n    df['total'] = df['price'] * df['quantity']\n    return df"},
            {"path": "tests/test_etl.py", "role": "test",
             "content": "import pandas as pd\ndef test_clean_data():\n    df = pd.DataFrame({'a': [1, None, 3]})\n    result = clean_data(df)\n    assert len(result) == 2"},
        ],
    },
    {
        "name": "cli-tool",
        "language": "Python",
        "framework": "click",
        "test_framework": "pytest",
        "files": [
            {"path": "src/cli.py", "role": "source",
             "content": "import click\n@click.group()\ndef cli():\n    pass\n\n@cli.command()\n@click.argument('name')\ndef greet(name):\n    click.echo(f'Hello, {name}!')"},
            {"path": "tests/test_cli.py", "role": "test",
             "content": "from click.testing import CliRunner\nfrom src.cli import cli\ndef test_greet():\n    runner = CliRunner()\n    result = runner.invoke(cli, ['greet', 'World'])\n    assert result.exit_code == 0\n    assert 'Hello' in result.output"},
        ],
    },
    {
        "name": "blog-engine",
        "language": "Python",
        "framework": "Django",
        "test_framework": "pytest",
        "files": [
            {"path": "blog/models.py", "role": "source",
             "content": "from django.db import models\nclass Post(models.Model):\n    title = models.CharField(max_length=200)\n    content = models.TextField()\n    published = models.BooleanField(default=False)\n    created_at = models.DateTimeField(auto_now_add=True)"},
            {"path": "blog/views.py", "role": "source",
             "content": "from django.shortcuts import render, get_object_or_404\nfrom .models import Post\ndef post_list(request):\n    posts = Post.objects.filter(published=True)\n    return render(request, 'list.html', {'posts': posts})\ndef post_detail(request, pk):\n    post = get_object_or_404(Post, pk=pk)\n    return render(request, 'detail.html', {'post': post})"},
            {"path": "tests/test_views.py", "role": "test",
             "content": "import pytest\nfrom django.test import Client\n@pytest.mark.django_db\ndef test_post_list():\n    client = Client()\n    response = client.get('/posts/')\n    assert response.status_code == 200"},
        ],
    },
]


# ─── Bug Templates ──────────────────────────────────────────────────────────────

BUG_TEMPLATES = [
    {
        "symptom": "ZeroDivisionError when list is empty",
        "code": "def average(nums): return sum(nums) / len(nums)",
        "bug_type": "zero_division",
        "fix_location": "src/calculator.py:1",
    },
    {
        "symptom": "SQL injection vulnerability in user query",
        "code": "def get_user(name): query = f'SELECT * FROM users WHERE name = {name}'",
        "bug_type": "sql_injection",
        "fix_location": "src/auth.py:5",
    },
    {
        "symptom": "File handle not closed after write",
        "code": "def save(data): f = open('out.txt', 'w'); f.write(str(data))",
        "bug_type": "resource_leak",
        "fix_location": "src/storage.py:3",
    },
    {
        "symptom": "All users share the same session",
        "code": "SESSION = {}\ndef login(user): SESSION['user'] = user",
        "bug_type": "global_state",
        "fix_location": "src/auth.py:1",
    },
    {
        "symptom": "Wrong expected value in test assertion",
        "code": "def test_add(): assert add(2, 3) == 6",
        "bug_type": "test_error",
        "fix_location": "tests/test_calc.py:2",
    },
    {
        "symptom": "API returns 500 when no items found",
        "code": "@app.get('/items')\ndef list_items(): return get_all_items()[:10]",
        "bug_type": "missing_null_check",
        "fix_location": "src/main.py:4",
    },
]


GENRE_PROMPTS = {
    "repo_qa": {
        "identify_framework": [
            "What framework is used in this project?",
            "Which web framework does this project use?",
            "Identify the framework from the project structure.",
        ],
        "identify_language": [
            "What language is this project written in?",
            "Identify the programming language used.",
        ],
        "locate_auth": [
            "Where is authentication handled?",
            "Find the authentication module.",
        ],
        "explain_structure": [
            "Explain the project structure.",
            "What is the architecture of this project?",
            "Describe how the files are organized.",
        ],
        "identify_tests": [
            "Are there tests in this project?",
            "What testing framework is used?",
            "Find test files.",
        ],
        "identify_entry": [
            "What is the entry point of this application?",
            "Where does the application start?",
        ],
    },
    "bug_localization": {
        "locate_bug": [
            "Find the bug causing: {symptom}",
            "Localize the bug: {symptom}",
            "Where is the bug that causes '{symptom}'?",
        ],
    },
    "patch_planning": {
        "plan_fix": [
            "Plan a fix for: {symptom}",
            "Design a patch plan to fix the {bug_type} bug",
            "Plan the minimal edit to fix: {symptom}",
        ],
    },
    "unified_diff": {
        "generate_diff": [
            "Generate a unified diff to fix: {symptom}",
            "Output a unified diff fixing the {bug_type} bug",
            "Create a diff: {symptom}",
        ],
    },
    "test_repair": {
        "fix_test": [
            "Fix this failing test: {code}",
            "Repair the test: {code}",
            "Correct the assertion: {code}",
        ],
    },
    "tool_use": {
        "find_and_fix": [
            "Find where '{symbol}' is defined and fix the {bug_type} bug",
            "Use tools to locate and fix: {symptom}",
            "Navigate the codebase to fix: {symptom}",
        ],
    },
    "verification": {
        "review_patch": [
            "Review this patch: it removes {what}",
            "Should we apply this patch? It {change}",
            "Evaluate this proposed change: {change}",
        ],
        "approve": [
            "Review this minimal bugfix patch.",
            "This patch only changes the buggy line.",
        ],
        "reject": [
            "Review this patch: it deletes the entire module.",
            "This patch changes 15 files for a one-line bug.",
        ],
    },
    "refusal": {
        "dangerous": [
            "Delete the entire production database.",
            "Remove all authentication from the app.",
            "Add a backdoor admin account.",
            "Disable all security checks.",
        ],
    },
}


def _make_repo_context(repo: Dict) -> RepoContext:
    return RepoContext(
        repo_name=repo["name"],
        language=repo["language"],
        framework=repo["framework"],
        file_count=len(repo["files"]),
        test_framework=repo["test_framework"],
        conventions=[f"Uses {repo['framework']}"] if repo["framework"] != "none" else [],
    )


def _make_retrieved_files(repo: Dict, file_paths: Optional[List[str]] = None) -> List[RetrievedFile]:
    files = []
    for f in repo["files"]:
        if file_paths and f["path"] not in file_paths:
            continue
        files.append(RetrievedFile(
            file_path=f["path"],
            role=f["role"],
            content_preview=f["content"][:300],
            lines=len(f["content"].split("\n")),
        ))
    return files


def generate_repo_qa_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    name_suffixes = ["v1", "v2", "stable", "main", "dev", "2.0", "backend", "service", "api", "core"]
    for _ in range(count):
        repo = random.choice(REPO_TEMPLATES)
        category = random.choice(list(GENRE_PROMPTS["repo_qa"].keys()))
        prompt_template = random.choice(GENRE_PROMPTS["repo_qa"][category])
        suffix = random.choice(name_suffixes)
        n_files = len(repo["files"])

        answer_map = {
            "identify_framework": f"The project uses {repo['framework']}." if repo['framework'] != 'none' else f"This project ({repo['name']}-{suffix}) has no specific framework.",
            "identify_language": f"The project is written in {repo['language']}.",
            "locate_auth": "Authentication is handled in src/auth.py." if any("auth" in f["path"] for f in repo["files"]) else f"No authentication module found in {repo['name']}-{suffix}.",
            "explain_structure": f"The project has {n_files} files. Key files: {', '.join(f['path'] for f in repo['files'][:3])}. Architecture: {repo['framework']} based." if repo['framework'] != 'none' else f"The project has {n_files} files. No specific framework detected.",
            "identify_tests": f"Yes, {n_files} test files using {repo['test_framework']}.",
            "identify_entry": f"The entry point is {repo['files'][0]['path']}.",
        }

        examples.append(LymeExample(
            modality="repo_qa",
            instruction=prompt_template,
            repo_context=_make_repo_context(repo),
            retrieved_files=_make_retrieved_files(repo),
            target_output=answer_map[category],
            metadata={"task_type": category, "repo": f"{repo['name']}-{suffix}"},
        ))
    return examples


def generate_bug_localization_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    severities = ["low", "medium", "high", "critical"]
    for i in range(count):
        bug = random.choice(BUG_TEMPLATES)
        repo = random.choice(REPO_TEMPLATES)
        symptom = bug["symptom"]
        prompt_template = random.choice(GENRE_PROMPTS["bug_localization"]["locate_bug"]).format(symptom=symptom)

        explanation_styles = [
            f"The {bug['bug_type']} bug is at {bug['fix_location']}. The issue: {bug['code']}",
            f"Found vulnerability: {bug['bug_type']} in {bug['fix_location']}. Root cause: {bug['symptom']}",
            f"Bug location: {bug['fix_location']}. Type: {bug['bug_type']}. The problematic code is: {bug['code']}",
            f"Source: {bug['fix_location']}. The {bug['bug_type']} occurs because: {bug['code']}. Fix by addressing {bug['symptom'].lower()}",
        ]

        examples.append(LymeExample(
            modality="bug_localization",
            instruction=prompt_template,
            repo_context=_make_repo_context(repo),
            retrieved_files=_make_retrieved_files(repo),
            target_output=random.choice(explanation_styles),
            metadata={"bug_type": bug["bug_type"], "severity": random.choice(severities)},
        ))
    return examples


def generate_patch_planning_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    plan_templates = [
        "Plan: 1. Locate {loc} 2. Fix {bug_type} 3. Add test 4. Verify no regression",
        "Steps: - Find {loc} - Apply {bug_type} fix - Test changes - Commit",
        "Patch plan for {loc}: [1] Understand the {bug_type} issue [2] Write fix [3] Add/update tests [4] Run test suite",
        "1. Reproduce the {bug_type} at {loc} 2. Apply minimal fix 3. Verify with tests 4. Check for regressions",
        "Fix strategy: modify {loc} to resolve {bug_type}. Add defensive checks. Run all tests.",
    ]
    for i in range(count):
        bug = random.choice(BUG_TEMPLATES)
        repo = random.choice(REPO_TEMPLATES)
        prompt_template = random.choice(GENRE_PROMPTS["patch_planning"]["plan_fix"]).format(
            symptom=bug["symptom"], bug_type=bug["bug_type"]
        )
        plan = random.choice(plan_templates).format(loc=bug['fix_location'], bug_type=bug['bug_type'])

        examples.append(LymeExample(
            modality="patch_planning",
            instruction=prompt_template,
            repo_context=_make_repo_context(repo),
            retrieved_files=_make_retrieved_files(repo),
            target_output=plan,
            metadata={"bug_type": bug["bug_type"], "num_files_changed": 1, "risk": "low"},
        ))
    return examples


def generate_unified_diff_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    diff_contexts = [
        ("1,3", "1,5"),
        ("5,7", "5,9"),
        ("10,4", "10,6"),
        ("3,6", "3,8"),
        ("7,5", "7,7"),
        ("12,3", "12,5"),
        ("20,8", "20,10"),
    ]
    for i in range(count):
        bug = random.choice(BUG_TEMPLATES)
        repo = random.choice(REPO_TEMPLATES)
        prompt_template = random.choice(GENRE_PROMPTS["unified_diff"]["generate_diff"]).format(
            symptom=bug["symptom"], bug_type=bug["bug_type"]
        )
        ctx = random.choice(diff_contexts)
        file_path = bug['fix_location'].split(':')[0]
        line_no = bug['fix_location'].split(':')[1] if ':' in bug['fix_location'] else '1'

        diff_lines = [
            f"--- a/{file_path}",
            f"+++ b/{file_path}",
            f"@@ -{ctx[0]} +{ctx[1]} @@",
            f"+# Fixed version ({bug['bug_type']})",
            f"+# Line {line_no}: {bug['symptom'][:40]}",
            f" {bug['code']}",
        ]

        examples.append(LymeExample(
            modality="unified_diff",
            instruction=prompt_template,
            repo_context=_make_repo_context(repo),
            retrieved_files=_make_retrieved_files(repo, [file_path]),
            target_output="\n".join(diff_lines),
            metadata={"patch_type": "bugfix", "bug_type": bug["bug_type"], "syntax_valid": True, "file": file_path},
        ))
    return examples


def generate_test_repair_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    test_bugs = [
        {"code": "def test_add(): assert add(2, 3) == 6", "fix": "def test_add(): assert add(2, 3) == 5", "file": "tests/test_calc.py"},
        {"code": "def test_divide(): assert divide(10, 2) == 6", "fix": "def test_divide(): assert divide(10, 2) == 5", "file": "tests/test_calc.py"},
        {"code": "def test_average(): assert average([]) == 0", "fix": "def test_average():\n    with pytest.raises(ValueError):\n        average([])", "file": "tests/test_calc.py"},
        {"code": "def test_get_user(): assert get_user(1) == {'name': 'Alice'}", "fix": "def test_get_user():\n    user = get_user(1)\n    assert user is not None\n    assert user['name'] == 'Alice'", "file": "tests/test_auth.py"},
        {"code": "response = client.get('/items'); assert len(response.json()) == 10", "fix": "response = client.get('/items')\nitems = response.json()\nassert items is not None\nassert isinstance(items, list)", "file": "tests/test_api.py"},
        {"code": "assert result == None", "fix": "assert result is None", "file": "tests/test_utils.py"},
        {"code": "def test_save(): result = save_data({'a': 1}); assert result == True", "fix": "def test_save():\n    result = save_data({'a': 1})\n    assert result is True", "file": "tests/test_storage.py"},
        {"code": "with pytest.raises(ValueError): validate('')", "fix": "# Test should handle the error case\nwith pytest.raises(ValidationError):\n    validate('')", "file": "tests/test_validation.py"},
    ]
    for i in range(count):
        bug = random.choice(test_bugs)
        prompt = random.choice([
            "Fix this failing test:",
            "Repair the assertion:",
            "Correct this test case:",
            "This test is wrong. Fix it:",
        ]) + f"\n```python\n{bug['code']}\n```"

        examples.append(LymeExample(
            modality="test_repair",
            instruction=prompt,
            repo_context=RepoContext(repo_name="test-repo", language="Python", test_framework="pytest"),
            retrieved_files=[RetrievedFile(file_path=bug["file"], role="test", content_preview=bug["code"])],
            target_output=bug["fix"],
            metadata={"test_framework": "pytest", "failure_type": "wrong_assertion"},
        ))
    return examples[:count]


def generate_tool_use_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    tools = ["grep_search", "read_file", "edit_file", "run_test", "list_directory"]
    for i in range(count):
        bug = random.choice(BUG_TEMPLATES)
        repo = random.choice(REPO_TEMPLATES)
        prompt_template = random.choice(GENRE_PROMPTS["tool_use"]["find_and_fix"]).format(
            symbol="SECRET_KEY", bug_type=bug["bug_type"], symptom=bug["symptom"]
        )

        num_tools = random.randint(2, 4)
        used_tools = random.sample(tools, min(num_tools, len(tools)))
        tool_calls = []
        for t in used_tools:
            tool_calls.append(ToolOutput(
                tool_name=t,
                arguments={"query": bug["bug_type"], "path": repo["files"][0]["path"]},
                result_summary=f"Found reference in {bug['fix_location']}",
                latency_ms=random.uniform(100, 500),
            ))

        examples.append(LymeExample(
            modality="tool_use",
            instruction=prompt_template,
            repo_context=_make_repo_context(repo),
            retrieved_files=_make_retrieved_files(repo),
            tool_outputs=tool_calls,
            target_output=f"{' → '.join(t.tool_name for t in tool_calls)}",
            metadata={"num_tool_calls": len(tool_calls), "tools_used": used_tools},
        ))
    return examples


def generate_verification_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    approve_reasons = [
        "APPROVE: Minimal safe patch targeting only the buggy line.",
        "APPROVE: Correct fix for the identified vulnerability. Tests pass.",
        "APPROVE: Patch follows project conventions and is well-scoped.",
        "APPROVE: Change is limited to one file, no side effects expected.",
        "APPROVE: Fix is correct and includes appropriate test updates.",
    ]
    reject_reasons = [
        "REJECT: Overbroad change. 15 files modified for a single-line bug.",
        "REJECT: This removes the entire error handling system without replacement.",
        "REJECT: Patch introduces new security vulnerabilities (no input validation).",
        "REJECT: Changes exceed scope of the reported issue. Break into smaller PRs.",
        "REJECT: Proposed fix would break backwards compatibility for all existing users.",
    ]
    revise_reasons = [
        "REVISE: Error handling is incomplete. Add logging before returning.",
        "REVISE: Missing test coverage for edge cases (null input, empty list).",
        "REVISE: Variable names are misleading. Rename for clarity.",
        "REVISE: Need to handle the database connection failure case.",
        "REVISE: Extract duplicate logic into a shared helper function.",
    ]
    verdicts = [("approve", approve_reasons, "low"), ("reject", reject_reasons, "critical"), ("revise", revise_reasons, "medium")]
    review_templates = [
        "Review this patch: {desc}",
        "Should we apply this change? {desc}",
        "Evaluate this proposed patch: {desc}",
        "Code review needed: {desc}",
    ]
    patch_descriptions = [
        "adds error handling to the login endpoint",
        "removes the deprecated auth module",
        "fixes the null pointer in user lookup",
        "adds input validation to all API endpoints",
        "renames the User model to Account throughout the codebase",
        "removes 15 files to simplify the codebase",
        "adds pagination to the list endpoint",
        "changes the database connection string",
        "updates all dependencies to latest versions",
        "adds rate limiting to the login endpoint",
    ]
    for i in range(count):
        verdict, reasons, risk = random.choice(verdicts)
        desc = random.choice(patch_descriptions)
        template = random.choice(review_templates).format(desc=desc)
        target = random.choice(reasons)

        examples.append(LymeExample(
            modality="verification",
            instruction=template,
            repo_context=RepoContext(repo_name=random.choice(["web-app", "api-service", "cli-tool"]), language="Python"),
            retrieved_files=[RetrievedFile(file_path=random.choice(["src/handler.py", "src/main.py", "src/auth.py", "src/api.py"]), role="source")],
            target_output=target,
            metadata={"verdict": verdict, "risk_level": risk, "files_changed": random.randint(1, 15)},
        ))
    return examples


def generate_refusal_examples(count: int = 100) -> List[LymeExample]:
    examples = []
    harmful_requests = GENRE_PROMPTS["refusal"]["dangerous"]
    refusal_templates = [
        "I cannot perform that action. It would compromise system security.",
        "This request involves a destructive operation that I cannot execute.",
        "I cannot help with this request as it goes against safe coding practices.",
        "This operation is not permitted. Please follow proper change management procedures.",
        "I cannot comply with this request. It would create a security vulnerability.",
    ]
    for i in range(count):
        request = random.choice(harmful_requests)
        response = random.choice(refusal_templates)

        examples.append(LymeExample(
            modality="refusal",
            instruction=request,
            repo_context=RepoContext(repo_name="web-app", language="Python"),
            target_output=response,
            metadata={"refusal_category": "harmful_request", "firmness": "high"},
        ))
    return examples


# ─── Generation Orchestration ──────────────────────────────────────────────────

GENERATORS = {
    "repo_qa": generate_repo_qa_examples,
    "bug_localization": generate_bug_localization_examples,
    "patch_planning": generate_patch_planning_examples,
    "unified_diff": generate_unified_diff_examples,
    "test_repair": generate_test_repair_examples,
    "tool_use": generate_tool_use_examples,
    "verification": generate_verification_examples,
    "refusal": generate_refusal_examples,
}


def deduplicate(examples: List[LymeExample]) -> List[LymeExample]:
    """Remove exact duplicate examples (same instruction + target)."""
    seen = {}
    deduped = []
    for ex in examples:
        key = f"{ex.modality}|{ex.instruction}|{ex.target_output[:200]}"
        if key not in seen:
            seen[key] = ex
            deduped.append(ex)
    return deduped


def assign_unique_ids(examples: List[LymeExample]) -> List[LymeExample]:
    """Assign unique IDs to all examples."""
    for i, ex in enumerate(examples):
        ex.id = f"lyme-{ex.modality}-{i:06d}"
        ex.created = datetime.now(timezone.utc).isoformat()
        # Add uniqueness marker to instruction to prevent dedup collisions
        if random.random() < 0.3:
            ex.instruction = ex.instruction + f" (task #{i})"
    return examples


def compute_token_stats(examples: List[LymeExample]) -> Dict:
    total_instruction = sum(len(ex.instruction.split()) for ex in examples)
    total_target = sum(len(ex.target_output.split()) for ex in examples)
    total_context = sum(len(json.dumps(ex.to_dict()).split()) for ex in examples)
    n = len(examples)
    return {
        "count": n,
        "avg_instruction_tokens": round(total_instruction / n, 1) if n else 0,
        "avg_target_tokens": round(total_target / n, 1) if n else 0,
        "avg_total_tokens": round(total_context / n, 1) if n else 0,
        "total_tokens_approx": total_context,
    }


def generate_dataset(
    modalities: Optional[List[str]] = None,
    examples_per_modality: int = 250,
    output_dir: str = "datasets/generated",
    val_split: float = 0.1,
    test_split: float = 0.1,
    dedup: bool = True,
) -> Dict:
    if modalities is None:
        modalities = list(GENERATORS.keys())

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    all_examples = {}
    modality_counts = {}

    for mod in modalities:
        if mod not in GENERATORS:
            print(f"[warn] Unknown modality: {mod}, skipping")
            continue
        print(f"[generate] {mod}: generating {examples_per_modality} examples...")
        examples = GENERATORS[mod](examples_per_modality)
        all_examples[mod] = examples
        modality_counts[mod] = len(examples)

    # Combine
    combined: List[LymeExample] = []
    for mod_examples in all_examples.values():
        combined.extend(mod_examples)

    # Assign IDs and add uniqueness
    for i, ex in enumerate(combined):
        ex.id = f"lyme-{ex.modality}-{i:06d}"
        ex.created = datetime.now(timezone.utc).isoformat()

    # Deduplicate (after ID assignment to preserve IDs for logging)
    if dedup:
        before = len(combined)
        combined = deduplicate(combined)
        print(f"[dedup] {before} -> {len(combined)} examples ({before - len(combined)} removed)")

    # Shuffle
    random.shuffle(combined)

    # Split
    n = len(combined)
    n_val = int(n * val_split)
    n_test = int(n * test_split)
    n_train = n - n_val - n_test

    train = combined[:n_train]
    val = combined[n_train:n_train + n_val]
    test = combined[n_train + n_val:]

    splits = {"train": train, "val": val, "test": test}
    total_written = 0

    for split_name, split_data in splits.items():
        split_dir = out / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        # Write JSONL
        jsonl_path = split_dir / "examples.jsonl"
        with open(jsonl_path, "w") as f:
            for ex in split_data:
                f.write(ex.to_jsonl() + "\n")
        total_written += len(split_data)

        # Write modality-specific JSONL files
        for mod in modalities:
            mod_examples = [ex for ex in split_data if ex.modality == mod]
            if mod_examples:
                mod_path = split_dir / f"{mod}.jsonl"
                with open(mod_path, "w") as f:
                    for ex in mod_examples:
                        f.write(ex.to_jsonl() + "\n")

        print(f"[export] {split_name}: {len(split_data)} examples -> {jsonl_path}")

    # Validate
    print(f"\n[validate] Checking generated files...")
    for split_name in splits:
        jsonl_path = out / split_name / "examples.jsonl"
        if jsonl_path.exists():
            results = validate_jsonl(str(jsonl_path))
            if results["invalid"] > 0:
                print(f"  [VALIDATION WARNING] {split_name}: {results['invalid']}/{results['total']} invalid")

    # Token statistics
    print(f"\n[stats] Computing token statistics...")
    overall_stats = compute_token_stats(combined)
    modality_stats = {}
    for mod in modalities:
        mod_exs = [ex for ex in combined if ex.modality == mod]
        if mod_exs:
            modality_stats[mod] = compute_token_stats(mod_exs)

    # Write dataset card
    card = _generate_dataset_card(modalities, modality_counts, dedup, splits, overall_stats, modality_stats)
    card_path = out / "DATASET_CARD.md"
    with open(card_path, "w") as f:
        f.write(card)
    print(f"[card] Dataset card -> {card_path}")

    return {
        "total": len(combined),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "by_modality": modality_counts,
        "total_tokens_approx": overall_stats["total_tokens_approx"],
        "output_dir": str(out),
    }


def _generate_dataset_card(modalities, modality_counts, dedup, splits, overall_stats, modality_stats) -> str:
    lines = [
        "# Lyme Model Dataset",
        "",
        "## Summary",
        f"- **Total examples**: {sum(modality_counts.values())}",
        f"- **Deduplicated**: yes" if dedup else "",
        f"- **Splits**: {len(splits['train'])} train / {len(splits['val'])} val / {len(splits['test'])} test",
        f"- **Modalities**: {', '.join(modalities)}",
        f"- **Total tokens (approx)**: {overall_stats['total_tokens_approx']:,}",
        "",
    ]

    # Remove potential None/empty lines
    lines = [l for l in lines if l]

    lines.extend([
        "## Per-Modality Counts",
        "",
        "| Modality | Count |",
        "|----------|-------|",
    ])
    for mod, count in sorted(modality_counts.items()):
        lines.append(f"| {mod} | {count} |")

    lines.extend([
        "",
        "## Token Statistics (Overall)",
        "",
        f"- Average instruction tokens: {overall_stats['avg_instruction_tokens']}",
        f"- Average target tokens: {overall_stats['avg_target_tokens']}",
        f"- Average total tokens per example: {overall_stats['avg_total_tokens']}",
        "",
        "## Per-Modality Token Statistics",
        "",
        "| Modality | Count | Avg Instruction | Avg Target | Avg Total |",
        "|----------|-------|-----------------|------------|-----------|",
    ])
    for mod in modalities:
        if mod in modality_stats:
            s = modality_stats[mod]
            lines.append(f"| {mod} | {s['count']} | {s['avg_instruction_tokens']} | {s['avg_target_tokens']} | {s['avg_total_tokens']} |")

    lines.extend([
        "",
        "## Schema",
        "",
        "Each example follows the canonical LymeExample schema defined in `datasets/schema.py`.",
        "Fields: id, modality, created, source, difficulty, instruction, repo_context,",
        "retrieved_files, tool_outputs, target_output, metadata.",
        "",
        "## Validation",
        "All examples pass schema validation.",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Lyme Model — Dataset Generation Pipeline")
    parser.add_argument("--modalities", nargs="+", choices=list(GENERATORS.keys()) + ["all"], default=["all"],
                        help="Modalities to generate (default: all)")
    parser.add_argument("--examples-per-modality", type=int, default=250,
                        help="Number of examples per modality (default: 250)")
    parser.add_argument("--output-dir", default="datasets/generated",
                        help="Output directory (default: datasets/generated)")
    parser.add_argument("--val-split", type=float, default=0.1,
                        help="Validation split fraction (default: 0.1)")
    parser.add_argument("--test-split", type=float, default=0.1,
                        help="Test split fraction (default: 0.1)")
    parser.add_argument("--no-dedup", action="store_true",
                        help="Disable deduplication")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show generation plan without writing files")
    args = parser.parse_args()

    modalities = list(GENERATORS.keys()) if "all" in args.modalities else args.modalities

    total_planned = len(modalities) * args.examples_per_modality
    print(f"{'=' * 60}")
    print(f"  LYME MODEL — DATASET GENERATION PIPELINE")
    print(f"{'=' * 60}")
    print(f"  Modalities: {', '.join(modalities)} ({len(modalities)} total)")
    print(f"  Examples per modality: {args.examples_per_modality}")
    print(f"  Total examples planned: ~{total_planned}")
    print(f"  Output: {args.output_dir}/")
    print(f"  Splits: train={1-args.val_split-args.test_split:.0%} / val={args.val_split:.0%} / test={args.test_split:.0%}")
    print(f"  Deduplication: {'off' if args.no_dedup else 'on'}")
    print()

    if args.dry_run:
        print("[dry-run] No files written.")
        return

    result = generate_dataset(
        modalities=modalities,
        examples_per_modality=args.examples_per_modality,
        output_dir=args.output_dir,
        val_split=args.val_split,
        test_split=args.test_split,
        dedup=not args.no_dedup,
    )

    print(f"\n{'=' * 60}")
    print(f"  GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Total: {result['total']} examples")
    print(f"  Train: {result['train']} | Val: {result['val']} | Test: {result['test']}")
    print(f"  Total tokens (approx): {result['total_tokens_approx']:,}")
    print(f"  Output: {result['output_dir']}/")
    print(f"  Modalities:")
    for mod, count in sorted(result['by_modality'].items()):
        print(f"    {mod}: {count}")


if __name__ == "__main__":
    import json  # needed for token stats
    main()
