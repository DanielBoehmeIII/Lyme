from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import time


@dataclass
class FeedbackEntry:
    user_id: str
    category: str
    message: str
    rating: int
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "category": self.category,
            "message": self.message,
            "rating": self.rating,
            "timestamp": self.timestamp,
        }


class FeedbackCapture:
    CAPTURE_DIR = Path(".lyme") / "beta" / "feedback"

    def __init__(self):
        self.CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    def capture(self, user_id: str, category: str, message: str, rating: int = 3) -> FeedbackEntry:
        entry = FeedbackEntry(
            user_id=user_id,
            category=category,
            message=message,
            rating=max(1, min(5, rating)),
            timestamp=time.time(),
        )
        self._save(entry)
        return entry

    def _save(self, entry: FeedbackEntry):
        path = self.CAPTURE_DIR / f"{int(entry.timestamp)}-{entry.user_id}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2))

    def list_all(self) -> list:
        entries = []
        for f in sorted(self.CAPTURE_DIR.iterdir()):
            if f.suffix == ".json":
                try:
                    entries.append(json.loads(f.read_text()))
                except Exception:
                    pass
        return entries

    def summary(self) -> dict:
        entries = self.list_all()
        if not entries:
            return {"count": 0, "avg_rating": 0, "categories": {}}
        categories = {}
        for e in entries:
            cat = e.get("category", "unknown")
            categories.setdefault(cat, []).append(e.get("rating", 3))
        avg_rating = sum(e.get("rating", 3) for e in entries) / len(entries)
        return {
            "count": len(entries),
            "avg_rating": round(avg_rating, 1),
            "categories": {k: {"count": len(v), "avg_rating": round(sum(v) / len(v), 1)} for k, v in categories.items()},
        }


feedback_capture = FeedbackCapture()
