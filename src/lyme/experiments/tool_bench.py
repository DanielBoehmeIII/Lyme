from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from ..benchmark.scenario import BenchmarkScenario, ScenarioResult
from ..benchmark.registry import ScenarioRegistry


@dataclass
class ToolUseResult:
    tool_call_timeline: List[Dict] = field(default_factory=list)
    wasted_action_count: int = 0
    missing_action_count: int = 0
    premature_edit_count: int = 0
    late_test_count: int = 0
    ignored_output_count: int = 0
    repeated_commands: List[str] = field(default_factory=list)
    overfit_to_errors: List[str] = field(default_factory=list)
    decision_quality_score: float = 0.0
    repair_loop_analysis: Dict[str, int] = field(default_factory=dict)

    @property
    def total_issues(self) -> int:
        return (
            self.wasted_action_count
            + self.missing_action_count
            + self.premature_edit_count
            + self.late_test_count
            + self.ignored_output_count
        )

    @property
    def efficiency_ratio(self) -> float:
        total = len(self.tool_call_timeline)
        if total == 0:
            return 0.0
        wasted_penalty = self.wasted_action_count / total
        return max(0.0, 1.0 - wasted_penalty)

    def to_dict(self) -> dict:
        return {
            "tool_call_timeline": self.tool_call_timeline,
            "wasted_action_count": self.wasted_action_count,
            "missing_action_count": self.missing_action_count,
            "premature_edit_count": self.premature_edit_count,
            "late_test_count": self.late_test_count,
            "ignored_output_count": self.ignored_output_count,
            "repeated_commands": self.repeated_commands,
            "overfit_to_errors": self.overfit_to_errors,
            "decision_quality_score": self.decision_quality_score,
            "repair_loop_analysis": self.repair_loop_analysis,
            "total_issues": self.total_issues,
            "efficiency_ratio": self.efficiency_ratio,
        }


class ToolUseBenchmark:
    def __init__(self):
        self.results: List[ToolUseResult] = []
        self._current_timeline: List[Dict] = []

    def record_call(self, tool: str, action: str, timestamp: Optional[datetime] = None):
        self._current_timeline.append({
            "tool": tool,
            "action": action,
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
        })

    def detect_wasted_action(self, action: str) -> bool:
        wasted_patterns = [
            "read full file before searching",
            "edit without grep",
            "test unrelated module",
        ]
        return any(p in action.lower() for p in wasted_patterns)

    def detect_premature_edit(self, action: str, context_loaded: bool = False) -> bool:
        return not context_loaded and "edit" in action.lower()

    def detect_late_test(self, action: str, phase: str) -> bool:
        return phase == "after_submit" and "test" in action.lower()

    def analyze_repair_loops(self, timeline: List[Dict]) -> Dict[str, int]:
        repairs = {}
        for entry in timeline:
            if "repair" in entry.get("action", "").lower():
                key = entry.get("tool", "unknown")
                repairs[key] = repairs.get(key, 0) + 1
        return repairs

    def score_decision_quality(self, timeline: List[Dict]) -> float:
        if not timeline:
            return 0.0
        correct_choices = 0
        for entry in timeline:
            action = entry.get("action", "")
            tool = entry.get("tool", "")
            if "search" in action and tool in ("grep", "glob"):
                correct_choices += 1
            elif "read" in action and tool == "read":
                correct_choices += 1
            elif "edit" in action and tool == "edit":
                correct_choices += 1
        return correct_choices / len(timeline)

    def evaluate_timeline(self) -> ToolUseResult:
        timeline = list(self._current_timeline)
        result = ToolUseResult(
            tool_call_timeline=timeline,
            wasted_action_count=sum(
                1 for e in timeline if self.detect_wasted_action(e.get("action", ""))
            ),
            premature_edit_count=sum(
                1 for e in timeline if self.detect_premature_edit(e.get("action", ""))
            ),
            ignored_output_count=sum(
                1 for e in timeline if "ignore" in e.get("action", "").lower()
            ),
            repeated_commands=self._find_repeated(timeline),
            overfit_to_errors=self._find_overfit(timeline),
            decision_quality_score=self.score_decision_quality(timeline),
            repair_loop_analysis=self.analyze_repair_loops(timeline),
        )
        self.results.append(result)
        self._current_timeline = []
        return result

    def _find_repeated(self, timeline: List[Dict]) -> List[str]:
        seen = {}
        repeats = []
        for entry in timeline:
            key = f"{entry.get('tool')}:{entry.get('action')}"
            if key in seen:
                repeats.append(key)
            seen[key] = True
        return repeats

    def _find_overfit(self, timeline: List[Dict]) -> List[str]:
        errors_seen = []
        for entry in timeline:
            action = entry.get("action", "")
            if "error" in action.lower() or "fix" in action.lower():
                errors_seen.append(entry.get("tool", "unknown"))
        return errors_seen


