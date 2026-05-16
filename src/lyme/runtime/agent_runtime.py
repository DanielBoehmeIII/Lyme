import os
import time
import uuid
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from pathlib import Path

from ..models import ModelAdapter
from ..memory import MemoryStore, MemoryEntry
from ..telemetry import Tracer, EventLog, EventType, MetricsStore
from ..benchmark import AgentRunner, AgentResult, AgentRunnerStatus
from ..replay import DeterministicReplayer, ReplaySession
from ..tools import AgentWrapper
from ..config import Settings


class RuntimeState(str, Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    MODEL_LOADING = "model_loading"
    MODEL_READY = "model_ready"
    PROCESSING = "processing"
    DEGRADED = "degraded"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class RuntimeConfig:
    model_name: str = "default"
    work_dir: str = "./lyme-work"
    vram_limit_mb: int = 8192
    cpu_only: bool = False
    model_swap_enabled: bool = False
    replay_mode: str = "off"
    privacy_first: bool = True


@dataclass
class TaskContext:
    task_id: str = ""
    state: str = "pending"
    history: List[dict] = field(default_factory=list)
    event_log: List[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    start_time: float = 0.0
    end_time: Optional[float] = None


class AgentRuntime:
    def __init__(self, config: Optional[RuntimeConfig] = None, settings: Optional[Settings] = None):
        self.config = config or RuntimeConfig()
        self.settings = settings or Settings()
        self.state = RuntimeState.UNINITIALIZED
        self.model: Optional[ModelAdapter] = None
        self.memory: Optional[MemoryStore] = None
        self.tracer = Tracer()
        self.event_log = EventLog()
        self.metrics = MetricsStore()
        self.replayer = DeterministicReplayer()
        self.agent_wrapper = AgentWrapper(tracer=self.tracer, event_log=self.event_log)
        self._lock = threading.Lock()
        self._vram_usage_mb: float = 0.0
        self._swap_lock = threading.Lock()
        self._replay_hooks: List[Callable] = []
        self._shutdown_event = threading.Event()
        self._logger = logging.getLogger("lyme.runtime")
        self._current_task: Optional[TaskContext] = None

    def initialize(self, work_dir: Optional[str] = None) -> None:
        if self.state != RuntimeState.UNINITIALIZED:
            raise RuntimeError(f"Cannot initialize from state {self.state.value}")

        with self._lock:
            if work_dir:
                self.config.work_dir = work_dir
            Path(self.config.work_dir).mkdir(parents=True, exist_ok=True)
            self.memory = MemoryStore()
            self.state = RuntimeState.INITIALIZED
            self.event_log.emit(
                EventType.SYSTEM,
                {"description": "Runtime initialized", "work_dir": self.config.work_dir,
                 "vram_limit_mb": self.config.vram_limit_mb},
                source="agent_runtime",
            )
            self.metrics.record("runtime.initialized", 1.0)

    def load_model(self) -> None:
        if self.state not in (RuntimeState.INITIALIZED, RuntimeState.DEGRADED):
            raise RuntimeError(f"Cannot load model from state {self.state.value}")

        with self._lock:
            self.state = RuntimeState.MODEL_LOADING
            self.event_log.emit(
                EventType.SYSTEM,
                {"description": f"Loading model: {self.config.model_name}",
                 "cpu_only": self.config.cpu_only},
                source="agent_runtime",
            )

            try:
                backend_kwargs: Dict[str, Any] = {}
                if self.config.cpu_only:
                    backend_kwargs["device"] = "cpu"
                self.model = ModelAdapter(
                    model_name=self.config.model_name,
                    **backend_kwargs,
                )
                self._vram_usage_mb = self._estimate_vram()
                self.state = RuntimeState.MODEL_READY
                self.metrics.record("model.load_time_ms", 0.0)
                self.metrics.record("model.vram_mb", self._vram_usage_mb)
                self.event_log.emit(
                    EventType.SYSTEM,
                    {"description": "Model loaded successfully",
                     "vram_mb": self._vram_usage_mb},
                    source="agent_runtime",
                )
            except Exception as e:
                self.state = RuntimeState.ERROR
                self.event_log.emit(
                    EventType.ERROR,
                    {"description": f"Model loading failed: {e}"},
                    severity="error", source="agent_runtime",
                )
                self.metrics.record("model.load_error", 1.0)
                raise

    def unload_model(self) -> None:
        with self._swap_lock:
            if self.model is not None:
                self.model = None
                self._vram_usage_mb = 0.0
                if self.state == RuntimeState.MODEL_READY:
                    self.state = RuntimeState.INITIALIZED
                self.event_log.emit(
                    EventType.SYSTEM,
                    {"description": "Model unloaded"},
                    source="agent_runtime",
                )
                self.metrics.record("model.unloaded", 1.0)

    def swap_model(self, model_name: str) -> None:
        if not self.config.model_swap_enabled:
            raise RuntimeError("Model swapping is disabled in config")
        with self._swap_lock:
            self.unload_model()
            self.config.model_name = model_name
            self.load_model()

    def process_task(self, task_input: str, metadata: Optional[dict] = None) -> Dict[str, Any]:
        if self.state == RuntimeState.SHUTDOWN:
            raise RuntimeError("Runtime is shut down")

        self._check_degradation()

        task_id = uuid.uuid4().hex[:12]
        ctx = TaskContext(task_id=task_id, start_time=time.time(), metadata=metadata or {})

        with self._lock:
            self._current_task = ctx
            previous_state = self.state
            self.state = RuntimeState.PROCESSING

        self.event_log.emit(
            EventType.SYSTEM,
            {"description": f"Processing task: {task_id}", "input_preview": task_input[:200]},
            source="agent_runtime",
        )
        self.metrics.record("task.started", 1.0, tags={"task_id": task_id})

        if self.config.replay_mode == "deterministic":
            self._run_replay_hooks("pre_task", task_id, task_input)

        try:
            if self.state == RuntimeState.DEGRADED:
                result = self._process_degraded(task_input, ctx)
            else:
                result = self._process_normal(task_input, ctx)

            ctx.state = "completed"
            self.metrics.record("task.completed", 1.0, tags={"task_id": task_id})
            result["task_id"] = task_id
            result["status"] = "completed"

        except Exception as e:
            ctx.state = "failed"
            self.event_log.emit(
                EventType.ERROR,
                {"description": f"Task failed: {e}", "task_id": task_id},
                severity="error", source="agent_runtime",
            )
            self.metrics.record("task.failed", 1.0, tags={"task_id": task_id})
            result = {"task_id": task_id, "status": "failed", "error": str(e)}

        finally:
            ctx.end_time = time.time()
            ctx.event_log = self.event_log.get_events(trace_id=task_id)
            if hasattr(self.memory, "store"):
                self.memory.store(task_id, ctx)
            self._current_task = None

            with self._lock:
                self.state = previous_state if previous_state != RuntimeState.PROCESSING else RuntimeState.MODEL_READY

            if self.config.replay_mode == "deterministic":
                self._run_replay_hooks("post_task", task_id, result)

            if self._should_swap_out():
                threading.Thread(target=self._delayed_swap, daemon=True).start()

        return result

    def _process_normal(self, task_input: str, ctx: TaskContext) -> Dict[str, Any]:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        with self.tracer.span(f"task:{ctx.task_id}", category="inference"):
            with self.agent_wrapper.wrap_tool_call("model_inference", {"input": task_input},
                                                   lambda: None):
                response = self.model.generate(task_input)

        ctx.history.append({"role": "user", "content": task_input})
        ctx.history.append({"role": "assistant", "content": response})

        return {"output": response, "model": self.config.model_name}

    def _process_degraded(self, task_input: str, ctx: TaskContext) -> Dict[str, Any]:
        self.event_log.emit(
            EventType.SYSTEM,
            {"description": "Processing in degraded mode",
             "vram_mb": self._vram_usage_mb, "limit_mb": self.config.vram_limit_mb},
            source="agent_runtime",
        )
        if self.model is None and self.config.model_swap_enabled:
            self.load_model()
            return self._process_normal(task_input, ctx)

        response = self._lightweight_inference(task_input)
        ctx.history.append({"role": "user", "content": task_input})
        ctx.history.append({"role": "assistant", "content": response})

        return {"output": response, "model": self.config.model_name, "degraded": True}

    def _lightweight_inference(self, task_input: str) -> str:
        return f"[degraded] {task_input[:100]}..."

    def _estimate_vram(self) -> float:
        return float(self.config.vram_limit_mb) * 0.6

    def _check_degradation(self) -> None:
        if self._vram_usage_mb > self.config.vram_limit_mb * 0.9:
            with self._lock:
                if self.state != RuntimeState.DEGRADED:
                    self.state = RuntimeState.DEGRADED
                    self.event_log.emit(
                        EventType.SYSTEM,
                        {"description": "Runtime degraded due to VRAM pressure",
                         "vram_mb": self._vram_usage_mb,
                         "limit_mb": self.config.vram_limit_mb},
                        severity="warning", source="agent_runtime",
                    )
                    self.metrics.record("runtime.degraded", 1.0)

    def _should_swap_out(self) -> bool:
        return (
            self.config.model_swap_enabled
            and self._vram_usage_mb > self.config.vram_limit_mb * 0.85
        )

    def _delayed_swap(self) -> None:
        time.sleep(1)
        with self._swap_lock:
            if self.state == RuntimeState.MODEL_READY and self._should_swap_out():
                self.unload_model()

    def _run_replay_hooks(self, hook_type: str, task_id: str, data: Any) -> None:
        for hook in self._replay_hooks:
            try:
                hook(hook_type, task_id, data)
            except Exception as e:
                self._logger.warning(f"Replay hook failed: {e}")

    def register_replay_hook(self, hook: Callable[[str, str, Any], None]) -> None:
        self._replay_hooks.append(hook)

    def get_current_task(self) -> Optional[TaskContext]:
        return self._current_task

    def get_vram_usage(self) -> float:
        return self._vram_usage_mb

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown_event.set()
            self.unload_model()
            self.state = RuntimeState.SHUTDOWN
            self.event_log.emit(
                EventType.SYSTEM,
                {"description": "Runtime shut down"},
                source="agent_runtime",
            )
            self.metrics.record("runtime.shutdown", 1.0)

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
