import json
import time
import uuid
from pathlib import Path
from typing import Optional


class BetaRecruitment:
    def __init__(self, storage_dir: str = ".lyme/beta/recruitment"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._pipeline: dict[str, dict] = {}
        self._load()

    def _pipeline_path(self) -> Path:
        return self._storage_dir / "pipeline.json"

    def _load(self):
        path = self._pipeline_path()
        if path.exists():
            try:
                self._pipeline = json.loads(path.read_text())
            except Exception:
                pass

    def _save(self):
        self._pipeline_path().write_text(json.dumps(self._pipeline, indent=2))

    def add_candidate(self, name: str, email: str, source: str = "", persona: str = "",
                      notes: str = "") -> str:
        cid = uuid.uuid4().hex[:8]
        self._pipeline[cid] = {
            "id": cid,
            "name": name,
            "email": email,
            "source": source,
            "persona": persona,
            "notes": notes,
            "status": "contacted",
            "created_at": time.time(),
            "last_contact": time.time(),
            "onboarding_call": False,
            "feedback_sessions": 0,
            "retention_days": 0,
        }
        self._save()
        return cid

    def update_status(self, candidate_id: str, status: str, notes: str = ""):
        candidate = self._pipeline.get(candidate_id)
        if candidate:
            candidate["status"] = status
            candidate["last_contact"] = time.time()
            if notes:
                candidate["notes"] = notes
            self._save()

    def record_onboarding_call(self, candidate_id: str, notes: str = ""):
        candidate = self._pipeline.get(candidate_id)
        if candidate:
            candidate["onboarding_call"] = True
            candidate["status"] = "onboarded"
            if notes:
                candidate["notes"] = candidate.get("notes", "") + f"\nOnboarding: {notes}"
            self._save()

    def record_feedback_session(self, candidate_id: str):
        candidate = self._pipeline.get(candidate_id)
        if candidate:
            candidate["feedback_sessions"] = candidate.get("feedback_sessions", 0) + 1
            self._save()

    def get_pipeline_summary(self) -> dict:
        if not self._pipeline:
            return {"total": 0}
        by_status = {}
        by_persona = {}
        by_source = {}
        onboarded = 0
        for c in self._pipeline.values():
            s = c.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            p = c.get("persona", "unknown")
            by_persona[p] = by_persona.get(p, 0) + 1
            src = c.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
            if c.get("onboarding_call"):
                onboarded += 1
        return {
            "total": len(self._pipeline),
            "by_status": by_status,
            "by_persona": by_persona,
            "by_source": by_source,
            "onboarded": onboarded,
            "total_feedback_sessions": sum(c.get("feedback_sessions", 0) for c in self._pipeline.values()),
        }


beta_recruitment = BetaRecruitment()
