#!/usr/bin/env python3
"""Merge migrated flat-format examples back into canonical dataset files."""

import json
from pathlib import Path

DATASET_DIR = Path("datasets/generated")
MIGRATED_PATH = Path("lyme-output/week41/migrated_flat_format.jsonl")

def load_jsonl(path):
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples

def write_jsonl(path, examples):
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

def main():
    migrated = load_jsonl(MIGRATED_PATH)
    print(f"Loaded {len(migrated)} migrated examples")

    # Group by source file
    by_source = {}
    for ex in migrated:
        src = ex.get("_file", "")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(ex)

    # Overwrite each source file with migrated versions
    total_updated = 0
    for src_file, examples in by_source.items():
        src_path = DATASET_DIR / src_file
        if not src_path.exists():
            print(f"  Skipping {src_file} (not found)")
            continue

        # Read original, build line-indexed map
        with open(src_path) as f:
            original_lines = f.readlines()

        migrated_by_line = {ex["_line"]: ex for ex in examples if "_line" in ex}

        # Replace lines
        updated_count = 0
        for line_no in sorted(migrated_by_line.keys(), reverse=True):
            ex = migrated_by_line[line_no]
            clean = {k: v for k, v in ex.items() if not k.startswith("_")}
            original_lines[line_no - 1] = json.dumps(clean) + "\n"
            updated_count += 1

        write_jsonl(src_path, [json.loads(l) for l in original_lines if l.strip()])
        total_updated += updated_count
        print(f"  Updated {updated_count} lines in {src_file}")

    print(f"\nTotal: {total_updated} examples migrated in-place")

if __name__ == "__main__":
    main()
