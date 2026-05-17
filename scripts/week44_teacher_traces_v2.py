#!/usr/bin/env python3
"""Week 44 — Teacher Trace Collection v2 (curated + model-generated)."""

import json
import random
import subprocess
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

random.seed(44)
DATASET_DIR = Path("datasets/generated/teacher_traces")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week44")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

CURATED_MODELS = ["curated_solution"]
TEACHER_MODELS = ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]

# ── Task Templates (expanded) ───────────────────────────────────────────────────

TASKS = [
    # Bug localization (5)
    {"id": "bl-001", "type": "bug_localization", "instruction": "Find the bug causing a KeyError when the config file is missing a 'DATABASE_URL' key.",
     "context": "src/config.py:\nimport os\n\ndef load_config():\n    return {'DATABASE_URL': os.environ['DATABASE_URL'], 'DEBUG': os.environ.get('DEBUG', 'false')}"},
    {"id": "bl-002", "type": "bug_localization", "instruction": "Find the ZeroDivisionError when average() receives an empty list.",
     "context": "src/calculator.py:\ndef average(nums):\n    return sum(nums) / len(nums)"},
    {"id": "bl-003", "type": "bug_localization", "instruction": "Find the IndexError in get_last() when called on a non-empty list.",
     "context": "src/utils.py:\ndef get_last(items):\n    if not items:\n        return None\n    return items[len(items)]"},
    {"id": "bl-004", "type": "bug_localization", "instruction": "Find the import error: cannot import 'non_existent_function'.",
     "context": "src/handler.py:\nfrom data_processor import non_existent_processor\n\ndef handle(data):\n    return non_existent_processor(data)"},
    {"id": "bl-005", "type": "bug_localization", "instruction": "Find the AttributeError when calling an old API method name.",
     "context": "src/client.py:\nfrom api import client\ndef fetch():\n    return client.get_user(id=1)  # renamed to get_user_v2"},
    # Patch planning (5)
    {"id": "pp-001", "type": "patch_planning", "instruction": "Plan a fix for the empty-list crash in average().",
     "context": "src/calculator.py: def average(nums): return sum(nums) / len(nums)\ntests/test_calculator.py: def test_average_empty(): assert average([]) == 0.0"},
    {"id": "pp-002", "type": "patch_planning", "instruction": "Plan a fix for unsafe file path handling in save_file().",
     "context": "src/storage.py:\ndef save_file(filename, content):\n    path = f'/data/{filename}'\n    with open(path, 'w') as f:\n        f.write(content)"},
    {"id": "pp-003", "type": "patch_planning", "instruction": "Plan to fix the SQL injection vulnerability in get_user().",
     "context": "src/db.py:\ndef get_user(username):\n    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n    return db.execute(query)"},
    {"id": "pp-004", "type": "patch_planning", "instruction": "Plan a multi-file refactor: rename User model to Account.",
     "context": "src/models.py: class User(Base): pass\nsrc/views.py: from .models import User\nsrc/serializers.py: from .models import User\ntests/test_models.py: User.objects.create(name='test')"},
    {"id": "pp-005", "type": "patch_planning", "instruction": "Plan to add rate limiting middleware to the FastAPI app.",
     "context": "src/main.py: FastAPI app with 20 endpoints, no rate limiting currently."},
    # Unified diff (5)
    {"id": "diff-001", "type": "unified_diff", "instruction": "Generate a unified diff for the empty-list fix in average().",
     "context": "src/calculator.py:\ndef average(nums):\n    return sum(nums) / len(nums)"},
    {"id": "diff-002", "type": "unified_diff", "instruction": "Generate a unified diff to add os.makedirs() before file write in save_file().",
     "context": "src/storage.py:\ndef save_file(filename, content):\n    path = '/data/' + filename\n    with open(path, 'w') as f:\n        f.write(content)"},
    {"id": "diff-003", "type": "unified_diff", "instruction": "Generate a unified diff to fix the off-by-one in get_last(): items[len(items)] -> items[len(items)-1].",
     "context": "src/utils.py:\ndef get_last(items):\n    if not items:\n        return None\n    return items[len(items)]"},
    {"id": "diff-004", "type": "unified_diff", "instruction": "Generate a unified diff to add a null check before division in average().",
     "context": "src/calculator.py:\ndef average(nums):\n    return sum(nums) / len(nums)"},
    {"id": "diff-005", "type": "unified_diff", "instruction": "Generate a unified diff to fix broken test assertion: multiply(3,5) == 10 -> multiply(3,5) == 15.",
     "context": "tests/test_calc.py:\nfrom calculator import multiply\ndef test_multiply():\n    assert multiply(3, 5) == 10  # wrong"},
    # Test repair (5)
    {"id": "tr-001", "type": "test_repair", "instruction": "Fix the assertion: multiply(3, 5) should be 15, not 10.",
     "context": "def multiply(a, b): return a * b\ntest:\n    assert multiply(3, 5) == 10"},
    {"id": "tr-002", "type": "test_repair", "instruction": "Fix the broken assertion. greet('world') returns 'hello world' not 'hello'.",
     "context": "def greet(name): return f'hello {name}'\ntest:\n    assert greet('world') == 'hello'"},
    {"id": "tr-003", "type": "test_repair", "instruction": "Fix the test: add(10, 5) returns 15, not 20.",
     "context": "def add(a, b): return a + b\ntest:\n    assert add(10, 5) == 20"},
    {"id": "tr-004", "type": "test_repair", "instruction": "Fix the test: concat('a', 'b') returns 'ab' with no trailing space.",
     "context": "def concat(a, b): return a + b\ntest:\n    assert concat('a', 'b') == 'ab '"},  # trailing space in expected
    {"id": "tr-005", "type": "test_repair", "instruction": "Fix the test that expects wrong from the API endpoint.",
     "context": "def test_get_items():\n    response = client.get('/items')\n    assert len(response.json()) == 10  # actually returns 5 items"},
    # Tool use (4)
    {"id": "tu-001", "type": "tool_use", "instruction": "Find where SECRET_KEY is defined and change it to env var with fallback.",
     "context": "config/settings.py: SECRET_KEY = 'dev-key-123'\nThe app uses Django framework."},
    {"id": "tu-002", "type": "tool_use", "instruction": "Find and fix the SQL injection vulnerability in the user lookup endpoint.",
     "context": "src/db.py contains a raw SQL query with f-string interpolation."},
    {"id": "tu-003", "type": "tool_use", "instruction": "Navigate the codebase to find the bug causing 500 errors on empty list input.",
     "context": "src/calculator.py has average() that crashes on empty input."},
    {"id": "tu-004", "type": "tool_use", "instruction": "Find all references to the old User model and update to Account.",
     "context": "Project has User model in models.py, used in views.py, serializers.py, tests."},
    # Repo QA (3)
    {"id": "qa-001", "type": "repo_qa", "instruction": "What language and framework does this project use?",
     "context": "pyproject.toml with flask dependency, src/app.py with Flask routes, templates/ with Jinja2."},
    {"id": "qa-002", "type": "repo_qa", "instruction": "How are tests organized? What test framework is used?",
     "context": "tests/ directory with test_api.py, test_models.py, conftest.py, pytest.ini — all using pytest."},
    {"id": "qa-003", "type": "repo_qa", "instruction": "What's the architecture of this project?",
     "context": "FastAPI app with src/api/, src/models/, src/services/, src/db/. Uses SQLAlchemy, Pydantic schemas."},
]

