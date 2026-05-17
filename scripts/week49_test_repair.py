#!/usr/bin/env python3
"""Week 49 — Test Repair Specialization.

Input: failing test output + relevant files.
Output: minimal patch to fix the test.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timezone

random.seed(49)
DATASET_DIR = Path("datasets/specialized/test_repair")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week49")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BUGGY_TESTS = [
    {
        "test_file": "tests/test_calc.py",
        "source_file": "src/calculator.py",
        "source_content": "def multiply(a, b): return a * b",
        "test_content": "def test_multiply():\n    assert multiply(3, 5) == 10",
        "failure": "FAIL: test_multiply — AssertionError: assert 15 == 10",
        "fix_content": "def test_multiply():\n    assert multiply(3, 5) == 15",
        "fix_diff": "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -1,2 +1,2 @@\n def test_multiply():\n-    assert multiply(3, 5) == 10\n+    assert multiply(3, 5) == 15",
    },
    {
        "test_file": "tests/test_greet.py",
        "source_file": "src/greeter.py",
        "source_content": "def greet(name): return f'hello {name}'",
        "test_content": "def test_greet():\n    assert greet('world') == 'hello'",
        "failure": "FAIL: test_greet — AssertionError: assert 'hello world' == 'hello'",
        "fix_content": "def test_greet():\n    assert greet('world') == 'hello world'",
        "fix_diff": "--- a/tests/test_greet.py\n+++ b/tests/test_greet.py\n@@ -1,2 +1,2 @@\n def test_greet():\n-    assert greet('world') == 'hello'\n+    assert greet('world') == 'hello world'",
    },
    {
        "test_file": "tests/test_add.py",
        "source_file": "src/math_ops.py",
        "source_content": "def add(a, b): return a + b",
        "test_content": "def test_add():\n    assert add(10, 5) == 20",
        "failure": "FAIL: test_add — AssertionError: assert 15 == 20",
        "fix_content": "def test_add():\n    assert add(10, 5) == 15",
        "fix_diff": "--- a/tests/test_add.py\n+++ b/tests/test_add.py\n@@ -1,2 +1,2 @@\n def test_add():\n-    assert add(10, 5) == 20\n+    assert add(10, 5) == 15",
    },
    {
        "test_file": "tests/test_concat.py",
        "source_file": "src/strings.py",
        "source_content": "def concat(a, b): return a + b",
        "test_content": "def test_concat():\n    assert concat('a', 'b') == 'ab '",
        "failure": "FAIL: test_concat — AssertionError: assert 'ab' == 'ab '",
        "fix_content": "def test_concat():\n    assert concat('a', 'b') == 'ab'",
        "fix_diff": "--- a/tests/test_concat.py\n+++ b/tests/test_concat.py\n@@ -1,2 +1,2 @@\n def test_concat():\n-    assert concat('a', 'b') == 'ab '\n+    assert concat('a', 'b') == 'ab'",
    },
    {
        "test_file": "tests/test_divide.py",
        "source_file": "src/math_ops.py",
        "source_content": "def divide(a, b):\n    if b == 0: raise ValueError('div by zero')\n    return a / b",
        "test_content": "def test_divide():\n    assert divide(10, 2) == 3",
        "failure": "FAIL: test_divide — AssertionError: assert 5.0 == 3",
        "fix_content": "def test_divide():\n    assert divide(10, 2) == 5.0",
        "fix_diff": "--- a/tests/test_divide.py\n+++ b/tests/test_divide.py\n@@ -1,2 +1,2 @@\n def test_divide():\n-    assert divide(10, 2) == 3\n+    assert divide(10, 2) == 5.0",
    },
    {
        "test_file": "tests/test_list.py",
        "source_file": "src/utils.py",
        "source_content": "def get_first(items): return items[0] if items else None",
        "test_content": "def test_get_first():\n    assert get_first([]) == 'error'",
        "failure": "FAIL: test_get_first — AssertionError: assert None == 'error'",
        "fix_content": "def test_get_first():\n    assert get_first([]) is None",
        "fix_diff": "--- a/tests/test_list.py\n+++ b/tests/test_list.py\n@@ -1,2 +1,2 @@\n def test_get_first():\n-    assert get_first([]) == 'error'\n+    assert get_first([]) is None",
    },
]

def main():
    print("=" * 72)
    print("  Week 49 — Test Repair Specialization Dataset")
    print("=" * 72)

    examples = []
    for task in BUGGY_TESTS:
        for _ in range(50):
            examples.append({
                "id": f"test-repair-{task['test_file'].replace('/','-')}-{random.randint(100,999)}",
                "modality": "test_repair",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "easy",
                "instruction": f"Fix the failing test. Test output: {task['failure']}",
                "repo_context": {"repo_name": "test-repair-proj", "language": "Python", "test_framework": "pytest"},
                "retrieved_files": [
                    {"file_path": task["test_file"], "role": "test", "content_preview": task["test_content"][:200]},
                    {"file_path": task["source_file"], "role": "source", "content_preview": task["source_content"][:200]},
                ],
                "target_output": task["fix_diff"],
                "metadata": {"test_framework": "pytest", "failure_type": "wrong_assertion", "fixed": True},
            })

    random.shuffle(examples)
    n = len(examples)
    train = examples[:int(n*0.7)]
    val = examples[int(n*0.7):int(n*0.85)]
    test = examples[int(n*0.85):]

    for split_name, split_exs in [("train", train), ("val", val), ("test", test)]:
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        with open(split_dir / "combined.jsonl", "w") as f:
            for ex in split_exs:
                f.write(json.dumps(ex) + "\n")

    print(f"  Generated {len(examples)} test repair examples")
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print(f"  Output: {DATASET_DIR}/")

    import yaml
    config = {
        "model": {"name": "Qwen/Qwen2.5-Coder-0.5B-Instruct", "dtype": "bfloat16", "device_map": "auto"},
        "quantization": {"enabled": True, "load_in_4bit": True, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_use_double_quant": True, "bnb_4bit_quant_type": "nf4"},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "training": {"output_dir": "checkpoints/test_repair_v1", "num_train_epochs": 3, "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, "learning_rate": 2e-4, "max_seq_length": 1024, "logging_steps": 10, "save_steps": 100, "eval_steps": 100, "save_total_limit": 3, "bf16": True, "optim": "paged_adamw_8bit"},
        "data": {"train_file": "datasets/specialized/test_repair/train/combined.jsonl", "val_file": "datasets/specialized/test_repair/val/combined.jsonl", "test_file": "datasets/specialized/test_repair/test/combined.jsonl", "instruction_template": "### Instruction:\n{instruction}\n\n### Failing test:\n{context}\n\n### Fix:\n"},
    }
    with open(DATASET_DIR / "training_config.yaml", "w") as f:
        yaml.dump(config, f)
    print("=" * 72)

if __name__ == "__main__":
    main()
