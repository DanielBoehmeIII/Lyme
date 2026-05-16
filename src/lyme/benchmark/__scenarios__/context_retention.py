from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class ContextRetentionBaselineScenario(BenchmarkScenario):
    @property
    def name(self): return "context-retention-baseline"

    @property
    def category(self): return "context_retention"

    @property
    def description(self): return "Measure ability to retain constraints across a single task"

    @property
    def difficulty(self): return 0.4

    def setup(self, work_dir: Path) -> dict:
        (work_dir / "api.py").write_text(
            "from dataclasses import dataclass\nfrom typing import Optional\n\n"
            "@dataclass\nclass User:\n    id: int\n    name: str\n    email: str\n\n"
            "@dataclass\nclass Product:\n    id: int\n    name: str\n    price: float\n\n"
            "users: list[User] = []\nproducts: list[Product] = []\n"
        )
        return {"file_count": 1, "constraints": ["do not modify User dataclass", "do not modify Product dataclass"]}

    def task_prompt(self, context: dict) -> str:
        return ("Extend api.py to add CRUD functions for User and Product. "
                "CRITICAL: Do NOT modify the User or Product dataclass definitions. "
                "Add functions only. Use type hints throughout.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "api.py"
        if source.exists():
            content = source.read_text()
            dataclass_lines = [l for l in content.split("\n") if "class User" in l or "class Product" in l]
            has_create = "def create" in content or "def add" in content or "def post" in content
            has_read = "def get" in content or "def read" in content or "def find" in content
            has_update = "def update" in content
            has_delete = "def delete" in content or "def remove" in content

            result.success = has_create and has_read and (has_update or has_delete)
            result.metrics["create"] = float(has_create)
            result.metrics["read"] = float(has_read)
            result.metrics["update"] = float(has_update)
            result.metrics["delete"] = float(has_delete)

            user_class = [l for l in content.split("\n") if "@dataclass" in l or "class User" in l]
            product_class = [l for l in content.split("\n") if "@dataclass" in l or "class Product" in l]

            if len(user_class) > 2:
                result.errors.append("User dataclass modified")
                result.metrics["constraint_violation"] = 1.0
            elif len(product_class) > 2:
                result.errors.append("Product dataclass modified")
                result.metrics["constraint_violation"] = 1.0
            else:
                result.metrics["constraint_violation"] = 0.0
        return result


@ScenarioRegistry.register
class ContextRetentionMultiConstraintScenario(BenchmarkScenario):
    @property
    def name(self): return "context-retention-multi-constraint"

    @property
    def category(self): return "context_retention"

    @property
    def description(self): return "Measure retention of multiple constraints across multiple files"

    @property
    def difficulty(self): return 0.7

    def setup(self, work_dir: Path) -> dict:
        files = {
            "models/user.py": "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    id: int\n    username: str\n    email: str\n    role: str = 'user'\n",
            "models/product.py": "from dataclasses import dataclass\n\n@dataclass\nclass Product:\n    id: int\n    name: str\n    price: float\n    stock: int = 0\n",
            "models/order.py": "from dataclasses import dataclass\nfrom datetime import datetime\n\n@dataclass\nclass Order:\n    id: int\n    user_id: int\n    product_ids: list[int]\n    total: float\n    created_at: datetime = None\n",
        }
        for path, content in files.items():
            p = work_dir / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

        (work_dir / "constraints.md").write_text(
            "ARCHITECTURAL CONSTRAINTS:\n"
            "1. NEVER modify model files (models/user.py, models/product.py, models/order.py)\n"
            "2. All business logic goes in services/\n"
            "3. All API endpoints go in routes/\n"
            "4. Use repository pattern for data access\n"
            "5. All functions must have type hints\n"
            "6. Max line length is 100 characters\n"
            "7. Use pathlib for file paths\n"
            "8. Never use bare except clauses\n"
        )
        return {"file_count": 4, "constraint_count": 8}

    def task_prompt(self, context: dict) -> str:
        return ("Read the constraints.md file carefully. Then implement a complete order processing system:\n"
                "- Create services/order_service.py with create_order, get_order, cancel_order\n"
                "- Create routes/order_routes.py with corresponding HTTP-like handlers\n"
                "- Create services/user_service.py with get_user, update_user\n"
                "- Do NOT modify any files in models/\n"
                "- Follow ALL constraints in constraints.md\n"
                "- All functions must have type hints")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        result.metrics["constraint_count"] = 8.0

        models_modified = 0
        for model_file in ["models/user.py", "models/product.py", "models/order.py"]:
            p = work_dir / model_file
            if p.exists():
                content = p.read_text()
                lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
                if len(lines) > 4:
                    models_modified += 1

        violations = 0
        if models_modified > 0:
            result.errors.append(f"{models_modified} model files modified")
            violations += models_modified

        services = ["services/order_service.py", "services/user_service.py"]
        routes = ["routes/order_routes.py"]

        created_files = []
        for f in services + routes:
            p = work_dir / f
            if p.exists():
                created_files.append(f)

        result.files_created = len(created_files)
        result.metrics["services_created"] = sum(1 for f in created_files if "services" in f)
        result.metrics["routes_created"] = sum(1 for f in created_files if "routes" in f)

        all_have_types = True
        for f in created_files:
            p = work_dir / f
            content = p.read_text()
            func_lines = [l for l in content.split("\n") if l.strip().startswith("def ")]
            for func in func_lines:
                if "->" not in func:
                    all_have_types = False
                    violations += 0.5

        result.success = len(created_files) >= 2 and violations <= 1
        result.metrics["constraint_violations"] = float(violations)
        result.metrics["type_hints_complete"] = float(all_have_types)

        if not result.success:
            result.errors.append(f"Constraint violations: {violations}, Created files: {len(created_files)}")
        return result
