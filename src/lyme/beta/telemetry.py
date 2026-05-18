from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import time
import uuid


@dataclass
class TelemetryEvent:
    event_type: str
    category: str
    duration_s: float
    success: bool
    metadata: dict
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "category": self.category,
            "duration_s": round(self.duration_s, 3),
            "success": self.success,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class LocalTelemetry:
    """Local-only telemetry. Data never leaves the machine."""

    TELEMETRY_DIR = Path(".lyme") / "telemetry"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        if enabled:
            self.TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        self._session_id = uuid.uuid4().hex[:12]

    def record(self, event_type: str, category: str = "general",
               duration_s: float = 0.0, success: bool = True,
               metadata: dict = None):
        if not self.enabled:
            return
        event = TelemetryEvent(
            event_type=event_type, category=category,
            duration_s=duration_s, success=success,
            metadata=metadata or {}, timestamp=time.time(),
        )
        self._save(event)

    def _save(self, event: TelemetryEvent):
        day = time.strftime("%Y-%m-%d")
        day_dir = self.TELEMETRY_DIR / day
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{self._session_id}-{int(event.timestamp)}.json"
        path.write_text(json.dumps(event.to_dict(), indent=2))

    def get_stats(self) -> dict:
        if not self.TELEMETRY_DIR.exists():
            return {"events": 0, "days": 0}
        days = sorted(self.TELEMETRY_DIR.iterdir())
        total_events = 0
        for day_dir in days:
            total_events += len(list(day_dir.glob("*.json")))
        return {
            "events": total_events,
            "days": len(days),
            "session_id": self._session_id,
            "enabled": self.enabled,
        }

    def print_stats(self):
        s = self.get_stats()
        print(f"{'='*60}")
        print(f"  LOCAL TELEMETRY")
        print(f"{'='*60}")
        print(f"  Enabled:   {s['enabled']}")
        print(f"  Events:    {s['events']}")
        print(f"  Days:      {s['days']}")
        print(f"  Session:   {s['session_id']}")
        print(f"  Data dir:  {self.TELEMETRY_DIR}")
        print(f"  Privacy:   Local-only. Nothing leaves your machine.")
        print(f"{'='*60}")


telemetry = LocalTelemetry()
