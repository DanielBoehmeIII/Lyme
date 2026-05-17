#!/usr/bin/env python3
"""Week 43 — Synthetic Bug Factory v2 (expanded bug types, multi-language)."""

import json
import random
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

random.seed(43)
DATASET_DIR = Path("datasets/generated/synthetic_bugs")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week43")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

N_EXAMPLES = 300

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

def make_example(bug_type, modality, instruction, buggy_code, fixed_code, test_code, test_output, file_path, lang="Python", fw="", difficulty="medium", severity="medium"):
    return {
        "id": f"synth-bug-{bug_type}-{random.randint(10000,99999)}",
        "modality": modality,
        "created": datetime.now(timezone.utc).isoformat(),
        "source": "synthetic",
        "difficulty": difficulty,
        "instruction": instruction,
        "buggy_code": buggy_code,
        "fixed_code": fixed_code,
        "test_code": test_code,
        "test_output": test_output,
        "target_output": make_diff(file_path, buggy_code, fixed_code),
        "repo_context": {"repo_name": f"synth-{bug_type}", "language": lang, "framework": fw, "file_count": 1, "total_lines": 0, "test_count": 1, "test_framework": "pytest" if lang == "Python" else ("jest" if lang == "JavaScript" else "cargo test"), "architecture_summary": "", "conventions": []},
        "retrieved_files": [{"file_path": file_path, "role": "source", "content_preview": buggy_code[:300], "lines": len(buggy_code.split("\n")), "relevance_score": 1.0}],
        "tool_outputs": [],
        "metadata": {"bug_type": bug_type, "severity": severity, "language": lang},
    }

# ── Bug Generators ──────────────────────────────────────────────────────────────

WRONG_IMPORT_SCENARIOS = [
    {"lang": "Python", "fw": "FastAPI", "file": "src/handler.py",
     "buggy": "from utils.database import non_existent_connector\n\ndef get_data():\n    conn = non_existent_connector()\n    return conn.query(\"SELECT * FROM items\")",
     "fixed": "from utils.database import get_connection\n\ndef get_data():\n    conn = get_connection()\n    return conn.query(\"SELECT * FROM items\")"},
    {"lang": "Python", "fw": "Django", "file": "src/views.py",
     "buggy": "from django.contrib.auth.decorators import login_not_required\n\n@login_not_required\ndef home(request):\n    return render(request, 'home.html')",
     "fixed": "from django.contrib.auth.decorators import login_required\n\n@login_required\ndef home(request):\n    return render(request, 'home.html')"},
    {"lang": "JavaScript", "fw": "Express", "file": "src/routes.js",
     "buggy": "const { nonExistentMiddleware } = require('./middleware');\n\napp.use(nonExistentMiddleware);",
     "fixed": "const { authMiddleware } = require('./middleware');\n\napp.use(authMiddleware);"},
    {"lang": "Go", "fw": "", "file": "src/handler.go",
     "buggy": "import \"github.com/wrong/pkg\"\n\nfunc Handle() {\n    wrong.DoSomething()\n}",
     "fixed": "import \"github.com/correct/pkg\"\n\nfunc Handle() {\n    correct.DoSomething()\n}"},
]
def gen_wrong_import():
    s = random.choice(WRONG_IMPORT_SCENARIOS)
    test = "# Test would fail with ImportError" if s["lang"] == "Python" else "// Test would fail with import error"
    return make_example("wrong_import", "test_repair",
        f"Fix the import error in {s['file']}: cannot import the correct symbol.",
        s["buggy"], s["fixed"], test,
        "ImportError: cannot import name" if s["lang"] != "Go" else "build error: undefined",
        s["file"], s["lang"], s["fw"], "easy", "high")