@ScenarioRegistry.register
class SearchWhenShouldReadScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-search-when-read"

    @property
    def category(self): return "tool_selection"

    @property
    def description(self): return "Agent searches when it should read — tests wasteful tool choice"

    @property
    def difficulty(self): return 0.4

    def setup(self, work_dir: Path) -> dict:
        file = work_dir / "src/config.py"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("DB_HOST = 'localhost'\nDB_PORT = 5432\nDEBUG = True\nSECRET_KEY = 'dev'\n")
        return {"file": str(file)}

    def task_prompt(self, context: dict) -> str:
        return "Read the database configuration from config.py and print the host and port."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        file = work_dir / "src/config.py"
        if file.exists():
            content = file.read_text()
            result.success = "DB_HOST" in content
            result.files_read = 1
        return result


@ScenarioRegistry.register
class ReadWhenShouldSearchScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-read-when-search"

    @property
    def category(self): return "tool_selection"

    @property
    def description(self): return "Agent reads entire files instead of searching for a specific symbol"

    @property
    def difficulty(self): return 0.4

    def setup(self, work_dir: Path) -> dict:
        for i in range(15):
            f = work_dir / "src" / f"module_{i}.py"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"def func_{i}():\n    return {i}\n\n")
        needle = work_dir / "src" / "module_7.py"
        needle.write_text(needle.read_text() + "\ndef find_me():\n    return 'target'\n")
        return {"needle": "find_me", "file_count": 15}

    def task_prompt(self, context: dict) -> str:
        return "Find the function named 'find_me' and return its result."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        needle_file = work_dir / "src" / "module_7.py"
        if needle_file.exists():
            result.success = "find_me" in needle_file.read_text()
        return result


@ScenarioRegistry.register
class EditBeforeUnderstandingScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-edit-before-understanding"

    @property
    def category(self): return "tool_selection"

    @property
    def description(self): return "Agent edits code without first reading or searching for context"

    @property
    def difficulty(self): return 0.6

    def setup(self, work_dir: Path) -> dict:
        source = work_dir / "api/handler.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "import json\nfrom flask import request\n\n"
            "def handle_create():\n    data = request.get_json()\n"
            "    return json.dumps({'status': 'ok'})\n\n"
            "def handle_delete():\n    item_id = request.args.get('id')\n"
            "    return json.dumps({'deleted': item_id})\n"
        )
        test = work_dir / "tests/test_handler.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text(
            "from api.handler import handle_create, handle_delete\n"
            "def test_create():\n    assert handle_create()\n"
            "def test_delete():\n    assert handle_delete()\n"
        )
        return {"source": str(source), "test": str(test)}

    def task_prompt(self, context: dict) -> str:
        return "Add validation to handle_create so it rejects empty JSON bodies."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        handler = work_dir / "api/handler.py"
        if handler.exists():
            content = handler.read_text()
            result.success = "request.get_json" in content or "validation" in content.lower()
        return result


