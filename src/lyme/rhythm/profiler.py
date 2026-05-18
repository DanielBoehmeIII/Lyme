from __future__ import annotations
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import RhythmAnalyzer, RhythmReport
from .predictor import CommandPredictor, Prediction


@dataclass
class DeveloperProfile:
    persona: str = "general"
    preferred_commands: List[str] = field(default_factory=list)
    common_workflows: List[str] = field(default_factory=list)
    peak_hours: List[int] = field(default_factory=list)
    avg_session_length_min: float = 30.0
    interruption_tendency: float = 0.1
    top_sequences: List[Dict[str, Any]] = field(default_factory=list)
    suggested_shortcuts: List[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "preferred_commands": self.preferred_commands[:5],
            "common_workflows": self.common_workflows[:3],
            "peak_hours": self.peak_hours,
            "avg_session_length_min": round(self.avg_session_length_min, 1),
            "interruption_tendency": round(self.interruption_tendency, 3),
            "top_sequences": self.top_sequences[:3],
            "suggested_shortcuts": self.suggested_shortcuts[:3],
            "last_updated": self.last_updated,
        }

    def to_markdown(self) -> str:
        lines = [f"## Developer Profile\n"]
        lines.append(f"**Persona**: {self.persona}\n")
        if self.preferred_commands:
            lines.append("**Preferred commands**:")
            for cmd in self.preferred_commands[:5]:
                lines.append(f"- `{cmd}`")
            lines.append("")
        if self.peak_hours:
            hours = ", ".join(f"{h:02d}:00" for h in sorted(self.peak_hours))
            lines.append(f"**Peak hours**: {hours}")
        lines.append(f"**Avg session**: {self.avg_session_length_min:.0f} min")
        lines.append(f"**Interruption tendency**: {self.interruption_tendency:.0%}")
        if self.suggested_shortcuts:
            lines.append("\n**Suggested shortcuts**:")
            for s in self.suggested_shortcuts:
                lines.append(f"- {s}")
        return "\n".join(lines)


class DeveloperProfiler:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "rhythm" / "profile.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._profile: Optional[DeveloperProfile] = None
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text())
                self._profile = DeveloperProfile(**data)
            except Exception:
                pass

    def _save(self) -> None:
        if self._profile:
            self._db_path.write_text(json.dumps(self._profile.to_dict(), indent=2))

    def get_or_create_profile(self) -> DeveloperProfile:
        if self._profile is None:
            self._profile = DeveloperProfile()
        return self._profile

    def update_from_report(self, report: RhythmReport) -> DeveloperProfile:
        profile = self.get_or_create_profile()

        commands = [c[0] for c in report.most_used_commands]
        profile.preferred_commands = commands[:10]
        profile.avg_session_length_min = report.avg_session_duration_min
        profile.interruption_tendency = report.interruption_rate
        profile.peak_hours = [report.peak_hour] if report.peak_hour else []

        # Detect persona
        cmd_set = set(commands)
        all_cmds_str = " ".join(commands).lower()
        if "heal" in all_cmds_str and ("fix" in all_cmds_str or "v1-fix" in all_cmds_str):
            profile.persona = "maintainer"
        elif "ask" in all_cmds_str or "query" in all_cmds_str:
            profile.persona = "explorer"
        elif "fix" in all_cmds_str or "test" in all_cmds_str:
            profile.persona = "debugger"
        elif "start" in all_cmds_str or "session" in all_cmds_str:
            profile.persona = "structured"
        else:
            profile.persona = "general"

        # Generate shortcuts
        profile.suggested_shortcuts = []
        sequences = report.command_sequences
        for a, b, count in sequences[:3]:
            if count >= 2:
                profile.suggested_shortcuts.append(
                    f"`{a}` → `{b}` (seen {count}x) — consider workflow alias"
                )

        profile.top_sequences = [{"from": a, "to": b, "count": c} for a, b, c in sequences[:5]]
        profile.last_updated = time.time()
        self._save()
        return profile

    def profile(self) -> Optional[DeveloperProfile]:
        return self._profile