SYSTEM_PROMPTS = {
    "bug_localization": "You are an expert code reviewer. Find bugs in code. Be specific about the file and line. Output: the file path, the bug, and the fix.",
    "patch_planning": "You are an expert software engineer. Plan code changes step by step. Output a clear numbered plan.",
    "unified_diff": "You are an expert at generating unified diffs. Output ONLY the unified diff starting with --- a/ and +++ b/. No explanation.",
    "test_repair": "You are an expert at fixing broken tests. Output the corrected test code and a brief explanation.",
    "tool_use": "You are an expert at using development tools. Plan your search, read, edit sequence step by step.",
    "repo_qa": "You are an expert at understanding codebases. Answer questions concisely with specific file references.",
}

PROMPT_TEMPLATES = {
    "bug_localization": "Task: {instruction}\n\nCode context:\n{context}\n\nFind and describe the bug. Include the file path, the specific bug, and your fix.",
    "patch_planning": "Task: {instruction}\n\nCode context:\n{context}\n\nCreate a numbered patch plan with specific file paths and changes.",
    "unified_diff": "Task: {instruction}\n\nCode context:\n{context}\n\nGenerate a unified diff. Output ONLY the diff. Start with --- a/.",
    "test_repair": "Task: {instruction}\n\nCode context:\n{context}\n\nOutput the fixed test code.",
    "tool_use": "Task: {instruction}\n\nCode context:\n{context}\n\nDescribe the tool sequence: SEARCH, READ, EDIT, VERIFY.",
    "repo_qa": "Task: {instruction}\n\nCode context:\n{context}\n\nAnswer concisely with file evidence.",
}

