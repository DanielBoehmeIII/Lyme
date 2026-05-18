"""DesktopApp — lightweight web UI server for Lyme."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional


class AppPage(Enum):
    DASHBOARD = "dashboard"
    REPO_VIEW = "repo_view"
    AGENT_MONITOR = "agent_monitor"
    BENCHMARKS = "benchmarks"
    SETTINGS = "settings"


@dataclass
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    theme: str = "dark"
    open_browser: bool = True


HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Lyme Desktop</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px}
.card h2{color:#58a6ff;font-size:16px;margin-bottom:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.stat{font-size:28px;font-weight:bold}
.stat-label{color:#8b949e;font-size:12px}
nav{display:flex;gap:10px;margin-bottom:20px}
nav a{color:#8b949e;text-decoration:none;padding:8px 16px;border-radius:6px}
nav a:hover{background:#161b22;color:#58a6ff}
table{border-collapse:collapse;width:100%}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}
th{color:#8b949e;font-weight:600}
</style></head><body>
<nav>
  <a href="/">Dashboard</a>
  <a href="/repo">Repository</a>
  <a href="/agents">Agents</a>
  <a href="/benchmarks">Benchmarks</a>
  <a href="/settings">Settings</a>
</nav>
<h1>{title}</h1>
{content}
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    app: "DesktopApp" = None

    def do_GET(self):
        if self.path == "/":
            self._respond(200, self.app._render_dashboard())
        elif self.path == "/api/status":
            self._respond_json(200, self.app._api_status())
        else:
            self._respond(200, self.app._render_dashboard())

    def _respond(self, code: int, body: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def _respond_json(self, code: int, data: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, *a):
        pass


class DesktopApp:
    def __init__(self, config: AppConfig = None):
        self.config = config or AppConfig()
        self._pages: Dict[str, str] = {}
        _Handler.app = self

    def add_page(self, name: str, content: str) -> None:
        self._pages[name] = content

    def _render_dashboard(self) -> str:
        cards = '<div class="grid">'
        for name, content in list(self._pages.items())[:4]:
            cards += f'<div class="card"><h2>{name}</h2><div>{content[:200]}</div></div>'
        cards += "</div>"
        return HTML_TEMPLATE.format(title="Lyme Desktop", content=cards)

    def _api_status(self) -> Dict[str, Any]:
        return {
            "status": "running",
            "pages": len(self._pages),
            "theme": self.config.theme,
        }

    def start(self) -> None:
        server = HTTPServer((self.config.host, self.config.port), _Handler)
        print(f"Lyme Desktop running at http://{self.config.host}:{self.config.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
