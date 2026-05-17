#!/usr/bin/env python3
"""Dataset v2 — Assembly Pipeline.

Merges all sources (v1, mined, synthetic failures, teacher traces),
quality-filters, deduplicates, splits into SFT/action/critic/reward/holdout,
and generates dataset card + stats.
"""

import json
import hashlib
import sys
import random
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from datasets.schema import LymeExample, compute_statistics
from datasets.v2.tools.quality_filter import check_example

random.seed(85)

V2_DIR = Path("datasets/v2")
V2_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DIR = Path("lyme-output/week85")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Source Directories ─────────────────────────────────────────────────────────

SOURCES = {
    "v1_existing": {
        "path": Path("datasets/v1/sft/train"),
        "weight": 1.0,
        "description": "Dataset v1 SFT training data (16,328 examples)",
    },
    "v1_critic": {
        "path": Path("datasets/v1/critic/train"),
        "weight": 1.0,
        "description": "Dataset v1 critic/verification data",
    },
    "v1_tool_policy": {
        "path": Path("datasets/v1/tool_policy/train"),
        "weight": 1.0,
        "description": "Dataset v1 tool-use policy data",
    },
    "mined": {
        "path": Path("datasets/v2/mined/train"),
        "weight": 1.0,
        "description": "Real repo mined tasks (Week 82)",
    },
    "synthetic_failures": {
        "path": Path("datasets/v2/synthetic_failures/train"),
        "weight": 1.0,
        "description": "Synthetic bug factory v2 (Week 83)",
    },
    "teacher_traces": {
        "path": Path("datasets/v2/teacher_traces/train"),
        "weight": 1.0,
        "description": "Teacher behavior traces (Week 84)",
    },
}


