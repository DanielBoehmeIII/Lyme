"""Plugin system for Lyme: extends product or research capabilities at runtime.

Plugins register against hook points in the dual architecture.
They can add new product commands, new research analyses, or new telemetry sinks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import importlib.util
import inspect
import sys


class PluginHook(Enum):
    POST_COMMAND = "post_command"
    PRE_COMMAND = "pre_command"
    POST_ANALYSIS = "post_analysis"
    ON_TELEMETRY = "on_telemetry"
    ON_MEMORY_ACCESS = "on_memory_access"
    ON_BENCHMARK_COMPLETE = "on_benchmark_complete"
    ON_EXPERIMENT_RESULT = "on_experiment_result"
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    CUSTOM = "custom"


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str = "unknown"
    hooks: List[PluginHook] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    min_lyme_version: str = "0.1.0"
    privacy_level: str = "medium"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "hooks": [h.value for h in self.hooks],
            "dependencies": self.dependencies,
            "min_lyme_version": self.min_lyme_version,
            "privacy_level": self.privacy_level,
            "tags": self.tags,
        }


@dataclass
class PluginContext:
    manifest: PluginManifest
    config: dict = field(default_factory=dict)
    data_dir: Optional[Path] = None
    loaded_at: Optional[float] = None


PluginHandler = Callable[..., Any]


@dataclass
class PluginSpec:
    manifest: PluginManifest
    module: Any
    handlers: Dict[PluginHook, List[PluginHandler]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "manifest": self.manifest.to_dict(),
            "registered_hooks": [h.value for h in self.handlers.keys()],
        }


class PluginRegistry:
    """Registry for loading, managing, and executing plugins."""

    def __init__(self):
        self._plugins: Dict[str, PluginSpec] = {}
        self._plugin_dirs: List[Path] = []
        self._handlers: Dict[PluginHook, List[tuple[str, PluginHandler]]] = {
            hook: [] for hook in PluginHook
        }

    def add_plugin_dir(self, path: Path):
        path = Path(path).resolve()
        if path.is_dir() and path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def discover_plugins(self) -> List[str]:
        discovered = []
        for plugin_dir in self._plugin_dirs:
            for py_file in sorted(plugin_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                name = py_file.stem
                if name not in self._plugins:
                    try:
                        spec = importlib.util.spec_from_file_location(
                            f"lyme_plugin_{name}", py_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[f"lyme_plugin_{name}"] = module
                            spec.loader.exec_module(module)
                            manifest = getattr(module, "manifest", None)
                            if isinstance(manifest, PluginManifest):
                                spec_obj = PluginSpec(manifest=manifest, module=module)
                                self._register_plugin_hooks(spec_obj)
                                self._plugins[name] = spec_obj
                                discovered.append(name)
                    except Exception as e:
                        pass
        return discovered

    def register_plugin(self, manifest: PluginManifest,
                        handlers: Dict[PluginHook, List[PluginHandler]]) -> str:
        spec = PluginSpec(manifest=manifest, module=None, handlers=handlers)
        self._register_plugin_hooks(spec)
        self._plugins[manifest.name] = spec
        return manifest.name

    def _register_plugin_hooks(self, spec: PluginSpec):
        for hook, hook_handlers in spec.handlers.items():
            for handler in hook_handlers:
                if hook not in self._handlers:
                    self._handlers[hook] = []
                self._handlers[hook].append((spec.manifest.name, handler))

    def get_plugin(self, name: str) -> Optional[PluginSpec]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[dict]:
        return [p.to_dict() for p in self._plugins.values()]

    def execute_hook(self, hook: PluginHook, *args, **kwargs) -> List[Any]:
        results = []
        for plugin_name, handler in self._handlers.get(hook, []):
            try:
                result = handler(*args, **kwargs)
                results.append((plugin_name, result))
            except Exception as e:
                results.append((plugin_name, None))
        return results

    def unload_plugin(self, name: str) -> bool:
        spec = self._plugins.pop(name, None)
        if not spec:
            return False
        for hook in PluginHook:
            self._handlers[hook] = [
                (pn, h) for pn, h in self._handlers[hook] if pn != name
            ]
        return True

    def to_dict(self) -> dict:
        return {
            "plugins": [p.to_dict() for p in self._plugins.values()],
            "plugin_dirs": [str(p) for p in self._plugin_dirs],
            "loaded_count": len(self._plugins),
        }


_default_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PluginRegistry()
    return _default_registry
