#!/usr/bin/env python3
"""Week 48 — Diff-Only Discipline.

Trains strict unified diff generation. Builds:
- malformed diff rejection dataset
- clean diff preference pairs
"""

import json
import random
from pathlib import Path
from datetime import datetime, timezone

random.seed(48)
DATASET_DIR = Path("datasets/specialized/diff_discipline")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week48")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def make_clean_diff(file_path, before, after):
    bl = before.split("\n"); al = after.split("\n")
    pe = 0
    while pe < len(bl) and pe < len(al) and bl[pe] == al[pe]: pe += 1
    sb, sa = len(bl)-1, len(al)-1
    while sb >= pe and sa >= pe and bl[sb] == al[sa]: sb -= 1; sa -= 1
    removed = bl[pe:sb+1]; added = al[pe:sa+1]
    cb = bl[max(0,pe-2):pe]; ca = al[sa+1:min(len(al),sa+3)]
    hs = max(1,pe-2)
    hlb = len(cb)+len(removed)+len(ca); hla = len(cb)+len(added)+len(ca)
    diff = f"--- a/{file_path}\n+++ b/{file_path}\n@@ -{hs},{hlb} +{hs},{hla} @@\n"
    for l in cb: diff += f" {l}\n"
    for l in removed: diff += f"-{l}\n"
    for l in added: diff += f"+{l}\n"
    for l in ca: diff += f" {l}\n"
    return diff

DIFF_TASKS = [
    {"file": "src/calculator.py", "before": "def average(nums):\n    return sum(nums) / len(nums)", "after": "def average(nums):\n    if not nums:\n        return 0.0\n    return sum(nums) / len(nums)", "desc": "Add null check to average()"},
    {"file": "src/utils.py", "before": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items)]", "after": "def get_last(items):\n    if not items:\n        return None\n    return items[len(items) - 1]", "desc": "Fix off-by-one in get_last()"},
    {"file": "src/storage.py", "before": "def save_file(filename, content):\n    path = '/data/' + filename\n    with open(path, 'w') as f:\n        f.write(content)", "after": "import os\ndef save_file(filename, content):\n    path = os.path.join('/data', filename)\n    os.makedirs(os.path.dirname(path), exist_ok=True)\n    with open(path, 'w') as f:\n        f.write(content)", "desc": "Fix unsafe path handling"},
    {"file": "tests/test_calc.py", "before": "from calculator import multiply\ndef test_multiply():\n    assert multiply(3, 5) == 10", "after": "from calculator import multiply\ndef test_multiply():\n    assert multiply(3, 5) == 15", "desc": "Fix wrong test assertion"},
    {"file": "src/config.py", "before": "import os\ndef get_db_url():\n    return os.environ['DATABASE_URL']", "after": "import os\ndef get_db_url():\n    return os.environ.get('DATABASE_URL', 'sqlite:///default.db')", "desc": "Fix KeyError with safe default"},
    {"file": "src/db.py", "before": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n    return db.execute(query)", "after": "def get_user(username):\n    query = 'SELECT * FROM users WHERE name = ?'\n    return db.execute(query, (username,))", "desc": "Fix SQL injection"},
]

MALFORMED_DIFFS = [
    "Here's the fix: just add a null check. Hope this helps!",
    "The bug is at line 2. You should add a null check.\n\ndef average(nums):\n    if not nums:\n        return 0\n    return sum(nums) / len(nums)",
    "--- a/file.py\n+++ b/file.py\n@@ wrong header @@\n-foo\n+bar",
    "Patch:\n```diff\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-foo\n+bar\n```\nAlso you need to update the tests.",
    "I found the issue. The problem is...",
    "--- src/file.py\n+++ src/file.py\n(diff content)",
    "Just change line 5 to return items[len(items)-1].",
]

def main():
    print("=" * 72)
    print("  Week 48 — Diff-Only Discipline Dataset")
    print("=" * 72)

    examples = []
    for task in DIFF_TASKS:
        clean_diff = make_clean_diff(task["file"], task["before"], task["after"])

        # Clean diff example (positive)
        for _ in range(30):
            examples.append({
                "id": f"diff-clean-{task['file'].replace('/','-')}-{random.randint(100,999)}",
                "modality": "unified_diff",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "medium",
                "instruction": f"Generate a unified diff to fix: {task['desc']}",
                "repo_context": {"repo_name": "diff-project", "language": "Python"},
                "retrieved_files": [{"file_path": task["file"], "role": "source", "content_preview": task["before"][:200]}],
                "target_output": clean_diff,
                "metadata": {"diff_discipline": "clean", "file": task["file"]},
            })

        # Rejection examples (negative — malformed output)
        for _ in range(15):
            malformed = random.choice(MALFORMED_DIFFS)
            examples.append({
                "id": f"diff-bad-{task['file'].replace('/','-')}-{random.randint(100,999)}",
                "modality": "unified_diff",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "medium",
                "instruction": f"Generate a unified diff to fix: {task['desc']}",
                "repo_context": {"repo_name": "diff-project", "language": "Python"},
                "retrieved_files": [{"file_path": task["file"], "role": "source", "content_preview": task["before"][:200]}],
                "target_output": malformed,
                "metadata": {"diff_discipline": "malformed", "rejection": True},
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

    cleans = sum(1 for e in train if e["metadata"].get("diff_discipline") == "clean")
    malds = sum(1 for e in train if e["metadata"].get("diff_discipline") == "malformed")
    print(f"  Generated {len(examples)} examples")
    print(f"  Clean diffs: {cleans}, Malformed rejection: {malds}")
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print(f"  Output: {DATASET_DIR}/")

    config = {
        "model": {"name": "Qwen/Qwen2.5-Coder-0.5B-Instruct", "dtype": "bfloat16", "device_map": "auto"},
        "quantization": {"enabled": True, "load_in_4bit": True, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_use_double_quant": True, "bnb_4bit_quant_type": "nf4"},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "training": {"output_dir": "checkpoints/diff_v1", "num_train_epochs": 3, "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, "learning_rate": 2e-4, "max_seq_length": 1024, "logging_steps": 10, "save_steps": 100, "eval_steps": 100, "save_total_limit": 3, "bf16": True, "optim": "paged_adamw_8bit"},
        "data": {"train_file": "datasets/specialized/diff_discipline/train/combined.jsonl", "val_file": "datasets/specialized/diff_discipline/val/combined.jsonl", "test_file": "datasets/specialized/diff_discipline/test/combined.jsonl", "instruction_template": "### Instruction:\n{instruction}\n\n### Context:\n{context}\n\n### Response:\n"},
    }
    import yaml
    with open(DATASET_DIR / "training_config.yaml", "w") as f:
        yaml.dump(config, f)
    print("=" * 72)

if __name__ == "__main__":
    main()
