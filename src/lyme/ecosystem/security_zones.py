from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json
import re


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityAdvisory:
    zone: str
    pattern: str
    risk: RiskLevel
    description: str
    file_pattern: str = ""
    code_patterns: List[str] = field(default_factory=list)
    remediation: str = ""
    cvss_estimate: float = 0.0


@dataclass
class SecurityZone:
    name: str
    risk_level: RiskLevel
    file_patterns: List[str]
    code_patterns: List[str]
    advisories: List[SecurityAdvisory] = field(default_factory=list)
    detection_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "risk_level": self.risk_level.value,
            "file_patterns": self.file_patterns,
            "code_patterns": self.code_patterns,
            "advisories": [a.__dict__ for a in self.advisories],
            "detection_count": self.detection_count,
        }


class SecurityZoneDetector:
    def __init__(self):
        self._zones = self._define_zones()

    def _define_zones(self) -> List[SecurityZone]:
        return [
            SecurityZone(
                name="Authentication",
                risk_level=RiskLevel.CRITICAL,
                file_patterns=["*auth*", "*login*", "*register*", "*token*", "*oauth*", "*session*"],
                code_patterns=["login", "register", "authenticate", "verify_password", "create_token", "jwt"],
                advisories=[
                    SecurityAdvisory("Authentication", "Hardcoded JWT secret", RiskLevel.CRITICAL,
                                     "JWT secret key found in source code", code_patterns=["SECRET_KEY =", "jwt_secret=", "secret ="]),
                    SecurityAdvisory("Authentication", "Weak password hashing", RiskLevel.CRITICAL,
                                     "Using unsalted or weak hash algorithms", code_patterns=["md5(", "sha1(", "hashlib.md5"]),
                    SecurityAdvisory("Authentication", "No rate limiting on login", RiskLevel.HIGH,
                                     "Login endpoint lacks brute force protection", code_patterns=["def login", "post.*login"]),
                ],
            ),
            SecurityZone(
                name="SQL/Injection",
                risk_level=RiskLevel.CRITICAL,
                file_patterns=["*sql*", "*query*", "*model*", "*repository*", "*dao*"],
                code_patterns=["execute(", "raw_sql", "text(", "connection.execute"],
                advisories=[
                    SecurityAdvisory("SQL/Injection", "Raw SQL execution", RiskLevel.CRITICAL,
                                     "Raw SQL queries without parameterization", code_patterns=["execute(f", "raw_sql = f"]),
                    SecurityAdvisory("SQL/Injection", "String interpolation in query", RiskLevel.CRITICAL,
                                     "F-string or concatenation in SQL query", code_patterns=["f\"SELECT", "\"SELECT.*+" + "f\"", "'SELECT'"]),
                ],
            ),
            SecurityZone(
                name="Secrets Management",
                risk_level=RiskLevel.CRITICAL,
                file_patterns=["*.env", "*.key", "*secret*", "*credential*", "*config*"],
                code_patterns=["SECRET", "PASSWORD", "API_KEY", "TOKEN", "PRIVATE_KEY"],
                advisories=[
                    SecurityAdvisory("Secrets Management", "Secret committed to repo", RiskLevel.CRITICAL,
                                     "Hardcoded secrets in source code", file_pattern="*.py", code_patterns=["API_KEY =", "PASSWORD =", "SECRET ="]),
                    SecurityAdvisory("Secrets Management", "Missing .env.example", RiskLevel.MEDIUM,
                                     "No .env.example template for required env vars", file_pattern=".env.example"),
                ],
            ),
            SecurityZone(
                name="CORS & Headers",
                risk_level=RiskLevel.MEDIUM,
                file_patterns=["*middleware*", "*cors*", "*app*", "*main*"],
                code_patterns=["CORSMiddleware", "allow_origins", "Access-Control"],
                advisories=[
                    SecurityAdvisory("CORS & Headers", "Permissive CORS", RiskLevel.HIGH,
                                     "CORS configured with allow_origins=[\"*\"]", code_patterns=["allow_origins=[\"*\"]"]),
                    SecurityAdvisory("CORS & Headers", "Missing security headers", RiskLevel.MEDIUM,
                                     "No Content-Security-Policy or X-Frame-Options", code_patterns=[]),
                ],
            ),
            SecurityZone(
                name="File Upload",
                risk_level=RiskLevel.HIGH,
                file_patterns=["*upload*", "*file*", "*attach*", "*media*"],
                code_patterns=["UploadFile", "FileResponse", "file.write", "save.*file"],
                advisories=[
                    SecurityAdvisory("File Upload", "No file size validation", RiskLevel.HIGH,
                                     "File upload without size limit check", code_patterns=["UploadFile"]),
                    SecurityAdvisory("File Upload", "Path traversal risk", RiskLevel.CRITICAL,
                                     "User-controlled filename in file path", code_patterns=["f\"{upload_dir}/", "os.path.join"]),
                ],
            ),
            SecurityZone(
                name="Data Validation",
                risk_level=RiskLevel.HIGH,
                file_patterns=["*model*", "*schema*", "*valid*", "*dto*"],
                code_patterns=["BaseModel", "Field(", "validator", "model_validator"],
                advisories=[
                    SecurityAdvisory("Data Validation", "Missing input validation", RiskLevel.HIGH,
                                     "Endpoints without Pydantic validation", code_patterns=[]),
                    SecurityAdvisory("Data Validation", "Overly permissive schema", RiskLevel.MEDIUM,
                                     "Pydantic model with Any type or too many optional fields", code_patterns=["Any", "Optional[Any]"]),
                ],
            ),
            SecurityZone(
                name="Deployment",
                risk_level=RiskLevel.HIGH,
                file_patterns=["*deploy*", "*docker*", "*Dockerfile*", "*k8s*", "*helm*", "*prod*"],
                code_patterns=["debug=True", "reload=True", "allow_origins='*'"],
                advisories=[
                    SecurityAdvisory("Deployment", "Debug mode in production", RiskLevel.CRITICAL,
                                     "Debug mode enabled in production", code_patterns=["debug=True"]),
                    SecurityAdvisory("Deployment", "No rate limiting configured", RiskLevel.MEDIUM,
                                     "Production deployment without rate limiting", code_patterns=[]),
                ],
            ),
        ]

    def detect_zones(self, file_paths: List[str], code_contents: Optional[Dict[str, str]] = None) -> List[SecurityZone]:
        matched_zones: List[SecurityZone] = []
        for zone in self._zones:
            zone_copy = SecurityZone(
                name=zone.name, risk_level=zone.risk_level,
                file_patterns=zone.file_patterns, code_patterns=zone.code_patterns,
                advisories=list(zone.advisories),
                detection_count=0,
            )
            matched_advisories = []
            for advisory in zone.advisories:
                for fp in file_paths:
                    file_matches = False
                    for pattern in zone.file_patterns:
                        pat = pattern.replace("*", ".*")
                        if re.match(pat, fp, re.IGNORECASE):
                            file_matches = True
                            break
                    code_match = False
                    if code_contents and fp in code_contents:
                        content = code_contents[fp]
                        for cp in advisory.code_patterns:
                            if cp and cp.lower() in content.lower():
                                code_match = True
                                break
                    if advisory.code_patterns and not advisory.code_patterns[0]:
                        code_match = True

                    if file_matches or code_match:
                        zone_copy.detection_count += 1
                        matched_advisories.append(advisory)
                        break

            zone_copy.advisories = matched_advisories
            if zone_copy.detection_count > 0 or matched_advisories:
                matched_zones.append(zone_copy)

        return matched_zones

    def analyze_project(self, root_path: Path) -> Dict:
        files = list(root_path.rglob("*"))
        file_paths = [str(f.relative_to(root_path)) for f in files if f.is_file()]

        code_contents: Dict[str, str] = {}
        for f in files:
            if f.is_file() and f.suffix in (".py", ".ts", ".js", ".env", ".yaml", ".yml", ".toml", ".cfg", ".ini"):
                try:
                    if f.stat().st_size < 500 * 1024:
                        code_contents[str(f.relative_to(root_path))] = f.read_text(errors="ignore")
                except Exception:
                    pass

        zones = self.detect_zones(file_paths, code_contents)
        total_risk = sum(
            {"low": 1, "medium": 2, "high": 3, "critical": 4}[z.risk_level.value]
            for z in zones
        )
        max_possible = len(self._zones) * 4
        risk_score = total_risk / max_possible if max_possible > 0 else 0

        return {
            "zones": [z.to_dict() for z in zones],
            "total_zones_detected": len(zones),
            "risk_score": round(risk_score, 3),
            "risk_level": self._score_to_level(risk_score),
            "critical_zones": [z.name for z in zones if z.risk_level == RiskLevel.CRITICAL],
            "total_advisories": sum(len(z.advisories) for z in zones),
        }

    def _score_to_level(self, score: float) -> str:
        if score >= 0.7:
            return "critical"
        if score >= 0.4:
            return "high"
        if score >= 0.2:
            return "medium"
        return "low"
