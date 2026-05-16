from __future__ import annotations

import json
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    EventSeverity,
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
    StackFrame,
    TraceSpan,
)


IngestSource = Callable[[], List[RuntimeTraceEvent]]
TransformFn = Callable[[List[RuntimeTraceEvent]], List[RuntimeTraceEvent]]
SinkFn = Callable[[RuntimeTrace], None]


class LogParser:
    @staticmethod
    def parse_line(line: str, source: str = "") -> Optional[RuntimeTraceEvent]:
        patterns = [
            (r"ERROR\s+(.+?):(\d+).*?(.+)", EventSeverity.ERROR),
            (r"WARNING\s+(.+?):(\d+).*?(.+)", EventSeverity.WARNING),
            (r"INFO\s+(.+?):(\d+).*?(.+)", EventSeverity.INFO),
            (r"DEBUG\s+(.+?):(\d+).*?(.+)", EventSeverity.DEBUG),
            (r"\[error\]\s*(.+)", EventSeverity.ERROR),
            (r"\[warn\]\s*(.+)", EventSeverity.WARNING),
            (r"Traceback.*", EventSeverity.ERROR),
            (r"^\s*File\s+\"(.+?)\",\s*line\s+(\d+).*", EventSeverity.ERROR),
        ]
        for pattern, severity in patterns:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                return RuntimeTraceEvent(
                    event_type=RuntimeEventType.LOG,
                    severity=severity,
                    source=source,
                    metadata={"raw": line, "match": m.groups()},
                )
        return None

    @staticmethod
    def parse_file(path: str, source: str = "") -> List[RuntimeTraceEvent]:
        events = []
        try:
            with open(path) as f:
                for line in f:
                    event = LogParser.parse_line(line.rstrip(), source or path)
                    if event:
                        events.append(event)
        except (IOError, OSError):
            pass
        return events


class StackTraceParser:
    @staticmethod
    def parse(text: str, source: str = "") -> Optional[RuntimeTraceEvent]:
        frames = []
        lines = text.strip().split("\n")
        for line in lines:
            m = re.search(r'File\s+"([^"]+)",\s*line\s+(\d+)(?:,\s*in\s+(\w+))?', line)
            if m:
                frames.append(StackFrame(
                    file=m.group(1),
                    line=int(m.group(2)),
                    function=m.group(3) or "",
                ))
            exc_m = re.search(r"^(\w+(?:\.\w+)*)\s*:\s*(.+)", line)
            if exc_m and frames:
                return RuntimeTraceEvent(
                    event_type=RuntimeEventType.STACK_TRACE,
                    severity=EventSeverity.ERROR,
                    source=source,
                    stack_frames=frames,
                    metadata={"exception_type": exc_m.group(1), "message": exc_m.group(2), "raw": text},
                )
        if not frames:
            return None
        exc_type = "Exception"
        exc_msg = text.split("\n")[-1] if text.split("\n") else ""
        return RuntimeTraceEvent(
            event_type=RuntimeEventType.STACK_TRACE,
            severity=EventSeverity.ERROR,
            source=source,
            stack_frames=frames,
            metadata={"exception_type": exc_type, "message": exc_msg, "raw": text},
        )


class IngestionPipeline:
    def __init__(self):
        self._sources: List[IngestSource] = []
        self._transforms: List[TransformFn] = []
        self._sinks: List[SinkFn] = []
        self._active_traces: Dict[str, RuntimeTrace] = {}

    def add_source(self, source: IngestSource):
        self._sources.append(source)

    def add_transform(self, transform: TransformFn):
        self._transforms.append(transform)

    def add_sink(self, sink: SinkFn):
        self._sinks.append(sink)

    def create_trace(self, name: str = "", application: str = "",
                     environment: str = "", version: str = "",
                     host: str = "", metadata: dict = None) -> RuntimeTrace:
        trace = RuntimeTrace(
            name=name,
            application=application,
            environment=environment,
            version=version,
            host=host,
            metadata=metadata or {},
        )
        self._active_traces[trace.trace_id] = trace
        return trace

    def ingest_events(self, trace: RuntimeTrace, events: List[RuntimeTraceEvent]):
        for event in events:
            trace.add_event(event)

    def ingest_from_sources(self, trace: RuntimeTrace):
        for source in self._sources:
            events = source()
            self.ingest_events(trace, events)

    def process(self, trace: RuntimeTrace) -> RuntimeTrace:
        for transform in self._transforms:
            trace.events = transform(trace.events)
        for sink in self._sinks:
            sink(trace)
        return trace

    def run_pipeline(self, trace: Optional[RuntimeTrace] = None) -> RuntimeTrace:
        trace = trace or self.create_trace()
        self.ingest_from_sources(trace)
        return self.process(trace)


