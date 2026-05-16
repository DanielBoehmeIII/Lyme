from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from lyme.ecosystem.graph import (
    EcosystemGraph, EcosystemNode, EcosystemEdge,
    NodeType, EdgeType,
)
import json
import uuid


@dataclass
class FastAPIKnowledgeBase:
    framework_version: str = "0.115+"
    python_version: str = "3.10+"
    async_native: bool = True
    starlette_based: bool = True
    pydantic_based: bool = True
    openapi_support: bool = True

    def to_dict(self) -> Dict:
        return {
            "framework_version": self.framework_version,
            "python_version": self.python_version,
            "async_native": self.async_native,
            "starlette_based": self.starlette_based,
            "pydantic_based": self.pydantic_based,
            "openapi_support": self.openapi_support,
        }


class FastAPIEcosystemKnowledge:
    def __init__(self):
        self.graph = EcosystemGraph()
        self._build_graph()

    def _build_graph(self):
        self._add_frameworks()
        self._add_libraries()
        self._add_databases()
        self._add_tools()
        self._add_integrations()
        self._add_migration_paths()
        self._add_security_zones()
        self._add_frequent_bugs()
        self._add_arch_norms()
        self._add_compatibility()

    def _add_frameworks(self):
        self.graph.add_node(EcosystemNode(
            id="fastapi", name="FastAPI", node_type=NodeType.FRAMEWORK,
            description="Modern, fast web framework for building APIs with Python 3.10+",
            version="0.115+", ecosystem="python", tags=["async", "openapi", "pydantic"],
            metadata={"stars": "90k+", "license": "MIT", "python_version": "3.10+"},
        ))
        self.graph.add_node(EcosystemNode(
            id="starlette", name="Starlette", node_type=NodeType.FRAMEWORK,
            description="ASGI framework/toolkit, foundation of FastAPI",
            version="0.40+", ecosystem="python", tags=["asgi", "async"],
            metadata={"stars": "10k+", "license": "BSD-3-Clause"},
        ))
        self.graph.add_node(EcosystemNode(
            id="flask", name="Flask", node_type=NodeType.FRAMEWORK,
            description="Lightweight WSGI web application framework",
            version="3.0+", ecosystem="python", tags=["wsgi", "synchronous"],
            metadata={"stars": "68k+", "license": "BSD-3-Clause"},
        ))
        self.graph.add_node(EcosystemNode(
            id="django", name="Django", node_type=NodeType.FRAMEWORK,
            description="High-level Python web framework with batteries included",
            version="5.0+", ecosystem="python", tags=["orm", "admin", "batteries-included"],
            metadata={"stars": "80k+", "license": "BSD-3-Clause"},
        ))

    def _add_libraries(self):
        libs = [
            ("sqlalchemy", "SQLAlchemy", "Database ORM and toolkit for Python", "2.0+", ["orm", "database", "async"], {"stars": "40k+"}),
            ("alembic", "Alembic", "Database migration tool for SQLAlchemy", "1.13+", ["migration", "database"], {"stars": "5k+"}),
            ("pydantic", "Pydantic", "Data validation using Python type hints", "2.0+", ["validation", "types"], {"stars": "22k+"}),
            ("pydantic_v1", "Pydantic v1", "Pydantic version 1.x, legacy but widely deployed", "1.10", ["validation", "legacy"], {"stars": "22k+"}),
            ("httpx", "HTTPX", "Async HTTP client for Python", "0.27+", ["http", "async", "client"], {"stars": "14k+"}),
            ("httptools", "httptools", "HTTP request/response parser, used by uvicorn", "0.6+", ["http", "parser"], {"stars": "2k+"}),
            ("websockets", "websockets", "Library for building WebSocket servers and clients", "12.0+", ["websocket", "async"], {"stars": "6k+"}),
            ("uvicorn", "Uvicorn", "ASGI server implementation, recommended for FastAPI", "0.30+", ["server", "asgi", "async"], {"stars": "10k+"}),
            ("gunicorn", "Gunicorn", "WSGI HTTP server, used with uvicorn workers", "22.0+", ["server", "wsgi"], {"stars": "10k+"}),
            ("celery", "Celery", "Distributed task queue for async task processing", "5.3+", ["task_queue", "async", "distributed"], {"stars": "25k+"}),
            ("redis_py", "redis-py", "Redis client for Python", "5.0+", ["cache", "queue", "session"], {"stars": "13k+"}),
            ("httpx_oauth", "httpx-oauth", "OAuth client library using HTTPX", "0.4+", ["oauth", "auth"], {"stars": "500+"}),
            ("python_jose", "python-jose", "JOSE implementation (JWT, JWS, JWE)", "3.3+", ["jwt", "auth"], {"stars": "2k+"}),
            ("passlib", "Passlib", "Password hashing library", "1.7+", ["password", "auth"], {"stars": "2k+"}),
            ("bcrypt", "bcrypt", "Modern password hashing", "4.1+", ["password", "auth"], {"stars": "1k+"}),
            ("aiosqlite", "aiosqlite", "Async SQLite wrapper", "0.20+", ["database", "async", "sqlite"], {"stars": "1k+"}),
            ("asyncpg", "asyncpg", "Async PostgreSQL driver", "0.29+", ["database", "async", "postgresql"], {"stars": "10k+"}),
            ("databases", "Databases", "Async database query builder", "0.9+", ["database", "async"], {"stars": "4k+"}),
            ("orjson", "orjson", "Fast JSON serialization library", "3.9+", ["json", "performance"], {"stars": "6k+"}),
            ("ujson", "ujson", "Ultra-fast JSON encoder/decoder", "5.10+", ["json", "performance"], {"stars": "2k+"}),
            ("dependy", "dependy", "Dependency injection for Python (alternative to FastAPI DI)", "0.1+", ["di", "injection"], {"stars": "100+"}),
            ("dependency_injector", "dependency-injector", "Dependency injection framework for Python", "4.41+", ["di", "injection"], {"stars": "4k+"}),
            ("structlog", "structlog", "Structured logging library", "24.0+", ["logging", "structured"], {"stars": "4k+"}),
            ("sentry_sdk", "Sentry SDK", "Error tracking and performance monitoring", "2.0+", ["monitoring", "error_tracking"], {"stars": "4k+"}),
            ("prometheus_client", "prometheus-client", "Prometheus monitoring client", "0.20+", ["monitoring", "metrics"], {"stars": "4k+"}),
            ("opentelemetry_python", "OpenTelemetry Python", "Observability framework for distributed tracing", "1.25+", ["observability", "tracing"], {"stars": "2k+"}),
            ("pytest", "pytest", "Testing framework for Python", "8.0+", ["testing"], {"stars": "12k+"}),
            ("httpx_testclient", "HTTPX TestClient", "Async test client for FastAPI/Starlette", "0.27+", ["testing", "async"], {"stars": "0"}),
            ("mypy", "mypy", "Static type checker for Python", "1.10+", ["typing", "static_analysis"], {"stars": "18k+"}),
            ("ruff", "Ruff", "Fast Python linter and formatter", "0.5+", ["linting", "formatting"], {"stars": "30k+"}),
        ]
        for lid, name, desc, version, tags, meta in libs:
            self.graph.add_node(EcosystemNode(
                id=lid, name=name, node_type=NodeType.LIBRARY,
                description=desc, version=version, ecosystem="python",
                tags=tags, metadata=meta,
            ))

    def _add_databases(self):
        dbs = [
            ("postgresql", "PostgreSQL", "Advanced open-source relational database", "16+", ["relational", "acid"]),
            ("sqlite", "SQLite", "Embedded relational database", "3.45+", ["embedded", "relational"]),
            ("mysql", "MySQL", "Popular open-source relational database", "8.0+", ["relational", "acid"]),
            ("redis", "Redis", "In-memory data structure store", "7.2+", ["cache", "key-value"]),
            ("mongodb", "MongoDB", "NoSQL document database", "7.0+", ["nosql", "document"]),
            ("elasticsearch", "Elasticsearch", "Distributed search and analytics engine", "8.0+", ["search", "analytics"]),
            ("kafka", "Apache Kafka", "Distributed event streaming platform", "3.7+", ["streaming", "event-bus"]),
            ("rabbitmq", "RabbitMQ", "Message broker for distributed systems", "3.13+", ["message-broker", "queue"]),
        ]
        for did, name, desc, version, tags in dbs:
            self.graph.add_node(EcosystemNode(
                id=did, name=name, node_type=NodeType.DATABASE,
                description=desc, version=version, ecosystem="infrastructure", tags=tags,
            ))

    def _add_tools(self):
        tools = [
            ("docker", "Docker", "Container platform", "25+", ["container", "deployment", "infrastructure"]),
            ("poetry", "Poetry", "Python dependency management and packaging", "1.8+", ["packaging", "dependency-management"]),
            ("pip", "pip", "Python package installer", "24+", ["packaging", "installer"]),
            ("hatch", "Hatch", "Modern Python project manager", "1.12+", ["packaging", "project-management"]),
            ("uv", "uv", "Fast Python package manager (Rust)", "0.2+", ["packaging", "fast"]),
            ("pre_commit", "pre-commit", "Framework for managing pre-commit hooks", "3.7+", ["linting", "hooks"]),
            ("make", "Make", "Build automation tool", "4.4+", ["build", "automation"]),
            ("github_actions", "GitHub Actions", "CI/CD platform", "-", ["ci", "cd"]),
            ("pypi", "PyPI", "Python Package Index", "-", ["registry", "distribution"]),
        ]
        for tid, name, desc, version, tags in tools:
            self.graph.add_node(EcosystemNode(
                id=tid, name=name, node_type=NodeType.TOOL,
                description=desc, version=version, ecosystem="devops", tags=tags,
            ))

    def _add_integrations(self):
        integrations = [
            ("fastapi", "starlette", EdgeType.EXTENDS, "FastAPI is built on Starlette", 1.0),
            ("fastapi", "pydantic", EdgeType.DEPENDS_ON, "Pydantic for request/response validation", 1.0),
            ("fastapi", "uvicorn", EdgeType.INTEGRATES_WITH, "Uvicorn is the recommended ASGI server", 1.0),
            ("uvicorn", "httptools", EdgeType.DEPENDS_ON, "Uvicorn uses httptools for HTTP parsing", 0.8),
            ("fastapi", "sqlalchemy", EdgeType.INTEGRATES_WITH, "Common integration via dependency injection", 0.9),
            ("fastapi", "alembic", EdgeType.SUGGESTS, "Alembic for database migrations with SQLAlchemy", 0.8),
            ("celery", "redis", EdgeType.INTEGRATES_WITH, "Redis as Celery message broker", 0.9),
            ("celery", "rabbitmq", EdgeType.INTEGRATES_WITH, "RabbitMQ as Celery message broker", 0.8),
            ("fastapi", "celery", EdgeType.INTEGRATES_WITH, "Background task processing via Celery", 0.7),
            ("fastapi", "pytest", EdgeType.INTEGRATES_WITH, "Testing FastAPI applications", 0.9),
            ("fastapi", "httpx", EdgeType.INTEGRATES_WITH, "Async test client via httpx", 0.9),
            ("httpx", "httpx_testclient", EdgeType.USES, "TestClient wraps httpx for async testing", 1.0),
            ("fastapi", "sentry_sdk", EdgeType.INTEGRATES_WITH, "Error monitoring integration", 0.7),
            ("fastapi", "prometheus_client", EdgeType.INTEGRATES_WITH, "Metrics export via middleware", 0.7),
            ("fastapi", "opentelemetry_python", EdgeType.INTEGRATES_WITH, "Distributed tracing via OpenTelemetry", 0.6),
            ("fastapi", "redis_py", EdgeType.INTEGRATES_WITH, "Session caching and rate limiting", 0.8),
            ("fastapi", "python_jose", EdgeType.INTEGRATES_WITH, "JWT token handling", 0.8),
            ("fastapi", "passlib", EdgeType.SUGGESTS, "Password hashing for user auth", 0.7),
            ("fastapi", "structlog", EdgeType.INTEGRATES_WITH, "Structured logging integration", 0.6),
            ("fastapi", "docker", EdgeType.SUGGESTS, "Containerized deployment", 0.9),
            ("sqlalchemy", "alembic", EdgeType.INTEGRATES_WITH, "Alembic is the migration tool for SQLAlchemy", 1.0),
            ("sqlalchemy", "asyncpg", EdgeType.INTEGRATES_WITH, "Async PostgreSQL via asyncpg driver", 0.8),
            ("sqlalchemy", "aiosqlite", EdgeType.INTEGRATES_WITH, "Async SQLite for development/testing", 0.7),
            ("flask", "pydantic", EdgeType.INTEGRATES_WITH, "Via flask-pydantic or manual integration", 0.4),
            ("flask", "sqlalchemy", EdgeType.INTEGRATES_WITH, "Flask-SQLAlchemy extension", 0.8),
            ("django", "celery", EdgeType.INTEGRATES_WITH, "Background tasks in Django", 0.7),
            ("python_jose", "pydantic", EdgeType.INTEGRATES_WITH, "Token models with Pydantic validation", 0.7),
            ("pytest", "httpx", EdgeType.INTEGRATES_WITH, "HTTPX integration for async HTTP testing", 0.8),
            ("ruff", "mypy", EdgeType.FREQUENTLY_PAIRED_WITH, "Common linting + type checking combo", 0.8),
            ("pre_commit", "ruff", EdgeType.INTEGRATES_WITH, "Ruff via pre-commit hook", 0.8),
            ("pre_commit", "mypy", EdgeType.INTEGRATES_WITH, "mypy via pre-commit hook", 0.7),
            ("docker", "github_actions", EdgeType.INTEGRATES_WITH, "Docker-based CI pipelines", 0.8),
        ]
        for src, tgt, etype, desc, weight in integrations:
            eid = f"e_{uuid.uuid4().hex[:8]}"
            self.graph.add_edge(EcosystemEdge(
                id=eid, source_id=src, target_id=tgt,
                edge_type=etype, weight=weight, description=desc,
            ))

    def _add_migration_paths(self):
        migrations = [
            ("flask", "fastapi", "Migrate from Flask to FastAPI for async support and OpenAPI docs",
             "medium", ["Rewrite route decorators", "Add Pydantic models", "Update dependency injection"]),
            ("django", "fastapi", "Migrate from Django REST to FastAPI for performance",
             "hard", ["Replace DRF serializers", "Adopt async patterns", "Set up ORM separately"]),
            ("pydantic_v1", "pydantic", "Upgrade from Pydantic v1 to v2",
             "medium", ["Update validators", "Replace custom_getter patterns", "Address config changes"]),
            ("sqlalchemy_1x", "sqlalchemy", "Upgrade SQLAlchemy 1.x to 2.0 style",
             "medium", ["Replace .query() with select()", "Use mapped_column", "Adopt native async"]),
        ]
        for mid, name, desc, risk, steps in migrations:
            node_id = f"migrate_{mid}"
            self.graph.add_node(EcosystemNode(
                id=node_id, name=f"Migration: {name}", node_type=NodeType.MIGRATION_PATH,
                description=desc, ecosystem="python",
                tags=["migration", risk], metadata={"steps": steps, "risk": risk},
            ))
            source_node = self.graph.get_node(mid)
            target_node = self.graph.get_node(name)
            if source_node and target_node:
                eid = f"em_{uuid.uuid4().hex[:8]}"
                self.graph.add_edge(EcosystemEdge(
                    id=eid, source_id=mid, target_id=name,
                    edge_type=EdgeType.MIGRATES_TO, weight=0.7,
                    description=desc,
                ))

    def _add_security_zones(self):
        zones = [
            ("auth_endpoints", "Authentication Endpoints", "Login, register, token refresh endpoints",
             "critical", ["rate_limiting", "brute_force_protection", "session_management"]),
            ("password_storage", "Password Storage", "Password hashing and storage",
             "critical", ["Argon2", "bcrypt", "salt"]),
            ("jwt_handling", "JWT Token Handling", "Token creation, verification, and rotation",
             "high", ["secret_rotation", "expiration", "revocation"]),
            ("sql_injection", "SQL Injection Prevention", "Parameterized queries and ORM safety",
             "critical", ["raw_sql", "query_builder", "escape"]),
            ("cors_config", "CORS Configuration", "Cross-origin resource sharing settings",
             "medium", ["origin_whitelist", "credentials", "methods"]),
            ("file_upload", "File Upload Handling", "User file upload validation and storage",
             "high", ["size_limit", "type_validation", "path_traversal"]),
            ("rate_limiting", "Rate Limiting", "Request rate limiting for API endpoints",
             "medium", ["ddos_protection", "abuse_prevention"]),
            ("api_keys", "API Key Management", "API key generation, storage, and validation",
             "high", ["key_rotation", "scope_enforcement", "leak_detection"]),
            ("data_validation", "Data Validation", "Input validation against injection and overflow",
             "critical", ["pydantic_validation", "sanitization", "type_enforcement"]),
            ("session_management", "Session Management", "User session handling and security",
             "high", ["csrf", "session_hijacking", "secure_cookies"]),
        ]
        for zid, name, desc, severity, tags in zones:
            self.graph.add_node(EcosystemNode(
                id=f"sec_{zid}", name=name, node_type=NodeType.SECURITY_ZONE,
                description=desc, ecosystem="python",
                tags=tags + [severity], metadata={"severity": severity},
            ))

    def _add_frequent_bugs(self):
        bugs = [
            ("sync_endpoint_blocking", "Sync Endpoint Blocking Event Loop",
             "Using sync I/O in async endpoints blocks the event loop. Use async DB drivers.",
             "critical", ["async", "blocking", "event_loop"]),
            ("pydantic_v1_v2_breakage", "Pydantic v1/v2 Incompatibility",
             "Code written for Pydantic v1 breaks on v2. Validators, config, and type changes.",
             "high", ["pydantic", "version", "validation"]),
            ("missing_asgi_lifespan", "Missing ASGI Lifespan Handler",
             "Not implementing startup/shutdown handlers leads to resource leaks.",
             "high", ["asgi", "lifespan", "startup"]),
            ("env_var_exposure", "Environment Variable Exposure",
             "Accidentally exposing secrets in error responses or logs.",
             "critical", ["secrets", "environment", "exposure"]),
            ("cors_misconfiguration", "CORS Misconfiguration",
             "Wide-open CORS allowing any origin. Common in development that goes to production.",
             "medium", ["cors", "security", "configuration"]),
            ("sqlalchemy_async_mismatch", "SQLAlchemy Async/Sync Mismatch",
             "Using sync SQLAlchemy session in async endpoint. Causes thread-safety issues.",
             "high", ["sqlalchemy", "async", "session"]),
            ("jwt_secret_hardcoded", "JWT Secret Hardcoded in Code",
             "Secret key embedded in source code instead of environment variable.",
             "critical", ["jwt", "secret", "hardcoded"]),
            ("missing_validation", "Missing Input Validation on Pydantic Models",
             "Not using Pydantic for all request bodies leads to injection vulnerabilities.",
             "high", ["validation", "pydantic", "injection"]),
            ("deprecated_io_loop", "Using Deprecated IOLoop in Uvicorn/Gunicorn",
             "Using --reload with gunicorn workers causes instability.",
             "medium", ["uvicorn", "gunicorn", "reload"]),
            ("session_per_request_mismatch", "Database Session Per Request Mismatch",
             "Not using dependency injection for DB sessions, creating connection leaks.",
             "high", ["database", "session", "dependency"]),
        ]
        for bid, name, desc, severity, tags in bugs:
            self.graph.add_node(EcosystemNode(
                id=f"bug_{bid}", name=name, node_type=NodeType.FREQUENT_BUG,
                description=desc, ecosystem="python",
                tags=tags + [severity], metadata={"severity": severity},
            ))
            for tag in tags:
                lib_id = self._find_lib_id(tag)
                if lib_id:
                    eid = f"eb_{uuid.uuid4().hex[:8]}"
                    self.graph.add_edge(EcosystemEdge(
                        id=eid, source_id=f"bug_{bid}", target_id=lib_id,
                        edge_type=EdgeType.KNOWN_BUG, weight=0.8,
                        description=f"Known bug related to {lib_id}",
                    ))

    def _add_arch_norms(self):
        norms = [
            ("layered_architecture", "Layered Architecture",
             "Router -> Service -> Repository pattern for FastAPI apps", ["architecture", "layered"]),
            ("dependency_injection", "Dependency Injection via FastAPI Depends",
             "Use FastAPI's Depends() for DI instead of global state", ["di", "testing"]),
            ("async_routes", "Async Routes for I/O Operations",
             "Use async def for all I/O-bound route handlers", ["async", "performance"]),
            ("pydantic_models_separate", "Separate Pydantic Models Layer",
             "Define request/response models separately from domain models", ["pydantic", "architecture"]),
            ("middleware_stack", "Middleware Stack Pattern",
             "CORS -> Auth -> Logging -> Rate Limit -> Route middleware ordering", ["middleware", "security"]),
            ("exception_handlers", "Centralized Exception Handlers",
             "Register custom exception handlers for consistent error responses", ["errors", "consistency"]),
            ("lifespan_management", "Lifespan Resource Management",
             "Use lifespan context manager for startup/shutdown resource lifecycle", ["resources", "lifecycle"]),
            ("background_tasks", "Background Task Pattern",
             "Use BackgroundTasks or Celery for non-critical async operations", ["async", "tasks"]),
        ]
        for nid, name, desc, tags in norms:
            self.graph.add_node(EcosystemNode(
                id=f"norm_{nid}", name=name, node_type=NodeType.ARCH_NORM,
                description=desc, ecosystem="python", tags=tags,
            ))

    def _add_compatibility(self):
        compat = [
            ("pydantic", "fastapi", EdgeType.COMPATIBLE_WITH, "Pydantic v2 fully supported in FastAPI 0.100+", 1.0),
            ("pydantic_v1", "fastapi", EdgeType.COMPATIBLE_WITH, "Pydantic v1 supported but deprecated", 0.6),
            ("sqlalchemy", "fastapi", EdgeType.COMPATIBLE_WITH, "SQLAlchemy 2.0 fully compatible", 1.0),
            ("databases", "fastapi", EdgeType.INCOMPATIBLE_WITH, "Databases library not recommended with FastAPI; use SQLAlchemy 2.0 async", 0.3),
            ("pydantic_v1", "pydantic", EdgeType.INCOMPATIBLE_WITH, "Pydantic v1 and v2 are incompatible in the same project", 0.9),
            ("dependy", "fastapi", EdgeType.COMPATIBLE_WITH, "Alternative DI, but conflicts with Depends pattern", 0.3),
            ("asyncpg", "sqlalchemy", EdgeType.COMPATIBLE_WITH, "asyncpg as async driver for SQLAlchemy 2.0", 1.0),
            ("uvicorn", "gunicorn", EdgeType.COMPATIBLE_WITH, "Uvicorn workers with Gunicorn for production", 0.9),
        ]
        for src, tgt, etype, desc, weight in compat:
            eid = f"ec_{uuid.uuid4().hex[:8]}"
            self.graph.add_edge(EcosystemEdge(
                id=eid, source_id=src, target_id=tgt,
                edge_type=etype, weight=weight, description=desc,
            ))

    def _find_lib_id(self, tag: str) -> Optional[str]:
        mapping = {
            "async": "fastapi",
            "pydantic": "pydantic",
            "validation": "pydantic",
            "jwt": "python_jose",
            "secret": "python_jose",
            "session": "redis_py",
            "database": "sqlalchemy",
            "sqlalchemy": "sqlalchemy",
            "uvicorn": "uvicorn",
            "gunicorn": "gunicorn",
            "cors": "fastapi",
            "configuration": "fastapi",
            "environment": "fastapi",
            "asgi": "starlette",
        }
        lid = mapping.get(tag)
        if lid and self.graph.get_node(lid):
            return lid
        return None

    def get_library_recommendations(self, category: str) -> List[Dict]:
        results = []
        for node in self.graph.nodes:
            if category in node.tags:
                results.append({
                    "id": node.id,
                    "name": node.name,
                    "description": node.description,
                    "version": node.version,
                    "confidence": node.confidence,
                })
        return sorted(results, key=lambda x: -x["confidence"])

    def get_security_advisories(self) -> List[Dict]:
        zones = self.graph.get_security_zones()
        return [
            {"name": z.name, "description": z.description, "severity": z.metadata.get("severity", "medium"), "tags": z.tags}
            for z in zones
        ]

    def get_known_bugs(self) -> List[Dict]:
        bugs = self.graph.get_frequent_bugs()
        return [
            {"name": b.name, "description": b.description, "severity": b.metadata.get("severity", "medium"), "tags": b.tags}
            for b in bugs
        ]

    def get_arch_norms(self) -> List[Dict]:
        norms = self.graph.get_arch_norms()
        return [
            {"name": n.name, "description": n.description, "tags": n.tags}
            for n in norms
        ]
