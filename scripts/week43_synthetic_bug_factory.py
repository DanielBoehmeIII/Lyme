#!/usr/bin/env python3
"""Week 43: Synthetic Bug Factory.

Injects realistic bugs into template code and generates:
- failing code state
- test output
- repair patch
- metadata for training

Bug types:
- wrong_import
- off_by_one
- missing_null_check
- wrong_config_key
- broken_test_expectation
- api_rename_mismatch
- bad_path_handling
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

random.seed(42)

DATASET_DIR = Path("datasets/generated/synthetic_bugs")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week43")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

N_EXAMPLES_PER_BUG = 100


def make_diff(file_path: str, before: str, after: str) -> str:
    """Generate a unified diff."""
    before_lines = before.split("\n")
    after_lines = after.split("\n")
    
    # Find common prefix/suffix
    prefix_end = 0
    while prefix_end < len(before_lines) and prefix_end < len(after_lines) and before_lines[prefix_end] == after_lines[prefix_end]:
        prefix_end += 1
    
    suffix_start_before = len(before_lines) - 1
    suffix_start_after = len(after_lines) - 1
    while (suffix_start_before >= prefix_end and suffix_start_after >= prefix_end and 
           before_lines[suffix_start_before] == after_lines[suffix_start_after]):
        suffix_start_before -= 1
        suffix_start_after -= 1
    
    # Extract changed regions
    removed = before_lines[prefix_end:suffix_start_before + 1]
    added = after_lines[prefix_end:suffix_start_after + 1]
    
    context_before = before_lines[max(0, prefix_end - 3):prefix_end]
    context_after = after_lines[suffix_start_after + 1:min(len(after_lines), suffix_start_after + 4)]
    
    # Build diff
    hunk_start = max(1, prefix_end - 3)
    hunk_len_before = len(context_before) + len(removed) + len(context_after)
    hunk_len_after = len(context_before) + len(added) + len(context_after)
    
    diff = f"--- a/{file_path}\n+++ b/{file_path}\n"
    diff += f"@@ -{hunk_start},{hunk_len_before} +{hunk_start},{hunk_len_after} @@\n"
    for line in context_before:
        diff += f" {line}\n"
    for line in removed:
        diff += f"-{line}\n"
    for line in added:
        diff += f"+{line}\n"
    for line in context_after:
        diff += f" {line}\n"
    
    return diff


def generate_test_output(test_code: str, buggy_code: str) -> str:
    """Generate simulated test output based on bug type."""
    if "missing_null_check" in buggy_code:
        return "FAIL: test_average_empty_list — ZeroDivisionError: division by zero\n  File \"src/calculator.py\", line 5, in average\n    return sum(nums) / len(nums)\nZeroDivisionError: division by zero"
    if "off_by_one" in buggy_code:
        return "FAIL: test_get_last_element — IndexError: list index out of range\n  File \"src/utils.py\", line 8, in get_last\n    return items[len(items)]\nIndexError: list index out of range"
    if "wrong_import" in buggy_code:
        return "FAIL: test_import_module — ImportError: cannot import name 'non_existent_function' from 'module'\n  File \"src/main.py\", line 1, in <module>\n    from module import non_existent_function\nImportError: cannot import name 'non_existent_function'"
    if "wrong_config_key" in buggy_code:
        return "FAIL: test_config_loading — KeyError: 'DATABASE_URL'\n  File \"src/config.py\", line 12, in load_config\n    return config['DATABASE_URL']\nKeyError: 'DATABASE_URL'"
    if "api_rename_mismatch" in buggy_code:
        return "FAIL: test_api_endpoint — AttributeError: module 'api' has no attribute 'get_user_v2'\n  File \"src/client.py\", line 15, in fetch_user\n    return api.get_user_v2(user_id)\nAttributeError: module 'api' has no attribute 'get_user_v2'"
    if "broken_test_expectation" in test_code:
        return "FAIL: test_calculation — AssertionError: assert 15 == 10\n  File \"tests/test_calc.py\", line 12, in test_calculation\n    assert result == 10\nAssertionError: assert 15 == 10"
    if "bad_path_handling" in buggy_code:
        return "FAIL: test_save_file — FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/data/file.txt'\n  File \"src/storage.py\", line 10, in save_file\n    with open(path, 'w') as f:\nFileNotFoundError"
    return "FAIL: test_unknown — AssertionError"


def bug_wrong_import() -> dict:
    codebase = random.choice([
        {"lang": "Python", "fw": "FastAPI"},
        {"lang": "Python", "fw": "Django"},
        {"lang": "Python", "fw": "Flask"},
    ])
    
    buggy = """from data_processor import non_existent_processor

