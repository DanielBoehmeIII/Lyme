from typing import List, Dict, Any, Optional, Callable
from ..telemetry import Tracer, EventLog, EventType
from ..cognition import ThoughtRecorder


class AgentWrapper:
    def __init__(self, tracer: Tracer = None, event_log: EventLog = None,
                 thought_recorder: ThoughtRecorder = None):
        self.tracer = tracer or Tracer()
        self.event_log = event_log or EventLog()
        self.thought_recorder = thought_recorder or ThoughtRecorder()

    def wrap_tool_call(self, tool_name: str, args: dict,
                       func: Callable) -> Any:
        with self.tracer.span(f"tool:{tool_name}", category="tool",
                              metadata={"args": args}):
            self.event_log.emit(
                EventType.TOOL_CALL,
                {"tool": tool_name, "args": args},
                source="agent_wrapper",
            )

            self.thought_recorder.record_tool_selection(
                tool_name,
                rationale=f"Calling {tool_name}",
            )

            try:
                result = func(**args)
                self.event_log.emit(
                    EventType.TOOL_RESULT,
                    {"tool": tool_name, "result_preview": str(result)[:200]},
                    source="agent_wrapper",
                )
                return result
            except Exception as e:
                self.event_log.emit(
                    EventType.ERROR,
                    {"tool": tool_name, "error": str(e)},
                    severity="error", source="agent_wrapper",
                )
                self.thought_recorder.record_error(
                    f"Tool {tool_name} failed: {e}",
                    {"tool": tool_name, "args": args},
                )
                raise

    def wrap_file_read(self, path: str) -> str:
        with self.tracer.span(f"read:{path}", category="file"):
            self.event_log.emit(
                EventType.FILE_READ,
                {"path": path},
                source="agent_wrapper",
            )
            self.thought_recorder.record_navigation("read", path)
            return path

    def wrap_file_write(self, path: str, content: str) -> None:
        with self.tracer.span(f"write:{path}", category="file"):
            self.event_log.emit(
                EventType.FILE_WRITE,
                {"path": path, "size": len(content)},
                source="agent_wrapper",
            )
            self.thought_recorder.record_navigation("write", path)

    def wrap_file_edit(self, path: str, old: str, new: str) -> None:
        with self.tracer.span(f"edit:{path}", category="file"):
            self.event_log.emit(
                EventType.FILE_EDIT,
                {"path": path, "old_size": len(old), "new_size": len(new)},
                source="agent_wrapper",
            )

    def wrap_search(self, query: str, results: int) -> None:
        self.event_log.emit(
            EventType.SEARCH,
            {"query": query, "results_count": results},
            source="agent_wrapper",
        )
        self.thought_recorder.record_navigation("search", query)

    def wrap_decision(self, question: str, options: list, chosen: str,
                      rationale: str = "", confidence: float = 1.0) -> None:
        self.thought_recorder.record_decision(
            question, options, chosen, rationale, confidence
        )
