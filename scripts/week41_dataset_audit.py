#!/usr/bin/env python3
"""Week 41: Dataset v1 Audit — Comprehensive audit of all Lyme Model datasets.

Audits:
- counts by modality
- token lengths
- languages
- quality issues (missing fields, format inconsistencies)
- duplicate rate
- missing categories
- train/val/test leakage
- per-file breakdown
"""

import json
import os
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime, timezone

DATASET_DIR = Path("datasets/generated")
REPORT_DIR = Path("lyme-output/week41")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MODALITIES = {
    "repo_qa", "bug_localization", "patch_planning",
    "unified_diff", "test_repair", "tool_use",
    "verification", "refusal",
    "multi_file_edit", "self_repair", "long_horizon_planning",
}

WEEK41_TARGET_CATEGORIES = [
    "repo_qa", "bug_localization", "patch_planning",
    "diff_generation", "test_repair", "tool_use",
    "critique", "multi_file_edit", "self_repair",
    "long_horizon_planning",
]


def find_all_jsonl_files(base_dir: Path) -> list[Path]:
    """Recursively find all JSONL files in the dataset directory."""
    return sorted(base_dir.rglob("*.jsonl"))


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, skipping empty lines."""
    examples = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                data["_line"] = i
                data["_file"] = str(path.relative_to(DATASET_DIR))
                examples.append(data)
            except json.JSONDecodeError as e:
                examples.append({
                    "_error": f"JSONDecodeError at line {i}: {e}",
                    "_file": str(path.relative_to(DATASET_DIR)),
                    "_line": i,
                })
    return examples


def classify_modality(ex: dict) -> str:
    """Classify an example into a modality category."""
    if "modality" in ex and ex["modality"]:
        m = ex["modality"]
        if m in ALLOWED_MODALITIES:
            return m
    if "task_type" in ex:
        t = ex["task_type"]
        if t in ALLOWED_MODALITIES:
            return t
    instruction = (ex.get("instruction") or ex.get("task") or "").lower()
    output = (ex.get("output") or ex.get("response") or ex.get("target_output") or "").lower()
    if "diff" in instruction or "unified diff" in instruction or "--- a/" in output:
        return "unified_diff"
    if "test" in instruction and ("fail" in instruction or "fix" in instruction or "repair" in instruction):
        return "test_repair"
    if "bug" in instruction or "localize" in instruction or "locate" in instruction or "find" in instruction:
        return "bug_localization"
    if "plan" in instruction or "patch plan" in instruction:
        return "patch_planning"
    if "grep_search" in output or "tool" in instruction or "search" in instruction:
        return "tool_use"
    if "review" in instruction or "approve" in instruction or "reject" in instruction:
        return "verification"
    if ("cannot" in output and "not" in output) or "refuse" in instruction or "refusal" in instruction:
        return "refusal"
    if "?" in instruction or "what" in instruction or "how" in instruction or "framework" in instruction:
        return "repo_qa"
    instruction = ex.get("instruction") or ex.get("task") or ""
    if instruction:
        return "repo_qa"
    return "unclassified"


def classify_week41_category(modality: str, ex: dict) -> str:
    """Map modality to Week 41 target categories."""
    instruction = (ex.get("instruction") or ex.get("task") or "").lower()
    output = (ex.get("output") or ex.get("target_output") or "").lower()

    # Try direct mapping first
    mapping = {
        "repo_qa": "repo_qa",
        "bug_localization": "bug_localization",
        "patch_planning": "patch_planning",
        "unified_diff": "diff_generation",
        "test_repair": "test_repair",
        "tool_use": "tool_use",
        "multi_file_edit": "multi_file_edit",
        "self_repair": "self_repair",
        "long_horizon_planning": "long_horizon_planning",
    }
    if modality in mapping:
        return mapping[modality]

    # Check for multi-file edit
    if modality == "tool_use":
        files = ex.get("retrieved_files", [])
        tools = ex.get("tool_outputs", [])
        if len(files) > 2 or any("edit_file" in str(t) for t in tools):
            return "multi_file_edit"

    # Check for critique
    if modality == "verification":
        verdict = ex.get("metadata", {}).get("verdict", "")
        if verdict in ("reject", "approve"):
            return "critique"
        return "critique"

    # Check for self-repair
    if "retry" in instruction or "self" in instruction or "correct" in instruction:
        return "self_repair"

    # Check for long-horizon planning
    if modality == "patch_planning":
        return "long_horizon_planning"

    return modality


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return len(text) // 4


def detect_language(ex: dict) -> str:
    """Detect the programming language from context."""
    rc = ex.get("repo_context", {})
    if isinstance(rc, dict):
        lang = rc.get("language", "")
        if lang:
            return lang
    context = str(ex.get("context", "")) + str(ex.get("instruction", ""))
    for kw, lang in [
        (".py", "Python"), ("python", "Python"),
        (".js", "JavaScript"), (".ts", "TypeScript"), ("typescript", "TypeScript"),
        (".go", "Go"), (".rs", "Rust"), (".java", "Java"),
        (".cpp", "C++"), (".c", "C"), (".rb", "Ruby"),
        (".php", "PHP"), (".swift", "Swift"), (".kt", "Kotlin"),
        (".cs", "C#"), (".r", "R"),
    ]:
        if kw in context.lower():
            return lang
    return "unknown"


def compute_id(ex: dict) -> str:
    """Get or derive a stable ID for dedup."""
    return ex.get("id") or ex.get("_id") or f"{ex.get('_file','')}:{ex.get('_line',0)}"


def audit_single_file(path: Path) -> dict:
    """Audit a single JSONL file."""
    examples = load_jsonl(path)
    total = len(examples)

    errors = [ex for ex in examples if "_error" in ex]
    valid = [ex for ex in examples if "_error" not in ex]

    modalities = Counter()
    week41_categories = Counter()
    difficulties = Counter()
    sources = Counter()
    languages = Counter()
    instruction_lens = []
    target_lens = []
    context_lens = []
    token_estimates = []
    missing_instruction = 0
    missing_output = 0
    missing_modality = 0
    missing_difficulty = 0
    missing_source = 0
    missing_repo_context = 0
    ids = []
    file_paths_seen = Counter()

    for ex in valid:
        mod = classify_modality(ex)
        modalities[mod] += 1
        cat = classify_week41_category(mod, ex)
        week41_categories[cat] += 1

        # Difficulty
        diff = ex.get("difficulty", "")
        if diff in ("trivial", "easy", "medium", "hard", "expert"):
            difficulties[diff] += 1
        elif diff:
            difficulties[f"unknown:{diff}"] += 1
        else:
            difficulties["unset"] += 1
            missing_difficulty += 1

        # Source
        src = ex.get("source", "")
        if src:
            if src in ("synthetic", "lyme_trace", "curated", "augmented", "distilled"):
                sources[src] += 1
            else:
                sources[f"unknown:{src}"] += 1
        else:
            sources["unset"] += 1
            missing_source += 1

        # Language
        lang = detect_language(ex)
        languages[lang] += 1

        # Lengths
        instruction = ex.get("instruction") or ex.get("task") or ""
        target = ex.get("output") or ex.get("target_output") or ex.get("response") or ""
        context = str(ex.get("context", "")) + str(ex.get("repo_context", ""))

        if not instruction:
            missing_instruction += 1
        if not target:
            missing_output += 1

        # Modality
        if "modality" not in ex and "task_type" not in ex:
            missing_modality += 1

        # Repo context
        rc = ex.get("repo_context")
        if not rc and not ex.get("context"):
            missing_repo_context += 1

        instruction_lens.append(len(instruction))
        target_lens.append(len(target))
        context_lens.append(len(context))
        token_estimates.append(estimate_tokens(instruction + target + context))

        # ID tracking
        ex_id = compute_id(ex)
        ids.append(ex_id)

        # File path tracking for uniqueness
        retrieved_files = ex.get("retrieved_files", [])
        for rf in retrieved_files:
            if isinstance(rf, dict):
                fp = rf.get("file_path", "")
                if fp:
                    file_paths_seen[fp] += 1

    # Duplicate analysis
    id_counts = Counter(ids)
    duplicates_by_id = {k: v for k, v in id_counts.items() if v > 1}

    # Format check
    canonical_format = 0
    flat_format = 0
    for ex in valid:
        if "modality" in ex or "repo_context" in ex or "retrieved_files" in ex:
            canonical_format += 1
        if "task_type" in ex:
            flat_format += 1

    return {
        "file": str(path.relative_to(DATASET_DIR)),
        "total": total,
        "valid": len(valid),
        "errors": len(errors),
        "error_details": errors[:5],
        "modalities": dict(modalities),
        "week41_categories": dict(week41_categories),
        "difficulties": dict(difficulties),
        "sources": dict(sources),
        "languages": dict(languages),
        "missing_instruction": missing_instruction,
        "missing_output": missing_output,
        "missing_modality": missing_modality,
        "missing_difficulty": missing_difficulty,
        "missing_source": missing_source,
        "missing_repo_context": missing_repo_context,
        "avg_instruction_len": round(sum(instruction_lens) / len(instruction_lens), 1) if instruction_lens else 0,
        "avg_target_len": round(sum(target_lens) / len(target_lens), 1) if target_lens else 0,
        "avg_context_len": round(sum(context_lens) / len(context_lens), 1) if context_lens else 0,
        "avg_token_estimate": round(sum(token_estimates) / len(token_estimates), 1) if token_estimates else 0,
        "total_tokens_estimated": sum(token_estimates),
        "canonical_format": canonical_format,
        "flat_format": flat_format,
        "duplicate_ids": len(duplicates_by_id),
        "duplicate_id_examples": list(duplicates_by_id.keys())[:10],
        "unique_file_paths": len(file_paths_seen),
    }


def check_train_val_test_leakage(files_by_split: dict[str, list[Path]]) -> dict:
    """Check for leakage between train/val/test splits."""
    split_examples = {}
    for split_name, paths in files_by_split.items():
        examples = []
        for p in paths:
            for ex in load_jsonl(p):
                if "_error" not in ex:
                    ex_id = compute_id(ex)
                    instruction = (ex.get("instruction") or ex.get("task") or "")[:100]
                    examples.append((ex_id, instruction, split_name))
        split_examples[split_name] = examples

    # Check for same instruction across splits
    train_instructions = set()
    leakage_pairs = []
    for ex_id, instr, _ in split_examples.get("train", []):
        train_instructions.add((ex_id, instr))

    for split_name in ["val", "test"]:
        for ex_id, instr, _ in split_examples.get(split_name, []):
            if (ex_id, instr) in train_instructions:
                leakage_pairs.append((split_name, ex_id, instr[:50]))

    return {
        "train_count": len(split_examples.get("train", [])),
        "val_count": len(split_examples.get("val", [])),
        "test_count": len(split_examples.get("test", [])),
        "leakage_count": len(leakage_pairs),
        "leakage_examples": leakage_pairs[:10],
    }


def main():
    print("=" * 72)
    print("  Week 41 — Lyme Model Dataset v1 Audit")
    print("=" * 72)
    print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"  Dataset dir: {DATASET_DIR.resolve()}")
    print()

    all_files = find_all_jsonl_files(DATASET_DIR)
    print(f"  Found {len(all_files)} JSONL files")
    print()

    # Organize files by split
    files_by_split = defaultdict(list)
    other_files = []
    for f in all_files:
        rel = str(f.relative_to(DATASET_DIR))
        if rel.startswith("train/"):
            files_by_split["train"].append(f)
        elif rel.startswith("val/"):
            files_by_split["val"].append(f)
        elif rel.startswith("test/"):
            files_by_split["test"].append(f)
        else:
            other_files.append(f)

    # Audit each file
    all_reports = []
    combined = {
        "modalities": Counter(),
        "week41_categories": Counter(),
        "languages": Counter(),
        "difficulties": Counter(),
        "sources": Counter(),
        "missing_instruction": 0,
        "missing_output": 0,
        "missing_modality": 0,
        "missing_difficulty": 0,
        "missing_source": 0,
        "missing_repo_context": 0,
        "total_valid": 0,
        "total_errors": 0,
        "duplicate_ids": 0,
        "canonical_format": 0,
        "flat_format": 0,
        "instruction_lens": [],
        "target_lens": [],
        "context_lens": [],
        "token_estimates": [],
    }

    for f in all_files:
        report = audit_single_file(f)
        all_reports.append(report)

        combined["total_valid"] += report["valid"]
        combined["total_errors"] += report["errors"]
        combined["missing_instruction"] += report["missing_instruction"]
        combined["missing_output"] += report["missing_output"]
        combined["missing_modality"] += report["missing_modality"]
        combined["missing_difficulty"] += report["missing_difficulty"]
        combined["missing_source"] += report["missing_source"]
        combined["missing_repo_context"] += report["missing_repo_context"]
        combined["duplicate_ids"] += report["duplicate_ids"]
        combined["canonical_format"] += report["canonical_format"]
        combined["flat_format"] += report["flat_format"]

        for k, v in report["modalities"].items():
            combined["modalities"][k] += v
        for k, v in report["week41_categories"].items():
            combined["week41_categories"][k] += v
        for k, v in report["languages"].items():
            combined["languages"][k] += v
        for k, v in report["difficulties"].items():
            combined["difficulties"][k] += v
        for k, v in report["sources"].items():
            combined["sources"][k] += v

        combined["instruction_lens"].append(report["avg_instruction_len"])
        combined["target_lens"].append(report["avg_target_len"])
        combined["context_lens"].append(report["avg_context_len"])
        combined["token_estimates"].append(report["avg_token_estimate"])

    # Leakage analysis
    leakage = check_train_val_test_leakage(files_by_split)

    # Generate REPORT
    report_lines = []
    report_lines.append("# Lyme Model — Dataset v1 Audit Report")
    report_lines.append(f"> Generated: {datetime.now(timezone.utc).isoformat()}")
    report_lines.append(f"> Source: `datasets/generated/` ({len(all_files)} files, {sum(r['total'] for r in all_reports)} lines)")
    report_lines.append("")

    # Section 1: Overview
    report_lines.append("## 1. Overview")
    report_lines.append(f"| Metric | Value |")
    report_lines.append(f"|--------|-------|")
    report_lines.append(f"| Total JSONL files | {len(all_files)} |")
    report_lines.append(f"| Total lines (including empty) | {sum(r['total'] for r in all_reports)} |")
    report_lines.append(f"| Valid examples | {combined['total_valid']} |")
    report_lines.append(f"| Parse errors | {combined['total_errors']} |")
    report_lines.append(f"| Estimated total tokens | {sum(r['total_tokens_estimated'] for r in all_reports):,} |")
    report_lines.append(f"| Canonical format (LymeExample) | {combined['canonical_format']} |")
    report_lines.append(f"| Flat format (legacy) | {combined['flat_format']} |")
    report_lines.append("")

    # Section 2: Counts by Modality
    report_lines.append("## 2. Counts by Modality")
    report_lines.append("| Modality | Count |")
    report_lines.append("|----------|-------|")
    for mod, count in sorted(combined["modalities"].items()):
        report_lines.append(f"| {mod} | {count} |")
    report_lines.append("")

    # Section 3: Week 41 Target Categories
    report_lines.append("## 3. Week 41 Target Categories")
    report_lines.append("| Category | Count |")
    report_lines.append("|----------|-------|")
    for cat in WEEK41_TARGET_CATEGORIES:
        count = combined["week41_categories"].get(cat, 0)
        report_lines.append(f"| {cat} | {count} |")
    report_lines.append("")
    missing_cats = [c for c in WEEK41_TARGET_CATEGORIES if combined["week41_categories"].get(c, 0) == 0]
    if missing_cats:
        report_lines.append(f"**Missing categories:** {', '.join(missing_cats)}")
        report_lines.append("")

    # Section 4: Token lengths
    report_lines.append("## 4. Token Lengths (character-based estimate ÷ 4)")
    report_lines.append("| Metric | Value |")
    report_lines.append("|--------|-------|")
    report_lines.append(f"| Total estimated tokens | {sum(r['total_tokens_estimated'] for r in all_reports):,} |")
    report_lines.append("")

    # Section 5: Languages
    report_lines.append("## 5. Languages Detected")
    report_lines.append("| Language | Count |")
    report_lines.append("|----------|-------|")
    for lang, count in sorted(combined["languages"].items()):
        report_lines.append(f"| {lang} | {count} |")
    report_lines.append("")

    # Section 6: Quality Issues
    report_lines.append("## 6. Quality Issues")
    report_lines.append(f"| Issue | Count |")
    report_lines.append(f"|-------|-------|")
    report_lines.append(f"| Missing instruction | {combined['missing_instruction']} |")
    report_lines.append(f"| Missing output/target | {combined['missing_output']} |")
    report_lines.append(f"| Missing modality | {combined['missing_modality']} |")
    report_lines.append(f"| Missing difficulty | {combined['missing_difficulty']} |")
    report_lines.append(f"| Missing source | {combined['missing_source']} |")
    report_lines.append(f"| Missing repo context | {combined['missing_repo_context']} |")
    report_lines.append(f"| Parse errors | {combined['total_errors']} |")
    report_lines.append("")

    # Section 7: Duplicate rate
    report_lines.append("## 7. Duplicate Rate")
    dup_count = combined["duplicate_ids"]
    total_valid = combined["total_valid"] or 1
    report_lines.append(f"| Metric | Value |")
    report_lines.append(f"|--------|-------|")
    report_lines.append(f"| IDs with duplicates | {dup_count} |")
    report_lines.append(f"| Duplicate rate | {dup_count}/{total_valid} ({100*dup_count/total_valid:.1f}%) |")
    report_lines.append("")

    # Section 8: Train/val/test analysis
    report_lines.append("## 8. Train/Val/Test Split Analysis")
    report_lines.append(f"| Split | Files | Lines |")
    report_lines.append(f"|-------|-------|-------|")
    for split_name in ["train", "val", "test"]:
        sf_count = sum(r["total"] for r in all_reports if r["file"].startswith(split_name + "/"))
        sf_files = len([r for r in all_reports if r["file"].startswith(split_name + "/")])
        report_lines.append(f"| {split_name} | {sf_files} | {sf_count} |")
    report_lines.append(f"")
    report_lines.append(f"**Leakage analysis:**")
    report_lines.append(f"- Training examples: {leakage['train_count']}")
    report_lines.append(f"- Validation examples: {leakage['val_count']}")
    report_lines.append(f"- Test examples: {leakage['test_count']}")
    report_lines.append(f"- Leaked examples (same ID/instr across splits): {leakage['leakage_count']}")
    if leakage["leakage_examples"]:
        report_lines.append(f"- Leakage details:")
        for split, ex_id, instr in leakage["leakage_examples"][:10]:
            report_lines.append(f"  - {split}: id={ex_id}, instr=\"{instr}...\"")
    report_lines.append("")

    # Section 9: Missing categories assessment
    report_lines.append("## 9. Missing Categories Assessment")
    report_lines.append("")
    for cat in WEEK41_TARGET_CATEGORIES:
        count = combined["week41_categories"].get(cat, 0)
        status = "❌ MISSING" if count == 0 else f"✅ {count} examples"
        report_lines.append(f"- **{cat}**: {status}")
    report_lines.append("")

    # Section 10: Per-file breakdown
    report_lines.append("## 10. Per-File Breakdown")
    report_lines.append("| File | Valid | Errors | Modalities | Missing Fields |")
    report_lines.append("|------|-------|--------|------------|---------------|")
    for r in all_reports:
        missing = sum([r["missing_instruction"], r["missing_output"], r["missing_modality"]])
        mods = ", ".join(sorted(r["modalities"].keys())[:3])
        report_lines.append(f"| {r['file']} | {r['valid']} | {r['errors']} | {mods} | {missing} |")
    report_lines.append("")

    # Section 11: Recommendations
    report_lines.append("## 11. Recommendations for Dataset v1")
    report_lines.append("")
    report_lines.append("Based on this audit, Dataset v1 should address:")
    report_lines.append("")
    for cat in missing_cats:
        report_lines.append(f"1. **Add {cat} category** — Zero examples found")
    if combined["flat_format"] > 0:
        report_lines.append(f"2. **Migrate {combined['flat_format']} flat-format examples to canonical LymeExample schema**")
    if combined["missing_modality"] > 0:
        report_lines.append(f"3. **Add modality field to {combined['missing_modality']} examples**")
    if leakage["leakage_count"] > 0:
        report_lines.append(f"4. **Fix {leakage['leakage_count']} train/val/test leakage**")
    if combined["missing_repo_context"] > 0:
        report_lines.append(f"5. **Add repo context to {combined['missing_repo_context']} examples**")
    report_lines.append(f"6. **Expand from {combined['total_valid']:,} to ~10K+ examples with real repo data**")
    report_lines.append(f"7. **Add language metadata to unknown-language examples**")
    report_lines.append("")

    report = "\n".join(report_lines)

    # Write report
    report_path = REPORT_DIR / "DATASET_AUDIT_WEEK41.md"
    report_path.write_text(report)
    print(f"  Report written to: {report_path}")

    # Write machine-readable JSON
    json_path = REPORT_DIR / "dataset_audit.json"
    json_data = {
        "report_time": datetime.now(timezone.utc).isoformat(),
        "total_files": len(all_files),
        "total_lines": sum(r["total"] for r in all_reports),
        "valid_examples": combined["total_valid"],
        "parse_errors": combined["total_errors"],
        "estimated_tokens": sum(r["total_tokens_estimated"] for r in all_reports),
        "modalities": dict(sorted(combined["modalities"].items())),
        "week41_categories": dict(sorted(combined["week41_categories"].items())),
        "languages": dict(sorted(combined["languages"].items())),
        "quality_issues": {
            "missing_instruction": combined["missing_instruction"],
            "missing_output": combined["missing_output"],
            "missing_modality": combined["missing_modality"],
            "missing_difficulty": combined["missing_difficulty"],
            "missing_source": combined["missing_source"],
            "missing_repo_context": combined["missing_repo_context"],
            "parse_errors": combined["total_errors"],
        },
        "duplicate_ids": combined["duplicate_ids"],
        "duplicate_rate_pct": round(100 * combined["duplicate_ids"] / total_valid, 2) if total_valid else 0,
        "leakage": leakage,
        "files": all_reports,
    }
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"  JSON data written to: {json_path}")

    # Print summary
    print()
    print("=" * 72)
    print("  AUDIT SUMMARY")
    print("=" * 72)
    print(f"  Total examples:     {combined['total_valid']:>6}")
    print(f"  Parse errors:        {combined['total_errors']:>6}")
    print(f"  Est. tokens:        {sum(r['total_tokens_estimated'] for r in all_reports):>8,}")
    print(f"  Duplicate rate:     {100*combined['duplicate_ids']/total_valid if total_valid else 0:>5.1f}%")
    print(f"  Leakage count:      {leakage['leakage_count']:>6}")
    print(f"  Missing categories: {len(missing_cats)}")
    print()
    print("  Categories coverage:")
    for cat in WEEK41_TARGET_CATEGORIES:
        count = combined["week41_categories"].get(cat, 0)
        indicator = "✅" if count > 0 else "❌"
        print(f"    {indicator} {cat}: {count}")
    print()
    print("  Quality issues:")
    print(f"    Missing instruction:  {combined['missing_instruction']}")
    print(f"    Missing output:       {combined['missing_output']}")
    print(f"    Missing modality:     {combined['missing_modality']}")
    print(f"    Missing difficulty:   {combined['missing_difficulty']}")
    print(f"    Missing source:       {combined['missing_source']}")
    print(f"    Missing repo context: {combined['missing_repo_context']}")
    print(f"    Flat format (legacy): {combined['flat_format']}")
    print()
    print(f"  Full report: {report_path}")
    print(f"  Full JSON:   {json_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
