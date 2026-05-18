from __future__ import annotations
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .report import StickinessReport


class DependenceAnalyzer:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()

    def analyze(self) -> StickinessReport:
        report = StickinessReport()

        # 1. Get command usage data
        cmd_stats = self._analyze_commands()
        report.total_commands = cmd_stats["total"]
        report.total_sessions = cmd_stats["sessions"]
        report.daily_active_users = cmd_stats["daily_active"]
        report.commands_per_session = cmd_stats["per_session"]
        report.repeat_workflows = cmd_stats["repeat_workflows"]
        report.most_used_commands = cmd_stats["top_commands"]

        # 2. Analyze session patterns
        session_stats = self._analyze_sessions()
        report.sessions_this_week = session_stats["this_week"]
        report.sessions_this_month = session_stats["this_month"]
        report.avg_session_length = session_stats["avg_length"]
        report.return_rate = session_stats["return_rate"]

        # 3. Analyze goal completion
        goal_stats = self._analyze_goals()
        report.goals_completed = goal_stats["completed"]
        report.goals_abandoned = goal_stats["abandoned"]
        report.goal_completion_rate = goal_stats["completion_rate"]

        # 4. Unprompted usage signals
        unprompted = self._analyze_unprompted_usage()
        report.unprompted_commands = unprompted["count"]
        report.command_shortcuts_used = unprompted["shortcuts"]
        report.reopen_after_close = unprompted["reopens"]

        # 5. Sticky features
        sticky = self._identify_sticky_features()
        report.sticky_features = sticky

        # 6. Calculate habit score
        report.habit_score = self._calculate_habit_score(report)

        # 7. Emotional dependence signals
        report.dependence_signals = self._detect_dependence_signals(report)

        return report

    def _analyze_commands(self) -> Dict[str, Any]:
        result = {
            "total": 0, "sessions": 0, "daily_active": 0,
            "per_session": 0.0, "repeat_workflows": 0, "top_commands": [],
        }
        try:
            from ..analytics.command_tracker import command_tracker
            stats = command_tracker.get_usage_stats()
            result["total"] = stats.get("total_commands", 0)
            result["sessions"] = stats.get("active_workflows", 0)
            heatmap = command_tracker.get_command_heatmap()
            for h in heatmap:
                if h["period"] == "today":
                    result["daily_active"] = h["commands"]
            commands = stats.get("commands", [])
            top = sorted(commands, key=lambda c: c["count"], reverse=True)
            result["top_commands"] = [(c["command"], c["count"]) for c in top[:5]]
            if result["sessions"] > 0:
                result["per_session"] = round(result["total"] / result["sessions"], 1)
            repeat_workflows = sum(1 for c in commands if c["count"] >= 3)
            result["repeat_workflows"] = repeat_workflows
        except Exception:
            pass
        return result

    def _analyze_sessions(self) -> Dict[str, Any]:
        result = {
            "this_week": 0, "this_month": 0,
            "avg_length": 0.0, "return_rate": 0.0,
        }
        try:
            from ..session.context import SessionContext
            ctx = SessionContext()
            sessions = ctx.list_sessions(limit=100)
            now = time.time()
            week_ago = now - 86400 * 7
            month_ago = now - 86400 * 30
            lengths = []
            weekly = 0
            monthly = 0
            for s in sessions:
                start = s.get("start_time", 0)
                if start >= week_ago:
                    weekly += 1
                if start >= month_ago:
                    monthly += 1
                if s.get("end_time") and s.get("start_time"):
                    lengths.append((s["end_time"] - s["start_time"]) / 60)
            result["this_week"] = weekly
            result["this_month"] = monthly
            if lengths:
                result["avg_length"] = round(sum(lengths) / len(lengths), 1)
            if monthly > 1:
                result["return_rate"] = round((weekly / monthly) * 100, 1) if monthly else 0
        except Exception:
            pass
        return result

    def _analyze_goals(self) -> Dict[str, Any]:
        result = {"completed": 0, "abandoned": 0, "completion_rate": 0.0}
        try:
            from ..session.context import SessionContext
            ctx = SessionContext()
            goals = ctx.all_goals()
            result["completed"] = sum(1 for g in goals if g.status == "completed")
            result["abandoned"] = sum(1 for g in goals if g.status in ("failed", "open"))
            total = result["completed"] + result["abandoned"]
            if total > 0:
                result["completion_rate"] = round(result["completed"] / total * 100, 1)
        except Exception:
            pass
        return result

    def _analyze_unprompted_usage(self) -> Dict[str, Any]:
        result = {"count": 0, "shortcuts": 0, "reopens": 0}
        try:
            from ..analytics.command_tracker import command_tracker
            stats = command_tracker.get_usage_stats()
            commands = stats.get("commands", [])
            for c in commands:
                name = c.get("command", "")
                count = c.get("count", 0)
                if name in ("start", "session", "suggest", "infer", "continue", "intel", "rhythm"):
                    result["count"] += count
                if name in ("continue", "suggest", "start"):
                    result["shortcuts"] += count
        except Exception:
            pass
        return result

    def _identify_sticky_features(self) -> List[Dict[str, Any]]:
        sticky = []
        try:
            from ..analytics.command_tracker import command_tracker
            stats = command_tracker.get_usage_stats()
            commands = stats.get("commands", [])
            for c in commands:
                name = c.get("command", "")
                count = c.get("count", 0)
                if count >= 2:
                    sticky.append({
                        "feature": name,
                        "usage_count": count,
                        "category": self._categorize_feature(name),
                        "stickiness": "high" if count >= 5 else "medium" if count >= 2 else "low",
                    })
            sticky.sort(key=lambda x: x["usage_count"], reverse=True)
        except Exception:
            pass
        return sticky[:10]

    def _categorize_feature(self, command: str) -> str:
        categories = {
            "heal": "repair", "fix": "repair", "v1-fix": "repair",
            "start": "workflow", "session": "workflow", "continue": "workflow",
            "intel": "intelligence", "drift": "intelligence", "debt": "intelligence",
            "rhythm": "rhythm", "predict": "rhythm",
            "infer": "flow", "suggest": "flow",
            "impact": "roi", "roi": "roi",
            "team": "team", "onboard": "team",
            "predictable": "trust",
        }
        for key, category in categories.items():
            if key in command:
                return category
        return "other"

    def _calculate_habit_score(self, report: StickinessReport) -> float:
        score = 0.0
        weights = {
            "daily_active": 0.2,
            "repeat_workflows": 0.2,
            "return_rate": 0.15,
            "goal_completion": 0.1,
            "session_frequency": 0.15,
            "unprompted": 0.1,
            "sticky_features": 0.1,
        }

        # Daily active (max 100 commands/day = full score)
        score += min(report.daily_active_users / 100, 1.0) * weights["daily_active"]

        # Repeat workflows
        score += min(report.repeat_workflows / 10, 1.0) * weights["repeat_workflows"]

        # Return rate
        score += (report.return_rate / 100) * weights["return_rate"]

        # Goal completion
        score += (report.goal_completion_rate / 100) * weights["goal_completion"]

        # Session frequency (weekly)
        score += min(report.sessions_this_week / 5, 1.0) * weights["session_frequency"]

        # Unprompted usage
        score += min(report.unprompted_commands / 20, 1.0) * weights["unprompted"]

        # Sticky features
        high_sticky = sum(1 for f in report.sticky_features if f.get("stickiness") == "high")
        score += min(high_sticky / 3, 1.0) * weights["sticky_features"]

        return round(min(score, 1.0), 3)

    def _detect_dependence_signals(self, report: StickinessReport) -> List[str]:
        signals = []
        if report.daily_active_users > 0:
            signals.append("User returns daily — high engagement signal")
        if report.unprompted_commands > 5:
            signals.append(f"Unprompted usage detected ({report.unprompted_commands}x) — habit forming")
        if report.repeat_workflows > 5:
            signals.append(f"{report.repeat_workflows} repeat workflows — muscle memory developing")
        if report.sessions_this_week > 3:
            signals.append(f"Multiple sessions per week — tool is part of workflow")
        if report.commands_per_session > 3:
            signals.append(f"Deep sessions ({report.commands_per_session} commands/session)")
        if report.goal_completion_rate > 50:
            signals.append(f"Goal completion rate {report.goal_completion_rate}% — trust established")
        if report.habit_score >= 0.5:
            signals.append("Habit score >= 0.5 — on track for dependence")
        if report.habit_score >= 0.8:
            signals.append("Habit score >= 0.8 — tool is becoming part of developer cognition")
        if report.reopen_after_close > 0:
            signals.append("Reopen-after-close detected — emotional dependence forming")
        return signals
