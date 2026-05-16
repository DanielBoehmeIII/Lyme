from typing import List, Dict, Any, Optional
from .deterministic import DeterministicReplayer, ReplaySession
from ..cognition import CognitiveTrace, ThoughtAnalyzer, AnomalyDetector
from ..telemetry import Timeline, TimelineEvent


class TraceViewer:
    def __init__(self):
        self.replayer = DeterministicReplayer()
        self.thought_analyzer = ThoughtAnalyzer()
        self.anomaly_detector = AnomalyDetector()

    def analyze(self, trace_data: dict) -> dict:
        session = self.replayer.load_from_trace(trace_data)
        replay_summary = self.replayer.session_summary(session)

        cog_trace = None
        if "steps" in trace_data or "decisions" in trace_data:
            cog_trace = CognitiveTrace(
                trace_id=trace_data.get("trace_id", ""),
                agent_name=trace_data.get("agent_name", ""),
                scenario_name=trace_data.get("scenario_name", ""),
            )
            for step_data in trace_data.get("steps", []):
                from .cognition.trace import ThoughtStep
                cog_trace.add_step(ThoughtStep(**step_data))
            for dec_data in trace_data.get("decisions", []):
                from .cognition.trace import DecisionPoint
                cog_trace.add_decision(DecisionPoint(**dec_data))

        analysis = {}
        anomalies = []

        if cog_trace:
            analysis = self.thought_analyzer.analyze(cog_trace)
            anomalies = self.anomaly_detector.detect_all(cog_trace)

        return {
            "session": replay_summary,
            "analysis": analysis,
            "anomalies": [a.to_dict() for a in anomalies],
            "event_timeline": self._build_timeline(trace_data),
        }

    def _build_timeline(self, trace_data: dict) -> List[dict]:
        timeline = []
        for event in trace_data.get("events", []):
            timeline.append(TimelineEvent(
                timestamp=event.get("timestamp", 0),
                type=event.get("type", "event"),
                label=event.get("type", "").replace("_", " ").title(),
                detail=event.get("payload", {}).get("description", ""),
                status=event.get("severity", "info"),
                event_id=event.get("id", ""),
            ).to_dict())
        return sorted(timeline, key=lambda e: e["timestamp"])

    def print_analysis(self, trace_data: dict):
        result = self.analyze(trace_data)

        print("=== Trace Analysis ===")
        print(f"Events: {result['session'].get('event_count', 0)}")
        print(f"Duration: {result['session'].get('real_duration_s', 0):.1f}s")

        if result["analysis"]:
            print("\n--- Cognitive Analysis ---")
            summary = result["analysis"].get("summary", {})
            print(f"Steps: {summary.get('total_steps', 0)}")
            print(f"Decisions: {summary.get('total_decisions', 0)}")
            print(f"Branches: {summary.get('branches_explored', 0)}")

            conf = result["analysis"].get("confidence_analysis", {})
            print(f"Confidence: avg={conf.get('avg', 0):.2f}, "
                  f"volatility={conf.get('volatility', 0):.3f}")

        if result["anomalies"]:
            print(f"\n!!! Anomalies Detected: {len(result['anomalies'])}")
            for a in result["anomalies"]:
                print(f"  [{a['type']}] severity={a['severity']:.2f}: {a['description'][:100]}")

        return result
