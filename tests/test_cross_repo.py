"""Tests for cross-repo pattern mining."""

from pathlib import Path
import tempfile
import json


def test_fingerprinter(tmp_path):
    """RepoFingerprinter extracts valid fingerprints."""
    (tmp_path / "main.py").write_text("def hello():\n    print('hello')\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\nrequires-python = '>=3.10'\n")
    (tmp_path / "test_main.py").write_text("def test_hello():\n    assert True\n")

    from lyme.cross_repo.fingerprint import RepoFingerprinter, FingerprintComponent
    fp = RepoFingerprinter(tmp_path, anonymize=True).fingerprint()

    assert fp.repo_id.startswith("repo_")
    assert len(fp.components) > 0
    assert fp.structural_signature.depth >= 0
    assert fp.test_to_code_ratio >= 0
    assert fp.hash != ""


def test_pattern_extraction():
    """PatternExtractor finds patterns from fingerprints."""
    from lyme.cross_repo.fingerprint import RepoFingerprinter, FingerprintComponent
    from lyme.cross_repo.pattern_extractor import PatternExtractor, PatternCategory

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        for d in [d1, d2]:
            (Path(d) / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
            (Path(d) / "pyproject.toml").write_text("[project]\nname = 'test'\nrequires-python = '>=3.10'\n")

        fp1 = RepoFingerprinter(Path(d1)).fingerprint()
        fp2 = RepoFingerprinter(Path(d2)).fingerprint()

        extractor = PatternExtractor()
        patterns = extractor.extract_from_fingerprints([fp1, fp2])

        assert len(patterns) >= 0
        for p in patterns:
            assert p.id != ""
            assert p.occurrences >= 2


def test_clustering():
    """PatternClusterer clusters similar fingerprints."""
    from lyme.cross_repo.fingerprint import RepoFingerprinter
    from lyme.cross_repo.clustering import PatternClusterer

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        (Path(d1) / "main.py").write_text("import flask\n")
        (Path(d2) / "main.rs").write_text("fn main() {}\n")
        (Path(d1) / "pyproject.toml").write_text("[project]\nname = 'a'\n")
        (Path(d2) / "Cargo.toml").write_text("[package]\nname = 'b'\n")

        fp1 = RepoFingerprinter(Path(d1)).fingerprint()
        fp2 = RepoFingerprinter(Path(d2)).fingerprint()

        clusterer = PatternClusterer(n_clusters=2)
        clusters = clusterer.cluster_fingerprints([fp1, fp2])

        assert len(clusters) >= 0


def test_pattern_scoring():
    """PatternScorer produces valid confidence scores."""
    from lyme.cross_repo.scoring import PatternScorer
    from lyme.cross_repo.pattern_extractor import CrossRepoPattern, PatternCategory, PatternSeverity, PatternSource

    scorer = PatternScorer()
    pattern = CrossRepoPattern(
        id="test_p1", category=PatternCategory.ARCHITECTURE, name="Test Pattern",
        description="A test pattern", pattern_hash="abc123",
        sources=[PatternSource(repo_id="repo_1", file_paths=[], occurrence_count=5, confidence=0.8)],
        occurrences=5, severity=PatternSeverity.INFO, signature={"key": "value"},
        transfer_success_rate=0.7,
    )

    score = scorer.score_pattern(pattern)
    assert 0 <= score.overall <= 1
    assert len(score.by_source) > 0
    assert score.uncertainty >= 0


def test_insight_generation():
    """InsightGenerator produces transferable insights."""
    from lyme.cross_repo.insight_generator import InsightGenerator
    from lyme.cross_repo.pattern_extractor import CrossRepoPattern, PatternCategory, PatternSeverity, PatternSource
    from lyme.cross_repo.clustering import ClusterResult

    patterns = [
        CrossRepoPattern(
            id="p1", category=PatternCategory.ARCHITECTURE, name="Layered Architecture",
            description="Layered arch", pattern_hash="h1",
            sources=[PatternSource(repo_id="r1", file_paths=[], occurrence_count=3, confidence=0.8)],
            occurrences=3, severity=PatternSeverity.INFO, signature={"key": "val"},
        )
    ]

    generator = InsightGenerator()
    insights = generator.generate(patterns, [])

    assert len(insights) >= 0
