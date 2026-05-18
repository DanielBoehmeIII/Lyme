from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import time


class BetaOnboarding:
    """Beta onboarding flow for first 10 users."""

    MAX_BETA_USERS = 10

    def __init__(self):
        self.onboarding_dir = Path(".lyme") / "beta"
        self.onboarding_dir.mkdir(parents=True, exist_ok=True)
        self._users_file = self.onboarding_dir / "users.json"
        self._users = self._load_users()

    def _load_users(self) -> list:
        if self._users_file.exists():
            try:
                return json.loads(self._users_file.read_text())
            except Exception:
                return []
        return []

    def _save_users(self):
        self._users_file.write_text(json.dumps(self._users, indent=2))

    def has_slots(self) -> bool:
        return len(self._users) < self.MAX_BETA_USERS

    def register(self, email: str, name: str, use_case: str) -> dict:
        if not self.has_slots():
            return {"status": "full", "message": "Beta is full. Waitlist opened."}

        user = {
            "email": email,
            "name": name,
            "use_case": use_case,
            "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_id": f"beta-{len(self._users) + 1:03d}",
            "active": True,
            "value_score": 0.0,
            "friction_events": 0,
            "feedback_count": 0,
        }
        self._users.append(user)
        self._save_users()
        return {"status": "onboarded", "user": user}

    def status(self) -> dict:
        active = sum(1 for u in self._users if u.get("active"))
        return {
            "total_registered": len(self._users),
            "active_users": active,
            "slots_remaining": self.MAX_BETA_USERS - len(self._users),
            "is_full": not self.has_slots(),
        }

    def print_status(self):
        s = self.status()
        print(f"{'='*60}")
        print(f"  BETA ONBOARDING")
        print(f"{'='*60}")
        print(f"  Registered:  {s['total_registered']}/{self.MAX_BETA_USERS}")
        print(f"  Active:      {s['active_users']}")
        print(f"  Slots left:  {s['slots_remaining']}")
        print(f"  {'FULL' if s['is_full'] else 'Open'}")
        if self._users:
            print(f"\n  Users:")
            for u in self._users:
                print(f"    {u['user_id']:10s} {u['name']:20s} use_case={u['use_case'][:30]}")
        print(f"{'='*60}")


onboarding = BetaOnboarding()
