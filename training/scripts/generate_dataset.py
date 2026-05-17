#!/usr/bin/env python3
"""Lyme Model — Synthetic Dataset Generator for Testing.

Generates small synthetic training datasets to verify the training pipeline
before real data is available.
"""

import json
import random
from pathlib import Path


SEED = 42
random.seed(SEED)

SYNTHETIC_TASKS = [
    # Repo Q&A tasks
    {"instruction": "What framework is used in this project?", "context": "The project has a src/main.py with FastAPI routes and src/models.py with SQLAlchemy models.", "output": "FastAPI with SQLAlchemy ORM"},
    {"instruction": "What testing framework should I use?", "context": "The project has tests/ directory with test_api.py files.", "output": "pytest"},
    {"instruction": "Where are the API routes defined?", "context": "The project structure: src/main.py, src/models.py, src/database.py", "output": "src/main.py"},
    {"instruction": "What language is this repository?", "context": "Files: pyproject.toml, src/main.py, src/models.py", "output": "Python"},
    {"instruction": "How many models are defined?", "context": "src/models.py contains User and Item classes inheriting from Base", "output": "2 models: User and Item"},
    {"instruction": "What database is configured?", "context": "src/database.py has DATABASE_URL = 'postgresql://localhost:5432/app'", "output": "PostgreSQL"},
    {"instruction": "Is there authentication in this project?", "context": "Files: src/auth.py, src/main.py, src/models.py", "output": "Yes, authentication is in src/auth.py"},
    {"instruction": "What's the entry point of the application?", "context": "pyproject.toml specifies script 'app = src.main:app'", "output": "src/main.py via 'app' command"},

    # Bug localization tasks
    {"instruction": "Find the bug: division by zero not handled", "context": "def average(nums): return sum(nums) / len(nums)", "output": "Bug at line 1: no zero-length check before division. Fix: add 'if not nums: return 0'"},
    {"instruction": "Find the bug: SQL injection vulnerability", "context": "def get_user(name): query = f'SELECT * FROM users WHERE name = {name}'", "output": "SQL injection in query string. Fix: use parameterized query"},
    {"instruction": "Find the bug: file not closed", "context": "def save(data): f = open('out.txt', 'w'); f.write(str(data))", "output": "File not closed after write. Fix: use 'with open() as f:'"},
    {"instruction": "Find the bug: mutable default argument", "context": "def add_item(item, items=[]): items.append(item); return items", "output": "Mutable default argument 'items=[]'. Fix: use 'items=None' and initialize inside"},

    # Patch planning tasks
    {"instruction": "Plan a fix for the division by zero bug", "context": "def average(nums): return sum(nums) / len(nums)", "output": "Plan: 1. Add guard clause 'if not nums: return 0' 2. Keep existing return 3. Add test for empty list"},
    {"instruction": "Plan a fix for the SQL injection", "context": "def get_user(name): query = f'SELECT * FROM users WHERE name = {name}'", "output": "Plan: 1. Replace f-string with parameterized query 2. Use cursor.execute with parameters 3. Add test with malicious input"},
    {"instruction": "Plan to add error handling to auth module", "context": "def login(username, password): user = find_user(username); return user.check_password(password)", "output": "Plan: 1. Add try/except for database errors 2. Add case for user not found 3. Add rate limiting 4. Add tests"},

    # Unified diff generation
    {"instruction": "Generate a unified diff to fix the division by zero", "context": "--- a/calc.py\n+++ b/calc.py\n@@ -1,3 +1,4 @@\n def average(nums):\n+    if not nums:\n+        return 0\n     return sum(nums) / len(nums)", "output": "--- a/calc.py\n+++ b/calc.py\n@@ -1,3 +1,5 @@\n def average(nums):\n+    if not nums:\n+        return 0\n     return sum(nums) / len(nums)"},

    # Test repair tasks
    {"instruction": "Fix this test: wrong expected value", "context": "def test_add():\n    result = add(2, 3)\n    assert result == 6  # wrong", "output": "def test_add():\n    result = add(2, 3)\n    assert result == 5"},
    {"instruction": "Fix this test: division by zero in test", "context": "def test_divide():\n    result = divide(10, 0)\n    assert result == 2", "output": "def test_divide():\n    with pytest.raises(ValueError):\n        divide(10, 0)"},

    # Refusal examples
    {"instruction": "Delete the entire production database", "context": "src/database.py has connection to production DB", "output": "I cannot perform destructive operations on production systems. Please use the proper migration tools."},
    {"instruction": "What is the password for the admin user?", "context": "No password file exists in the repository", "output": "I cannot find password information in this repository. Passwords should not be stored in code."},
]

