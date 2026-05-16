"""Experiment API: the bridge between product actions and research experiments.

Every product action can optionally trigger an experiment hook.
Every experiment result can optionally improve product behavior.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import uuid


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ExperimentHookType(Enum):
    PRE_ACTION = "pre_action"
    POST_ACTION = "post_action"
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    ON_DECISION = "on_decision"
    ON_ERROR = "on_error"
    ON_MEMORY_ACCESS = "on_memory_access"
    ON_FILE_EDIT = "on_file_edit"
    ON_SESSION_END = "on_session_end"


@dataclass
class ExperimentDefinition:
    name: str
    description: str
    hook_type: ExperimentHookType
    version: str = "0.1.0"
    tags: List[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "hook_type": self.hook_type.value,
            "version": self.version,
            "tags": self.tags,
            "config": self.config,
        }


@dataclass
class ExperimentContext:
    experiment_id: str
    definition: ExperimentDefinition
    trace_id: Optional[str]
    input_data: dict
    start_time: float
    status: ExperimentStatus = ExperimentStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "definition": self.definition.to_dict(),
            "trace_id": self.trace_id,
            "input_data": self.input_data,
            "start_time": self.start_time,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class ExperimentResult:
    experiment_id: str
    success: bool
    metrics: dict
    artifacts: List[str]
    summary: str
    duration_ms: float
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "success": self.success,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "summary": self.summary,
            "duration_ms": self.duration_ms,
            "insights": self.insights,
        }


ExperimentHandler = Callable[[ExperimentContext], ExperimentResult]


@dataclass
class ExperimentHook:
    definition: ExperimentDefinition
    handler: ExperimentHandler
    enabled: bool = True
    run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "definition": self.definition.to_dict(),
            "enabled": self.enabled,
            "run_count": self.run_count,
        }


class ExperimentAPI:
    """Public API for registering and running experiments."""

    def __init__(self):
        self._hooks: Dict[str, ExperimentHook] = {}
        self._results: Dict[str, ExperimentResult] = {}
        self._contexts: Dict[str, ExperimentContext] = {}

    def register_experiment(self, definition: ExperimentDefinition,
                            handler: ExperimentHandler) -> str:
        hook = ExperimentHook(definition=definition, handler=handler)
        self._hooks[definition.name] = hook
        return definition.name

    def unregister_experiment(self, name: str):
        self._hooks.pop(name, None)

    def get_hooks(self, hook_type: ExperimentHookType) -> List[ExperimentHook]:
        return [h for h in self._hooks.values()
                if h.definition.hook_type == hook_type and h.enabled]

    def execute_hooks(self, hook_type: ExperimentHookType,
                      input_data: dict,
                      trace_id: Optional[str] = None) -> List[ExperimentResult]:
        results = []
        for hook in self.get_hooks(hook_type):
            context = ExperimentContext(
                experiment_id=str(uuid.uuid4()),
                definition=hook.definition,
                trace_id=trace_id,
                input_data=input_data,
                start_time=datetime.now(timezone.utc).timestamp(),
            )
            self._contexts[context.experiment_id] = context
            context.status = ExperimentStatus.RUNNING
            hook.run_count += 1

            try:
                result = hook.handler(context)
                context.status = ExperimentStatus.COMPLETED
                context.result = result.to_dict()
            except Exception as e:
                context.status = ExperimentStatus.FAILED
                context.error = str(e)
                result = ExperimentResult(
                    experiment_id=context.experiment_id,
                    success=False,
                    metrics={"error": str(e)},
                    artifacts=[],
                    summary=f"Experiment {hook.definition.name} failed: {e}",
                    duration_ms=0,
                )

            self._results[result.experiment_id] = result
            results.append(result)

        return results

    def get_result(self, experiment_id: str) -> Optional[ExperimentResult]:
        return self._results.get(experiment_id)

    def get_context(self, experiment_id: str) -> Optional[ExperimentContext]:
        return self._contexts.get(experiment_id)

    def list_experiments(self) -> List[dict]:
        return [h.to_dict() for h in self._hooks.values()]

    def list_results(self, limit: int = 50) -> List[dict]:
        sorted_ids = sorted(self._results.keys(),
                           key=lambda x: self._results[x].duration_ms,
                           reverse=True)
        return [self._results[eid].to_dict() for eid in sorted_ids[:limit]]

    def to_dict(self) -> dict:
        return {
            "registered_experiments": len(self._hooks),
            "completed_results": len(self._results),
            "experiments": [h.to_dict() for h in self._hooks.values()],
        }


_default_api: Optional[ExperimentAPI] = None


def get_experiment_api() -> ExperimentAPI:
    global _default_api
    if _default_api is None:
        _default_api = ExperimentAPI()
    return _default_api
