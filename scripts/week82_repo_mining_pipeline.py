#!/usr/bin/env python3
"""Week 82 — Public Repo Mining Pipeline v2.

Mines commits from public repos and converts them to LymeModel Dataset v2 examples.
Outputs JSONL in v2 schema format with quality filtering, dedup, and leakage prevention.
"""

import json
import re
import subprocess
import tempfile
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datasets.schema import LymeExample, RepoContext, RetrievedFile, VALID_MODALITIES

DATASET_DIR = Path("datasets/v2")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
MINED_DIR = DATASET_DIR / "mined"
MINED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path("lyme-output/week82")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Repo Registry ──────────────────────────────────────────────────────────────
# (url, name, license, language, categories)
REPOS = [
    # ── Python (10 repos) ──
    ("https://github.com/pallets/flask", "flask", "BSD-3-Clause", "Python", ["web"]),
    ("https://github.com/psf/requests", "requests", "Apache-2.0", "Python", ["networking"]),
    ("https://github.com/tiangolo/fastapi", "fastapi", "MIT", "Python", ["web"]),
    ("https://github.com/pytest-dev/pytest", "pytest", "MIT", "Python", ["testing"]),
    ("https://github.com/python/cpython", "cpython", "Python-2.0", "Python", ["language"]),
    ("https://github.com/django/django", "django", "BSD-3-Clause", "Python", ["web"]),
    ("https://github.com/tox-dev/tox", "tox", "MIT", "Python", ["testing"]),
    ("https://github.com/psf/black", "black", "MIT", "Python", ["formatting"]),
    ("https://github.com/pypa/pip", "pip", "MIT", "Python", ["packaging"]),
    ("https://github.com/kedro-org/kedro", "kedro", "Apache-2.0", "Python", ["data-pipeline"]),

    # ── JavaScript/TypeScript (6 repos) ──
    ("https://github.com/expressjs/express", "express", "MIT", "JavaScript", ["web"]),
    ("https://github.com/lodash/lodash", "lodash", "MIT", "JavaScript", ["utility"]),
    ("https://github.com/mochajs/mocha", "mocha", "MIT", "JavaScript", ["testing"]),
    ("https://github.com/vercel/next.js", "next.js", "MIT", "TypeScript", ["web"]),
    ("https://github.com/sveltejs/svelte", "svelte", "MIT", "TypeScript", ["framework"]),
    ("https://github.com/prettier/prettier", "prettier", "MIT", "TypeScript", ["formatting"]),

    # ── Rust (4 repos) ──
    ("https://github.com/rust-lang/regex", "regex", "MIT/Apache-2.0", "Rust", ["text"]),
    ("https://github.com/serde-rs/serde", "serde", "MIT/Apache-2.0", "Rust", ["serialization"]),
    ("https://github.com/clap-rs/clap", "clap", "MIT/Apache-2.0", "Rust", ["cli"]),
    ("https://github.com/rust-lang/rustfmt", "rustfmt", "MIT/Apache-2.0", "Rust", ["formatting"]),

    # ── Go (4 repos) ──
    ("https://github.com/gorilla/mux", "mux", "BSD-3-Clause", "Go", ["web"]),
    ("https://github.com/golang-jwt/jwt", "jwt", "MIT", "Go", ["auth"]),
    ("https://github.com/golang/go", "go", "BSD-3-Clause", "Go", ["language"]),
    ("https://github.com/prometheus/client_golang", "prometheus-client", "Apache-2.0", "Go", ["monitoring"]),

    # ── Java (3 repos) ──
    ("https://github.com/spring-projects/spring-boot", "spring-boot", "Apache-2.0", "Java", ["web"]),
    ("https://github.com/google/gson", "gson", "Apache-2.0", "Java", ["serialization"]),
    ("https://github.com/junit-team/junit5", "junit5", "EPL-2.0", "Java", ["testing"]),

    # ── C/C++ (3 repos) ──
    ("https://github.com/nlohmann/json", "json", "MIT", "C++", ["serialization"]),
    ("https://github.com/microsoft/STL", "msft-stl", "Apache-2.0", "C++", ["stdlib"]),
    ("https://github.com/libuv/libuv", "libuv", "MIT", "C", ["io"]),

    # ── Ruby (2 repos) ──
    ("https://github.com/rails/rails", "rails", "MIT", "Ruby", ["web"]),
    ("https://github.com/ruby/ruby", "ruby", "Ruby", "Ruby", ["language"]),

    # ── Shell/Bash (1 repo) ──
    ("https://github.com/nvm-sh/nvm", "nvm", "MIT", "Shell", ["tooling"]),
]

