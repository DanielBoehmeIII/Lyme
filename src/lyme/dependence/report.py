from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StickinessReport:
    # Usage metrics
    total_commands: int = 0
    total_sessions: int = 0
    daily_active_users: int = 0
    commands_per_session: float = 0.0
    repeat_workflows: int = 0
    most_used_commands: List = field(default_factory=list)

    # Session metrics
    sessions_this_week: int = 0
    sessions_this_month: int = 0
    avg_session_length: float = 0.0
    return_rate: float = 0.0

    # Goal metrics
    goals_completed: int = 0
    goals_abandoned: int = 0
    goal_completion_rate: float = 0.0

    # Unprompted usage
    unprompted_commands: int = 0
    command_shortcuts_used: int = 0
    reopen_after_close: int = 0

    # Stickiness
    sticky_features: List[Dict[str, Any]] = field(default_factory=list)

    # Composite
    habit_score: float = 0.0
    dependence_signals: List[str] = field(default_factory=list)

    @property
    def session_frequency(self) -> float:
        return self.sessions_this_week / max(self.sessions_this_month, 1) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_commands": self.total_commands,
            "total_sessions": self.total_sessions,
            "daily_active_users": self.daily_active_users,
            "commands_per_session": self.commands_per_session,
            "repeat_workflows": self.repeat_workflows,
            "most_used_commands": self.most_used_commands[:5],
            "sessions_this_week": self.sessions_this_week,
            "sessions_this_month": self.sessions_this_month,
            "avg_session_length_min": self.avg_session_length,
            "return_rate_pct": self.return_rate,
            "goals_completed": self.goals_completed,
            "goals_abandoned": self.goals_abandoned,
            "goal_completion_rate_pct": self.goal_completion_rate,
            "unprompted_commands": self.unprompted_commands,
            "command_shortcuts_used": self.command_shortcuts_used,
            "reopen_after_close": self.reopen_after_close,
            "sticky_features": self.sticky_features[:5],
            "habit_score": self.habit_score,
            "dependence_signals": self.dependence_signals,
        }

    def to_markdown(self) -> str:
        lines = [f"# Stickiness & Dependence Report\n"]

        lines.append(f"## Habit Score: {self.habit_score:.1%}\n")
        bar_len = 30
        filled = int(self.habit_score * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"`{bar}`\n")

        lines.append("## Usage Metrics\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Total commands | {self.total_commands} |")
        lines.append(f"| Total sessions | {self.total_sessions} |")
        lines.append(f"| Commands per session | {self.commands_per_session} |")
        lines.append(f"| Daily active commands | {self.daily_active_users} |")
        lines.append(f"| Repeat workflows | {self.repeat_workflows} |")
        lines.append(f"| Sessions this week | {self.sessions_this_week} |")
        lines.append(f"| Sessions this month | {self.sessions_this_month} |")
        lines.append(f"| Avg session length | {self.avg_session_length}m |")
        lines.append(f"| Return rate | {self.return_rate:.0f}% |")
        lines.append("")

        lines.append("## Goal Completion\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Completed | {self.goals_completed} |")
        lines.append(f"| Abandoned | {self.goals_abandoned} |")
        lines.append(f"| Completion rate | {self.goal_completion_rate:.0f}% |")
        lines.append("")

        if self.unprompted_commands > 0:
            lines.append("## Unprompted Usage\n")
            lines.append(f"- **{self.unprompted_commands}** unprompted commands")
            lines.append(f"- **{self.command_shortcuts_used}** shortcuts used")
            lines.append(f"- **{self.reopen_after_close}** reopen-after-close events")
            lines.append("")

        if self.sticky_features:
            lines.append("## Sticky Features\n")
            for f in self.sticky_features[:5]:
                icon = "🔴" if f["stickiness"] == "high" else "🟡" if f["stickiness"] == "medium" else "🟢"
                lines.append(f"{icon} **{f['feature']}**: {f['usage_count']} uses ({f['category']})")
            lines.append("")

        if self.dependence_signals:
            lines.append("## Dependence Signals\n")
            for s in self.dependence_signals:
                lines.append(f"- {s}")
            lines.append("")

        lines.append("## Verdict\n")
        if self.habit_score >= 0.8:
            lines.append("**Lyme has become habit-forming.** The tool is part of the developer's cognition.")
        elif self.habit_score >= 0.5:
            lines.append("**Lyme is on track.** Habit is forming. Continue building depth.")
        elif self.habit_score >= 0.3:
            lines.append("**Early stage.** Usage is consistent but not yet reflexive.")
        else:
            lines.append("**Getting started.** More usage needed to form habits.")

        lines.append("")
        lines.append("## Roadmap for Deeper Integration\n")
        if self.habit_score < 0.5:
            lines.append("- Increase session frequency (target: daily)")
            lines.append("- Build more command sequences")
            lines.append("- Use `lyme start` as daily ritual")
            lines.append("- Set goals with `lyme session goal create`")
        else:
            lines.append("- Deepen existing workflows")
            lines.append("- Explore team features: `lyme team`")
            lines.append("- Check passive intelligence regularly: `lyme intel watch`")
            lines.append("- Review personal ROI: `lyme impact`")

        return "\n".join(lines)
