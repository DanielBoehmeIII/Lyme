from __future__ import annotations

import json
import math
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .observatory import ObservatorySnapshot, AnomalyEvent, SubsystemHealthReport
from .continuous_observatory import ContinuousObservatory, RiskAlert, StructuralForecast, DailySummary
from .health_forecasting import HealthForecast


def _build_html(values: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lyme Observatory — Mission Control</title>
<style>
  :root {{
    --bg-primary: #0a0e17;
    --bg-secondary: #111827;
    --bg-card: #1a1f2e;
    --border: #2a3040;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --accent-cyan: #22d3ee;
    --accent-green: #4ade80;
    --accent-yellow: #facc15;
    --accent-orange: #fb923c;
    --accent-red: #f87171;
    --accent-purple: #a78bfa;
    --accent-blue: #60a5fa;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'SF Mono', 'JetBrains Mono', 'Cascadia Code', monospace;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    padding: 20px;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px; background: var(--bg-card);
    border: 1px solid var(--border); border-radius: 8px;
    margin-bottom: 24px;
  }}
  .header h1 {{
    font-size: 20px; font-weight: 600;
    color: var(--accent-cyan); letter-spacing: 1px;
  }}
  .status-dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--accent-green); display: inline-block;
  }}
  .status-dot.warning {{ background: var(--accent-yellow); }}
  .status-dot.critical {{ background: var(--accent-red); animation: pulse 1.5s infinite; }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} }}
  .dashboard-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px; margin-bottom: 24px;
  }}
  .card {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 8px; padding: 20px;
  }}
  .card h3 {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--text-secondary); margin-bottom: 12px;
  }}
  .metric-value {{ font-size: 32px; font-weight: 700; line-height: 1.2; }}
  .metric-label {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
  .metric-trend {{ font-size: 12px; margin-top: 8px; }}
  .trend-up {{ color: var(--accent-green); }}
  .trend-down {{ color: var(--accent-red); }}
  .trend-stable {{ color: var(--accent-yellow); }}
  .section {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 8px; padding: 20px; margin-bottom: 16px;
  }}
  .section h2 {{ font-size: 14px; color: var(--accent-cyan); margin-bottom: 16px; letter-spacing: 0.5px; }}
  .subsystem-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .subsystem-item {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; background: var(--bg-secondary);
    border-radius: 6px; border-left: 3px solid var(--accent-green);
  }}
  .subsystem-item.critical {{ border-left-color: var(--accent-red); }}
  .subsystem-item.warning {{ border-left-color: var(--accent-orange); }}
  .subsystem-name {{ font-size: 13px; }}
  .subsystem-health {{ font-size: 14px; font-weight: 600; }}
  .alert-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .alert-item {{
    padding: 10px 14px; background: var(--bg-secondary);
    border-radius: 6px; border-left: 3px solid var(--accent-yellow);
    font-size: 13px;
  }}
  .alert-item.critical {{ border-left-color: var(--accent-red); }}
  .alert-item.high {{ border-left-color: var(--accent-orange); }}
  .alert-title {{ font-weight: 600; margin-bottom: 4px; }}
  .alert-desc {{ color: var(--text-secondary); font-size: 12px; }}
  .forecast-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .forecast-item {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; background: var(--bg-secondary);
    border-radius: 6px; font-size: 13px;
  }}
  .forecast-metric {{ color: var(--text-secondary); }}
  .forecast-value {{ font-weight: 600; }}
  .timeline-bar {{ display: flex; align-items: center; gap: 2px; margin-top: 12px; }}
  .timeline-segment {{ flex: 1; height: 8px; border-radius: 2px; transition: background 0.3s; }}
  .health-gauge {{ width: 100%; height: 6px; background: var(--bg-secondary); border-radius: 3px; margin-top: 8px; overflow: hidden; }}
  .health-gauge-fill {{ height: 100%; border-radius: 3px; transition: width 0.5s; background: linear-gradient(90deg, var(--accent-red), var(--accent-yellow), var(--accent-green)); }}
  .two-column {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 768px) {{ .two-column {{ grid-template-columns: 1fr; }} }}
  .section-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 1024px) {{ .section-grid {{ grid-template-columns: 1fr; }} }}
  .evidence-list {{ list-style: none; font-size: 12px; color: var(--text-secondary); }}
  .evidence-list li::before {{ content: "→ "; color: var(--accent-cyan); }}