def handle_request(data):
    result = non_existent_processor(data)
    return {"status": "ok", "data": result}
"""
    fixed = """from data_processor import DataProcessor

def handle_request(data):
    processor = DataProcessor()
    result = processor.process(data)
    return {"status": "ok", "data": result}
"""
    test = """from data_processor import DataProcessor

def test_handle_request():
    result = handle_request({"key": "value"})
    assert result["status"] == "ok"
"""
    return {
        "id": f"synth-bug-wrong_import-{random.randint(10000,99999)}",
        "modality": "test_repair",
        "source": "synthetic",
        "difficulty": "easy",
        "bug_type": "wrong_import",
        "instruction": "Fix the import error in the data handler module.",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": "ImportError: cannot import name 'non_existent_processor' from 'data_processor'",
        "target_output": make_diff("src/handler.py", buggy, fixed),
        "repo_context": {"repo_name": "data-app", "language": codebase["lang"], "framework": codebase["fw"]},
        "retrieved_files": [{"file_path": "src/handler.py", "role": "source", "content_preview": buggy[:200]}],
        "metadata": {"bug_type": "wrong_import", "severity": "high"},
    }


def bug_off_by_one() -> dict:
    buggy = """def get_last(items):
    if not items:
        return None
    return items[len(items)]
"""
    fixed = """def get_last(items):
    if not items:
        return None
    return items[len(items) - 1]
"""
    test = """def test_get_last():
    assert get_last([1, 2, 3]) == 3
    assert get_last([]) is None
    assert get_last(["a"]) == "a"
"""
    return {
        "id": f"synth-bug-off_by_one-{random.randint(10000,99999)}",
        "modality": "test_repair",
        "source": "synthetic",
        "difficulty": "easy",
        "bug_type": "off_by_one",
        "instruction": "Fix the off-by-one error causing an IndexError in get_last().",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": "IndexError: list index out of range",
        "target_output": make_diff("src/utils.py", buggy, fixed),
        "repo_context": {"repo_name": "lib", "language": "Python", "framework": ""},
        "retrieved_files": [{"file_path": "src/utils.py", "role": "source", "content_preview": buggy[:150]}],
        "metadata": {"bug_type": "off_by_one", "severity": "medium"},
    }


def bug_null_check() -> dict:
    buggy = """def average(nums):
    return sum(nums) / len(nums)
"""
    fixed = """def average(nums):
    if not nums:
        return 0.0
    return sum(nums) / len(nums)
"""
    test = """def test_average():
    assert average([1, 2, 3]) == 2.0
    assert average([]) == 0.0
"""
    return {
        "id": f"synth-bug-null_check-{random.randint(10000,99999)}",
        "modality": "test_repair",
        "source": "synthetic",
        "difficulty": "easy",
        "bug_type": "missing_null_check",
        "instruction": "Fix the ZeroDivisionError when average() receives an empty list.",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": "ZeroDivisionError: division by zero",
        "target_output": make_diff("src/calculator.py", buggy, fixed),
        "repo_context": {"repo_name": "calc", "language": "Python", "framework": ""},
        "retrieved_files": [{"file_path": "src/calculator.py", "role": "source", "content_preview": buggy[:100]}],
        "metadata": {"bug_type": "missing_null_check", "severity": "high"},
    }


def bug_config_key() -> dict:
    codebase = random.choice([
        {"lang": "Python", "fw": "Django", "config_file": "settings.py"},
        {"lang": "Python", "fw": "Flask", "config_file": "config.py"},
    ])
    
    buggy = """import os

def get_database_url():
    return os.environ['DATABASE_URL']
"""
    fixed = """import os

def get_database_url():
    return os.environ.get('DATABASE_URL', 'sqlite:///default.db')
"""
    test = """def test_get_database_url():
    url = get_database_url()
    assert url is not None
    assert '://' in url
