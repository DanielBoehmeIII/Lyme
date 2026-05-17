#!/usr/bin/env python3
"""Week 42: Real Repo Task Mining (v2)."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional

DATASET_DIR = Path("datasets/generated/real_repo")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week42")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_REPOS = [
    ("https://github.com/pallets/flask", "flask", "BSD-3-Clause"),
    ("https://github.com/psf/requests", "requests", "Apache-2.0"),
    ("https://github.com/tiangolo/fastapi", "fastapi", "MIT"),
    ("https://github.com/django/django", "django", "BSD-3-Clause"),
    ("https://github.com/pallets/click", "click", "BSD-3-Clause"),
    ("https://github.com/python/cpython", "cpython", "Python-2.0"),
]


def run_git(repo_path: str | Path, args: list[str]) -> str:
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(repo_path), timeout=30)
        return r.stdout
    except:
        return ""


def parse_diffstat(diff: str) -> dict:
    files = set()
    adds = 0
    dels = 0
    for line in diff.split("\n"):
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            files.add(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            adds += 1
        elif line.startswith("-") and not line.startswith("---"):
            dels += 1
    return {"files_changed": len(files), "files": sorted(files)[:10], "additions": adds, "deletions": dels}


def classify(msg: str, stat: dict) -> str:
    m = msg.lower()
    if "fix" in m or "bug" in m or "hotfix" in m or "patch" in m or "repair" in m:
        return "bug_fix"
    if "test" in m and ("fix" in m or "update" in m or "repair" in m):
        return "fix_test"
    if "refactor" in m or "clean" in m or "rename" in m or "move" in m:
        return "refactor"
    if "dep" in m or "bump" in m or "version" in m or "requirements" in m:
        return "dep_update"
    if "config" in m or ("setting" in m and "change" in m):
        return "config_change"
    if "test" in m and ("add" in m or "cover" in m or "more" in m):
        return "add_test"
    if stat["files_changed"] <= 3 and stat["additions"] <= 30:
        return "small_fix"
    if "add" in m or "support" in m or "implement" in m or "feature" in m or "feat" in m:
        return "feature"
    if "update" in m or "improve" in m or "better" in m:
        return "update"
    if "remove" in m or "delete" in m or "drop" in m:
        return "cleanup"
    return "other"


def is_merge(diff: str) -> bool:
    return diff.strip() == ""


def has_parent_in_repo(repo_path, sha):
    try:
        r = subprocess.run(["git", "rev-parse", f"{sha}^"], capture_output=True, text=True, cwd=str(repo_path), timeout=5)
        return r.returncode == 0
    except:
        return False


def extract_single_file_diffs(diff: str) -> list[dict]:
    """Split a multi-file diff into per-file diffs."""
    files = []
    current_file = None
    current_diff = []
    
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_diff:
                files.append({"file": current_file, "diff": "\n".join(current_diff)})
            current_file = None
            current_diff = []
        elif line.startswith("--- a/"):
            continue
        elif line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if current_file is not None:
            current_diff.append(line)
    
    if current_file and current_diff:
        files.append({"file": current_file, "diff": "\n".join(current_diff)})
    
    return files


def commit_to_examples(sha: str, subject: str, body: str, date: str, diff: str, repo_name: str, lang: str, test_fw: str, repo_url: str) -> list[dict]:
    """Convert a commit into one or more LymeExamples."""
    stat = parse_diffstat(diff)
    
    ct = classify(subject, stat)
    if ct == "other":
        return []
    if stat["additions"] == 0:
        return []
    if stat["additions"] + stat["deletions"] > 300:
        return []
    
    # Build the main example from the full diff
    task = f"Implement: {subject}"
    if body and body != subject:
        b = body[:500].strip()
        if b:
            task += f"\n\n{b}"
    
    files_changed = stat["files"]
    
    # Map to modality
    mod_map = {
        "bug_fix": "unified_diff", "fix_test": "test_repair",
        "config_change": "patch_planning", "feature": "unified_diff",
        "refactor": "unified_diff", "small_fix": "unified_diff",
        "update": "unified_diff", "dep_update": "patch_planning",
        "add_test": "test_repair", "cleanup": "unified_diff",
    }
    modality = mod_map.get(ct, "unified_diff")
    
    files_json = []
    for f in files_changed[:5]:
        role = "test" if "test" in f.lower() or "tests" in f.lower() else "source"
        files_json.append({
            "file_path": f, "role": role,
            "content_preview": f"Modified in {repo_name} commit {sha[:12]}",
            "lines": stat["additions"] + stat["deletions"],
            "relevance_score": 1.0,
        })
    
    example = {
        "id": f"real-{repo_name}-{sha[:12]}-0",
        "modality": modality,
        "created": date,
        "source": "mined",
        "source_trace_id": f"commit:{sha}",
        "difficulty": "easy" if stat["additions"] < 10 else ("medium" if stat["additions"] < 30 else "hard"),
        "instruction": task,
        "repo_context": {
            "repo_name": repo_name, "language": lang, "framework": "",
            "file_count": 0, "total_lines": 0, "test_count": 0,
            "test_framework": test_fw, "architecture_summary": "", "conventions": [],
        },
        "retrieved_files": files_json,
        "tool_outputs": [],
        "target_output": diff[:3000],
        "metadata": {
            "task_type": ct, "commit_sha": sha, "files_changed": stat["files_changed"],
            "additions": stat["additions"], "deletions": stat["deletions"],
            "source_repo": repo_name, "source_url": repo_url,
        },
    }
    
    examples = [example]
    
    # Also create per-file examples for multi-file diffs
    per_file_diffs = extract_single_file_diffs(diff)
    if len(per_file_diffs) > 1:
        for i, pf in enumerate(per_file_diffs):
            pf_stat = parse_diffstat(pf["diff"])
            if pf_stat["additions"] == 0:
                continue
            ex = {
                "id": f"real-{repo_name}-{sha[:12]}-file-{i}",
                "modality": modality,
                "created": date,
                "source": "mined",
                "source_trace_id": f"commit:{sha}:{pf['file']}",
                "difficulty": "easy" if pf_stat["additions"] < 10 else "medium",
                "instruction": f"In {pf['file']}: {subject}",
                "repo_context": example["repo_context"],
                "retrieved_files": [{
                    "file_path": pf["file"],
                    "role": "test" if "test" in pf["file"].lower() else "source",
                    "content_preview": f"Modified in {sha[:12]}",
                    "lines": pf_stat["additions"] + pf_stat["deletions"],
                    "relevance_score": 1.0,
                }],
                "tool_outputs": [],
                "target_output": pf["diff"],
                "metadata": {
                    "task_type": ct, "commit_sha": sha, "files_changed": 1,
                    "additions": pf_stat["additions"], "deletions": pf_stat["deletions"],
                    "source_repo": repo_name, "source_url": repo_url,
                    "single_file": True,
                },
            }
            examples.append(ex)
    
    return examples


def detect_lang(repo_path: Path) -> str:
    if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists() or list(repo_path.glob("**/*.py")):
        return "Python"
    if (repo_path / "Cargo.toml").exists():
        return "Rust"
    if (repo_path / "go.mod").exists():
        return "Go"
    if (repo_path / "package.json").exists():
        return "JavaScript"
    return "unknown"


def detect_test_fw(repo_path: Path, lang: str) -> str:
    if lang == "Python":
        if (repo_path / "tox.ini").exists() or (repo_path / "pytest.ini").exists():
            return "pytest"
        if list(repo_path.glob("**/test_*.py")):
            return "pytest"
        return "unittest"
    return "unknown"


def mine_repo(repo_url: str, repo_name: str, max_commits: int = 200) -> list[dict]:
    print(f"  Mining {repo_name}...", end=" ", flush=True)
    
    with tempfile.TemporaryDirectory(prefix="lyme-mining-") as tmpdir:
        clone_path = Path(tmpdir) / repo_name
        
        r = subprocess.run(
            ["git", "clone", "--depth", str(max_commits + 10), repo_url, str(clone_path)],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"clone failed: {r.stderr[:60]}")
            return []
        
        lang = detect_lang(clone_path)
        test_fw = detect_test_fw(clone_path, lang)
        
        log = run_git(clone_path, ["log", f"-{max_commits}",
                                   "--format=COMMIT%n%H%n%an%n%ai%n%s%n%B%n---END---"])
        
        all_examples = []
        raw_commits = [x.strip() for x in log.split("---END---") if x.strip()]
        
        for raw in raw_commits:
            lines = raw.split("\n")
            if not lines or lines[0] != "COMMIT":
                continue
            try:
                sha = lines[1]
                if not has_parent_in_repo(clone_path, sha):
                    continue
                date = lines[3]
                subject = lines[4]
                body = "\n".join(lines[5:]).strip()
                
                diff = run_git(clone_path, ["diff", "--diff-filter=AM", f"{sha}^..{sha}"])
                if is_merge(diff):
                    continue
                
                examples = commit_to_examples(sha, subject, body, date, diff, repo_name, lang, test_fw, repo_url)
                all_examples.extend(examples)
            except (IndexError, ValueError):
                continue
        
        print(f"{len(all_examples)} ex")
        return all_examples


def save_splits(all_examples: list[dict]):
    """Group by modality and save train/val/test splits."""
    unique = {}
    for ex in all_examples:
        unique[ex["id"]] = ex
    
    ids = sorted(unique.keys())
    n = len(ids)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    splits = {
        "train": [unique[i] for i in ids[:train_end]],
        "val": [unique[i] for i in ids[train_end:val_end]],
        "test": [unique[i] for i in ids[val_end:]],
    }
    
    for split_name, examples in splits.items():
        split_dir = DATASET_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        
        by_mod = defaultdict(list)
        for ex in examples:
            by_mod[ex["modality"]].append(ex)
        
        for mod, mod_exs in by_mod.items():
            path = split_dir / f"{mod}.jsonl"
            with open(path, "w") as f:
                for ex in mod_exs:
                    f.write(json.dumps(ex) + "\n")
        
        comb_path = split_dir / "combined.jsonl"
        with open(comb_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        
        mod_str = ", ".join(f"{m}={len(v)}" for m, v in sorted(by_mod.items()))
        print(f"    {split_name}: {len(examples)} ex [{mod_str}]")
    
    return splits


def main():
    print("=" * 72)
    print("  Week 42 — Real Repo Task Mining")
    print("=" * 72)
    print()
    
    all_examples = []
    repo_stats = {}
    
    # Mine external repos
    for repo_url, repo_name, license_type in TARGET_REPOS:
        exs = mine_repo(repo_url, repo_name, max_commits=200)
        all_examples.extend(exs)
        repo_stats[repo_name] = len(exs)
    
    print()
    print("  Saving splits...")
    splits = save_splits(all_examples)
    print()
    
    # Generate report
    unique_ids = list(set(e["id"] for e in all_examples))
    
    modality_counts = defaultdict(int)
    task_counts = defaultdict(int)
    diff_counts = defaultdict(int)
    for ex in all_examples:
        modality_counts[ex["modality"]] += 1
        task_counts[ex["metadata"]["task_type"]] += 1
        diff_counts[ex["difficulty"]] += 1
    
    report = [
        "# Week 42 — Real Repo Task Mining Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total examples: {len(all_examples)}",
        f"- Unique examples: {len(unique_ids)}",
        f"- Source repos: {len(repo_stats)}",
        "",
        "## Per-Repo Breakdown",
        "| Repo | Examples |",
        "|------|----------|",
    ]
    for repo, count in sorted(repo_stats.items()):
        report.append(f"| {repo} | {count} |")
    report.append("")
    report.append("## Per-Modality Breakdown")
    report.append("| Modality | Count |")
    report.append("|----------|-------|")
    for mod, count in sorted(modality_counts.items()):
        report.append(f"| {mod} | {count} |")
    report.append("")
    report.append("## Task Type Breakdown")
    report.append("| Task Type | Count |")
    report.append("|-----------|-------|")
    for task, count in sorted(task_counts.items()):
        report.append(f"| {task} | {count} |")
    report.append("")
    report.append("## Difficulty")
    report.append("| Level | Count |")
    report.append("|-------|-------|")
    for d, count in sorted(diff_counts.items()):
        report.append(f"| {d} | {count} |")
    report.append("")
    report.append("## Splits")
    for s in ["train", "val", "test"]:
        report.append(f"- {s}: {len(splits.get(s, []))}")
    report.append("")
    report.append("## Sources")
    for repo_url, repo_name, lic in TARGET_REPOS:
        if repo_stats.get(repo_name, 0) > 0:
            report.append(f"- {repo_name} ({repo_url}) [{lic}]: {repo_stats[repo_name]}")
    
    report_path = REPORT_DIR / "REPO_MINING_REPORT.md"
    report_path.write_text("\n".join(report))
    
    stats = {
        "total": len(all_examples), "unique": len(unique_ids),
        "repos": repo_stats, "modalities": dict(modality_counts),
        "task_types": dict(task_counts), "difficulties": dict(diff_counts),
    }
    with open(REPORT_DIR / "mining_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"  Report: {report_path}")
    print()
    print("=" * 72)
    print(f"  Total: {len(unique_ids)} unique examples")
    for r, c in sorted(repo_stats.items()):
        print(f"    {r}: {c}")
    print(f"  Splits: train={len(splits.get('train',[]))}, val={len(splits.get('val',[]))}, test={len(splits.get('test',[]))}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
