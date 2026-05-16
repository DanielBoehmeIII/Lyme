import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from collections import defaultdict
import statistics


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict = field(default_factory=dict)
    trace_id: str = ""
    span_id: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }


class MetricsStore:
    def __init__(self):
        self._points: List[MetricPoint] = []
        self._aggregators: Dict[str, Callable] = {}

    def record(self, name: str, value: float, tags: dict = None,
               trace_id: str = "", span_id: str = ""):
        point = MetricPoint(
            name=name, value=value,
            tags=tags or {},
            trace_id=trace_id,
            span_id=span_id,
        )
        self._points.append(point)
        return point

    def get_series(self, name: str, tags: dict = None) -> List[MetricPoint]:
        result = [p for p in self._points if p.name == name]
        if tags:
            result = [p for p in result if all(p.tags.get(k) == v for k, v in tags.items())]
        return sorted(result, key=lambda p: p.timestamp)

    def aggregate(self, name: str, operation: str = "mean") -> float:
        series = self.get_series(name)
        if not series:
            return 0.0
        values = [p.value for p in series]
        if operation == "mean":
            return statistics.mean(values)
        elif operation == "median":
            return statistics.median(values)
        elif operation == "min":
            return min(values)
        elif operation == "max":
            return max(values)
        elif operation == "p95":
            return sorted(values)[int(len(values) * 0.95)]
        elif operation == "sum":
            return sum(values)
        elif operation == "count":
            return len(values)
        return statistics.mean(values)

    def summarize(self, name: str) -> dict:
        series = self.get_series(name)
        if not series:
            return {"name": name, "count": 0}
        values = [p.value for p in series]
        return {
            "name": name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": sorted(values)[int(len(values) * 0.95)],
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    def all_metric_names(self) -> List[str]:
        return list(set(p.name for p in self._points))

    def clear(self):
        self._points.clear()

    def __len__(self):
        return len(self._points)
