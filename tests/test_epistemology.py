"""Tests for epistemology module."""


def test_evidence_theory():
    """EvidenceTheoryEngine assesses claims with evidence."""
    from lyme.epistemology.evidence_theory import (
        EvidenceTheoryEngine, Evidence, EvidenceType, EvidenceSource
    )

    engine = EvidenceTheoryEngine()
    claim = engine.make_claim("Test claim", domain="testing")
    engine.add_evidence(claim.id, Evidence(
        id="ev1", evidence_type=EvidenceType.CODE,
        source=EvidenceSource.STATIC_ANALYSIS,
        content="Evidence content", source_location="test.py",
        reliability=0.9, confidence=0.95,
    ))

    assessment = engine.assess_claim(claim.id)
    assert assessment.overall_confidence > 0
    assert assessment.evidence_count == 1
    assert assessment.claim.strength.value in ("certain", "strong", "moderate", "weak", "speculative")


def test_evidence_aggregation():
    """EvidenceAggregator produces reasonable confidence scores."""
    from lyme.epistemology.evidence_theory import EvidenceAggregator, Evidence, EvidenceType, EvidenceSource

    aggregator = EvidenceAggregator()
    ev1 = Evidence(
        id="ev1", evidence_type=EvidenceType.CODE,
        source=EvidenceSource.STATIC_ANALYSIS,
        content="code evidence", source_location="f.py",
        reliability=0.9, confidence=0.95,
    )
    ev2 = Evidence(
        id="ev2", evidence_type=EvidenceType.TEST,
        source=EvidenceSource.TEST_RUNNER,
        content="test evidence", source_location="test_f.py",
        reliability=0.8, confidence=0.85,
    )

    result = aggregator.aggregate([ev1, ev2])
    assert result["evidence_count"] == 2
    assert result["weighted_confidence"] > 0


def test_confidence_calibration():
    """ConfidenceCalibrator produces calibration curves."""
    from lyme.epistemology.confidence_calibration import ConfidenceCalibrator

    calibrator = ConfidenceCalibrator(n_bins=5)
    for pred, actual in [(0.9, True), (0.8, True), (0.7, False), (0.95, True),
                          (0.6, True), (0.5, False), (0.3, False), (0.85, True)]:
        calibrator.record(pred, actual, domain="test")

    report = calibrator.generate_report()
    assert report.curve.total_points == 8
    assert report.curve.ece >= 0
    assert len(report.recommendations) > 0


def test_epistemic_debugging():
    """EpistemicDebugger records and reports failures."""
    from lyme.epistemology.epistemic_debugging import (
        EpistemicDebugger, FailureCategory, FailedInference
    )

    debugger = EpistemicDebugger()
    debugger.record_failure(
        category=FailureCategory.OVERCONFIDENCE,
        false_claim="Test claim", description="Test description",
        what_was_believed="X was true", what_was_true="X was false",
        confidence_at_time=0.85, corrected_confidence=0.2,
    )

    report = debugger.generate_report()
    assert len(report.failures) == 1
    assert report.pattern_summary["total_failures"] >= 1
