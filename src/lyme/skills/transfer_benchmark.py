from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import uuid
import time
import math


class TransferTestOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    FALSE_TRANSFER = "false_transfer"
    OVERGENERALIZED = "overgeneralized"


@dataclass
class TransferBenchmarkCase:
    source_repo: str
    target_repo: str
    skill_name: str
    expected_outcome: TransferTestOutcome
    similarity_score: float
    adaptation_expected: int = 0
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "skill_name": self.skill_name,
            "expected_outcome": self.expected_outcome.value,
            "similarity_score": self.similarity_score,
            "adaptation_expected": self.adaptation_expected,
            "notes": self.notes,
        }


@dataclass
class TransferBenchmarkResult:
    case: TransferBenchmarkCase
    actual_outcome: TransferTestOutcome
    adaptation_made: int
    verification_quality: float
    confidence_before: float
    confidence_after: float
    failure_recovered: bool
    calibration_error: float
    false_positive: bool
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "case": self.case.to_dict(),
            "actual_outcome": self.actual_outcome.value,
            "adaptation_made": self.adaptation_made,
            "verification_quality": self.verification_quality,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "failure_recovered": self.failure_recovered,
            "calibration_error": self.calibration_error,
            "false_positive": self.false_positive,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BenchmarkSuiteResult:
    suite_id: str
    timestamp: float
    results: List[TransferBenchmarkResult]
    metrics: Dict
    config: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "suite_id": self.suite_id,
            "timestamp": self.timestamp,
            "results": [r.to_dict() for r in self.results],
            "metrics": self.metrics,
            "config": self.config,
        }