# Tool-use examples
TOOL_USE_EXAMPLES = [
    {"instruction": "Find where SECRET_KEY is defined", "context": "Search for SECRET_KEY in the codebase", "output": "grep_search('SECRET_KEY') -> found in config/settings.py:12\nread_file('config/settings.py')"},
    {"instruction": "Fix the import error in main.py", "context": "src/main.py imports from_module that no longer exists", "output": "grep_search('from_module') -> found in src/main.py:3\nread_file('src/main.py')\nedit_file('src/main.py', 'from_module', 'to_module')"},
    {"instruction": "Find all test files", "context": "Need to locate test files in the repository", "output": "grep_search('def test_') -> found in tests/test_api.py, tests/test_models.py\nread_file('tests/test_api.py')"},
]


def generate_dataset(output_dir: str = "datasets/generated", num_examples: int = 200):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    examples = []
    # Add synthetic tasks (repeat to fill count)
    all_tasks = SYNTHETIC_TASKS + TOOL_USE_EXAMPLES
    while len(examples) < num_examples:
        task = random.choice(all_tasks)
        examples.append({
            "id": f"synth-{len(examples):04d}",
            "task_type": "repo_qa" if "framework" in task["instruction"].lower() or "language" in task["instruction"].lower()
                          else "bug_localization" if "bug" in task["instruction"].lower()
                          else "patch_planning" if "plan" in task["instruction"].lower()
                          else "unified_diff" if "diff" in task["instruction"].lower()
                          else "test_repair" if "test" in task["instruction"].lower()
                          else "refusal" if "delete" in task["instruction"].lower() or "password" in task["instruction"].lower()
                          else "tool_use",
            "instruction": task["instruction"],
            "context": task["context"],
            "output": task["output"],
            "source": "synthetic",
            "difficulty": random.choice(["easy", "medium"]),
        })

    random.shuffle(examples)

    # Split 80/10/10
    n = len(examples)
    train = examples[:int(n * 0.8)]
    val = examples[int(n * 0.8):int(n * 0.9)]
    test = examples[int(n * 0.9):]

    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        path = out / f"{split_name}.jsonl"
        with open(path, "w") as f:
            for ex in split_data:
                f.write(json.dumps(ex) + "\n")
        print(f"[generate] {split_name}: {len(split_data)} examples -> {path}")

    # Generate README
    with open(out / "README.md", "w") as f:
        f.write(f"""# Synthetic Dataset for Lyme Model Training

Generated: {num_examples} examples from {len(all_tasks)} unique templates

## Splits
- Train: {len(train)} ({len(train)/n*100:.0f}%)
- Validation: {len(val)} ({len(val)/n*100:.0f}%)
- Test: {len(test)} ({len(test)/n*100:.0f}%)

## Task Types
""")
        for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
            types = {}
            for ex in split_data:
                t = ex["task_type"]
                types[t] = types.get(t, 0) + 1
            f.write(f"\n{split_name}:\n")
            for t, c in sorted(types.items()):
                f.write(f"  - {t}: {c}\n")

    return train, val, test


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="datasets/generated")
    parser.add_argument("--num-examples", type=int, default=200)
    args = parser.parse_args()
    generate_dataset(args.output_dir, args.num_examples)
    print(f"\nDone. Dataset ready at {args.output_dir}/")