"""
    return {
        "id": f"synth-bug-config_key-{random.randint(10000,99999)}",
        "modality": "unified_diff",
        "source": "synthetic",
        "difficulty": "medium",
        "bug_type": "wrong_config_key",
        "instruction": f"Fix the KeyError when DATABASE_URL is not set in environment. Use a safe default.",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": "KeyError: 'DATABASE_URL'",
        "target_output": make_diff(f"src/{codebase['config_file']}", buggy, fixed),
        "repo_context": {"repo_name": "web-app", "language": codebase["lang"], "framework": codebase["fw"]},
        "retrieved_files": [{"file_path": f"src/{codebase['config_file']}", "role": "source", "content_preview": buggy[:120]}],
        "metadata": {"bug_type": "wrong_config_key", "severity": "medium"},
    }


def bug_broken_test_expectation() -> dict:
    func_bodies = [
        ("def multiply(a, b):\\n    return a * b", "assert multiply(3, 5) == 10", "assert multiply(3, 5) == 15"),
        ("def add(a, b):\\n    return a + b", "assert add(10, 5) == 20", "assert add(10, 5) == 15"),
        ("def divide(a, b):\\n    return a / b", "assert divide(10, 2) == 3", "assert divide(10, 2) == 5.0"),
    ]
    func, bad_assert, good_assert = random.choice(func_bodies)
    
    buggy_test = f"""from calculator import multiply

def test_multiply():
    {bad_assert}
"""
    fixed_test = f"""from calculator import multiply

def test_multiply():
    {good_assert}
"""
    return {
        "id": f"synth-bug-broken_test-{random.randint(10000,99999)}",
        "modality": "test_repair",
        "source": "synthetic",
        "difficulty": "easy",
        "bug_type": "broken_test_expectation",
        "instruction": "Fix the failing test assertion.",
        "buggy_code": buggy_test,
        "fixed_code": fixed_test,
        "test_code": buggy_test,
        "test_output": "AssertionError",
        "target_output": make_diff("tests/test_calculator.py", buggy_test, fixed_test),
        "repo_context": {"repo_name": "calc", "language": "Python", "framework": "", "test_framework": "pytest"},
        "retrieved_files": [{"file_path": "tests/test_calculator.py", "role": "test", "content_preview": buggy_test[:150]}],
        "metadata": {"bug_type": "broken_test_expectation", "severity": "low"},
    }


def bug_api_rename() -> dict:
    old_name = random.choice(["get_user", "fetch_data", "process_item", "validate_input"])
    new_name = random.choice(["get_user_v2", "fetch_data_v2", "process_item_v2", "validate_input_v2"])
    
    buggy = f"""from api import client

def handle():
    return client.{old_name}(id=1)
"""
    fixed = f"""from api import client

def handle():
    return client.{new_name}(id=1)
"""
    test = f"""def test_handle():
    result = handle()
    assert result is not None
"""
    return {
        "id": f"synth-bug-api_rename-{random.randint(10000,99999)}",
        "modality": "unified_diff",
        "source": "synthetic",
        "difficulty": "medium",
        "bug_type": "api_rename_mismatch",
        "instruction": f"Update the API call from {old_name} to {new_name} to match the new API.",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": f"AttributeError: module 'api' has no attribute '{old_name}'",
        "target_output": make_diff("src/client.py", buggy, fixed),
        "repo_context": {"repo_name": "api-client", "language": "Python", "framework": ""},
        "retrieved_files": [{"file_path": "src/client.py", "role": "source", "content_preview": buggy[:120]}],
        "metadata": {"bug_type": "api_rename_mismatch", "severity": "medium"},
    }


def bug_bad_path_handling() -> dict:
    buggy = """def save_file(filename, content):
    path = f"/data/{filename}"
    with open(path, 'w') as f:
        f.write(content)
    return path
"""
    fixed = """import os

