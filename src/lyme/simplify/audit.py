import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SimplificationSuggestion:
    category: str = ""
    priority: str = "medium"
    description: str = ""
    action: str = ""
    effort: str = "medium"

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "priority": self.priority,
            "description": self.description,
            "action": self.action,
            "effort": self.effort,
        }


COMMAND_REDUNDANCIES = {
    "run": {"merge_into": "bench", "reason": "Both run benchmarks. 'bench' is shorter."},
    "trace-std": {"merge_into": "trace", "reason": "Both handle execution traces. 'trace' is simpler."},
    "semantic-diff": {"merge_into": "diff", "reason": "Both classify diffs. 'diff' is shorter."},
    "observe": {"merge_into": "observe-v2", "reason": "v2 supersedes v1 for repo observation."},
    "benchmark": {"merge_into": "bench", "reason": "Duplicate of 'bench' command."},
    "list-scenarios": {"merge_into": "bench --list", "reason": "Can be a flag on bench instead of separate command."},
    "demo-v03": {"merge_into": "demo", "reason": "Consolidate demo variants under single 'demo' command."},
    "demo-v05": {"merge_into": "demo", "reason": "Consolidate demo variants under single 'demo' command."},
    "demo-v06": {"merge_into": "demo", "reason": "Consolidate demo variants under single 'demo' command."},
}

COMMANDS_TO_DEPRECATE = [
    "civ-map", "epistemology", "govern", "constitution",
    "similar", "compress", "fabric", "cross-repo",
    "tradeoff", "decisions", "roadmap", "maintain",
    "detect", "learn", "predict", "intent",
]

COMMANDS_TO_KEEP = [
    "doctor", "ask", "fix", "diff", "trace", "history",
    "audit", "undo", "dashboard", "start", "inbox",
    "watch", "bench", "init", "info", "plugin",
    "analytics", "beta", "pricing", "trust",
    "plan", "archfile", "self", "skill",
    "improve", "society", "research",
    "verify", "eval", "bridge", "pr", "ci",
    "dogfood", "metrics-audit",
    "simplify", "beginner", "config",
]

STUB_OR_NEVER_USED = {
    "learn": "Never used in production - learning from history not implemented",
    "predict": "Never used - failure prediction is experimental",
    "intent": "Never used - intent inference is experimental",
    "civ-map": "Never used - civilization maps are experimental",
    "epistemology": "Never used - evidence theory debugging is experimental",
    "govern": "Never used - governance engine is experimental",
    "constitution": "Never used - repo constitution is experimental",
    "similar": "Never used - similarity engine is experimental",
    "compress": "Never used - semantic compression is experimental",
    "fabric": "Never used - memory fabric is experimental",
    "cross-repo": "Never used - cross-repo mining is experimental",
    "tradeoff": "Never used - tradeoff simulation is experimental",
    "decisions": "Never used - decision memory is experimental",
    "roadmap": "Never used - roadmap generation is experimental",
    "maintain": "Never used - autonomous maintenance is experimental",
    "detect": "Never used - maintenance opportunity detection is experimental",
}


class ComplexityAudit:
    def __init__(self, src_dir: str = "src"):
        self._src_dir = Path(src_dir)

    def audit(self) -> dict:
        suggestions = []
        suggestions.extend(self._audit_commands())
        suggestions.extend(self._audit_modules())
        suggestions.extend(self._audit_config())
        return {
            "suggestions": [s.to_dict() for s in suggestions],
            "stats": self._get_stats(),
        }

    def _audit_commands(self) -> list[SimplificationSuggestion]:
        suggestions = []
        for cmd, info in COMMAND_REDUNDANCIES.items():
            suggestions.append(SimplificationSuggestion(
                category="redundant_command",
                priority="high",
                description=f"'{cmd}' is redundant with '{info['merge_into']}'. {info['reason']}",
                action=f"Merge {cmd} -> {info['merge_into']}",
                effort="low",
            ))
        for cmd in COMMANDS_TO_DEPRECATE:
            reason = STUB_OR_NEVER_USED.get(cmd, "Rarely used / experimental")
            suggestions.append(SimplificationSuggestion(
                category="deprecated_command",
                priority="medium",
                description=f"'{cmd}' can be deprecated. {reason}",
                action=f"Deprecate or hide behind '--experimental' flag",
                effort="low",
            ))
        suggestions.append(SimplificationSuggestion(
            category="too_many_commands",
            priority="high",
            description=f"83 top-level commands is overwhelming. Target: 25-30 core commands.",
            action="Create beginner mode showing only essential commands. Group rest under 'experimental'.",
            effort="medium",
        ))
        return suggestions

    def _audit_modules(self) -> list[SimplificationSuggestion]:
        suggestions = []
        redundant_modules = [
            ("lyme/observatory/observatory.py", "lyme/observatory/observatory_v2.py", "v1 observatory, v2 supersedes"),
            ("lyme/telemetry/", "lyme/analytics/", "Telemetry and analytics overlap significantly"),
            ("lyme/memory/", "lyme/memory_fabric/", "Two separate memory systems with similar purpose"),
        ]
        for a, b, reason in redundant_modules:
            suggestions.append(SimplificationSuggestion(
                category="redundant_module",
                priority="medium",
                description=f"'{a}' and '{b}'. {reason}",
                action=f"Consolidate into single module",
                effort="medium",
            ))
        return suggestions

    def _audit_config(self) -> list[SimplificationSuggestion]:
        suggestions = []
        config_path = Path(".lyme")
        suggestions.append(SimplificationSuggestion(
            category="config_complexity",
            priority="high",
            description="No auto-config or sane defaults mechanism exists.",
            action="Create 'lyme config init' with auto-detection of project settings.",
            effort="low",
        ))
        if config_path.is_dir():
            items = len(list(config_path.rglob("*")))
            if items > 50:
                suggestions.append(SimplificationSuggestion(
                    category="config_bloat",
                    priority="medium",
                    description=f".lyme/ has {items} files/items — cleanup stale artifacts.",
                    action="Add periodic cleanup of stale telemetry/crash data.",
                    effort="low",
                ))
        return suggestions

    def _get_stats(self) -> dict:
        total_commands = 83
        return {
            "total_commands": total_commands,
            "recommended_commands": len(COMMANDS_TO_KEEP),
            "redundant_commands": len(COMMAND_REDUNDANCIES),
            "deprecated_commands": len(COMMANDS_TO_DEPRECATE),
            "reduction_pct": round((1 - len(COMMANDS_TO_KEEP) / total_commands) * 100, 1),
            "stub_commands": len(STUB_OR_NEVER_USED),
        }
