"""HealthCheck — server health monitoring."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: float = 0.0
    latency_ms: float = 0.0
    errors_last_minute: int = 0
    requests_last_minute: int = 0
    vram_used_gb: float = 0.0
    vram_total_gb: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "last_check": time.strftime("%H:%M:%S", time.localtime(self.last_check)) if self.last_check else "",
            "latency_ms": round(self.latency_ms, 2),
            "errors_last_minute": self.errors_last_minute,
            "requests_last_minute": self.requests_last_minute,
            "vram_used_gb": self.vram_used_gb,
            "vram_total_gb": self.vram_total_gb,
            "message": self.message,
        }
