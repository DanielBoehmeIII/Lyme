"""Core — Lyme architecture interfaces and base abstractions."""
from .plugin import Plugin, PluginRegistry, PluginSpec
from .layer import (
    ArchitectureLayer, ArchitectureLayers,
    ORCHESTRATION_LAYER, INFERENCE_LAYER, PLANNING_LAYER,
    REPO_MEMORY_LAYER, VALIDATION_LAYER, EXECUTION_LAYER,
    TRAINING_LAYER, UI_LAYER,
)
from .interfaces import (
    LymeComponent, Configurable, Runnable, Stoppable,
    HasMetrics, HasStatus, ComponentStatus,
    Task, TaskResult, TaskStatus,
    AgentID, RunID, TraceID,
)
from .events import EventBus, Event, EventHandler, SystemEventType

__all__ = [
    "Plugin", "PluginRegistry", "PluginSpec",
    "ArchitectureLayer", "ArchitectureLayers",
    "ORCHESTRATION_LAYER", "INFERENCE_LAYER", "PLANNING_LAYER",
    "REPO_MEMORY_LAYER", "VALIDATION_LAYER", "EXECUTION_LAYER",
    "TRAINING_LAYER", "UI_LAYER",
    "LymeComponent", "Configurable", "Runnable", "Stoppable",
    "HasMetrics", "HasStatus", "ComponentStatus",
    "Task", "TaskResult", "TaskStatus",
    "AgentID", "RunID", "TraceID",
    "EventBus", "Event", "EventHandler", "SystemEventType",
]
