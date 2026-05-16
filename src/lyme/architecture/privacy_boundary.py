"""Privacy boundaries for Lyme's dual architecture.

Ensures that research data collection never leaks sensitive information,
and that users have explicit control over what crosses the boundary.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Pattern
from pathlib import Path
import re
import hashlib


class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class PrivacyZone(Enum):
    PRODUCT_ONLY = "product_only"
    RESEARCH_ANONYMIZED = "research_anonymized"
    RESEARCH_FULL = "research_full"
    BLOCKED = "blocked"


@dataclass
class SanitizationRule:
    name: str
    pattern: Pattern
    replacement: str = "[REDACTED]"
    classification: DataClassification = DataClassification.SENSITIVE
    apply_to_research: bool = True
    apply_to_storage: bool = True

    def sanitize(self, text: str) -> str:
        return self.pattern.sub(self.replacement, text)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pattern": self.pattern.pattern,
            "replacement": self.replacement,
            "classification": self.classification.value,
            "apply_to_research": self.apply_to_research,
            "apply_to_storage": self.apply_to_storage,
        }


@dataclass
class PrivacyPolicy:
    name: str
    version: str = "1.0.0"
    rules: List[SanitizationRule] = field(default_factory=list)
    default_classification: DataClassification = DataClassification.INTERNAL
    allow_research_collection: bool = True
    require_consent_for_secrets: bool = True
    anonymize_paths: bool = True
    anonymize_repo_names: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "rules": [r.to_dict() for r in self.rules],
            "default_classification": self.default_classification.value,
            "allow_research_collection": self.allow_research_collection,
            "require_consent_for_secrets": self.require_consent_for_secrets,
            "anonymize_paths": self.anonymize_paths,
            "anonymize_repo_names": self.anonymize_repo_names,
        }


class BoundaryViolationError(Exception):
    def __init__(self, message: str, classification: DataClassification,
                 target_zone: PrivacyZone):
        self.classification = classification
        self.target_zone = target_zone
        super().__init__(f"Privacy boundary violation: {message} "
                        f"({classification.value} -> {target_zone.value})")


class PrivacyBoundary:
    """Enforces privacy rules across the product/research boundary."""

    def __init__(self, policy: Optional[PrivacyPolicy] = None):
        self.policy = policy or self._default_policy()
        self._audit_log: List[dict] = []

    @staticmethod
    def _default_policy() -> PrivacyPolicy:
        return PrivacyPolicy(
            name="default",
            rules=[
                SanitizationRule(
                    name="api_keys",
                    pattern=re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\']?[^\s"\'"]+'),
                ),
                SanitizationRule(
                    name="file_paths_home",
                    pattern=re.compile(r'/home/[^/\s]+(/[^\s:]+)'),
                    replacement="/home/[user]\\1",
                ),
                SanitizationRule(
                    name="email_addresses",
                    pattern=re.compile(r'[\w\.-]+@[\w\.-]+\.\w+'),
                ),
                SanitizationRule(
                    name="ip_addresses",
                    pattern=re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
                ),
                SanitizationRule(
                    name="git_remote_urls_with_credentials",
                    pattern=re.compile(r'https?://[^@]+@'),
                    replacement="https://[REDACTED]@",
                ),
                SanitizationRule(
                    name="environment_variables",
                    pattern=re.compile(r'(?i)(export|set|env)\s+[A-Z_]+=([^\s]+)'),
                    replacement="\\1 [REDACTED]",
                    classification=DataClassification.SENSITIVE,
                ),
            ],
        )

    def classify_data(self, data: dict) -> DataClassification:
        has_secrets = any(
            rule.classification == DataClassification.SECRET
            for rule in self.policy.rules
            for _ in [True]
        )
        secrets_keys = {"key", "secret", "token", "password", "credential"}
        for key in data.keys():
            key_lower = key.lower().replace("_", "").replace("-", "")
            if any(sk in key_lower for sk in secrets_keys):
                return DataClassification.SECRET
        return self.policy.default_classification

    def check_boundary(self, data: dict, target_zone: PrivacyZone) -> bool:
        classification = self.classify_data(data)

        if target_zone == PrivacyZone.BLOCKED:
            raise BoundaryViolationError(
                "Data routed to blocked zone", classification, target_zone
            )

        if classification == DataClassification.SECRET:
            if target_zone != PrivacyZone.PRODUCT_ONLY:
                raise BoundaryViolationError(
                    "Secrets cannot cross product boundary",
                    classification, target_zone
                )

        if classification == DataClassification.SENSITIVE:
            if target_zone == PrivacyZone.RESEARCH_FULL:
                raise BoundaryViolationError(
                    "Sensitive data requires anonymization for research",
                    classification, target_zone
                )

        return True

    def sanitize_for_research(self, data: dict) -> dict:
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                for rule in self.policy.rules:
                    if rule.apply_to_research:
                        value = rule.sanitize(value)
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_for_research(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_for_research(item) if isinstance(item, dict)
                    else item for item in value
                ]
            else:
                sanitized[key] = value

        if self.policy.anonymize_paths:
            sanitized = self._anonymize_paths(sanitized)

        return sanitized

    def _anonymize_paths(self, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and ("/" in value or "\\" in value):
                path_like = value.replace("\\", "/")
                parts = path_like.split("/")
                if any("." in p for p in parts):
                    hashed = hashlib.sha256(path_like.encode()).hexdigest()[:12]
                    result[key] = f"path_{hashed}/{parts[-1]}"
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self._anonymize_paths(value)
            elif isinstance(value, list):
                result[key] = [
                    self._anonymize_paths(item) if isinstance(item, dict)
                    else item for item in value
                ]
            else:
                result[key] = value
        return result

    def log_violation(self, data_classification: DataClassification,
                      target_zone: PrivacyZone, reason: str):
        self._audit_log.append({
            "classification": data_classification.value,
            "target_zone": target_zone.value,
            "reason": reason,
        })

    def get_audit_log(self) -> List[dict]:
        return list(self._audit_log)

    def to_dict(self) -> dict:
        return {
            "policy": self.policy.to_dict(),
            "violation_count": len(self._audit_log),
        }


_default_boundary: Optional[PrivacyBoundary] = None


def get_privacy_boundary() -> PrivacyBoundary:
    global _default_boundary
    if _default_boundary is None:
        _default_boundary = PrivacyBoundary()
    return _default_boundary