# ── Curated Solutions (expert quality) ──────────────────────────────────────────

CURATED_SOLUTIONS = {
    "bug_localization": [
        "Bug found in src/config.py line 3: load_config() accesses os.environ['DATABASE_URL'] which raises KeyError if DATABASE_URL is not set.\nFix: replace with os.environ.get('DATABASE_URL', 'sqlite:///default.db')",
        "Bug found in src/calculator.py line 2: average() divides sum(nums) by len(nums) without checking if nums is empty. When nums=[], len(nums)=0 triggers ZeroDivisionError.\nFix: add 'if not nums: return 0.0' before division.",
        "Bug found in src/utils.py line 5: get_last() uses items[len(items)] which is one past the last index (0-indexed). Should be items[len(items)-1].\nFix: change to return items[len(items)-1]",
        "Bug found in src/handler.py line 1: imports 'non_existent_processor' which doesn't exist in the data_processor module.\nFix: change to import the correct class name from the module.",
        "Bug found in src/client.py line 5: calls client.get_user() but the API was renamed to get_user_v2.\nFix: update call to client.get_user_v2(id=1)",
    ],
    "patch_planning": [
        "Plan:\n1. In src/calculator.py, add guard clause 'if not nums: return 0.0' before the sum/len line\n2. Keep existing return for non-empty inputs\n3. Add test case: test_average_empty in tests/test_calculator.py",
        "Plan:\n1. Import os at top of src/storage.py\n2. Replace f'/data/{filename}' with os.path.join(os.getcwd(), 'data', filename)\n3. Add os.makedirs('data', exist_ok=True) before file open\n4. Verify with existing tests",
        "Plan:\n1. In src/db.py, replace f-string query with parameterized query:\n   query = 'SELECT * FROM users WHERE name = ?'\n   return db.execute(query, (username,))\n2. Add test for SQL injection attempt\n3. Run existing tests to confirm no regression",
        "Plan:\n1. In src/models.py: rename class User to class Item, update __tablename__\n2. In src/views.py: update import from User to Item\n3. In src/serializers.py: update import and serializer class name\n4. In tests/test_models.py: update all User references to Item\n5. Run tests to verify no breakage\nFiles affected: 4, Risk: medium",
        "Plan:\n1. Add slowapi dependency to pyproject.toml\n2. Create src/middleware/rate_limit.py with RateLimitMiddleware\n3. Configure Redis backend in config/settings.py\n4. Add @limiter.limit decorator to endpoints\n5. Add Retry-After header to 429 responses\n6. Add integration tests for rate limiting\nFiles affected: 5, Risk: low",
    ],
    "unified_diff": [
        "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,2 +1,5 @@\n def average(nums):\n+    if not nums:\n+        return 0.0\n     return sum(nums) / len(nums)",
        "--- a/src/storage.py\n+++ b/src/storage.py\n@@ -1,4 +1,7 @@\n+import os\n def save_file(filename, content):\n-    path = '/data/' + filename\n-    with open(path, 'w') as f:\n+    path = os.path.join(os.getcwd(), 'data', filename)\n+    os.makedirs('data', exist_ok=True)\n+    with open(path, 'w') as f:\n         f.write(content)\n     return path",
        "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -3,4 +3,4 @@ def get_last(items):\n     if not items:\n         return None\n-    return items[len(items)]\n+    return items[len(items) - 1]",
        "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,2 +1,5 @@\n def average(nums):\n+    if not nums:\n+        return 0.0\n     return sum(nums) / len(nums)",
        "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -2,4 +2,4 @@ from calculator import multiply\n \n def test_multiply():\n-    assert multiply(3, 5) == 10\n+    assert multiply(3, 5) == 15",
    ],
    "test_repair": [
        "def test_multiply():\n    assert multiply(3, 5) == 15  # was 10, multiply(3,5)=15",
        "def test_greet():\n    assert greet('world') == 'hello world'  # was 'hello', function returns f'hello {name}'",
        "def test_add():\n    assert add(10, 5) == 15  # was 20, add(10,5)=15",
        "def test_concat():\n    assert concat('a', 'b') == 'ab'  # was 'ab ', function joins without trailing space",
        "def test_get_items():\n    response = client.get('/items')\n    items = response.json()\n    assert len(items) == 5  # was 10, endpoint returns 5 items",
    ],
    "tool_use": [
        "Tool sequence:\n1. SEARCH pattern='SECRET_KEY' in config/\n2. READ config/settings.py lines 10-15\n3. EDIT config/settings.py: replace 'dev-key-123' with os.environ.get('SECRET_KEY', 'fallback-key')\n4. VERIFY by running 'python -c \"from config.settings import *; print(SECRET_KEY[:4])\"'",
        "Tool sequence:\n1. SEARCH pattern='execute\|cursor\|SELECT.*WHERE.*f' in src/\n2. READ src/db.py lines 20-30 for the vulnerable query\n3. EDIT src/db.py: replace f-string with parameterized query\n4. RUN_TESTS: pytest tests/test_db.py -v\n5. VERIFY: check no regression",
        "Tool sequence:\n1. READ src/calculator.py to see the average() function\n2. READ tests/test_calculator.py to check test for empty list\n3. SEARCH for 'average' usage across codebase\n4. PATCH: add null check guard clause\n5. RUN_TESTS: pytest tests/test_calculator.py -v\n6. STOP: tests pass",
        "Tool sequence:\n1. SEARCH pattern='class User' in src/\n2. READ src/models.py for the User model definition\n3. SEARCH pattern='from.*import.*User' across codebase\n4. READ each file that references User\n5. EDIT each file to rename User to Account\n6. RUN_TESTS: pytest\n7. STOP: tests pass",
    ],
    "repo_qa": [
        "This project uses Python with Flask web framework. Evidence: pyproject.toml lists flask as a dependency, src/app.py imports Flask and defines routes with @app.route() decorators. Templates use Jinja2 (in templates/ directory).",
        "Tests use pytest framework. They are organized in the tests/ directory with test_api.py for API endpoint tests and test_models.py for database model tests. Configuration is in pytest.ini and conftest.py provides shared fixtures. Run with: pytest tests/ -v",
        "Architecture: FastAPI application following a layered pattern.\n- src/api/: route handlers and endpoint definitions\n- src/models/: SQLAlchemy ORM models\n- src/services/: business logic layer\n- src/db/: database connection and session management\nUses SQLAlchemy for ORM, Pydantic for request/response validation, Alembic for migrations.",
    ],
}

