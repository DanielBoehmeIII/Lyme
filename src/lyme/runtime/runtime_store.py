from __future__ import annotations

import gzip
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
    TraceSpan,
)


class RuntimeStore:
    def __init__(self, base_dir: str = "./lyme-output/runtime"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "traces").mkdir(exist_ok=True)
        (self.base_dir / "events").mkdir(exist_ok=True)
        (self.base_dir / "spans").mkdir(exist_ok=True)
        (self.base_dir / "correlations").mkdir(exist_ok=True)
        (self.base_dir / "index").mkdir(exist_ok=True)
        self._trace_index: Dict[str, RuntimeTrace] = {}
        self._event_index: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._load_index()

    def _index_path(self) -> Path:
        return self.base_dir / "index" / "trace_index.json"

    def _type_index_path(self) -> Path:
        return self.base_dir / "index" / "type_index.json"

    def _file_index_path(self) -> Path:
        return self.base_dir / "index" / "file_index.json"

    def _subsystem_index_path(self) -> Path:
        return self.base_dir / "index" / "subsystem_index.json"

    def _trace_path(self, trace_id: str) -> Path:
        return self.base_dir / "traces" / f"{trace_id}.json"

    def _events_path(self, trace_id: str) -> Path:
        return self.base_dir / "events" / f"{trace_id}.json"

    def _spans_path(self, trace_id: str) -> Path:
        return self.base_dir / "spans" / f"{trace_id}.json"

    def _correlation_path(self, trace_id: str) -> Path:
        return self.base_dir / "correlations" / f"{trace_id}.json"

    def _load_index(self):
        idx = self._index_path()
        if idx.exists():
            try:
                with open(idx) as f:
                    trace_ids = json.load(f)
                for tid in trace_ids:
                    trace_data = self._load_trace_file(tid)
                    if trace_data:
                        self._trace_index[tid] = trace_data
            except (json.JSONDecodeError, IOError):
                pass

        fi = self._file_index_path()
        if fi.exists():
            try:
                with open(fi) as f:
                    self._event_index["file"] = defaultdict(list, json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

        si = self._subsystem_index_path()
        if si.exists():
            try:
                with open(si) as f:
                    self._event_index["subsystem"] = defaultdict(list, json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

        ti = self._type_index_path()
        if ti.exists():
            try:
                with open(ti) as f:
                    self._event_index["type"] = defaultdict(list, json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

    def _save_trace_index(self):
        with open(self._index_path(), "w") as f:
            json.dump(list(self._trace_index.keys()), f)

    def _save_file_index(self):
        with open(self._file_index_path(), "w") as f:
            json.dump(dict(self._event_index["file"]), f)

    def _save_subsystem_index(self):
        with open(self._subsystem_index_path(), "w") as f:
            json.dump(dict(self._event_index["subsystem"]), f)

    def _save_type_index(self):
        with open(self._type_index_path(), "w") as f:
            json.dump(dict(self._event_index["type"]), f)

    def save_trace(self, trace: RuntimeTrace, compress: bool = False):
        self._trace_index[trace.trace_id] = trace
        path = self._trace_path(trace.trace_id)
        data = trace.to_dict()
        if compress:
            path = path.with_suffix(".json.gz")
            with gzip.open(path, "wt") as f:
                json.dump(data, f, default=str)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        events_path = self._events_path(trace.trace_id)
        with open(events_path, "w") as f:
            json.dump([e.to_dict() for e in trace.events], f, indent=2, default=str)

        if trace.spans:
            spans_path = self._spans_path(trace.trace_id)
            with open(spans_path, "w") as f:
                json.dump([s.to_dict() for s in trace.spans], f, indent=2, default=str)

        for event in trace.events:
            if event.source_file:
                self._event_index["file"][event.source_file].append(trace.trace_id)
            if event.subsystem:
                self._event_index["subsystem"][event.subsystem].append(trace.trace_id)
            self._event_index["type"][event.event_type.value].append(trace.trace_id)

        self._save_trace_index()
        self._save_file_index()
        self._save_subsystem_index()
        self._save_type_index()

    def _load_trace_file(self, trace_id: str) -> Optional[RuntimeTrace]:
        path = self._trace_path(trace_id)
        if path.exists():
            try:
                with open(path) as f:
                    return RuntimeTrace.from_dict(json.load(f))
            except (json.JSONDecodeError, IOError):
                return None
        gz_path = path.with_suffix(".json.gz")
        if gz_path.exists():
            try:
                with gzip.open(gz_path, "rt") as f:
                    return RuntimeTrace.from_dict(json.load(f))
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def load_trace(self, trace_id: str) -> Optional[RuntimeTrace]:
        trace = self._trace_index.get(trace_id)
        if trace:
            return trace
        return self._load_trace_file(trace_id)

    def load_events(self, trace_id: str) -> List[RuntimeTraceEvent]:
        trace = self.load_trace(trace_id)
        return trace.events if trace else []

    def save_correlation(self, trace_id: str, correlation_data: dict):
        path = self._correlation_path(trace_id)
        with open(path, "w") as f:
            json.dump(correlation_data, f, indent=2, default=str)

    def load_correlation(self, trace_id: str) -> Optional[dict]:
        path = self._correlation_path(trace_id)
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def find_traces_by_file(self, file_path: str) -> List[str]:
        return self._event_index["file"].get(file_path, [])

    def find_traces_by_subsystem(self, subsystem: str) -> List[str]:
        return self._event_index["subsystem"].get(subsystem, [])

    def find_traces_by_type(self, event_type: RuntimeEventType) -> List[str]:
        return self._event_index["type"].get(event_type.value, [])

    def find_traces_by_time_range(self, start: float, end: float) -> List[RuntimeTrace]:
        results = []
        for trace in self._trace_index.values():
            if start <= trace.start_time <= end:
                results.append(trace)
        return results

    def list_traces(self) -> List[Dict[str, Any]]:
        summaries = []
        for trace_id, trace in self._trace_index.items():
            summaries.append({
                "trace_id": trace_id,
                "name": trace.name,
                "application": trace.application,
                "start_time": trace.start_time,
                "duration_ms": trace.duration_ms,
                "status": trace.status,
                "event_count": trace.event_count,
                "error_count": trace.error_count,
            })
        return sorted(summaries, key=lambda s: s["start_time"], reverse=True)

    def delete_trace(self, trace_id: str) -> bool:
        if trace_id in self._trace_index:
            del self._trace_index[trace_id]
        removed = False
        for path in [
            self._trace_path(trace_id),
            self._trace_path(trace_id).with_suffix(".json.gz"),
            self._events_path(trace_id),
            self._spans_path(trace_id),
            self._correlation_path(trace_id),
        ]:
            if path.exists():
                path.unlink()
                removed = True
        for idx in self._event_index.values():
            for key in list(idx.keys()):
                if trace_id in idx[key]:
                    idx[key] = [t for t in idx[key] if t != trace_id]
        self._save_trace_index()
        return removed

    def prune(self, max_age_days: int = 90):
        cutoff = time.time() - max_age_days * 86400
        to_remove = [
            tid for tid, trace in self._trace_index.items()
            if trace.start_time < cutoff
        ]
        for tid in to_remove:
            self.delete_trace(tid)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_traces": len(self._trace_index),
            "total_events": sum(t.event_count for t in self._trace_index.values()),
            "total_errors": sum(t.error_count for t in self._trace_index.values()),
            "traces_by_type": {
                t.value: len(self._event_index["type"].get(t.value, []))
                for t in RuntimeEventType
            },
            "traces_by_subsystem": {
                sub: len(ids) for sub, ids in self._event_index["subsystem"].items()
            },
            "storage_path": str(self.base_dir),
        }
