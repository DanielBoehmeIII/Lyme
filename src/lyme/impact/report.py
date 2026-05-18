from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict

from .models import PersonalMetrics


@dataclass
class ImpactReport:
    metrics: PersonalMetrics = field(default_factory=PersonalMetrics)
    generated_at: float = 0.0

    def __post_init__(self):
        import time as _time
        self.generated_at = _time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "generated_at": self.generated_at,
        }

    def to_markdown(self) -> str:
        m = self.metrics
        lines = [f"# Lyme Impact Report\n"]
        lines.append(f"## Personal ROI\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Commands run | {m.commands_run} |")
        lines.append(f"| Commands automated | {m.commands_automated} |")
        lines.append(f"| Sessions tracked | {m.sessions_completed} |")
        lines.append(f"| Goals completed | {m.goals_completed} |")
        lines.append(f"| Bugs prevented (warnings) | {m.total_warnings_generated} |")
        lines.append(f"| Suspicious commits caught | {m.suspicious_commits_caught} |")
        lines.append(f"| Flaky tests identified | {m.flaky_tests_identified} |")
        lines.append(f"| Architecture drift found | {m.drift_violations_detected} |")
        lines.append(f"| Technical debt surfaced | {m.debt_items_surfaced} |")
        lines.append("")
        lines.append("## Savings\n")
        lines.append(f"| Category | Amount |")
        lines.append(f"|---|---|")
        lines.append(f"| Time saved | {m.estimated_time_saved_min:.0f} minutes |")
        lines.append(f"| Hours saved | {m.estimated_time_saved_min / 60:.1f} hours |")
        lines.append(f"| Cost saved (${100}/hr) | ${m.estimated_cost_saved:.0f} |")
        lines.append(f"| Active days | {m.uptime_days:.0f} days |")
        lines.append("")
        lines.append("## Throughput\n")
        if m.uptime_days > 0:
            cmds_per_day = m.commands_run / max(m.uptime_days, 0.1)
            lines.append(f"- **{cmds_per_day:.1f}** commands per day")
        if m.sessions_completed > 0:
            goals_per_session = m.goals_completed / max(m.sessions_completed, 1)
            lines.append(f"- **{goals_per_session:.1f}** goals per session")
        warnings_per_session = m.total_warnings_generated / max(m.sessions_completed, 1)
        lines.append(f"- **{warnings_per_session:.1f}** warnings surfaced per session")
        lines.append("")
        lines.append("## Verdict\n")
        if m.estimated_time_saved_min > 120:
            lines.append("**Lyme is saving you significant time.** Keep using it to compound these gains.")
        elif m.estimated_time_saved_min > 30:
            lines.append("**Lyme is providing measurable value.** The more you use it, the better it gets.")
        else:
            lines.append("**Lyme is getting started.** Run more commands and sessions to build your impact profile.")
        return "\n".join(lines)
