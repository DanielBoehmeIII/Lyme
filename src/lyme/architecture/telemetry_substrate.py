"""Shared telemetry substrate: the fusion layer between product and research.

Every telemetry event is dual-use:
  - Product: debugging, observability, UX improvement
  - Research: cognition analysis, failure study, scaling law discovery
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import uuid
import json


class TelemetryConsent(Enum):
    PRODUCT_ONLY = "product_only"
    RESEARCH_ONLY = "research_only"
    DUAL_USE = "dual_use"
    ANONYMIZED_RESEARCH = "anonymized_research"


class DataCategory(Enum):
    COMMAND_USAGE = "command_usage"
    MODEL_INTERACTION = "model_interaction"
    TOOL_CALL = "tool_call"
    FILE_OPERATION = "file_operation"
    DECISION_POINT = "decision_point"
    ERROR_EVENT = "error_event"
    PERFORMANCE_METRIC = "performance_metric"
    MEMORY_ACCESS = "memory_access"
    BENCHMARK_RESULT = "benchmark_result"
    USER_FEEDBACK = "user_feedback"


@dataclass
class TelemetryRecord:
    id: str
    timestamp: float
    source: str
    category: DataCategory
    consent: TelemetryConsent
    payload: dict
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    experiment_id: Optional[str] = None
    privacy_sanitized: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "category": self.category.value,
            "consent": self.consent.value,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "experiment_id": self.experiment_id,
            "privacy_sanitized": self.privacy_sanitized,
        }


class TelemetrySink:
    def __init__(self, name: str, consent_filter: Optional[List[TelemetryConsent]] = None):
        self.name = name
        self.consent_filter = consent_filter or list(TelemetryConsent)
        self.records: List[TelemetryRecord] = []

    def accept(self, record: TelemetryRecord) -> bool:
        return record.consent in self.consent_filter

    def ingest(self, record: TelemetryRecord):
        if self.accept(record):
            self.records.append(record)

    def flush(self) -> List[TelemetryRecord]:
        batch = self.records
        self.records = []
        return batch

    def query(self, category: Optional[DataCategory] = None,
              source: Optional[str] = None,
              min_timestamp: Optional[float] = None) -> List[TelemetryRecord]:
        results = self.records
        if category:
            results = [r for r in results if r.category == category]
        if source:
            results = [r for r in results if r.source == source]
        if min_timestamp:
            results = [r for r in results if r.timestamp >= min_timestamp]
        return results


@dataclass
class TelemetrySource:
    name: str
    module_path: str
    default_consent: TelemetryConsent = TelemetryConsent.DUAL_USE
    enabled: bool = True


class TelemetrySubstrate:
    """Central telemetry hub that routes records to sinks based on consent."""

    def __init__(self):
        self.sinks: Dict[str, TelemetrySink] = {}
        self.sources: Dict[str, TelemetrySource] = {}
        self._buffer: List[TelemetryRecord] = []
        self._transformers: List[Callable] = []

    def register_sink(self, sink: TelemetrySink):
        self.sinks[sink.name] = sink

    def register_source(self, source: TelemetrySource):
        self.sources[source.name] = source

    def add_transformer(self, transformer: Callable[[TelemetryRecord], TelemetryRecord]):
        self._transformers.append(transformer)

    def emit(self,
             source: str,
             category: DataCategory,
             payload: dict,
             consent: Optional[TelemetryConsent] = None,
             trace_id: Optional[str] = None,
             span_id: Optional[str] = None,
             experiment_id: Optional[str] = None) -> TelemetryRecord:

        src = self.sources.get(source)
        effective_consent = consent or (src.default_consent if src else TelemetryConsent.DUAL_USE)

        record = TelemetryRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).timestamp(),
            source=source,
            category=category,
            consent=effective_consent,
            payload=payload,
            trace_id=trace_id,
            span_id=span_id,
            experiment_id=experiment_id,
        )

        for transformer in self._transformers:
            record = transformer(record)

        self._buffer.append(record)

        for sink in self.sinks.values():
            sink.ingest(record)

        return record

    def flush(self) -> Dict[str, List[TelemetryRecord]]:
        result = {}
        for name, sink in self.sinks.items():
            result[name] = sink.flush()
        batch = self._buffer
        self._buffer = []
        return result

    def get_stats(self) -> dict:
        return {
            "sinks": len(self.sinks),
            "sources": len(self.sources),
            "buffered": len(self._buffer),
            "transformers": len(self._transformers),
        }


_default_substrate: Optional[TelemetrySubstrate] = None


def get_telemetry_substrate() -> TelemetrySubstrate:
    global _default_substrate
    if _default_substrate is None:
        _default_substrate = TelemetrySubstrate()
    return _default_substrate
