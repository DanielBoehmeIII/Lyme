#!/usr/bin/env python3
"""Week 51 — Critic Model v1.

Trains a critic that scores patches:
- patch applies
- likely fixes failure
- hallucinated paths
- risky files
- overbroad edit
- missing tests
- wrong target
"""

import json
import random
from pathlib import Path
from datetime import datetime, timezone

random.seed(51)
DATASET_DIR = Path("datasets/specialized/critic")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week51")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

CRITIQUE_SCENARIOS = [
    {
        "patch": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1 +1,4 @@\n+def average(nums):\n+    if not nums:\n+        return 0.0\n     return sum(nums) / len(nums)",
        "proposed_fix": "Fix ZeroDivisionError in average()",
        "score_valid": 5, "score_risk": 1, "score_overbroad": 1,
        "score_hallucinated": 0, "score_missing_tests": 1,
        "verdict": "approve", "reasoning": "Minimal fix, adds null check, no hallucinated paths.",
    },
    {
        "patch": "--- a/src/handler.py\n+++ b/src/handler.py\n@@ -1,10 +1,3 @@\n-import os\n-import sys\n-from utils.database import get_db\n-from utils.auth import login, logout, verify_token\n-from utils.cache import Cache\n-from utils.logging import logger\n-\n-def handle(request):\n-    ...entire 100 line handler deleted...\n+def handle(request):\n+    pass",
        "proposed_fix": "Fix the bug in the handler",
        "score_valid": 5, "score_risk": 5, "score_overbroad": 5,
        "score_hallucinated": 0, "score_missing_tests": 3,
        "verdict": "reject", "reasoning": "Overbroad edit — deleted entire handler instead of fixing specific bug.",
    },
    {
        "patch": "--- a/src/config.py\n+++ b/src/config.py\n@@ -3,3 +3,3 @@\n-    return os.environ['DATABASE_URL']\n+    return os.environ.get('DATABASE_URL', 'sqlite:///default.db')",
        "proposed_fix": "Fix KeyError when DATABASE_URL is missing",
        "score_valid": 5, "score_risk": 1, "score_overbroad": 1,
        "score_hallucinated": 0, "score_missing_tests": 2,
        "verdict": "approve", "reasoning": "Correct fix, minimal change, uses safe default.",
    },
    {
        "patch": "--- a/src/nonexistent.py\n+++ b/src/nonexistent.py\n@@ -1 +1 @@\n-print('hello')\n+print('world')",
        "proposed_fix": "Fix greeting message",
        "score_valid": 3, "score_risk": 3, "score_overbroad": 1,
        "score_hallucinated": 5, "score_missing_tests": 2,
        "verdict": "reject", "reasoning": "Hallucinated path — src/nonexistent.py does not exist in the repository.",
    },
    {
        "patch": "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -2,2 +2,2 @@\n def test_multiply():\n-    assert multiply(3, 5) == 10\n+    assert multiply(3, 5) == 15",
        "proposed_fix": "Fix wrong test assertion",
        "score_valid": 5, "score_risk": 1, "score_overbroad": 1,
        "score_hallucinated": 0, "score_missing_tests": 0,
        "verdict": "approve", "reasoning": "Minimal test fix, correct expected value.",
    },
    {
        "patch": "--- a/src/db.py\n+++ b/src/db.py\n@@ -3,3 +3,3 @@\n-    query = f\"SELECT * FROM users WHERE name = '{username}'\"\n+    query = 'SELECT * FROM users WHERE name = ?'\n-    return db.execute(query)\n+    return db.execute(query, (username,))",
        "proposed_fix": "Fix SQL injection vulnerability",
        "score_valid": 5, "score_risk": 1, "score_overbroad": 1,
        "score_hallucinated": 0, "score_missing_tests": 2,
        "verdict": "approve", "reasoning": "Correct fix, parameterized query. Should add test for SQL injection attempt.",
    },
    {
        "patch": "--- a/src/app.py\n+++ b/src/app.py\n@@ -1,50 +1,3 @@\n-...entire app.py deleted and rewritten...\n+print('hello world')",
        "proposed_fix": "Rewrite the application",
        "score_valid": 2, "score_risk": 5, "score_overbroad": 5,
        "score_hallucinated": 0, "score_missing_tests": 5,
        "verdict": "reject", "reasoning": "Destructive rewrite. Deletes 50 lines, replaces with 1-line script. No tests. Extreme risk.",
    },
]

def main():
    print("=" * 72)
    print("  Week 51 — Critic Model v1 Dataset")
    print("=" * 72)

    examples = []
    for scenario in CRITIQUE_SCENARIOS:
        for _ in range(50):
            target = json.dumps({
                "verdict": scenario["verdict"],
                "scores": {
                    "patch_applies": scenario["score_valid"],
                    "risk_level": scenario["score_risk"],
                    "overbroad_edit": scenario["score_overbroad"],
                    "hallucinated_paths": scenario["score_hallucinated"],
                    "missing_tests": scenario["score_missing_tests"],
                },
                "reasoning": scenario["reasoning"],
            })
            examples.append({
                "id": f"critic-{random.randint(10000,99999)}",
                "modality": "verification",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "medium",
                "instruction": f"Review this patch: {scenario['proposed_fix']}\n\n```diff\n{scenario['patch']}\n```\n\nScore the patch on validity, risk, overbreadth, hallucinated paths, and missing tests. Output verdict (approve/revise/reject) with reasoning.",
                "repo_context": {"repo_name": "critic-project", "language": "Python"},
                "retrieved_files": [{"file_path": "src/main.py", "role": "source", "content_preview": scenario["patch"][:200]}],
                "target_output": target,
                "metadata": {"task_type": "verification", "verdict": scenario["verdict"], "critic_training": True},
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

    print(f"  Generated {len(examples)} critic examples")
    print(f"  Verdicts: approve={sum(1 for e in examples if e['metadata']['verdict']=='approve')}, reject={sum(1 for e in examples if e['metadata']['verdict']=='reject')}")
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print(f"  Output: {DATASET_DIR}/")

    import yaml
    config = {
        "model": {"name": "Qwen/Qwen2.5-Coder-0.5B-Instruct", "dtype": "bfloat16", "device_map": "auto"},
        "quantization": {"enabled": True, "load_in_4bit": True, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_use_double_quant": True, "bnb_4bit_quant_type": "nf4"},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "training": {"output_dir": "checkpoints/critic_v1", "num_train_epochs": 3, "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, "learning_rate": 2e-4, "max_seq_length": 1024, "logging_steps": 10, "save_steps": 100, "eval_steps": 100, "save_total_limit": 3, "bf16": True, "optim": "paged_adamw_8bit"},
        "data": {"train_file": "datasets/specialized/critic/train/combined.jsonl", "val_file": "datasets/specialized/critic/val/combined.jsonl", "test_file": "datasets/specialized/critic/test/combined.jsonl", "instruction_template": "### Instruction:\n{instruction}\n\n### Patch:\n{context}\n\n### Critique:\n"},
    }
    with open(DATASET_DIR / "training_config.yaml", "w") as f:
        yaml.dump(config, f)
    print("=" * 72)

if __name__ == "__main__":
    main()
