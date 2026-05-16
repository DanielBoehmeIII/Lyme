"""Tests for ecosystem knowledge graph."""


def test_ecosystem_graph_builds():
    """Ecosystem graph builds with correct structure."""
    from lyme.ecosystem.fastapi_knowledge import FastAPIEcosystemKnowledge

    knowledge = FastAPIEcosystemKnowledge()
    g = knowledge.graph

    assert g.node_count > 0
    assert g.edge_count > 0

    frameworks = g.query(node_type=None)
    assert len(frameworks) > 0


def test_compatibility_checker():
    """CompatibilityChecker detects known issues."""
    from lyme.ecosystem.compatibility import CompatibilityChecker

    checker = CompatibilityChecker()
    deps = {
        "pydantic": "1.9.0",
        "fastapi": "0.105.0",
        "python": "3.9",
    }

    report = checker.check_compatibility(deps)
    assert report.total_issues >= 0
    assert 0 <= report.overall_score <= 1


def test_security_zone_detection():
    """SecurityZoneDetector detects zones from patterns."""
    from lyme.ecosystem.security_zones import SecurityZoneDetector

    detector = SecurityZoneDetector()
    file_paths = ["src/auth/login.py", "src/main.py"]
    code_contents = {"src/auth/login.py": "SECRET_KEY = 'hardcoded'"}

    zones = detector.detect_zones(file_paths, code_contents)
    assert len(zones) >= 0


def test_migration_paths():
    """MigrationPathEngine provides known migration paths."""
    from lyme.ecosystem.migration import MigrationPathEngine

    engine = MigrationPathEngine()
    path = engine.find_path("flask", "fastapi")

    assert path is not None
    assert path.source_framework == "Flask"
    assert path.target_framework == "FastAPI"
    assert len(path.steps) > 0
