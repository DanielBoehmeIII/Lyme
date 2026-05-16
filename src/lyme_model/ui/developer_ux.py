"""Week 129 — Developer UX for Local Agents.

Focus:
- clear progress updates
- visible mode choice
- confidence display
- pause/resume
- show current context packet
- show why a file was selected
- show risk before edit
- show verification status
- concise final report
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import time


@dataclass
class UXPhase:
    name: str
    status: str
    detail: str
    confidence: Optional[float] = None
    risk: Optional[str] = None
    latency_s: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def render(self) -> str:
        icon = {"completed": "✓", "in_progress": "→", "pending": "·", "failed": "✗", "refused": "⊘"}.get(self.status, "?")
        parts = [f"{icon} {self.name}"]
        if self.detail:
            parts.append(f"  {self.detail}")
        if self.confidence is not None:
            bar = "█" * int(self.confidence * 10) + "░" * (10 - int(self.confidence * 10))
            parts.append(f"  Confidence: {bar} {self.confidence:.0%}")
        if self.risk:
            parts.append(f"  Risk: {self.risk.upper()}")
        if self.warnings:
            for w in self.warnings:
                parts.append(f"  ⚠ {w}")
        if self.latency_s > 0.5:
            parts.append(f"  Time: {self.latency_s:.1f}s")
        return "\n".join(parts)


@dataclass
class FileSelectionReason:
    file_path: str
    reason: str
    relevance_score: float
    contains_keywords: List[str] = field(default_factory=list)

    def render(self) -> str:
        kw = f" [{', '.join(self.contains_keywords[:3])}]" if self.contains_keywords else ""
        return f"  {self.file_path} ({self.relevance_score:.0%} relevant) — {self.reason}{kw}"


@dataclass
class VerificationDisplay:
    step: str
    command: str
    passed: Optional[bool] = None
    output_preview: str = ""
    latency_s: float = 0.0

    def render(self) -> str:
        icon = "✓" if self.passed else "✗" if self.passed is False else "?"
        status = "PASS" if self.passed else "FAIL" if self.passed is False else "RUNNING"
        return f"  {icon} {self.command} — {status} ({self.latency_s:.1f}s)"


class DeveloperUX:
    """User experience for Lyme Model — transparency and trust."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.phases: List[UXPhase] = []
        self.file_selections: List[FileSelectionReason] = []
        self.verifications: List[VerificationDisplay] = []
        self._start_time = time.time()

    def begin_phase(self, name: str, detail: str = "", confidence: Optional[float] = None,
                    risk: Optional[str] = None):
        phase = UXPhase(name=name, status="in_progress", detail=detail,
                        confidence=confidence, risk=risk)
        self.phases.append(phase)
        if self.verbose:
            print(phase.render())
        return phase

    def complete_phase(self, name: str, latency_s: Optional[float] = None,
                       warnings: Optional[List[str]] = None):
        for p in self.phases:
            if p.name == name and p.status == "in_progress":
                p.status = "completed"
                p.latency_s = latency_s or (time.time() - self._start_time)
                p.warnings = warnings or []
                if self.verbose:
                    print(f"  → Completed ({p.latency_s:.1f}s)")
                break

    def fail_phase(self, name: str, reason: str):
        for p in self.phases:
            if p.name == name and p.status == "in_progress":
                p.status = "failed"
                p.detail = reason
                if self.verbose:
                    print(f"  → FAILED: {reason}")
                break

    def explain_file(self, file_path: str, reason: str, relevance: float = 0.5,
                     keywords: Optional[List[str]] = None):
        fsr = FileSelectionReason(file_path=file_path, reason=reason,
                                   relevance_score=relevance,
                                   contains_keywords=keywords or [])
        self.file_selections.append(fsr)
        if self.verbose:
            print(fsr.render())

    def show_verification(self, step: str, command: str, passed: Optional[bool] = None,
                          output: str = "", latency_s: float = 0.0):
        vd = VerificationDisplay(step=step, command=command, passed=passed,
                                 output_preview=output[:200], latency_s=latency_s)
        self.verifications.append(vd)
        if self.verbose:
            print(vd.render())

    def show_risk_before_edit(self, file_path: str, risk_level: str, reason: str):
        if self.verbose:
            print(f"\n⚠ RISK: {risk_level.upper()}")
            print(f"  File: {file_path}")
            print(f"  Reason: {reason}")
            print(f"  Confirm? (auto-continuing in verbose mode)")

    def show_context_packet(self, subtask_id: str, files: List[str],
                            summary: str, assumptions: List[str],
                            token_estimate: int):
        if self.verbose:
            print(f"\n📦 Context Packet [{subtask_id}]")
            print(f"  Files: {', '.join(files[:5])}")
            print(f"  From previous: {summary[:100]}")
            print(f"  Assumptions: {len(assumptions)}")
            print(f"  Estimated tokens: {token_estimate}")

    def show_mode_choice(self, mode: str, reasoning: List[str]):
        if self.verbose:
            print(f"\n🔧 Mode: {mode}")
            for r in reasoning[:3]:
                print(f"  {r}")

    def generate_final_report(self, success: bool, total_time_s: float) -> dict:
        report = {
            "success": success,
            "total_time_s": round(total_time_s, 1),
            "phases_completed": len([p for p in self.phases if p.status == "completed"]),
            "phases_total": len(self.phases),
            "files_examined": len(self.file_selections),
            "verifications_run": len(self.verifications),
            "verifications_passed": sum(1 for v in self.verifications if v.passed),
            "verifications_failed": sum(1 for v in self.verifications if v.passed is False),
        }

        if self.verbose:
            print("\n" + "=" * 50)
            print("FINAL REPORT")
            print("=" * 50)
            print(f"  {'✓' if success else '✗'} {'Success' if success else 'Failed'} in {report['total_time_s']}s")
            print(f"  Phases: {report['phases_completed']}/{report['phases_total']}")
            print(f"  Files examined: {report['files_examined']}")
            print(f"  Verifications: {report['verifications_passed']} passed, {report['verifications_failed']} failed")

        return report


ux = DeveloperUX()