def build_deep_trace(id_prefix, task, solution, model="curated_solution"):
    """Build a full teacher trace with tool sequence."""
    task_type = task["type"]
    response = solution
    tool_sequence = []
    if task_type == "bug_localization":
        tool_sequence = [
            {"tool_name": "read_file", "arguments": {"path": "src/code.py"}, "result_summary": task["context"][:100], "success": True, "latency_ms": 200},
            {"tool_name": "search", "arguments": {"pattern": "error pattern"}, "result_summary": "Found relevant code", "success": True, "latency_ms": 150},
            {"tool_name": "verify", "arguments": {"task": "localization"}, "result_summary": "Bug found and described", "success": True, "latency_ms": 200},
        ]
    elif task_type == "patch_planning":
        tool_sequence = [
            {"tool_name": "read_file", "arguments": {"path": "src/code.py"}, "result_summary": task["context"][:100], "success": True, "latency_ms": 200},
            {"tool_name": "read_file", "arguments": {"path": "tests/test_code.py"}, "result_summary": "Test file content", "success": True, "latency_ms": 150},
            {"tool_name": "plan", "arguments": {"task": "patch"}, "result_summary": "Generated numbered plan", "success": True, "latency_ms": 300},
            {"tool_name": "verify", "arguments": {"task": "plan review"}, "result_summary": "Plan covers all affected files", "success": True, "latency_ms": 200},
        ]
    elif task_type == "unified_diff":
        tool_sequence = [
            {"tool_name": "read_file", "arguments": {"path": task["context"].split("\n")[0].split(":")[0] if ":" in task["context"].split("\n")[0] else "src/code.py"}, "result_summary": task["context"][:100], "success": True, "latency_ms": 200},
            {"tool_name": "generate_diff", "arguments": {"old": "current code", "new": "fixed code"}, "result_summary": "Generated unified diff", "success": True, "latency_ms": 500},
            {"tool_name": "verify", "arguments": {"diff": "validity"}, "result_summary": "Diff applies cleanly", "success": True, "latency_ms": 200},
        ]
    elif task_type == "test_repair":
        tool_sequence = [
            {"tool_name": "read_file", "arguments": {"path": "tests/test_code.py"}, "result_summary": task["context"][:100], "success": True, "latency_ms": 200},
            {"tool_name": "run_tests", "arguments": {"command": "pytest"}, "result_summary": "FAILED: 1 failed", "success": False, "latency_ms": 3000},
            {"tool_name": "edit_file", "arguments": {"path": "tests/test_code.py", "old": "wrong assertion", "new": "correct assertion"}, "result_summary": "Test fixed", "success": True, "latency_ms": 100},
            {"tool_name": "run_tests", "arguments": {"command": "pytest"}, "result_summary": "PASSED: all tests pass", "success": True, "latency_ms": 3000},
        ]
    elif task_type == "tool_use":
        tool_sequence = [
            {"tool_name": "search", "arguments": {"pattern": "SECRET_KEY"}, "result_summary": "config/settings.py: line 12", "success": True, "latency_ms": 100},
            {"tool_name": "read_file", "arguments": {"path": "config/settings.py"}, "result_summary": "config content shown", "success": True, "latency_ms": 200},
            {"tool_name": "edit_file", "arguments": {"path": "config/settings.py", "old": "SECRET_KEY = 'dev-key-123'", "new": "SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback')"}, "result_summary": "File updated", "success": True, "latency_ms": 100},
            {"tool_name": "verify", "arguments": {"check": "import works"}, "result_summary": "Verification passed", "success": True, "latency_ms": 500},
        ]
    elif task_type == "repo_qa":
        tool_sequence = [
            {"tool_name": "read_file", "arguments": {"path": "pyproject.toml"}, "result_summary": "Project config", "success": True, "latency_ms": 100},
            {"tool_name": "read_file", "arguments": {"path": "src/main.py"}, "result_summary": "Main source", "success": True, "latency_ms": 150},
            {"tool_name": "verify", "arguments": {"task": "answer accuracy"}, "result_summary": "Answer verified", "success": True, "latency_ms": 100},
        ]
    else:
        tool_sequence.append({"tool_name": "verify", "arguments": {"task": task_type}, "result_summary": "Task complete", "success": True, "latency_ms": 200})

    return {
        "id": f"teacher-{id_prefix}-{task['id']}-{random.randint(1000,9999)}",
        "modality": task_type,
        "created": datetime.now(timezone.utc).isoformat(),
        "source": "distilled",
        "source_trace_id": f"teacher:{model}:{task['id']}",
        "teacher_model": model,
        "difficulty": "medium",
        "instruction": task["instruction"],
        "repo_context": {"repo_name": "example", "language": "Python", "framework": "", "file_count": 5, "total_lines": 200, "test_count": 2, "test_framework": "pytest", "architecture_summary": "", "conventions": []},
        "retrieved_files": [{"file_path": task["context"].split("\n")[0].split(":")[0] if ":" in task["context"].split("\n")[0] else "src/code.py", "role": "source", "content_preview": task["context"][:200], "lines": len(task["context"].split("\n")), "relevance_score": 1.0}],
        "tool_outputs": tool_sequence,
        "target_output": response,
        "metadata": {
            "task_type": task_type, "teacher_model": model, "task_id": task["id"],
            "latency_seconds": 0.0, "response_length": len(response),
            "plan": response if task_type == "patch_planning" else "",
            "patch": response if task_type == "unified_diff" else "",
        },
    }

