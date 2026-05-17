#!/usr/bin/env python3
"""Week 52 — Lyme Model v1.1 Release Packaging.

Packages:
- SFT v1 adapter
- tool-use specialization data & config
- diff discipline data & config
- test repair data & config
- multi-file edit data & config
- critic v1 data & config
- eval report
- model card
- failure report
- hardware notes
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone

RELEASE_DIR = Path("releases/v1.1")
RELEASE_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINTS = Path("checkpoints")
ADAPTERS = Path("adapters")
REPORT_DIR = Path("lyme-output/week52")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

RELEASE_ASSETS = {
    "checkpoints/sft_v1_week46": "model/sft_v1/",
    "datasets/v1": "data/dataset_v1/",
    "datasets/specialized": "data/specialized/",
    "datasets/generated": "data/generated/",
}

def copy_asset(src, dst):
    src_p = Path(src)
    dst_p = RELEASE_DIR / dst
    if src_p.exists():
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if src_p.is_dir():
            shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
        else:
            shutil.copy2(src_p, dst_p)
        return True
    return False

def compute_stats():
    import subprocess
    result = subprocess.run(["find", "datasets/", "-name", "*.jsonl", "-exec", "wc", "-l", "{}", "+"],
                          capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    total = 0
    for line in lines:
        try:
            total += int(line.split()[0])
        except:
            pass
    return {"total_jsonl_lines": total}

def build_model_card(sft_completed, metrics):
    return f"""# Lyme Model v1.1 — Model Card

> Generated: {datetime.now(timezone.utc).isoformat()}

## Model Overview
- **Base Model**: Qwen/Qwen2.5-Coder-0.5B-Instruct
- **Fine-tuning Method**: QLoRA (4-bit NF4, LoRA r=16, alpha=32)
- **Training Data**: Lyme Dataset v1 (16,328 examples across 10 modalities)
- **Specializations**: tool-use, diff-only, test repair, multi-file edit, critic

## Training Summary
| Component | Status | Epochs | Train Examples |
|-----------|--------|--------|----------------|
| SFT v1 | {'✅ Complete' if sft_completed else '🔄 In progress'} | 2 | 10,610 |
| Tool-Use | ✅ Dataset ready | - | 168 |
| Diff Discipline | ✅ Dataset ready | - | 189 |
| Test Repair | ✅ Dataset ready | - | 210 |
| Multi-File Edit | ✅ Dataset ready | - | 125 |
| Critic v1 | ✅ Dataset ready | - | 244 |

## Performance Metrics
| Metric | Base Model | SFT v1 |
|--------|-----------|--------|
| Valid diff rate | {metrics.get('base_valid_diff', 'TBD')}% | {metrics.get('sft_valid_diff', 'TBD')}% |
| Test repair success | {metrics.get('base_test_repair', 'TBD')}% | {metrics.get('sft_test_repair', 'TBD')}% |
| Evidence use | {metrics.get('base_evidence', 'TBD')}% | {metrics.get('sft_evidence', 'TBD')}% |

## Hardware Requirements
- **Training**: 8GB VRAM GPU (RTX 4060 laptop) with QLoRA
- **Inference**: 4GB VRAM or CPU with 16GB RAM
- **Quantization**: 4-bit NF4 (2.5GB model size)

## Included Components
1. SFT v1 LoRA adapter
2. Dataset v1 (16,328 examples)
3. Specialized datasets (tool-use, diff, test repair, multi-file, critic)
4. Training configurations for each specialization
5. Evaluation suite

## Known Limitations
- 0.5B parameter model — limited reasoning capacity vs 7B+ models
- Training on single GPU with small batch size
- Datasets are synthetic/mined — limited real-world diversity
- No RLHF/DPO training yet
"""

def build_failure_report():
    return """# Lyme Model v1.1 — Failure Analysis Report

## Known Failure Modes

1. **Long-context tasks** (>1024 tokens): Model truncates context, loses information
2. **Multi-file consistency**: 0.5B model struggles to maintain consistency across 3+ files
3. **Complex SQL/general logic**: Small model limited reasoning depth
4. **Hallucinated file paths**: Model occasionally references files not in context
5. **Verbose output**: SFT model sometimes adds extra commentary instead of pure diff
6. **Diff formatting**: Minor formatting inconsistencies in edge cases

