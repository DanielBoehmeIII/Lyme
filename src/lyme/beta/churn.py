from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import time


class ChurnFrictionTracker:
    """Track churn risk and friction events for beta users."""

    TRACKER_DIR = Path(".lyme") / "beta" / "churn"

    def __init__(self):
        self.TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    def record_friction(self, user_id: str, event: str, severity: int = 1):
        entry = {
            "user_id": user_id,
            "event": event,
            "severity": severity,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        day = time.strftime("%Y-%m-%d")
        day_dir = self.TRACKER_DIR / day
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{user_id}-{int(time.time())}.json"
        path.write_text(json.dumps(entry, indent=2))
        return entry

    def get_churn_risk(self, user_id: str) -> dict:
        events = []
        for day_dir in sorted(self.TRACKER_DIR.iterdir()):
            if day_dir.is_dir():
                for f in day_dir.glob(f"{user_id}-*.json"):
                    try:
                        events.append(json.loads(f.read_text()))
                    except Exception:
                        pass

        total_severity = sum(e.get("severity", 1) for e in events)
        event_count = len(events)
        risk_score = min(1.0, total_severity / 10.0)

        return {
            "user_id": user_id,
            "friction_events": event_count,
            "total_severity": total_severity,
            "churn_risk": round(risk_score, 2),
            "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.3 else "low",
        }

    def print_tracker(self):
        print(f"{'='*60}")
        print(f"  CHURN / FRICTION TRACKER")
        print(f"{'='*60}")
        days = sorted(self.TRACKER_DIR.iterdir())
        if not days:
            print(f"\n  No friction events recorded.")
            print(f"{'='*60}")
            return
        print(f"\n  Days with events: {len(days)}")
        for day_dir in days:
            events = len(list(day_dir.glob("*.json")))
            print(f"    {day_dir.name}: {events} events")
        print(f"{'='*60}")


churn_tracker = ChurnFrictionTracker()
