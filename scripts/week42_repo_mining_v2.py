#!/usr/bin/env python3
"""Week 42 — Real Repo Task Mining v2 (extended repos + task types)."""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DATASET_DIR = Path("datasets/generated/real_repo")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week42")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPOS = [
    # Python
    ("https://github.com/pallets/flask", "flask", "BSD-3-Clause", "Python"),
    ("https://github.com/psf/requests", "requests", "Apache-2.0", "Python"),
    ("https://github.com/tiangolo/fastapi", "fastapi", "MIT", "Python"),
    ("https://github.com/pallets/click", "click", "BSD-3-Clause", "Python"),
    ("https://github.com/tox-dev/tox", "tox", "MIT", "Python"),
    ("https://github.com/pytest-dev/pytest", "pytest", "MIT", "Python"),
    ("https://github.com/microsoft/pyright", "pyright", "MIT", "Python"),
    # JavaScript/TypeScript
    ("https://github.com/expressjs/express", "express", "MIT", "JavaScript"),
    ("https://github.com/lodash/lodash", "lodash", "MIT", "JavaScript"),
    ("https://github.com/mochajs/mocha", "mocha", "MIT", "JavaScript"),
    # Rust
    ("https://github.com/rust-lang/regex", "regex", "MIT/Apache-2.0", "Rust"),
    ("https://github.com/serde-rs/serde", "serde", "MIT/Apache-2.0", "Rust"),
    # Go
    ("https://github.com/gorilla/mux", "mux", "BSD-3-Clause", "Go"),
    ("https://github.com/golang-jwt/jwt", "jwt", "MIT", "Go"),
]

def run_git(repo_path, args):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(repo_path), timeout=30)
        return r.stdout
    except:
        return ""

