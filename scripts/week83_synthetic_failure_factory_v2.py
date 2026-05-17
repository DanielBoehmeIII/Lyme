#!/usr/bin/env python3
"""Week 83 — Synthetic Failure Factory v2.

Generates realistic code failures with test output, correct patches,
and difficulty labels for training bug localization and repair.

Categories:
- broken_import, wrong_function_name, incorrect_config_key, failing_assertion,
  api_mismatch, path_error, type_error, off_by_one, cli_argument_mistake,
  bad_dependency_usage, null_dereference, infinite_loop, unclosed_resource,
  race_condition, sql_injection
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datasets.schema import LymeExample, RepoContext, RetrievedFile, VALID_MODALITIES

random.seed(83)
DATASET_DIR = Path("datasets/v2/synthetic_failures")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week83")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

N_EXAMPLES_PER_TYPE = 500


def make_diff(file_path, before, after):
    before_lines = before.split("\n")
    after_lines = after.split("\n")
    prefix_end = 0
    while prefix_end < len(before_lines) and prefix_end < len(after_lines) and before_lines[prefix_end] == after_lines[prefix_end]:
        prefix_end += 1
    suffix_start_before = len(before_lines) - 1
    suffix_start_after = len(after_lines) - 1
    while suffix_start_before >= prefix_end and suffix_start_after >= prefix_end and before_lines[suffix_start_before] == after_lines[suffix_start_after]:
        suffix_start_before -= 1
        suffix_start_after -= 1
    removed = before_lines[prefix_end:suffix_start_before + 1]
    added = after_lines[prefix_end:suffix_start_after + 1]
    context_before = before_lines[max(0, prefix_end - 3):prefix_end]
    context_after = after_lines[suffix_start_after + 1:min(len(after_lines), suffix_start_after + 4)]
    hunk_start = max(1, prefix_end - 3)
    hunk_len_before = len(context_before) + len(removed) + len(context_after)
    hunk_len_after = len(context_before) + len(added) + len(context_after)
    diff = f"--- a/{file_path}\n+++ b/{file_path}\n"
    diff += f"@@ -{hunk_start},{hunk_len_before} +{hunk_start},{hunk_len_after} @@\n"
    for line in context_before: diff += f" {line}\n"
    for line in removed: diff += f"-{line}\n"
    for line in added: diff += f"+{line}\n"
    for line in context_after: diff += f" {line}\n"
    return diff


def make_example(bug_type, modality, instruction, buggy_code, fixed_code,
                 test_code, test_output, file_path, lang="Python", fw="",
                 difficulty="medium", severity="medium"):
    return LymeExample(
        id=f"v2-fail-{bug_type}-{random.randint(10000, 99999)}",
        modality=modality,
        created=datetime.now(timezone.utc).isoformat(),
        source="synthetic",
        difficulty=difficulty,
        instruction=instruction,
        repo_context=RepoContext(
            repo_name=f"synth-{bug_type}", language=lang,
            framework=fw, file_count=1, test_count=1,
            test_framework="pytest" if lang == "Python" else (
                "jest" if lang == "JavaScript" else "cargo test"),
        ),
        retrieved_files=[
            RetrievedFile(file_path=file_path, role="source",
                          content_preview=buggy_code[:400],
                          lines=len(buggy_code.split("\n"))),
        ],
        patch_before=buggy_code,
        patch_after=fixed_code,
        patch_diff=make_diff(file_path, buggy_code, fixed_code),
        target_output=make_diff(file_path, buggy_code, fixed_code),
        language=lang,
        metadata={
            "bug_type": bug_type,
            "severity": severity,
            "language": lang,
            "framework": fw,
            "failing_test": test_output[:100],
        },
    )


# ─── 1. broken_import ──────────────────────────────────────────────────────────

IMPORT_SCENARIOS = [
    {"lang": "Python", "fw": "FastAPI", "file": "src/handler.py",
     "buggy": "from utils.database import non_existent_connector\n\ndef get_data():\n    conn = non_existent_connector()\n    return conn.query(\"SELECT * FROM items\")",
     "fixed": "from utils.database import get_connection\n\ndef get_data():\n    conn = get_connection()\n    return conn.query(\"SELECT * FROM items\")",
     "output": "ImportError: cannot import name 'non_existent_connector' from 'utils.database'"},
    {"lang": "Python", "fw": "Django", "file": "src/views.py",
     "buggy": "from django.contrib.auth.decorators import login_not_required\n\n@login_not_required\ndef home(request):\n    return render(request, 'home.html')",
     "fixed": "from django.contrib.auth.decorators import login_required\n\n@login_required\ndef home(request):\n    return render(request, 'home.html')",
     "output": "ImportError: cannot import name 'login_not_required'"},
    {"lang": "JavaScript", "fw": "Express", "file": "src/routes.js",
     "buggy": "const { nonExistentMiddleware } = require('./middleware');\napp.use(nonExistentMiddleware);",
     "fixed": "const { authMiddleware } = require('./middleware');\napp.use(authMiddleware);",
     "output": "Error: Cannot destructure property 'nonExistentMiddleware'"},
    {"lang": "Go", "fw": "", "file": "src/handler.go",
     "buggy": "import \"github.com/wrong/pkg\"\nfunc Handle() {\n    wrong.DoSomething()\n}",
     "fixed": "import \"github.com/correct/pkg\"\nfunc Handle() {\n    correct.DoSomething()\n}",
     "output": "build error: imported and not used: \"github.com/wrong/pkg\""},
    {"lang": "Rust", "fw": "", "file": "src/lib.rs",
     "buggy": "use std::collections::NonExistentMap;\nfn process() {\n    let m = NonExistentMap::new();\n}",
     "fixed": "use std::collections::HashMap;\nfn process() {\n    let m = HashMap::new();\n}",
     "output": "error[E0432]: unresolved import `std::collections::NonExistentMap`"},
]

def gen_broken_import():
    s = random.choice(IMPORT_SCENARIOS)
    return make_example("broken_import", "test_repair",
        f"Fix the import error in {s['file']}: {s['output'].split(':')[0]}.",
        s["buggy"], s["fixed"], f"# Test fails with import error\n{s['output']}",
        s["output"], s["file"], s["lang"], s["fw"], "easy", "high")


# ─── 2. wrong_function_name ────────────────────────────────────────────────────

FUNC_NAME_SCENARIOS = [
    {"lang": "Python", "file": "src/client.py",
     "buggy": "from api import client\ndef handle():\n    return client.fetchUsser(id=1)",
     "fixed": "from api import client\ndef handle():\n    return client.fetch_user(id=1)",
     "output": "AttributeError: 'APIClient' object has no attribute 'fetchUsser'"},
    {"lang": "Python", "file": "src/utils.py",
     "buggy": "result = UtillityClass.process_data()",
     "fixed": "result = UtilityClass.process_data()",
     "output": "NameError: name 'UtillityClass' is not defined"},
    {"lang": "JavaScript", "file": "src/app.js",
     "buggy": "const user = db.getUsrs({ active: true });",
     "fixed": "const user = db.getUsers({ active: true });",
     "output": "TypeError: db.getUsrs is not a function"},
    {"lang": "Go", "file": "src/main.go",
     "buggy": "json.Unmarhsal(data, &result)",
     "fixed": "json.Unmarshal(data, &result)",
     "output": "undefined: json.Unmarhsal"},
]

def gen_wrong_function_name():
    s = random.choice(FUNC_NAME_SCENARIOS)
    return make_example("wrong_function_name", "bug_localization",
        f"Find and fix the wrong function name in {s['file']}: {s['output']}.",
        s["buggy"], s["fixed"], f"# Test fails\n# {s['output']}",
        s["output"], s["file"], s["lang"], "", "easy", "high")


# ─── 3. incorrect_config_key ───────────────────────────────────────────────────

CONFIG_KEY_SCENARIOS = [
    {"file": "src/config.py",
     "buggy": "import os\ndef get_db_url():\n    return os.environ['DATABASE_URL']",
     "fixed": "import os\ndef get_db_url():\n    return os.environ.get('DATABASE_URL', 'sqlite:///default.db')",
     "output": "KeyError: 'DATABASE_URL'"},
    {"file": "src/settings.py",
     "buggy": "DEBUG = settings['DEBUG_MODE']  # key doesn't exist",
     "fixed": "DEBUG = settings.get('DEBUG_MODE', False)",
     "output": "KeyError: 'DEBUG_MODE'"},
    {"file": "config/app.config.js",
     "buggy": "const port = process.env.PORT || undefined;\nserver.listen(port);",
     "fixed": "const port = parseInt(process.env.PORT, 10) || 3000;\nserver.listen(port);",
     "output": "TypeError: Server.listen() requires a valid port number"},
    {"file": "src/config.rs",
     "buggy": "let db_url = env::var(\"DATABASE_URL\").unwrap();",
     "fixed": "let db_url = env::var(\"DATABASE_URL\").unwrap_or_else(|_| \"postgres://localhost/db\".to_string());",
     "output": "thread 'main' panicked: called `Result::unwrap()` on an `Err` value: NotPresent"},
]

def gen_incorrect_config_key():
    s = random.choice(CONFIG_KEY_SCENARIOS)
    return make_example("incorrect_config_key", "unified_diff",
        f"Fix the missing config key error in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails with KeyError\n{s['output']}",
        s["output"], s["file"],
        "Python" if s["file"].endswith(".py") else (
            "JavaScript" if s["file"].endswith(".js") else "Rust"),
        "", "medium", "medium")


# ─── 4. failing_assertion ──────────────────────────────────────────────────────

ASSERTION_SCENARIOS = [
    {"buggy": "def test_multiply():\n    assert multiply(3, 5) == 10",
     "fixed": "def test_multiply():\n    assert multiply(3, 5) == 15",
     "output": "AssertionError: assert 15 == 10"},
    {"buggy": "def test_add():\n    assert add(10, 5) == 20",
     "fixed": "def test_add():\n    assert add(10, 5) == 15",
     "output": "AssertionError: assert 15 == 20"},
    {"buggy": "def test_divide():\n    assert divide(10, 2) == 3",
     "fixed": "def test_divide():\n    assert divide(10, 2) == 5.0",
     "output": "AssertionError: assert 5.0 == 3"},
    {"buggy": "def test_concat():\n    assert concat('a', 'b') == 'ab '",
     "fixed": "def test_concat():\n    assert concat('a', 'b') == 'ab'",
     "output": "AssertionError: assert 'ab' == 'ab '"},
    {"buggy": "it('should return true', () => {\n  expect(isActive(false)).toBe(true);\n});",
     "fixed": "it('should return false when inactive', () => {\n  expect(isActive(false)).toBe(false);\n});",
     "output": "Expected: true, Received: false"},
]

def gen_failing_assertion():
    s = random.choice(ASSERTION_SCENARIOS)
    return make_example("failing_assertion", "test_repair",
        f"Fix the failing assertion: {s['output'][:60]}.",
        s["buggy"], s["fixed"], s["buggy"],
        s["output"], "tests/test_calc.py",
        "Python" if "def test_" in s["buggy"] else "JavaScript",
        "pytest" if "def test_" in s["buggy"] else "jest", "easy", "low")


# ─── 5. api_mismatch ───────────────────────────────────────────────────────────

API_MISMATCH_SCENARIOS = [
    {"lang": "Python", "file": "src/migration.py",
     "buggy": "client_v2.get_user(42)  # v2 returns dict, not object",
     "fixed": "result = client_v2.get_user(42)\nuser_id = result['id']  # v2 returns dict",
     "output": "TypeError: 'dict' object has no attribute 'id'"},
    {"lang": "JavaScript", "file": "src/request.js",
     "buggy": "fetch('/api/users').then(res => res.json()).then(data => console.log(data.name))",
     "fixed": "fetch('/api/users').then(res => res.json()).then(data => console.log(data[0].name))",
     "output": "TypeError: Cannot read properties of undefined (reading 'name')"},
    {"lang": "Python", "file": "src/logger.py",
     "buggy": "logger.log('info', 'message')  # new API uses logger.info()",
     "fixed": "logger.info('message')",
     "output": "TypeError: log() takes 2 positional arguments but 3 were given"},
    {"lang": "Go", "file": "src/http.go",
     "buggy": "http.Get(\"https://api.example.com\")  # returns (resp, err) now",
     "fixed": "resp, err := http.Get(\"https://api.example.com\")\nif err != nil { return err }",
     "output": "http.Get defined but multiple-value return not handled"},
]

def gen_api_mismatch():
    s = random.choice(API_MISMATCH_SCENARIOS)
    return make_example("api_mismatch", "unified_diff",
        f"Fix API mismatch in {s['file']}: {s['output'][:70]}.",
        s["buggy"], s["fixed"], f"# Test fails\n# {s['output']}",
        s["output"], s["file"], s["lang"], "", "medium", "medium")


# ─── 6. path_error ─────────────────────────────────────────────────────────────

PATH_SCENARIOS = [
    {"lang": "Python", "file": "src/storage.py",
     "buggy": "def save_file(filename, content):\n    with open(f'/data/{filename}', 'w') as f:\n        f.write(content)",
     "fixed": "import os\ndef save_file(filename, content):\n    path = os.path.join(os.getcwd(), 'data', filename)\n    os.makedirs('data', exist_ok=True)\n    with open(path, 'w') as f:\n        f.write(content)",
     "output": "FileNotFoundError: [Errno 2] No such file or directory: '/data/file.txt'"},
    {"lang": "Python", "file": "src/fs.py",
     "buggy": "def read_file(path):\n    with open(path, 'r') as f:\n        return f.read()",
     "fixed": "def read_file(path):\n    if not os.path.exists(path):\n        return None\n    with open(path, 'r') as f:\n        return f.read()",
     "output": "FileNotFoundError: [Errno 2] No such file or directory: '/tmp/missing.txt'"},
    {"lang": "JavaScript", "file": "src/fs.js",
     "buggy": "const data = fs.readFileSync('/etc/config.json');",
     "fixed": "const path = require('path');\nconst configPath = path.join(__dirname, 'config.json');\nconst data = fs.readFileSync(configPath, 'utf8');",
     "output": "Error: ENOENT: no such file or directory, open '/etc/config.json'"},
]

def gen_path_error():
    s = random.choice(PATH_SCENARIOS)
    return make_example("path_error", "unified_diff",
        f"Fix path error in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails with FileNotFoundError\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "medium", "high")


# ─── 7. type_error ─────────────────────────────────────────────────────────────

TYPE_SCENARIOS = [
    {"lang": "Python", "file": "src/processor.py",
     "buggy": "def process(data):\n    return data + 1",
     "fixed": "def process(data):\n    if not isinstance(data, (int, float)):\n        raise TypeError('expected numeric')\n    return data + 1",
     "output": "TypeError: can only concatenate str (not int) to str"},
    {"lang": "Python", "file": "src/serializer.py",
     "buggy": "def serialize(obj):\n    return json.dumps(obj) + 1",
     "fixed": "def serialize(obj):\n    return json.dumps(obj)",
     "output": "TypeError: can only concatenate str (not int) to str"},
    {"lang": "JavaScript", "file": "src/calc.js",
     "buggy": "function sum(arr) { return arr.reduce((a, b) => a + b); }\n// arr may contain strings",
     "fixed": "function sum(arr) {\n    return arr.reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0);\n}",
     "output": "TypeError: Cannot mix BigInt and other types"},
    {"lang": "Rust", "file": "src/types.rs",
     "buggy": "fn add(a: i32, b: i32) -> i32 { a + b }\n// called with &str by mistake",
     "fixed": "fn add(a: i32, b: i32) -> i32 { a + b }\n// caller must parse strings first",
     "output": "error[E0308]: mismatched types expected `i32`, found `&str`"},
]

def gen_type_error():
    s = random.choice(TYPE_SCENARIOS)
    return make_example("type_error", "test_repair",
        f"Fix type error in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails with TypeError\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "medium", "medium")


# ─── 8. off_by_one ─────────────────────────────────────────────────────────────

OFF_BY_ONE_SCENARIOS = [
    {"lang": "Python", "file": "src/utils.py",
     "buggy": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items)]",
     "fixed": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items) - 1]",
     "output": "IndexError: list index out of range"},
    {"lang": "JavaScript", "file": "src/array.js",
     "buggy": "function getLast(items) {\n    if (items.length === 0) return null;\n    return items[items.length];\n}",
     "fixed": "function getLast(items) {\n    if (items.length === 0) return null;\n    return items[items.length - 1];\n}",
     "output": "TypeError: Cannot read properties of undefined"},
    {"lang": "Python", "file": "src/range.py",
     "buggy": "def first_n(n):\n    return list(range(1, n))",
     "fixed": "def first_n(n):\n    return list(range(n))",
     "output": "AssertionError: first_n(3) returned [1, 2] expected [0, 1, 2]"},
    {"lang": "Rust", "file": "src/lib.rs",
     "buggy": "fn get_last(items: &[i32]) -> i32 {\n    items[items.len()]\n}",
     "fixed": "fn get_last(items: &[i32]) -> Option<i32> {\n    items.get(items.len() - 1).copied()\n}",
     "output": "thread 'main' panicked: index out of bounds: len 3, index 3"},
    {"lang": "Go", "file": "src/slice.go",
     "buggy": "func last(items []int) int {\n    return items[len(items)]\n}",
     "fixed": "func last(items []int) (int, error) {\n    if len(items) == 0 { return 0, errors.New(\"empty\") }\n    return items[len(items)-1], nil\n}",
     "output": "panic: runtime error: index out of range [3] with length 3"},
]

def gen_off_by_one():
    s = random.choice(OFF_BY_ONE_SCENARIOS)
    return make_example("off_by_one", "test_repair",
        f"Fix off-by-one error in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "easy", "medium")


# ─── 9. cli_argument_mistake ───────────────────────────────────────────────────

CLI_SCENARIOS = [
    {"lang": "Python", "fw": "argparse", "file": "src/cli.py",
     "buggy": "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('name')  # should be --name\nargs = parser.parse_args()\nprint(f'Hello {args.name}')",
     "fixed": "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--name', default='world')\nargs = parser.parse_args()\nprint(f'Hello {args.name}')",
     "output": "usage: cli.py [-h] name\ncli.py: error: the following arguments are required: name"},
    {"lang": "Python", "fw": "click", "file": "src/cli.py",
     "buggy": "@click.command()\n@click.option('--count', default=1, type=str)\ndef greet(count):\n    for _ in range(count):\n        click.echo('Hello!')",
     "fixed": "@click.command()\n@click.option('--count', default=1, type=int)\ndef greet(count):\n    for _ in range(count):\n        click.echo('Hello!')",
     "output": "TypeError: '<' not supported between instances of 'str' and 'int'"},
    {"lang": "Python", "fw": "argparse", "file": "src/tool.py",
     "buggy": "parser.add_argument('--verbose', type=str)  # should be action='store_true'",
     "fixed": "parser.add_argument('--verbose', action='store_true')",
     "output": "TypeError: expected True/False, got 'yes'"},
    {"lang": "JavaScript", "file": "src/cli.js",
     "buggy": "const yargs = require('yargs');\nconst argv = yargs.argv;\nconsole.log(`Hello ${argv.name}`);  // must be --name=value, not positional",
     "fixed": "const yargs = require('yargs');\nconst argv = yargs.option('name', { type: 'string', demand: false }).argv;\nconsole.log(`Hello ${argv.name || 'world'}`);",
     "output": "undefined is printed for name"},
]

def gen_cli_argument_mistake():
    s = random.choice(CLI_SCENARIOS)
    return make_example("cli_argument_mistake", "bug_localization",
        f"Fix CLI argument mistake in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# CLI test fails\n{s['output']}",
        s["output"], s["file"], s["lang"], s.get("fw", ""),
        "medium" if "type" in s["buggy"] else "easy", "medium")


# ─── 10. bad_dependency_usage ──────────────────────────────────────────────────

DEP_SCENARIOS = [
    {"lang": "Python", "file": "src/main.py",
     "buggy": "import requests\nresponse = requests.get('https://api.example.com')\ndata = json.loads(response)  # response is Response object, not str",
     "fixed": "import requests\nresponse = requests.get('https://api.example.com')\ndata = response.json()",
     "output": "TypeError: the JSON object must be str, bytes or bytearray, not Response"},
    {"lang": "Python", "file": "src/db.py",
     "buggy": "import sqlite3\nconn = sqlite3.connect('db.sqlite')\ncursor = conn.execute('SELECT * FROM users')\nresults = cursor  # cursor is not a list",
     "fixed": "conn = sqlite3.connect('db.sqlite')\ncursor = conn.execute('SELECT * FROM users')\nresults = cursor.fetchall()",
     "output": "sqlite3.Cursor object at 0x... (not iterable in expected way)"},
    {"lang": "JavaScript", "file": "src/server.js",
     "buggy": "const express = require('express');\nconst app = express();\napp.use(express.bodyParser());  # deprecated since 4.16",
     "fixed": "const express = require('express');\nconst app = express();\napp.use(express.json());",
     "output": "TypeError: express.bodyParser is not a function"},
    {"lang": "Python", "file": "src/pandas_usage.py",
     "buggy": "import pandas as pd\ndf = pd.read_csv('data.csv')\nrow = df[0]  # should use .iloc[0]",
     "fixed": "df = pd.read_csv('data.csv')\nrow = df.iloc[0]",
     "output": "KeyError: 0"},
    {"lang": "Go", "file": "src/http.go",
     "buggy": "import \"net/http\"\nclient := &http.Client{}\nresp, _ := client.Get(\"https://example.com\")\nbody := resp.Body  # need to read resp.Body",
     "fixed": "import (\"net/http\"; \"io\")\nclient := &http.Client{}\nresp, _ := client.Get(\"https://example.com\")\nbody, _ := io.ReadAll(resp.Body)",
     "output": "body is *http.Response, not string"},
]

def gen_bad_dependency_usage():
    s = random.choice(DEP_SCENARIOS)
    return make_example("bad_dependency_usage", "unified_diff",
        f"Fix bad dependency usage in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "medium", "medium")


# ─── 11. null_dereference (existing: missing_null_check, upgraded) ─────────────

NULL_DEREF_SCENARIOS = [
    {"lang": "Python", "file": "src/calculator.py",
     "buggy": "def average(nums):\n    return sum(nums) / len(nums)",
     "fixed": "def average(nums):\n    if not nums:\n        return 0.0\n    return sum(nums) / len(nums)",
     "output": "ZeroDivisionError: division by zero"},
    {"lang": "JavaScript", "file": "src/stats.js",
     "buggy": "function average(nums) {\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n}",
     "fixed": "function average(nums) {\n    if (nums.length === 0) return 0;\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n}",
     "output": "TypeError: Cannot read properties of undefined (reading 'length')"},
    {"lang": "Go", "file": "src/calc.go",
     "buggy": "func Average(nums []float64) float64 {\n    sum := 0.0\n    for _, n := range nums { sum += n }\n    return sum / float64(len(nums))\n}",
     "fixed": "func Average(nums []float64) float64 {\n    if len(nums) == 0 { return 0 }\n    sum := 0.0\n    for _, n := range nums { sum += n }\n    return sum / float64(len(nums))\n}",
     "output": "panic: runtime error: float64 divided by zero"},
    {"lang": "Java", "file": "src/Calculator.java",
     "buggy": "public double average(int[] nums) {\n    int sum = 0;\n    for (int n : nums) sum += n;\n    return sum / nums.length;\n}",
     "fixed": "public double average(int[] nums) {\n    if (nums == null || nums.length == 0) return 0;\n    int sum = 0;\n    for (int n : nums) sum += n;\n    return (double) sum / nums.length;\n}",
     "output": "java.lang.ArithmeticException: / by zero"},
]

def gen_null_dereference():
    s = random.choice(NULL_DEREF_SCENARIOS)
    return make_example("null_dereference", "test_repair",
        f"Fix null/empty dereference in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Test fails\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "easy", "high")


# ─── 12. infinite_loop (upgraded) ──────────────────────────────────────────────

INFINITE_LOOP_SCENARIOS = [
    {"lang": "Python", "file": "src/search.py",
     "buggy": "def find_item(items, target):\n    i = 0\n    while i < len(items):\n        if items[i] == target:\n            return i\n    return -1",
     "fixed": "def find_item(items, target):\n    for i, item in enumerate(items):\n        if item == target:\n            return i\n    return -1",
     "output": "TimeoutError: test timed out after 5s"},
    {"lang": "JavaScript", "file": "src/search.js",
     "buggy": "function findItem(items, target) {\n    let i = 0;\n    while (i < items.length) {\n        if (items[i] === target) return i;\n    }\n    return -1;\n}",
     "fixed": "function findItem(items, target) {\n    for (let i = 0; i < items.length; i++) {\n        if (items[i] === target) return i;\n    }\n    return -1;\n}",
     "output": "Timeout: test exceeded 5000ms"},
    {"lang": "Python", "file": "src/loop.py",
     "buggy": "def process(items):\n    for item in items:\n        items.append(item * 2)  # grows forever",
     "fixed": "def process(items):\n    result = []\n    for item in items:\n        result.append(item * 2)\n    return result",
     "output": "MemoryError: list grows indefinitely"},
]

def gen_infinite_loop():
    s = random.choice(INFINITE_LOOP_SCENARIOS)
    return make_example("infinite_loop", "unified_diff",
        f"Fix infinite loop in {s['file']}: {s['output'][:50]}.",
        s["buggy"], s["fixed"], f"# Test times out\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "hard", "high")


# ─── 13. unclosed_resource (upgraded) ──────────────────────────────────────────

RESOURCE_SCENARIOS = [
    {"lang": "Python", "file": "src/config.py",
     "buggy": "def read_config():\n    f = open('config.json')\n    return json.load(f)",
     "fixed": "def read_config():\n    with open('config.json') as f:\n        return json.load(f)",
     "output": "ResourceWarning: unclosed file <_io.TextIOWrapper"},
    {"lang": "Python", "file": "src/db.py",
     "buggy": "def query_db(sql):\n    conn = sqlite3.connect('db.sqlite')\n    return conn.execute(sql).fetchall()",
     "fixed": "def query_db(sql):\n    with sqlite3.connect('db.sqlite') as conn:\n        return conn.execute(sql).fetchall()",
     "output": "ResourceWarning: unclosed database connection"},
    {"lang": "JavaScript", "file": "src/reader.js",
     "buggy": "const stream = fs.createReadStream('file.txt');\nstream.on('data', chunk => process(chunk));",
     "fixed": "const stream = fs.createReadStream('file.txt');\nstream.on('data', chunk => process(chunk));\nstream.on('end', () => stream.destroy());",
     "output": "Warning: Event emitter leak detected (stream not destroyed)"},
]

def gen_unclosed_resource():
    s = random.choice(RESOURCE_SCENARIOS)
    return make_example("unclosed_resource", "unified_diff",
        f"Fix unclosed resource in {s['file']}: {s['output'][:50]}.",
        s["buggy"], s["fixed"], f"# Resource leak warning\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "easy", "low")


# ─── 14. race_condition (upgraded) ─────────────────────────────────────────────

RACE_SCENARIOS = [
    {"lang": "Python", "file": "src/counter.py",
     "buggy": "counter = 0\ndef increment():\n    global counter\n    counter += 1",
     "fixed": "import threading\ncounter = 0\nlock = threading.Lock()\ndef increment():\n    global counter\n    with lock:\n        counter += 1",
     "output": "FAIL: test_concurrent_increment — expected 1000, got 997"},
    {"lang": "Python", "file": "src/cache.py",
     "buggy": "cache = {}\ndef set_key(key, value):\n    cache[key] = value  # not thread-safe",
     "fixed": "import threading\ncache = {}\ncache_lock = threading.Lock()\ndef set_key(key, value):\n    with cache_lock:\n        cache[key] = value",
     "output": "FAIL: test_concurrent_cache — inconsistent reads"},
    {"lang": "Go", "file": "src/counter.go",
     "buggy": "var counter int\nfunc increment() {\n    counter++\n}",
     "fixed": "var (\n    counter int\n    mu      sync.Mutex\n)\nfunc increment() {\n    mu.Lock()\n    defer mu.Unlock()\n    counter++\n}",
     "output": "WARNING: DATA RACE — Write at 0x... by goroutine"},
]

def gen_race_condition():
    s = random.choice(RACE_SCENARIOS)
    return make_example("race_condition", "unified_diff",
        f"Fix race condition in {s['file']}: {s['output'][:60]}.",
        s["buggy"], s["fixed"], f"# Concurrent test fails\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "hard", "high")


# ─── 15. sql_injection (upgraded) ──────────────────────────────────────────────

SQL_INJECTION_SCENARIOS = [
    {"lang": "Python", "file": "src/db.py",
     "buggy": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n    return db.execute(query)",
     "fixed": "def get_user(username):\n    query = \"SELECT * FROM users WHERE name = ?\"\n    return db.execute(query, (username,))",
     "output": "SecurityError: SQL injection pattern detected in query"},
    {"lang": "JavaScript", "file": "src/db.js",
     "buggy": "db.query(`SELECT * FROM users WHERE id = ${userId}`)",
     "fixed": "db.query('SELECT * FROM users WHERE id = $1', [userId])",
     "output": "Possible SQL injection detected by linter"},
    {"lang": "Python", "file": "src/orm.py",
     "buggy": "User.objects.raw(f\"SELECT * FROM users WHERE name = '{name}'\")",
     "fixed": "User.objects.filter(name=name)",
     "output": "SQL injection vulnerability warning"},
]

def gen_sql_injection():
    s = random.choice(SQL_INJECTION_SCENARIOS)
    return make_example("sql_injection", "unified_diff",
        f"Fix SQL injection vulnerability in {s['file']}: use parameterized query.",
        s["buggy"], s["fixed"], f"# Security scan fails\n{s['output']}",
        s["output"], s["file"], s["lang"], "", "hard", "critical")


# ─── Generator Registry ────────────────────────────────────────────────────────

BUG_GENERATORS = {
    "broken_import": gen_broken_import,
    "wrong_function_name": gen_wrong_function_name,
    "incorrect_config_key": gen_incorrect_config_key,
    "failing_assertion": gen_failing_assertion,
    "api_mismatch": gen_api_mismatch,
    "path_error": gen_path_error,
    "type_error": gen_type_error,
    "off_by_one": gen_off_by_one,
    "cli_argument_mistake": gen_cli_argument_mistake,
    "bad_dependency_usage": gen_bad_dependency_usage,
    "null_dereference": gen_null_dereference,
    "infinite_loop": gen_infinite_loop,
    "unclosed_resource": gen_unclosed_resource,
    "race_condition": gen_race_condition,
    "sql_injection": gen_sql_injection,
}


def write_jsonl(examples, path):
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex.to_dict()) + "\n")


def main():
    print("=" * 72)
    print("  Week 83 — Synthetic Failure Factory v2")
    print(f"  Bug types: {len(BUG_GENERATORS)}")
    print(f"  Per type: {N_EXAMPLES_PER_TYPE}")
    print("=" * 72)
    print()

    all_examples = []
    bug_counts = {}
    for bug_type, generator in sorted(BUG_GENERATORS.items()):
        exs = [generator() for _ in range(N_EXAMPLES_PER_TYPE)]
        all_examples.extend(exs)
        bug_counts[bug_type] = len(exs)

        # Validate each example
        valid = sum(1 for e in exs if not e.validate())
        has_diff = sum(1 for e in exs if e.patch_diff)
        has_test = sum(1 for e in exs if e.metadata.get("failing_test"))
        print(f"  {bug_type}: {len(exs)} generated, {valid} valid, "
              f"{has_diff} with diff, {has_test} with test output")

    random.shuffle(all_examples)
    n = len(all_examples)
    train_end = int(n * 0.80)
    val_end = int(n * 0.90)
    splits = {
        "train": all_examples[:train_end],
        "val": all_examples[train_end:val_end],
        "test": all_examples[val_end:],
    }

    for split_name, examples in splits.items():
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        by_bug = defaultdict(list)
        for ex in examples:
            bt = ex.metadata["bug_type"]
            by_bug[bt].append(ex)
        for bt, exs in by_bug.items():
            write_jsonl(exs, split_dir / f"{bt}.jsonl")
        write_jsonl(examples, split_dir / "combined.jsonl")
        by_mod = defaultdict(list)
        for ex in examples:
            by_mod[ex.modality].append(ex)
        for mod, exs in by_mod.items():
            write_jsonl(exs, split_dir / f"modality_{mod}.jsonl")

    lang_counts = defaultdict(int)
    diff_counts = defaultdict(int)
    for ex in all_examples:
        lang_counts[ex.language] += 1
        diff_counts[ex.difficulty] += 1

    report_lines = [
        "# Week 83 — Synthetic Failure Factory v2 Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> {len(all_examples)} examples, {len(BUG_GENERATORS)} bug types, {len(lang_counts)} languages",
        "",
        "## Per-Bug-Type",
    ]
    for bt, count in sorted(bug_counts.items()):
        report_lines.append(f"- {bt}: {count}")
    report_lines.append("")
    report_lines.append("## Languages")
    for lang, count in sorted(lang_counts.items()):
        report_lines.append(f"- {lang}: {count}")
    report_lines.append("")
    report_lines.append("## Difficulty Distribution")
    for d, count in sorted(diff_counts.items()):
        report_lines.append(f"- {d}: {count}")
    report_lines.append("")
    report_lines.append("## Splits")
    for s in ["train", "val", "test"]:
        report_lines.append(f"- {s}: {len(splits[s])}")

    report_path = REPORT_DIR / "SYNTHETIC_FAILURE_V2_REPORT.md"
    report_path.write_text("\n".join(report_lines))

    print(f"\n  Report: {report_path}")
    print("=" * 72)
    print(f"  Total: {len(all_examples)} examples")
    print(f"  Languages: {dict(lang_counts)}")
    print(f"  Difficulty: {dict(diff_counts)}")
    print(f"  Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
