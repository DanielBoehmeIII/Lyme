from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import json


class MigrationRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MigrationStep:
    step: str
    risk: MigrationRisk
    automated: bool = False
    verification_required: bool = True
    details: str = ""


@dataclass
class MigrationPath:
    source_framework: str
    target_framework: str
    overall_risk: MigrationRisk
    steps: List[MigrationStep]
    total_automated: int = 0
    total_manual: int = 0
    breaking_changes: List[str] = field(default_factory=list)
    compatibility_notes: List[str] = field(default_factory=list)
    estimated_effort: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_framework": self.source_framework,
            "target_framework": self.target_framework,
            "overall_risk": self.overall_risk.value,
            "steps": [{"step": s.step, "risk": s.risk.value, "automated": s.automated, "verification_required": s.verification_required} for s in self.steps],
            "total_automated": self.total_automated,
            "total_manual": self.total_manual,
            "breaking_changes": self.breaking_changes,
            "compatibility_notes": self.compatibility_notes,
            "estimated_effort": self.estimated_effort,
        }


class MigrationPathEngine:
    def __init__(self):
        self._paths = self._build_known_paths()

    def _build_known_paths(self) -> Dict[Tuple[str, str], MigrationPath]:
        paths = {}

        paths[("flask", "fastapi")] = MigrationPath(
            source_framework="Flask", target_framework="FastAPI",
            overall_risk=MigrationRisk.MEDIUM,
            steps=[
                MigrationStep("Replace route decorators with FastAPI equivalents", MigrationRisk.LOW, automated=True),
                MigrationStep("Add Pydantic models for request/response validation", MigrationRisk.LOW, automated=False),
                MigrationStep("Convert synchronous I/O to async/await", MigrationRisk.HIGH, automated=False),
                MigrationStep("Update dependency injection from global state to Depends()", MigrationRisk.MEDIUM, automated=True),
                MigrationStep("Replace Flask extensions with FastAPI-compatible libraries", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Update test suite from Flask test client to httpx TestClient", MigrationRisk.LOW, automated=True),
                MigrationStep("Add OpenAPI documentation configuration", MigrationRisk.LOW, automated=False),
                MigrationStep("Update deployment config (ASGI server instead of WSGI)", MigrationRisk.LOW, automated=True),
            ],
            breaking_changes=["Request/response model changes", "Async-first pattern requires await", "Extension compatibility"],
            compatibility_notes=["Flask-SQLAlchemy -> SQLAlchemy 2.0", "Flask-Migrate -> Alembic", "No direct Flask-Babel equivalent"],
            estimated_effort="2-4 weeks for medium app",
        )

        paths[("django", "fastapi")] = MigrationPath(
            source_framework="Django REST", target_framework="FastAPI",
            overall_risk=MigrationRisk.HIGH,
            steps=[
                MigrationStep("Replace DRF serializers with Pydantic models", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Replace DRF views with FastAPI route handlers", MigrationRisk.MEDIUM, automated=True),
                MigrationStep("Set up SQLAlchemy ORM to replace Django ORM", MigrationRisk.HIGH, automated=False),
                MigrationStep("Migrate database schema via Alembic instead of Django migrations", MigrationRisk.HIGH, automated=False),
                MigrationStep("Rewrite authentication middleware", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Convert admin panel or replace with alternative", MigrationRisk.HIGH, automated=False),
                MigrationStep("Update test suite", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Update deployment and ASGI configuration", MigrationRisk.LOW, automated=True),
            ],
            breaking_changes=["Complete ORM replacement", "No admin panel equivalent", "Auth system redesign"],
            compatibility_notes=["Django ORM features (query expressions, OR) need SQLAlchemy equivalents"],
            estimated_effort="4-12 weeks for medium app",
        )

        paths[("pydantic_v1", "pydantic_v2")] = MigrationPath(
            source_framework="Pydantic v1", target_framework="Pydantic v2",
            overall_risk=MigrationRisk.MEDIUM,
            steps=[
                MigrationStep("Replace @validator with @field_validator", MigrationRisk.LOW, automated=True),
                MigrationStep("Update Config class to model_config dict", MigrationRisk.LOW, automated=True),
                MigrationStep("Replace .dict() with .model_dump()", MigrationRisk.LOW, automated=True),
                MigrationStep("Handle strict mode changes", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Update custom types and validators", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Test serialization behavior changes", MigrationRisk.LOW, automated=False),
            ],
            breaking_changes=["Validator signature changes", "Config class removed", ".dict() removed in v2.1+"],
            compatibility_notes=["pydantic-settings replaces BaseSettings import path", "orm_mode -> model_config"],
            estimated_effort="1-3 days for medium project",
        )

        paths[("fastapi_below_100", "fastapi_100_plus")] = MigrationPath(
            source_framework="FastAPI <0.100", target_framework="FastAPI 0.100+",
            overall_risk=MigrationRisk.LOW,
            steps=[
                MigrationStep("Update Pydantic to v2 if not already", MigrationRisk.MEDIUM, automated=False),
                MigrationStep("Replace deprecated app.add_middleware() patterns", MigrationRisk.LOW, automated=True),
                MigrationStep("Adopt lifespan context manager instead of on_event", MigrationRisk.LOW, automated=True),
                MigrationStep("Update dependency overrides pattern if used", MigrationRisk.LOW, automated=True),
            ],
            breaking_changes=["on_event deprecated for lifespan", "Pydantic v2 required"],
            compatibility_notes=["Most code compatible without changes"],
            estimated_effort="Few hours for medium project",
        )

        return paths

    def find_path(self, source: str, target: str) -> Optional[MigrationPath]:
        return self._paths.get((source, target))

    def find_all_from(self, source: str) -> List[MigrationPath]:
        return [p for (s, _), p in self._paths.items() if s == source]

    def find_all_to(self, target: str) -> List[MigrationPath]:
        return [p for (_, t), p in self._paths.items() if t == target]

    def estimate_effort(self, source: str, target: str, repo_size_estimate: str = "medium") -> MigrationPath:
        path = self.find_path(source, target)
        if not path:
            effort = MigrationPath(
                source_framework=source, target_framework=target,
                overall_risk=MigrationRisk.HIGH,
                steps=[MigrationStep("Research migration path", MigrationRisk.MEDIUM, automated=False)],
                estimated_effort="Unknown - research required",
            )
            return effort

        multipliers = {"small": 0.5, "medium": 1.0, "large": 2.5, "xlarge": 5.0}
        mult = multipliers.get(repo_size_estimate, 1.0)
        path.estimated_effort = f"{int(path.total_manual * mult)}-{int(int(path.estimated_effort.split('-')[1].split()[0]) * mult)} days"
        return path

    def get_known_paths(self) -> List[Dict]:
        return [{"from": p.source_framework, "to": p.target_framework, "risk": p.overall_risk.value} for p in self._paths.values()]
