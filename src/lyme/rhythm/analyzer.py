from __future__ import annotations
import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from ..analytics.command_tracker import command_tracker
from ..session.context import session_context


@dataclass
class RhythmReport:
    total_commands: int = 0
    commands_per_session: float = 0.0
    peak_hour: int = 0
    peak_day: str = ""
    avg_session_duration_min: float = 0.0
    weekday_activity: Dict[str, int] = field(default_factory=dict)
    hourly_activity: Dict[str, List[int]] = field(default_factory=dict)
    command_sequences: List[Tuple[str, str, int]] = field(default_factory=list)
    most_used_commands: List[Tuple[str, int]] = field(default_factory=list)
    success_rate: float = 0.0
    interruption_rate: float = 0.0
    productivity_windows: List[Dict[str, Any]] = field(default_factory=list)
    preferred_workflows: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_commands": self.total_commands,
            "commands_per_session": round(self.commands_per_session, 1),
            "peak_hour": self.peak_hour,
            "peak_day": self.peak_day,
            "avg_session_duration_min": round(self.avg_session_duration_min, 1),
            "weekday_activity": dict(self.weekday_activity),
            "hourly_activity": {str(k): v for k, v in self.hourly_activity.items()},
            "command_sequences": [[a, b, c] for a, b, c in self.command_sequences[:5]],
            "most_used_commands": [[c, n] for c, n in self.most_used_commands[:5]],
            "success_rate": round(self.success_rate, 3),
            "interruption_rate": round(self.interruption_rate, 3),
            "productivity_windows": self.productivity_windows,
            "preferred_workflows": self.preferred_workflows,
        }

    def to_markdown(self) -> str:
        lines = [f"## Developer Rhythm Report\n"]
        lines.append(f"**Activity**: {self.total_commands} commands across sessions\n")
        lines.append(f"**Peak time**: {self.peak_day} at {self.peak_hour}:00")
        lines.append(f"**Avg session**: {self.avg_session_duration_min:.0f}m, {self.commands_per_session:.0f} commands")
        lines.append(f"**Success rate**: {self.success_rate:.0%}")
        lines.append(f"**Interruption rate**: {self.interruption_rate:.0%}")
        lines.append("")
        if self.productivity_windows:
            lines.append("### Productivity Windows\n")
            for w in self.productivity_windows[:3]:
                lines.append(f"- {w['label']}: {w['commands']} commands, {w['success_rate']:.0%} success")
            lines.append("")
        if self.most_used_commands:
            lines.append("### Most Used Commands\n")
            for cmd, count in self.most_used_commands[:5]:
                lines.append(f"- `{cmd}`: {count}x")
            lines.append("")
        if self.command_sequences:
            lines.append("### Common Sequences\n")
            for a, b, count in self.command_sequences[:3]:
                lines.append(f"- `{a}` → `{b}`: {count}x")
            lines.append("")
        if self.preferred_workflows:
            lines.append("### Preferred Workflows\n")
            for w in self.preferred_workflows[:3]:
                lines.append(f"- {w}")
            lines.append("")
        return "\n".join(lines)


@dataclass
class ActionSequence:
    actions: List[str]
    count: int = 1
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": self.actions,
            "count": self.count,
            "last_seen": self.last_seen,
        }