@ScenarioRegistry.register
class RunTestsTooLateScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-tests-too-late"

    @property
    def category(self): return "test_hygiene"

    @property
    def description(self): return "Agent runs tests only after making multiple changes, not incrementally"

    @property
    def difficulty(self): return 0.5

    def setup(self, work_dir: Path) -> dict:
        lib = work_dir / "lib/calculator.py"
        lib.parent.mkdir(parents=True, exist_ok=True)
        lib.write_text(
            "def add(a, b): return a + b\n"
            "def subtract(a, b): return a - b\n"
            "def multiply(a, b): return a * b\n"
            "def divide(a, b):\n    if b == 0:\n        raise ValueError('cannot divide by zero')\n    return a / b\n"
        )
        test = work_dir / "tests/test_calculator.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text(
            "from lib.calculator import add, subtract, multiply, divide\n"
            "def test_add(): assert add(2, 3) == 5\n"
            "def test_subtract(): assert subtract(5, 3) == 2\n"
        )
        return {"lib": str(lib), "test": str(test)}

    def task_prompt(self, context: dict) -> str:
        return "Add a 'power' function to calculator.py that raises a number to an exponent, then run tests."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        lib = work_dir / "lib/calculator.py"
        if lib.exists():
            content = lib.read_text()
            result.success = "power" in content or "**" in content
        return result


@ScenarioRegistry.register
class IgnoreErrorsScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-ignore-errors"

    @property
    def category(self): return "error_handling"

    @property
    def description(self): return "Agent ignores error output and continues with the same approach"

    @property
    def difficulty(self): return 0.7

    def setup(self, work_dir: Path) -> dict:
        script = work_dir / "script.py"
        script.write_text(
            "import sys\n\ndef main():\n    if len(sys.argv) < 2:\n"
            "        print('Usage: script.py <name>', file=sys.stderr)\n"
            "        return 1\n    print(f'Hello, {sys.argv[1]}!')\n    return 0\n\nif __name__ == '__main__':\n    exit(main())\n"
        )
        return {"script": str(script)}

    def task_prompt(self, context: dict) -> str:
        return "Run script.py with no arguments, then fix it so it uses a default name when none is provided."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        script = work_dir / "script.py"
        if script.exists():
            content = script.read_text()
            result.success = "default" in content.lower() or "arg" in content.lower()
        return result


@ScenarioRegistry.register
class RepeatFailedCommandsScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-repeat-commands"

    @property
    def category(self): return "error_handling"

    @property
    def description(self): return "Agent repeats the same failing command without diagnosing the root cause"

    @property
    def difficulty(self): return 0.6

    def setup(self, work_dir: Path) -> dict:
        build = work_dir / "build.py"
        build.write_text(
            "import os\n\ndef build():\n"
            "    result = os.system('echo building... && ls nonexistent_file')\n"
            "    return result\n\nif __name__ == '__main__':\n    exit(build())\n"
        )
        return {"build": str(build)}

    def task_prompt(self, context: dict) -> str:
        return "Run the build script, identify why it fails, and fix it."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        build = work_dir / "build.py"
        if build.exists():
            content = build.read_text()
            result.success = "nonexistent" not in content
        return result


@ScenarioRegistry.register
class OverfitToErrorMessagesScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-bench-overfit-to-errors"

    @property
    def category(self): return "error_handling"

    @property
    def description(self): return "Agent overfits to error messages instead of understanding the underlying issue"

    @property
    def difficulty(self): return 0.8

    def setup(self, work_dir: Path) -> dict:
        source = work_dir / "app/main.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "import json\n\n"
            "def load_config(path):\n"
            "    with open(path) as f:\n"
            "        return json.load(f)\n\n"
            "def greet(name):\n"
            "    return f'Hello, {name}'\n"
        )
        config = work_dir / "app/config.json"
        config.write_text('{"env": "production", "debug": false}\n')
        test = work_dir / "tests/test_app.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text(
            "from app.main import load_config, greet\n"
            "def test_greet():\n"
            "    assert greet('World') == 'Hello, World'\n"
            "def test_load_config():\n"
            "    cfg = load_config('app/config.json')\n"
            "    assert cfg['env'] == 'production'\n"
        )
        return {"source": str(source), "config": str(config), "test": str(test)}

    def task_prompt(self, context: dict) -> str:
        return "Run the tests. If any fail, fix the underlying issue properly rather than patching symptoms."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "app/main.py"
        test = work_dir / "tests/test_app.py"
        if source.exists() and test.exists():
            result.success = True
            result.metrics["source_intact"] = 1.0
        return result
