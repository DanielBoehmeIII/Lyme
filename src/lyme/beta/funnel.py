"""Activation funnel: track user journey from install → first value → repeat use."""

import json
import time
from pathlib import Path
from typing import Optional


FUNNEL_STAGES = [
    "installed",
    "first_command",
    "first_heal",
    "first_fix",
    "first_value",
    "repeat_user",
]

ABANDONMENT_REASONS = [
    "too_slow",
    "crashed",
    "confusing_output",
    "no_value_found",
    "wrong_tool",
    "install_failed",
    "other",
]


class ActivationFunnel:
    """Track user progression through activation stages."""

    FUNNEL_DIR = Path(".lyme") / "beta" / "funnel"

    def __init__(self):
        self.FUNNEL_DIR.mkdir(parents=True, exist_ok=True)

    def record_stage(self, user_id: str, stage: str, metadata: dict = None):
        if stage not in FUNNEL_STAGES:
            stage = f"custom:{stage}"
        entry = {
            "user_id": user_id,
            "stage": stage,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": metadata or {},
        }
        path = self.FUNNEL_DIR / f"{user_id}-{stage}-{int(time.time())}.json"
        path.write_text(json.dumps(entry, indent=2))

    def record_abandonment(self, user_id: str, reason: str, detail: str = "", metadata: dict = None):
        if reason not in ABANDONMENT_REASONS:
            reason = "other"
        entry = {
            "user_id": user_id,
            "reason": reason,
            "detail": detail,
            "stage_at_abandonment": self._get_current_stage(user_id),
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": metadata or {},
        }
        path = self.FUNNEL_DIR / f"abandonment-{user_id}-{int(time.time())}.json"
        path.write_text(json.dumps(entry, indent=2))

    def _get_current_stage(self, user_id: str) -> Optional[str]:
        stages = []
        for f in self.FUNNEL_DIR.glob(f"{user_id}-*.json"):
            try:
                data = json.loads(f.read_text())
                stage = data.get("stage", "")
                if stage in FUNNEL_STAGES:
                    stages.append((data["timestamp"], stage))
            except Exception:
                pass
        stages.sort(key=lambda x: x[0], reverse=True)
        return stages[0][1] if stages else None

    def get_funnel(self) -> dict:
        users = set()
        stage_counts = {s: 0 for s in FUNNEL_STAGES}
        abandonments = []

        for f in self.FUNNEL_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                stage = data.get("stage", "")
                user_id = data.get("user_id", "")
                if stage in FUNNEL_STAGES:
                    users.add(user_id)
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                if data.get("reason"):
                    abandonments.append({
                        "user_id": user_id,
                        "reason": data["reason"],
                        "detail": data.get("detail", ""),
                        "timestamp": data.get("timestamp", 0),
                    })
            except Exception:
                pass

        funnel = {}
        for i, stage in enumerate(FUNNEL_STAGES):
            count = stage_counts.get(stage, 0)
            prev_count = stage_counts.get(FUNNEL_STAGES[i - 1], count) if i > 0 else count
            conversion = round(count / max(prev_count, 1) * 100, 1) if i > 0 else 100.0
            funnel[stage] = {
                "users": count,
                "conversion_rate_pct": conversion,
            }

        reason_counts = {}
        for a in abandonments:
            reason = a.get("reason", "other")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        return {
            "total_unique_users": len(users),
            "funnel": funnel,
            "abandonments": {
                "total": len(abandonments),
                "by_reason": reason_counts,
                "top_reasons": sorted(reason_counts.items(), key=lambda x: x[1], reverse=True),
            },
        }

    def print_funnel(self):
        funnel = self.get_funnel()
        print("=" * 55)
        print("  ACTIVATION FUNNEL")
        print("=" * 55)
        print(f"  Unique users: {funnel['total_unique_users']}")
        print()
        for stage, data in funnel["funnel"].items():
            bar = "█" * max(1, int(data["users"] / max(funnel["total_unique_users"], 1) * 20))
            print(f"  {stage:20s} {data['users']:4d}  [{bar:20s}] {data['conversion_rate_pct']:5.1f}%")
        print()
        if funnel["abandonments"]["total"] > 0:
            print("  Abandonment reasons:")
            for reason, count in funnel["abandonments"]["top_reasons"][:5]:
                print(f"    • {reason}: {count}")
        print("=" * 55)

    def print_retention(self):
        sessions_dir = Path(".lyme") / "beta" / "sessions"
        if not sessions_dir.is_dir():
            print("  No session data yet.")
            return

        users = {}
        for f in sessions_dir.glob("*.json"):
            try:
                session = json.loads(f.read_text())
                uid = session.get("user_id", "unknown")
                if uid not in users:
                    users[uid] = {"sessions": 0, "commands": 0, "errors": 0, "last_seen": 0, "first_seen": float("inf")}
                users[uid]["sessions"] += 1
                users[uid]["commands"] += len(session.get("commands", []))
                users[uid]["errors"] += len(session.get("errors", []))
                start = session.get("start_time", 0)
                end = session.get("end_time", 0)
                users[uid]["last_seen"] = max(users[uid]["last_seen"], end)
                users[uid]["first_seen"] = min(users[uid]["first_seen"], start)
            except Exception:
                pass

        print("=" * 55)
        print("  RETENTION REPORT")
        print("=" * 55)
        print(f"  Total users with sessions: {len(users)}")
        print()
        now = time.time()
        active = sum(1 for u in users.values() if (now - u["last_seen"]) < 86400 * 7)
        churned = sum(1 for u in users.values() if (now - u["last_seen"]) > 86400 * 30)
        print(f"  Active (last 7d):  {active}")
        print(f"  At-risk (7-30d):   {len(users) - active - churned}")
        print(f"  Churned (>30d):    {churned}")
        print()
        heavy = sum(1 for u in users.values() if u["commands"] > 20)
        medium = sum(1 for u in users.values() if 5 < u["commands"] <= 20)
        light = sum(1 for u in users.values() if u["commands"] <= 5)
        print(f"  Heavy users:  {heavy}")
        print(f"  Medium users: {medium}")
        print(f"  Light users:  {light}")
        print("=" * 55)


activation_funnel = ActivationFunnel()
