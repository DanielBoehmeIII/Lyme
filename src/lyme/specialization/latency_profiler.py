"""LatencyProfiler — measures and optimizes end-to-end latency for model calls."""
from __future__ import annotations
import time
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class PipelineStage(str, Enum):
    MODEL_LOAD = "model_load"
    TOKENIZE = "tokenize"
    INFERENCE = "inference"
    DETOKENIZE = "detokenize"
    TOOL_EXECUTION = "tool_execution"
    VERIFICATION = "verification"
    MEMORY_RETRIEVAL = "memory_retrieval"
    CONTEXT_ASSEMBLY = "context_assembly"


@dataclass
class LatencySample:
    stage: PipelineStage
    duration_sec: float
    timestamp: float
    metadata: str = ""

    def to_dict(self) -> Dict:
        return {
            "stage": self.stage.value,
            "duration_sec": round(self.duration_sec, 3),
            "metadata": self.metadata[:40],
        }


@dataclass
class StageStats:
    stage: PipelineStage
    samples: int
    min_sec: float
    max_sec: float
    avg_sec: float
    median_sec: float
    p95_sec: float
    total_sec: float

    def to_dict(self) -> Dict:
        return {
            "stage": self.stage.value,
            "samples": self.samples,
            "avg_sec": round(self.avg_sec, 3),
            "median_sec": round(self.median_sec, 3),
            "p95_sec": round(self.p95_sec, 3),
            "min_sec": round(self.min_sec, 3),
            "max_sec": round(self.max_sec, 3),
        }


@dataclass
class LatencyReport:
    total_samples: int
    stage_stats: List[StageStats]
    total_time_sec: float
    bottleneck: Optional[str]
    recommendations: List[str]

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  LATENCY PROFILER")
        lines.append("=" * 70)
        lines.append(f"  Total Samples: {self.total_samples}")
        lines.append(f"  Total Time: {self.total_time_sec:.1f}s")
        if self.bottleneck:
            lines.append(f"  Bottleneck: {self.bottleneck}")
        lines.append("")
        for s in sorted(self.stage_stats, key=lambda x: -x.avg_sec):
            bar = "█" * int(s.avg_sec / max(x.avg_sec for x in self.stage_stats) * 20) if self.stage_stats else 0
            lines.append(f"  {s.stage.value}: avg={s.avg_sec:.3f}s "
                         f"p95={s.p95_sec:.3f}s {bar}")
            lines.append(f"    ({s.samples} samples, range {s.min_sec:.3f}-{s.max_sec:.3f})")
        if self.recommendations:
            lines.append("-" * 70)
            for r in self.recommendations:
                lines.append(f"  • {r}")
        lines.append("=" * 70)
        return "\n".join(lines)


class LatencyProfiler:
    def __init__(self):
        self._samples: List[LatencySample] = []

    def record(self, stage: PipelineStage, duration_sec: float,
               metadata: str = "") -> None:
        self._samples.append(LatencySample(
            stage=stage,
            duration_sec=duration_sec,
            timestamp=time.time(),
            metadata=metadata,
        ))

    def measure(self, stage: PipelineStage, fn: Callable,
                *args, **kwargs) -> Any:
        start = time.time()
        try:
            result = fn(*args, **kwargs)
            self.record(stage, time.time() - start)
            return result
        except Exception as e:
            self.record(stage, time.time() - start, metadata=str(e)[:40])
            raise

    def analyze(self) -> LatencyReport:
        if not self._samples:
            return LatencyReport(
                total_samples=0, stage_stats=[], total_time_sec=0.0,
                bottleneck=None,
                recommendations=["No latency data collected"],
            )

        by_stage: Dict[PipelineStage, List[float]] = {}
        for s in self._samples:
            if s.stage not in by_stage:
                by_stage[s.stage] = []
            by_stage[s.stage].append(s.duration_sec)

        stage_stats: List[StageStats] = []
        for stage, durations in by_stage.items():
            sorted_d = sorted(durations)
            stage_stats.append(StageStats(
                stage=stage,
                samples=len(durations),
                min_sec=min(durations),
                max_sec=max(durations),
                avg_sec=statistics.mean(durations),
                median_sec=statistics.median(durations),
                p95_sec=sorted_d[int(len(sorted_d) * 0.95)] if len(sorted_d) > 1 else max(durations),
                total_sec=sum(durations),
            ))

        stage_stats.sort(key=lambda s: -s.avg_sec)
        bottleneck = stage_stats[0].stage.value if stage_stats else None

        total_time = sum(s.total_sec for s in stage_stats)

        recommendations: List[str] = []
        if stage_stats:
            slowest = stage_stats[0]
            if slowest.avg_sec > 5.0:
                recommendations.append(f"Optimize {slowest.stage.value}: {slowest.avg_sec:.1f}s avg")
            if slowest.p95_sec > slowest.avg_sec * 2:
                recommendations.append(f"High variance in {slowest.stage.value} "
                                       f"(p95={slowest.p95_sec:.1f}s vs avg={slowest.avg_sec:.1f}s)")
        inference = [s for s in stage_stats if s.stage == PipelineStage.INFERENCE]
        if inference and inference[0].avg_sec > 10:
            recommendations.append("Consider smaller model or quantization to reduce inference time")
        load = [s for s in stage_stats if s.stage == PipelineStage.MODEL_LOAD]
        if load and load[0].avg_sec > 5:
            recommendations.append("Keep model loaded in memory to avoid reload latency")
        if not recommendations:
            recommendations.append("Latency within acceptable parameters")

        return LatencyReport(
            total_samples=len(self._samples),
            stage_stats=stage_stats,
            total_time_sec=total_time,
            bottleneck=bottleneck,
            recommendations=recommendations,
        )