def parse_diffstat(diff):
    files = set()
    adds = dels = 0
    for line in diff.split("\n"):
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            files.add(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            adds += 1
        elif line.startswith("-") and not line.startswith("---"):
            dels += 1
    return {"files_changed": len(files), "files": sorted(files)[:10], "additions": adds, "deletions": dels}

def classify_commit(msg, body, stat):
    m = msg.lower()
    mb = (msg + " " + body).lower()
    if "fix" in m or "bug" in m or "hotfix" in m or "patch" in m:
        return "bug_fix"
    if ("test" in m and ("fix" in m or "update" in m or "repair" in m)):
        return "fix_test"
    if "refactor" in m or "clean" in m or "rename" in m or "move" in m:
        return "refactor"
    if "dep" in m or "bump" in m or "version" in m or "requirements" in m:
        return "dep_update"
    if "config" in m or "migrate" in m or "setting" in m:
        return "config_change"
    if ("test" in m and ("add" in m or "cover" in m)):
        return "add_test"
    if stat["files_changed"] <= 2 and stat["additions"] <= 20:
        return "small_fix"
    if "add" in m or "feat" in m or "implement" in m:
        return "feature"
    if "update" in m or "improve" in m:
        return "update"
    if "remove" in m or "delete" in m or "drop" in m:
        return "cleanup"
    if "todo" in mb or "issue" in mb or "fixme" in mb:
        return "small_fix"
    if "typo" in m or "spelling" in m or "lint" in m:
        return "small_fix"
    return "other"

def is_merge(diff):
    return diff.strip() == ""

def extract_single_file_diffs(diff):
    files = []
    current_file = None
    current_diff = []
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_diff:
                files.append({"file": current_file, "diff": "\n".join(current_diff)})
            current_file = None
            current_diff = []
        elif line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if current_file is not None:
            current_diff.append(line)
    if current_file and current_diff:
        files.append({"file": current_file, "diff": "\n".join(current_diff)})
    return files

def extract_verification_cmd(msg, body, files):
    """Try to extract a verification command for the task."""
    mb = (msg + " " + body).lower()
    if "pytest" in mb or "test" in files:
        return "pytest"
    if "npm test" in mb or "package.json" in files:
        return "npm test"
    if "cargo test" in mb or "Cargo.toml" in files:
        return "cargo test"
    if "go test" in mb:
        return "go test"
    if "tox" in mb:
        return "tox"
    # Guess from file paths
    for f in files:
        if f.startswith("test") or "/test" in f:
            return "pytest" if f.endswith(".py") else ("npm test" if f.endswith(".js") else "cargo test")
    return ""

def commit_to_examples(sha, subject, body, date, diff, repo_name, lang, repo_url):
    stat = parse_diffstat(diff)
    ct = classify_commit(subject, body, stat)
    if ct == "other":
        return []
    if stat["additions"] == 0:
        return []
    if stat["additions"] + stat["deletions"] > 400:
        return []

    task = subject
    if body and body.strip() != subject:
        b = body[:600].strip()
        if b:
            task += f"\n\n{b}"

    files_changed = stat["files"]
    mod_map = {
        "bug_fix": ("unified_diff", "Fix bug"),
        "fix_test": ("test_repair", "Fix test"),
        "config_change": ("patch_planning", "Change config"),
        "feature": ("unified_diff", "Add feature"),
        "refactor": ("unified_diff", "Refactor"),
        "small_fix": ("unified_diff", "Small fix"),
        "update": ("unified_diff", "Update"),
        "dep_update": ("patch_planning", "Update dependency"),
        "add_test": ("test_repair", "Add test"),
        "cleanup": ("unified_diff", "Clean up"),
    }
    modality, prefix = mod_map.get(ct, ("unified_diff", "Change"))
    verif_cmd = extract_verification_cmd(subject, body, files_changed)

    files_json = []
    for f in files_changed[:5]:
        role = "test" if "test" in f.lower() else "source"
        files_json.append({
            "file_path": f, "role": role,
            "content_preview": f"Modified in {repo_name}@{sha[:12]}",
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
            "repo_name": repo_name, "language": lang,
            "file_count": 0, "total_lines": 0, "test_count": 0,
            "test_framework": "", "architecture_summary": "", "conventions": [],
        },
        "retrieved_files": files_json,
        "tool_outputs": [],
        "target_output": diff[:3000],
        "metadata": {
            "task_type": ct, "commit_sha": sha, "files_changed": stat["files_changed"],
            "additions": stat["additions"], "deletions": stat["deletions"],
            "source_repo": repo_name, "source_url": repo_url,
            "verification_cmd": verif_cmd,
        },
    }
    examples = [example]

    per_file_diffs = extract_single_file_diffs(diff)
    if len(per_file_diffs) > 1:
        for i, pf in enumerate(per_file_diffs):
            pf_stat = parse_diffstat(pf["diff"])
            if pf_stat["additions"] == 0:
                continue
            pf_verif = extract_verification_cmd(subject, body, [pf["file"]])
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
                    "verification_cmd": pf_verif,
                    "single_file": True,
                },
            }
            examples.append(ex)
    return examples

def detect_lang(repo_path, lang_hint):
    if lang_hint != "unknown":
        return lang_hint
    if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
        return "Python"
    if (repo_path / "Cargo.toml").exists():
        return "Rust"
    if (repo_path / "go.mod").exists():
        return "Go"
    if (repo_path / "package.json").exists():
        return "JavaScript"
    return "unknown"

