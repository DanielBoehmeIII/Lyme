from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class LongHorizonTodoAppScenario(BenchmarkScenario):
    @property
    def name(self): return "long-horizon-todo-app"

    @property
    def category(self): return "long_horizon"

    @property
    def description(self): return "Build a complete todo app with multiple files and features"

    @property
    def difficulty(self): return 0.7

    @property
    def timeout_s(self): return 300

    def setup(self, work_dir: Path) -> dict:
        # Empty project directory
        (work_dir / "requirements.txt").write_text("# TODO app\n")
        return {"file_count": 1}

    def task_prompt(self, context: dict) -> str:
        return ("Build a complete command-line todo application with these features:\n"
                "1. Add, list, complete, and delete todos\n"
                "2. Persistent storage (JSON file)\n"
                "3. Due dates and priority levels\n"
                "4. Filter todos by status/priority\n"
                "5. Search functionality\n"
                "6. Statistics (total, completed, overdue)\n"
                "7. Tags/categories for todos\n"
                "Structure: main.py as entry point, separate modules for storage, models, and CLI.\n"
                "Use type hints throughout. Handle errors gracefully.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        features = []
        errors = []

        all_files = list(work_dir.rglob("*.py"))
        result.files_created = len(all_files)

        if not all_files:
            errors.append("No Python files created")
            result.success = False
            return result

        all_content = ""
        for f in all_files:
            all_content += f.read_text() + "\n"

        feature_checks = {
            "add_todo": "add" in all_content.lower(),
            "list_todos": "list" in all_content.lower() or "show" in all_content.lower(),
            "complete_todo": "complete" in all_content.lower() or "done" in all_content.lower(),
            "delete_todo": "delete" in all_content.lower() or "remove" in all_content.lower(),
            "persistent_storage": "json" in all_content.lower() or "pickle" in all_content.lower(),
            "due_dates": "due" in all_content.lower() or "date" in all_content.lower(),
            "priority": "priority" in all_content.lower() or "high" in all_content.lower(),
            "filter": "filter" in all_content.lower(),
            "search": "search" in all_content.lower() or "find" in all_content.lower(),
            "statistics": "stat" in all_content.lower() or "count" in all_content.lower(),
            "tags": "tag" in all_content.lower() or "categor" in all_content.lower(),
            "error_handling": "except" in all_content or "try" in all_content,
            "type_hints": "->" in all_content or ": int" in all_content or ": str" in all_content,
        }

        feature_count = sum(1 for v in feature_checks.values() if v)
        result.success = feature_count >= 7

        for name, present in feature_checks.items():
            result.metrics[f"feature_{name}"] = float(present)

        result.metrics["features_implemented"] = float(feature_count)
        result.metrics["features_total"] = float(len(feature_checks))
        result.metrics["files_created"] = float(len(all_files))
        result.metrics["completion_ratio"] = feature_count / len(feature_checks)

        try:
            for f in all_files:
                compile(f.read_text(), str(f), "exec")
            result.metrics["all_files_compile"] = 1.0
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            result.metrics["all_files_compile"] = 0.0

        result.errors = errors
        return result
