#!/usr/bin/env python3
"""Weeks 88-91 — Specialization Eval Suite.

Evaluates: Diff Discipline v2, Test Repair v2, Bug Localization v2, Multi-File Edit v2.
Produces a combined readiness report for the v2.0 release.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datasets.schema import compute_statistics

REPORT_DIR = Path("lyme-output/weeks88-91")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Specialization data checks ────────────────────────────────────────────────

SPECIALIZATIONS = {
    "diff_discipline": {
        "config": "training/configs/diff_discipline_v2.yaml",
        "checkpoint": "checkpoints/diff_discipline_v2",
        "train_data": "datasets/v2/sft/train/unified_diff.jsonl",
        "metrics": {
            "valid_diff_rate": {"target": 0.90, "description": "Diff parses as valid unified diff"},
            "apply_success_rate": {"target": 0.85, "description": "Patch applies cleanly"},
            "patch_minimality": {"target": 0.80, "description": "Patch only changes necessary lines"},
        },
    },
    "test_repair": {
        "config": "training/configs/test_repair_v2.yaml",
        "checkpoint": "checkpoints/test_repair_v2",
        "train_data": "datasets/v2/sft/train/test_repair.jsonl",
        "metrics": {
            "first_attempt_pass": {"target": 0.70, "description": "First patch passes tests"},
            "second_attempt_pass": {"target": 0.85, "description": "Second patch passes after repair"},
            "regression_rate": {"target": 0.05, "description": "Fix breaks unrelated tests"},
            "patch_size": {"target": 0.75, "description": "Patch is minimal (<= 5 lines)"},
        },
    },
    "bug_localization": {
        "config": "training/configs/bug_localization_v2.yaml",
        "checkpoint": "checkpoints/bug_localization_v2",
        "train_data": "datasets/v2/sft/train/bug_localization.jsonl",
        "metrics": {
            "top1_accuracy": {"target": 0.60, "description": "Correct file:line as top guess"},
            "top3_accuracy": {"target": 0.80, "description": "Correct location in top 3"},
            "wrong_file_rate": {"target": 0.15, "description": "Wrong file identified"},
        },
    },
    "multi_file_edit": {
        "config": "training/configs/multi_file_edit_v2.yaml",
        "checkpoint": "checkpoints/multi_file_edit_v2",
        "train_data": "datasets/v2/sft/train/multi_file_edit.jsonl",
        "metrics": {
            "cross_file_consistency": {"target": 0.75, "description": "Changes across files are consistent"},
            "patch_validity": {"target": 0.85, "description": "All patches apply cleanly"},
            "over_edit_rate": {"target": 0.10, "description": "Unnecessary changes made"},
        },
    },
}


def check_data_availability():
    """Check which specialization data files exist."""
    results = {}
    for spec_name, spec in SPECIALIZATIONS.items():
        spec_result = {"config_ok": False, "data_ok": False, "checkpoint_ok": False, "details": []}

        # Config
        config_path = Path(spec["config"])
        if config_path.exists():
            spec_result["config_ok"] = True
            spec_result["details"].append(f"Config: {spec['config']} ✅")
        else:
            spec_result["details"].append(f"Config: {spec['config']} ❌ NOT FOUND")

        # Train data
        data_path = Path(spec["train_data"])
        if data_path.exists():
            spec_result["data_ok"] = True
            with open(data_path) as f:
                n_lines = sum(1 for _ in f)
            spec_result["details"].append(f"Data: {spec['train_data']} ({n_lines} examples) ✅")
        else:
            spec_result["details"].append(f"Data: {spec['train_data']} ❌ NOT FOUND")

        # Checkpoint
        checkpoint_path = Path(spec["checkpoint"])
        if checkpoint_path.exists():
            spec_result["checkpoint_ok"] = True
            n_ckpt = len(list(checkpoint_path.glob("checkpoint-*")))
            has_final = (checkpoint_path / "final").exists()
            spec_result["details"].append(f"Checkpoint: {spec['checkpoint']} ({n_ckpt} checkpoints, final={'✅' if has_final else '❌'})")
        else:
            spec_result["details"].append(f"Checkpoint: {spec['checkpoint']} ❌ NOT FOUND")

        results[spec_name] = spec_result
    return results


def compute_target_matrix():
    """Build the target improvement matrix."""
    rows = []
    for spec_name, spec in SPECIALIZATIONS.items():
        for metric_name, metric in spec["metrics"].items():
            rows.append({
                "specialization": spec_name,
                "metric": metric_name,
                "target": metric["target"],
                "description": metric["description"],
            })
    return rows


def main():
    print("=" * 72)
    print("  Weeks 88-91 — Specialization Eval Suite")
    print("=" * 72)
    print()

    # 1. Check data, configs, checkpoints
    print("  [1/3] Checking specialization infrastructure...")
    availability = check_data_availability()
    for spec_name, result in sorted(availability.items()):
        status = "✅" if result["config_ok"] and result["data_ok"] else "⚠️"
        print(f"\n  {status} {spec_name}")
        for detail in result["details"]:
            print(f"    {detail}")
    print()

    # 2. Target matrix
    print("  [2/3] Target improvement matrix...")
    targets = compute_target_matrix()
    print(f"    {len(targets)} targets across {len(SPECIALIZATIONS)} specializations")
    for t in targets:
        print(f"    {t['specialization']}.{t['metric']}: target={t['target']} ({t['description']})")
    print()

    # 3. Generate report
    all_ready = all(
        r["config_ok"] and r["data_ok"]
        for r in availability.values()
    )

    report_lines = [
        "# Weeks 88-91 — Specialization Eval Report",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Infrastructure Readiness",
        f"{'✅ ALL SPECIALIZATIONS READY' if all_ready else '⚠️ Some specializations need setup'}",
        "",
    ]
    for spec_name, result in sorted(availability.items()):
        status_icon = "✅" if result["config_ok"] and result["data_ok"] else "⚠️"
        report_lines.append(f"### {spec_name} {status_icon}")
        for detail in result["details"]:
            report_lines.append(f"- {detail}")
        report_lines.append("")

    report_lines.append("## Target Metrics Matrix")
    report_lines.append("| Specialization | Metric | Target | Description |")
    report_lines.append("|---------------|--------|--------|-------------|")
    for t in targets:
        report_lines.append(f"| {t['specialization']} | {t['metric']} | {t['target']} | {t['description']} |")

    report_lines.append("")
    report_lines.append("## Training Order")
    report_lines.append("1. **SFT v2** → base adapter")
    report_lines.append("2. **Diff Discipline v2** → strict patch output (Week 88)")
    report_lines.append("3. **Test Repair v2** → test-driven repair (Week 89)")
    report_lines.append("4. **Bug Localization v2** → find bug location (Week 90)")
    report_lines.append("5. **Multi-File Edit v2** → cross-file changes (Week 91)")
    report_lines.append("")
    report_lines.append("## Run Commands")
    report_lines.append("```bash")
    report_lines.append("# Step 1: SFT v2")
    report_lines.append("python training/scripts/sft_train.py --config training/configs/sft_v2.yaml")
    report_lines.append("")
    report_lines.append("# Step 2: Diff Discipline (uses SFT v2 as base)")
    report_lines.append("python training/scripts/sft_train.py --config training/configs/diff_discipline_v2.yaml")
    report_lines.append("")
    report_lines.append("# Step 3: Test Repair (uses Diff Discipline as base)")
    report_lines.append("python training/scripts/sft_train.py --config training/configs/test_repair_v2.yaml")
    report_lines.append("")
    report_lines.append("# Step 4: Bug Localization (uses SFT v2 as base)")
    report_lines.append("python training/scripts/sft_train.py --config training/configs/bug_localization_v2.yaml")
    report_lines.append("")
    report_lines.append("# Step 5: Multi-File Edit (uses SFT v2 as base)")
    report_lines.append("python training/scripts/sft_train.py --config training/configs/multi_file_edit_v2.yaml")
    report_lines.append("```")

    report_path = REPORT_DIR / "SPECIALIZATION_EVAL_REPORT.md"
    report_path.write_text("\n".join(report_lines))

    structured = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "specializations": availability,
        "targets": targets,
        "all_ready": all_ready,
    }
    with open(REPORT_DIR / "specialization_eval.json", "w") as f:
        json.dump(structured, f, indent=2)

    print(f"  Report: {report_path}")
    print("=" * 72)
    print(f"  {'ALL READY' if all_ready else 'SOME ISSUES'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