## Mitigation Strategies
- Use critic model to reject hallucinated patches
- Enforce action grammar (Week 53+) for structured output
- Distill from larger teacher models (Phase 10)
- Increase to 7B base model when hardware permits
"""

def build_hardware_notes():
    return """# Lyme Model v1.1 — Hardware Notes

## Training Hardware
- **GPU**: NVIDIA GeForce RTX 4060 Laptop (8.3GB VRAM)
- **CPU**: 12th Gen Intel Core i7
- **RAM**: 32GB
- **Storage**: SSD

## Training Configuration
- **Base Model**: Qwen2.5-Coder-0.5B-Instruct (495M params)
- **Quantization**: 4-bit NF4 (BitsAndBytes)
- **LoRA**: r=16, alpha=32, all linear layers
- **Trainable params**: 8.8M (1.75% of total)
- **Batch Size**: 1 per GPU with 8 gradient accumulation steps
- **Max Sequence Length**: 1024 tokens
- **Peak VRAM**: ~4.5GB during training

## Inference Hardware Tiers
| Tier | Hardware | Config | Expected Performance |
|------|----------|--------|---------------------|
| Low | CPU only, 16GB RAM | 4-bit, seq=512 | ~5-10s per generation |
| Mid | 8GB VRAM GPU | 4-bit, seq=1024 | ~1-3s per generation |
| High | 24GB VRAM GPU | 8-bit, seq=2048 | ~0.5-1s per generation |

## Scaling Notes
- The 0.5B model fits easily on consumer hardware
- Moving to 1.5B or 3B models would require reduced batch size or deeper quantization
- 7B models require 24GB VRAM for training even with QLoRA
"""

def main():
    print("=" * 72)
    print("  Week 52 — Lyme Model v1.1 Release Packaging")
    print("=" * 72)

    # Check SFT completion
    sft_done = (CHECKPOINTS / "sft_v1_week46" / "final").exists()
    
    # Copy assets
    print("\n  Packaging assets...")
    for src, dst in RELEASE_ASSETS.items():
        result = copy_asset(src, dst)
        print(f"    {'✅' if result else '❌'} {src} → {dst}")

    # Copy checkpoints
    ckpt_dirs = ["sft_v1_week46", "tool_use_v1", "diff_v1", "test_repair_v1", "multifile_v1", "critic_v1"]
    for ckpt in ckpt_dirs:
        src = CHECKPOINTS / ckpt
        if src.exists():
            shutil.copytree(src, RELEASE_DIR / "model" / ckpt, dirs_exist_ok=True)
            print(f"    ✅ {ckpt}")

    # Collect metrics
    metrics = {}
    training_metrics = CHECKPOINTS / "sft_v1_week46" / "training_metrics.json"
    if training_metrics.exists():
        with open(training_metrics) as f:
            m = json.load(f)
            metrics["final_loss"] = m.get("training_loss", "N/A")
            metrics["eval_loss"] = m.get("eval_loss", "N/A")

    # Write model card
    card = build_model_card(sft_done, metrics)
    (RELEASE_DIR / "MODEL_CARD.md").write_text(card)
    print(f"    ✅ MODEL_CARD.md")

    # Write failure report
    (RELEASE_DIR / "FAILURE_REPORT.md").write_text(build_failure_report())
    print(f"    ✅ FAILURE_REPORT.md")

    # Write hardware notes
    (RELEASE_DIR / "HARDWARE_NOTES.md").write_text(build_hardware_notes())
    print(f"    ✅ HARDWARE_NOTES.md")

    # Write release manifest
    manifest = {
        "version": "1.1",
        "build_date": datetime.now(timezone.utc).isoformat(),
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "training_method": "QLoRA",
        "sft_completed": sft_done,
        "specializations": ["tool_use", "diff_discipline", "test_repair", "multi_file_edit", "critic"],
        "metrics": metrics,
        "assets": list(RELEASE_ASSETS.keys()),
    }
    (RELEASE_DIR / "release_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"    ✅ release_manifest.json")

    print(f"\n  Release packaged: {RELEASE_DIR.resolve()}")
    print(f"    Model card: {RELEASE_DIR / 'MODEL_CARD.md'}")
    print(f"    Size: {sum(f.stat().st_size for f in RELEASE_DIR.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
    print("=" * 72)

if __name__ == "__main__":
    main()
