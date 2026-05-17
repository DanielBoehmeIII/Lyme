#!/usr/bin/env python3
"""Week 47 — Tool-Use Specialization.

Trains model to output structured actions: SEARCH, READ, RUN_TESTS, PATCH, VERIFY, STOP.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

random.seed(47)
DATASET_DIR = Path("datasets/specialized/tool_use")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week47")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TOOL_ACTIONS = ["SEARCH", "READ", "RUN_TESTS", "PATCH", "VERIFY", "STOP", "LIST_DIR", "GREP"]

SCENARIOS = [
    {
        "task": "Find where SECRET_KEY is defined and change it to use env var with fallback.",
        "context": "config/settings.py contains SECRET_KEY = 'dev-key-123'",
        "trace": [
            ("SEARCH", '{"pattern": "SECRET_KEY", "path": "config/"}', 'Found in config/settings.py:12'),
            ("READ", '{"path": "config/settings.py"}', 'SECRET_KEY = \'dev-key-123\'\nDEBUG = True\nALLOWED_HOSTS = [\'*\']'),
            ("PATCH", '{"file": "config/settings.py", "old": "SECRET_KEY = \'dev-key-123\'", "new": "SECRET_KEY = os.environ.get(\'SECRET_KEY\', \'fallback\')"}', 'File patched successfully'),
            ("VERIFY", '{"check": "import works"}', 'Verification passed'),
            ("STOP", '{"reason": "tests_passed"}', ''),
        ]
    },
    {
        "task": "Fix the ZeroDivisionError when average() receives an empty list.",
        "context": "src/calculator.py: def average(nums): return sum(nums) / len(nums)",
        "trace": [
            ("READ", '{"path": "src/calculator.py"}', 'def average(nums):\n    return sum(nums) / len(nums)'),
            ("READ", '{"path": "tests/test_calculator.py"}', 'def test_average_empty():\n    assert average([]) == 0.0'),
            ("PATCH", '{"file": "src/calculator.py", "old": "def average(nums):\\n    return sum(nums) / len(nums)", "new": "def average(nums):\\n    if not nums:\\n        return 0.0\\n    return sum(nums) / len(nums)"}', 'File patched successfully'),
            ("RUN_TESTS", '{"command": "pytest tests/test_calculator.py -v"}', 'PASSED: 2 passed'),
            ("STOP", '{"reason": "tests_passed"}', ''),
        ]
    },
    {
        "task": "Find the bug causing IndexError in get_last() and fix it.",
        "context": "src/utils.py: def get_last(items): if not items: return None; return items[len(items)]",
        "trace": [
            ("SEARCH", '{"pattern": "def get_last", "path": "src/"}', 'Found in src/utils.py:1'),
            ("READ", '{"path": "src/utils.py"}', 'def get_last(items):\n    if not items:\n        return None\n    return items[len(items)]'),
            ("PATCH", '{"file": "src/utils.py", "old": "return items[len(items)]", "new": "return items[len(items) - 1]"}', 'File patched successfully'),
            ("RUN_TESTS", '{"command": "pytest"}', 'PASSED: all tests pass'),
            ("STOP", '{"reason": "tests_passed"}', ''),
        ]
    },
    {
        "task": "Update API call from get_user to get_user_v2.",
        "context": "src/client.py: from api import client; def fetch(): return client.get_user(id=1)",
        "trace": [
            ("SEARCH", '{"pattern": "get_user", "path": "src/"}', 'Found in src/client.py:3, src/api.py:15'),
            ("READ", '{"path": "src/client.py"}', 'from api import client\n\ndef fetch():\n    return client.get_user(id=1)'),
            ("PATCH", '{"file": "src/client.py", "old": "client.get_user", "new": "client.get_user_v2"}', 'File patched successfully'),
            ("RUN_TESTS", '{"command": "pytest tests/"}', 'PASSED: 3 passed'),
            ("STOP", '{"reason": "tests_passed"}', ''),
        ]
    },
    {
        "task": "Navigate the codebase to understand the project architecture.",
        "context": "Project has src/, tests/, config/ directories.",
        "trace": [
            ("LIST_DIR", '{"path": "."}', 'src/, tests/, config/, pyproject.toml, README.md'),
            ("READ", '{"path": "pyproject.toml"}', '[project]\nname = "my-app"\ndependencies = ["fastapi", "sqlalchemy"]'),
            ("LIST_DIR", '{"path": "src/"}', 'api/, models/, services/, db/, main.py'),
            ("READ", '{"path": "src/main.py"}', 'from fastapi import FastAPI\napp = FastAPI()'),
            ("STOP", '{"reason": "sufficient_evidence"}', ''),
        ]
    },
    {
        "task": "Fix the SQL injection in get_user().",
        "context": "src/db.py: def get_user(username): query = f\"SELECT * FROM users WHERE name = '{username}'\"; return db.execute(query)",
        "trace": [
            ("SEARCH", '{"pattern": "execute", "path": "src/db.py"}', 'Found at line 5'),
            ("READ", '{"path": "src/db.py"}', 'def get_user(username):\n    query = f"SELECT * FROM users WHERE name = \'{username}\' "\n    return db.execute(query)'),
            ("PATCH", '{"file": "src/db.py", "old": "query = f\\"SELECT * FROM users WHERE name = \'{\'+username+\'}\'\\"\\n    return db.execute(query)", "new": "query = \\"SELECT * FROM users WHERE name = ?\\"\\n    return db.execute(query, (username,))"}', 'File patched'),
            ("RUN_TESTS", '{"command": "pytest tests/test_db.py -v"}', 'PASSED: 2 passed'),
            ("VERIFY", '{"check": "sql_injection_attempt"}', 'SQL injection blocked correctly'),
            ("STOP", '{"reason": "tests_passed"}', ''),
        ]
    },
]

def generate_tool_use_examples():
    examples = []
    for task_idx, scenario in enumerate(SCENARIOS):
        for _ in range(40):
            trace = scenario["trace"]
            tool_seq = []
            for action, args, result in trace:
                tool_seq.append({
                    "tool_name": action,
                    "arguments": json.loads(args) if args else {},
                    "result_summary": result[:200],
                    "success": "FAIL" not in result,
                    "latency_ms": random.randint(100, 5000),
                })

            target = "\n".join(f"{action}({args}) → {result[:50]}..." for action, args, result in trace)

            examples.append({
                "id": f"tool-use-week47-{task_idx}-{random.randint(1000,9999)}",
                "modality": "tool_use",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "medium",
                "instruction": scenario["task"],
                "repo_context": {"repo_name": "tool-use-project", "language": "Python", "file_count": 10},
                "retrieved_files": [{"file_path": "src/main.py", "role": "source", "content_preview": scenario["context"][:200]}],
                "tool_outputs": tool_seq,
                "target_output": target,
                "metadata": {"task_type": "tool_use", "num_tool_calls": len(trace), "tools_used": [t[0] for t in trace]},
            })
    return examples

def main():
    print("=" * 72)
    print("  Week 47 — Tool-Use Specialization Dataset")
    print("=" * 72)
    examples = generate_tool_use_examples()
    print(f"  Generated {len(examples)} tool-use examples")

    # Split
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

    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print(f"  Output: {DATASET_DIR}/")

    # Config
    config = {
        "model": {"name": "Qwen/Qwen2.5-Coder-0.5B-Instruct", "dtype": "bfloat16", "device_map": "auto"},
        "quantization": {"enabled": True, "load_in_4bit": True, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_use_double_quant": True, "bnb_4bit_quant_type": "nf4"},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "training": {"output_dir": "checkpoints/tool_use_v1", "num_train_epochs": 3, "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, "learning_rate": 2e-4, "max_seq_length": 1024, "logging_steps": 10, "save_steps": 100, "eval_steps": 100, "save_total_limit": 3, "bf16": True, "optim": "paged_adamw_8bit"},
        "data": {"train_file": "datasets/specialized/tool_use/train/combined.jsonl", "val_file": "datasets/specialized/tool_use/val/combined.jsonl", "test_file": "datasets/specialized/tool_use/test/combined.jsonl", "instruction_template": "### Instruction:\n{instruction}\n\n### Context:\n{context}\n\n### Response:\n"},
    }
    with open(DATASET_DIR / "training_config.yaml", "w") as f:
        import yaml
        yaml.dump(config, f)
    print(f"  Training config: {DATASET_DIR}/training_config.yaml")
    print("=" * 72)

if __name__ == "__main__":
    main()
