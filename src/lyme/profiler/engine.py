import time
import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ProfileResult:
    name: str
    duration_s: float
    success: bool = True
    error: Optional[str] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_s": round(self.duration_s, 4),
            "success": self.success,
            "error": self.error,
            "details": self.details,
        }


class ProfilerEngine:
    def __init__(self):
        self._results: list[ProfileResult] = []

    def profile_import(self, module_path: str) -> ProfileResult:
        start = time.perf_counter()
        try:
            if module_path in sys.modules:
                del sys.modules[module_path]
            importlib.import_module(module_path)
            duration = time.perf_counter() - start
            result = ProfileResult(name=f"import:{module_path}", duration_s=duration)
            self._results.append(result)
            return result
        except Exception as e:
            duration = time.perf_counter() - start
            result = ProfileResult(name=f"import:{module_path}", duration_s=duration, success=False, error=str(e))
            self._results.append(result)
            return result

    def profile_function(self, name: str, fn, *args, **kwargs) -> ProfileResult:
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            duration = time.perf_counter() - start
            pr = ProfileResult(name=name, duration_s=duration)
            self._results.append(pr)
            return pr
        except Exception as e:
            duration = time.perf_counter() - start
            pr = ProfileResult(name=name, duration_s=duration, success=False, error=str(e))
            self._results.append(pr)
            return pr

    def profile_cli_startup(self) -> ProfileResult:
        start = time.perf_counter()
        try:
            from lyme.cli import LymeCLI
            LymeCLI()
            duration = time.perf_counter() - start
            result = ProfileResult(name="cli_startup", duration_s=duration)
            self._results.append(result)
            return result
        except Exception as e:
            duration = time.perf_counter() - start
            result = ProfileResult(name="cli_startup", duration_s=duration, success=False, error=str(e))
            self._results.append(result)
            return result

    def run_full_profile(self) -> dict:
        self._results.clear()
        self.profile_cli_startup()
        heavy_imports = [
            "lyme",
            "lyme.cli",
            "lyme.doctor",
            "lyme.ask",
            "lyme.graph",
            "lyme.society",
            "lyme.evolution",
            "lyme.benchmark",
            "lyme.analytics",
        ]
        for mod in heavy_imports:
            self.profile_import(mod)
        total = sum(r.duration_s for r in self._results)
        slowest = max(self._results, key=lambda r: r.duration_s)
        return {
            "results": [r.to_dict() for r in self._results],
            "total_duration_s": round(total, 4),
            "slowest": slowest.to_dict() if slowest else None,
            "count": len(self._results),
        }

    def suggest_optimizations(self) -> list[str]:
        suggestions = []
        for r in self._results:
            if r.duration_s > 0.5:
                suggestions.append(
                    f"Lazy-load '{r.name}' ({r.duration_s:.2f}s) — defer import until first use"
                )
            if r.duration_s > 1.0:
                suggestions.append(
                    f"CRITICAL: '{r.name}' takes {r.duration_s:.2f}s — consider async loading or warm cache"
                )
        if not suggestions:
            suggestions.append("All imports are fast (<500ms each). No optimizations needed.")
        return suggestions
