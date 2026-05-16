"""Week 89 — Speed as a First-Class Metric.

Measure and profile all latency-critical paths in Lyme Model:
- model load time (cold vs warm)
- first token latency
- tokens/sec
- retrieval latency (per policy type)
- tool overhead
- verification time
- total task time
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import json
import time


@dataclass
class SpeedProfile:
    model_load_time_s: float = 0.0
    first_token_latency_s: float = 0.0
    tokens_per_second: float = 0.0
    retrieval_latency_ms: float = 0.0
    tool_overhead_ms: float = 0.0
    verification_latency_ms: float = 0.0
    patch_critic_latency_ms: float = 0.0
    total_task_time_s: float = 0.0
    cold_start: bool = True
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = ["## Speed Profile", ""]
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        for key, val in asdict(self).items():
            if key == "timestamp":
                continue
            lines.append(f"| {key} | {val} |")
        return "\n".join(lines)


@dataclass
class LatencyReport:
    cold_profile: SpeedProfile = field(default_factory=SpeedProfile)
    warm_profile: SpeedProfile = field(default_factory=SpeedProfile)
    speedup_factor: float = 1.0
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cold": asdict(self.cold_profile),
            "warm": asdict(self.warm_profile),
            "speedup_factor": self.speedup_factor,
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
        }

    def summary(self) -> str:
        lines = [f"# Latency Report", ""]
        lines.append(f"**Cold start:** {self.cold_profile.total_task_time_s:.2f}s")
        lines.append(f"**Warm start:** {self.warm_profile.total_task_time_s:.2f}s")
        lines.append(f"**Speedup:** {self.speedup_factor:.1f}x")
        lines.append("")
        if self.bottlenecks:
            lines.append("## Bottlenecks")
            for b in self.bottlenecks:
                lines.append(f"- {b}")
        if self.recommendations:
            lines.append("## Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)


class SpeedProfiler:
    """Profiles Lyme Model speed across all critical paths."""

    def __init__(self):
        self.reports: List[LatencyReport] = []

    def measure_retrieval_latency(self, policy_fn: Callable, query: str,
                                  samples: int = 3) -> float:
        """Measure average retrieval latency for a policy."""
        times = []
        for _ in range(samples):
            start = time.time()
            policy_fn(query)
            times.append((time.time() - start) * 1000)
        return sum(times) / len(times) if times else 0.0

    def measure_tool_overhead(self, tool_fn: Callable, *args,
                              samples: int = 3) -> float:
        """Measure average tool dispatch overhead in ms."""
        times = []
        for _ in range(samples):
            start = time.time()
            tool_fn(*args)
            times.append((time.time() - start) * 1000)
        return sum(times) / len(times) if times else 0.0

    def measure_verification_latency(self, verifier_fn: Callable,
                                     samples: int = 3) -> float:
        """Measure average verification latency in ms."""
        return self.measure_tool_overhead(verifier_fn, samples=samples)

    def profile_cold(
        self,
        load_fn: Callable[[], Any],
        generate_fn: Callable[[str], Any],
        prompt: str = "def hello():\n    pass",
    ) -> SpeedProfile:
        """Profile cold start (model not loaded)."""
        start = time.time()
        load_fn()
        load_time = time.time() - start

        gen_start = time.time()
        output = generate_fn(prompt)
        gen_time = time.time() - gen_start

        total = time.time() - start
        output_tokens = len(str(output).split())

        return SpeedProfile(
            model_load_time_s=round(load_time, 3),
            first_token_latency_s=round(gen_time, 3),
            tokens_per_second=round(output_tokens / gen_time, 1) if gen_time > 0 else 0.0,
            total_task_time_s=round(total, 3),
            cold_start=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def profile_warm(
        self,
        generate_fn: Callable[[str], Any],
        prompt: str = "def hello():\n    pass",
    ) -> SpeedProfile:
        """Profile warm start (model already loaded)."""
        start = time.time()
        output = generate_fn(prompt)
        gen_time = time.time() - start

        output_tokens = len(str(output).split())

        return SpeedProfile(
            model_load_time_s=0.0,
            first_token_latency_s=round(gen_time, 3),
            tokens_per_second=round(output_tokens / gen_time, 1) if gen_time > 0 else 0.0,
            total_task_time_s=round(gen_time, 3),
            cold_start=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def benchmark(
        self,
        cold_load_fn: Callable[[], Any],
        generate_fn: Callable[[str], Any],
        retrieval_fns: Optional[Dict[str, Callable]] = None,
        tool_fns: Optional[Dict[str, Callable]] = None,
        verifier_fn: Optional[Callable] = None,
        prompt: str = "def hello():\n    pass",
    ) -> LatencyReport:
        """Run a full speed benchmark."""
        cold = self.profile_cold(cold_load_fn, generate_fn, prompt)
        warm = self.profile_warm(generate_fn, prompt)

        bottlenecks = []
        recommendations = []

        if cold.model_load_time_s > 5.0:
            bottlenecks.append(f"Model load time: {cold.model_load_time_s:.1f}s")
            recommendations.append("Keep model loaded between requests (warm pool)")
        if cold.tokens_per_second < 5:
            bottlenecks.append(f"Generation speed: {cold.tokens_per_second:.1f} tok/s")
            recommendations.append("Use smaller model or Q4 quantization")
        if cold.first_token_latency_s > 10.0:
            bottlenecks.append(f"First token latency: {cold.first_token_latency_s:.1f}s")
            recommendations.append("Reduce context size or use prompt caching")

        if retrieval_fns:
            for name, fn in retrieval_fns.items():
                lat = self.measure_retrieval_latency(fn, "test")
                setattr(warm, "retrieval_latency_ms", lat)
                if lat > 500:
                    bottlenecks.append(f"Retrieval ({name}): {lat:.0f}ms")

        if tool_fns:
            for name, fn in tool_fns.items():
                lat = self.measure_tool_overhead(fn)
                if lat > 200:
                    bottlenecks.append(f"Tool ({name}): {lat:.0f}ms")

        if verifier_fn:
            lat = self.measure_verification_latency(verifier_fn)
            setattr(warm, "verification_latency_ms", lat)
            if lat > 300:
                bottlenecks.append(f"Verification: {lat:.0f}ms")

        speedup = (cold.total_task_time_s / warm.total_task_time_s
                   if warm.total_task_time_s > 0 else 1.0)

        report = LatencyReport(
            cold_profile=cold,
            warm_profile=warm,
            speedup_factor=round(speedup, 1),
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )
        self.reports.append(report)
        return report

    def report_all(self) -> List[Dict]:
        return [r.to_dict() for r in self.reports]


def benchmark_all() -> str:
    """Quick benchmark summary suitable for CLI display."""
    profiler = SpeedProfiler()

    def fake_load():
        time.sleep(0.05)

    def fake_generate(p: str) -> str:
        time.sleep(0.1)
        return "def result():\n    return 42"

    report = profiler.benchmark(
        cold_load_fn=fake_load,
        generate_fn=fake_generate,
    )
    return report.summary()
