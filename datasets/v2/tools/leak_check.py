#!/usr/bin/env python3
"""Cross-split leakage detection for Dataset v2.

Detects:
- Repo overlap between train and eval splits
- Instruction near-duplicates across splits
- ID collisions
"""

import json
import hashlib
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Set, Tuple


def load_jsonl(path: Path) -> List[Dict]:
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def check_repo_overlap(splits: Dict[str, List[Dict]]) -> Dict:
    """Check if same repo appears in multiple splits."""
    repo_splits = defaultdict(set)
    for split_name, examples in splits.items():
        for ex in examples:
            repo = ex.get("metadata", {}).get("source_repo",
                    ex.get("repo_context", {}).get("repo_name", "unknown"))
            repo_splits[repo].add(split_name)

    overlaps = {repo: list(rs) for repo, rs in repo_splits.items() if len(rs) > 1}
    return overlaps


def check_id_collisions(splits: Dict[str, List[Dict]]) -> Dict[str, List[str]]:
    """Check if same ID appears in multiple splits."""
    id_splits = defaultdict(set)
    for split_name, examples in splits.items():
        for ex in examples:
            id_splits[ex.get("id", "?")].add(split_name)
    collisions = {eid: list(ss) for eid, ss in id_splits.items() if len(ss) > 1}
    return collisions


def find_near_duplicates(
    examples: List[Dict], threshold: float = 0.85
) -> List[Tuple[str, str, str, float]]:
    """Find near-duplicate instructions within a set of examples."""
    dups = []
    texts = [(ex.get("id", "?"), ex.get("instruction", "")) for ex in examples]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            sim = SequenceMatcher(None, texts[i][1], texts[j][1]).ratio()
            if sim > threshold:
                dups.append((texts[i][0], texts[j][0], texts[i][1][:80], sim))
    return dups


def run_leak_check(split_paths: Dict[str, Path]) -> Dict:
    """Run full leak check across splits."""
    report = {"warnings": [], "ok": True}

    splits = {}
    for name, path in split_paths.items():
        if path.exists():
            splits[name] = load_jsonl(path)
        else:
            report["warnings"].append(f"Split {name} not found at {path}")

    if len(splits) < 2:
        report["warnings"].append("Need at least 2 splits to check leakage")
        report["ok"] = False
        return report

    print(f"  Checking {len(splits)} splits ({sum(len(v) for v in splits.values())} total examples)")

    # ID collisions
    collisions = check_id_collisions(splits)
    if collisions:
        report["id_collisions"] = collisions
        report["warnings"].append(f"Found {len(collisions)} ID collisions across splits")
        report["ok"] = False

    # Repo overlap
    overlaps = check_repo_overlap(splits)
    if overlaps:
        report["repo_overlaps"] = overlaps
        report["warnings"].append(f"Found {len(overlaps)} repos spanning multiple splits")
        report["ok"] = False

    # Near-duplicate instructions within test split (most critical)
    if "test" in splits:
        test_dups = find_near_duplicates(splits["test"], threshold=0.85)
        if test_dups:
            report["test_near_duplicates"] = test_dups[:10]
            report["warnings"].append(f"Found {len(test_dups)} near-duplicates in test split")
            report["ok"] = False

    # Cross-split instruction similarity (train vs test)
    if "train" in splits and "test" in splits:
        train_texts = {(ex.get("id", "?"), ex.get("instruction", "")) for ex in splits["train"]}
        test_texts = {(ex.get("id", "?"), ex.get("instruction", "")) for ex in splits["test"]}
        cross_dups = []
        for tid, ttext in train_texts:
            for eid, etext in test_texts:
                sim = SequenceMatcher(None, ttext, etext).ratio()
                if sim > 0.90:
                    cross_dups.append((tid, eid, sim))
        if cross_dups:
            report["cross_split_duplicates"] = cross_dups[:10]
            report["warnings"].append(f"Found {len(cross_dups)} train/test cross-duplicates")
            report["ok"] = False

    if report["ok"]:
        report["warnings"].append("No leakage detected")
        print("  ✅ No leaks found")
    else:
        print(f"  ⚠️  {len(report['warnings'])} issues found")

    return report


def main():
    import sys
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("datasets/v2")

    split_paths = {}
    for split_name in ("train", "val", "test"):
        p = base / "mined" / split_name / "combined.jsonl"
        if p.exists():
            split_paths[split_name] = p

    if not split_paths:
        print("No splits found. Run mining pipeline first.")
        return

    report = run_leak_check(split_paths)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
