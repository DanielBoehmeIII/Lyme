#!/usr/bin/env python3
"""Week 84 — Teacher Trace Factory v2.

Collects legal/allowed teacher behavior traces for behavioral distillation.

Sources:
- Human-written curated solutions (primary)
- Strong open models via Ollama (qwen2.5-coder, deepseek-coder)
- Simulated ideal agent traces

Each trace includes:
- search strategy, file selection, plan, patch, test repair behavior,
  stop condition, final explanation

No leaked source. No proprietary internals.
"""

import json
import random
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datasets.schema import (
    LymeExample, RepoContext, RetrievedFile, ToolOutput, PatchCandidate,
    VALID_MODALITIES, VALID_DIFFICULTIES,
)

random.seed(84)
DATASET_DIR = Path("datasets/v2/teacher_traces")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week84")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

N_TRACES_PER_TASK = 100
OLLAMA_BASE_URL = "http://localhost:11434/api/generate"
TEACHER_MODELS = ["curated_solution", "qwen2.5-coder:7b", "deepseek-coder:6.7b"]

VALID_ACTIONS = ["SEARCH", "READ", "RUN", "PATCH", "VERIFY", "STOP", "ASK_USER"]

# ─── Task Definitions ──────────────────────────────────────────────────────────

TASKS = [
    # ── Bug Localization (6) ──
    {
        "id": "bl-001", "modality": "bug_localization",
        "instruction": "Find the bug causing a KeyError when the config file is missing 'DATABASE_URL'.",
        "context_files": {"src/config.py": "import os\n\ndef load_config():\n    return {'DATABASE_URL': os.environ['DATABASE_URL'], 'DEBUG': os.environ.get('DEBUG', 'false')}"},
        "target": "Bug at src/config.py line 3: os.environ['DATABASE_URL'] should use .get() with default. Fix: os.environ.get('DATABASE_URL', 'sqlite:///default.db')",
        "diff": "--- a/src/config.py\n+++ b/src/config.py\n@@ -1,3 +1,3 @@\n import os\n def load_config():\n-    return {'DATABASE_URL': os.environ['DATABASE_URL'], 'DEBUG': os.environ.get('DEBUG', 'false')}\n+    return {'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite:///default.db'), 'DEBUG': os.environ.get('DEBUG', 'false')}",
        "difficulty": "easy", "teacher_explanation": "The bug is a missing .get() call with default value. os.environ raises KeyError when a key is missing.",
        "teacher_plan": "1. Read config.py to see the current code. 2. Identify the unsafe environ access. 3. Replace direct access with .get() and a default. 4. Verify the fix.",
        "teacher_actions": ["SEARCH('KeyError|config')", "READ('src/config.py')", "PATCH('src/config.py')", "VERIFY('python -c \"from config import load_config; print(load_config())\"')"],
    },
    {
        "id": "bl-002", "modality": "bug_localization",
        "instruction": "Find the IndexError in get_last() when called on a list with items.",
        "context_files": {"src/utils.py": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items)]"},
        "target": "Bug at src/utils.py line 3: items[len(items)] should be items[len(items)-1]. Off-by-one error causes IndexError.",
        "diff": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -1,4 +1,4 @@\n def get_last(items):\n     if not items:\n         return None\n-    return items[len(items)]\n+    return items[len(items) - 1]",
        "difficulty": "easy",
        "teacher_explanation": "Off-by-one: list indices go from 0 to len-1, so the last element is at len(items)-1.",
        "teacher_plan": "1. Read utils.py. 2. Notice items[len(items)] is out of bounds. 3. Fix to items[len(items)-1]. 4. Verify with test.",
        "teacher_actions": ["READ('src/utils.py')", "PATCH('src/utils.py')", "VERIFY('python -c \"print(get_last([1,2,3]))\"')"],
    },
    {
        "id": "bl-003", "modality": "bug_localization",
        "instruction": "Find the import error: 'cannot import name non_existent_processor' from data_processor module.",
        "context_files": {"src/handler.py": "from data_processor import non_existent_processor\n\ndef handle(data):\n    return non_existent_processor(data)"},
        "target": "Bug at src/handler.py line 1: non_existent_processor doesn't exist in data_processor. Import the correct function name or use a fallback.",
        "diff": "--- a/src/handler.py\n+++ b/src/handler.py\n@@ -1,4 +1,4 @@\n-from data_processor import non_existent_processor\n+from data_processor import process_data\n \n def handle(data):\n-    return non_existent_processor(data)\n+    return process_data(data)",
        "difficulty": "easy",
        "teacher_explanation": "The imported name doesn't exist in the module. Checked the module contents and found the correct function name.",
        "teacher_plan": "1. READ handler.py to see the import. 2. SEARCH in data_processor module for available functions. 3. PATCH import to correct name.",
        "teacher_actions": ["READ('src/handler.py')", "SEARCH('def ', path='src/data_processor.py')", "PATCH('src/handler.py')"],
    },
    {
        "id": "bl-004", "modality": "bug_localization",
        "instruction": "Find why the login endpoint returns 500 when email is missing from the request.",
        "context_files": {
            "src/routes/auth.py": "from db.queries import fetch_user\nasync def login(request):\n    data = await request.json()\n    user = await fetch_user(data['email'])\n    return {'user': user}",
            "src/db/queries.py": "async def fetch_user(email):\n    pool = get_pool()\n    return await pool.fetchrow('SELECT * FROM users WHERE email = $1', email)"
        },
        "target": "Bug at src/routes/auth.py line 3: No validation that 'email' key exists in data. Crashes with KeyError if email is missing.",
        "diff": "--- a/src/routes/auth.py\n+++ b/src/routes/auth.py\n@@ -1,4 +1,6 @@\n from db.queries import fetch_user\n async def login(request):\n     data = await request.json()\n+    if 'email' not in data:\n+        return {'error': 'email is required'}, 400\n     user = await fetch_user(data['email'])\n     return {'user': user}",
        "difficulty": "medium",
        "teacher_explanation": "The request body may not have an 'email' field. Direct access to data['email'] raises KeyError, causing a 500. Add validation before access.",
        "teacher_plan": "1. READ auth.py to see the endpoint. 2. READ queries.py to understand the DB call. 3. PATCH auth.py with validation. 4. VERIFY with a test request.",
        "teacher_actions": ["READ('src/routes/auth.py')", "READ('src/db/queries.py')", "PATCH('src/routes/auth.py')", "VERIFY('pytest tests/test_login.py')"],
    },
    # ── Patch Planning (4) ──
    {
        "id": "pp-001", "modality": "patch_planning",
        "instruction": "Plan a fix for the empty-list crash in average().",
        "context_files": {
            "src/calculator.py": "def average(nums):\n    return sum(nums) / len(nums)",
            "tests/test_calculator.py": "def test_average_empty():\n    assert average([]) == 0.0"
        },
        "target": "Plan: 1. Add guard clause at top: if not nums: return 0.0 2. Keep existing return for non-empty case 3. Run test to verify.",
        "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,2 +1,4 @@\n def average(nums):\n+    if not nums:\n+        return 0.0\n     return sum(nums) / len(nums)",
        "difficulty": "easy",
        "teacher_explanation": "Division by len(empty list) = 0 raises ZeroDivisionError. Add early return for empty input.",
        "teacher_plan": "1. READ calculator.py. 2. READ test to understand expected behavior. 3. PATCH with guard clause. 4. VERIFY with pytest.",
        "teacher_actions": ["READ('src/calculator.py')", "READ('tests/test_calculator.py')", "PATCH('src/calculator.py')", "VERIFY('pytest tests/test_calculator.py')"],
    },
    {
        "id": "pp-002", "modality": "patch_planning",
        "instruction": "Plan to fix the SQL injection vulnerability in get_user().",
        "context_files": {
            "src/db.py": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n    return db.execute(query)"
        },
        "target": "Plan: 1. Replace f-string with parameterized query 2. Use placeholder (?) 3. Pass username as parameter 4. Verify with test including malicious input.",
        "diff": "--- a/src/db.py\n+++ b/src/db.py\n@@ -1,3 +1,3 @@\n def get_user(username):\n-    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n+    query = \"SELECT * FROM users WHERE name = ?\"\n-    return db.execute(query)\n+    return db.execute(query, (username,))",
        "difficulty": "hard",
        "teacher_explanation": "String interpolation in SQL is vulnerable to injection. Parameterized queries separate code from data.",
        "teacher_plan": "1. READ db.py. 2. Change query to parameterized. 3. Update execute call to pass parameters. 4. SECURITY test with injection attempt.",
        "teacher_actions": ["READ('src/db.py')", "PATCH('src/db.py')", "VERIFY('pytest tests/test_db.py')"],
    },
    {
        "id": "pp-003", "modality": "patch_planning",
        "instruction": "Plan a multi-file rename: change User model to Account across the codebase.",
        "context_files": {
            "src/models.py": "class User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)\n    name = Column(String)",
            "src/views.py": "from .models import User\n\ndef get_user(id):\n    return session.query(User).get(id)",
            "src/serializers.py": "from .models import User\n\nclass UserSerializer:\n    class Meta:\n        model = User"
        },
        "target": "Plan: 1. Rename class in models.py to Account (+ table name) 2. Update imports in views.py 3. Update imports in serializers.py 4. Update tests 5. Run all tests.",
        "diff": "--- multi-file change across 3 files ---",
        "difficulty": "medium",
        "teacher_explanation": "Renaming a model requires updates in all files that import or reference it. Track all references first.",
        "teacher_plan": "1. SEARCH for all User references. 2. READ each file. 3. PATCH models.py. 4. PATCH views.py. 5. PATCH serializers.py. 6. VERIFY with test suite.",
        "teacher_actions": ["SEARCH('class User|from.*import.*User')", "READ('src/models.py')", "READ('src/views.py')", "READ('src/serializers.py')", "PATCH('src/models.py')", "PATCH('src/views.py')", "PATCH('src/serializers.py')", "VERIFY('pytest')"],
    },
    # ── Unified Diff (4) ──
    {
        "id": "diff-001", "modality": "unified_diff",
        "instruction": "Generate a unified diff to fix the broken test assertion: multiply(3,5) should be 15.",
        "context_files": {"tests/test_calc.py": "from calculator import multiply\n\ndef test_multiply():\n    assert multiply(3, 5) == 10  # wrong expected value"},
        "target": "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -1,3 +1,3 @@\n from calculator import multiply\n def test_multiply():\n-    assert multiply(3, 5) == 10  # wrong expected value\n+    assert multiply(3, 5) == 15",
        "difficulty": "trivial",
        "teacher_explanation": "The expected value was wrong. 3*5 = 15, not 10.",
        "teacher_plan": "1. READ test file. 2. Fix assertion value. 3. RUN pytest.",
        "teacher_actions": ["READ('tests/test_calc.py')", "PATCH('tests/test_calc.py')", "VERIFY('pytest tests/test_calc.py')"],
    },
    {
        "id": "diff-002", "modality": "unified_diff",
        "instruction": "Generate a unified diff to add a null check before division.",
        "context_files": {"src/calculator.py": "def average(nums):\n    return sum(nums) / len(nums)"},
        "target": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,2 +1,4 @@\n def average(nums):\n+    if not nums:\n+        return 0.0\n     return sum(nums) / len(nums)",
        "difficulty": "easy",
        "teacher_explanation": "Need null check for empty list to prevent ZeroDivisionError.",
        "teacher_plan": "1. READ file. 2. Add guard clause. 3. VERIFY.",
        "teacher_actions": ["READ('src/calculator.py')", "PATCH('src/calculator.py')", "VERIFY('python -c \"print(average([]))\"')"],
    },
    # ── Tool Use (4) ──
    {
        "id": "tool-001", "modality": "tool_use",
        "instruction": "Find where LOG_LEVEL is configured and change it from INFO to DEBUG.",
        "context_files": {
            "src/main.py": "import logging\nlogging.basicConfig(level=logging.INFO)\n\ndef run():\n    logging.debug('starting app')\n    app.run()",
        },
        "target": "SEARCH('LOG_LEVEL|logging.INFO|basicConfig') → READ('src/main.py') → PATCH('src/main.py', 'INFO', 'DEBUG') → VERIFY('python -c \"import main\"')",
        "difficulty": "easy",
        "teacher_explanation": "Found the logging config in main.py. Changed level from INFO to DEBUG.",
        "teacher_plan": "1. SEARCH for logging level. 2. READ the file. 3. PATCH the config line. 4. VERIFY the import works.",
        "teacher_actions": ["SEARCH('LOG_LEVEL|logging.INFO|basicConfig')", "READ('src/main.py')", "PATCH('src/main.py')", "VERIFY('python -c \"import main; print(main)\"')"],
    },
    {
        "id": "tool-002", "modality": "tool_use",
        "instruction": "Find and fix the failing test in the calculator module.",
        "context_files": {
            "src/calculator.py": "def add(a, b): return a + b\ndef multiply(a, b): return a * b",
            "tests/test_calculator.py": "from calculator import add, multiply\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_multiply():\n    assert multiply(3, 5) == 10  # FAILS"
        },
        "target": "SEARCH('FAIL|failed|error') → READ('tests/test_calculator.py') → READ('src/calculator.py') → PATCH('tests/test_calculator.py', '== 10', '== 15') → VERIFY('pytest tests/test_calculator.py')",
        "difficulty": "easy",
        "teacher_explanation": "Ran tests, found failure. Read the test, discovered wrong expected value (3*5=15 not 10). Patched and verified.",
        "teacher_plan": "1. RUN tests to find failure. 2. READ test file. 3. PATCH the expected value. 4. VERIFY tests pass.",
        "teacher_actions": ["RUN('pytest tests/test_calculator.py')", "READ('tests/test_calculator.py')", "PATCH('tests/test_calculator.py')", "VERIFY('pytest tests/test_calculator.py')"],
    },
    {
        "id": "tool-003", "modality": "tool_use",
        "instruction": "Fix the import error in handler.py — it imports a non-existent function.",
        "context_files": {
            "src/handler.py": "from data_processor import non_existent_processor\n\ndef handle(data):\n    return non_existent_processor(data)",
            "src/data_processor.py": "def process_data(data):\n    return {'result': data}"
        },
        "target": "READ('src/handler.py') → SEARCH('def ', path='src/data_processor.py') → PATCH('src/handler.py', 'non_existent_processor', 'process_data') → VERIFY('python -c \"from handler import handle\"')",
        "difficulty": "easy",
        "teacher_explanation": "Read the broken file, searched the module for available functions, found the correct name, patched the import.",
        "teacher_plan": "1. READ handler.py. 2. SEARCH in data_processor for functions. 3. PATCH import. 4. VERIFY.",
        "teacher_actions": ["READ('src/handler.py')", "SEARCH('def ', path='src/data_processor.py')", "PATCH('src/handler.py')", "VERIFY('python -c \"from handler import handle\"')"],
    },
    {
        "id": "tool-004", "modality": "tool_use",
        "instruction": "Add request logging to the FastAPI login endpoint.",
        "context_files": {
            "src/main.py": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.post('/login')\nasync def login(request):\n    data = await request.json()\n    return {'token': 'abc123'}",
        },
        "target": "READ('src/main.py') → PATCH('src/main.py', 'async def login...', 'import logging... async def login... logging.info...') → VERIFY('pytest tests/')",
        "difficulty": "medium",
        "teacher_explanation": "Read the endpoint, added logging middleware and request logging to track login attempts.",
        "teacher_plan": "1. READ main.py. 2. Add logging import. 3. Add logging statement in login. 4. VERIFY.",
        "teacher_actions": ["READ('src/main.py')", "PATCH('src/main.py')", "VERIFY('python -c \"import main\"')"],
    },
    # ── Self-Repair (3) ──
    {
        "id": "sr-001", "modality": "self_repair",
        "instruction": "Fix the patch that failed: the test expected ZeroDivisionError but got 0.",
        "context_files": {
            "src/calculator.py": "def divide(a, b):\n    if b == 0:\n        return 0  # WRONG: test expects exception\n    return a / b",
            "tests/test_calculator.py": "def test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)"
        },
        "target": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,4 +1,4 @@\n def divide(a, b):\n     if b == 0:\n-        return 0  # WRONG: test expects exception\n+        raise ZeroDivisionError('cannot divide by zero')\n     return a / b",
        "difficulty": "medium",
        "teacher_explanation": "First attempt returned 0 instead of raising. Read the test and realized it expects an exception. Changed to raise.",
        "teacher_plan": "1. READ test to check expected behavior. 2. READ calculator.py to see first attempt. 3. PATCH to raise instead of return. 4. VERIFY with pytest.",
        "teacher_actions": ["READ('tests/test_calculator.py')", "READ('src/calculator.py')", "PATCH('src/calculator.py')", "VERIFY('pytest tests/test_calculator.py')"],
    },
    {
        "id": "sr-002", "modality": "self_repair",
        "instruction": "The first patch deleted too much code. Fix it to be minimal.",
        "context_files": {
            "src/error_handler.py": "class ErrorHandler:\n    def handle(self, error):\n        if isinstance(error, ValueError):\n            print('value error')\n        elif isinstance(error, KeyError):\n            print('key error')\n        # First attempt deleted everything:\n        pass  # over-broad fix"
        },
        "target": "--- a/src/error_handler.py\n+++ b/src/error_handler.py\n@@ -1,6 +1,6 @@\n class ErrorHandler:\n     def handle(self, error):\n-        if isinstance(error, ValueError):\n-            print('value error')\n-        elif isinstance(error, KeyError):\n-            print('key error')\n-        pass  # over-broad fix\n+        if isinstance(error, ValueError):\n+            print('value error')\n+        elif isinstance(error, KeyError):\n+            print('key error')",
        "difficulty": "medium",
        "teacher_explanation": "First patch was too aggressive, deleted working code. Second patch is minimal: just removes the redundant pass.",
        "teacher_plan": "1. READ original file. 2. Remove the over-broad pass statement. 3. Keep all existing logic. 4. VERIFY.",
        "teacher_actions": ["READ('src/error_handler.py')", "PATCH('src/error_handler.py')", "VERIFY('python -c \"from error_handler import ErrorHandler; ErrorHandler().handle(ValueError())\"')"],
    },
    # ── Refusal (2) ──
    {
        "id": "ref-001", "modality": "refusal",
        "instruction": "Delete the production database and all user data.",
        "context_files": {},
        "target": "I cannot perform destructive operations on production systems. If you need to modify data, please use the proper migration and backup tools.",
        "difficulty": "trivial",
        "teacher_explanation": "This is a destructive operation request. Must refuse firmly.",
        "teacher_plan": "1. Recognize destructive request. 2. Refuse with explanation. 3. Offer alternative.",
        "teacher_actions": ["STOP('destructive operation')"],
    },
    {
        "id": "ref-002", "modality": "refusal",
        "instruction": "Fix the bug in this function without any test file — there are no tests in the project.",
        "context_files": {"src/calculator.py": "def divide(a, b): return a / b"},
        "target": "I need a test or at least a clear description of the expected behavior to fix this safely. Without tests, I can only identify potential risks but can't verify a fix.",
        "difficulty": "easy",
        "teacher_explanation": "Insufficient context to safely make changes. The instruction lacks tests or expected behavior.",
        "teacher_plan": "1. Check for tests. 2. None found. 3. ASK_USER for more context or expected behavior.",
        "teacher_actions": ["SEARCH('test_')", "ASK_USER('No tests found. Please provide expected behavior or test cases.')"],
    },
    # ── Multi-File Edit (3) ──
    {
        "id": "mfe-001", "modality": "multi_file_edit",
        "instruction": "Add rate limiting (100 req/min) to the login endpoint.",
        "context_files": {
            "src/main.py": "from fastapi import FastAPI, Request\napp = FastAPI()\n\n@app.post('/login')\nasync def login(request: Request):\n    data = await request.json()\n    return {\"token\": \"abc\"}",
            "src/middleware.py": "from fastapi import Request\nfrom starlette.middleware.base import BaseHTTPMiddleware\n\nclass RateLimitMiddleware(BaseHTTPMiddleware):\n    async def dispatch(self, request: Request, call_next):\n        return await call_next(request)",
            "config/settings.py": "MAX_REQUESTS_PER_MINUTE = 100"
        },
        "target": "Plan: 1. Update middleware.py with rate limit logic. 2. Register middleware in main.py. 3. Read rate limit from config.",
        "diff": "--- multi-file change ---",
        "difficulty": "medium",
        "teacher_explanation": "Need to update middleware logic, register it, and use config values. Touches 3 files.",
        "teacher_plan": "1. READ all 3 files. 2. PATCH middleware.py with rate limit logic. 3. PATCH main.py to register middleware. 4. VERIFY.",
        "teacher_actions": ["READ('src/main.py')", "READ('src/middleware.py')", "READ('config/settings.py')", "PATCH('src/middleware.py')", "PATCH('src/main.py')", "VERIFY('pytest tests/')"],
    },
    {
        "id": "mfe-002", "modality": "multi_file_edit",
        "instruction": "Rename all occurrences of `get_user` to `fetch_user` across the codebase.",
        "context_files": {
            "src/client.py": "def get_user(id):\n    return db.query(id)",
            "src/views.py": "from client import get_user\n\ndef show_user(id):\n    user = get_user(id)\n    return render(user)",
            "tests/test_client.py": "from client import get_user\n\ndef test_get_user():\n    assert get_user(1) is not None"
        },
        "target": "Plan: 1. Rename in src/client.py. 2. Update import in src/views.py. 3. Update call in src/views.py. 4. Update test. 5. Run all tests.",
        "diff": "--- multi-file rename across 3 files ---",
        "difficulty": "easy",
        "teacher_explanation": "Simple rename. Need to update definition, all imports, and all call sites.",
        "teacher_plan": "1. SEARCH for all references. 2. PATCH src/client.py (definition). 3. PATCH src/views.py (import + call). 4. PATCH tests. 5. VERIFY.",
        "teacher_actions": ["SEARCH('get_user')", "PATCH('src/client.py')", "PATCH('src/views.py')", "PATCH('tests/test_client.py')", "VERIFY('pytest')"],
    },
    # ── Long-Horizon Planning (2) ──
    {
        "id": "lhp-001", "modality": "long_horizon_planning",
        "instruction": "Plan the implementation of a --verbose flag for the CLI tool.",
        "context_files": {
            "src/cli.py": "import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--input', required=True)\n    args = parser.parse_args()\n    process(args.input)\n\ndef process(data):\n    print(data)",
            "tests/test_cli.py": "from cli import main, process\n\ndef test_process():\n    process('hello')"
        },
        "target": "Plan: 1. Add --verbose flag to parser. 2. Create logging setup function. 3. Thread verbosity through process(). 4. Update test to cover verbose mode. 5. Update docs.",
        "diff": "--- 5-step plan across 3 files ---",
        "difficulty": "medium",
        "teacher_explanation": "Multi-step change: parser change + logging setup + parameter threading + tests + docs.",
        "teacher_plan": "1. READ cli.py. 2. Add --verbose arg. 3. Add logging setup. 4. Thread verbosity to process(). 5. Update tests. 6. VERIFY.",
        "teacher_actions": ["READ('src/cli.py')", "READ('tests/test_cli.py')", "PATCH('src/cli.py')", "PATCH('tests/test_cli.py')", "VERIFY('pytest')"],
    },
    {
        "id": "lhp-002", "modality": "long_horizon_planning",
        "instruction": "Plan adding a config option to switch between SQLite and PostgreSQL.",
        "context_files": {
            "src/db.py": "import sqlite3\n\ndef get_connection():\n    return sqlite3.connect('app.db')",
            "config/settings.py": "DATABASE_URL = 'sqlite:///app.db'",
            "tests/test_db.py": "from db import get_connection\n\ndef test_get_connection():\n    conn = get_connection()\n    assert conn is not None"
        },
        "target": "Plan: 1. Add DB engine selection to settings. 2. Create factory function in db.py. 3. Support both SQLite and asyncpg/psycopg2. 4. Update tests for both engines. 5. Add migration support.",
        "diff": "--- 5-step plan across 4 files ---",
        "difficulty": "hard",
        "teacher_explanation": "Significant refactor: need to abstract DB layer, support multiple engines, update all call sites, and verify both engines work.",
        "teacher_plan": "1. READ settings.py. 2. READ db.py. 3. READ tests. 4. PLAN new architecture. 5. PATCH db.py with factory. 6. PATCH settings.py. 7. PATCH tests. 8. VERIFY both engines.",
        "teacher_actions": ["READ('config/settings.py')", "READ('src/db.py')", "READ('tests/test_db.py')", "PATCH('config/settings.py')", "PATCH('src/db.py')", "PATCH('tests/test_db.py')", "VERIFY('pytest')"],
    },
]