def save_file(filename, content):
    path = os.path.join(os.getcwd(), "data", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    return path
"""
    test = """def test_save_file():
    path = save_file("test.txt", "hello")
    assert os.path.exists(path)
    os.remove(path)
"""
    return {
        "id": f"synth-bug-bad_path-{random.randint(10000,99999)}",
        "modality": "unified_diff",
        "source": "synthetic",
        "difficulty": "medium",
        "bug_type": "bad_path_handling",
        "instruction": "Fix the file path handling to be safe and cross-platform.",
        "buggy_code": buggy,
        "fixed_code": fixed,
        "test_code": test,
        "test_output": "FileNotFoundError: [Errno 2] No such file or directory: '/data/test.txt'",
        "target_output": make_diff("src/storage.py", buggy, fixed),
        "repo_context": {"repo_name": "file-util", "language": "Python", "framework": ""},
        "retrieved_files": [{"file_path": "src/storage.py", "role": "source", "content_preview": buggy[:140]}],
        "metadata": {"bug_type": "bad_path_handling", "severity": "high"},
    }


BUG_GENERATORS = {
    "wrong_import": bug_wrong_import,
    "off_by_one": bug_off_by_one,
    "missing_null_check": bug_null_check,
    "wrong_config_key": bug_config_key,
    "broken_test_expectation": bug_broken_test_expectation,
    "api_rename_mismatch": bug_api_rename,
    "bad_path_handling": bug_bad_path_handling,
}


def build_jsonl(examples: list[dict], path: Path):
    """Write examples to JSONL."""
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"  Wrote {len(examples)} examples -> {path}")


def main():
    print("=" * 72)
    print("  Week 43 — Synthetic Bug Factory")
    print("=" * 72)
    print()
    
    all_examples = []
    bug_counts = {}
    
    for bug_type, generator in sorted(BUG_GENERATORS.items()):
        print(f"  Generating {bug_type}...", end=" ", flush=True)
        examples = [generator() for _ in range(N_EXAMPLES_PER_BUG)]
        all_examples.extend(examples)
        bug_counts[bug_type] = len(examples)
        print(f"{len(examples)} examples")
    
    print()
    print(f"  Total: {len(all_examples)} synthetic bug examples")
    print()
    
    # Split
    random.shuffle(all_examples)
    n = len(all_examples)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    splits = {
        "train": all_examples[:train_end],
        "val": all_examples[train_end:val_end],
        "test": all_examples[val_end:],
    }
    
    # Save per-split
    for split_name, examples in splits.items():
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        
        by_bug = defaultdict(list)
        for ex in examples:
            by_bug[ex["bug_type"]].append(ex)
        
        for bug_type, bug_exs in by_bug.items():
            path = split_dir / f"{bug_type}.jsonl"
            build_jsonl(bug_exs, path)
        
        # Combined
        build_jsonl(examples, split_dir / "combined.jsonl")
    
    # Per-modality combined
    for split_name, examples in splits.items():
        by_mod = defaultdict(list)
        for ex in examples:
            by_mod[ex["modality"]].append(ex)
        for mod, mod_exs in by_mod.items():
            path = DATASET_DIR / split_name / f"modality_{mod}.jsonl"
            build_jsonl(mod_exs, path)
    
    # Report
    modality_counts = defaultdict(int)
    for ex in all_examples:
        modality_counts[ex["modality"]] += 1
    
    report = [
        "# Week 43 — Synthetic Bug Factory Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total examples: {len(all_examples)}",
        f"- Bug types: {len(BUG_GENERATORS)}",
        "",
        "## Per-Bug-Type Breakdown",
        "| Bug Type | Count | Sample Instruction |",
        "|----------|-------|-------------------|",
    ]
    for bt, count in sorted(bug_counts.items()):
        sample = BUG_GENERATORS[bt]()["instruction"][:60]
        report.append(f"| {bt} | {count} | {sample} |")
    report.append("")
    report.append("## Per-Modality Breakdown")
    report.append("| Modality | Count |")
    report.append("|----------|-------|")
    for mod, count in sorted(modality_counts.items()):
        report.append(f"| {mod} | {count} |")
    report.append("")
    report.append("## Splits")
    for s in ["train", "val", "test"]:
        report.append(f"- {s}: {len(splits[s])}")
    report.append("")
    report.append("## Sample Metadata Fields")
    report.append("- bug_type: identifies the synthetic bug category")
    report.append("- severity: low/medium/high")
    report.append("- buggy_code: the code with the injected bug")
    report.append("- fixed_code: the corrected code")
    report.append("- test_code: pytest-style test")
    report.append("- test_output: simulated failure output")
    report.append("- target_output: unified diff repair patch")
    
    report_path = REPORT_DIR / "SYNTHETIC_BUG_REPORT.md"
    report_path.write_text("\n".join(report))
    print(f"\n  Report: {report_path}")
    
    print()
    print("=" * 72)
    print(f"  Generated {len(all_examples)} synthetic bug examples across {len(BUG_GENERATORS)} bug types")
    print(f"  Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
