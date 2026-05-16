from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .observatory import (
    FrameworkObservatory, FrameworkSnapshot, APISnapshot,
    BreakingChange, MigrationTrend, ConventionEvolution,
    ConventionCategory,
)
import time


@dataclass
class FrameworkKnowledge:
    name: str
    ecosystem: str
    category: str
    current_version: str
    first_major_version: str
    description: str
    key_abstractions: List[str]
    typical_adoption_patterns: List[str]
    common_mistakes: List[str]
    migration_paths: List[Dict]
    strengths: List[str]
    weaknesses: List[str]


class FrameworkKnowledgeBase:
    def __init__(self):
        self._frameworks: Dict[str, FrameworkKnowledge] = {}
        self._load_known_frameworks()

    def _load_known_frameworks(self):
        self._frameworks["react"] = FrameworkKnowledge(
            name="React", ecosystem="javascript", category="ui_framework",
            current_version="18.3", first_major_version="0.14",
            description="Component-based UI library with virtual DOM, unidirectional data flow",
            key_abstractions=["Components", "Hooks", "JSX", "Virtual DOM", "Reconciliation"],
            typical_adoption_patterns=[
                "Incremental adoption in existing apps", "Create React App / Vite scaffolding",
                "Next.js for full-stack", "Component library pattern",
            ],
            common_mistakes=[
                "Mutating state directly", "Missing dependency arrays in hooks",
                "Overusing useEffect", "Prop drilling without context",
            ],
            migration_paths=[
                {"from": "class_components", "to": "hooks", "effort": "medium", "codemod": True},
                {"from": "react_16", "to": "react_18", "effort": "low", "codemod": True},
                {"from": "create_react_app", "to": "vite", "effort": "medium"},
            ],
            strengths=["Large ecosystem", "Excellent tooling", "Backward compatibility", "Huge community"],
            weaknesses=["Boilerplate", "Rendering optimization complexity", "Bundle size"],
        )

        self._frameworks["fastapi"] = FrameworkKnowledge(
            name="FastAPI", ecosystem="python", category="web_framework",
            current_version="0.115", first_major_version="0.1",
            description="Modern async Python web framework with automatic OpenAPI docs",
            key_abstractions=["Path operations", "Dependency injection", "Pydantic models", "ASGI"],
            typical_adoption_patterns=[
                "New API services", "Migration from Flask", "Microservices architecture",
                "ML model serving",
            ],
            common_mistakes=[
                "Sync I/O in async endpoints", "Missing lifespan handlers",
                "Pydantic v1/v2 incompatibility", "CORS misconfiguration",
            ],
            migration_paths=[
                {"from": "flask", "to": "fastapi", "effort": "hard"},
                {"from": "django_rest", "to": "fastapi", "effort": "hard"},
                {"from": "fastapi_below_100", "to": "fastapi_100_plus", "effort": "low"},
            ],
            strengths=["Performance", "Auto docs", "Type safety", "Async native"],
            weaknesses=["Younger ecosystem", "Less middleware", "ORM agnostic"],
        )

        self._frameworks["nextjs"] = FrameworkKnowledge(
            name="Next.js", ecosystem="javascript", category="meta_framework",
            current_version="14.2", first_major_version="1.0",
            description="React meta-framework with SSR, SSG, and server components",
            key_abstractions=["File-based routing", "Server components", "App Router", "Middleware"],
            typical_adoption_patterns=[
                "New React projects", "Migrating from CRA", "E-commerce sites",
                "Content sites with ISR",
            ],
            common_mistakes=[
                "Client/server component boundary violations", "Missing 'use client' directive",
                "Overusing client components", "Data fetching without caching",
            ],
            migration_paths=[
                {"from": "pages_router", "to": "app_router", "effort": "hard"},
                {"from": "next_12", "to": "next_14", "effort": "medium"},
                {"from": "create_react_app", "to": "nextjs", "effort": "medium"},
            ],
            strengths=["SSR/SSG/ISR", "File routing", "Image optimization", "Server components"],
            weaknesses=["Opinionated", "Learning curve for App Router", "Build complexity"],
        )

    def get(self, name: str) -> Optional[FrameworkKnowledge]:
        return self._frameworks.get(name.lower())

    def list_frameworks(self) -> List[str]:
        return list(self._frameworks.keys())

    def compare_frameworks(self, name_a: str, name_b: str) -> Dict:
        a = self.get(name_a)
        b = self.get(name_b)
        if not a or not b:
            return {"error": "Framework not found"}
        return {
            "comparison": f"{a.name} vs {b.name}",
            "a_strengths": list(set(a.strengths) - set(b.strengths)),
            "b_strengths": list(set(b.strengths) - set(a.strengths)),
            "common_strengths": list(set(a.strengths) & set(b.strengths)),
            "a_mistakes": a.common_mistakes[:3],
            "b_mistakes": b.common_mistakes[:3],
            "a_migration_paths": a.migration_paths,
            "b_migration_paths": b.migration_paths,
        }


