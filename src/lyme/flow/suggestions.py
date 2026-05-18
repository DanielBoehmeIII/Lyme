from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..rhythm.predictor import CommandPredictor
from ..rhythm.analyzer import RhythmAnalyzer
from ..session.context import session_context
from ..session.recovery import session_recovery
from ..intelligence.engine import IntelligenceEngine


class ContextualSuggestions:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()

    def get_suggestions(self, max_items: int = 5) -> List[Dict[str, Any]]:
        suggestions = []

        try:
            if session_recovery.needs_resume():
                prompt = session_recovery.get_resume_prompt()
                if prompt:
                    suggestions.append({
                        "priority": 1,
                        "command": "lyme continue --resume",
                        "label": "Resume interrupted work",
                        "detail": "You have unfinished work",
                        "shortcut": "c",
                    })
        except Exception:
            pass

        if len(suggestions) < max_items:
            try:
                predictor = CommandPredictor()
                predictions = predictor.predict_next(top_n=2)
                for p in predictions:
                    if p.confidence > 0.3:
                        suggestions.append({
                            "priority": 2,
                            "command": p.command,
                            "label": p.command,
                            "detail": p.reason,
                            "shortcut": p.command.split()[-1][0] if " " in p.command else p.command[0],
                        })
            except Exception:
                pass

        if len(suggestions) < max_items:
            try:
                engine = IntelligenceEngine()
                report = engine.latest_report()
                if report and report.warning_count > 0:
                    suggestions.append({
                        "priority": 3,
                        "command": "lyme intel status",
                        "label": "Check intelligence warnings",
                        "detail": f"{report.warning_count} warning(s)",
                        "shortcut": "i",
                    })
            except Exception:
                pass

        if len(suggestions) < max_items:
            try:
                session = session_context.current()
                if session and session_context.is_active():
                    goal = session_context.active_goal()
                    if goal:
                        suggestions.append({
                            "priority": 3,
                            "command": "lyme session goal list",
                            "label": "Show active goals",
                            "detail": f"{goal.description[:50]}",
                            "shortcut": "g",
                        })
            except Exception:
                pass

        if len(suggestions) < max_items:
            suggestions.append({
                "priority": 4,
                "command": "lyme start",
                "label": "Daily startup",
                "detail": "Git status, tests, intelligence check",
                "shortcut": "s",
            })

        suggestions.sort(key=lambda x: x["priority"])
        return suggestions[:max_items]

    def print_suggestions(self) -> None:
        suggestions = self.get_suggestions()
        if not suggestions:
            return
        print(f"\n  Suggestions:")
        for s in suggestions:
            print(f"    [{s['shortcut']}] {s['label']}")
            print(f"         {s['detail']}")
        print(f"  (type a shortcut or run the command)")


contextual_suggestions = ContextualSuggestions()
