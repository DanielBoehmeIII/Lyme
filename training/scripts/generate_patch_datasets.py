#!/usr/bin/env python3
"""Weeks 8-10: Patch Planning + Unified Diff Dataset Generator.

Generates:
- patch_planning: structured edit plans
- unified_diff: strict unified diff output
- test_repair: failing test repair with diffs

Each with task, relevant files, intended modifications, and verification.
"""

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from datasets.schema import LymeExample, RepoContext, RetrievedFile, generate_example

SEED = 42
random.seed(SEED)

PATCH_SCENARIOS = [
    # Bug fixes
    {
        "type": "bugfix",
        "task": "Fix division by zero in average calculation",
        "file": "src/calculator.py",
        "code_before": "def average(nums):\n    return sum(nums) / len(nums)",
        "code_after": "def average(nums):\n    if not nums:\n        return 0\n    return sum(nums) / len(nums)",
        "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n def average(nums):\n+    if not nums:\n+        return 0\n     return sum(nums) / len(nums)",
        "plan": "1. Add guard clause for empty input at start of average()\n2. Return 0 for empty lists\n3. Keep existing logic for non-empty lists\n4. Add test case for empty list",
        "test_command": "pytest tests/test_calculator.py -v",
    },
    {
        "type": "bugfix",
        "task": "Fix SQL injection vulnerability in user lookup",
        "file": "src/auth.py",
        "code_before": "def get_user(name):\n    query = f\"SELECT * FROM users WHERE name = '{name}'\"\n    return db.execute(query)",
        "code_after": "def get_user(name):\n    query = \"SELECT * FROM users WHERE name = ?\"\n    return db.execute(query, (name,))",
        "diff": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1,3 +1,3 @@\n def get_user(name):\n-    query = f\"SELECT * FROM users WHERE name = '{name}'\"\n-    return db.execute(query)\n+    query = \"SELECT * FROM users WHERE name = ?\"\n+    return db.execute(query, (name,))",
        "plan": "1. Replace f-string with parameterized query\n2. Pass name as parameter to execute()\n3. Remove string interpolation for SQL\n4. Add test with malicious input",
        "test_command": "pytest tests/test_auth.py -v",
    },
    {
        "type": "bugfix",
        "task": "Fix file handle not closed after write",
        "file": "src/storage.py",
        "code_before": "def save_data(data, filename):\n    f = open(filename, 'w')\n    f.write(json.dumps(data))\n    return True",
        "code_after": "def save_data(data, filename):\n    with open(filename, 'w') as f:\n        f.write(json.dumps(data))\n    return True",
        "diff": "--- a/src/storage.py\n+++ b/src/storage.py\n@@ -1,4 +1,3 @@\n def save_data(data, filename):\n-    f = open(filename, 'w')\n-    f.write(json.dumps(data))\n+    with open(filename, 'w') as f:\n+        f.write(json.dumps(data))\n     return True",
        "plan": "1. Replace open() with 'with' statement for auto-close\n2. Nest write inside the with block\n3. Keep return statement\n4. Verify file is properly closed",
        "test_command": "pytest tests/test_storage.py",
    },
    {
        "type": "bugfix",
        "task": "Fix mutable default argument in function",
        "file": "src/utils.py",
        "code_before": "def add_item(item, items=[]):\n    items.append(item)\n    return items",
        "code_after": "def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items",
        "diff": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -1,3 +1,5 @@\n-def add_item(item, items=[]):\n+def add_item(item, items=None):\n+    if items is None:\n+        items = []\n     items.append(item)\n     return items",
        "plan": "1. Change default from [] to None\n2. Add None check inside function\n3. Initialize empty list only when needed\n4. Keep existing logic unchanged",
        "test_command": "pytest tests/test_utils.py",
    },
    # Import repair
    {
        "type": "import_repair",
        "task": "Update imports after module rename",
        "file": "src/main.py",
        "code_before": "from src.old_module import helper\nfrom src.legacy import parser",
        "code_after": "from src.new_module import helper\nfrom src.parser import parser",
        "diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1,2 +1,2 @@\n-from src.old_module import helper\n-from src.legacy import parser\n+from src.new_module import helper\n+from src.parser import parser",
        "plan": "1. Update import path for helper\n2. Update import path for parser\n3. Verify all usages still resolve\n4. Run test suite",
        "test_command": "pytest",
    },
    # Syntax repair
    {
        "type": "syntax_repair",
        "task": "Fix syntax error: missing colon and indentation",
        "file": "src/handler.py",
        "code_before": "def handle(request)\nif request.method == 'GET':\nreturn 'ok'",
        "code_after": "def handle(request):\n    if request.method == 'GET':\n        return 'ok'",
        "diff": "--- a/src/handler.py\n+++ b/src/handler.py\n@@ -1,3 +1,3 @@\n-def handle(request)\n+def handle(request):\n     if request.method == 'GET':\n-    return 'ok'\n+        return 'ok'",
        "plan": "1. Add colon after function signature\n2. Fix indentation of return statement\n3. Validate with python -c 'import src.handler'\n4. Run tests",
        "test_command": "python -c \"import src.handler; print('syntax OK')\"",
    },
    # API rename
    {
        "type": "api_rename",
        "task": "Rename deprecated API method get_users -> fetch_users",
        "file": "src/api.py",
        "code_before": "def get_users():\n    return [{'id': 1, 'name': 'Alice'}]",
        "code_after": "def fetch_users():\n    return [{'id': 1, 'name': 'Alice'}]",
        "diff": "--- a/src/api.py\n+++ b/src/api.py\n@@ -1,2 +1,2 @@\n-def get_users():\n+def fetch_users():\n     return [{'id': 1, 'name': 'Alice'}]",
        "plan": "1. Rename function from get_users to fetch_users\n2. Update all callers\n3. Update tests\n4. Verify everything links",
        "test_command": "pytest tests/test_api.py",
    },
    # Config updates
    {
        "type": "config_update",
        "task": "Update database URL to use environment variable",
        "file": "src/config.py",
        "code_before": "DATABASE_URL = 'postgresql://localhost:5432/app'",
        "code_after": "import os\nDATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost:5432/app')",
        "diff": "--- a/src/config.py\n+++ b/src/config.py\n@@ -1 +1,2 @@\n+import os\n-DATABASE_URL = 'postgresql://localhost:5432/app'\n+DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost:5432/app')",
        "plan": "1. Add os import\n2. Replace hardcoded URL with environment variable\n3. Keep existing URL as fallback\n4. Update tests to use test DB URL",
        "test_command": "pytest tests/test_config.py",
    },
    # Add error handling
    {
        "type": "error_handling",
        "task": "Add error handling for database connection failure",
        "file": "src/database.py",
        "code_before": "def get_connection():\n    return sqlite3.connect('app.db')",
        "code_after": "def get_connection():\n    try:\n        return sqlite3.connect('app.db')\n    except sqlite3.Error as e:\n        raise RuntimeError(f'DB connection failed: {e}') from e",
        "diff": "--- a/src/database.py\n+++ b/src/database.py\n@@ -1 +1,4 @@\n def get_connection():\n-    return sqlite3.connect('app.db')\n+    try:\n+        return sqlite3.connect('app.db')\n+    except sqlite3.Error as e:\n+        raise RuntimeError(f'DB connection failed: {e}') from e",
        "plan": "1. Wrap connection in try/except\n2. Log the database error\n3. Raise a descriptive RuntimeError\n4. Add test for connection failure",
        "test_command": "pytest tests/test_database.py",
    },
]