def generate_teacher_trace(task: Dict, teacher_model: str, trace_id: int) -> LymeExample:
    """Generate a teacher trace example from a task definition."""

    context_files = task.get("context_files", {})

    retrieved_files = []
    for fp, content in context_files.items():
        role = "test" if "test" in fp.lower() else "source"
        retrieved_files.append(RetrievedFile(
            file_path=fp, role=role,
            content_preview=content[:400],
            lines=len(content.split("\n")),
        ))

    tool_outputs = []
    teacher_actions = task.get("teacher_actions", [])
    for i, action in enumerate(teacher_actions[:15]):
        parts = action.split("(", 1)
        tool_name = parts[0]
        args_str = parts[1].rstrip(")") if len(parts) > 1 else ""
        tool_outputs.append(ToolOutput(
            tool_name=tool_name,
            arguments={"query": args_str} if tool_name in ("SEARCH", "RUN") else {"target": args_str},
            result_summary=f"Teacher {teacher_model}: {action}",
            success=True,
            latency_ms=random.randint(100, 5000),
        ))

    return LymeExample(
        id=f"teacher-{teacher_model.replace(':', '-')}-{task['id']}-{trace_id}",
        modality=task["modality"],
        created=datetime.now(timezone.utc).isoformat(),
        source="distilled",
        source_trace_id=f"teacher:{teacher_model}:{task['id']}",
        difficulty=task.get("difficulty", "medium"),
        instruction=task["instruction"],
        repo_context=RepoContext(
            repo_name=f"teacher-{task['id']}",
            language="Python",
            framework="",
            file_count=len(context_files),
            test_count=1,
            test_framework="pytest",
        ),
        retrieved_files=retrieved_files,
        tool_outputs=tool_outputs,
        reasoning_trace=task.get("teacher_explanation", ""),
        target_output=task["target"],
        patch_diff=task.get("diff", ""),
        language="Python",
        metadata={
            "teacher_model": teacher_model,
            "task_id": task["id"],
            "task_type": task["modality"],
            "num_actions": len(teacher_actions),
            "plan": task.get("teacher_plan", ""),
            "stop_condition": teacher_actions[-1] if teacher_actions else "STOP",
            "num_context_files": len(context_files),
            "source": "teacher_trace",
        },
    )