OFF_BY_ONE_SCENARIOS = [
    {"lang": "Python", "file": "src/utils.py",
     "buggy": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items)]",
     "fixed": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items) - 1]"},
    {"lang": "JavaScript", "file": "src/array.js",
     "buggy": "function getLast(items) {\n    if (items.length === 0) return null;\n    return items[items.length];\n}",
     "fixed": "function getLast(items) {\n    if (items.length === 0) return null;\n    return items[items.length - 1];\n}"},
    {"lang": "Rust", "file": "src/lib.rs",
     "buggy": "fn get_last(items: &[i32]) -> i32 {\n    items[items.len()]\n}",
     "fixed": "fn get_last(items: &[i32]) -> Option<i32> {\n    items.get(items.len() - 1).copied()\n}"},
    {"lang": "Python", "file": "src/range.py",
     "buggy": "def first_n(n):\n    return list(range(1, n))  # should be range(n) for 0-indexed",
     "fixed": "def first_n(n):\n    return list(range(n))"},
]
def gen_off_by_one():
    s = random.choice(OFF_BY_ONE_SCENARIOS)
    return make_example("off_by_one", "test_repair",
        f"Fix the off-by-one error in {s['file']} causing IndexError.",
        s["buggy"], s["fixed"], "# Test would fail with IndexError",
        "IndexError: list index out of range",
        s["file"], s["lang"], "", "easy", "medium")

NULL_CHECK_SCENARIOS = [
    {"lang": "Python", "file": "src/calculator.py",
     "buggy": "def average(nums):\n    return sum(nums) / len(nums)",
     "fixed": "def average(nums):\n    if not nums:\n        return 0.0\n    return sum(nums) / len(nums)"},
    {"lang": "JavaScript", "file": "src/stats.js",
     "buggy": "function average(nums) {\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n}",
     "fixed": "function average(nums) {\n    if (nums.length === 0) return 0;\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n}"},
    {"lang": "Go", "file": "src/calc.go",
     "buggy": "func Average(nums []float64) float64 {\n    sum := 0.0\n    for _, n := range nums { sum += n }\n    return sum / float64(len(nums))\n}",
     "fixed": "func Average(nums []float64) float64 {\n    if len(nums) == 0 { return 0 }\n    sum := 0.0\n    for _, n := range nums { sum += n }\n    return sum / float64(len(nums))\n}"},
]
def gen_null_check():
    s = random.choice(NULL_CHECK_SCENARIOS)
    return make_example("missing_null_check", "test_repair",
        f"Fix the ZeroDivisionError/null-deref in {s['file']} when input is empty.",
        s["buggy"], s["fixed"], "# Test fails with ZeroDivisionError",
        "ZeroDivisionError: division by zero",
        s["file"], s["lang"], "", "easy", "high")

CONFIG_KEY_SCENARIOS = [
    {"file": "src/config.py", "buggy": "import os\ndef get_db_url():\n    return os.environ['DATABASE_URL']",
     "fixed": "import os\ndef get_db_url():\n    return os.environ.get('DATABASE_URL', 'sqlite:///default.db')"},
    {"file": "src/settings.py", "buggy": "SECRET_KEY = config['SECRET_KEY']",
     "fixed": "SECRET_KEY = config.get('SECRET_KEY', 'fallback-dev-key')"},
]
def gen_config_key():
    s = random.choice(CONFIG_KEY_SCENARIOS)
    return make_example("wrong_config_key", "unified_diff",
        f"Fix the KeyError when config key is missing in {s['file']}. Use safe defaults.",
        s["buggy"], s["fixed"], "# Test fails with KeyError",
        "KeyError: 'DATABASE_URL'",
        s["file"], "Python", "", "medium", "medium")

BROKEN_TEST_SCENARIOS = [
    {"buggy": "def test_multiply():\n    assert multiply(3, 5) == 10",
     "fixed": "def test_multiply():\n    assert multiply(3, 5) == 15"},
    {"buggy": "def test_add():\n    assert add(10, 5) == 20",
     "fixed": "def test_add():\n    assert add(10, 5) == 15"},
    {"buggy": "def test_divide():\n    assert divide(10, 2) == 3",
     "fixed": "def test_divide():\n    assert divide(10, 2) == 5.0"},
    {"buggy": "def test_concat():\n    assert concat('a', 'b') == 'ab '",
     "fixed": "def test_concat():\n    assert concat('a', 'b') == 'ab'"},
]
def gen_broken_test():
    s = random.choice(BROKEN_TEST_SCENARIOS)
    return make_example("broken_test_expectation", "test_repair",
        "Fix the failing test assertion.",
        s["buggy"], s["fixed"], s["buggy"],
        "AssertionError: assert X == Y",
        "tests/test_calc.py", "Python", "pytest", "easy", "low")

