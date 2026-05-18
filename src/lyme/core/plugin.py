"""Plugin system — registry, discovery, and base classes."""
from __future__ import annotations
import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type


@dataclass
class PluginSpec:
    name: str
    version: str
    description: str
    entry_point: str
    layer: str
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entry_point": self.entry_point,
            "layer": self.layer,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
        }


class Plugin:
    spec: PluginSpec
    instance: Any = None

    def __init__(self, spec: PluginSpec):
        self.spec = spec

    def activate(self) -> None: ...
    def deactivate(self) -> None: ...
    def health_check(self) -> bool:
        return True


PluginFactory = Callable[[], Plugin]


class PluginRegistry:
    _plugins: Dict[str, Plugin] = {}
    _factories: Dict[str, PluginFactory] = {}
    _discovered: Set[str] = set()

    @classmethod
    def register(cls, name: str, factory: PluginFactory) -> None:
        cls._factories[name] = factory

    @classmethod
    def get(cls, name: str) -> Optional[Plugin]:
        if name in cls._plugins:
            return cls._plugins[name]
        if name in cls._factories:
            plugin = cls._factories[name]()
            cls._plugins[name] = plugin
            return plugin
        return None

    @classmethod
    def get_all(cls) -> List[Plugin]:
        for name in list(cls._factories.keys()):
            if name not in cls._plugins:
                cls.get(name)
        return list(cls._plugins.values())

    @classmethod
    def discover(cls, *paths: str) -> int:
        count = 0
        for path in paths:
            p = Path(path)
            if not p.is_dir():
                continue
            for entry in p.iterdir():
                if entry.is_dir() and entry.name.startswith("lyme_plugin_"):
                    try:
                        module_name = entry.name
                        if module_name not in cls._discovered:
                            importlib.import_module(module_name)
                            cls._discovered.add(module_name)
                            count += 1
                    except Exception:
                        continue
                elif entry.suffix == ".py" and entry.stem.startswith("lyme_plugin_"):
                    try:
                        module_name = f"lyme_plugins.{entry.stem}"
                        if module_name not in cls._discovered:
                            importlib.import_module(module_name)
                            cls._discovered.add(module_name)
                            count += 1
                    except Exception:
                        continue
        return count

    @classmethod
    def discover_entry_points(cls) -> int:
        count = 0
        for module_info in pkgutil.iter_modules():
            name = module_info.name
            if name.startswith("lyme_plugin_"):
                try:
                    importlib.import_module(name)
                    count += 1
                except Exception:
                    continue
        return count

    @classmethod
    def list_plugins(cls) -> List[Dict[str, Any]]:
        return [
            {"name": name, "activated": name in cls._plugins}
            for name in sorted(set(list(cls._factories.keys()) + list(cls._plugins.keys())))
        ]

    @classmethod
    def clear(cls) -> None:
        cls._plugins.clear()
        cls._factories.clear()
        cls._discovered.clear()
