"""Desktop — web-based UI for repo visualization and agent monitoring."""
from .app import DesktopApp, AppConfig, AppPage
from .monitoring import LiveMonitor, AgentSnapshot

__all__ = ["DesktopApp", "AppConfig", "AppPage", "LiveMonitor", "AgentSnapshot"]
