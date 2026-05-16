import time
from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class LatencyBaselineScenario(BenchmarkScenario):
    @property
    def name(self): return "latency-baseline"

    @property
    def category(self): return "latency"

    @property
    def description(self): return "Measure basic latency: time to respond to a simple coding query"

    @property
    def difficulty(self): return 0.1

    def setup(self, work_dir: Path) -> dict:
        (work_dir / "hello.py").write_text("def greet(name):\n    return f'Hello, {name}!'\n")
        return {"file_count": 1, "complexity": "trivial"}

    def task_prompt(self, context: dict) -> str:
        return "Add a goodbye function to hello.py that says goodbye to a name."

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "hello.py"
        if source.exists():
            content = source.read_text()
            result.success = "goodbye" in content.lower() or "bye" in content.lower()
            result.files_modified = 1 if result.success else 0
            if not result.success:
                result.errors.append("No goodbye function found")
        else:
            result.errors.append("hello.py not found")
        return result


@ScenarioRegistry.register
class LatencyToolCallScenario(BenchmarkScenario):
    @property
    def name(self): return "latency-tool-call"

    @property
    def category(self): return "latency"

    @property
    def description(self): return "Measure tool call latency with multiple sequential reads"

    @property
    def difficulty(self): return 0.3

    def setup(self, work_dir: Path) -> dict:
        for i in range(5):
            (work_dir / f"module_{i}.py").write_text(f"# Module {i}\ndef func_{i}():\n    return {i}\n")
        return {"file_count": 5}

    def task_prompt(self, context: dict) -> str:
        return ("Read all 5 module files (module_0.py through module_4.py) and "
                "create a single main.py that imports and calls each function in sequence.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        main = work_dir / "main.py"
        if main.exists():
            content = main.read_text()
            imports = sum(1 for i in range(5) if f"module_{i}" in content)
            result.success = imports >= 3
            result.files_created = 1
            result.metrics["imports_correct"] = float(imports)
        else:
            result.errors.append("main.py not created")
        return result


@ScenarioRegistry.register
class LatencyTokenThroughputScenario(BenchmarkScenario):
    @property
    def name(self): return "latency-token-throughput"

    @property
    def category(self): return "latency"

    @property
    def description(self): return "Measure token generation throughput on a medium-sized task"

    @property
    def difficulty(self): return 0.4

    def setup(self, work_dir: Path) -> dict:
        (work_dir / "data_processor.py").write_text(
            "import json\nimport csv\nfrom pathlib import Path\n\n"
            "def load_json(path):\n    with open(path) as f:\n        return json.load(f)\n\n"
            "def load_csv(path):\n    with open(path) as f:\n        return list(csv.DictReader(f))\n\n"
            "def process_data(data):\n    return [{'id': i, 'value': d} for i, d in enumerate(data)]\n"
        )
        return {"file_count": 1}

    def task_prompt(self, context: dict) -> str:
        return ("Extend data_processor.py with:\n"
                "1. A function to filter data by key/value\n"
                "2. A function to sort data by a key\n"
                "3. A function to aggregate numeric values\n"
                "4. A function to merge two datasets\n"
                "5. Comprehensive type hints and docstrings\n"
                "6. Error handling for malformed data")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "data_processor.py"
        if source.exists():
            content = source.read_text()
            features = ["filter", "sort", "aggregat", "merge", "type hint", "docstring",
                        "ValueError", "KeyError", "TypeError"]
            found = sum(1 for f in features if f.lower() in content.lower())
            result.success = found >= 5
            result.metrics["features_implemented"] = float(found)
        return result
