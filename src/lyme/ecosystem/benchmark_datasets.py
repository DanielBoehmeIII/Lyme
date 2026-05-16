from __future__ import annotations
from typing import Dict, List, Optional
from .dependency_engine import (
    DependencyGraphEngine, LibraryNode, DependencyEdge,
    DependencyType, EcosystemPhase,
)
from .propagation import PropagationEvent
import json
import uuid
import math
import random


class EcosystemBenchmarkDatasets:
    @staticmethod
    def build_python_web_ecosystem() -> DependencyGraphEngine:
        engine = DependencyGraphEngine()
        libs = [
            LibraryNode("flask", "Flask", "3.0", "python", category="web_framework",
                        latest_version="3.0", release_count=120, release_frequency=0.8,
                        adoption_rate=0.7, abandonment_risk=0.2, centrality=0.8, phase=EcosystemPhase.MATURE),
            LibraryNode("fastapi", "FastAPI", "0.115", "python", category="web_framework",
                        latest_version="0.115", release_count=80, release_frequency=0.9,
                        adoption_rate=0.85, abandonment_risk=0.05, centrality=0.9, phase=EcosystemPhase.GROWING),
            LibraryNode("django", "Django", "5.0", "python", category="web_framework",
                        latest_version="5.0", release_count=200, release_frequency=0.6,
                        adoption_rate=0.75, abandonment_risk=0.1, centrality=0.85, phase=EcosystemPhase.MATURE),
            LibraryNode("starlette", "Starlette", "0.40", "python", category="asgi",
                        latest_version="0.40", release_count=60, release_frequency=0.7,
                        adoption_rate=0.8, abandonment_risk=0.05, centrality=0.7, phase=EcosystemPhase.MATURE),
            LibraryNode("pydantic", "Pydantic", "2.0", "python", category="validation",
                        latest_version="2.10", release_count=90, release_frequency=0.85,
                        adoption_rate=0.9, abandonment_risk=0.02, centrality=0.85, phase=EcosystemPhase.GROWING),
            LibraryNode("sqlalchemy", "SQLAlchemy", "2.0", "python", category="orm",
                        latest_version="2.0", release_count=150, release_frequency=0.5,
                        adoption_rate=0.8, abandonment_risk=0.1, centrality=0.8, phase=EcosystemPhase.MATURE),
            LibraryNode("alembic", "Alembic", "1.13", "python", category="migration",
                        latest_version="1.13", release_count=40, release_frequency=0.3,
                        adoption_rate=0.7, abandonment_risk=0.15, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("uvicorn", "Uvicorn", "0.30", "python", category="server",
                        latest_version="0.30", release_count=50, release_frequency=0.4,
                        adoption_rate=0.85, abandonment_risk=0.05, centrality=0.7, phase=EcosystemPhase.MATURE),
            LibraryNode("gunicorn", "Gunicorn", "22.0", "python", category="server",
                        latest_version="22.0", release_count=30, release_frequency=0.2,
                        adoption_rate=0.6, abandonment_risk=0.3, centrality=0.5, phase=EcosystemPhase.DECLINING),
            LibraryNode("httpx", "HTTPX", "0.27", "python", category="http_client",
                        latest_version="0.27", release_count=45, release_frequency=0.5,
                        adoption_rate=0.75, abandonment_risk=0.1, centrality=0.6, phase=EcosystemPhase.MATURE),
            LibraryNode("celery", "Celery", "5.3", "python", category="task_queue",
                        latest_version="5.3", release_count=100, release_frequency=0.3,
                        adoption_rate=0.6, abandonment_risk=0.25, centrality=0.6, phase=EcosystemPhase.MATURE),
            LibraryNode("redis_py", "redis-py", "5.0", "python", category="cache",
                        latest_version="5.0", release_count=60, release_frequency=0.3,
                        adoption_rate=0.7, abandonment_risk=0.15, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("asyncpg", "asyncpg", "0.29", "python", category="database_driver",
                        latest_version="0.29", release_count=35, release_frequency=0.3,
                        adoption_rate=0.65, abandonment_risk=0.15, centrality=0.4, phase=EcosystemPhase.MATURE),
            LibraryNode("aiosqlite", "aiosqlite", "0.20", "python", category="database_driver",
                        latest_version="0.20", release_count=15, release_frequency=0.2,
                        adoption_rate=0.4, abandonment_risk=0.3, centrality=0.3, phase=EcosystemPhase.MATURE),
            LibraryNode("orjson", "orjson", "3.9", "python", category="serialization",
                        latest_version="3.9", release_count=25, release_frequency=0.4,
                        adoption_rate=0.5, abandonment_risk=0.15, centrality=0.4, phase=EcosystemPhase.MATURE),
            LibraryNode("pytest", "pytest", "8.0", "python", category="testing",
                        latest_version="8.0", release_count=120, release_frequency=0.5,
                        adoption_rate=0.9, abandonment_risk=0.02, centrality=0.7, phase=EcosystemPhase.MATURE),
            LibraryNode("mypy", "mypy", "1.10", "python", category="static_analysis",
                        latest_version="1.10", release_count=80, release_frequency=0.4,
                        adoption_rate=0.7, abandonment_risk=0.1, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("ruff", "Ruff", "0.5", "python", category="linting",
                        latest_version="0.5", release_count=90, release_frequency=0.9,
                        adoption_rate=0.85, abandonment_risk=0.05, centrality=0.6, phase=EcosystemPhase.GROWING),
            LibraryNode("sentry_sdk", "Sentry SDK", "2.0", "python", category="monitoring",
                        latest_version="2.0", release_count=70, release_frequency=0.5,
                        adoption_rate=0.6, abandonment_risk=0.1, centrality=0.4, phase=EcosystemPhase.MATURE),
            LibraryNode("opentelemetry", "OpenTelemetry Python", "1.25", "python", category="observability",
                        latest_version="1.25", release_count=60, release_frequency=0.6,
                        adoption_rate=0.5, abandonment_risk=0.1, centrality=0.4, phase=EcosystemPhase.GROWING),
            LibraryNode("python_jose", "python-jose", "3.3", "python", category="auth",
                        latest_version="3.3", release_count=20, release_frequency=0.1,
                        adoption_rate=0.4, abandonment_risk=0.6, centrality=0.3, phase=EcosystemPhase.DECLINING),
            LibraryNode("passlib", "Passlib", "1.7", "python", category="auth",
                        latest_version="1.7", release_count=10, release_frequency=0.05,
                        adoption_rate=0.3, abandonment_risk=0.7, centrality=0.3, phase=EcosystemPhase.DECLINING),
        ]

        for lib in libs:
            engine.add_library(lib)

        edges = [
            ("fastapi", "starlette", DependencyType.DIRECT, ">=0.40", 1.0),
            ("fastapi", "pydantic", DependencyType.DIRECT, ">=2.0", 1.0),
            ("fastapi", "uvicorn", DependencyType.PEER, ">=0.30", 0.9),
            ("fastapi", "httpx", DependencyType.PEER, ">=0.27", 0.7),
            ("fastapi", "sqlalchemy", DependencyType.OPTIONAL, ">=2.0", 0.6),
            ("fastapi", "ruff", DependencyType.DEV, ">=0.5", 0.5),
            ("flask", "pydantic", DependencyType.OPTIONAL, ">=2.0", 0.3),
            ("flask", "sqlalchemy", DependencyType.OPTIONAL, ">=2.0", 0.6),
            ("django", "celery", DependencyType.OPTIONAL, ">=5.3", 0.5),
            ("django", "pytest", DependencyType.DEV, ">=8.0", 0.7),
            ("sqlalchemy", "alembic", DependencyType.PEER, ">=1.13", 0.8),
            ("sqlalchemy", "asyncpg", DependencyType.OPTIONAL, ">=0.29", 0.6),
            ("sqlalchemy", "aiosqlite", DependencyType.OPTIONAL, ">=0.20", 0.4),
            ("uvicorn", "gunicorn", DependencyType.PEER, ">=22.0", 0.5),
            ("pytest", "httpx", DependencyType.OPTIONAL, ">=0.27", 0.6),
            ("celery", "redis_py", DependencyType.OPTIONAL, ">=5.0", 0.8),
            ("sentry_sdk", "fastapi", DependencyType.OPTIONAL, ">=0.100", 0.5),
            ("opentelemetry", "fastapi", DependencyType.OPTIONAL, ">=0.100", 0.4),
            ("ruff", "mypy", DependencyType.PEER, ">=1.10", 0.6),
            ("fastapi", "orjson", DependencyType.OPTIONAL, ">=3.9", 0.5),
        ]

        for src, tgt, dtype, constraint, weight in edges:
            edge = DependencyEdge(
                id=f"e_{uuid.uuid4().hex[:8]}",
                source_id=src, target_id=tgt, dep_type=dtype,
                version_constraint=constraint, weight=weight,
            )
            engine.add_dependency(edge)

        return engine

    @staticmethod
    def build_js_frontend_ecosystem() -> DependencyGraphEngine:
        engine = DependencyGraphEngine()
        libs = [
            LibraryNode("react", "React", "18.3", "javascript", category="ui_framework",
                        latest_version="18.3", release_count=80, release_frequency=0.6,
                        adoption_rate=0.95, abandonment_risk=0.02, centrality=0.95, phase=EcosystemPhase.DOMINANT),
            LibraryNode("nextjs", "Next.js", "14.2", "javascript", category="meta_framework",
                        latest_version="14.2", release_count=120, release_frequency=0.9,
                        adoption_rate=0.85, abandonment_risk=0.03, centrality=0.85, phase=EcosystemPhase.GROWING),
            LibraryNode("vue", "Vue.js", "3.4", "javascript", category="ui_framework",
                        latest_version="3.4", release_count=70, release_frequency=0.5,
                        adoption_rate=0.7, abandonment_risk=0.1, centrality=0.7, phase=EcosystemPhase.MATURE),
            LibraryNode("svelte", "Svelte", "4.2", "javascript", category="ui_framework",
                        latest_version="4.2", release_count=40, release_frequency=0.6,
                        adoption_rate=0.5, abandonment_risk=0.15, centrality=0.5, phase=EcosystemPhase.GROWING),
            LibraryNode("angular", "Angular", "17.3", "javascript", category="ui_framework",
                        latest_version="17.3", release_count=150, release_frequency=0.5,
                        adoption_rate=0.5, abandonment_risk=0.15, centrality=0.6, phase=EcosystemPhase.MATURE),
            LibraryNode("typescript", "TypeScript", "5.5", "javascript", category="language",
                        latest_version="5.5", release_count=60, release_frequency=0.5,
                        adoption_rate=0.9, abandonment_risk=0.02, centrality=0.9, phase=EcosystemPhase.DOMINANT),
            LibraryNode("webpack", "webpack", "5.92", "javascript", category="bundler",
                        latest_version="5.92", release_count=80, release_frequency=0.2,
                        adoption_rate=0.6, abandonment_risk=0.3, centrality=0.6, phase=EcosystemPhase.DECLINING),
            LibraryNode("vite", "Vite", "5.4", "javascript", category="bundler",
                        latest_version="5.4", release_count=50, release_frequency=0.8,
                        adoption_rate=0.8, abandonment_risk=0.05, centrality=0.7, phase=EcosystemPhase.GROWING),
            LibraryNode("tailwindcss", "Tailwind CSS", "3.4", "javascript", category="css_framework",
                        latest_version="3.4", release_count=30, release_frequency=0.5,
                        adoption_rate=0.8, abandonment_risk=0.08, centrality=0.6, phase=EcosystemPhase.GROWING),
            LibraryNode("eslint", "ESLint", "9.0", "javascript", category="linting",
                        latest_version="9.0", release_count=70, release_frequency=0.3,
                        adoption_rate=0.85, abandonment_risk=0.1, centrality=0.6, phase=EcosystemPhase.MATURE),
            LibraryNode("prettier", "Prettier", "3.3", "javascript", category="formatting",
                        latest_version="3.3", release_count=30, release_frequency=0.2,
                        adoption_rate=0.8, abandonment_risk=0.1, centrality=0.4, phase=EcosystemPhase.MATURE),
            LibraryNode("zustand", "Zustand", "4.5", "javascript", category="state_management",
                        latest_version="4.5", release_count=20, release_frequency=0.5,
                        adoption_rate=0.6, abandonment_risk=0.1, centrality=0.4, phase=EcosystemPhase.GROWING),
            LibraryNode("redux", "Redux", "5.0", "javascript", category="state_management",
                        latest_version="5.0", release_count=60, release_frequency=0.2,
                        adoption_rate=0.4, abandonment_risk=0.3, centrality=0.4, phase=EcosystemPhase.DECLINING),
            LibraryNode("tanstack_query", "TanStack Query", "5.51", "javascript", category="data_fetching",
                        latest_version="5.51", release_count=50, release_frequency=0.7,
                        adoption_rate=0.7, abandonment_risk=0.05, centrality=0.5, phase=EcosystemPhase.GROWING),
            LibraryNode("jest", "Jest", "29.7", "javascript", category="testing",
                        latest_version="29.7", release_count=40, release_frequency=0.2,
                        adoption_rate=0.7, abandonment_risk=0.2, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("vitest", "Vitest", "1.6", "javascript", category="testing",
                        latest_version="1.6", release_count=30, release_frequency=0.8,
                        adoption_rate=0.6, abandonment_risk=0.05, centrality=0.4, phase=EcosystemPhase.GROWING),
            LibraryNode("playwright", "Playwright", "1.45", "javascript", category="testing",
                        latest_version="1.45", release_count=60, release_frequency=0.6,
                        adoption_rate=0.65, abandonment_risk=0.08, centrality=0.4, phase=EcosystemPhase.GROWING),
        ]

        for lib in libs:
            engine.add_library(lib)

        edges = [
            ("nextjs", "react", DependencyType.DIRECT, "^18.0", 1.0),
            ("nextjs", "typescript", DependencyType.PEER, "^5.0", 0.9),
            ("nextjs", "vite", DependencyType.OPTIONAL, "^5.0", 0.3),
            ("react", "typescript", DependencyType.PEER, "^5.0", 0.8),
            ("vue", "typescript", DependencyType.OPTIONAL, "^5.0", 0.6),
            ("svelte", "vite", DependencyType.DIRECT, "^5.0", 0.9),
            ("svelte", "typescript", DependencyType.OPTIONAL, "^5.0", 0.5),
            ("angular", "typescript", DependencyType.DIRECT, "^5.0", 1.0),
            ("vite", "typescript", DependencyType.DIRECT, "^5.0", 0.8),
            ("tailwindcss", "vite", DependencyType.OPTIONAL, "^5.0", 0.7),
            ("zustand", "react", DependencyType.PEER, "^18.0", 1.0),
            ("redux", "react", DependencyType.PEER, "^18.0", 0.5),
            ("tanstack_query", "react", DependencyType.PEER, "^18.0", 0.9),
            ("vitest", "vite", DependencyType.PEER, "^5.0", 0.9),
            ("vitest", "typescript", DependencyType.PEER, "^5.0", 0.7),
            ("playwright", "typescript", DependencyType.DIRECT, "^5.0", 0.6),
            ("eslint", "typescript", DependencyType.DIRECT, "^5.0", 0.7),
            ("eslint", "prettier", DependencyType.PEER, "^3.0", 0.6),
        ]

        for src, tgt, dtype, constraint, weight in edges:
            edge = DependencyEdge(
                id=f"e_{uuid.uuid4().hex[:8]}",
                source_id=src, target_id=tgt, dep_type=dtype,
                version_constraint=constraint, weight=weight,
            )
            engine.add_dependency(edge)

        return engine

    @staticmethod
    def build_rust_ecosystem() -> DependencyGraphEngine:
        engine = DependencyGraphEngine()
        libs = [
            LibraryNode("tokio", "Tokio", "1.39", "rust", category="async_runtime",
                        latest_version="1.39", release_count=80, release_frequency=0.7,
                        adoption_rate=0.9, abandonment_risk=0.02, centrality=0.9, phase=EcosystemPhase.DOMINANT),
            LibraryNode("async_std", "async-std", "1.13", "rust", category="async_runtime",
                        latest_version="1.13", release_count=30, release_frequency=0.2,
                        adoption_rate=0.3, abandonment_risk=0.5, centrality=0.4, phase=EcosystemPhase.DECLINING),
            LibraryNode("serde", "Serde", "1.0", "rust", category="serialization",
                        latest_version="1.0", release_count=60, release_frequency=0.4,
                        adoption_rate=0.95, abandonment_risk=0.01, centrality=0.85, phase=EcosystemPhase.DOMINANT),
            LibraryNode("axum", "Axum", "0.7", "rust", category="web_framework",
                        latest_version="0.7", release_count=30, release_frequency=0.6,
                        adoption_rate=0.7, abandonment_risk=0.05, centrality=0.6, phase=EcosystemPhase.GROWING),
            LibraryNode("actix_web", "Actix-web", "4.8", "rust", category="web_framework",
                        latest_version="4.8", release_count=50, release_frequency=0.3,
                        adoption_rate=0.5, abandonment_risk=0.15, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("rocket", "Rocket", "0.5", "rust", category="web_framework",
                        latest_version="0.5", release_count=20, release_frequency=0.15,
                        adoption_rate=0.2, abandonment_risk=0.4, centrality=0.3, phase=EcosystemPhase.DECLINING),
            LibraryNode("tower", "Tower", "0.4", "rust", category="middleware",
                        latest_version="0.4", release_count=15, release_frequency=0.3,
                        adoption_rate=0.7, abandonment_risk=0.1, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("reqwest", "Reqwest", "0.12", "rust", category="http_client",
                        latest_version="0.12", release_count=40, release_frequency=0.4,
                        adoption_rate=0.8, abandonment_risk=0.05, centrality=0.6, phase=EcosystemPhase.MATURE),
            LibraryNode("tracing", "Tracing", "0.1", "rust", category="observability",
                        latest_version="0.1", release_count=30, release_frequency=0.3,
                        adoption_rate=0.75, abandonment_risk=0.05, centrality=0.5, phase=EcosystemPhase.MATURE),
            LibraryNode("clap", "Clap", "4.5", "rust", category="cli",
                        latest_version="4.5", release_count=40, release_frequency=0.4,
                        adoption_rate=0.8, abandonment_risk=0.05, centrality=0.4, phase=EcosystemPhase.MATURE),
            LibraryNode("sqlx", "SQLx", "0.8", "rust", category="database",
                        latest_version="0.8", release_count=35, release_frequency=0.5,
                        adoption_rate=0.6, abandonment_risk=0.1, centrality=0.4, phase=EcosystemPhase.GROWING),
            LibraryNode("diesel", "Diesel", "2.2", "rust", category="orm",
                        latest_version="2.2", release_count=40, release_frequency=0.3,
                        adoption_rate=0.4, abandonment_risk=0.2, centrality=0.3, phase=EcosystemPhase.MATURE),
        ]

        for lib in libs:
            engine.add_library(lib)

        edges = [
            ("axum", "tokio", DependencyType.DIRECT, "^1.0", 1.0),
            ("axum", "tower", DependencyType.DIRECT, "^0.4", 0.9),
            ("axum", "serde", DependencyType.DIRECT, "^1.0", 0.8),
            ("actix_web", "serde", DependencyType.DIRECT, "^1.0", 0.8),
            ("actix_web", "tokio", DependencyType.OPTIONAL, "^1.0", 0.4),
            ("rocket", "serde", DependencyType.DIRECT, "^1.0", 0.7),
            ("reqwest", "tokio", DependencyType.DIRECT, "^1.0", 0.9),
            ("reqwest", "serde", DependencyType.OPTIONAL, "^1.0", 0.6),
            ("sqlx", "tokio", DependencyType.OPTIONAL, "^1.0", 0.8),
            ("sqlx", "serde", DependencyType.OPTIONAL, "^1.0", 0.5),
            ("tracing", "tokio", DependencyType.OPTIONAL, "^1.0", 0.7),
            ("tower", "tokio", DependencyType.OPTIONAL, "^1.0", 0.6),
        ]

        for src, tgt, dtype, constraint, weight in edges:
            edge = DependencyEdge(
                id=f"e_{uuid.uuid4().hex[:8]}",
                source_id=src, target_id=tgt, dep_type=dtype,
                version_constraint=constraint, weight=weight,
            )
            engine.add_dependency(edge)

        return engine