class FileWatcherSource:
    def __init__(self, log_dir: str, pattern: str = "*.log", source_name: str = ""):
        self.log_dir = Path(log_dir)
        self.pattern = pattern
        self.source_name = source_name or str(log_dir)
        self._seen_files: Set[str] = set()

    def __call__(self) -> List[RuntimeTraceEvent]:
        events = []
        if not self.log_dir.exists():
            return events
        for path in self.log_dir.glob(self.pattern):
            if str(path) not in self._seen_files:
                self._seen_files.add(str(path))
                parsed = LogParser.parse_file(str(path), source=self.source_name)
                events.extend(parsed)
        return events


class JSONTraceSource:
    def __init__(self, trace_dir: str, pattern: str = "*.json"):  
        self.trace_dir = Path(trace_dir)
        self.pattern = pattern

    def __call__(self) -> List[RuntimeTraceEvent]:
        events = []
        if not self.trace_dir.exists():
            return events
        for path in self.trace_dir.glob(self.pattern):
            try:
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        events.append(RuntimeTraceEvent.from_dict(item))
                elif isinstance(data, dict):
                    events.append(RuntimeTraceEvent.from_dict(data))
            except (json.JSONDecodeError, IOError):
                pass
        return events


class MetricsConverter:
    @staticmethod
    def metric_to_event(name: str, value: float, tags: dict = None,
                        timestamp: float = 0) -> RuntimeTraceEvent:
        return RuntimeTraceEvent(
            event_type=RuntimeEventType.METRIC,
            timestamp=timestamp or time.time(),
            metadata={
                "metric_name": name,
                "metric_value": value,
                "tags": tags or {},
            },
        )


class DeduplicateTransform:
    def __init__(self, window_ms: float = 100):
        self.window_ms = window_ms

    def __call__(self, events: List[RuntimeTraceEvent]) -> List[RuntimeTraceEvent]:
        seen: Dict[Tuple, float] = {}
        result = []
        for e in events:
            key = (e.event_type.value, e.source_file, e.source_line,
                   str(e.metadata.get("metric_name", "")),
                   str(e.metadata.get("exception_type", "")))
            last_ts = seen.get(key, 0)
            if (e.timestamp - last_ts) * 1000 > self.window_ms:
                seen[key] = e.timestamp
                result.append(e)
        return result


class TagTransform:
    def __init__(self, tags: Dict[str, str]):
        self.tags = tags

    def __call__(self, events: List[RuntimeTraceEvent]) -> List[RuntimeTraceEvent]:
        for e in events:
            for k, v in self.tags.items():
                if k == "subsystem":
                    e.subsystem = v
                elif k == "service":
                    e.service = v
                elif k == "environment":
                    e.environment = v
                else:
                    e.tags.append(f"{k}:{v}")
        return events


class SeverityFilter:
    def __init__(self, min_severity: EventSeverity = EventSeverity.INFO):
        self.min_severity = min_severity
        self._order = {s: i for i, s in enumerate(EventSeverity)}

    def __call__(self, events: List[RuntimeTraceEvent]) -> List[RuntimeTraceEvent]:
        min_val = self._order.get(self.min_severity, 0)
        return [e for e in events if self._order.get(e.severity, 0) >= min_val]


class BatchProcessor:
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    def process_events(self, trace: RuntimeTrace) -> List[RuntimeTrace]:
        batches = []
        for i in range(0, len(trace.events), self.batch_size):
            batch = trace.events[i:i + self.batch_size]
            batch_trace = RuntimeTrace(
                trace_id=f"{trace.trace_id}_batch_{i // self.batch_size}",
                name=f"{trace.name}_batch_{i // self.batch_size}",
                application=trace.application,
                environment=trace.environment,
            )
            for e in batch:
                batch_trace.add_event(e)
            batches.append(batch_trace)
        return batches


class StreamProcessor:
    def __init__(self, pipeline: IngestionPipeline, buffer_size: int = 1000):
        self.pipeline = pipeline
        self.buffer_size = buffer_size
        self._buffer: List[RuntimeTraceEvent] = []

    def push(self, event: RuntimeTraceEvent):
        self._buffer.append(event)
        if len(self._buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> Optional[RuntimeTrace]:
        if not self._buffer:
            return None
        trace = self.pipeline.create_trace()
        trace.events = self._buffer
        result = self.pipeline.process(trace)
        self._buffer = []
        return result
