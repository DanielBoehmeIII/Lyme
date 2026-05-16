from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import uuid
import time


class TransferOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    OVERGENERALIZED = "overgeneralized"
    REQUIRED_ADAPTATION = "required_adaptation"


@dataclass
class TransferTest:
    id: str
    source_repo: str
    target_repo: str
    pattern_id: str
    outcome: TransferOutcome
    adaptation_required: bool
    verification_quality: float
    confidence_before: float
    confidence_after: float
    failure_recovery: bool
    adaptation_steps: int = 0
    false_positive: bool = False
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "pattern_id": self.pattern_id,
            "outcome": self.outcome.value,
            "adaptation_required": self.adaptation_required,
            "verification_quality": self.verification_quality,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "failure_recovery": self.failure_recovery,
            "adaptation_steps": self.adaptation_steps,
            "false_positive": self.false_positive,
            "notes": self.notes,
        }


@dataclass
class BenchmarkResult:
    benchmark_id: str
    timestamp: float
    tests: List[TransferTest]
    metrics: Dict
    patterns_tested: List[str]
    repo_pairs: List[Tuple[str, str]]

    def to_dict(self) -> Dict:
        return {
            "benchmark_id": self.benchmark_id,
            "timestamp": self.timestamp,
            "tests": [t.to_dict() for t in self.tests],
            "metrics": self.metrics,
            "patterns_tested": self.patterns_tested,
            "repo_pairs": self.repo_pairs,
        }


