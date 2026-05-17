#!/usr/bin/env python3
"""Quality filter for Dataset v2 examples.

Applies mandatory and modality-specific filters to ensure
only high-quality examples pass through to the final dataset.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from datasets.schema import LymeExample, VALID_MODALITIES

# ─── Exclusion Patterns ─────────────────────────────────────────────────────────

PLACEHOLDER_PATTERNS = [
    r'TODO',
    r'FIXME',
    r'XXX',
    r'Lorem ipsum',
    r'example\.com',
    r'placeholder',
    r'change_this',
    r'your-code-here',
]

SECRET_PATTERNS = [
    r'(?i)(password|secret|api_key|apikey|token|credential)\s*[:=]\s*["\']?[^\s"\']{8,}["\']?',
    r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
    r'(?i)(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36}',
]

VENDOR_PATTERNS = [
    r'/node_modules/',
    r'/vendor/',
    r'/venv/',
    r'/__pycache__/',
    r'/\.git/',
]

MIN_INSTRUCTION_LENGTH = 10
MIN_TARGET_LENGTH = 5
MAX_INSTRUCTION_LENGTH = 2000
MAX_TARGET_LENGTH = 8192
MAX_RETRIEVED_FILES = 20
MAX_TOOL_CALLS = 30
MAX_DIFF_SIZE = 500  # lines added+removed


def has_placeholders(text: str) -> bool:
    for p in PLACEHOLDER_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def has_secrets(text: str) -> bool:
    for p in SECRET_PATTERNS:
        if re.search(p, text):
            return True
    return False


def has_vendor_paths(text: str) -> bool:
    for p in VENDOR_PATTERNS:
        if re.search(p, text):
            return True
    return False


def modality_specific_checks(ex: LymeExample) -> List[str]:
    issues = []
    mod = ex.modality

    if mod == "unified_diff":
        if not ex.patch_diff and "---" not in ex.target_output:
            issues.append("unified_diff must contain diff syntax")
        diff_lines = ex.target_output.count("\n")
        if diff_lines > MAX_DIFF_SIZE:
            issues.append(f"diff too large: {diff_lines} lines")
        has_paths = "--- a/" in ex.target_output and "+++ b/" in ex.target_output
        if not has_paths:
            issues.append("unified_diff must have file paths (--- a/ +++ b/)")

    elif mod == "test_repair":
        if not ex.retrieved_files:
            issues.append("test_repair needs retrieved test files")
        if not any(f.role == "test" for f in ex.retrieved_files):
            issues.append("test_repair should include a test file")
        if not ex.patch_before and not ex.patch_diff:
            issues.append("test_repair should have patch data")

    elif mod == "bug_localization":
        if len(ex.target_output) < 20:
            issues.append("bug_localization target too short")
        has_location = ":" in ex.target_output or "line" in ex.target_output.lower()
        if not has_location:
            issues.append("bug_localization should specify file:line or function")

    elif mod == "multi_file_edit":
        if len(ex.retrieved_files) < 2:
            issues.append("multi_file_edit needs 2+ files")

    elif mod == "tool_use":
        if len(ex.tool_outputs) < 2:
            issues.append("tool_use needs 2+ tool calls")

    elif mod == "debugging_trace":
        if not ex.reasoning_trace:
            issues.append("debugging_trace needs reasoning_trace")
        if len(ex.tool_outputs) < 2:
            issues.append("debugging_trace needs 2+ tool calls")
        if len(ex.reasoning_trace) < 50:
            issues.append("debugging_trace reasoning_trace too short")

    elif mod == "patch_critique":
        if len(ex.candidate_patches) < 2:
            issues.append("patch_critique needs 2+ candidates")

    elif mod == "self_repair":
        if not ex.patch_before:
            issues.append("self_repair needs patch_before (first attempt)")
        if not ex.patch_diff:
            issues.append("self_repair needs patch_diff (repair attempt)")

    elif mod == "long_horizon_planning":
        if not ex.reasoning_trace:
            issues.append("long_horizon_planning needs reasoning_trace")
        n_steps = ex.metadata.get("num_steps", 0)
        if n_steps < 3:
            issues.append(f"long_horizon_planning needs 3+ steps (got {n_steps})")

    elif mod == "refusal":
        if len(ex.target_output) < 20:
            issues.append("refusal target output too short")

    elif mod == "repo_qa":
        if not ex.retrieved_files:
            issues.append("repo_qa needs retrieved files as evidence")

    elif mod == "verification":
        if len(ex.target_output) < 15:
            issues.append("verification target output too short")

    elif mod == "patch_planning":
        if not ex.retrieved_files:
            issues.append("patch_planning needs retrieved files")
        steps = ["1.", "2.", "step"] if mod == "patch_planning" else []
        has_steps = any(s in ex.target_output.lower() for s in ["1.", "step"])
        if not has_steps:
            issues.append("patch_planning should contain numbered steps")

    return issues


def check_example(ex: LymeExample) -> Tuple[bool, List[str]]:
    """Quality filter check. Returns (passes, issues)."""
    issues = []

    if not ex.id:
        issues.append("missing id")
    if ex.modality not in VALID_MODALITIES:
        issues.append(f"invalid modality: {ex.modality}")
    if len(ex.instruction) < MIN_INSTRUCTION_LENGTH:
        issues.append(f"instruction too short ({len(ex.instruction)} < {MIN_INSTRUCTION_LENGTH})")
    if len(ex.instruction) > MAX_INSTRUCTION_LENGTH:
        issues.append(f"instruction too long ({len(ex.instruction)} > {MAX_INSTRUCTION_LENGTH})")
    if len(ex.target_output) < MIN_TARGET_LENGTH:
        issues.append(f"target too short ({len(ex.target_output)} < {MIN_TARGET_LENGTH})")
    if len(ex.target_output) > MAX_TARGET_LENGTH:
        issues.append(f"target too long ({len(ex.target_output)} > {MAX_TARGET_LENGTH})")
    if has_placeholders(ex.instruction):
        issues.append("instruction has placeholder text")
    if has_placeholders(ex.target_output):
        issues.append("target has placeholder text")
    if has_secrets(ex.instruction) or has_secrets(ex.target_output):
        issues.append("contains potential secrets")
    if has_vendor_paths(ex.instruction) or has_vendor_paths(ex.target_output):
        issues.append("contains vendor paths")
    if len(ex.retrieved_files) > MAX_RETRIEVED_FILES:
        issues.append(f"too many retrieved files ({len(ex.retrieved_files)})")
    if len(ex.tool_outputs) > MAX_TOOL_CALLS:
        issues.append(f"too many tool outputs ({len(ex.tool_outputs)})")

    issues.extend(modality_specific_checks(ex))
    return len(issues) == 0, issues


def filter_file(input_path: Path, output_path: Path, stats_path: Optional[Path] = None):
    """Filter a JSONL file, writing passing examples to output."""
    passed = 0
    failed = 0
    failure_reasons = {}

    with open(input_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ex = LymeExample.from_dict(data)
                ok, issues = check_example(ex)
                if ok:
                    fout.write(json.dumps(ex.to_dict()) + "\n")
                    passed += 1
                else:
                    failed += 1
                    key = issues[0] if issues else "unknown"
                    failure_reasons[key] = failure_reasons.get(key, 0) + 1
            except json.JSONDecodeError:
                failed += 1
                failure_reasons["json_parse_error"] = failure_reasons.get("json_parse_error", 0) + 1

    print(f"  {input_path.name}: {passed} passed, {failed} failed")
    if failure_reasons:
        print(f"    Top failures:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1])[:5]:
            print(f"      {reason}: {count}")
    print()

    if stats_path:
        stats = {"passed": passed, "failed": failed, "failure_reasons": failure_reasons}
        stats_path.write_text(json.dumps(stats, indent=2))

    return passed, failed