</style>
</head>
<body>
<div class="header">
  <h1>⚡ LYME OBSERVATORY</h1>
  <div style="display:flex;align-items:center;gap:16px">
    <span class="status-dot {values['status_class']}"></span>
    <span>{values['status_text']}</span>
    <span style="color:var(--text-secondary);font-size:12px">
      {values['observation_count']} obs &middot; {values['uptime']}
    </span>
  </div>
</div>

<div class="dashboard-grid">
  <div class="card">
    <h3>Overall Health</h3>
    <div class="metric-value" style="color:{values['health_color']}">{values['health_score']}</div>
    <div class="metric-label">Composite health score</div>
    <div class="health-gauge"><div class="health-gauge-fill" style="width:{values['health_pct']}%"></div></div>
    <div class="metric-trend {values['health_trend_class']}">{values['health_trend_text']}</div>
  </div>
  <div class="card">
    <h3>Subsystems Monitored</h3>
    <div class="metric-value" style="color:var(--accent-cyan)">{values['subsystem_count']}</div>
    <div class="metric-label">Active subsystems</div>
  </div>
  <div class="card">
    <h3>Active Alerts</h3>
    <div class="metric-value" style="color:{values['alert_color']}">{values['alert_count']}</div>
    <div class="metric-label">Unacknowledged risk alerts</div>
  </div>
  <div class="card">
    <h3>Trend Health</h3>
    <div class="metric-value" style="color:var(--accent-purple)">{values['trend_health']}</div>
    <div class="metric-label">{values['trend_improving']} improving / {values['trend_degrading']} degrading</div>
  </div>
</div>

<div class="section-grid">
  <div class="section">
    <h2>Subsystem Health</h2>
    <div class="subsystem-list">{values['subsystem_html']}</div>
  </div>
  <div class="section">
    <h2>Active Alerts</h2>
    <div class="alert-list">{values['alert_html']}</div>
  </div>
</div>

<div class="section">
  <h2>Structural Forecasts</h2>
  <div class="forecast-list">{values['forecast_html']}</div>
</div>

<div class="section">
  <h2>Daily Summary</h2>
  <div class="two-column">
    <div>
      <h3 style="font-size:11px;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px">Repository Health Timeline</h3>
      <div class="timeline-bar">{values['timeline_html']}</div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-secondary);margin-top:4px"><span>Past</span><span>Present</span></div>
    </div>
    <div>
      <h3 style="font-size:11px;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px">Evidence Trail</h3>
      <ul class="evidence-list">{values['evidence_html']}</ul>
    </div>
  </div>
</div>

<div class="section">
  <h2>Recommendations</h2>
  <div style="font-size:13px;line-height:1.8">{values['recommendation_html']}</div>
</div>

<div style="text-align:center;font-size:11px;color:var(--text-secondary);padding:20px">
  Lyme Observatory &mdash; Generated at {values['generated_at']}
