import time
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from ..telemetry import Span, Event, TimelineEvent


@dataclass
class ReplaySession:
    replay_id: str = ""
    trace_id: str = ""
    agent_name: str = ""
    scenario_name: str = ""
    events: List[dict] = field(default_factory=list)
    spans: List[dict] = field(default_factory=list)
    timeline: List[dict] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    speed: float = 1.0
    current_index: int = 0

    def to_dict(self) -> dict:
        return {
            "replay_id": self.replay_id,
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "scenario_name": self.scenario_name,
            "events": self.events,
            "spans": self.spans,
            "timeline": self.timeline,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speed": self.speed,
        }


class DeterministicReplayer:
    def __init__(self):
        self._sessions: Dict[str, ReplaySession] = {}

    def load_from_trace(self, trace_data: dict) -> ReplaySession:
        session = ReplaySession(
            replay_id=Path(trace_data.get("trace_id", "unknown")).stem,
            trace_id=trace_data.get("trace_id", ""),
            agent_name=trace_data.get("agent", ""),
            scenario_name=trace_data.get("scenario", ""),
            events=trace_data.get("events", []),
            spans=trace_data.get("spans", []),
            timeline=trace_data.get("timeline", []),
            start_time=trace_data.get("start_time", 0)
                or min((e.get("timestamp", 0) for e in trace_data.get("events", [])), default=0),
            end_time=trace_data.get("end_time", 0)
                or max((e.get("timestamp", 0) for e in trace_data.get("events", [])), default=0),
        )
        self._sessions[session.replay_id] = session
        return session

    def load_from_file(self, path: str) -> Optional[ReplaySession]:
        p = Path(path)
        if not p.exists():
            return None
        with open(p) as f:
            data = json.load(f)
        return self.load_from_trace(data)

    def get_session(self, replay_id: str) -> Optional[ReplaySession]:
        return self._sessions.get(replay_id)

    def play(self, session: ReplaySession, speed: float = 1.0,
             on_event: Callable = None, on_step: Callable = None):
        session.speed = speed
        sorted_events = sorted(
            session.events,
            key=lambda e: e.get("timestamp", 0)
        )

        if not sorted_events:
            return

        base_time = sorted_events[0].get("timestamp", time.time())
        real_start = time.time()

        for i, event in enumerate(sorted_events):
            session.current_index = i
            event_time = event.get("timestamp", base_time)
            elapsed = event_time - base_time
            scaled_delay = elapsed / speed

            target_time = real_start + scaled_delay
            now = time.time()
            if target_time > now:
                time.sleep(target_time - now)

            if on_event:
                on_event(event, i, len(sorted_events))
            if on_step:
                on_step(i, len(sorted_events))

    def step_through(self, session: ReplaySession, step: int = 1) -> Optional[dict]:
        session.current_index = min(session.current_index + step, len(session.events) - 1)
        if session.events:
            return session.events[session.current_index]
        return None

    def get_playback_speed(self, session: ReplaySession, event_index: int) -> float:
        if not session.events or event_index < 1:
            return 1.0

        prev = session.events[event_index - 1]
        curr = session.events[event_index]
        real_gap = curr.get("timestamp", 0) - prev.get("timestamp", 0)
        if real_gap <= 0:
            return 1.0
        return 1.0 / real_gap if real_gap > 0 else 1.0

    def session_summary(self, session: ReplaySession) -> dict:
        if not session.events:
            return {"event_count": 0}

        type_counts = {}
        for e in session.events:
            etype = e.get("type", "unknown")
            type_counts[etype] = type_counts.get(etype, 0) + 1

        real_duration = session.end_time - session.start_time

        return {
            "event_count": len(session.events),
            "span_count": len(session.spans),
            "type_distribution": type_counts,
            "real_duration_s": real_duration,
            "events_per_second": len(session.events) / real_duration if real_duration > 0 else 0,
        }
