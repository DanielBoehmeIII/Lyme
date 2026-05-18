"""SpecializedOrchestrator — routes tasks to the right specialized model slice."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class SliceType(str, Enum):
    BUG_LOCALIZATION = "bug_localization"
    TEST_REPAIR = "test_repair"
    PATCH_PLANNING = "patch_planning"
    MULTI_FILE_EDIT = "multi_file_edit"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    DEPENDENCY_MANAGEMENT = "dependency_management"
    SECURITY_REVIEW = "security_review"


@dataclass
class ModelSlice:
    slice_type: SliceType
    model_path: str
    adapter_path: str
    hardware_requirement: str
    avg_latency_sec: float
    success_rate: float
    total_calls: int
    token_limit: int
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "slice_type": self.slice_type.value,
            "model_path": self.model_path,
            "adapter_path": self.adapter_path,
            "hardware": self.hardware_requirement,
            "avg_latency_sec": round(self.avg_latency_sec, 2),
            "success_rate": round(self.success_rate, 3),
            "total_calls": self.total_calls,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class SliceRoutingDecision:
    task_type: str
    selected_slice: SliceType
    model_path: str
    confidence: float
    estimated_latency_sec: float
    fallback_slices: List[str]
    rationale: str

    def to_dict(self) -> Dict:
        return {
            "task_type": self.task_type,
            "selected_slice": self.selected_slice.value,
            "confidence": round(self.confidence, 3),
            "estimated_latency_sec": round(self.estimated_latency_sec, 1),
        }


@dataclass
class OrchestratorReport:
    total_slices: int
    total_routes: int
    slice_performance: List[Dict]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  SPECIALIZED ORCHESTRATOR")
        lines.append("=" * 70)
        lines.append(f"  Slices: {self.total_slices} | Routes: {self.total_routes}")
        lines.append("")
        for sp in self.slice_performance:
            lines.append(f"  {sp['slice_type']}: {sp['success_rate']:.0%} success "
                         f"({sp['total_calls']} calls, {sp['avg_latency']:.1f}s avg)")
        if self.recommendations:
            lines.append("-" * 70)
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class SpecializedOrchestrator:
    def __init__(self):
        self._slices: Dict[SliceType, ModelSlice] = {}
        self._routing_history: List[SliceRoutingDecision] = []
        self._task_runners: Dict[SliceType, Callable] = {}

    def register_slice(self, slice_type: SliceType, model_path: str,
                        adapter_path: str = "",
                        hardware_requirement: str = "8gb",
                        token_limit: int = 4096) -> None:
        self._slices[slice_type] = ModelSlice(
            slice_type=slice_type,
            model_path=model_path,
            adapter_path=adapter_path,
            hardware_requirement=hardware_requirement,
            avg_latency_sec=0.0,
            success_rate=1.0,
            total_calls=0,
            token_limit=token_limit,
            confidence=0.5,
        )

    def register_runner(self, slice_type: SliceType, runner_fn: Callable) -> None:
        self._task_runners[slice_type] = runner_fn

    def route(self, task_type: str, task_input: Any,
              hardware_profile: str = "8gb") -> SliceRoutingDecision:
        slice_type = self._resolve_slice_type(task_type)
        primary = self._slices.get(slice_type)

        fallbacks: List[str] = []
        for st, sl in self._slices.items():
            if st != slice_type and sl.confidence > 0.3:
                fallbacks.append(st.value)

        if primary and self._check_hardware(primary, hardware_profile):
            decision = SliceRoutingDecision(
                task_type=task_type,
                selected_slice=slice_type,
                model_path=primary.model_path,
                confidence=primary.confidence,
                estimated_latency_sec=primary.avg_latency_sec or 10.0,
                fallback_slices=fallbacks,
                rationale=f"Primary slice {slice_type.value} on {primary.model_path}",
            )
        elif fallbacks:
            fb_type = SliceType(fallbacks[0])
            fb_slice = self._slices[fb_type]
            decision = SliceRoutingDecision(
                task_type=task_type,
                selected_slice=fb_type,
                model_path=fb_slice.model_path,
                confidence=fb_slice.confidence * 0.8,
                estimated_latency_sec=fb_slice.avg_latency_sec or 15.0,
                fallback_slices=fallbacks[1:],
                rationale=f"Fallback to {fb_type.value} (primary {slice_type.value} unavailable)",
            )
        else:
            decision = SliceRoutingDecision(
                task_type=task_type,
                selected_slice=SliceType.CODE_REVIEW,
                model_path="qwen2.5-coder:7b",
                confidence=0.3,
                estimated_latency_sec=30.0,
                fallback_slices=[],
                rationale="No specialized slice available — using general code model",
            )

        self._routing_history.append(decision)
        runner = self._task_runners.get(decision.selected_slice)
        if runner:
            self._record_outcome(decision.selected_slice, True, decision.estimated_latency_sec)

        return decision

    def _resolve_slice_type(self, task_type: str) -> SliceType:
        mapping: Dict[str, SliceType] = {
            "bug": SliceType.BUG_LOCALIZATION,
            "fix": SliceType.TEST_REPAIR,
            "test": SliceType.TEST_REPAIR,
            "patch": SliceType.PATCH_PLANNING,
            "edit": SliceType.MULTI_FILE_EDIT,
            "refactor": SliceType.REFACTORING,
            "review": SliceType.CODE_REVIEW,
            "doc": SliceType.DOCUMENTATION,
            "arch": SliceType.ARCHITECTURE,
            "security": SliceType.SECURITY_REVIEW,
        }
        t = task_type.lower()
        for key, st in mapping.items():
            if key in t:
                return st
        return SliceType.CODE_REVIEW

    def _check_hardware(self, slice: ModelSlice, profile: str) -> bool:
        levels = ["4gb", "8gb", "12gb", "16gb", "24gb", "48gb"]
        try:
            return levels.index(profile) >= levels.index(slice.hardware_requirement)
        except ValueError:
            return True

    def _record_outcome(self, slice_type: SliceType, success: bool, latency: float) -> None:
        sl = self._slices.get(slice_type)
        if not sl:
            return
        sl.total_calls += 1
        sl.avg_latency_sec = (
            (sl.avg_latency_sec * (sl.total_calls - 1) + latency) / sl.total_calls
        )
        sl.success_rate = (
            (sl.success_rate * (sl.total_calls - 1) + (1.0 if success else 0.0))
            / sl.total_calls
        )
        old_conf = sl.confidence
        adjustment = 0.05 if success else -0.1
        sl.confidence = max(0.0, min(1.0, old_conf + adjustment))

    def report(self) -> OrchestratorReport:
        slice_perf = []
        for st, sl in self._slices.items():
            slice_perf.append({
                "slice_type": st.value,
                "success_rate": sl.success_rate,
                "total_calls": sl.total_calls,
                "avg_latency": round(sl.avg_latency_sec, 1),
                "confidence": round(sl.confidence, 2),
            })
        slice_perf.sort(key=lambda x: -x["success_rate"])

        recommendations: List[str] = []
        unused = [s for s in slice_perf if s["total_calls"] == 0]
        if unused:
            recommendations.append(f"Unused slices: {', '.join(s['slice_type'] for s in unused)}")
        low_conf = [s for s in slice_perf if s["confidence"] < 0.3 and s["total_calls"] > 5]
        if low_conf:
            recommendations.append(f"Low confidence slices need retraining: "
                                  f"{', '.join(s['slice_type'] for s in low_conf)}")
        if not recommendations:
            recommendations.append("All slices performing within expected parameters")

        return OrchestratorReport(
            total_slices=len(self._slices),
            total_routes=len(self._routing_history),
            slice_performance=slice_perf,
            recommendations=recommendations,
        )
