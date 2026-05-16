from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import time


@dataclass
class FrameworkInfluence:
    framework: str
    influence_score: float
    influenced_by: List[str]
    influenced: List[str]
    peak_period: str
    current_trend: str
    descendant_frameworks: List[str]

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework,
            "influence_score": self.influence_score,
            "influenced_by": self.influenced_by,
            "influenced": self.influenced,
            "peak_period": self.peak_period,
            "current_trend": self.current_trend,
            "descendant_frameworks": self.descendant_frameworks,
        }


@dataclass
class MigrationPathway:
    from_framework: str
    to_framework: str
    volume: int
    period: str
    primary_reason: str
    difficulty: str
    typical_duration: str

    def to_dict(self) -> Dict:
        return {
            "from_framework": self.from_framework,
            "to_framework": self.to_framework,
            "volume": self.volume,
            "period": self.period,
            "primary_reason": self.primary_reason,
            "difficulty": self.difficulty,
            "typical_duration": self.typical_duration,
        }


@dataclass
class DependencyEmpire:
    root_library: str
    ecosystem: str
    total_dependents: int
    transitive_depth: int
    market_share: float
    competing_libraries: List[str]
    growth_trend: str
    risk_score: float

    def to_dict(self) -> Dict:
        return {
            "root_library": self.root_library,
            "ecosystem": self.ecosystem,
            "total_dependents": self.total_dependents,
            "transitive_depth": self.transitive_depth,
            "market_share": self.market_share,
            "competing_libraries": self.competing_libraries,
            "growth_trend": self.growth_trend,
            "risk_score": self.risk_score,
        }


@dataclass
class AbstractionLineage:
    abstraction: str
    origin_framework: str
    year_introduced: int
    adopted_by: List[str]
    original_form: str
    current_form: str
    evolutionary_pressure: str
    predicted_next_form: str

    def to_dict(self) -> Dict:
        return {
            "abstraction": self.abstraction,
            "origin_framework": self.origin_framework,
            "year_introduced": self.year_introduced,
            "adopted_by": self.adopted_by,
            "original_form": self.original_form,
            "current_form": self.current_form,
            "evolutionary_pressure": self.evolutionary_pressure,
            "predicted_next_form": self.predicted_next_form,
        }


@dataclass
class RepairCulture:
    name: str
    ecosystem: str
    common_patterns: List[str]
    typical_approaches: List[str]
    tooling: List[str]
    community_practices: List[str]
    effectiveness_score: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "ecosystem": self.ecosystem,
            "common_patterns": self.common_patterns,
            "typical_approaches": self.typical_approaches,
            "tooling": self.tooling,
            "community_practices": self.community_practices,
            "effectiveness_score": self.effectiveness_score,
        }


@dataclass
class EcosystemCivilization:
    name: str
    primary_languages: List[str]
    estimated_population: int
    total_packages: int
    health_score: float
    diversity_index: float
    dominant_frameworks: List[FrameworkInfluence]
    major_migrations: List[MigrationPathway]
    large_dependency_empires: List[DependencyEmpire]
    abstraction_lineages: List[AbstractionLineage]
    repair_cultures: List[RepairCulture]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "primary_languages": self.primary_languages,
            "estimated_population": self.estimated_population,
            "total_packages": self.total_packages,
            "health_score": self.health_score,
            "diversity_index": self.diversity_index,
            "dominant_frameworks": [f.to_dict() for f in self.dominant_frameworks[:5]],
            "major_migrations": [m.to_dict() for m in self.major_migrations[:5]],
            "large_dependency_empires": [e.to_dict() for e in self.large_dependency_empires[:5]],
            "abstraction_lineages": [a.to_dict() for a in self.abstraction_lineages[:5]],
            "repair_cultures": [r.to_dict() for r in self.repair_cultures],
        }


