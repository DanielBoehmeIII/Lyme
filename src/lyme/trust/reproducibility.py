"""ReproducibilityEngine — ensures deterministic behavior and verifiable outputs."""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class DeterminismLevel(str, Enum):
    NONE = "none"
    SEEDED = "seeded"
    LOCKED = "locked"
    VERIFIED = "verified"


@dataclass
class ExecutionSignature:
    inputs_hash: str
    parameters_hash: str
    environment_hash: str
    expected_output_hash: str
    actual_output_hash: str
    deterministic: bool
    determinism_level: DeterminismLevel
    seed: Optional[int]
    model_name: str
    temperature: float
    top_p: float

    def to_dict(self) -> Dict:
        return {
            "inputs_hash": self.inputs_hash[:16],
            "deterministic": self.deterministic,
            "level": self.determinism_level.value,
            "model": self.model_name,
        }


@dataclass
class ReproducibilityReport:
    total_executions: int
    deterministic_count: int
    non_deterministic_count: int
    determinism_rate: float
    verified_signatures: int
    mismatches: List[Dict]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  REPRODUCIBILITY REPORT")
        lines.append("=" * 70)
        lines.append(f"  Executions: {self.total_executions} | "
                     f"Deterministic: {self.deterministic_count}/{self.total_executions}")
        lines.append(f"  Determinism Rate: {self.determinism_rate:.0%}")
        lines.append(f"  Verified Signatures: {self.verified_signatures}")
        if self.mismatches:
            lines.append(f"  Mismatches: {len(self.mismatches)}")
            for m in self.mismatches[:3]:
                lines.append(f"    ❌ {m.get('description', 'unknown')[:60]}")
        if self.recommendations:
            lines.append("-" * 70)
            for r in self.recommendations:
                lines.append(f"  • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class ReproducibilityEngine:
    def __init__(self):
        self._signatures: List[ExecutionSignature] = []
        self._mismatches: List[Dict] = []
        self._environment_snapshot: Optional[str] = None

    def snapshot_environment(self) -> str:
        import platform
        info = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "timestamp": time.time(),
        }
        self._environment_snapshot = hashlib.sha256(
            json.dumps(info, sort_keys=True).encode()
        ).hexdigest()
        return self._environment_snapshot

    def verify_execution(self, fn: Callable, inputs: Any,
                         model_name: str = "unknown",
                         seed: Optional[int] = None,
                         temperature: float = 0.0,
                         top_p: float = 1.0,
                         runs: int = 2) -> ReproducibilityReport:
        inputs_str = json.dumps(inputs, sort_keys=True, default=str)
        inputs_hash = hashlib.sha256(inputs_str.encode()).hexdigest()

        results = []
        for i in range(runs):
            result = fn(inputs)
            result_str = json.dumps(result, sort_keys=True, default=str)
            results.append(result_str)

        all_same = len(set(results)) == 1
        expected = results[0] if results else ""

        sig = ExecutionSignature(
            inputs_hash=inputs_hash,
            parameters_hash=hashlib.sha256(
                json.dumps({"seed": seed, "temperature": temperature, "top_p": top_p}).encode()
            ).hexdigest(),
            environment_hash=self._environment_snapshot or self.snapshot_environment(),
            expected_output_hash=hashlib.sha256(expected.encode()).hexdigest(),
            actual_output_hash=hashlib.sha256(expected.encode()).hexdigest(),
            deterministic=all_same,
            determinism_level=DeterminismLevel.VERIFIED if all_same else DeterminismLevel.NONE,
            seed=seed,
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
        )
        self._signatures.append(sig)

        if not all_same:
            self._mismatches.append({
                "inputs": inputs_str[:50],
                "model": model_name,
                "run_count": runs,
                "unique_outputs": len(set(results)),
                "description": f"Non-deterministic: {len(set(results))} different outputs across {runs} runs",
            })

        return self.report()

    def verify_rerun(self, fn: Callable, inputs: Any,
                     previous_signature: ExecutionSignature) -> bool:
        result = fn(inputs)
        result_str = json.dumps(result, sort_keys=True, default=str)
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()
        return result_hash == previous_signature.expected_output_hash

    def report(self) -> ReproducibilityReport:
        total = len(self._signatures)
        deterministic = sum(1 for s in self._signatures if s.deterministic)

        recommendations: List[str] = []
        if total > 0 and deterministic / total < 0.8:
            recommendations.append("Set temperature=0.0 and seed for deterministic outputs")
            recommendations.append("Lock random seeds across all model calls")
        if self._mismatches:
            recommendations.append("Investigate non-deterministic executions for root cause")
        if not recommendations and total > 0:
            recommendations.append("All executions are reproducible")
        if total == 0:
            recommendations.append("Run reproducibility checks to build trust baseline")

        return ReproducibilityReport(
            total_executions=total,
            deterministic_count=deterministic,
            non_deterministic_count=total - deterministic,
            determinism_rate=deterministic / max(total, 1),
            verified_signatures=len(self._signatures),
            mismatches=self._mismatches,
            recommendations=recommendations,
        )