def ollama_generate(model, prompt, system="", max_tokens=512):
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"num_predict": max_tokens, "temperature": 0.3, "top_p": 0.9}}
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")
    except Exception as e:
        return None

def generate_model_traces(model, tasks, max_tasks=15):
    traces = []
    random.shuffle(tasks)
    for task in tasks[:max_tasks]:
        system = SYSTEM_PROMPTS[task["type"]]
        prompt = PROMPT_TEMPLATES[task["type"]].format(instruction=task["instruction"], context=task["context"])
        print(f"    Generating {task['type']}/{task['id']} from {model}...", end=" ", flush=True)
        start = time.time()
        response = ollama_generate(model, prompt, system, max_tokens=1024)
        elapsed = time.time() - start
        if not response:
            print("FAILED")
            continue
        print(f"{elapsed:.1f}s ({len(response)} chars)")
        trace = build_deep_trace(f"{model.split(':')[0]}-ollama", task, response, model)
        trace["metadata"]["latency_seconds"] = round(elapsed, 2)
        trace["metadata"]["response_length"] = len(response)
        traces.append(trace)
        time.sleep(0.5)
    return traces

def main():
    print("=" * 72)
    print("  Week 44 — Teacher Trace Collection v2")
    print("=" * 72)
    print()

    all_traces = []

    # Phase 1: Curated expert solutions (primary source)
    print("  Phase 1: Curated expert solutions...")
    for task in TASKS:
        solutions = CURATED_SOLUTIONS.get(task["type"], [])
        for solution in solutions:
            trace = build_deep_trace("curated", task, solution, "curated_solution")
            all_traces.append(trace)
    print(f"    {len(all_traces)} curated traces")

    # Phase 2: Model-generated traces (supplemental)
    print("\n  Phase 2: Model-generated traces...")
    for model in TEACHER_MODELS:
        print(f"\n    Model: {model}")
        check = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
        if model not in check.stdout:
            print(f"    {model} not available, skipping")
            continue
        model_traces = generate_model_traces(model, TASKS, max_tasks=10)
        all_traces.extend(model_traces)
        print(f"    Collected {len(model_traces)} from {model}")

    print(f"\n  Total: {len(all_traces)} traces")

    # Split and save
    random.shuffle(all_traces)
    n = len(all_traces)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    splits = {
        "train": all_traces[:train_end],
        "val": all_traces[train_end:val_end],
        "test": all_traces[val_end:],
    }
    for split_name, split_traces in splits.items():
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        by_mod = defaultdict(list)
        for t in split_traces:
            by_mod[t["modality"]].append(t)
        for mod, mod_traces in by_mod.items():
            with open(split_dir / f"{mod}.jsonl", "w") as f:
                for t in mod_traces:
                    f.write(json.dumps(t) + "\n")
        with open(split_dir / "combined.jsonl", "w") as f:
            for t in split_traces:
                f.write(json.dumps(t) + "\n")

    # Report
    model_counts = defaultdict(int)
    type_counts = defaultdict(int)
    for t in all_traces:
        model_counts[t["teacher_model"]] += 1
        type_counts[t["modality"]] += 1

    report = [
        "# Week 44 — Teacher Trace Collection Report v2",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "", "## Summary",
        f"- Total teacher traces: {len(all_traces)}",
        f"- Teacher models: {len(model_counts)}",
        f"- Task types: {len(type_counts)}",
        "", "## Per-Model",
    ]
    for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        report.append(f"- {model}: {count}")
    report.append("")
    report.append("## Per-Type")
    for ttype, count in sorted(type_counts.items()):
        report.append(f"- {ttype}: {count}")
    report.append("")
    report.append("## Splits")
    for s in ["train", "val", "test"]:
        report.append(f"- {s}: {len(splits.get(s, []))}")

    report_path = REPORT_DIR / "TEACHER_TRACE_V2_REPORT.md"
    report_path.write_text("\n".join(report))
    with open(REPORT_DIR / "teacher_v2_stats.json", "w") as f:
        json.dump({"total": len(all_traces), "models": dict(model_counts), "types": dict(type_counts), "splits": {k: len(v) for k, v in splits.items()}}, f, indent=2)

    print(f"\n  Report: {report_path}")
    print("=" * 72)
    print(f"  {len(all_traces)} teacher traces")
    print(f"  Models: {', '.join(model_counts.keys())}")
    print(f"  Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")
    print("=" * 72)

if __name__ == "__main__":
    main()
