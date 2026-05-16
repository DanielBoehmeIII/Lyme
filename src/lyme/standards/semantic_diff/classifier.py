"""Semantic diff classifier — classifies git diffs by intent, risk, and scope."""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ChangeIntent(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChangedFile:
    path: str
    added: int = 0
    removed: int = 0
    is_sensitive: bool = False
    primary_intent: str = "unknown"
    risk_score: float = 0.0


@dataclass
class ClassificationResult:
    intent: ChangeIntent
    risk: RiskLevel
    risk_score: float
    files: List[ChangedFile]
    summary: str
    suggested_verification: List[str]
    sensitive_files: List[str]
    raw_stats: Dict = field(default_factory=dict)


SENSITIVE_PATTERNS = [
    r".*auth.*", r".*credential.*", r".*secret.*", r".*password.*",
    r".*token.*", r".*key\.", r".*cert.*", r".*pem", r".*\.env",
    r".*deploy.*", r".*\.gitignore", r".*docker-compose.*",
    r".*k8s.*", r".*kubernetes.*", r".*helm.*",
    r".*config.*\.py", r".*settings\.py", r".*database.*",
]

INTENT_PATTERNS = {
    ChangeIntent.BUG_FIX: [
        r"fix", r"bug", r"crash", r"error", r"issue", r"incorrect",
        r"wrong", r"broken", r"fail", r"off.by.one", r"null", r"edge.case",
    ],
    ChangeIntent.FEATURE: [
        r"add", r"feature", r"implement", r"new", r"support", r"allow",
        r"introduce", r"enable", r"create",
    ],
    ChangeIntent.REFACTOR: [
        r"refactor", r"rename", r"move", r"extract", r"inline",
        r"simplify", r"clean", r"restructure", r"reorganize",
    ],
    ChangeIntent.TEST: [
        r"test", r"spec", r"assert", r"mock", r"pytest", r"unittest",
    ],
    ChangeIntent.DOCS: [
        r"doc", r"readme", r"comment", r"docstring", r"\.md$",
    ],
    ChangeIntent.CONFIG: [
        r"config", r"\.toml$", r"\.yaml$", r"\.yml$", r"\.json$",
        r"\.ini$", r"setup\.", r"dockerfile", r"makefile",
    ],
    ChangeIntent.DEPENDENCY: [
        r"depend", r"requirement", r"package", r"import.*new",
    ],
    ChangeIntent.PERFORMANCE: [
        r"perform", r"speed", r"slow", r"fast", r"cache", r"optimize",
        r"latency", r"throughput",
    ],
    ChangeIntent.SECURITY: [
        r"security", r"vulnerability", r"cve", r"xss", r"csrf", r"injection",
        r"sanitize", r"escape", r"permission", r"auth", r"sensitive",
    ],
}


def _run_git_diff(path: Optional[Path] = None, staged: bool = False) -> str:
    cwd = path.resolve() if path else Path.cwd()
    cmd = ["git", "diff", "--staged"] if staged else ["git", "diff"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return result.stdout
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def _parse_diff(diff_text: str) -> Tuple[List[ChangedFile], Dict]:
    files: Dict[str, ChangedFile] = {}
    total_added = 0
    total_removed = 0
    current_file = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            fname = line[6:]
            if fname not in files:
                files[fname] = ChangedFile(path=fname)
            current_file = fname
        elif line.startswith("--- a/"):
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            total_added += 1
            if current_file:
                files[current_file].added += 1
        elif line.startswith("-") and not line.startswith("---"):
            total_removed += 1
            if current_file:
                files[current_file].removed += 1

    return list(files.values()), {"added": total_added, "removed": total_removed}


def _detect_sensitive(path: str) -> bool:
    lower = path.lower()
    for pattern in SENSITIVE_PATTERNS:
        if re.match(pattern, lower):
            return True
    return False


def _detect_primary_intent(files: List[ChangedFile], diff_text: str, message: str = "") -> ChangeIntent:
    scored: Dict[ChangeIntent, int] = {intent: 0 for intent in ChangeIntent}

    for f in files:
        lower = f.path.lower()
        for intent, patterns in INTENT_PATTERNS.items():
            for p in patterns:
                if re.search(p, lower):
                    scored[intent] = scored.get(intent, 0) + 2

    lower_text = diff_text.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for p in patterns:
            matches = len(re.findall(p, lower_text))
            if matches:
                scored[intent] = scored.get(intent, 0) + matches

    if message:
        lower_msg = message.lower()
        for intent, patterns in INTENT_PATTERNS.items():
            for p in patterns:
                if re.search(p, lower_msg):
                    scored[intent] = scored.get(intent, 0) + 3

    if scored:
        best = max(scored, key=scored.get)
        if scored[best] > 0:
            return best

    file_extensions = [Path(f.path).suffix for f in files]
    if all(ext in (".md", ".rst", ".txt") for ext in file_extensions if ext):
        return ChangeIntent.DOCS
    if all(ext in (".toml", ".yaml", ".yml", ".json", ".ini") for ext in file_extensions if ext):
        return ChangeIntent.CONFIG
    if any("test" in f.path.lower() for f in files):
        return ChangeIntent.TEST

    return ChangeIntent.UNKNOWN


def _compute_risk_score(files: List[ChangedFile], stats: Dict) -> Tuple[float, RiskLevel]:
    score = 0.0

    sensitive_count = sum(1 for f in files if f.is_sensitive)
    score += sensitive_count * 0.3

    total_changed = stats.get("added", 0) + stats.get("removed", 0)
    if total_changed > 500:
        score += 0.3
    elif total_changed > 100:
        score += 0.15
    elif total_changed > 50:
        score += 0.05

    if len(files) > 10:
        score += 0.2
    elif len(files) > 5:
        score += 0.1

    if sensitive_count > 0 and total_changed > 50:
        score += 0.2

    score = min(score, 1.0)

    if score >= 0.7:
        level = RiskLevel.CRITICAL
    elif score >= 0.5:
        level = RiskLevel.HIGH
    elif score >= 0.3:
        level = RiskLevel.MEDIUM
    elif score >= 0.1:
        level = RiskLevel.LOW
    else:
        level = RiskLevel.NONE

    return score, level


def _generate_verification_suggestions(intent: ChangeIntent, risk: RiskLevel, sensitive_files: List[str]) -> List[str]:
    suggestions = []

    if sensitive_files:
        suggestions.append(f"Review {len(sensitive_files)} sensitive file(s) for approval")

    if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        suggestions.append("Require human review before applying")

    if intent == ChangeIntent.BUG_FIX:
        suggestions.append("Run existing tests to confirm no regression")
        suggestions.append("Add test case that reproduces the bug")
    elif intent == ChangeIntent.FEATURE:
        suggestions.append("Add tests for the new feature")
        suggestions.append("Run all existing tests to check for regressions")
    elif intent == ChangeIntent.REFACTOR:
        suggestions.append("Run full test suite to verify no behavior change")
        suggestions.append("Verify code coverage is maintained")
    elif intent == ChangeIntent.TEST:
        suggestions.append("Run the changed tests to confirm they pass")
    elif intent == ChangeIntent.DEPENDENCY:
        suggestions.append("Verify dependency version compatibility")
        suggestions.append("Run tests to check for breaking changes")

    if risk == RiskLevel.NONE:
        suggestions.append("Low risk — standard review sufficient")

    suggestions.append("Run linting on changed files") if risk.value in ("medium", "high", "critical") else None

    return suggestions


def classify_diff(diff_text: str = None, path: Optional[Path] = None, staged: bool = False, message: str = "") -> ClassificationResult:
    if diff_text is None and path:
        diff_text = _run_git_diff(path, staged)
    elif diff_text is None:
        diff_text = _run_git_diff(staged=staged)

    if not diff_text or not diff_text.strip():
        return ClassificationResult(
            intent=ChangeIntent.UNKNOWN, risk=RiskLevel.NONE, risk_score=0.0,
            files=[], summary="No changes to classify",
            suggested_verification=[], sensitive_files=[],
        )

    files, stats = _parse_diff(diff_text)
    for f in files:
        f.is_sensitive = _detect_sensitive(f.path)

    intent = _detect_primary_intent(files, diff_text, message)
    sensitive_files = [f.path for f in files if f.is_sensitive]
    risk_score, risk_level = _compute_risk_score(files, stats)
    suggestions = _generate_verification_suggestions(intent, risk_level, sensitive_files)

    total_changed = stats["added"] + stats["removed"]
    summary = (
        f"{len(files)} file(s) changed, +{stats['added']}/-{stats['removed']} lines. "
        f"Intent: {intent.value.replace('_', ' ').title()}. "
        f"Risk: {risk_level.value.upper()} ({risk_score:.0%})."
    )

    return ClassificationResult(
        intent=intent, risk=risk_level, risk_score=risk_score,
        files=files, summary=summary,
        suggested_verification=suggestions,
        sensitive_files=sensitive_files,
        raw_stats=stats,
    )


def to_dict(result: ClassificationResult) -> Dict:
    return {
        "intent": result.intent.value,
        "risk": result.risk.value,
        "risk_score": round(result.risk_score, 2),
        "files_changed": len(result.files),
        "lines_added": result.raw_stats.get("added", 0),
        "lines_removed": result.raw_stats.get("removed", 0),
        "sensitive_files": result.sensitive_files,
        "summary": result.summary,
        "files": [
            {
                "path": f.path, "added": f.added, "removed": f.removed,
                "sensitive": f.is_sensitive,
            }
            for f in result.files
        ],
        "suggested_verification": result.suggested_verification,
    }