class CrossRepoBenchmark:
    def __init__(self):
        self._results: List[BenchmarkResult] = []

    def evaluate_transfer(self, patterns: List, source_fps: List, target_fps: List) -> BenchmarkResult:
        tests: List[TransferTest] = []
        bid = f"bench_{uuid.uuid4().hex[:12]}"

        for pattern in patterns:
            for target_fp in target_fps:
                test = self._run_transfer_test(pattern, source_fps, target_fp)
                tests.append(test)

        metrics = self._compute_metrics(tests)

        repo_pairs = []
        for sf in source_fps:
            for tf in target_fps:
                repo_pairs.append((sf.repo_id, tf.repo_id))

        result = BenchmarkResult(
            benchmark_id=bid,
            timestamp=time.time(),
            tests=tests,
            metrics=metrics,
            patterns_tested=[p.id for p in patterns],
            repo_pairs=repo_pairs,
        )
        self._results.append(result)
        return result

    def _run_transfer_test(self, pattern, source_fps: List, target_fp) -> TransferTest:
        tid = f"test_{uuid.uuid4().hex[:12]}"
        source_repo_ids = [sf.repo_id for sf in source_fps]

        outcome, adaptation, verification, recovery, steps, false_pos = self._simulate_transfer(
            pattern, target_fp
        )

        return TransferTest(
            id=tid,
            source_repo=", ".join(source_repo_ids[:3]),
            target_repo=target_fp.repo_id,
            pattern_id=pattern.id,
            outcome=outcome,
            adaptation_required=adaptation,
            verification_quality=verification,
            confidence_before=self._estimate_confidence_before(pattern, target_fp),
            confidence_after=self._estimate_confidence_after(pattern, target_fp, outcome),
            failure_recovery=recovery,
            adaptation_steps=steps,
            false_positive=false_pos,
        )

    def _simulate_transfer(self, pattern, target_fp) -> tuple:
        match_score = self._compute_match(pattern, target_fp)
        steps = 0
        adaptation = False
        recovery = True
        false_pos = False

        if match_score > 0.8:
            outcome = TransferOutcome.SUCCESS
            verification = 0.9
        elif match_score > 0.6:
            outcome = TransferOutcome.PARTIAL
            adaptation = True
            steps = 1
            verification = 0.7
        elif match_score > 0.4:
            outcome = TransferOutcome.REQUIRED_ADAPTATION
            adaptation = True
            steps = 2
            verification = 0.5
            recovery = False
        elif match_score > 0.2:
            outcome = TransferOutcome.OVERGENErALIZED
            verification = 0.3
            recovery = True
            false_pos = True
        else:
            outcome = TransferOutcome.FAILURE
            verification = 0.1
            recovery = False

        return outcome, adaptation, verification, recovery, steps, false_pos

    def _compute_match(self, pattern, target_fp) -> float:
        score = 0.0
        factors = 0

        target_langs = target_fp.components.get("language", {})
        for tag in pattern.tags:
            for lang in target_langs:
                if tag in lang or lang in tag:
                    score += 0.3
                    factors += 1

        target_arch = target_fp.components.get("arch_patterns", {})
        for sig_key in pattern.signature:
            if sig_key in str(target_arch):
                score += 0.2
                factors += 1

        score += target_fp.test_to_code_ratio * 0.1
        factors += 1

        target_conv = target_fp.convention_signature
        for conv, val in target_conv.items():
            if val > 0.3:
                score += 0.1
                factors += 1

        return score / max(factors, 1)

    def _estimate_confidence_before(self, pattern, target_fp) -> float:
        base = min(pattern.transfer_success_rate, 0.5)
        match = self._compute_match(pattern, target_fp)
        return round((base + match) / 2, 2)

    def _estimate_confidence_after(self, pattern, target_fp, outcome) -> float:
        base = self._estimate_confidence_before(pattern, target_fp)
        if outcome == TransferOutcome.SUCCESS:
            return round(min(base + 0.3, 1.0), 2)
        if outcome == TransferOutcome.PARTIAL:
            return round(base, 2)
        if outcome == TransferOutcome.FAILURE:
            return round(max(base - 0.3, 0.0), 2)
        return round(max(base - 0.1, 0.0), 2)

    def _compute_metrics(self, tests: List[TransferTest]) -> Dict:
        n = len(tests)
        if n == 0:
            return {"error": "no tests"}

        success_rate = sum(1 for t in tests if t.outcome == TransferOutcome.SUCCESS) / n
        partial_rate = sum(1 for t in tests if t.outcome == TransferOutcome.PARTIAL) / n
        failure_rate = sum(1 for t in tests if t.outcome == TransferOutcome.FAILURE) / n
        overgeneralization_rate = sum(1 for t in tests if t.outcome == TransferOutcome.OVERGENErALIZED) / n
        adaptation_required_rate = sum(1 for t in tests if t.adaptation_required) / n
        avg_verification = sum(t.verification_quality for t in tests) / n
        recovery_rate = sum(1 for t in tests if t.failure_recovery) / n
        false_positive_rate = sum(1 for t in tests if t.false_positive) / n

        conf_before = sum(t.confidence_before for t in tests) / n
        conf_after = sum(t.confidence_after for t in tests) / n

        return {
            "total_tests": n,
            "transfer_success_rate": round(success_rate, 3),
            "partial_success_rate": round(partial_rate, 3),
            "failure_rate": round(failure_rate, 3),
            "overgeneralization_rate": round(overgeneralization_rate, 3),
            "adaptation_required_rate": round(adaptation_required_rate, 3),
            "avg_verification_quality": round(avg_verification, 3),
            "failure_recovery_rate": round(recovery_rate, 3),
            "false_positive_rate": round(false_positive_rate, 3),
            "avg_confidence_before": round(conf_before, 3),
            "avg_confidence_after": round(conf_after, 3),
            "calibration_error": round(abs(conf_before - success_rate), 3),
        }

    def compare_runs(self, run_ids: Optional[List[str]] = None) -> Dict:
        results = self._results
        if run_ids:
            results = [r for r in results if r.benchmark_id in run_ids]

        if not results:
            return {"error": "no runs to compare"}

        improvements = []
        for r in results:
            imp = r.metrics.get("avg_confidence_after", 0) - r.metrics.get("avg_confidence_before", 0)
            improvements.append(imp)

        return {
            "run_count": len(results),
            "avg_transfer_success": sum(r.metrics.get("transfer_success_rate", 0) for r in results) / len(results),
            "avg_calibration_error": sum(r.metrics.get("calibration_error", 0) for r in results) / len(results),
            "avg_improvement": sum(improvements) / len(improvements) if improvements else 0,
            "total_tests": sum(r.metrics.get("total_tests", 0) for r in results),
            "trend": "improving" if sum(improvements) > 0 else "declining" if sum(improvements) < 0 else "stable",
        }

    @property
    def results(self) -> List[BenchmarkResult]:
        return self._results

    def save(self, path: Path):
        data = [r.to_dict() for r in self._results]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> List[BenchmarkResult]:
        data = json.loads(path.read_text())
        self._results = []
        for d in data:
            tests = []
            for td in d["tests"]:
                tests.append(TransferTest(
                    id=td["id"],
                    source_repo=td["source_repo"],
                    target_repo=td["target_repo"],
                    pattern_id=td["pattern_id"],
                    outcome=TransferOutcome(td["outcome"]),
                    adaptation_required=td["adaptation_required"],
                    verification_quality=td["verification_quality"],
                    confidence_before=td["confidence_before"],
                    confidence_after=td["confidence_after"],
                    failure_recovery=td["failure_recovery"],
                    adaptation_steps=td.get("adaptation_steps", 0),
                    false_positive=td.get("false_positive", False),
                    notes=td.get("notes", ""),
                ))
            self._results.append(BenchmarkResult(
                benchmark_id=d["benchmark_id"],
                timestamp=d["timestamp"],
                tests=tests,
                metrics=d["metrics"],
                patterns_tested=d["patterns_tested"],
                repo_pairs=[tuple(p) for p in d["repo_pairs"]],
            ))
        return self._results
