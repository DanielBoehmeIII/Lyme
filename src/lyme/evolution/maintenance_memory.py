from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from .maintenance_loops import MaintenanceTask


class MaintenanceMemory:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self._memory_dir = self.repo_path / ".lyme" / "maintenance-memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self.entries: Dict[str, Any] = {}
        self._load()

    def remember_maintenance_event(self, task):  # MaintenanceTask
        entry = {
            "task_id": task.task_id,
            "opportunity_id": task.opportunity.opportunity_id,
            "category": task.opportunity.category.value,
            "title": task.opportunity.title,
            "target_files": task.opportunity.target_files,
            "outcome": task.outcome.value if task.outcome else None,
            "risk_level": task.risk_level,
            "approval_status": task.approval_status.value,
            "value": task.opportunity.value,
            "risk": task.opportunity.risk,
            "effort": task.opportunity.effort,
            "confidence": task.opportunity.confidence,
            "verification_passed": task.verification_result.get("passed", False) if task.verification_result else False,
            "timestamp": time.time(),
        }
        self.entries[task.task_id] = entry
        self._persist()

    def get_fragile_files(self) -> Set[str]:
        fragile = set()
        for entry in self.entries.values():
            if entry.get("outcome") in ("failed", "rolled_back"):
                for f in entry.get("target_files", []):
                    fragile.add(f)
        return fragile

    def get_safe_patterns(self) -> List[Dict[str, Any]]:
        safe = []
        for entry in self.entries.values():
            if entry.get("outcome") == "success" and entry.get("verification_passed"):
                safe.append({
                    "category": entry["category"],
                    "title": entry["title"],
                    "files": entry["target_files"],
                    "success_count": 1,
                })
        return safe

    def get_risky_categories(self) -> List[str]:
        risky = Counter()
        for entry in self.entries.values():
            if entry.get("outcome") in ("failed", "rolled_back"):
                risky[entry["category"]] += 1
        return [cat for cat, count in risky.most_common() if count >= 2]

    def get_recurring_patterns(self) -> List[Dict[str, Any]]:
        pattern_counter: Dict[str, int] = Counter()
        for entry in self.entries.values():
            key = f"{entry['category']}:{entry['title'][:40]}"
            pattern_counter[key] += 1
        return [
            {"pattern": pattern, "count": count}
            for pattern, count in pattern_counter.most_common(10)
            if count >= 2
        ]

    def what_was_safe(self) -> List[Dict[str, Any]]:
        return [
            e for e in self.entries.values()
            if e.get("outcome") == "success"
        ]

    def what_broke_tests(self) -> List[Dict[str, Any]]:
        return [
            e for e in self.entries.values()
            if e.get("outcome") == "rolled_back"
        ]

    def what_users_rejected(self) -> List[Dict[str, Any]]:
        return [
            e for e in self.entries.values()
            if e.get("approval_status") == "rejected"
        ]

    def which_files_are_fragile(self) -> List[str]:
        return sorted(self.get_fragile_files())

    def which_refactors_improved_metrics(self) -> List[Dict[str, Any]]:
        improved = []
        for entry in self.entries.values():
            if entry.get("outcome") == "success" and entry.get("value", 0) > 0.5:
                improved.append(entry)
        return improved

    def produce_report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(" MAINTENANCE MEMORY REPORT")
        lines.append("=" * 60)
        lines.append(f"  Total entries: {len(self.entries)}")
        lines.append("")

        safe = self.what_was_safe()
        lines.append(f"  Safe cleanups ({len(safe)}):")
        for s in safe[:5]:
            lines.append(f"    ✓ {s['title'][:70]}")

        broken = self.what_broke_tests()
        if broken:
            lines.append("")
            lines.append(f"  Broke tests ({len(broken)}):")
            for b in broken[:3]:
                lines.append(f"    ✗ {b['title'][:70]}")

        rejected = self.what_users_rejected()
        if rejected:
            lines.append("")
            lines.append(f"  User-rejected ({len(rejected)}):")
            for r in rejected[:3]:
                lines.append(f"    ⊘ {r['title'][:70]}")

        fragile = self.which_files_are_fragile()
        if fragile:
            lines.append("")
            lines.append(f"  Fragile files ({len(fragile)}):")
            for f in fragile[:10]:
                lines.append(f"    ⚠ {f}")

        patterns = self.get_recurring_patterns()
        if patterns:
            lines.append("")
            lines.append("  Recurring patterns:")
            for p in patterns[:5]:
                lines.append(f"    ↻ {p['pattern'][:60]} (x{p['count']})")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _persist(self):
        path = self._memory_dir / "memory.json"
        path.write_text(json.dumps(list(self.entries.values()), indent=2, default=str))

    def _load(self):
        path = self._memory_dir / "memory.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for entry in data:
                    if "task_id" in entry:
                        self.entries[entry["task_id"]] = entry
            except Exception:
                pass
