from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import re
import uuid


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SensitivePattern:
    name: str
    patterns: List[str]
    level: SensitivityLevel
    description: str
    category: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "patterns": self.patterns,
            "level": self.level.value,
            "description": self.description,
            "category": self.category,
        }


@dataclass
class SensitiveZone:
    file_path: str
    zone_type: str
    level: SensitivityLevel
    patterns_matched: List[str]
    line_count: int = 0
    risk_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "zone_type": self.zone_type,
            "level": self.level.value,
            "patterns_matched": self.patterns_matched,
            "line_count": self.line_count,
            "risk_score": self.risk_score,
        }


@dataclass
class DetectionResult:
    zones: List[SensitiveZone]
    total_critical: int
    total_high: int
    total_medium: int
    total_low: int
    risk_summary: Dict
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "zones": [z.to_dict() for z in self.zones],
            "total_critical": self.total_critical,
            "total_high": self.total_high,
            "total_medium": self.total_medium,
            "total_low": self.total_low,
            "risk_summary": self.risk_summary,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Sensitive Code Detection Report")
        lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"- Critical: {self.total_critical} | High: {self.total_high} | Medium: {self.total_medium} | Low: {self.total_low}")
        lines.append(f"- Total Risk Score: {self.risk_summary.get('total_risk_score', 0):.2f}")
        lines.append(f"- Risk Level: {self.risk_summary.get('risk_level', 'unknown')}")
        lines.append(f"")
        for zone in self.zones:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(zone.level.value, "⚪")
            lines.append(f"{icon} **{zone.file_path}** ({zone.zone_type})")
            lines.append(f"  - Level: {zone.level.value}, Risk: {zone.risk_score:.2f}")
        if self.recommendations:
            lines.append(f"## Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)


class SensitiveCodeDetector:
    def __init__(self):
        self._patterns = self._define_patterns()

    def _define_patterns(self) -> List[SensitivePattern]:
        return [
            SensitivePattern("Authentication", [
                r"login", r"authenticate", r"oauth", r"jwt", r"token",
                r"verify_password", r"password_hash", r"sign_in", r"sign_up",
            ], SensitivityLevel.CRITICAL, "Authentication and authorization logic", "auth"),

            SensitivePattern("Payments", [
                r"payment", r"stripe", r"checkout", r"invoice", r"billing",
                r"charge", r"refund", r"subscription", r"price", r"payout",
            ], SensitivityLevel.CRITICAL, "Payment processing and billing", "financial"),

            SensitivePattern("Secrets", [
                r"SECRET_KEY", r"API_KEY", r"api_key", r"api_secret",
                r"db_password", r"DB_PASSWORD", r"private_key", r"PRIVATE_KEY",
                r"access_key", r"ACCESS_KEY", r"secret_key", r"SECRET",
                r"password\s*=", r"PASSWORD\s*=",
            ], SensitivityLevel.CRITICAL, "Secrets, keys and credentials", "secrets"),

            SensitivePattern("Database", [
                r"execute\(.*f[\"']", r"raw_sql", r"connection\.execute",
                r"cursor\.execute", r"session\.execute", r"text\(",
                r"ALTER TABLE", r"DROP TABLE", r"TRUNCATE",
            ], SensitivityLevel.HIGH, "Database operations with SQL", "database"),

            SensitivePattern("File Operations", [
                r"open\(.*[\"'][\w/]+[\"']", r"shutil\.", r"os\.remove",
                r"os\.unlink", r"os\.rmdir", r"shutil\.rmtree",
                r"pathlib.*\.unlink", r"pathlib.*\.rmdir",
            ], SensitivityLevel.MEDIUM, "File system operations", "filesystem"),

            SensitivePattern("Network", [
                r"socket\.", r"requests\.", r"httpx\.", r"aiohttp\.",
                r"urllib", r"urlopen",
            ], SensitivityLevel.MEDIUM, "Network communication", "network"),

            SensitivePattern("Deployment", [
                r"kubectl", r"helm", r"docker", r"docker-compose",
                r"deploy", r"rollout", r"terraform", r"ansible",
                r"ci:", r"cd:", r"pipeline",
            ], SensitivityLevel.HIGH, "Deployment and infrastructure", "deployment"),

            SensitivePattern("Encryption", [
                r"encrypt", r"decrypt", r"cipher", r"crypto",
                r"hashlib", r"bcrypt", r"argon2", r"Fernet",
            ], SensitivityLevel.CRITICAL, "Encryption and cryptography", "crypto"),

            SensitivePattern("Compliance", [
                r"gdpr", r"hipaa", r"pci", r"ccpa", r"pii",
                r"personally_identifiable", r"privacy",
            ], SensitivityLevel.HIGH, "Legal and compliance", "compliance"),

            SensitivePattern("System Commands", [
                r"subprocess\.", r"os\.system", r"os\.popen",
                r"shlex", r"eval\(", r"exec\(", r"compile\(",
            ], SensitivityLevel.CRITICAL, "System command execution", "system"),

            SensitivePattern("Configuration", [
                r"settings\.py", r"config\.py", r"\.env", r"\.ini",
                r"config\.yaml", r"config\.json", r"application\.properties",
            ], SensitivityLevel.MEDIUM, "Configuration files", "config"),

            SensitivePattern("Migration", [
                r"alembic", r"migrate", r"migration", r"schema_change",
                r"ALTER TABLE", r"CREATE TABLE", r"DROP COLUMN",
            ], SensitivityLevel.HIGH, "Database migrations", "migration"),

            SensitivePattern("Production Infrastructure", [
                r"production", r"prod", r"kubernetes", r"k8s",
                r"load_balancer", r"auto_scaling", r"replica",
                r"service_monitor", r"alertmanager",
            ], SensitivityLevel.HIGH, "Production infrastructure", "infrastructure"),
        ]

    def detect(self, project_path: Path) -> DetectionResult:
        zones: List[SensitiveZone] = []
        files_scanned = 0
        files_with_issues = 0

        for file_path in project_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size == 0:
                continue
            if any(part.startswith(".") for part in file_path.parts):
                continue

            files_scanned += 1
            rel_path = str(file_path.relative_to(project_path))
            try:
                content = file_path.read_text(errors="ignore")
            except Exception:
                continue

            for pattern in self._patterns:
                matches = [m for m in pattern.patterns if re.search(m, content, re.IGNORECASE)]
                if matches:
                    line_count = len(content.splitlines())
                    severity_weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                    risk = severity_weights.get(pattern.level.value, 1) * len(matches)
                    risk_score = min(1.0, risk / 20.0)

                    zones.append(SensitiveZone(
                        file_path=rel_path,
                        zone_type=pattern.category,
                        level=pattern.level,
                        patterns_matched=matches,
                        line_count=line_count,
                        risk_score=round(risk_score, 3),
                    ))
                    files_with_issues += 1

        critical = len([z for z in zones if z.level == SensitivityLevel.CRITICAL])
        high = len([z for z in zones if z.level == SensitivityLevel.HIGH])
        medium = len([z for z in zones if z.level == SensitivityLevel.MEDIUM])
        low_count = len([z for z in zones if z.level == SensitivityLevel.LOW])

        total_risk = sum(z.risk_score for z in zones)
        avg_risk = total_risk / max(len(zones), 1)
        risk_level = "critical" if avg_risk > 0.7 else "high" if avg_risk > 0.4 else "medium" if avg_risk > 0.2 else "low"

        recommendations = self._generate_recommendations(zones, risk_level)

        return DetectionResult(
            zones=sorted(zones, key=lambda z: -z.risk_score),
            total_critical=critical,
            total_high=high,
            total_medium=medium,
            total_low=low_count,
            risk_summary={
                "files_scanned": files_scanned,
                "files_with_sensitive_code": files_with_issues,
                "total_risk_score": round(total_risk, 2),
                "avg_risk_score": round(avg_risk, 3),
                "risk_level": risk_level,
                "total_zones": len(zones),
            },
            recommendations=recommendations,
        )

    def _generate_recommendations(self, zones: List[SensitiveZone], risk_level: str) -> List[str]:
        recs = []
        if risk_level in ("critical", "high"):
            recs.append("Reduce autonomy level for files in critical/high sensitivity zones")
            recs.append("Require explicit approval for any modification to sensitive files")
            recs.append("Enable enhanced audit trail for all sensitive file operations")

        critical_auth = [z for z in zones if z.zone_type == "auth"]
        if critical_auth:
            recs.append(f"Authentication code in {len(critical_auth)} files: require peer review for changes")

        secrets = [z for z in zones if z.zone_type == "secrets"]
        if secrets:
            recs.append(f"Secrets detected in {len(secrets)} files: NEVER allow automatic modification")

        crypto = [z for z in zones if z.zone_type == "crypto"]
        if crypto:
            recs.append("Encryption code: mandate security review for any changes")

        payment = [z for z in zones if z.zone_type == "financial"]
        if payment:
            recs.append("Payment processing code: require compliance review")

        deployment = [z for z in zones if z.zone_type == "deployment"]
        if deployment:
            recs.append("Deployment infrastructure: require approval pipeline")

        if not recs:
            recs.append("No critical sensitive zones detected. Standard policy applies.")

        return recs
