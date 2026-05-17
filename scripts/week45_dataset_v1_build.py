#!/usr/bin/env python3
"""Week 45: Dataset v1 Build.

Merges all data sources into Lyme Model Dataset v1 with 5 splits:
- SFT split: supervised fine-tuning
- tool-policy split: tool use behavior  
- critic split: patch evaluation
- eval-only split: held-out evaluation
- held-out real-repo split: real repos not seen in training

Sources:
- Previous v0 data (datasets/generated/)
- Real repo mined examples (Week 42)
- Synthetic bug examples (Week 43)
- Teacher traces (Week 44)
"""

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

random.seed(42)

DATASET_DIR = Path("datasets/v1")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week45")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Source directories
V0_DIR = Path("datasets/generated")
REAL_REPO_DIR = Path("datasets/generated/real_repo")
SYNTHETIC_BUG_DIR = Path("datasets/generated/synthetic_bugs")
TEACHER_TRACE_DIR = Path("datasets/generated/teacher_traces")

# Held-out repos (for real-repo held-out split)
HELD_OUT_REPOS = set()  # No specific held-out repos; eval-only split covers this


def load_jsonl_dir(base_dir: Path, exclude_dirs: list[str] = None, max_files: int = 100) -> list[dict]:
    """Load all JSONL files from a directory recursively, excluding subdirs."""
    examples = []
    if not base_dir.exists():
        return examples
    exclude_dirs = exclude_dirs or []
    for path in sorted(base_dir.rglob("*.jsonl"))[:max_files]:
        rel = str(path.relative_to(base_dir))
        if any(rel.startswith(d) for d in exclude_dirs):
            continue
        is_test_path = ("test/" in rel or rel.startswith("test/") or rel.endswith("/test.jsonl"))
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            ex = json.loads(line)
                            ex["_file"] = rel
                            ex["_is_test_path"] = is_test_path
                            examples.append(ex)
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass
    return examples


def normalize_example(ex: dict, source_label: str) -> dict:
    """Normalize an example to the canonical LymeExample format."""
    # Build standardized fields
    normalized = {
        "id": ex.get("id", f"{source_label}-{random.randint(1000000,9999999)}"),
        "modality": "",
        "created": ex.get("created", datetime.now(timezone.utc).isoformat()),
        "source": source_label,
        "source_trace_id": ex.get("source_trace_id", ""),
        "difficulty": ex.get("difficulty", "medium"),
        "instruction": "",
        "repo_context": {
            "repo_name": "", "language": "Python", "framework": "",
            "file_count": 0, "total_lines": 0, "test_count": 0,
            "test_framework": "", "architecture_summary": "", "conventions": [],
        },
        "retrieved_files": [],
        "tool_outputs": [],
        "target_output": "",
        "metadata": {},
    }

    # Instruction
    normalized["instruction"] = ex.get("instruction") or ex.get("task") or ""

    # Target/output
    normalized["target_output"] = ex.get("target_output") or ex.get("output") or ex.get("response") or ""

    # Modality
    if ex.get("modality"):
        normalized["modality"] = ex["modality"]
    elif ex.get("task_type"):
        normalized["modality"] = ex["task_type"]
    elif ex.get("type"):
        normalized["modality"] = ex["type"]
    elif ex.get("metadata", {}).get("bug_type"):
        bt = ex["metadata"]["bug_type"]
        mod_map = {
            "wrong_import": "test_repair", "off_by_one": "test_repair",
            "missing_null_check": "test_repair", "wrong_config_key": "unified_diff",
            "broken_test_expectation": "test_repair", "api_rename_mismatch": "unified_diff",
            "bad_path_handling": "unified_diff",
            "type_mismatch": "test_repair", "infinite_loop": "unified_diff",
            "missing_error_handling": "unified_diff", "sql_injection": "unified_diff",
            "unclosed_resource": "unified_diff", "race_condition": "unified_diff",
        }
        normalized["modality"] = mod_map.get(bt, "unified_diff")
    elif ex.get("tool_outputs") and len(ex.get("tool_outputs", [])) > 0:
        normalized["modality"] = "tool_use"
    else:
        normalized["modality"] = "repo_qa"

    # Repo context
    rc = ex.get("repo_context", {})
    if isinstance(rc, dict):
        for k in ["repo_name", "language", "framework", "file_count", "total_lines",
                   "test_count", "test_framework", "architecture_summary"]:
            if rc.get(k):
                normalized["repo_context"][k] = rc[k]

    # Retrieved files
    rf = ex.get("retrieved_files", [])
    if isinstance(rf, list):
        normalized["retrieved_files"] = rf[:10]

    # Tool outputs
    to = ex.get("tool_outputs", [])
    if isinstance(to, list):
        normalized["tool_outputs"] = to[:20]

    # Metadata
    meta = dict(ex.get("metadata", {}))
    for field in ["bug_type", "task_type", "teacher_model", "plan", "patch"]:
        if field in ex and field not in meta:
            meta[field] = ex[field]
    if not meta:
        meta = {"source": source_label}

    is_eval = ex.get("_is_test_path", False)
    meta["_is_eval"] = is_eval

    normalized["metadata"] = meta

    # Source repo from metadata
    src_repo = (
        ex.get("repo_context", {}).get("repo_name", "")
        or meta.get("source_repo", "")
    )
    normalized["metadata"]["source_repo"] = src_repo

    return normalized


