from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class ToolCallAccuracyScenario(BenchmarkScenario):
    @property
    def name(self): return "tool-call-accuracy"

    @property
    def category(self): return "tool_call_overhead"

    @property
    def description(self): return "Measure accuracy of tool call parameter construction"

    @property
    def difficulty(self): return 0.5

    def setup(self, work_dir: Path) -> dict:
        files = {
            "src/config.py": "DEFAULT_PORT = 8080\nDEFAULT_HOST = 'localhost'\n",
            "src/database.py": "class Database:\n    def connect(self, host, port): pass\n    def query(self, sql): pass\n",
            "src/server.py": "class Server:\n    def __init__(self, host, port): pass\n    def start(self): pass\n",
            "src/utils.py": "def validate_port(p): return 0 < p < 65536\ndef validate_host(h): return len(h) > 0\n",
        }
        for path, content in files.items():
            full_path = work_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        return {"file_count": len(files), "structure": "multi-module"}

    def task_prompt(self, context: dict) -> str:
        return ("Refactor the src/ package to use a single config object "
                "that's shared across modules. Create src/config_manager.py "
                "with a Config class, update database.py and server.py to use it, "
                "and ensure all existing tests would still pass.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        cm = work_dir / "src/config_manager.py"
        config = work_dir / "src/config.py"
        db = work_dir / "src/database.py"
        server = work_dir / "src/server.py"

        if cm.exists():
            content = cm.read_text()
            result.success = "class Config" in content or "Config" in content
            result.files_created = 1

        if db.exists():
            db_content = db.read_text()
            if "Config" in db_content:
                result.metrics["database_updated"] = 1.0

        if server.exists():
            srv_content = server.read_text()
            if "Config" in srv_content:
                result.metrics["server_updated"] = 1.0

        if not result.success:
            result.errors.append("config_manager.py not created or missing Config class")
        return result


@ScenarioRegistry.register
class SearchEfficiencyScenario(BenchmarkScenario):
    @property
    def name(self): return "search-efficiency"

    @property
    def category(self): return "file_navigation"

    @property
    def description(self): return "Measure efficiency of searching and understanding a codebase"

    @property
    def difficulty(self): return 0.6

    def setup(self, work_dir: Path) -> dict:
        import random
        random.seed(42)
        (work_dir / "src").mkdir(exist_ok=True)
        (work_dir / "tests").mkdir(exist_ok=True)
        (work_dir / "docs").mkdir(exist_ok=True)

        for i in range(20):
            (work_dir / "src" / f"component_{i}.py").write_text(
                f"# Component {i}\ndef process_{i}(data):\n    return data * {i}\n"
            )

        (work_dir / "src" / "payment_processor.py").write_text(
            "def charge_user(user_id, amount):\n    return {'success': True, 'charge_id': 'ch_123'}\n"
        )
        (work_dir / "src" / "email_service.py").write_text(
            "def send_welcome_email(email): pass\ndef send_receipt(email, amount): pass\n"
        )
        (work_dir / "src" / "user_manager.py").write_text(
            "def get_user(user_id): return {'id': user_id, 'email': 'a@b.com'}\n"
            "def update_user(user_id, data): return True\n"
        )

        return {"file_count": 23, "needle_functions": ["charge_user", "send_welcome_email"]}

    def task_prompt(self, context: dict) -> str:
        return ("Find the payment processing code and the email service code. "
                "Create a new file `checkout_flow.py` that imports and uses both: "
                "charge the user, then send a receipt email. Handle errors.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        checkout = work_dir / "checkout_flow.py"
        if checkout.exists():
            content = checkout.read_text()
            has_payment = "charge_user" in content or "payment" in content.lower()
            has_email = "send_" in content or "email" in content.lower()
            result.success = has_payment and has_email
            result.metrics["payment_found"] = float(has_payment)
            result.metrics["email_found"] = float(has_email)
        else:
            result.errors.append("checkout_flow.py not created")
        return result