</div>
</body>
</html>"""


class ObservatoryUIRenderer:
    def render(self, observatory: ContinuousObservatory,
               health_forecasts: Optional[List[HealthForecast]] = None,
               output_path: str = "lyme-observatory.html") -> str:
        state = observatory.get_state()
        current = observatory.current_snapshot()

        health_score = state.get("overall_health", 0.5)
        observation_count = state.get("observations", 0)
        uptime_seconds = state.get("uptime_seconds", 0)

        uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
        if uptime_seconds < 60:
            uptime_str = f"{int(uptime_seconds)}s"

        status_text = "ACTIVE" if state.get("status") == "active" else "PAUSED"
        status_class = "warning" if state.get("status") != "active" else ""

        if health_score < 0.3:
            health_color = "var(--accent-red)"
            health_trend_class = "trend-down"
            health_trend_text = "Critical — immediate attention required"
            status_class = "critical"
        elif health_score < 0.5:
            health_color = "var(--accent-orange)"
            health_trend_class = "trend-down"
            health_trend_text = "Degraded — monitor closely"
            status_class = "warning"
        elif health_score < 0.7:
            health_color = "var(--accent-yellow)"
            health_trend_class = "trend-stable"
            health_trend_text = "Fair — room for improvement"
        else:
            health_color = "var(--accent-green)"
            health_trend_class = "trend-up"
            health_trend_text = "Good — healthy trajectory"

        health_pct = health_score * 100

        subsystem_count = len(current.subsystem_health) if current else 0
        alert_count = len(observatory.get_active_alerts())

        if alert_count > 0:
            alert_color = "var(--accent-red)"
        else:
            alert_color = "var(--accent-green)"

        degrading_count = sum(
            1 for s in (current.subsystem_health.values() if current else [])
            if s.health_score < 0.4
        ) if current else 0
        improving_count = sum(
            1 for s in (current.subsystem_health.values() if current else [])
            if s.health_score > 0.7
        ) if current else 0

        trend_health = "At Risk" if degrading_count > improving_count else "Stable"
        trend_degrading = degrading_count
        trend_improving = improving_count

        subsystem_html = ""
        if current:
            for sub, health in sorted(
                current.subsystem_health.items(),
                key=lambda x: x[1].health_score,
            ):
                cls = "critical" if health.health_score < 0.3 else "warning" if health.health_score < 0.5 else ""
                color = "var(--accent-red)" if health.health_score < 0.3 else "var(--accent-orange)" if health.health_score < 0.5 else "var(--accent-green)"
                subsystem_html += f"""
                <div class="subsystem-item {cls}">
                  <span class="subsystem-name">{sub}</span>
                  <span class="subsystem-health" style="color:{color}">{health.health_score:.2f}</span>
                </div>"""

        alert_html = ""
        alerts = observatory.get_active_alerts()
        if alerts:
            for alert in alerts[:5]:
                cls = alert.risk_level.value
                alert_html += f"""
                <div class="alert-item {cls}">
                  <div class="alert-title">[{alert.risk_level.value.upper()}] {alert.title}</div>
                  <div class="alert-desc">{alert.description[:150]}</div>
                </div>"""
        else:
            alert_html = '<div style="color:var(--accent-green);font-size:13px">No active alerts</div>'

        forecast_html = ""
        forecasts = observatory._forecasts[-8:] if observatory._forecasts else []
        if forecasts:
            for fc in forecasts:
                color = "var(--accent-green)" if fc.trend == "improving" else "var(--accent-red)" if fc.trend == "degrading" else "var(--accent-yellow)"
                forecast_html += f"""
                <div class="forecast-item">
                  <span class="forecast-metric">{fc.metric}</span>
                  <span>
                    <span class="forecast-value" style="color:{color}">{fc.current_value:.2f} → {fc.projected_value:.2f}</span>
                    <span style="font-size:11px;color:var(--text-secondary);margin-left:8px">ci:[{fc.confidence_lower:.2f},{fc.confidence_upper:.2f}]</span>
                  </span>
                </div>"""
        else:
            forecast_html = '<div style="color:var(--text-secondary);font-size:13px">No forecasts available</div>'

        timeline_html = ""
        health_hist = observatory.get_health_trajectory()
        hist = health_hist.get("history", [])
        if len(hist) > 1:
            for val in hist:
                if val < 0.3:
                    color = "var(--accent-red)"
                elif val < 0.5:
                    color = "var(--accent-orange)"
                elif val < 0.7:
                    color = "var(--accent-yellow)"
                else:
                    color = "var(--accent-green)"
                timeline_html += f'<div class="timeline-segment" style="background:{color}"></div>'

        evidence_html = ""
        if health_forecasts:
            for fc in health_forecasts[:2]:
                for ev in fc.evidence_trail[:3]:
                    evidence_html += f"<li>{ev.observation[:100]}</li>"
        if not evidence_html:
            evidence_html = "<li>No evidence trails recorded yet</li>"

        recent_summaries = observatory._daily_summaries[-3:] if observatory._daily_summaries else []
        recommendation_html = ""
        if recent_summaries:
            for summary in recent_summaries:
                for rec in summary.recommendations:
                    recommendation_html += f"<div>• {rec}</div>"
        else:
            recommendation_html = "<div>• Begin monitoring to generate recommendations</div>"

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        values = {
            "status_class": status_class,
            "status_text": status_text,
            "observation_count": str(observation_count),
            "uptime": uptime_str,
            "health_score": f"{health_score:.2f}",
            "health_color": health_color,
            "health_pct": f"{health_pct:.0f}",
            "health_trend_class": health_trend_class,
            "health_trend_text": health_trend_text,
            "subsystem_count": str(subsystem_count),
            "alert_count": str(alert_count),
            "alert_color": alert_color,
            "trend_health": trend_health,
            "trend_improving": str(trend_improving),
            "trend_degrading": str(trend_degrading),
            "subsystem_html": subsystem_html,
            "alert_html": alert_html,
            "forecast_html": forecast_html,
            "timeline_html": timeline_html,
            "evidence_html": evidence_html,
            "recommendation_html": recommendation_html,
            "generated_at": generated_at,
        }

        html = _build_html(values)

        with open(output_path, "w") as f:
            f.write(html)
        return output_path
