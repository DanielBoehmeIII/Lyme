import time
import uuid
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scenario import BenchmarkScenario, ScenarioResult
from .runner import AgentRunner, AgentResult, AgentRunnerStatus
from .registry import ScenarioRegistry
from ..config import AgentConfig, Settings
from ..telemetry import Tracer, EventLog, MetricsStore, EventType, Timeline
from ..store import EventStore, StructuredOutput, BenchmarkReport
from ..cognition import ThoughtRecorder


class BenchmarkRun:
    def __init__(self, run_id: str, agent_name: str, scenario_name: str):
        self.run_id = run_id
        self.agent_name = agent_name
        self.scenario_name = scenario_name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = "pending"
        self.tracer = Tracer()
        self.event_log = EventLog()
        self.metrics = MetricsStore()
        self.timeline = Timeline()
        self.thought_recorder = ThoughtRecorder(store=self.metrics)
        self.agent_result: Optional[AgentResult] = None
        self.scenario_result: Optional[ScenarioResult] = None
        self.error: Optional[str] = None


class BenchmarkEngine:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.store = EventStore(self.settings.benchmark.output_dir)
        self._runs: Dict[str, BenchmarkRun] = {}
        self._active_run: Optional[BenchmarkRun] = None
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []

    def run_scenario(self, scenario: BenchmarkScenario, agent_cfg: AgentConfig,
                     run_id: str = "") -> BenchmarkRun:
        run_id = run_id or uuid.uuid4().hex[:12]
        run = BenchmarkRun(run_id=run_id, agent_name=agent_cfg.name,
                           scenario_name=scenario.name)
        self._runs[run_id] = run
        self._active_run = run

        scenario_result = ScenarioResult(scenario_name=scenario.name)

        run.event_log.emit(
            EventType.SYSTEM,
            {"description": f"Benchmark run started: {agent_cfg.name} on {scenario.name}",
             "run_id": run_id},
            source="engine",
        )

        context = {}
        work_dir = scenario.create_work_dir(
            self.settings.benchmark.experiments_dir
        )

        try:
            with run.tracer.trace(f"scenario:{scenario.name}", category="benchmark"):
                with run.tracer.span("setup", category="benchmark"):
                    context = scenario.setup(work_dir)

                with run.tracer.span("agent_execution", category="agent"):
                    runner = AgentRunner(
                        agent_cfg,
                        tracer=run.tracer,
                        event_log=run.event_log,
                        metrics=run.metrics,
                    )
                    prompt = scenario.task_prompt(context)

                    if self.settings.benchmark.record_thoughts:
                        run.thought_recorder.begin_trace(
                            trace_id=run.run_id,
                            agent_name=agent_cfg.name,
                            scenario_name=scenario.name,
                        )
                        run.thought_recorder.record_plan(
                            prompt, context={
                                "scenario": scenario.name,
                                "agent": agent_cfg.name,
                            }
                        )

                    agent_result = runner.run(
                        prompt, work_dir,
                        timeout_s=scenario.timeout_s,
                    )
                    run.agent_result = agent_result

                    if self.settings.benchmark.record_thoughts:
                        run.thought_recorder.finish_trace(
                            status=agent_result.status.value,
                            metrics={"duration_ms": agent_result.duration_ms},
                        )

                with run.tracer.span("evaluation", category="benchmark"):
                    scenario_result = scenario.evaluate(work_dir, context)
                    scenario_result.tokens_input = agent_result.tokens_input
                    scenario_result.tokens_output = agent_result.tokens_output
                    scenario_result.tool_calls_count = len(agent_result.tool_calls)
                    scenario_result.events_count = len(run.event_log.get_events())

                    if agent_result.status == AgentRunnerStatus.TIMEOUT:
                        scenario_result.errors.append(f"Timeout ({scenario.timeout_s}s)")
                    elif agent_result.status == AgentRunnerStatus.ERROR:
                        scenario_result.errors.append(agent_result.error or "Unknown error")

                run.scenario_result = scenario_result
                run.status = "success" if scenario_result.success else "failure"

        except Exception as e:
            run.status = "error"
            run.error = str(e)
            run.event_log.emit(
                EventType.ERROR,
                {"description": f"Engine error: {e}"},
                severity="error", source="engine",
            )
        finally:
            run.end_time = time.time()
            scenario.teardown(work_dir, context)

            run.timeline.clear()
            for event in run.event_log.get_events():
                run.timeline.add_from_event(event)
            for span in run.tracer.get_spans(run.run_id):
                run.timeline.add_from_span(span)

            self._save_run(run)
            self._notify_listeners(run)
            self._active_run = None

        return run

    def run_scenarios(self, scenario_names: List[str], agent_configs: List[AgentConfig],
                      parallel: bool = False) -> List[BenchmarkRun]:
        scenarios = []
        for name in scenario_names:
            s = ScenarioRegistry.get_instance(name)
            if s is None:
                print(f"Warning: Scenario '{name}' not found, skipping")
                continue
            scenarios.append(s)

        runs = []
        if parallel and len(scenarios) > 1:
            with ThreadPoolExecutor(max_workers=self.settings.benchmark.max_parallel) as ex:
                futures = []
                for scenario in scenarios:
                    for agent_cfg in agent_configs:
                        f = ex.submit(self.run_scenario, scenario, agent_cfg)
                        futures.append(f)
                for f in as_completed(futures):
                    runs.append(f.result())
        else:
            for scenario in scenarios:
                for agent_cfg in agent_configs:
                    runs.append(self.run_scenario(scenario, agent_cfg))

        return runs

    def run_all(self, agent_configs: List[AgentConfig] = None,
                parallel: bool = False) -> List[BenchmarkRun]:
        agents = agent_configs or self.settings.agents
        scenario_names = [s["name"] for s in ScenarioRegistry.list_scenarios()]
        return self.run_scenarios(scenario_names, agents, parallel=parallel)

    def compare_agents(self, scenario_name: str,
                       agent_configs: List[AgentConfig]) -> dict:
        results = {}
        for agent_cfg in agent_configs:
            s = ScenarioRegistry.get_instance(scenario_name)
            if s:
                run = self.run_scenario(s, agent_cfg)
                results[agent_cfg.name] = run
        return self._build_comparison(results)

    def _build_comparison(self, runs: Dict[str, BenchmarkRun]) -> dict:
        comparison = {}
        for name, run in runs.items():
            if run.scenario_result:
                comparison[name] = {
                    "success": run.scenario_result.success,
                    "duration_ms": run.scenario_result.duration_ms,
                    "metrics": run.scenario_result.metrics,
                    "errors": run.scenario_result.errors,
                }
        return {
            "scenario": next(iter(runs.values())).scenario_name if runs else "",
            "agents": comparison,
        }

    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        return self._runs.get(run_id)

    def subscribe(self, listener: Callable):
        self._listeners.append(listener)

    def _save_run(self, run: BenchmarkRun):
        try:
            report = BenchmarkReport(
                title=f"Benchmark: {run.agent_name} / {run.scenario_name}",
                run_id=run.run_id,
                agent_name=run.agent_name,
                scenario_name=run.scenario_name,
                success=run.status == "success",
                total_duration_ms=(run.end_time - run.start_time) * 1000 if run.end_time else 0,
                summary=run.scenario_result.metrics if run.scenario_result else {},
                metrics=run.scenario_result.metrics if run.scenario_result else {},
                spans_count=len(run.tracer.get_spans(run.run_id)),
                events_count=len(run.event_log.get_events()),
                tool_calls_count=run.scenario_result.tool_calls_count if run.scenario_result else 0,
                retries_count=run.scenario_result.repair_attempts if run.scenario_result else 0,
                errors_count=len(run.scenario_result.errors) if run.scenario_result else 0,
                hallucinations_detected=run.scenario_result.hallucination_count if run.scenario_result else 0,
                diff_files_changed=run.scenario_result.files_modified if run.scenario_result else 0,
                tags={"status": run.status},
            )

            self.store.save_run(run.run_id, report.to_dict())

            trace_data = {
                "trace_id": run.run_id,
                "agent": run.agent_name,
                "scenario": run.scenario_name,
                "spans": [s.to_dict() for s in run.tracer.get_spans(run.run_id)],
                "events": [e.to_dict() for e in run.event_log.get_events()],
                "timeline": run.timeline.to_dict(),
                "agent_result": run.agent_result.to_dict() if run.agent_result else {},
                "scenario_result": run.scenario_result.to_dict() if run.scenario_result else {},
            }
            self.store.save_trace(run.run_id, trace_data)

            if self.settings.benchmark.record_thoughts:
                thought_data = run.thought_recorder.export_trace()
                self.store.save_cognitive_trace(run.run_id, thought_data)

        except Exception as e:
            print(f"Warning: Failed to save run {run.run_id}: {e}")

    def _notify_listeners(self, run: BenchmarkRun):
        for listener in self._listeners:
            try:
                listener(run)
            except Exception:
                pass

    def generate_report(self, run_id: str) -> Optional[str]:
        data = self.store.load_run(run_id)
        if not data:
            return None
        report = BenchmarkReport(**data)
        return StructuredOutput.report_to_markdown(report)

    def generate_comparison_report(self, run_ids: List[str]) -> str:
        lines = ["# Agent Comparison Report", ""]
        for rid in run_ids:
            data = self.store.load_run(rid)
            if data:
                r = BenchmarkReport(**data)
                lines.append(f"## {r.agent_name} / {r.scenario_name}")
                lines.append(f"- **Success**: {r.success}")
                lines.append(f"- **Duration**: {r.total_duration_ms:.1f}ms")
                lines.append(f"- **Tool Calls**: {r.tool_calls_count}")
                lines.append(f"- **Errors**: {r.errors_count}")
                lines.append(f"- **Hallucinations**: {r.hallucinations_detected}")
                lines.append("")
        return "\n".join(lines)