@dataclass
class CivilizationMap:
    civilizations: List[EcosystemCivilization]
    cross_civilization_influence: Dict[str, List[str]]
    global_health_score: float
    total_packages_across_civilizations: int

    def to_dict(self) -> Dict:
        return {
            "civilizations": [c.to_dict() for c in self.civilizations],
            "cross_civilization_influence": self.cross_civilization_influence,
            "global_health_score": self.global_health_score,
            "total_packages_across_civilizations": self.total_packages_across_civilizations,
        }

    def to_html(self) -> str:
        civ_html = ""
        for civ in self.civilizations:
            frameworks = ", ".join(f.name for f in civ.dominant_frameworks[:5])
            migrations = "".join(f"<li>{m.from_framework} → {m.to_framework} ({m.volume:,})</li>" for m in civ.major_migrations[:5])
            civ_html += f"""
            <div style='margin:20px 0;padding:16px;background:#2a2a4e;border-radius:8px'>
                <h3>{civ.name}</h3>
                <p>Languages: {', '.join(civ.primary_languages)} | Population: {civ.estimated_population:,} | Health: {civ.health_score:.0%}</p>
                <p>Dominant: {frameworks}</p>
                <p>Packages: {civ.total_packages:,} | Diversity: {civ.diversity_index:.2f}</p>
                <h4>Major Migrations</h4>
                <ul>{migrations}</ul>
            </div>"""

        return f"""<!DOCTYPE html>
<html><head><title>Software Civilization Map</title>
<style>body{{background:#1a1a2e;color:#eee;font-family:sans-serif;padding:40px}} h2{{border-bottom:1px solid #444;padding-bottom:8px}}</style></head><body>
<h1>Software Civilization Map</h1>
<p>Global Health: {self.global_health_score:.0%} | Total Packages: {self.total_packages_across_civilizations:,} | Civilizations: {len(self.civilizations)}</p>
{civ_html}
</body></html>"""


