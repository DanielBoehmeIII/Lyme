"""RollbackSafety — tested recovery paths with verification."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class SafetyStatus(str, Enum):
    SAFE = "safe"
    CONDITIONAL = "conditional"
    RISKY = "risky"
    UNSAFE = "unsafe"


@dataclass
class RecoveryProcedure:
    name: str
    description: str
    steps: List[str]
    verified: bool
    last_tested: Optional[float]
    success_rate: float
    estimated_duration_sec: float
    side_effects: List[str]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "verified": self.verified,
            "success_rate": round(self.success_rate, 3),
            "duration_sec": round(self.estimated_duration_sec, 1),
            "side_effects": self.side_effects[:3],
        }


@dataclass
class RollbackSafetyReport:
    total_procedures: int
    verified_count: int
    overall_status: SafetyStatus
    safe_procedures: List[Dict]
    risky_procedures: List[Dict]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  ROLLBACK SAFETY REPORT")
        lines.append("=" * 70)
        icons = {SafetyStatus.SAFE: "✅", SafetyStatus.CONDITIONAL: "🟡",
                 SafetyStatus.RISKY: "⚠️", SafetyStatus.UNSAFE: "🚫"}
        lines.append(f"  Status: {icons.get(self.overall_status, '•')} {self.overall_status.value}")
        lines.append(f"  Procedures: {self.total_procedures} | "
                     f"Verified: {self.verified_count}/{self.total_procedures}")
        lines.append("")
        if self.safe_procedures:
            lines.append("  Safe Procedures:")
            for p in self.safe_procedures[:3]:
                lines.append(f"    ✅ {p['name']} ({p['success_rate']:.0%} success)")
        if self.risky_procedures:
            lines.append("  Risky Procedures:")
            for p in self.risky_procedures[:3]:
                lines.append(f"    ⚠️ {p['name']} ({p['success_rate']:.0%} success)")
        if self.recommendations:
            lines.append("-" * 70)
            for r in self.recommendations:
                lines.append(f"  • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class RollbackSafety:
    def __init__(self):
        self._procedures: Dict[str, RecoveryProcedure] = {}
        self._outcome_counts: Dict[str, List[bool]] = {}

    def register(self, name: str, description: str, steps: List[str],
                 estimated_duration_sec: float = 60.0,
                 side_effects: Optional[List[str]] = None) -> None:
        self._procedures[name] = RecoveryProcedure(
            name=name,
            description=description,
            steps=steps,
            verified=False,
            last_tested=None,
            success_rate=0.0,
            estimated_duration_sec=estimated_duration_sec,
            side_effects=side_effects or [],
        )

    def verify(self, name: str, verifier_fn: Callable) -> bool:
        proc = self._procedures.get(name)
        if not proc:
            return False
        try:
            success = verifier_fn(proc)
            proc.verified = success
            import time
            proc.last_tested = time.time()
            proc.success_rate = 1.0 if success else 0.0
            return success
        except Exception:
            proc.verified = False
            return False

    def record_outcome(self, name: str, success: bool, duration_sec: float) -> None:
        proc = self._procedures.get(name)
        if not proc:
            return
        import time
        proc.last_tested = time.time()
        if name not in self._outcome_counts:
            self._outcome_counts[name] = []
        self._outcome_counts[name].append(success)
        successes = sum(1 for s in self._outcome_counts[name] if s)
        total = len(self._outcome_counts[name])
        proc.success_rate = successes / max(total, 1)
        proc.verified = proc.success_rate > 0.6 and total >= 2

    def check(self, name: str) -> SafetyStatus:
        proc = self._procedures.get(name)
        if not proc:
            return SafetyStatus.UNSAFE
        if not proc.verified:
            return SafetyStatus.UNSAFE
        if proc.success_rate >= 0.95:
            return SafetyStatus.SAFE
        if proc.success_rate >= 0.8:
            return SafetyStatus.CONDITIONAL
        return SafetyStatus.RISKY

    def report(self) -> RollbackSafetyReport:
        if not self._procedures:
            return RollbackSafetyReport(
                total_procedures=0, verified_count=0,
                overall_status=SafetyStatus.UNSAFE,
                safe_procedures=[], risky_procedures=[],
                recommendations=["Register recovery procedures to verify rollback safety"],
            )

        verified = sum(1 for p in self._procedures.values() if p.verified)
        safe = [p.to_dict() for p in self._procedures.values()
               if p.success_rate >= 0.9 and p.verified]
        risky = [p.to_dict() for p in self._procedures.values()
                if p.success_rate < 0.7 or not p.verified]

        if verified == len(self._procedures) and not risky:
            status = SafetyStatus.SAFE
        elif verified > 0:
            status = SafetyStatus.CONDITIONAL
        else:
            status = SafetyStatus.UNSAFE

        recommendations: List[str] = []
        if not verified:
            recommendations.append("No recovery procedures verified — run verification tests")
        if risky:
            recommendations.append(f"Review {len(risky)} risky procedures with low success rate")
        unverified = [n for n, p in self._procedures.items() if not p.verified]
        if unverified:
            recommendations.append(f"Verify procedures: {', '.join(unverified[:3])}")
        if not recommendations:
            recommendations.append("All recovery procedures verified and safe")

        return RollbackSafetyReport(
            total_procedures=len(self._procedures),
            verified_count=verified,
            overall_status=status,
            safe_procedures=safe,
            risky_procedures=risky,
            recommendations=recommendations,
        )