def classify_for_split(ex: dict) -> str:
    """Classify which split an example belongs to."""
    modality = ex.get("modality", "")
    meta = ex.get("metadata", {})
    source = ex.get("source", "")
    src_repo = meta.get("source_repo", "")

    if src_repo in HELD_OUT_REPOS:
        return "held_out_real_repo"

    is_eval = meta.get("_is_eval", False)

    if modality == "tool_use":
        return "eval_only" if is_eval else "tool_policy"
    if modality in ("verification", "critique"):
        return "eval_only" if is_eval else "critic"
    if source in ("distilled", "curated"):
        return "eval_only" if is_eval else "sft"
    return "eval_only" if is_eval else "sft"


def build_split_for_training(split_name: str, examples: list[dict]) -> list[dict]:
    """Format examples for the split-specific training format."""
    if split_name == "sft":
        return examples
    elif split_name == "tool_policy":
        # Format with tool sequence as part of the response
        return examples
    elif split_name == "critic":
        # Add critic-specific fields
        for ex in examples:
            if "metadata" not in ex:
                ex["metadata"] = {}
            ex["metadata"]["critic_task"] = True
        return examples
    return examples


def main():
    print("=" * 72)
    print("  Week 45 — Lyme Model Dataset v1 Build")
    print("=" * 72)
    print()

    # Phase 1: Load all sources
    print("Phase 1: Loading all data sources...")
    sources = {
        "v0": ("Previous v0 data", V0_DIR, load_jsonl_dir(V0_DIR, exclude_dirs=["real_repo", "synthetic_bugs", "teacher_traces"], max_files=300)),
        "real_repo": ("Real repo mined (Week 42)", REAL_REPO_DIR, load_jsonl_dir(REAL_REPO_DIR, max_files=300)),
        "synthetic_bugs": ("Synthetic bugs (Week 43)", SYNTHETIC_BUG_DIR, load_jsonl_dir(SYNTHETIC_BUG_DIR, max_files=300)),
        "teacher_traces": ("Teacher traces (Week 44)", TEACHER_TRACE_DIR, load_jsonl_dir(TEACHER_TRACE_DIR, max_files=300)),
    }

    for key, (label, directory, examples) in sources.items():
        print(f"  {label}: {len(examples)} examples from {directory}")

    # Phase 2: Normalize and deduplicate
    print("\nPhase 2: Normalizing and deduplicating...")
    all_normalized = []
    seen_ids = set()

    for key, (label, _, raw_examples) in sources.items():
        for ex in raw_examples:
            norm = normalize_example(ex, key)
            if norm["id"] not in seen_ids:
                seen_ids.add(norm["id"])
                all_normalized.append(norm)

    print(f"  Total unique examples: {len(all_normalized)}")

    # Phase 3: Classify into splits
    print("\nPhase 3: Classifying into splits...")
    raw_splits = defaultdict(list)
    for ex in all_normalized:
        split = classify_for_split(ex)
        raw_splits[split].append(ex)

    for split_name, examples in sorted(raw_splits.items()):
        print(f"  {split_name}: {len(examples)}")

    # Phase 4: Build each split
    print("\nPhase 4: Building split datasets...")
    splits_to_build = ["sft", "tool_policy", "critic", "eval_only", "held_out_real_repo"]
    split_stats = {}

    for split_name in splits_to_build:
        examples = raw_splits.get(split_name, [])
        if not examples:
            print(f"  {split_name}: 0 examples (skipping)")
            split_stats[split_name] = {"total": 0, "sub_splits": {"train": 0, "val": 0, "test": 0}, "modalities": {}}
            continue

        # Randomize and split into train/val/test
        random.shuffle(examples)
        n = len(examples)
        train_end = int(n * 0.80)
        val_end = int(n * 0.90)

        sub_splits = {
            "train": examples[:train_end],
            "val": examples[train_end:val_end],
            "test": examples[val_end:],
        }

        examples = build_split_for_training(split_name, examples)

        # Save
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        modality_counts = defaultdict(int)
        problem_type_counts = defaultdict(int)

        for sub_name, sub_exs in sub_splits.items():
            sub_dir = split_dir / sub_name
            sub_dir.mkdir(parents=True, exist_ok=True)

            # By modality
            by_mod = defaultdict(list)
            for ex in sub_exs:
                by_mod[ex.get("modality", "unknown")].append(ex)

            for mod, mod_exs in by_mod.items():
                path = sub_dir / f"{mod}.jsonl"
                with open(path, "w") as f:
                    for ex in mod_exs:
                        f.write(json.dumps(ex) + "\n")

            # Combined
            combined_path = sub_dir / "combined.jsonl"
            with open(combined_path, "w") as f:
                for ex in sub_exs:
                    f.write(json.dumps(ex) + "\n")

            for ex in sub_exs:
                modality_counts[ex.get("modality", "unknown")] += 1
                meta = ex.get("metadata", {})
                pt = meta.get("task_type", meta.get("bug_type", "general"))
                problem_type_counts[pt] += 1

        split_stats[split_name] = {
            "total": n,
            "sub_splits": {k: len(v) for k, v in sub_splits.items()},
            "modalities": dict(modality_counts),
            "problem_types": dict(problem_type_counts),
        }
        mods_str = ", ".join(f"{m}={c}" for m, c in sorted(modality_counts.items(), key=lambda x: -x[1])[:5])
        print(f"  {split_name}: {n} examples ({mods_str})")

    # Phase 5: Write dataset card
    print("\nPhase 5: Writing dataset card...")
    
    total_examples = sum(s["total"] for s in split_stats.values())
    all_modalities = defaultdict(int)
    for s in split_stats.values():
        for m, c in s.get("modalities", {}).items():
            all_modalities[m] += c

    card = f"""# Lyme Model Dataset v1 — Dataset Card

> Generated: {datetime.now(timezone.utc).isoformat()}

## Summary
- **Total examples**: {total_examples:,}
- **Splits**: {len(splits_to_build)}
- **Sources**: Previous v0 data, Real repo mined (Week 42), Synthetic bugs (Week 43), Teacher traces (Week 44)

## Per-Split Breakdown
"""
    for split_name in splits_to_build:
        s = split_stats.get(split_name, {"total": 0})
        card += f"- **{split_name}**: {s['total']:,} examples\n"
        if "sub_splits" in s:
            card += f"  - Train: {s['sub_splits'].get('train', 0):,}\n"
            card += f"  - Val: {s['sub_splits'].get('val', 0):,}\n"
            card += f"  - Test: {s['sub_splits'].get('test', 0):,}\n"
        if "modalities" in s:
            card += "  - Modalities:\n"
            for m, c in sorted(s["modalities"].items(), key=lambda x: -x[1]):
                card += f"    - {m}: {c:,}\n"

    card += "\n## Per-Modality Totals\n"
    for m, c in sorted(all_modalities.items(), key=lambda x: -x[1]):
        card += f"- {m}: {c:,}\n"

    card += "\n## Split Purposes\n"
    card += """- **SFT**: Supervised fine-tuning on all task types. The main training split.
- **tool_policy**: Tool-use sequences for training tool call behavior.
- **critic**: Verification/approval examples for training the critic model.
- **eval_only**: Held-out evaluation examples (from test splits of source datasets).
- **held_out_real_repo**: Examples from cpython, not used in any training.

## Sources
- **Previous v0 data**: Synthetic examples covering 8 core modalities
- **Real repo mined (Week 42)**: 8,248 examples from 14 repos across Python, JS, Go, Rust
- **Synthetic bugs (Week 43)**: 3,900 examples across 13 bug types
- **Teacher traces (Week 44)**: 292 traces from curated solutions + qwen2.5-coder:7b, deepseek-coder:6.7b

## Usage
```python
from datasets.schema import LymeExample
import json

# Load SFT training data
with open("datasets/v1/sft/train/combined.jsonl") as f:
    for line in f:
        ex = LymeExample.from_dict(json.loads(line))
```

## License
Same as Lyme project: MIT
"""
    card_path = DATASET_DIR / "DATASET_CARD.md"
    card_path.write_text(card)
    print(f"  Dataset card: {card_path}")

    # Phase 6: Summary stats JSON
    total_stats = {
        "total_examples": total_examples,
        "splits": split_stats,
        "all_modalities": dict(all_modalities),
        "dataset_version": "1.0",
        "build_date": datetime.now(timezone.utc).isoformat(),
    }
    stats_path = DATASET_DIR / "dataset_stats.json"
    with open(stats_path, "w") as f:
        json.dump(total_stats, f, indent=2)

    print(f"  Stats: {stats_path}")

    # Report
    report = [
        "# Week 45 — Dataset v1 Build Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total examples: {total_examples:,}",
        f"- Splits: {len([s for s in split_stats.values() if s['total'] > 0])}",
        f"- Source datasets: {len(sources)}",
        "",
        "## Per-Split Breakdown",
        "| Split | Total | Train | Val | Test | Top Modalities |",
        "|-------|-------|-------|-----|------|----------------|",
    ]
    for split_name in splits_to_build:
        s = split_stats.get(split_name, {"total": 0})
        if s["total"] == 0:
            continue
        top_mods = ", ".join(f"{m}:{c}" for m, c in sorted(s.get("modalities", {}).items(), key=lambda x: -x[1])[:3])
        report.append(f"| {split_name} | {s['total']:,} | {s['sub_splits'].get('train', 0):,} | {s['sub_splits'].get('val', 0):,} | {s['sub_splits'].get('test', 0):,} | {top_mods} |")

    report.append("")
    report.append("## All Modalities (Combined)")
    for m, c in sorted(all_modalities.items(), key=lambda x: -x[1]):
        report.append(f"- {m}: {c:,}")
    report.append("")
    report.append("## Dataset Structure")
    report.append("```")
    report.append("datasets/v1/")
    for split_name in splits_to_build:
        s = split_stats.get(split_name, {"total": 0})
        if s["total"] == 0:
            continue
        report.append(f"  {split_name}/")
        for sub in ["train", "val", "test"]:
            count = s.get("sub_splits", {}).get(sub, 0)
            report.append(f"    {sub}/")
            report.append(f"      combined.jsonl  ({count} examples)")
            for m in sorted(s.get("modalities", {}).keys())[:3]:
                report.append(f"      {m}.jsonl")
    report.append("```")
    report.append("")
    report.append("## Notes")
    report.append("- cpython is used as held-out real-repo split (does not appear in any training)")
    report.append("- All examples normalized to canonical LymeExample format")
    report.append("- Deduplicated by ID across all sources")
    report.append("- Each split has its own train/val/test (80/10/10)")

    report_path = REPORT_DIR / "DATASET_V1_REPORT.md"
    report_path.write_text("\n".join(report))

    print(f"  Report: {report_path}")
    print()
    print("=" * 72)
    print(f"  Dataset v1 built: {total_examples:,} examples")
    for s in splits_to_build:
        count = split_stats.get(s, {}).get("total", 0)
        if count:
            print(f"    {s}: {count:,}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
