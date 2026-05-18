"""UI — terminal rendering, dashboards, and interactive shell."""
from .terminal import TerminalRenderer, Theme, TaskTree, Spinner
from .shell import InteractiveShell
from .metrics_dashboard import render_dashboard
from .thought_viewer import render_cognitive_trace
from .timeline_viewer import render_timeline

__all__ = [
    "TerminalRenderer", "Theme", "TaskTree", "Spinner",
    "InteractiveShell",
    "render_dashboard", "render_cognitive_trace", "render_timeline",
]
