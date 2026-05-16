"""Week 105 — Repo-Conditioned Model Behavior.

Conditioning packets for different repository types:
- Python package, FastAPI service, React app, CLI tool, test-heavy, undocumented
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json


@dataclass
class ConditioningPacket:
    repo_type: str = ""
    framework_conventions: List[str] = field(default_factory=list)
    repo_style: List[str] = field(default_factory=list)
    test_workflow: List[str] = field(default_factory=list)
    architecture_rules: List[str] = field(default_factory=list)
    common_failure_modes: List[str] = field(default_factory=list)
    retrieval_strategy: str = "hybrid"

    def to_dict(self) -> dict:
        return {
            "repo_type": self.repo_type,
            "framework_conventions": self.framework_conventions[:5],
            "repo_style": self.repo_style[:5],
            "test_workflow": self.test_workflow[:5],
            "architecture_rules": self.architecture_rules[:5],
            "common_failure_modes": self.common_failure_modes[:5],
            "retrieval_strategy": self.retrieval_strategy,
        }


REPO_CONDITIONING_PACKETS = {
    "python_package": ConditioningPacket(
        repo_type="python_package",
        framework_conventions=[
            "Use src/ layout", "setup.py or pyproject.toml",
            "__init__.py exports public API", "Type-annotated Python 3.10+",
        ],
        repo_style=["PEP 8", "Snake case", "Descriptive module names"],
        test_workflow=["pytest", "coverage >= 80%", "tox for multi-version"],
        architecture_rules=[
            "Circular imports forbidden",
            "Business logic in services/, not views/",
            "External calls through adapter interfaces",
        ],
        common_failure_modes=[
            "Missing __init__.py", "Circular imports",
            "Incorrect dependency specification",
        ],
    ),
    "fastapi_service": ConditioningPacket(
        repo_type="fastapi_service",
        framework_conventions=[
            "Pydantic models for request/response",
            "Dependency injection for auth/db",
            "Router prefix per module",
            "OpenAPI documentation",
        ],
        repo_style=["async endpoints", "Repository pattern", "Service layer"],
        test_workflow=["pytest + httpx", "TestClient", "Integration tests per endpoint"],
        architecture_rules=[
            "No business logic in route handlers",
            "DB session via dependency injection",
            "Environment variables for config",
        ],
        common_failure_modes=[
            "Missing async/await", "Incorrect status codes",
            "Unhandled validation errors",
        ],
    ),
    "react_app": ConditioningPacket(
        repo_type="react_app",
        framework_conventions=[
            "Functional components with hooks",
            "Component per file",
            "CSS modules or styled-components",
            "State management via context/Redux",
        ],
        repo_style=["JSX/TSX", "Export default", "index.js barrel exports"],
        test_workflow=["Jest + React Testing Library", "Storybook", "E2E with Playwright"],
        architecture_rules=[
            "No logic in render functions",
            "API calls in custom hooks, not components",
            "Presentational vs container separation",
        ],
        common_failure_modes=[
            "Missing key props in lists",
            "Stale closures in useEffect",
            "Unnecessary re-renders",
        ],
    ),
    "cli_tool": ConditioningPacket(
        repo_type="cli_tool",
        framework_conventions=[
            "Click or argparse for CLI",
            "Exit codes: 0 success, 1 error",
            "--help flag required",
            "stdin/stdout/stderr discipline",
        ],
        repo_style=["Single entry point", "Plugin architecture", "Config files in ~/.config"],
        test_workflow=["pytest + CliRunner", "Integration tests", "Snapshot testing"],
        architecture_rules=[
            "No GUI dependencies",
            "Graceful error messages to stderr",
            "Machine-readable output flag",
        ],
        common_failure_modes=[
            "Silent failures",
            "Hard-coded paths",
            "Missing error exit codes",
        ],
    ),
    "test_heavy": ConditioningPacket(
        repo_type="test_heavy",
        framework_conventions=[
            "Arrange-Act-Assert pattern",
            "Fixtures for setup/teardown",
            "Parametrized tests for edge cases",
            "Mock external services",
        ],
        repo_style=["Test per module", "Conftest.py for shared fixtures"],
        test_workflow=["pytest", "Coverage >= 90%", "Property-based testing with Hypothesis"],
        architecture_rules=[
            "Tests mirror source structure",
            "No test dependencies in production code",
            "Slow tests marked @pytest.mark.slow",
        ],
        common_failure_modes=[
            "Flaky tests", "Mock not matching real API",
            "Test pollution via shared state",
        ],
    ),
    "undocumented": ConditioningPacket(
        repo_type="undocumented",
        framework_conventions=[
            "Infer from imports and usage",
            "Look at test files for expected behavior",
            "Check .gitignore for build artifacts",
            "Read setup.py/pyproject.toml for metadata",
        ],
        repo_style=["Unknown — infer from patterns"],
        test_workflow=["Check if tests exist", "Run tests to discover behavior"],
        architecture_rules=[
            "Do not assume architectural intent",
            "Prefer minimal changes when uncertain",
            "Add documentation as you go",
        ],
        common_failure_modes=[
            "Wrong architectural assumptions",
            "Missing dependency discovery",
            "Breaking implicit contracts",
        ],
    ),
}


class RepoConditioner:
    """Condition model behavior based on repository type."""

    @staticmethod
    def detect_repo_type(files: List[str], config: Optional[dict] = None) -> str:
        config = config or {}
        file_set = set(files)
        if any("pyproject.toml" in f for f in file_set):
            if any("fastapi" in (config.get("dependencies") or []) for _ in [1]):
                pass
            return "python_package"
        for f in file_set:
            if "fastapi" in f.lower() or "main.py" in f:
                return "fastapi_service"
            if f.endswith((".jsx", ".tsx", ".js")):
                return "react_app"
        if "cli" in str(files).lower():
            return "cli_tool"
        if "test" in str(files).lower():
            return "test_heavy"
        return "undocumented"

    @staticmethod
    def get_packet(repo_type: str) -> ConditioningPacket:
        return REPO_CONDITIONING_PACKETS.get(repo_type, REPO_CONDITIONING_PACKETS["undocumented"])

    @staticmethod
    def build_conditioning_prompt(repo_type: str, task: str) -> str:
        packet = RepoConditioner.get_packet(repo_type)
        lines = [
            f"Repository type: {repo_type}",
            "",
            "Conventions:",
        ]
        for c in packet.framework_conventions:
            lines.append(f"  - {c}")
        lines.append("")
        lines.append("Architecture rules:")
        for r in packet.architecture_rules:
            lines.append(f"  - {r}")
        lines.append("")
        lines.append("Common failure modes to avoid:")
        for f in packet.common_failure_modes:
            lines.append(f"  - {f}")
        lines.append("")
        lines.append(f"Task: {task}")
        return "\n".join(lines)

    @staticmethod
    def benchmark() -> Dict:
        tasks = [
            ("python_package", "Add a new module with public API"),
            ("fastapi_service", "Add rate limiting to endpoints"),
            ("react_app", "Add loading state to component"),
            ("cli_tool", "Add --verbose flag"),
            ("test_heavy", "Add property-based tests"),
            ("undocumented", "Fix the bug in unknown codebase"),
        ]
        results = []
        for repo_type, task in tasks:
            prompt = RepoConditioner.build_conditioning_prompt(repo_type, task)
            results.append({
                "repo_type": repo_type,
                "task": task,
                "prompt_length": len(prompt),
                "packet_fields": len(REPO_CONDITIONING_PACKETS[repo_type].framework_conventions),
            })
        return {
            "total_types": len(REPO_CONDITIONING_PACKETS),
            "tasks": results,
        }