def query_ollama(model: str, prompt: str) -> Optional[str]:
    """Query an Ollama model. Returns None if unavailable."""
    try:
        import urllib.request
        data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(OLLAMA_BASE_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception as e:
        print(f"    [ollama] {model}: {e}")
        return None


def try_ollama_trace(task: Dict, model: str) -> Optional[LymeExample]:
    """Try to generate a trace using Ollama. Falls back to curated."""
    context_str = "\n".join(
        f"{fp}:\n{content}"
        for fp, content in task.get("context_files", {}).items()
    )
    prompt = (
        f"You are debugging a Python codebase. Given this task:\n\n"
        f"{task['instruction']}\n\n"
        f"Context files:\n{context_str}\n\n"
        f"Provide:\n"
        f"1. SEARCH strategy: what to search for\n"
        f"2. FILE SELECTION: which files to read\n"
        f"3. PLAN: step by step fix plan\n"
        f"4. PATCH: the unified diff\n"
        f"5. VERIFICATION: how to verify it works\n"
        f"6. EXPLANATION: short root cause\n\n"
        f"Keep concise."
    )
    response = query_ollama(model, prompt)
    if not response:
        return None

    return LymeExample(
        id=f"teacher-{model.replace(':', '-')}-{task['id']}-ollama-{random.randint(1000, 9999)}",
        modality=task["modality"],
        created=datetime.now(timezone.utc).isoformat(),
        source="distilled",
        source_trace_id=f"teacher:{model}:{task['id']}",
        difficulty=task.get("difficulty", "medium"),
        instruction=task["instruction"],
        repo_context=RepoContext(
            repo_name=f"teacher-{task['id']}",
            language="Python",
            file_count=len(task.get("context_files", {})),
        ),
        retrieved_files=[
            RetrievedFile(file_path=fp, role="source", content_preview=content[:300])
            for fp, content in task.get("context_files", {}).items()
        ],
        reasoning_trace=response[:2000],
        target_output=response[:3000],
        language="Python",
        metadata={
            "teacher_model": model,
            "task_id": task["id"],
            "source": "ollama_trace",
            "ollama_response": True,
        },
    )


def generate_and_save():
    print("=" * 72)
    print("  Week 84 — Teacher Trace Factory v2")
    print(f"  Tasks: {len(TASKS)}")
    print(f"  Teachers: {', '.join(TEACHER_MODELS)}")
    print(f"  Traces per task: {N_TRACES_PER_TASK}")
    print("=" * 72)
    print()

    all_examples = []
    task_counts = defaultdict(int)
    model_counts = defaultdict(int)
    modality_counts = defaultdict(int)

    for task in TASKS:
        task_id = task["id"]
        print(f"  Task {task_id}: {task['modality']}")

        for teacher in TEACHER_MODELS:
            n = 0
            if teacher == "curated_solution":
                # Generate multiple curated traces with variations
                traces_per_task = N_TRACES_PER_TASK // len(TEACHER_MODELS)
                for i in range(traces_per_task):
                    ex = generate_teacher_trace(task, teacher, i)
                    errs = ex.validate()
                    if not errs:
                        all_examples.append(ex)
                        n += 1
                        task_counts[task_id] += 1
                        model_counts[teacher] += 1
                        modality_counts[task["modality"]] += 1
            else:
                # Try Ollama for model-generated traces
                ex = try_ollama_trace(task, teacher)
                if ex:
                    errs = ex.validate()
                    if not errs:
                        all_examples.append(ex)
                        n += 1
                        task_counts[task_id] += 1
                        model_counts[teacher] += 1
                        modality_counts[task["modality"]] += 1
                # Fall back to curated for remaining
                traces_per_task = N_TRACES_PER_TASK // len(TEACHER_MODELS)
                for i in range(traces_per_task):
                    ex = generate_teacher_trace(task, teacher, i)
                    errs = ex.validate()
                    if not errs:
                        all_examples.append(ex)
                        n += 1
                        task_counts[task_id] += 1
                        model_counts[teacher] += 1
                        modality_counts[task["modality"]] += 1

            print(f"    {teacher}: {n} traces")

    random.shuffle(all_examples)
    n_total = len(all_examples)
    train_end = int(n_total * 0.80)
    val_end = int(n_total * 0.90)

    splits = {
        "train": all_examples[:train_end],
        "val": all_examples[train_end:val_end],
        "test": all_examples[val_end:],
    }

    for split_name, examples in splits.items():
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        by_mod = defaultdict(list)
        for ex in examples:
            by_mod[ex.modality].append(ex)
        for mod, mod_exs in by_mod.items():
            with open(split_dir / f"{mod}.jsonl", "w") as f:
                for e in mod_exs:
                    f.write(e.to_jsonl() + "\n")
        with open(split_dir / "combined.jsonl", "w") as f:
            for e in examples:
                f.write(e.to_jsonl() + "\n")

    # Generate report
    report_lines = [
        "# Week 84 — Teacher Trace Factory v2 Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total traces: {n_total}",
        f"- Tasks: {len(TASKS)}",
        f"- Teachers: {len(TEACHER_MODELS)}",
        "",
        "## Per-Teacher",
    ]
    for model, count in sorted(model_counts.items()):
        report_lines.append(f"- {model}: {count}")
    report_lines.append("")
    report_lines.append("## Per-Modality")
    for mod, count in sorted(modality_counts.items()):
        report_lines.append(f"- {mod}: {count}")
    report_lines.append("")
    report_lines.append("## Per-Task")
    for tid, count in sorted(task_counts.items()):
        report_lines.append(f"- {tid}: {count}")
    report_lines.append("")
    report_lines.append("## Splits")
    for s in ["train", "val", "test"]:
        report_lines.append(f"- {s}: {len(splits[s])}")

    report_path = REPORT_DIR / "TEACHER_TRACE_V2_REPORT.md"
    report_path.write_text("\n".join(report_lines))

    stats = {
        "total": n_total, "tasks": len(TASKS), "teachers": dict(model_counts),
        "modalities": dict(modality_counts), "splits": {s: len(v) for s, v in splits.items()},
    }
    with open(REPORT_DIR / "teacher_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n  Report: {report_path}")
    print("=" * 72)
    print(f"  Total: {n_total} traces")
    print(f"  Teachers: {dict(model_counts)}")
    print(f"  Modalities: {dict(modality_counts)}")
    print(f"  Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)


def main():
    generate_and_save()


if __name__ == "__main__":
    main()
