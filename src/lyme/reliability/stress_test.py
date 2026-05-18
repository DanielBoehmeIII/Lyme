"""StressTestRunner — systematic stress testing for agent operations."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class StressConfig:
    iterations: int = 10
    concurrency: int = 1
    timeout_s: int = 30
    ramp_up: bool = True
    name: str = "default"


@dataclass
class StressReport:
    name: str = ""
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    total_duration_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.total_calls, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "successes": self.successes,
            "failures": self.failures,
            "timeouts": self.timeouts,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
        }


class StressTestRunner:
    def __init__(self, config: StressConfig = None):
        self.config = config or StressConfig()
        self._latencies: List[float] = []

    def run(self, fn: Callable, *args, **kwargs) -> StressReport:
        report = StressReport(name=self.config.name)
        start = time.time()

        for i in range(self.config.iterations):
            if self.config.ramp_up:
                time.sleep(min(i * 0.1, 2.0))

            op_start = time.time()
            try:
                fn(*args, **kwargs)
                report.successes += 1
                self._latencies.append((time.time() - op_start) * 1000)
            except TimeoutError:
                report.timeouts += 1
            except Exception:
                report.failures += 1

        report.total_calls = self.config.iterations
        report.total_duration_ms = (time.time() - start) * 1000
        report.avg_latency_ms = sum(self._latencies) / max(len(self._latencies), 1)
        if self._latencies:
            sorted_lat = sorted(self._latencies)
            report.p95_latency_ms = sorted_lat[int(len(sorted_lat) * 0.95)]
        return report
