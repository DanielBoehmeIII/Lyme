"""Batching — batch inference support for multiple prompts."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BatchRequest:
    id: str
    prompt: str
    max_tokens: int = 2048
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    id: str
    text: str
    tokens: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tokens": self.tokens,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
        }


@dataclass
class BatchStats:
    total_requests: int = 0
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    errors: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_duration_ms / max(self.total_requests, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "total_tokens": self.total_tokens,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "errors": self.errors,
        }


InferenceFn = Callable[[str, int, float], str]


class BatchProcessor:
    def __init__(self, infer: InferenceFn, max_concurrent: int = 4):
        self.infer = infer
        self.max_concurrent = max_concurrent

    def process(self, requests: List[BatchRequest]) -> List[BatchResult]:
        results: List[BatchResult] = []
        for req in requests:
            start = time.time()
            try:
                text = self.infer(req.prompt, req.max_tokens, req.temperature)
                duration = (time.time() - start) * 1000
                results.append(BatchResult(
                    id=req.id, text=text,
                    tokens=len(text.split()),
                    duration_ms=duration,
                ))
            except Exception as e:
                results.append(BatchResult(
                    id=req.id, text="", error=str(e),
                ))
        return results

    def process_with_stats(self, requests: List[BatchRequest]) -> tuple[List[BatchResult], BatchStats]:
        results = self.process(requests)
        stats = BatchStats(
            total_requests=len(requests),
            total_duration_ms=sum(r.duration_ms for r in results),
            total_tokens=sum(r.tokens for r in results),
            errors=sum(1 for r in results if r.error),
        )
        if stats.total_duration_ms > 0:
            stats.tokens_per_second = stats.total_tokens / (stats.total_duration_ms / 1000)
        return results, stats


class ParallelBatchProcessor(BatchProcessor):
    def process(self, requests: List[BatchRequest]) -> List[BatchResult]:
        import concurrent.futures
        results_map: Dict[str, BatchResult] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as ex:
            future_map = {}
            for req in requests:
                future = ex.submit(self._infer_single, req)
                future_map[future] = req.id
            for future in concurrent.futures.as_completed(future_map):
                req_id = future_map[future]
                results_map[req_id] = future.result()
        return [results_map[r.id] for r in requests]

    def _infer_single(self, req: BatchRequest) -> BatchResult:
        start = time.time()
        try:
            text = self.infer(req.prompt, req.max_tokens, req.temperature)
            duration = (time.time() - start) * 1000
            return BatchResult(id=req.id, text=text, tokens=len(text.split()), duration_ms=duration)
        except Exception as e:
            return BatchResult(id=req.id, text="", error=str(e))