def generate(count: int, modality: str = "patch_planning") -> list:
    """Generate patch-related examples."""
    examples = []
    for i in range(count):
        s = random.choice(PATCH_SCENARIOS)
        repo = random.choice(["web-app", "api-service", "data-pipeline"])

        if modality == "patch_planning":
            instruction = random.choice([
                f"Plan a fix: {s['task']}",
                f"Design a patch plan for: {s['task']}",
                f"Outline the steps to fix: {s['task']}",
                f"Create an edit plan: {s['task']}",
            ])
            target = s["plan"]
        elif modality == "unified_diff":
            instruction = random.choice([
                f"Generate a unified diff to: {s['task']}",
                f"Output a diff fixing: {s['task']}",
                f"Create a patch: {s['task']}",
            ])
            target = s["diff"]
        elif modality == "test_repair":
            instruction = random.choice([
                f"This test is failing. Fix it:\n```python\n{s['code_before']}\n```",
                f"Repair the test case:\n```python\n{s['code_before']}\n```",
            ])
            target = s["code_after"]
        else:
            continue

        examples.append(LymeExample(
            modality=modality,
            instruction=instruction,
            repo_context=RepoContext(
                repo_name=repo, language="Python",
                architecture_summary=f"Fixing {s['type']} in {s['file']}",
            ),
            retrieved_files=[
                RetrievedFile(file_path=s["file"], role="source",
                              content_preview=s["code_before"]),
            ],
            target_output=target,
            metadata={
                "patch_type": s["type"],
                "file": s["file"],
                "verification_command": s["test_command"],
                "rollback_strategy": "git checkout -- " + s["file"],
            },
        ))
    return examples


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--output-dir", default="datasets/generated")
    args = parser.parse_args()

    modalities = ["patch_planning", "unified_diff", "test_repair"]
    per_mod = args.count // len(modalities)

    all_examples = []
    for mod in modalities:
        exs = generate(per_mod, mod)
        all_examples.extend(exs)
        print(f"[{mod}] {len(exs)} examples")

    # Assign IDs and dedup
    seen = set()
    deduped = []
    for i, ex in enumerate(all_examples):
        ex.id = f"patch-{i:06d}"
        ex.created = datetime.now(timezone.utc).isoformat()
        key = f"{ex.modality}|{ex.instruction[:80]}|{ex.target_output[:80]}"
        if key not in seen:
            seen.add(key)
            deduped.append(ex)

    random.shuffle(deduped)
    n = len(deduped)
    n_val = int(n * 0.1)
    n_test = int(n * 0.1)
    train, val, test = deduped[:n-n_val-n_test], deduped[n-n_val-n_test:n-n_test], deduped[n-n_test:]

    out = Path(args.output_dir)
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        p = out / split_name / "patch.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            for ex in split_data:
                f.write(ex.to_jsonl() + "\n")

    print(f"\nTotal unique: {len(deduped)}")
    print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    print(f"Output: {out}/{{train,val,test}}/patch.jsonl")


if __name__ == "__main__":
    main()