# ─── Rejection Patterns ─────────────────────────────────────────────────────────
GENERATED_FILE_PATTERNS = [
    r'\.min\.(js|css)$',
    r'(^|/)dist/',
    r'(^|/)build/',
    r'(^|/)gen/',
    r'(^|/)generated/',
    r'(^|/)vendor/',
    r'(^|/)node_modules/',
    r'(^|/)\.next/',
    r'(^|/)target/',
    r'(^|/)__pycache__/',
    r'(^|/)\.eggs/',
    r'(^|/)\.tox/',
    r'(^|/)venv/',
    r'\.pb\.(go|py)$',
    r'_pb2\.py$',
    r'\.grpc\.py$',
    r'package-lock\.json$',
    r'yarn\.lock$',
    r'pnpm-lock\.yaml$',
    r'poetry\.lock$',
    r'Cargo\.lock$',
    r'go\.sum$',
    r'\.svg$',
    r'\.png$',
    r'\.jpg$',
    r'\.ico$',
    r'\.woff2?$',
    r'\.eot$',
    r'\.ttf$',
]

SECRET_PATTERNS = [
    r'(?i)(password|secret|api_key|apikey|token|credential)\s*[:=]\s*["\']?[^\s"\']{8,}["\']?',
    r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
    r'(?i)(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36}',
    r'AKIA[0-9A-Z]{16}',
    r'sk-[0-9a-zA-Z]{32,}',
]

VENDOR_DIR_PATTERNS = [
    r'(^|/)vendor/',
    r'(^|/)third_party/',
    r'(^|/)third-party/',
    r'(^|/)3rdparty/',
    r'(^|/)extern/',
    r'(^|/)deps/',
]


def is_generated_file(filepath: str) -> bool:
    for p in GENERATED_FILE_PATTERNS:
        if re.search(p, filepath):
            return True
    return False


def is_vendored(filepath: str) -> bool:
    for p in VENDOR_DIR_PATTERNS:
        if re.search(p, filepath):
            return True
    return False


def contains_secrets(content: str) -> bool:
    for p in SECRET_PATTERNS:
        if re.search(p, content):
            return True
    return False


def run_git(repo_path, args, timeout=30):
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True,
            cwd=str(repo_path), timeout=timeout
        )
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        return ""