API_RENAME_SCENARIOS = [
    {"old": "get_user", "new": "get_user_v2"},
    {"old": "fetch_data", "new": "fetch_data_v2"},
    {"old": "process_item", "new": "process_item_v2"},
    {"old": "validate_input", "new": "validate_input_v2"},
]
def gen_api_rename():
    s = random.choice(API_RENAME_SCENARIOS)
    buggy = f"from api import client\ndef handle():\n    return client.{s['old']}(id=1)"
    fixed = f"from api import client\ndef handle():\n    return client.{s['new']}(id=1)"
    return make_example("api_rename_mismatch", "unified_diff",
        f"Update API call from {s['old']} to {s['new']}.",
        buggy, fixed, "# Test fails with AttributeError",
        f"AttributeError: module 'api' has no attribute '{s['old']}'",
        "src/client.py", "Python", "", "medium", "medium")

PATH_HANDLING_SCENARIOS = [
    {"buggy": "def save_file(filename, content):\n    with open(f'/data/{filename}', 'w') as f:\n        f.write(content)",
     "fixed": "import os\ndef save_file(filename, content):\n    path = os.path.join(os.getcwd(), 'data', filename)\n    os.makedirs('data', exist_ok=True)\n    with open(path, 'w') as f:\n        f.write(content)"},
    {"buggy": "def read_file(path):\n    with open(path, 'r') as f:\n        return f.read()",
     "fixed": "def read_file(path):\n    if not os.path.exists(path):\n        return None\n    with open(path, 'r') as f:\n        return f.read()"},
]
def gen_bad_path():
    s = random.choice(PATH_HANDLING_SCENARIOS)
    return make_example("bad_path_handling", "unified_diff",
        "Fix unsafe file path handling.",
        s["buggy"], s["fixed"], "# Test fails with FileNotFoundError",
        "FileNotFoundError: [Errno 2] No such file or directory",
        "src/storage.py", "Python", "", "medium", "high")

def gen_type_mismatch():
    buggy = "def process(data):\n    return data + 1  # fails if data is string"
    fixed = "def process(data):\n    if not isinstance(data, (int, float)):\n        raise TypeError('expected numeric')\n    return data + 1"
    return make_example("type_mismatch", "test_repair",
        "Fix type mismatch error in process() — add type guard.",
        buggy, fixed, "TypeError: can only concatenate str (not int) to str",
        "TypeError: can only concatenate str (not int) to str",
        "src/processor.py", "Python", "", "medium", "medium")

def gen_infinite_loop():
    buggy = "def find_item(items, target):\n    i = 0\n    while i < len(items):\n        if items[i] == target:\n            return i\n    return -1"
    fixed = "def find_item(items, target):\n    for i, item in enumerate(items):\n        if item == target:\n            return i\n    return -1"
    return make_example("infinite_loop", "unified_diff",
        "Fix infinite loop in find_item — iterator never advances.",
        buggy, fixed, "TimeoutError: test timed out after 5s",
        "TimeoutError: test timed out after 5s",
        "src/search.py", "Python", "", "hard", "high")

def gen_missing_error_handling():
    buggy = "def divide(a, b):\n    return a / b"
    fixed = "def divide(a, b):\n    if b == 0:\n        raise ValueError('division by zero')\n    return a / b"
    return make_example("missing_error_handling", "unified_diff",
        "Add error handling for division by zero.",
        buggy, fixed, "ZeroDivisionError: division by zero",
        "ZeroDivisionError: division by zero",
        "src/math_ops.py", "Python", "", "easy", "medium")

def gen_sql_injection():
    buggy = "def get_user(username):\n    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n    return db.execute(query)"
    fixed = "def get_user(username):\n    query = \"SELECT * FROM users WHERE name = ?\"\n    return db.execute(query, (username,))"
    return make_example("sql_injection", "unified_diff",
        "Fix SQL injection vulnerability in get_user(). Use parameterized query.",
        buggy, fixed, "Security warning: SQL injection detected",
        "Security warning: SQL injection detected",
        "src/db.py", "Python", "", "hard", "critical")

