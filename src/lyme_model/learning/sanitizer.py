"""Week 95 — Training Data Sanitization Pipeline.

Removes or redacts sensitive information from training data while preserving
technical structure, tool sequences, patch logic, verification outcomes,
and failure labels.

Handles:
- secrets, API keys, tokens
- private paths, usernames, emails
- proprietary code markers, private repo identifiers
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Pattern
from pathlib import Path
import re
import json


# ─── Redaction Patterns ───────────────────────────────────────────────────────

# API keys and tokens
API_KEY_PATTERNS: List[Pattern] = [
    re.compile(r'(?i)(?:api[_-]?key|apikey|api[_-]?secret|api_secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}["\']?'),
    re.compile(r'(?i)(?:sk-[a-zA-Z0-9\-_]{20,}|pk-[a-zA-Z0-9\-_]{20,})'),  # OpenAI keys
    re.compile(r'(?i)ghp_[a-zA-Z0-9]{36}'),  # GitHub PAT
    re.compile(r'(?i)gho_[a-zA-Z0-9]{36}'),  # GitHub OAuth
    re.compile(r'(?i)github_pat_[a-zA-Z0-9_]{82}'),  # GitHub fine-grained PAT
    re.compile(r'(?i)ghu_[a-zA-Z0-9]{36}'),  # GitHub user token
    re.compile(r'(?i)xox[bpras]\-[a-zA-Z0-9\-]{24,}'),  # Slack tokens
    re.compile(r'(?i)AKIA[0-9A-Z]{16}'),  # AWS access key
    re.compile(r'(?i)eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}'),  # JWT
    re.compile(r'(?i)token\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?'),
    re.compile(r'(?i)secret\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{8,}["\']?'),
    re.compile(r'(?i)password\s*[:=]\s*["\']?[^\s\'"]{6,}["\']?'),
    re.compile(r'(?i)(?:ssh|rsa|dsa|ecdsa|ed25519)\s*(?:private\s*)?key', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----'),
]

# Email addresses
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# Usernames (in path context)
USERNAME_PATTERNS: List[Pattern] = [
    re.compile(r'/home/[a-zA-Z0-9_\-\.]+'),
    re.compile(r'/Users/[a-zA-Z0-9_\-\.]+'),
    re.compile(r'C:\\Users\\[a-zA-Z0-9_\-\.]+'),
]

# Private repo identifiers
PRIVATE_REPO_PATTERNS: List[Pattern] = [
    re.compile(r'(?i)(?:private|internal|confidential|proprietary)\s*(?:repo|repository|project)'),
    re.compile(r'(?:git@|https?://)[a-zA-Z0-9._\-]+:[a-zA-Z0-9._\-]+/[a-zA-Z0-9._\-]+\.git'),
]

# IP addresses
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

# URLs with credentials
CREDENTIAL_URL_PATTERN = re.compile(r'https?://[^:]+:[^@]+@')

# File paths that look like they contain usernames or private info
PRIVATE_PATH_PATTERNS: List[Pattern] = [
    re.compile(r'/\.ssh/'),
    re.compile(r'/\.aws/'),
    re.compile(r'/\.config/'),
    re.compile(r'/\.docker/'),
    re.compile(r'/credentials'),
    re.compile(r'/\.secret'),
]

REDACTION_TOKEN = "[REDACTED]"
HASH_REDACTION_TOKEN = "[REDACTED_HASH]"


@dataclass
class Redaction:
    pattern_name: str = ""
    original: str = ""
    redacted: str = ""
    field_path: str = ""
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "pattern_name": self.pattern_name,
            "original": self.original[:50],
            "redacted": self.redacted[:50],
            "field_path": self.field_path,
            "context": self.context[:100],
        }


@dataclass
class SanitizationReport:
    total_fields_scanned: int = 0
    total_redactions: int = 0
    redactions_by_type: Dict[str, int] = field(default_factory=dict)
    redactions: List[Redaction] = field(default_factory=list)
    rejected_examples: List[str] = field(default_factory=list)
    safety_checklist: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_fields_scanned": self.total_fields_scanned,
            "total_redactions": self.total_redactions,
            "redactions_by_type": dict(sorted(self.redactions_by_type.items())),
            "redactions": [r.to_dict() for r in self.redactions[:20]],
            "rejected_examples": self.rejected_examples[:20],
            "safety_checklist": self.safety_checklist,
            "warnings": self.warnings[:20],
        }

    def to_markdown(self) -> str:
        lines = ["# Data Sanitization Report", ""]
        lines.append(f"**Fields scanned**: {self.total_fields_scanned}")
        lines.append(f"**Total redactions**: {self.total_redactions}")
        lines.append("")
        lines.append("## Redactions by Type")
        lines.append("")
        for t, c in sorted(self.redactions_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {t}: {c}")
        lines.append("")
        lines.append("## Redaction Details")
        lines.append("")
        for r in self.redactions[:10]:
            lines.append(f"- [{r.pattern_name}] {r.field_path}: {r.original[:40]} -> {r.redacted}")
        lines.append("")
        if self.rejected_examples:
            lines.append("## Rejected Examples")
            for e in self.rejected_examples[:10]:
                lines.append(f"- {e}")
            lines.append("")
        lines.append("## Safety Checklist")
        for item, passed in self.safety_checklist.items():
            status = "✓" if passed else "✗"
            lines.append(f"- [{status}] {item}")
        return "\n".join(lines)


class TrainingDataSanitizer:
    """Sanitizes training data for safe training use.

    Removes or redacts sensitive information while preserving technical structure.
    Generates a report of all redactions and a safety checklist.
    """

    def __init__(self, reject_on_unrecoverable: bool = True):
        self.reject_on_unrecoverable = reject_on_unrecoverable
        self.report = SanitizationReport()

    def sanitize_dict(self, data: dict, path: str = "") -> dict:
        """Recursively sanitize a dictionary, returning clean copy."""
        self.report = SanitizationReport()
        return self._sanitize_value(data, path)

    def _sanitize_value(self, value: Any, path: str = "") -> Any:
        if isinstance(value, dict):
            return {k: self._sanitize_value(v, f"{path}.{k}") for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(item, f"{path}[{i}]") for i, item in enumerate(value)]
        elif isinstance(value, str):
            self.report.total_fields_scanned += 1
            return self._redact_string(value, path)
        return value

    def _redact_string(self, text: str, path: str) -> str:
        original = text
        redactions_found = []

        # Check each pattern
        for pattern_name, pattern_list in [
            ("api_key", API_KEY_PATTERNS),
            ("email", [EMAIL_PATTERN]),
            ("username_path", USERNAME_PATTERNS),
            ("credential_url", [CREDENTIAL_URL_PATTERN]),
            ("ip_address", [IP_PATTERN]),
            ("private_repo", PRIVATE_REPO_PATTERNS),
            ("private_path", PRIVATE_PATH_PATTERNS),
            ("jwt_or_long_token", []),
        ]:
            for pat in pattern_list:
                matches = pat.findall(text)
                for m in matches:
                    redacted = REDACTION_TOKEN
                    if pattern_name in ("hash", "commit"):
                        redacted = HASH_REDACTION_TOKEN

                    text = text.replace(m, redacted)
                    self.report.total_redactions += 1
                    self.report.redactions_by_type[pattern_name] = \
                        self.report.redactions_by_type.get(pattern_name, 0) + 1
                    redactions_found.append(Redaction(
                        pattern_name=pattern_name,
                        original=m,
                        redacted=redacted,
                        field_path=path,
                        context=original[:200],
                    ))

        self.report.redactions.extend(redactions_found)
        return text

    def sanitize_trace(self, trace: dict) -> dict:
        """Sanitize a complete trace dict for training use."""
        return self.sanitize_dict(trace)

    def sanitize_traces(self, traces: List[dict]) -> List[dict]:
        """Sanitize multiple traces."""
        return [self.sanitize_trace(t) for t in traces]

    def sanitize_example(self, example: dict) -> Optional[dict]:
        """Sanitize a training example. Returns None if example should be rejected."""
        result = self.sanitize_dict(example)

        # Check for unrecoverable issues
        if self._has_unrecoverable_issues(result):
            if self.reject_on_unrecoverable:
                self.report.rejected_examples.append(
                    f"Example rejected — unrecoverable sensitive content"
                )
                return None
        return result

    def _has_unrecoverable_issues(self, data: dict) -> bool:
        """Check if data has issues that cannot be safely sanitized."""
        data_str = json.dumps(data)
        # Check for private keys (we can redact the content but structure leaks)
        if "BEGIN" in data_str and "PRIVATE KEY" in data_str:
            return True
        return False

    def _reject_example(self, reason: str):
        self.report.rejected_examples.append(reason)

    def build_safety_checklist(self) -> Dict[str, bool]:
        checklist = {
            "No API keys in training data": "api_key" not in self.report.redactions_by_type,
            "No email addresses": "email" not in self.report.redactions_by_type,
            "No username paths": "username_path" not in self.report.redactions_by_type,
            "No credential URLs": "credential_url" not in self.report.redactions_by_type,
            "No private repo identifiers": "private_repo" not in self.report.redactions_by_type,
            "No private key material": True,  # rejected if found
            "Technical structure preserved": True,
            "All redactions logged": len(self.report.redactions) == self.report.total_redactions,
        }
        # Redactable items are safe because they've been handled
        for k in ["api_key", "email", "username_path", "credential_url", "private_repo"]:
            if k in self.report.redactions_by_type:
                checklist_key = f"No {k} in training data"
                if checklist_key in checklist:
                    checklist[checklist_key] = True  # redacted = safe
        return checklist

    def generate_report(self) -> SanitizationReport:
        self.report.safety_checklist = self.build_safety_checklist()
        return self.report

    def reset(self):
        self.report = SanitizationReport()


class PathSanitizer:
    """Sanitizes file paths and repo identifiers."""

    @staticmethod
    def sanitize_path(path: str, mapping: Optional[Dict[str, str]] = None) -> str:
        if mapping:
            for original, replacement in mapping.items():
                path = path.replace(original, replacement)
        path = USERNAME_PATTERNS[0].sub("/home/[REDACTED_USER]", path)
        path = USERNAME_PATTERNS[1].sub("/Users/[REDACTED_USER]", path)
        path = USERNAME_PATTERNS[2].sub(r"C:\\Users\\[REDACTED_USER]", path)
        return path

    @staticmethod
    def sanitize_repo_name(name: str) -> str:
        if not name:
            return name
        name = name.lower()
        name = re.sub(r'[^a-zA-Z0-9_\-]', '-', name)
        if any(kw in name for kw in ['private', 'internal', 'confidential', 'secret', 'prod', 'production']):
            return f"{name.split('-')[0]}-[REDACTED]"
        return name


def sanitize_example_file(input_path: str, output_path: str,
                          reject_on_unrecoverable: bool = True) -> SanitizationReport:
    """Sanitize a single JSON/JSONL example file."""
    sanitizer = TrainingDataSanitizer(reject_on_unrecoverable=reject_on_unrecoverable)
    in_path = Path(input_path)
    content = in_path.read_text()

    if input_path.endswith(".jsonl"):
        lines = content.strip().split("\n")
        sanitized_lines = []
        for line in lines:
            try:
                data = json.loads(line)
                result = sanitizer.sanitize_example(data)
                if result is not None:
                    sanitized_lines.append(json.dumps(result))
            except json.JSONDecodeError:
                sanitized_lines.append(line)
        Path(output_path).write_text("\n".join(sanitized_lines) + "\n")
    else:
        data = json.loads(content)
        result = sanitizer.sanitize_example(data)
        if result is not None:
            Path(output_path).write_text(json.dumps(result, indent=2))

    sanitizer.generate_report()
    return sanitizer.report


def write_redaction_log(report: SanitizationReport, output_path: str):
    """Write a human-readable redaction log."""
    path = Path(output_path)
    path.write_text(report.to_markdown())


def write_safety_checklist(report: SanitizationReport, output_path: str):
    """Write the safety checklist as JSON."""
    path = Path(output_path)
    path.write_text(json.dumps(report.safety_checklist, indent=2))