def parse_diffstat(diff: str) -> Dict:
    files = set()
    adds = dels = 0
    for line in diff.split("\n"):
        if line.startswith("--- a/"):
            files.add(line[6:])
        elif line.startswith("+++ b/"):
            files.add(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            adds += 1
        elif line.startswith("-") and not line.startswith("---"):
            dels += 1
    return {
        "files_changed": len(files),
        "files": sorted(files)[:15],
        "additions": adds,
        "deletions": dels,
    }


def classify_commit(msg: str, body: str, stat: Dict) -> str:
    m = msg.lower()
    mb = (msg + " " + body).lower()

    if ("test" in m and ("fix" in m or "update" in m or "repair" in m or "broken" in m)):
        return "fix_test"
    if "fix" in m or "bug" in m or "hotfix" in m or "patch" in m:
        return "bug_fix"
    if "fix" in m and ("typo" in m or "lint" in m or "spelling" in m):
        return "small_fix"
    if "refactor" in m or "clean" in m or "reorganize" in m:
        return "refactor"
    if "dep" in m or "bump" in m or "version" in m or "requirements" in m:
        return "dep_update"
    if "config" in m or "setting" in m or "configure" in m:
        return "config_change"
    if ("test" in m and ("add" in m or "cover" in m or "write" in m)):
        return "add_test"
    if "migrate" in m or "migration" in m:
        return "migration"
    if stat["files_changed"] <= 2 and stat["additions"] <= 20 and stat["deletions"] <= 20:
        return "small_fix"
    if "add" in m or "feat" in m or "implement" in m or "introduce" in m:
        return "feature"
    if "update" in m or "improve" in m or "better" in m:
        return "update"
    if "remove" in m or "delete" in m or "drop" in m:
        return "cleanup"
    if "typo" in m or "spelling" in m or "lint" in m:
        return "small_fix"
    return "other"


def extract_verification_hints(msg: str, body: str, files: List[str]) -> Dict:
    mb = (msg + " " + body).lower()
    hints = {"cmd": "", "frameworks": []}
    if "pytest" in mb or "tox" in mb:
        hints["cmd"] = "pytest"
        hints["frameworks"].append("pytest")
    elif "npm test" in mb or "jest" in mb or "mocha" in mb:
        hints["cmd"] = "npm test"
        hints["frameworks"].append("jest")
    elif "cargo test" in mb:
        hints["cmd"] = "cargo test"
        hints["frameworks"].append("cargo-test")
    elif "go test" in mb:
        hints["cmd"] = "go test"
        hints["frameworks"].append("go-test")
    elif "mvn test" in mb:
        hints["cmd"] = "mvn test"
        hints["frameworks"].append("maven")
    for f in files:
        if f.endswith(".py") and hints["cmd"] == "":
            hints["cmd"] = "pytest"
            hints["frameworks"].append("pytest")
        elif f.endswith((".js", ".ts")) and hints["cmd"] == "":
            hints["cmd"] = "npm test"
            hints["frameworks"].append("node")
        elif f.endswith(".rs") and hints["cmd"] == "":
            hints["cmd"] = "cargo test"
            hints["frameworks"].append("cargo-test")
        elif f.endswith(".go") and hints["cmd"] == "":
            hints["cmd"] = "go test"
            hints["frameworks"].append("go-test")
    return hints


def extract_issue_refs(msg: str, body: str) -> List[str]:
    refs = []
    for word in (msg + " " + body).split():
        if re.match(r'^#[0-9]{1,6}$', word):
            refs.append(word)
    return refs


def should_reject_commit(diff: str, files: List[str], msg: str, body: str) -> Optional[str]:
    stat = parse_diffstat(diff)

    # Giant diffs
    if stat["additions"] + stat["deletions"] > 500:
        return "giant_diff"
    if stat["files_changed"] > 15:
        return "too_many_files"
    if stat["additions"] == 0:
        return "no_additions"

    # Generated files
    for f in files:
        if is_generated_file(f):
            return "generated_file"
        if is_vendored(f):
            return "vendored_code"

    # Secrets in diff content
    if contains_secrets(diff):
        return "contains_secrets"
    if contains_secrets(msg + " " + body):
        return "contains_secrets"

    return None


def file_role(filepath: str) -> str:
    lp = filepath.lower()
    if "test" in lp or "spec" in lp or lp.endswith("_test.go") or lp.endswith(".test."):
        return "test"
    if "config" in lp or "setting" in lp or lp.endswith(".cfg") or lp.endswith(".ini"):
        return "config"
    if "doc" in lp or "readme" in lp or "changelog" in lp:
        return "docs"
    return "source"


def commit_to_examples(
    sha: str, subject: str, body: str, date: str, diff: str,
    repo_name: str, lang: str, repo_url: str, repo_license: str, categories: List[str]
) -> List[Dict]:
    stat = parse_diffstat(diff)
    ct = classify_commit(subject, body, stat)
    if ct == "other":
        return []

    reject_reason = should_reject_commit(diff, stat["files"], subject, body)
    if reject_reason:
        return []

    issue_refs = extract_issue_refs(subject, body)
    verif_hints = extract_verification_hints(subject, body, stat["files"])

    # Determine modality from commit type
    modality_map = {
        "bug_fix": "unified_diff",
        "fix_test": "test_repair",
        "config_change": "patch_planning",
        "feature": "unified_diff",
        "refactor": "unified_diff",
        "small_fix": "unified_diff",
        "update": "unified_diff",
        "dep_update": "patch_planning",
        "add_test": "test_repair",
        "cleanup": "unified_diff",
        "migration": "multi_file_edit",
    }
    modality = modality_map.get(ct, "unified_diff")

    if 2 <= stat["files_changed"] <= 5 and modality == "unified_diff":
        modality = "multi_file_edit"

    difficulty = "easy"
    if stat["additions"] >= 30 or stat["files_changed"] >= 4:
        difficulty = "medium"
    if stat["additions"] >= 80 or stat["files_changed"] >= 8:
        difficulty = "hard"

    files_json = []
    for f in stat["files"][:5]:
        files_json.append(RetrievedFile(
            file_path=f,
            role=file_role(f),
            content_preview=f"Modified in {sha[:12]}",
            lines=stat["additions"] + stat["deletions"],
        ).to_dict())

    instruction = subject
    if body and body.strip() != subject:
        b = body[:800].strip()
        if b:
            instruction += f"\n\n{b}"

    example = LymeExample(
        id=f"mined-{repo_name}-{sha[:12]}",
        modality=modality,
        created=date,
        source="mined",
        source_trace_id=f"commit:{sha}",
        difficulty=difficulty,
        instruction=instruction,
        repo_context=RepoContext(
            repo_name=repo_name,
            language=lang,
            framework=categories[0] if categories else "",
            conventions=[repo_license],
        ),
        retrieved_files=[RetrievedFile.from_dict(f) for f in files_json],
        target_output=diff[:6000],
        language=lang,
        metadata={
            "task_type": ct,
            "commit_sha": sha,
            "files_changed": stat["files_changed"],
            "additions": stat["additions"],
            "deletions": stat["deletions"],
            "source_repo": repo_name,
            "source_url": repo_url,
            "license": repo_license,
            "categories": categories,
            "verification_hints": verif_hints,
            "issue_refs": issue_refs,
            "source": "mined",
        },
    )
    return [example.to_dict()]


def mine_repo(
    repo_url: str, repo_name: str, language: str,
    license_type: str, categories: List[str],
    max_commits: int = 500
) -> List[Dict]:
    print(f"  [mine] {repo_name} ({language})...", end=" ", flush=True)
    with tempfile.TemporaryDirectory(prefix="lyme-mine-") as tmpdir:
        clone_path = Path(tmpdir) / repo_name
        r = subprocess.run(
            ["git", "clone", "--depth", str(max_commits + 20),
             repo_url, str(clone_path)],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode != 0:
            print(f"clone FAILED: {r.stderr[:100]}")
            return []

        log = run_git(clone_path, [
            "log", f"-{max_commits}",
            "--format=COMMIT%n%H%n%an%n%ai%n%s%n%B%n---END---"
        ], timeout=60)
        if not log:
            print("no log")
            return []

        all_examples = []
        seen_ids = set()
        for raw in [x.strip() for x in log.split("---END---") if x.strip()]:
            lines = raw.split("\n")
            if not lines or lines[0] != "COMMIT":
                continue
            try:
                sha = lines[1]
                has_parent = run_git(clone_path, ["rev-parse", f"{sha}^"], timeout=5).strip()
                if not has_parent:
                    continue
                date = lines[3]
                subject = lines[4]
                body = "\n".join(lines[5:]).strip()
                diff = run_git(clone_path, ["diff", "--diff-filter=AM", f"{sha}^..{sha}"], timeout=30)
                if not diff.strip():
                    continue
                examples = commit_to_examples(
                    sha, subject, body, date, diff,
                    repo_name, language, repo_url,
                    license_type, categories,
                )
                for ex in examples:
                    if ex["id"] not in seen_ids:
                        all_examples.append(ex)
                        seen_ids.add(ex["id"])
            except (IndexError, ValueError):
                continue

        print(f"{len(all_examples)} ex")
        return all_examples


def deduplicate_by_hash(examples: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for ex in examples:
        h = hashlib.md5(ex["target_output"][:200].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(ex)
    return unique


def save_splits(all_examples: List[Dict]):
    unique = deduplicate_by_hash(all_examples)
    print(f"\n  Dedup: {len(all_examples)} → {len(unique)}")

    # Per-repo dedup (leakage prevention: entire repo goes to one split)
    by_repo = defaultdict(list)
    for ex in unique:
        repo = ex["metadata"]["source_repo"]
        by_repo[repo].append(ex)

    # Sort repos, assign to train/val/test
    repo_names = sorted(by_repo.keys())
    n = len(repo_names)
    train_repos = repo_names[:int(n * 0.80)]
    val_repos = repo_names[int(n * 0.80):int(n * 0.90)]
    test_repos = repo_names[int(n * 0.90):]

    splits = {"train": [], "val": [], "test": []}
    repo_splits = {}
    for r in train_repos:
        splits["train"].extend(by_repo[r])
        repo_splits[r] = "train"
    for r in val_repos:
        splits["val"].extend(by_repo[r])
        repo_splits[r] = "val"
    for r in test_repos:
        splits["test"].extend(by_repo[r])
        repo_splits[r] = "test"

    for split_name, examples in splits.items():
        split_dir = MINED_DIR / split_name
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
        print(f"  {split_name}: {len(examples)} [{mod_str}]")

    leak_check_file = REPORT_DIR / "leak_check.txt"
    with open(leak_check_file, "w") as f:
        f.write("Leak Check: Repo-to-Split Assignment\n")
        f.write("=" * 50 + "\n")
        for repo, split in sorted(repo_splits.items()):
            f.write(f"  {repo}: {split} ({len(by_repo[repo])} ex)\n")
    print(f"  Leak check: {leak_check_file}")

    return splits


def generate_report(all_examples: List[Dict], repo_stats: Dict):
    unique = deduplicate_by_hash(all_examples)

    modality_counts = defaultdict(int)
    task_counts = defaultdict(int)
    lang_counts = defaultdict(int)
    diff_counts = defaultdict(int)
    for ex in unique:
        modality_counts[ex["modality"]] += 1
        task_counts[ex["metadata"]["task_type"]] += 1
        lang_counts[ex.get("language", ex["repo_context"]["language"])] += 1
        diff_counts[ex["metadata"]["difficulty"]] += 1

    report_lines = [
        "# Week 82 — Public Repo Mining Pipeline Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Total examples mined: {len(all_examples)}",
        f"- Unique examples (after dedup): {len(unique)}",
        f"- Source repos: {len([r for r, c in repo_stats.items() if c > 0])}",
        f"- Languages: {len(lang_counts)}",
        "",
        "## Per-Repo Breakdown",
    ]
    for repo, count in sorted(repo_stats.items()):
        status = "OK" if count > 0 else "FAILED/empty"
        report_lines.append(f"- {repo}: {count} ({status})")

    report_lines.append("")
    report_lines.append("## Languages")
    for lang, count in sorted(lang_counts.items()):
        report_lines.append(f"- {lang}: {count}")

    report_lines.append("")
    report_lines.append("## Modalities")
    for mod, count in sorted(modality_counts.items()):
        report_lines.append(f"- {mod}: {count}")

    report_lines.append("")
    report_lines.append("## Task Types")
    for task, count in sorted(task_counts.items()):
        report_lines.append(f"- {task}: {count}")

    report_lines.append("")
    report_lines.append("## Difficulty Distribution")
    for d, count in sorted(diff_counts.items()):
        report_lines.append(f"- {d}: {count}")

    report_path = REPORT_DIR / "MINING_REPORT.md"
    report_path.write_text("\n".join(report_lines))

    stats = {
        "total": len(all_examples),
        "unique": len(unique),
        "repos": repo_stats,
        "modalities": dict(modality_counts),
        "task_types": dict(task_counts),
        "languages": dict(lang_counts),
        "difficulties": dict(diff_counts),
    }
    with open(REPORT_DIR / "mining_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n  Report: {report_path}")
    print(f"  Stats: {REPORT_DIR / 'mining_stats.json'}")

    return stats


def main():
    print("=" * 72)
    print("  Week 82 — Public Repo Mining Pipeline v2")
    print(f"  {len(REPOS)} repos across 8 languages")
    print("=" * 72)
    print()

    all_examples = []
    repo_stats: Dict[str, int] = {}

    for repo_url, repo_name, license_type, language, categories in REPOS:
        exs = mine_repo(repo_url, repo_name, language, license_type, categories)
        all_examples.extend(exs)
        repo_stats[repo_name] = len(exs)

    print(f"\n  Total mined: {len(all_examples)} raw examples")
    print(f"  Saving splits (per-repo isolation)...")
    splits = save_splits(all_examples)
    print(f"\n  Generating report...")
    stats = generate_report(all_examples, repo_stats)

    print()
    print("=" * 72)
    print(f"  Week 82 Complete")
    print(f"  Mined: {len(all_examples)} raw → {stats['unique']} unique")
    print(f"  Output: {MINED_DIR}/")
    print(f"  Langs: {', '.join(sorted(stats['languages'].keys()))}")
    print(f"  Modalities: {', '.join(sorted(stats['modalities'].keys()))}")
    print("=" * 72)

    return stats


if __name__ == "__main__":
    main()