class SoftwareCivilizationMapper:
    def __init__(self):
        self._knowledge = self._init_knowledge()

    def _init_knowledge(self) -> Dict[str, Any]:
        return {
            "python": {
                "frameworks": {
                    "Django": {"influence_score": 0.85, "influenced_by": ["Ruby on Rails"], "influenced": ["FastAPI", "Flask"], "peak": "2015-2020", "trend": "mature_stable", "descendants": ["Wagtail", "CMS"]},
                    "Flask": {"influence_score": 0.7, "influenced_by": ["Sinatra"], "influenced": ["FastAPI", "Quart"], "peak": "2018-2022", "trend": "gradual_decline", "descendants": ["Quart"]},
                    "FastAPI": {"influence_score": 0.8, "influenced_by": ["Flask", "Starlette"], "influenced": ["Litestar", "Starlite"], "peak": "2022-present", "trend": "rapid_growth", "descendants": ["Litestar"]},
                },
                "migrations": [
                    ("Flask", "FastAPI", 200000, "2021-2025", "Async support needed", "medium", "2-4 weeks"),
                    ("Django REST", "FastAPI", 80000, "2022-2025", "Performance requirements", "hard", "4-12 weeks"),
                ],
                "empires": [
                    ("numpy", "python", 2000000, 5, 0.85, ["jax", "cupy"], "growing", 0.2),
                    ("requests", "python", 1500000, 3, 0.75, ["httpx", "aiohttp"], "stable", 0.15),
                    ("pydantic", "python", 800000, 4, 0.7, ["attrs", "marshmallow"], "growing", 0.1),
                ],
                "abstractions": [
                    ("ASGI", "Starlette", 2018, ["FastAPI", "Django Channels", "Quart"], "WSGI-inspired async protocol", "Mature async server standard", "HTTP/3 adaptation", "HTTP/3 native ASGI"),
                    ("Dependency Injection", "FastAPI", 2018, ["Litestar", "BlackSheep"], "Simple parameter injection", "Type-annotated Depends()", "AOT compilation", "Compile-time DI resolution"),
                ],
                "repair": RepairCulture("Python Testing Culture", "python",
                    ["Write tests first", "Use pytest fixtures", "Mock external services", "Property-based testing"],
                    ["TDD", "BDD", "Hypothesis testing"], ["pytest", "tox", "pre-commit", "mypy"],
                    ["Code review", "CI/CD gates", "Test coverage targets"], 0.8),
            },
            "javascript": {
                "frameworks": {
                    "React": {"influence_score": 0.95, "influenced_by": [], "influenced": ["Next.js", "Gatsby", "Remix"], "peak": "2019-present", "trend": "dominant", "descendants": []},
                    "Next.js": {"influence_score": 0.85, "influenced_by": ["React"], "influenced": ["Remix", "Astro"], "peak": "2022-present", "trend": "rapid_growth", "descendants": []},
                    "Vue": {"influence_score": 0.65, "influenced_by": ["Angular", "React"], "influenced": ["Nuxt", "VitePress"], "peak": "2020-2023", "trend": "stable", "descendants": []},
                },
                "migrations": [
                    ("Create React App", "Next.js", 300000, "2022-2025", "Better DX and performance", "medium", "1-4 weeks"),
                    ("Pages Router", "App Router", 250000, "2023-2025", "Server components", "hard", "2-6 weeks"),
                    ("Redux", "Zustand", 200000, "2022-2025", "Simplicity", "low", "1-2 weeks"),
                    ("Webpack", "Vite", 500000, "2022-2025", "Build speed", "medium", "1-3 weeks"),
                ],
                "empires": [
                    ("react", "javascript", 3000000, 4, 0.9, ["vue", "svelte", "angular"], "stable", 0.15),
                    ("typescript", "javascript", 2500000, 2, 0.85, ["flow"], "growing", 0.1),
                    ("nextjs", "javascript", 1000000, 3, 0.6, ["remix", "astro"], "growing", 0.2),
                ],
                "abstractions": [
                    ("Virtual DOM", "React", 2013, ["Preact", "Inferno", "Vue"], "DOM diffing algorithm", "Fiber reconciliation", "Server components", "Compile-time VDOM elimination"),
                    ("Hooks", "React", 2018, ["Vue Composition API", "Solid Signals", "Preact Hooks"], "Class-based lifecycle", "Functional hooks", "Compiler-optimized", "Automatic dependency tracking"),
                    ("File-based Routing", "Next.js", 2016, ["Nuxt", "SvelteKit", "Remix", "Astro"], "Manual route config", "Convention-based file routes", "Hybrid routing", "AI-generated routes"),
                ],
                "repair": RepairCulture("JavaScript Testing Culture", "javascript",
                    ["Component testing", "Integration over unit", "Snapshot testing", "E2E critical paths"],
                    ["TDD", "Visual regression", "Storybook-driven"], ["vitest", "playwright", "cypress", "testing-library"],
                    ["CI pipelines", "Bundle size budgets", "A11y checks"], 0.7),
            },
            "rust": {
                "frameworks": {
                    "Tokio": {"influence_score": 0.9, "influenced_by": [], "influenced": ["Axum", "Tower", "Hyper"], "peak": "2021-present", "trend": "dominant", "descendants": []},
                    "Axum": {"influence_score": 0.7, "influenced_by": ["Tokio", "Tower"], "influenced": [], "peak": "2023-present", "trend": "rapid_growth", "descendants": []},
                },
                "migrations": [
                    ("async-std", "Tokio", 50000, "2021-2024", "Ecosystem consolidation", "medium", "1-3 weeks"),
                    ("Rocket", "Axum", 30000, "2022-2025", "Better ecosystem integration", "medium", "2-4 weeks"),
                ],
                "empires": [
                    ("tokio", "rust", 500000, 4, 0.9, ["async-std", "smol"], "growing", 0.1),
                    ("serde", "rust", 400000, 2, 0.95, [], "stable", 0.05),
                    ("clap", "rust", 200000, 1, 0.7, ["structopt"], "stable", 0.08),
                ],
                "abstractions": [
                    ("Async/Await", "Rust", 2019, ["Python", "C#", "JS", "C++20"], "Callback-based async", "async/await with futures", "Structured concurrency", "Algebraic effects"),
                    ("Ownership System", "Rust", 2015, ["Mojo", "Zig"], "Manual memory management", "Borrow checker", "Region-based memory", "Proof-carrying code"),
                ],
                "repair": RepairCulture("Rust Repair Culture", "rust",
                    ["Compiler-driven fixes", "Clippy linting", "Semver-aware changes"],
                    ["Fix compilations first", "Edition-based migrations"], ["cargo", "clippy", "rust-analyzer", "cargo-audit"],
                    ["Edition migrations", "RFC process", "Crater testing"], 0.9),
            },
        }

    def map_civilization(self, ecosystem: str) -> Optional[EcosystemCivilization]:
        knowledge = self._knowledge.get(ecosystem)
        if not knowledge:
            return None

        frameworks_data = knowledge.get("frameworks", {})
        frameworks = [
            FrameworkInfluence(
                framework=name,
                influence_score=details["influence_score"],
                influenced_by=details.get("influenced_by", []),
                influenced=details.get("influenced", []),
                peak_period=details.get("peak", ""),
                current_trend=details.get("trend", ""),
                descendant_frameworks=details.get("descendants", []),
            )
            for name, details in frameworks_data.items()
        ]

        migrations = [
            MigrationPathway(
                from_framework=m[0], to_framework=m[1], volume=m[2],
                period=m[3], primary_reason=m[4], difficulty=m[5],
                typical_duration=m[6],
            )
            for m in knowledge.get("migrations", [])
        ]

        empires = [
            DependencyEmpire(
                root_library=e[0], ecosystem=e[1], total_dependents=e[2],
                transitive_depth=e[3], market_share=e[4],
                competing_libraries=e[5], growth_trend=e[6], risk_score=e[7],
            )
            for e in knowledge.get("empires", [])
        ]

        abstractions = [
            AbstractionLineage(
                abstraction=a[0], origin_framework=a[1], year_introduced=a[2],
                adopted_by=a[3], original_form=a[4], current_form=a[5],
                evolutionary_pressure=a[6], predicted_next_form=a[7],
            )
            for a in knowledge.get("abstractions", [])
        ]

        repair = knowledge.get("repair")

        diversity = len(frameworks_data) / 10
        health = sum(f.influence_score for f in frameworks) / max(1, len(frameworks)) if frameworks else 0.5

        return EcosystemCivilization(
            name=ecosystem.title(),
            primary_languages=[ecosystem],
            estimated_population=self._estimate_population(ecosystem),
            total_packages=self._estimate_packages(ecosystem),
            health_score=round(health * 0.7 + 0.3, 3),
            diversity_index=round(diversity, 3),
            dominant_frameworks=frameworks,
            major_migrations=migrations,
            large_dependency_empires=empires,
            abstraction_lineages=abstractions,
            repair_cultures=[repair] if repair else [],
        )

    def _estimate_population(self, ecosystem: str) -> int:
        pops = {"python": 8000000, "javascript": 12000000, "rust": 2000000}
        return pops.get(ecosystem, 1000000)

    def _estimate_packages(self, ecosystem: str) -> int:
        pkgs = {"python": 500000, "javascript": 2000000, "rust": 150000}
        return pkgs.get(ecosystem, 100000)

    def build_civilization_map(self) -> CivilizationMap:
        ecosystems = ["python", "javascript", "rust"]
        civilizations = []

        for eco in ecosystems:
            civ = self.map_civilization(eco)
            if civ:
                civilizations.append(civ)

        cross_influence = {
            "python": ["javascript"],
            "javascript": ["python", "rust"],
            "rust": ["python", "javascript"],
        }

        total_pkgs = sum(c.total_packages for c in civilizations)
        health_scores = [c.health_score * c.total_packages for c in civilizations]
        global_health = sum(health_scores) / max(1, total_pkgs) if total_pkgs else 0

        return CivilizationMap(
            civilizations=civilizations,
            cross_civilization_influence=cross_influence,
            global_health_score=round(global_health, 3),
            total_packages_across_civilizations=total_pkgs,
        )

    def save(self, path: str):
        cm = self.build_civilization_map()
        with open(path, "w") as f:
            json.dump(cm.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> CivilizationMap:
        with open(path) as f:
            data = json.load(f)
        mapper = cls()
        return CivilizationMap(**data)
