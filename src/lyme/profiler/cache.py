import json
import time
from pathlib import Path
from typing import Optional


class WarmCache:
    def __init__(self, cache_dir: str = ".lyme/cache"):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, tuple] = {}
        self._hits = 0
        self._misses = 0

    def _cache_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
        return self._cache_dir / f"{safe}.json"

    def get(self, key: str, max_age_s: Optional[float] = None) -> Optional[dict]:
        if key in self._memory:
            data, ts = self._memory[key]
            if max_age_s is None or (time.time() - ts) < max_age_s:
                self._hits += 1
                return data
        path = self._cache_path(key)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                age = time.time() - data.get("_cached_at", 0)
                if max_age_s is None or age < max_age_s:
                    self._memory[key] = (data, data.get("_cached_at", 0))
                    self._hits += 1
                    return data
            except Exception:
                pass
        self._misses += 1
        return None

    def set(self, key: str, data: dict):
        data["_cached_at"] = time.time()
        self._memory[key] = (data, time.time())
        path = self._cache_path(key)
        path.write_text(json.dumps(data, indent=2))

    def invalidate(self, key: str = ""):
        if key:
            self._memory.pop(key, None)
            path = self._cache_path(key)
            if path.exists():
                path.unlink()
        else:
            self._memory.clear()
            for path in self._cache_dir.glob("*.json"):
                path.unlink()

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total else 0,
            "memory_entries": len(self._memory),
            "disk_entries": len(list(self._cache_dir.glob("*.json"))),
        }


warm_cache = WarmCache()
