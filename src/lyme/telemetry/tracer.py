import time
import uuid
import threading
import contextlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from .span import Span


class TraceContext:
    _local = threading.local()

    def __init__(self, trace_id: str = ""):
        self.trace_id = trace_id or uuid.uuid4().hex[:16]
        self.spans: List[Span] = []
        self._stack: List[str] = []
        self._local.trace_id = self.trace_id
        self.start_time = time.time()
        self.metadata: dict = {}

    @classmethod
    def current(cls) -> Optional["TraceContext"]:
        return getattr(cls._local, "current", None)

    @classmethod
    def current_trace_id(cls) -> Optional[str]:
        ctx = cls.current()
        return ctx.trace_id if ctx else None

    def push_span_id(self, span_id: str):
        self._stack.append(span_id)

    def pop_span_id(self) -> Optional[str]:
        return self._stack.pop() if self._stack else None

    def parent_span_id(self) -> Optional[str]:
        return self._stack[-1] if self._stack else None


class Tracer:
    def __init__(self):
        self._contexts: Dict[str, TraceContext] = {}

    @contextlib.contextmanager
    def trace(self, name: str, category: str = "", metadata: dict = None):
        ctx = TraceContext()
        self._contexts[ctx.trace_id] = ctx
        TraceContext._local.current = ctx
        try:
            with self.span(name, category=category, metadata=metadata) as root:
                yield ctx
        finally:
            TraceContext._local.current = None

    @contextlib.contextmanager
    def span(self, name: str, category: str = "", metadata: dict = None, tags: list = None):
        ctx = TraceContext.current()
        if ctx is None:
            ctx = TraceContext()
            self._contexts[ctx.trace_id] = ctx
            TraceContext._local.current = ctx

        span = Span(
            trace_id=ctx.trace_id,
            parent_id=ctx.parent_span_id(),
            name=name,
            category=category,
            metadata=metadata or {},
            tags=tags or [],
        )
        ctx.spans.append(span)
        ctx.push_span_id(span.id)
        try:
            yield span
            span.finish("success")
        except Exception as e:
            span.finish("error", error=str(e))
            raise
        finally:
            ctx.pop_span_id()

    def get_context(self, trace_id: str) -> Optional[TraceContext]:
        return self._contexts.get(trace_id)

    def get_spans(self, trace_id: str) -> List[Span]:
        ctx = self._contexts.get(trace_id)
        return ctx.spans if ctx else []

    def build_tree(self, trace_id: str) -> List[dict]:
        spans = self.get_spans(trace_id)
        span_map = {s.id: s.to_dict() for s in spans}
        tree = []
        for s in spans:
            node = span_map[s.id]
            if s.parent_id:
                parent = span_map.get(s.parent_id)
                if parent:
                    parent.setdefault("children", []).append(node)
            else:
                tree.append(node)
        return tree

    def clear(self):
        self._contexts.clear()

    @property
    def all_traces(self) -> List[str]:
        return list(self._contexts.keys())