class ReactEcosystemKnowledge:
    @staticmethod
    def build_observatory() -> FrameworkObservatory:
        obs = FrameworkObservatory()
        now = time.time()

        versions = [
            ("16.8", 33000, ["components", "lifecycle", "setState"], ["useState", "useEffect", "useContext"], 30),
            ("17.0", 34000, ["components", "lifecycle"], ["hooks", "context"], 25),
            ("18.0", 34500, ["concurrent rendering", "automatic batching"], ["useId", "useTransition", "useDeferredValue"], 15),
            ("18.3", 34800, ["server components", "actions"], ["useOptimistic", "useFormStatus", "use"], 10),
        ]

        for ver, ts, arch_trends, new_apis, bug_count in versions:
            api = APISnapshot(
                framework="React", version=ver, timestamp=ts,
                public_api_count=50 + bug_count * 2,
                exported_symbols=list(new_apis),
                method_signatures={api: "standard" for api in new_apis},
                decorator_patterns=[], configuration_keys=[],
            )

            snapshot = FrameworkSnapshot(
                framework="React", version=ver, timestamp=ts, api=api,
                common_bug_patterns=[
                    {"pattern": "Hook dependency array mismatch", "frequency": 0.3 + bug_count * 0.01},
                    {"pattern": "State mutation", "frequency": 0.2},
                ],
                convention_shifts=[
                    ConventionEvolution(ConventionCategory.STATE_MANAGEMENT,
                                        "Hooks pattern", "16.8", ver),
                    ConventionEvolution(ConventionCategory.ARCHITECTURE,
                                        "Functional components", "16.8", ver),
                ],
                ecosystem_migrations=[
                    MigrationTrend("Class components", "Hooks", "2020-2022", 500000,
                                   ["Better DX", "Code reuse"], ["Migration cost"], 0.6, 0.7),
                ],
                architectural_trends=list(arch_trends),
                community_health={"overall_score": 0.85 + 0.05 * (bug_count < 20), "npm_downloads": f"{200 + bug_count * 5}M/week"},
            )
            obs.record_snapshot(snapshot)

        obs.record_breaking_change(BreakingChange("React", "16.x", "17.0", "event_pooling",
                                                   "removal", "Event pooling removed", ["Remove event.persist() calls"], 0.3, 0.4))
        obs.record_breaking_change(BreakingChange("React", "17.x", "18.0", "render",
                                                   "change", "Strict mode effects run twice", ["Adjust effect cleanup"], 0.5, 0.6))
        return obs


class FastAPIEcosystemKnowledge:
    @staticmethod
    def build_observatory() -> FrameworkObservatory:
        obs = FrameworkObservatory()
        now = time.time()

        versions = [
            ("0.1", 32000, ["path operations", "dependency injection"], 10),
            ("0.50", 34000, ["WebSocket support", "middleware"], 20),
            ("0.100", 35000, ["Pydantic v2", "lifespan"], 15),
            ("0.115", 35500, ["Annotated validators", "openapi 3.1"], 8),
        ]

        for ver, ts, trends, bug_count in versions:
            api = APISnapshot(
                framework="FastAPI", version=ver, timestamp=ts,
                public_api_count=30 + bug_count * 2,
                exported_symbols=["FastAPI", "APIRouter", "Depends", "Query", "Path", "Body"],
                method_signatures={"get": "standard", "post": "standard"},
                decorator_patterns=["@app.get", "@app.post", "@app.middleware"],
                configuration_keys=["title", "version", "docs_url", "redoc_url"],
            )

            snapshot = FrameworkSnapshot(
                framework="FastAPI", version=ver, timestamp=ts, api=api,
                common_bug_patterns=[
                    {"pattern": "Sync endpoint blocking event loop", "frequency": 0.3},
                    {"pattern": "Pydantic v1/v2 incompatibility", "frequency": 0.25 if ver >= "0.100" else 0.1},
                    {"pattern": "Missing ASGI lifespan handler", "frequency": 0.15},
                ],
                convention_shifts=[
                    ConventionEvolution(ConventionCategory.API_DESIGN, "Dependency injection with Depends", "0.1", "0.50"),
                    ConventionEvolution(ConventionCategory.ARCHITECTURE, "Router/Service/Repository", "0.50", ver),
                    ConventionEvolution(ConventionCategory.ERROR_HANDLING, "Centralized exception handlers", "0.50", ver),
                ],
                ecosystem_migrations=[
                    MigrationTrend("Flask", "FastAPI", "2021-2024", 200000,
                                   ["Async support", "Auto docs", "Type safety"],
                                   ["Migration cost", "Extension compatibility"], 0.5, 0.3),
                ],
                architectural_trends=list(trends),
                community_health={"overall_score": 0.8 + 0.1 * (bug_count < 12), "pypi_downloads": f"{10 + bug_count * 5}M/week"},
            )
            obs.record_snapshot(snapshot)

        return obs


