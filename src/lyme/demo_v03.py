"""Lyme v0.3 Demo — Cross-Repository Intelligence + Epistemic Reliability + Safe Autonomy.

Usage:
    python -m lyme.demo_v03
    python -m lyme.demo_v03 --full
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys
import json
import time
import textwrap


def print_header(text: str):
    width = 72
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)
    print()


def print_step(num: int, title: str):
    print(f"\n  ▶ Step {num}: {title}")
    print(f"    {'─' * 50}")


def print_result(label: str, content: str):
    lines = content.strip().split("\n")
    print(f"    [{label}] {lines[0]}")
    for l in lines[1:]:
        print(f"             {l}")


def run_demo(full: bool = False):
    print_header("Lyme v0.3 — Cross-Repo Intelligence + Epistemic Reliability + Safe Autonomy")

    # Step 1: Analyze repos and extract patterns
    print_step(1, "Cross-Repo Pattern Mining")
    print("    Mining patterns across repositories...")

    from lyme.cross_repo.fingerprint import RepoFingerprinter, FingerprintComponent
    from lyme.cross_repo.pattern_extractor import PatternExtractor
    from lyme.cross_repo.clustering import PatternClusterer
    from lyme.cross_repo.scoring import PatternScorer
    from lyme.cross_repo.insight_generator import InsightGenerator

    demo_repos = [Path.cwd()]
    fingerprints = []
    for repo in demo_repos:
        if repo.exists():
            fp = RepoFingerprinter(repo, anonymize=True).fingerprint()
            fingerprints.append(fp)
            print_result("FINGERPRINT", f"{fp.repo_id}: {len(fp.components)} components, {len(fp.dependency_signature)} deps")

    extractor = PatternExtractor()
    patterns = extractor.extract_from_fingerprints(fingerprints)
    print_result("PATTERNS", f"Found {len(patterns)} cross-repo patterns: {', '.join(p.name for p in patterns[:5])}")

    clusterer = PatternClusterer()
    clusters = clusterer.cluster_fingerprints(fingerprints)
    clusterer.label_clusters(clusters)
    if clusters:
        print_result("CLUSTERS", f"{len(clusters)} cluster(s), largest: {clusters[0].label} ({clusters[0].size} repos, {clusters[0].intra_cluster_similarity:.0%} similarity)")

    insights = InsightGenerator().generate(patterns, clusters)
    print_result("INSIGHTS", f"Generated {len(insights)} transferable insights")
    if insights:
        print(f"             Top: {insights[0].title} ({insights[0].confidence.value})")

    scorer = PatternScorer()
    if patterns:
        score = scorer.score_pattern(patterns[0])
        print_result("CONFIDENCE", f"Pattern confidence: {score.overall:.2f} (uncertainty: {score.uncertainty:.2f})")

    # Step 2: Ecosystem Knowledge
    print_step(2, "Ecosystem Knowledge Graph")
    print("    Querying Python/FastAPI ecosystem knowledge...")

    from lyme.ecosystem.fastapi_knowledge import FastAPIEcosystemKnowledge
    from lyme.ecosystem.compatibility import CompatibilityChecker
    from lyme.ecosystem.security_zones import SecurityZoneDetector

    ecosystem = FastAPIEcosystemKnowledge()
    g = ecosystem.graph
    print_result("GRAPH", f"Ecosystem graph: {g.node_count} nodes, {g.edge_count} edges")

    bugs = ecosystem.get_known_bugs()
    print_result("BUGS", f"{len(bugs)} known bugs in ecosystem knowledge base")
    if bugs:
        print(f"             Top: {bugs[0]['name']} ({bugs[0]['severity']})")

    advisories = ecosystem.get_security_advisories()
    print_result("SECURITY", f"{len(advisories)} security advisories mapped")

    checker = CompatibilityChecker()
    sample_deps = {"fastapi": "0.115.0", "pydantic": "1.9.0", "python": "3.9"}
    report = checker.check_compatibility(sample_deps)
    print_result("COMPAT", f"Compatibility score: {report.overall_score:.2f} ({report.total_issues} issues)")

    # Step 3: Transfer Benchmark
    print_step(3, "Skill Transfer Benchmark")
    from lyme.skills.transfer_benchmark import SkillTransferBenchmark

    benchmark = SkillTransferBenchmark()
    cases = benchmark.define_suite()
    result = benchmark.run_suite(cases)
    m = result.metrics
    print_result("BENCHMARK", f"Transfer accuracy: {m['accuracy']:.0%}, success: {m['transfer_success_rate']:.0%}")
    print(f"             False transfer: {m['false_transfer_rate']:.0%}, overgeneralization: {m['overgeneralization_rate']:.0%}")
    print(f"             Calibration error: {m['avg_calibration_error']:.0%}")

    # Step 4: Evidence Theory
    print_step(4, "Evidence Theory — Knowledge Confidence")
    from lyme.epistemology.evidence_theory import EvidenceTheoryEngine, Evidence, EvidenceType, EvidenceSource

    theory = EvidenceTheoryEngine()
    claim = theory.make_claim("This repository is a Python project", domain="code_analysis")
    theory.add_evidence(claim.id, Evidence(
        id="ev1", evidence_type=EvidenceType.CODE, source=EvidenceSource.STATIC_ANALYSIS,
        content="Found pyproject.toml with Python build config",
        source_location="pyproject.toml", reliability=0.95, confidence=0.95,
    ))
    theory.add_evidence(claim.id, Evidence(
        id="ev2", evidence_type=EvidenceType.CODE, source=EvidenceSource.STATIC_ANALYSIS,
        content="Found .py files in source tree",
        source_location="src/", reliability=0.90, confidence=0.90,
    ))
    theory.add_evidence(claim.id, Evidence(
        id="ev3", evidence_type=EvidenceType.PACKAGE_METADATA, source=EvidenceSource.PACKAGE_REGISTRY,
        content="Python version constraint: >=3.10",
        source_location="pyproject.toml", reliability=0.85, confidence=0.85,
    ))

    assessment = theory.assess_claim(claim.id)
    print_result("CLAIM", f"\"{claim.statement[:60]}...\"")
    print(f"             Confidence: {assessment.overall_confidence:.0%}")
    print(f"             Evidence: {assessment.evidence_count} sources")
    print(f"             Hallucination risk: {claim.hallucination_risk.value}")
    print(f"             Recommendation: {assessment.recommendation}")

    # Step 5: Confidence Calibration
    print_step(5, "Confidence Calibration")
    from lyme.epistemology.confidence_calibration import ConfidenceCalibrator

    calibrator = ConfidenceCalibrator()
    for pred, actual in [(0.9, True), (0.8, True), (0.7, True), (0.6, True),
                          (0.5, False), (0.4, True), (0.3, False), (0.95, False),
                          (0.85, True), (0.75, True), (0.65, True), (0.55, False)]:
        calibrator.record(pred, actual, domain="code_analysis")

    cal_report = calibrator.generate_report()
    print_result("CALIBRATION", f"ECE: {cal_report.curve.ece:.4f}, MCE: {cal_report.curve.mce:.4f}")
    print(f"             Overconfident cases: {cal_report.metrics['overconfidence_cases']}")
    print(f"             Recommendation: {cal_report.recommendations[0] if cal_report.recommendations else 'none'}")

    # Step 6: Sensitive Code Detection
    print_step(6, "Sensitive Code Detection")
    from lyme.governance.sensitive_code import SensitiveCodeDetector

    detector = SensitiveCodeDetector()
    if Path.cwd().exists():
        sec_result = detector.detect(Path.cwd())
        print_result("SENSITIVE", f"Sensitive zones: {len(sec_result.zones)} | Critical: {sec_result.total_critical} | High: {sec_result.total_high}")
        print(f"             Risk: {sec_result.risk_summary['risk_level']} ({sec_result.risk_summary['total_risk_score']:.2f})")

    # Step 7: Autonomy Policy
    print_step(7, "Autonomy Policy Engine")
    from lyme.governance.autonomy_policy import AutonomyPolicyEngine, ActionType, AutonomyLevel

    policy = AutonomyPolicyEngine()
    context = {
        "autonomy_level": "verified_auto",
        "test_coverage": 0.4,
        "edit_size": 30,
        "confidence": 0.75,
        "sensitive_zone": False,
        "repo_risk": 0.3,
    }

    for action in [ActionType.READ_ONLY, ActionType.MODIFY_FILES, ActionType.DELETE_FILES, ActionType.MODIFY_SECRETS]:
        eval_result = policy.evaluate(action, context)
        status = "✅ ALLOWED" if eval_result.allowed else "❌ DENIED"
        print(f"             {status}: {action.value} (risk: {eval_result.risk_score:.2f})")
        if eval_result == eval_result and not eval_result.allowed:
            print(f"               Reason: {eval_result.reason}")

    # Step 8: Action Review Board
    print_step(8, "Action Review Board")
    from lyme.governance.review_board import ActionReviewBoard, ReviewRequest

    board = ActionReviewBoard()
    request = ReviewRequest(
        id="demo_req_001",
        title="Update authentication module",
        description="Refactor password hashing to use bcrypt with increased work factor",
        action_type="modify_files",
        files_changed=["src/auth/password.py", "src/auth/session.py", "tests/test_auth.py"],
        diff_summary="Replace passlib with bcrypt; update session token generation to use SHA-256",
        risk_score=0.65,
        proposer_notes="Security audit recommended upgrading password hashing; changes are backward compatible",
        context={"has_tests": True, "impact_scope": "auth", "breaking": False},
    )

    decision = board.submit_request(request)
    verdict_icon = {"approve": "✅", "reject": "❌", "revise": "🔄", "require_human": "👤"}
    print_result("BOARD", f"Verdict: {verdict_icon.get(decision.final_verdict.value, '❓')} {decision.final_verdict.value.upper()}")
    print(f"             Majority: {decision.majority}")
    print(f"             Human required: {decision.human_required}")
    print(f"             Reasoning: {decision.reasoning[:100]}...")

    # Summary
    print_header("v0.3 Demo Complete")
    print("  Lyme v0.3 demonstrates:")
    print("  ✅ Cross-repository pattern mining and insight generation")
    print("  ✅ Ecosystem knowledge graph with dependency/security awareness")
    print("  ✅ Skill transfer benchmarking with calibration")
    print("  ✅ Evidence-grounded claims with quantified uncertainty")
    print("  ✅ Confidence calibration with overconfidence detection")
    print("  ✅ Sensitive code zone detection")
    print("  ✅ Autonomy policy enforcement")
    print("  ✅ Computational action review board")
    print()
    print("  Lyme is not just acting.")
    print("  Lyme is knowing what it knows.")


def main():
    full = "--full" in sys.argv
    run_demo(full)


if __name__ == "__main__":
    main()