def load_jsonl_dir(dir_path: Path, max_examples: int = 0) -> List[Dict]:
    """Load examples from a directory. Prefers combined.jsonl, falls back to
    per-modality files but NOT both (to avoid double-loading)."""
    examples = []
    if not dir_path.exists():
        return examples

    combined = dir_path / "combined.jsonl"
    if combined.exists():
        with open(combined) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    else:
        for jsonl_file in sorted(dir_path.glob("*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            examples.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    if max_examples > 0 and len(examples) > max_examples:
        random.shuffle(examples)
        examples = examples[:max_examples]
    return examples


def deduplicate(examples: List[Dict]) -> List[Dict]:
    """Deduplicate by instruction hash (exact)."""
    seen_instructions = set()
    unique = []
    for ex in examples:
        inst = ex.get("instruction", "")
        inst_hash = hashlib.md5(inst.encode()).hexdigest()
        if inst_hash in seen_instructions:
            continue
        seen_instructions.add(inst_hash)
        unique.append(ex)
    return unique


def convert_to_v2_schema(ex: Dict) -> Optional[Dict]:
    """Ensure an example conforms to v2 schema. Upgrade v1 examples."""
    if not ex.get("id"):
        return None
    if not ex.get("instruction"):
        return None
    # Ensure language field
    if not ex.get("language"):
        rc = ex.get("repo_context", {})
        ex["language"] = rc.get("language", "unknown")
    # Ensure created field
    if not ex.get("created"):
        ex["created"] = datetime.now(timezone.utc).isoformat()
    return ex


def assign_split(ex: Dict) -> str:
    """Assign to SFT, action, critic, or reward based on modality."""
    modality = ex.get("modality", "")
    if modality == "tool_use":
        return "action"
    if modality in ("verification", "patch_critique"):
        return "critic"
    return "sft"


def is_hard_holdout(ex: Dict) -> bool:
    """Check if this should go to held-out hard set."""
    return ex.get("difficulty") in ("hard", "expert") and random.random() < 0.15


def is_eval_only(ex: Dict) -> bool:
    """Check if this is explicitly eval-only."""
    meta = ex.get("metadata", {})
    if isinstance(meta, dict) and meta.get("_is_eval"):
        return True
    return False


def main():
    print("=" * 72)
    print("  Week 85 — Dataset v2 Assembly")
    print("=" * 72)
    print()

    all_examples = []
    source_stats = {}

    # Load all sources
    for source_name, source_config in SOURCES.items():
        src_path = source_config["path"]
        weight = source_config.get("weight", 1.0)
        print(f"  Loading {source_name} from {src_path}...", end=" ", flush=True)
        raw = load_jsonl_dir(src_path)
        print(f"{len(raw)} raw", end=" ", flush=True)

        # Convert to v2 schema
        converted = []
        for ex in raw:
            c = convert_to_v2_schema(ex)
            if c:
                converted.append(c)
        print(f"→ {len(converted)} after conversion", end=" ", flush=True)

        # Quality filter
        passed = 0
        for ex in converted:
            le = LymeExample.from_dict(ex)
            ok, _ = check_example(le)
            if ok:
                le_dict = le.to_dict()
                all_examples.append(le_dict)
                passed += 1

        print(f"→ {passed} after quality filter")
        source_stats[source_name] = {
            "raw": len(raw), "converted": len(converted), "passed": passed,
        }

    print(f"\n  Total loaded: {sum(s['raw'] for s in source_stats.values())}")
    print(f"  After filter: {len(all_examples)}")

    # Deduplicate
    print(f"\n  Deduplicating...", end=" ", flush=True)
    unique = deduplicate(all_examples)
    print(f"{len(all_examples)} → {len(unique)} ({len(all_examples) - len(unique)} removed)")

    # Split into SFT / action / critic / reward / heldout
    sft = []
    action = []
    critic = []
    reward = []
    heldout_hard = []
    eval_only = []

    for ex in unique:
        if is_eval_only(ex):
            eval_only.append(ex)
            continue
        if is_hard_holdout(ex):
            heldout_hard.append(ex)
            continue

        split_name = assign_split(ex)
        if split_name == "sft":
            sft.append(ex)
        elif split_name == "action":
            action.append(ex)
        elif split_name == "critic":
            critic.append(ex)
        else:
            sft.append(ex)  # fallback

    # Split SFT into train/val/test
    random.shuffle(sft)
    n_sft = len(sft)
    sft_train = sft[:int(n_sft * 0.80)]
    sft_val = sft[int(n_sft * 0.80):int(n_sft * 0.90)]
    sft_test = sft[int(n_sft * 0.90):]

    # Split action
    random.shuffle(action)
    n_action = len(action)
    action_train = action[:int(n_action * 0.80)]
    action_val = action[int(n_action * 0.80):int(n_action * 0.90)] if n_action > 0 else []
    action_test = action[int(n_action * 0.90):] if n_action > 0 else []

    # Split critic
    random.shuffle(critic)
    n_critic = len(critic)
    critic_train = critic[:int(n_critic * 0.80)]
    critic_val = critic[int(n_critic * 0.80):int(n_critic * 0.90)] if n_critic > 0 else []
    critic_test = critic[int(n_critic * 0.90):] if n_critic > 0 else []

    # Split reward (use a portion of SFT)
    reward_size = min(2000, len(sft) // 10)
    reward_pool = sft[:reward_size]
    random.shuffle(reward_pool)
    reward_n = len(reward_pool)
    reward_train = reward_pool[:int(reward_n * 0.80)]
    reward_val = reward_pool[int(reward_n * 0.80):int(reward_n * 0.90)]
    reward_test = reward_pool[int(reward_n * 0.90):]

    # Also generate preference pairs for reward
    preference = []
    if len(sft_train) >= 200:
        for ex in sft_train[:1000]:
            pref = ex.copy()
            pref["modality"] = "preference"
            pref["metadata"] = pref.get("metadata", {}).copy() if isinstance(pref.get("metadata"), dict) else {}
            pref["metadata"]["preference_type"] = "good_example"
            preference.append(pref)

    splits = {
        "sft": {"train": sft_train, "val": sft_val, "test": sft_test},
        "action": {"train": action_train, "val": action_val, "test": action_test},
        "critic": {"train": critic_train, "val": critic_val, "test": critic_test},
        "reward": {"train": reward_train, "val": reward_val, "test": reward_test},
        "heldout_hard": {"train": [], "val": [], "test": heldout_hard},
        "eval_only": {"train": [], "val": [], "test": eval_only},
        "preference": {"train": preference, "val": [], "test": []},
    }

    # Write splits
    for split_name, split_data in splits.items():
        print(f"\n  {split_name}:")
        split_dir = V2_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        for subset_name, examples in split_data.items():
            if not examples:
                continue
            subset_dir = split_dir / subset_name
            subset_dir.mkdir(parents=True, exist_ok=True)
            by_mod = defaultdict(list)
            for ex in examples:
                by_mod[ex.get("modality", "unknown")].append(ex)
            for mod, mod_exs in by_mod.items():
                with open(subset_dir / f"{mod}.jsonl", "w") as f:
                    for e in mod_exs:
                        f.write(json.dumps(e) + "\n")
            with open(subset_dir / "combined.jsonl", "w") as f:
                for e in examples:
                    f.write(json.dumps(e) + "\n")
            print(f"    {subset_name}: {len(examples)} ({len(by_mod)} modalities)")

    # Generate Dataset Card
    total = sum(len(v) for s in splits.values() for v in s.values())
    total_train = sum(len(v) for s in splits.values() for k, v in s.items() if k == "train")
    total_val = sum(len(v) for s in splits.values() for k, v in s.items() if k == "val")
    total_test = sum(len(v) for s in splits.values() for k, v in s.items() if k == "test")

    modality_totals = defaultdict(int)
    for s in splits.values():
        for v in s.values():
            for ex in v:
                modality_totals[ex.get("modality", "unknown")] += 1

    dataset_card = [
        "# Lyme Model Dataset v2 — Dataset Card",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> Assembly: Week 85",
        "",
        "## Summary",
        f"- **Total examples**: {total}",
        f"- **Total unique**: {len(unique)}",
        f"- **Splits**: {len(splits)}",
        f"- **Sources**: {len(SOURCES)}",
        f"- **Modalities**: {len(modality_totals)}",
        "",
        "## Sources",
    ]
    for src_name, src_stat in sorted(source_stats.items()):
        dataset_card.append(f"- **{src_name}**: {src_stat['raw']} raw → {src_stat['passed']} after filter")

    dataset_card.append("")
    dataset_card.append("## Split Breakdown")
    for split_name, split_data in sorted(splits.items()):
        sizes = {k: len(v) for k, v in split_data.items()}
        dataset_card.append(f"- **{split_name}**: {sizes}")

    dataset_card.append("")
    dataset_card.append("## Per-Modality Totals")
    for mod, count in sorted(modality_totals.items()):
        dataset_card.append(f"- {mod}: {count}")

    dataset_card.append("")
    dataset_card.append("## Split Purposes")
    dataset_card.append("- **sft**: Main supervised fine-tuning on all task types")
    dataset_card.append("- **action**: Tool-use action sequences for training tool behavior")
    dataset_card.append("- **critic**: Patch critique/verification examples")
    dataset_card.append("- **reward**: Preference/reward model training data")
    dataset_card.append("- **heldout_hard**: Expert-difficulty examples, never used in training")
    dataset_card.append("- **eval_only**: Held-out evaluation (from test splits)")
    dataset_card.append("- **preference**: Generated preference pairs for DPO/RLHF")

    dataset_card.append("")
    dataset_card.append("## Usage")
    dataset_card.append("```python")
    dataset_card.append("from datasets.schema import LymeExample")
    dataset_card.append("import json")
    dataset_card.append("")
    dataset_card.append("with open('datasets/v2/sft/train/combined.jsonl') as f:")
    dataset_card.append("    for line in f:")
    dataset_card.append("        ex = LymeExample.from_dict(json.loads(line))")
    dataset_card.append("```")

    dataset_card_path = V2_DIR / "DATASET_CARD.md"
    dataset_card_path.write_text("\n".join(dataset_card))

    # Generate stats JSON
    stats = {
        "version": "2.0",
        "total": total,
        "total_unique": len(unique),
        "generated": datetime.now(timezone.utc).isoformat(),
        "sources": {k: v["passed"] for k, v in source_stats.items()},
        "splits": {s: {k: len(v) for k, v in d.items()} for s, d in splits.items()},
        "modalities": dict(modality_totals),
    }
    with open(V2_DIR / "dataset_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n  Dataset card: {dataset_card_path}")
    print(f"  Stats: {V2_DIR}/dataset_stats.json")
    print("=" * 72)
    print(f"  Total: {total} examples")
    print(f"  Train: {total_train}, Val: {total_val}, Test: {total_test}")
    print(f"  Modalities: {len(modality_totals)}")
    print("=" * 72)

    return stats


if __name__ == "__main__":
    main()