class RustAsyncEcosystemKnowledge:
    @staticmethod
    def build_observatory() -> FrameworkObservatory:
        obs = FrameworkObservatory()

        versions = [
            ("tokio_0.1", 30000, ["event loop", "tasks"], 20),
            ("tokio_0.2", 32000, ["async/await stabilization"], 15),
            ("tokio_1.0", 34000, ["tokio::main", "select"], 10),
            ("tokio_1.39", 35000, ["cooperative scheduling"], 5),
        ]

        for ver, ts, trends, bug_count in versions:
            api = APISnapshot(
                framework="Tokio", version=ver, timestamp=ts,
                public_api_count=40 - bug_count,
                exported_symbols=["tokio::main", "spawn", "select"],
                method_signatures={"spawn": "async fn"},
                decorator_patterns=["#[tokio::main]"],
                configuration_keys=[],
            )

            snapshot = FrameworkSnapshot(
                framework="Tokio", version=ver, timestamp=ts, api=api,
                common_bug_patterns=[
                    {"pattern": "Blocking in async context", "frequency": 0.3},
                    {"pattern": "Task cancellation safety", "frequency": 0.2 if ver >= "tokio_1.0" else 0.1},
                ],
                convention_shifts=[
                    ConventionEvolution(ConventionCategory.ARCHITECTURE, "async/await everywhere", "tokio_0.2", ver),
                ],
                ecosystem_migrations=[
                    MigrationTrend("async-std", "Tokio", "2021-2024", 100000,
                                   ["Ecosystem dominance", "Performance", "Maintenance"],
                                   ["Migration cost", "API differences"], 0.7, 0.5),
                ],
                architectural_trends=list(trends),
                community_health={"overall_score": 0.7 + 0.2 * (bug_count < 10)},
            )
            obs.record_snapshot(snapshot)

        return obs


class NextJSEcosystemKnowledge:
    @staticmethod
    def build_observatory() -> FrameworkObservatory:
        obs = FrameworkObservatory()

        versions = [
            ("10", 31000, ["static generation", "ISR"], 25),
            ("12", 33000, ["middleware", "SWC compiler"], 20),
            ("13", 34000, ["App Router", "server components"], 15),
            ("14", 35000, ["server actions", "partial prerendering"], 10),
        ]

        for ver, ts, trends, bug_count in versions:
            api = APISnapshot(
                framework="Next.js", version=ver, timestamp=ts,
                public_api_count=40 + bug_count,
                exported_symbols=["NextRequest", "NextResponse", "Image", "Link", "notFound"],
                method_signatures={"getServerSideProps": "async", "getStaticProps": "async"},
                decorator_patterns=[],
                configuration_keys=["next.config.js", "next.config.mjs"],
            )

            snapshot = FrameworkSnapshot(
                framework="Next.js", version=ver, timestamp=ts, api=api,
                common_bug_patterns=[
                    {"pattern": "Server/client component boundary", "frequency": 0.3 if ver >= "13" else 0.1},
                    {"pattern": "Missing 'use client' directive", "frequency": 0.25 if ver >= "13" else 0.05},
                    {"pattern": "Data fetching in wrong component", "frequency": 0.2},
                ],
                convention_shifts=[
                    ConventionEvolution(ConventionCategory.ARCHITECTURE, "Server components first", "13", ver),
                    ConventionEvolution(ConventionCategory.DATA_FETCHING, "fetch() with caching", "13", ver),
                    ConventionEvolution(ConventionCategory.STATE_MANAGEMENT, "Server state over client", "13", ver),
                ],
                ecosystem_migrations=[
                    MigrationTrend("Pages Router", "App Router", "2023-2025", 300000,
                                   ["Better performance", "Server components", "Layouts"],
                                   ["Migration complexity", "API changes"], 0.4, 0.25),
                ],
                architectural_trends=list(trends),
                community_health={"overall_score": 0.75 + 0.1 * (bug_count < 15)},
            )
            obs.record_snapshot(snapshot)

        return obs