def gen_unclosed_resource():
    buggy = "def read_config():\n    f = open('config.json')\n    return json.load(f)"
    fixed = "def read_config():\n    with open('config.json') as f:\n        return json.load(f)"
    return make_example("unclosed_resource", "unified_diff",
        "Fix unclosed file resource in read_config(). Use context manager.",
        buggy, fixed, "ResourceWarning: unclosed file",
        "ResourceWarning: unclosed file",
        "src/config.py", "Python", "", "easy", "low")

def gen_race_condition():
    buggy = "counter = 0\ndef increment():\n    global counter\n    counter += 1"
    fixed = "import threading\ncounter = 0\nlock = threading.Lock()\ndef increment():\n    global counter\n    with lock:\n        counter += 1"
    return make_example("race_condition", "unified_diff",
        "Fix race condition in counter increment. Add thread lock.",
        buggy, fixed, "FAIL: test_concurrent_increment — expected 1000, got 997",
        "FAIL: test_concurrent_increment — expected 1000, got 997",
        "src/counter.py", "Python", "", "hard", "high")

BUG_GENERATORS = {
    "wrong_import": gen_wrong_import,
    "off_by_one": gen_off_by_one,
    "missing_null_check": gen_null_check,
    "wrong_config_key": gen_config_key,
    "broken_test_expectation": gen_broken_test,
    "api_rename_mismatch": gen_api_rename,
    "bad_path_handling": gen_bad_path,
    "type_mismatch": gen_type_mismatch,
    "infinite_loop": gen_infinite_loop,
    "missing_error_handling": gen_missing_error_handling,
    "sql_injection": gen_sql_injection,
    "unclosed_resource": gen_unclosed_resource,
    "race_condition": gen_race_condition,
}

def write_jsonl(examples, path):
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

def main():
    print("=" * 72)
    print("  Week 43 — Synthetic Bug Factory v2")
    print("=" * 72)
    print(f"  Bug types: {len(BUG_GENERATORS)}")
    print(f"  Per type: {N_EXAMPLES}")
    print()

    all_examples = []
    bug_counts = {}
    for bug_type, generator in sorted(BUG_GENERATORS.items()):
        exs = [generator() for _ in range(N_EXAMPLES)]
        all_examples.extend(exs)
        bug_counts[bug_type] = len(exs)
        print(f"  {bug_type}: {len(exs)}")

    random.shuffle(all_examples)
    n = len(all_examples)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
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
            by_bug[ex["metadata"]["bug_type"]].append(ex)
        for bt, exs in by_bug.items():
            write_jsonl(exs, split_dir / f"{bt}.jsonl")
        write_jsonl(examples, split_dir / "combined.jsonl")
        by_mod = defaultdict(list)
        for ex in examples:
            by_mod[ex["modality"]].append(ex)
        for mod, exs in by_mod.items():
            write_jsonl(exs, split_dir / f"modality_{mod}.jsonl")

    lang_counts = defaultdict(int)
    for ex in all_examples:
        lang_counts[ex["metadata"]["language"]] += 1

    report = [
        "# Week 43 — Synthetic Bug Factory v2 Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> {len(all_examples)} examples, {len(BUG_GENERATORS)} bug types, {len(lang_counts)} languages",
        "",
        "## Per-Bug-Type",
    ]
    for bt, count in sorted(bug_counts.items()):
        report.append(f"- {bt}: {count}")
    report.append("")
    report.append("## Languages")
    for lang, count in sorted(lang_counts.items()):
        report.append(f"- {lang}: {count}")
    report.append("")
    report.append("## Splits")
    for s in ["train", "val", "test"]:
        report.append(f"- {s}: {len(splits[s])}")

    report_path = REPORT_DIR / "SYNTHETIC_BUG_V2_REPORT.md"
    report_path.write_text("\n".join(report))
    print(f"\n  Report: {report_path}")
    print("=" * 72)
    print(f"  Total: {len(all_examples)} examples")
    print(f"  Languages: {dict(lang_counts)}")
    print(f"  Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)

if __name__ == "__main__":
    main()