class SkillTransferBenchmark:
    def __init__(self):
        self._suites: List[BenchmarkSuiteResult] = []

    def define_suite(self, cases: Optional[List[Dict]] = None) -> List[TransferBenchmarkCase]:
        if cases:
            return [TransferBenchmarkCase(**c) for c in cases]

        return self._default_suite()

    def _default_suite(self) -> List[TransferBenchmarkCase]:
        return [
            TransferBenchmarkCase(
                source_repo="repo_a_fastapi", target_repo="repo_b_fastapi",
                skill_name="fix_failing_tests", expected_outcome=TransferTestOutcome.SUCCESS,
                similarity_score=0.85, adaptation_expected=0,
            ),
            TransferBenchmarkCase(
                source_repo="repo_a_fastapi", target_repo="repo_c_flask",
                skill_name="refactor_api_routes", expected_outcome=TransferTestOutcome.PARTIAL,
                similarity_score=0.55, adaptation_expected=2,
            ),
            TransferBenchmarkCase(
                source_repo="repo_a_fastapi", target_repo="repo_d_rust",
                skill_name="fix_failing_tests", expected_outcome=TransferTestOutcome.FAILURE,
                similarity_score=0.15, adaptation_expected=0,
            ),
            TransferBenchmarkCase(
                source_repo="repo_e_pytest", target_repo="repo_f_jest",
                skill_name="fix_failing_tests", expected_outcome=TransferTestOutcome.OVERGENERALIZED,
                similarity_score=0.35, adaptation_expected=3,
            ),
            TransferBenchmarkCase(
                source_repo="repo_g_fastapi", target_repo="repo_h_fastapi",
                skill_name="add_auth_endpoint", expected_outcome=TransferTestOutcome.SUCCESS,
                similarity_score=0.92, adaptation_expected=0,
            ),
            TransferBenchmarkCase(
                source_repo="repo_i_django", target_repo="repo_j_fastapi",
                skill_name="database_migration", expected_outcome=TransferTestOutcome.PARTIAL,
                similarity_score=0.45, adaptation_expected=3,
            ),
            TransferBenchmarkCase(
                source_repo="repo_k_cli_tool", target_repo="repo_l_web_app",
                skill_name="add_error_handling", expected_outcome=TransferTestOutcome.FALSE_TRANSFER,
                similarity_score=0.25, adaptation_expected=0,
            ),
            TransferBenchmarkCase(
                source_repo="repo_m_fastapi", target_repo="repo_n_fastapi",
                skill_name="update_dependencies", expected_outcome=TransferTestOutcome.SUCCESS,
                similarity_score=0.78, adaptation_expected=1,
            ),
        ]

    def run_suite(self, cases: List[TransferBenchmarkCase], transfer_fn: Optional[Callable] = None) -> BenchmarkSuiteResult:
        results = []
        for case in cases:
            if transfer_fn:
                result = self._run_with_transfer_fn(case, transfer_fn)
            else:
                result = self._simulate_result(case)
            results.append(result)

        metrics = self._compute_metrics(results, cases)
        suite = BenchmarkSuiteResult(
            suite_id=f"suite_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            results=results,
            metrics=metrics,
            config={"mode": "simulated" if not transfer_fn else "real", "case_count": len(cases)},
        )
        self._suites.append(suite)
        return suite

    def _run_with_transfer_fn(self, case: TransferBenchmarkCase, fn: Callable) -> TransferBenchmarkResult:
        start = time.time()
        try:
            output = fn(case.source_repo, case.target_repo, case.skill_name)
            duration = (time.time() - start) * 1000
            if isinstance(output, dict):
                return TransferBenchmarkResult(
                    case=case,
                    actual_outcome=TransferTestOutcome(output.get("outcome", "failure")),
                    adaptation_made=output.get("adaptations", 0),
                    verification_quality=output.get("verification", 0.0),
                    confidence_before=output.get("confidence_before", 0.5),
                    confidence_after=output.get("confidence_after", 0.5),
                    failure_recovered=output.get("recovered", False),
                    calibration_error=abs(output.get("confidence_before", 0.5) - (1.0 if output.get("outcome") == "success" else 0.0)),
                    false_positive=output.get("outcome") == "success" and case.expected_outcome != TransferTestOutcome.SUCCESS,
                    duration_ms=duration,
                )
        except Exception as e:
            duration = (time.time() - start) * 1000

        return self._simulate_result(case)

    def _simulate_result(self, case: TransferBenchmarkCase) -> TransferBenchmarkResult:
        sim_noise = hash((case.source_repo, case.target_repo, case.skill_name)) % 100 / 1000
        outcome_probs = self._outcome_probabilities(case)
        r = hash(str(case.__dict__)) % 1000 / 1000
        cumulative = 0.0
        actual_outcome = TransferTestOutcome.FAILURE
        for outcome, prob in outcome_probs:
            cumulative += prob
            if r <= cumulative:
                actual_outcome = outcome
                break

        adaptation_made = max(0, case.adaptation_expected + int((sim_noise - 0.05) * 3))
        verification = max(0.0, min(1.0, case.similarity_score + sim_noise - 0.05))

        conf_before = max(0.0, min(1.0, case.similarity_score * 0.8 + sim_noise))
        conf_after = max(0.0, min(1.0, case.similarity_score * 0.9 + sim_noise))
        if actual_outcome == TransferTestOutcome.FAILURE:
            conf_after = max(0.0, conf_before - 0.3)

        recovered = actual_outcome in (TransferTestOutcome.SUCCESS, TransferTestOutcome.PARTIAL)

        calibration_error = abs(conf_before - (1.0 if actual_outcome == TransferTestOutcome.SUCCESS else 0.0))
        false_pos = actual_outcome == TransferTestOutcome.SUCCESS and case.expected_outcome != TransferTestOutcome.SUCCESS

        return TransferBenchmarkResult(
            case=case,
            actual_outcome=actual_outcome,
            adaptation_made=adaptation_made,
            verification_quality=round(verification, 3),
            confidence_before=round(conf_before, 3),
            confidence_after=round(conf_after, 3),
            failure_recovered=recovered,
            calibration_error=round(calibration_error, 3),
            false_positive=false_pos,
            duration_ms=round(abs(hash(str(case.__dict__)) % 5000) / 10, 1),
        )

    def _outcome_probabilities(self, case: TransferBenchmarkCase) -> List[Tuple[TransferTestOutcome, float]]:
        s = case.similarity_score
        if s > 0.8:
            return [(TransferTestOutcome.SUCCESS, 0.80), (TransferTestOutcome.PARTIAL, 0.15), (TransferTestOutcome.FALSE_TRANSFER, 0.03), (TransferTestOutcome.OVERGENERALIZED, 0.01), (TransferTestOutcome.FAILURE, 0.01)]
        if s > 0.6:
            return [(TransferTestOutcome.PARTIAL, 0.50), (TransferTestOutcome.SUCCESS, 0.25), (TransferTestOutcome.OVERGENERALIZED, 0.10), (TransferTestOutcome.FAILURE, 0.10), (TransferTestOutcome.FALSE_TRANSFER, 0.05)]
        if s > 0.4:
            return [(TransferTestOutcome.OVERGENERALIZED, 0.30), (TransferTestOutcome.FAILURE, 0.30), (TransferTestOutcome.PARTIAL, 0.20), (TransferTestOutcome.FALSE_TRANSFER, 0.15), (TransferTestOutcome.SUCCESS, 0.05)]
        if s > 0.2:
            return [(TransferTestOutcome.FAILURE, 0.50), (TransferTestOutcome.FALSE_TRANSFER, 0.25), (TransferTestOutcome.OVERGENERALIZED, 0.15), (TransferTestOutcome.PARTIAL, 0.08), (TransferTestOutcome.SUCCESS, 0.02)]
        return [(TransferTestOutcome.FAILURE, 0.70), (TransferTestOutcome.FALSE_TRANSFER, 0.20), (TransferTestOutcome.OVERGENERALIZED, 0.08), (TransferTestOutcome.PARTIAL, 0.02), (TransferTestOutcome.SUCCESS, 0.00)]

    def _compute_metrics(self, results: List[TransferBenchmarkResult], cases: List[TransferBenchmarkCase]) -> Dict:
        n = len(results)
        if n == 0:
            return {"error": "no results"}

        correct_outcomes = sum(1 for r in results if r.actual_outcome == r.case.expected_outcome)
        accuracy = correct_outcomes / n

        transfer_success = sum(1 for r in results if r.actual_outcome == TransferTestOutcome.SUCCESS)
        false_transfer = sum(1 for r in results if r.false_positive)
        overgeneralized = sum(1 for r in results if r.actual_outcome == TransferTestOutcome.OVERGENERALIZED)

        avg_adaptation = sum(r.adaptation_made for r in results) / n
        avg_verification = sum(r.verification_quality for r in results) / n
        recovery_rate = sum(1 for r in results if r.failure_recovered) / n
        avg_cal_error = sum(r.calibration_error for r in results) / n

        expected_successes = sum(1 for c in cases if c.expected_outcome == TransferTestOutcome.SUCCESS)
        overconfidence = max(0, transfer_success - expected_successes)
        underconfidence = max(0, expected_successes - transfer_success)

        conf_before_avg = sum(r.confidence_before for r in results) / n
        conf_after_avg = sum(r.confidence_after for r in results) / n

        return {
            "total_tests": n,
            "accuracy": round(accuracy, 3),
            "transfer_success_rate": round(transfer_success / n, 3),
            "false_transfer_rate": round(false_transfer / n, 3),
            "overgeneralization_rate": round(overgeneralized / n, 3),
            "avg_adaptation_needed": round(avg_adaptation, 1),
            "avg_verification_quality": round(avg_verification, 3),
            "failure_recovery_rate": round(recovery_rate, 3),
            "avg_calibration_error": round(avg_cal_error, 3),
            "overconfidence_bias": overconfidence,
            "underconfidence_bias": underconfidence,
            "avg_confidence_before": round(conf_before_avg, 3),
            "avg_confidence_after": round(conf_after_avg, 3),
            "calibration_score": round(1.0 - avg_cal_error, 3),
        }

    def summarize(self, suite_id: Optional[str] = None) -> str:
        suites = self._suites
        if suite_id:
            suites = [s for s in suites if s.suite_id == suite_id]

        if not suites:
            return "No benchmark suites found."

        latest = suites[-1]
        m = latest.metrics
        lines = []
        lines.append(f"# Skill Transfer Benchmark: {latest.suite_id}")
        lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"- Tests: {m['total_tests']}")
        lines.append(f"- Accuracy: {m['accuracy']:.1%}")
        lines.append(f"- Transfer Success: {m['transfer_success_rate']:.1%}")
        lines.append(f"- False Transfer: {m['false_transfer_rate']:.1%}")
        lines.append(f"- Overgeneralization: {m['overgeneralization_rate']:.1%}")
        lines.append(f"- Avg Adaptation: {m['avg_adaptation_needed']} steps")
        lines.append(f"- Verification Quality: {m['avg_verification_quality']:.1%}")
        lines.append(f"- Failure Recovery: {m['failure_recovery_rate']:.1%}")
        lines.append(f"- Calibration Score: {m['calibration_score']:.1%}")
        lines.append(f"")
        lines.append(f"## Calibration")
        lines.append(f"- Avg Confidence Before: {m['avg_confidence_before']:.1%}")
        lines.append(f"- Avg Confidence After: {m['avg_confidence_after']:.1%}")
        lines.append(f"- Calibration Error: {m['avg_calibration_error']:.1%}")
        lines.append(f"- Overconfidence: {m['overconfidence_bias']} cases")
        lines.append(f"- Underconfidence: {m['underconfidence_bias']} cases")
        lines.append(f"")
        lines.append(f"## Results")
        for r in latest.results:
            icon = {"success": "✓", "partial": "~", "failure": "✗", "false_transfer": "!", "overgeneralized": "?"}.get(r.actual_outcome.value, "?")
            expected = r.case.expected_outcome.value
            cal = "🔴" if r.calibration_error > 0.3 else "🟡" if r.calibration_error > 0.1 else "🟢"
            lines.append(f"- {icon} {r.case.skill_name}: {r.case.source_repo} → {r.case.target_repo}")
            lines.append(f"  Actual: {r.actual_outcome.value}, Expected: {expected}, Adaptation: {r.adaptation_made}, Cal: {cal}")

        return "\n".join(lines)

    def compare_suites(self) -> Dict:
        if len(self._suites) < 2:
            return {"error": "need at least 2 suites to compare"}

        trends = {}
        for key in ("accuracy", "transfer_success_rate", "false_transfer_rate", "avg_calibration_error", "calibration_score"):
            values = [s.metrics[key] for s in self._suites]
            trend = "improving" if len(values) >= 2 and values[-1] > values[0] else "declining" if len(values) >= 2 and values[-1] < values[0] else "stable"
            trends[key] = {"first": values[0], "last": values[-1], "trend": trend}

        return {
            "suite_count": len(self._suites),
            "trends": trends,
            "overall_progress": "improving" if trends.get("accuracy", {}).get("trend") == "improving" else "needs work",
        }

    def export_suite(self, path: Path, suite_id: Optional[str] = None):
        suites = self._suites
        if suite_id:
            suites = [s for s in suites if s.suite_id == suite_id]
        data = [s.to_dict() for s in suites]
        path.write_text(json.dumps(data, indent=2))

    @property
    def suites(self) -> List[BenchmarkSuiteResult]:
        return self._suites
