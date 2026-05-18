import importlib
import sys
from types import ModuleType
from typing import Any


class LazyLoader:
    def __init__(self, name: str, fallback: Any = None, error_msg: str = ""):
        self._name = name
        self._fallback = fallback
        self._error_msg = error_msg
        self._module = None

    def _load(self):
        if self._module is None:
            try:
                self._module = importlib.import_module(self._name)
            except ImportError:
                if self._fallback is not None:
                    return self._fallback
                raise ImportError(self._error_msg or f"Could not load '{self._name}'")
        return self._module

    def __getattr__(self, name: str) -> Any:
        mod = self._load()
        return getattr(mod, name)

    def __call__(self, *args, **kwargs):
        mod = self._load()
        return mod(*args, **kwargs)

    @property
    def loaded(self) -> bool:
        return self._module is not None


class LazyImport:
    def __init__(self):
        self._lazy: dict[str, LazyLoader] = {}

    def register(self, name: str, alias: str = "", fallback: Any = None):
        key = alias or name.split(".")[-1]
        if key not in self._lazy:
            self._lazy[key] = LazyLoader(name, fallback=fallback)

    def __getattr__(self, name: str) -> LazyLoader:
        if name in self._lazy:
            return self._lazy[name]
        loader = LazyLoader(name)
        self._lazy[name] = loader
        return loader


lazy_imports = LazyImport()
