"""LymePlugin — base class for all Lyme plugins."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PluginType(Enum):
    AGENT = "agent"
    TOOL = "tool"
    WORKFLOW = "workflow"
    MODEL_PACK = "model_pack"
    UI_THEME = "ui_theme"


@dataclass
class PluginManifest:
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.TOOL
    requires_lyme: str = ">=0.8.0"
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "type": self.plugin_type.value,
            "entry_point": self.entry_point,
        }


class LymePlugin:
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self._hooks: Dict[str, Callable] = {}

    def on_load(self) -> None: ...
    def on_unload(self) -> None: ...
    def on_task(self, task: str) -> Optional[str]: return None

    def register_hook(self, event: str, handler: Callable) -> None:
        self._hooks[event] = handler

    def get_info(self) -> Dict[str, Any]:
        return self.manifest.to_dict()
