#!/usr/bin/env python3
"""Week 50 — Multi-File Edit Specialization."""

import json
import random
from pathlib import Path
from datetime import datetime, timezone

random.seed(50)
DATASET_DIR = Path("datasets/specialized/multi_file_edit")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week50")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    {
        "name": "rename_user_to_account",
        "instruction": "Rename the User model to Account across all files: models.py, views.py, serializers.py, tests.",
        "files": {
            "src/models.py": "from django.db import models\n\nclass User(models.Model):\n    name = models.CharField(max_length=100)\n    email = models.EmailField()",
            "src/views.py": "from .models import User\n\ndef user_list(request):\n    users = User.objects.all()\n    return render(request, 'list.html', {'users': users})",
            "src/serializers.py": "from .models import User\n\nclass UserSerializer:\n    class Meta:\n        model = User",
            "tests/test_models.py": "from src.models import User\n\ndef test_user_create():\n    user = User.objects.create(name='test', email='test@test.com')\n    assert user.name == 'test'",
        },
        "plan": "1. Rename class User to Account in models.py\n2. Update imports in views.py, serializers.py\n3. Update model reference in serializers.py Meta\n4. Update imports and references in tests",
        "output": {
            "src/models.py": "from django.db import models\n\nclass Account(models.Model):\n    name = models.CharField(max_length=100)\n    email = models.EmailField()",
            "src/views.py": "from .models import Account\n\ndef account_list(request):\n    accounts = Account.objects.all()\n    return render(request, 'list.html', {'accounts': accounts})",
            "src/serializers.py": "from .models import Account\n\nclass AccountSerializer:\n    class Meta:\n        model = Account",
            "tests/test_models.py": "from src.models import Account\n\ndef test_account_create():\n    account = Account.objects.create(name='test', email='test@test.com')\n    assert account.name == 'test'",
        },
    },
    {
        "name": "add_verbose_flag",
        "instruction": "Add a --verbose CLI option that propagates through cli.py, handler.py, and service.py.",
        "files": {
            "src/cli.py": "import click\n\n@click.command()\ndef main():\n    process()",
            "src/handler.py": "def process():\n    run_service()",
            "src/service.py": "def run_service():\n    print('doing work')",
        },
        "plan": "1. Add @click.option('--verbose') to CLI\n2. Pass verbose param to process()\n3. Pass verbose to run_service()\n4. Use verbose flag for conditional logging",
        "output": {
            "src/cli.py": "import click\n\n@click.command()\n@click.option('--verbose', is_flag=True, help='Enable verbose output')\ndef main(verbose):\n    process(verbose)",
            "src/handler.py": "def process(verbose=False):\n    run_service(verbose)",
            "src/service.py": "def run_service(verbose=False):\n    if verbose:\n        print('Starting work...')\n    print('doing work')",
        },
    },
    {
        "name": "update_import_path",
        "instruction": "Update import paths after moving utils/db.py to database/connection.py.",
        "files": {
            "src/api.py": "from utils.db import get_session\n\ndef handle():\n    session = get_session()",
            "src/handlers.py": "from utils.db import get_session\n\nclass DataHandler:\n    def __init__(self):\n        self.session = get_session()",
            "src/config.py": "from utils.db import get_session\n\nsession = get_session()",
        },
        "plan": "1. Update all imports from utils.db to database.connection\n2. Verify all three files updated consistently",
        "output": {
            "src/api.py": "from database.connection import get_session\n\ndef handle():\n    session = get_session()",
            "src/handlers.py": "from database.connection import get_session\n\nclass DataHandler:\n    def __init__(self):\n        self.session = get_session()",
            "src/config.py": "from database.connection import get_session\n\nsession = get_session()",
        },
    },
]

def main():
    print("=" * 72)
    print("  Week 50 — Multi-File Edit Specialization Dataset")
    print("=" * 72)

    examples = []
    for task in TASKS:
        for _ in range(60):
            files_list = [{"file_path": fp, "role": "source", "content_preview": fc[:200], "lines": len(fc.split("\n")), "relevance_score": 1.0} for fp, fc in task["files"].items()]
            target = "\n".join(f"{fp}:\n{fc}" for fp, fc in task["output"].items())
            examples.append({
                "id": f"multi-{task['name']}-{random.randint(100,999)}",
                "modality": "multi_file_edit",
                "created": datetime.now(timezone.utc).isoformat(),
                "source": "synthetic",
                "difficulty": "hard",
                "instruction": task["instruction"],
                "repo_context": {"repo_name": "multi-file-project", "language": "Python", "file_count": len(task["files"])},
                "retrieved_files": files_list,
                "target_output": target,
                "metadata": {"files_changed": len(task["files"]), "task_type": "multi_file_edit", "plan": task["plan"]},
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

    print(f"  Generated {len(examples)} multi-file edit examples")
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print(f"  Output: {DATASET_DIR}/")

    import yaml
    config = {
        "model": {"name": "Qwen/Qwen2.5-Coder-0.5B-Instruct", "dtype": "bfloat16", "device_map": "auto"},
        "quantization": {"enabled": True, "load_in_4bit": True, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_use_double_quant": True, "bnb_4bit_quant_type": "nf4"},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "training": {"output_dir": "checkpoints/multifile_v1", "num_train_epochs": 3, "per_device_train_batch_size": 1, "per_device_eval_batch_size": 1, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, "learning_rate": 2e-4, "max_seq_length": 1024, "logging_steps": 10, "save_steps": 100, "eval_steps": 100, "save_total_limit": 3, "bf16": True, "optim": "paged_adamw_8bit"},
        "data": {"train_file": "datasets/specialized/multi_file_edit/train/combined.jsonl", "val_file": "datasets/specialized/multi_file_edit/val/combined.jsonl", "test_file": "datasets/specialized/multi_file_edit/test/combined.jsonl", "instruction_template": "### Instruction:\n{instruction}\n\n### Files:\n{context}\n\n### Edits:\n"},
    }
    with open(DATASET_DIR / "training_config.yaml", "w") as f:
        yaml.dump(config, f)
    print("=" * 72)

if __name__ == "__main__":
    main()