class RhythmAnalyzer:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._db_path = self._repo / ".lyme" / "rhythm" / "sequences.json"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._sequences: Dict[str, ActionSequence] = {}
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text())
                for k, v in data.items():
                    self._sequences[k] = ActionSequence(**v)
            except Exception:
                pass

    def _save(self) -> None:
        data = {k: v.to_dict() for k, v in self._sequences.items()}
        self._db_path.write_text(json.dumps(data, indent=2))

    def record_action(self, action: str) -> None:
        for key, seq in list(self._sequences.items()):
            actions = seq.actions
            if len(actions) >= 2:
                shifted = actions[1:] + [action]
                new_key = " → ".join(shifted)
                seq.actions = shifted
                seq.count += 1 if new_key == key else 0
                seq.last_seen = time.time()
                self._sequences[new_key] = seq
                if new_key != key:
                    del self._sequences[key]
                return
            elif len(actions) == 1:
                actions.append(action)
                seq.last_seen = time.time()
                self._save()
                return
        key = action
        if key not in self._sequences:
            self._sequences[key] = ActionSequence(actions=[action])
        else:
            self._sequences[key].count += 1
            self._sequences[key].last_seen = time.time()
        self._save()

    def analyze(self) -> RhythmReport:
        report = RhythmReport()

        try:
            stats = command_tracker.get_usage_stats()
            report.total_commands = stats.get("total_commands", 0)
            report.most_used_commands = [
                (c["command"], c["count"])
                for c in sorted(stats.get("commands", []), key=lambda x: x["count"], reverse=True)
            ]
            successes = sum(c.get("successes", 0) for c in stats.get("commands", []))
            total = sum(c.get("count", 0) for c in stats.get("commands", []))
            report.success_rate = successes / max(total, 1)

            heatmap = command_tracker.get_command_heatmap()
            for h in heatmap:
                if h["period"] == "today":
                    pass
        except Exception:
            pass

        activity_by_hour: Dict[int, int] = defaultdict(int)
        activity_by_day: Dict[str, int] = defaultdict(int)
        session_durations: List[float] = []
        session_commands: List[int] = []
        failed_commands = 0
        total_commands_from_sessions = 0

        try:
            sessions = session_context.list_sessions(limit=50)
            for s in sessions:
                if s.get("end_time") and s.get("start_time"):
                    dur = (s["end_time"] - s["start_time"]) / 60
                    if dur > 0 and dur < 480:
                        session_durations.append(dur)
                cmd_count = s.get("commands", 0)
                if cmd_count > 0:
                    session_commands.append(cmd_count)
        except Exception:
            pass

        try:
            command_history = []
            sessions_data = session_context.list_sessions(limit=30)
            for s in sessions_data:
                sid = s.get("session_id", "")
                archive_path = self._repo / ".lyme" / "session" / f"archive_{sid}.json"
                if archive_path.exists():
                    try:
                        data = json.loads(archive_path.read_text())
                        for cmd_entry in data.get("commands_run", []):
                            command_history.append(cmd_entry)
                    except Exception:
                        pass

            for entry in command_history:
                ts = entry.get("timestamp", time.time())
                t = time.localtime(ts)
                activity_by_hour[t.tm_hour] += 1
                activity_by_day[time.strftime("%A", t)] += 1
                if not entry.get("success", True):
                    failed_commands += 1
                total_commands_from_sessions += 1
        except Exception:
            pass

        if activity_by_hour:
            report.peak_hour = max(activity_by_hour, key=activity_by_hour.get)
        if activity_by_day:
            report.peak_day = max(activity_by_day, key=activity_by_day.get)
        report.weekday_activity = dict(activity_by_day)
        report.hourly_activity = {str(h): [activity_by_hour.get(h, 0)] for h in range(24)}

        report.avg_session_duration_min = (
            sum(session_durations) / len(session_durations) if session_durations else 0
        )
        report.commands_per_session = (
            sum(session_commands) / len(session_commands) if session_commands else 0
        )
        report.interruption_rate = failed_commands / max(total_commands_from_sessions, 1)

        sequences = sorted(
            [(seq.actions[0] if len(seq.actions) == 1 else seq.actions[0],
              seq.actions[-1] if len(seq.actions) > 1 else "",
              seq.count)
             for seq in self._sequences.values() if len(seq.actions) >= 2],
            key=lambda x: -x[2],
        )
        report.command_sequences = [(a, b, c) for a, b, c in sequences[:10]]

        report.productivity_windows = self._find_productivity_windows(activity_by_hour)
        report.preferred_workflows = self._detect_preferred_workflows(report.most_used_commands)

        return report

    def _find_productivity_windows(self, hourly: Dict[int, int]) -> List[Dict[str, Any]]:
        if not hourly:
            return []
        windows = []
        for hour in range(0, 24, 3):
            count = sum(hourly.get(h, 0) for h in range(hour, min(hour + 3, 24)))
            if count > 0:
                windows.append({
                    "label": f"{hour:02d}:00-{min(hour+3, 24):02d}:00",
                    "commands": count,
                    "success_rate": self.success_rate if hasattr(self, 'success_rate') else 0.8,
                })
        windows.sort(key=lambda w: w["commands"], reverse=True)
        return windows

    def _detect_preferred_workflows(self, commands: List[Tuple[str, int]]) -> List[str]:
        workflows = []
        cmd_names = [c[0] for c in commands]
        if "heal" in cmd_names:
            workflows.append("lyme heal — repair workflow")
        if "fix" in cmd_names or "v1-fix" in cmd_names:
            workflows.append("lyme fix — targeted fixes")
        if "ask" in cmd_names:
            workflows.append("lyme ask — codebase Q&A")
        if "start" in cmd_names:
            workflows.append("lyme start — daily startup")
        if "session" in cmd_names:
            workflows.append("lyme session — structured sessions")
        return workflows

    def common_sequences(self) -> List[Dict[str, Any]]:
        return [
            {"sequence": seq.actions, "count": seq.count, "last_seen": seq.last_seen}
            for seq in sorted(self._sequences.values(), key=lambda s: -s.count)[:10]
            if len(seq.actions) >= 2
        ]