def mine_repo(repo_url, repo_name, language, max_commits=200):
    print(f"  Mining {repo_name} ({language})...", end=" ", flush=True)
    with tempfile.TemporaryDirectory(prefix="lyme-mining-") as tmpdir:
        clone_path = Path(tmpdir) / repo_name
        r = subprocess.run(
            ["git", "clone", "--depth", str(max_commits + 10), repo_url, str(clone_path)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"clone failed: {r.stderr[:80]}")
            return []
        lang = detect_lang(clone_path, language)
        log = run_git(clone_path, ["log", f"-{max_commits}", "--format=COMMIT%n%H%n%an%n%ai%n%s%n%B%n---END---"])
        all_examples = []
        for raw in [x.strip() for x in log.split("---END---") if x.strip()]:
            lines = raw.split("\n")
            if not lines or lines[0] != "COMMIT":
                continue
            try:
                sha = lines[1]
                r2 = subprocess.run(["git", "rev-parse", f"{sha}^"], capture_output=True, cwd=str(clone_path), timeout=5)
                if r2.returncode != 0:
                    continue
                date = lines[3]; subject = lines[4]; body = "\n".join(lines[5:]).strip()
                diff = run_git(clone_path, ["diff", "--diff-filter=AM", f"{sha}^..{sha}"])
                if is_merge(diff):
                    continue
                examples = commit_to_examples(sha, subject, body, date, diff, repo_name, lang, repo_url)
                all_examples.extend(examples)
            except (IndexError, ValueError):
                continue
        print(f"{len(all_examples)} ex")
        return all_examples

def save_splits(all_examples):
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
            with open(split_dir / f"{mod}.jsonl", "w") as f:
                for ex in mod_exs:
                    f.write(json.dumps(ex) + "\n")
        with open(split_dir / "combined.jsonl", "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        mod_str = ", ".join(f"{m}={len(v)}" for m, v in sorted(by_mod.items()))
        print(f"    {split_name}: {len(examples)} ex [{mod_str}]")
    return splits

def main():
    print("=" * 72)
    print("  Week 42 — Real Repo Task Mining v2")
    print("=" * 72)
    print()
    all_examples = []
    repo_stats = {}
    for repo_url, repo_name, license_type, language in REPOS:
        exs = mine_repo(repo_url, repo_name, language, max_commits=300)
        all_examples.extend(exs)
        repo_stats[repo_name] = len(exs)
    print("\n  Saving splits...")
    splits = save_splits(all_examples)
    print()
    unique_ids = list(set(e["id"] for e in all_examples))
    modality_counts = defaultdict(int)
    task_counts = defaultdict(int)
    lang_counts = defaultdict(int)
    for ex in all_examples:
        modality_counts[ex["modality"]] += 1
        task_counts[ex["metadata"]["task_type"]] += 1
        lang_counts[ex["repo_context"]["language"]] += 1

    report = [
        "# Week 42 — Real Repo Task Mining v2 Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total examples: {len(all_examples)}",
        f"- Unique examples: {len(unique_ids)}",
        f"- Source repos: {len(repo_stats)}",
        "",
        "## Per-Repo Breakdown",
    ]
    for repo, count in sorted(repo_stats.items()):
        report.append(f"- {repo}: {count}")
    report.append("")
    report.append("## Languages")
    for lang, count in sorted(lang_counts.items()):
        report.append(f"- {lang}: {count}")
    report.append("")
    report.append("## Modalities")
    for mod, count in sorted(modality_counts.items()):
        report.append(f"- {mod}: {count}")
    report.append("")
    report.append("## Task Types")
    for task, count in sorted(task_counts.items()):
        report.append(f"- {task}: {count}")
    report.append("")
    report_path = REPORT_DIR / "REPO_MINING_V2_REPORT.md"
    report_path.write_text("\n".join(report))
    stats = {"total": len(all_examples), "unique": len(unique_ids), "repos": repo_stats, "modalities": dict(modality_counts), "task_types": dict(task_counts), "languages": dict(lang_counts)}
    with open(REPORT_DIR / "mining_v2_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Report: {report_path}")
    print("=" * 72)
    print(f"  Total: {len(unique_ids)} unique examples")
    for r, c in sorted(repo_stats.items()):
        print(f"    {r}: {c}")
    print(f"  Output: {DATASET_DIR}/")
    print("=" * 72)

if __name__ == "__main__":
    main()
