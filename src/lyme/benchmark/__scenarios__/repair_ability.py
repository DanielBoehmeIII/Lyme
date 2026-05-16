from pathlib import Path
from ..scenario import BenchmarkScenario, ScenarioResult
from ..registry import ScenarioRegistry


@ScenarioRegistry.register
class RepairSyntaxErrorScenario(BenchmarkScenario):
    @property
    def name(self): return "repair-syntax-error"

    @property
    def category(self): return "repair_ability"

    @property
    def description(self): return "Measure ability to fix syntax errors in code"

    @property
    def difficulty(self): return 0.3

    def setup(self, work_dir: Path) -> dict:
        (work_dir / "broken.py").write_text(
            "def calculate_total(items)\n"
            "    total = 0\n"
            "    for item in items\n"
            "        total += item['price']\n"
            "    return total\n\n"
            "def apply_discount(total, discount)\n"
            "    if discount > 0\n"
            "        return total * (1 - discount)\n"
            "    else\n"
            "        return total\n"
        )
        return {"file_count": 1, "errors": ["missing colons", "syntax errors"]}

    def task_prompt(self, context: dict) -> str:
        return ("Fix all syntax errors in broken.py. The file has missing colons. "
                "Do not change the logic, only fix syntax.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "broken.py"
        if source.exists():
            content = source.read_text()
            try:
                compile(content, "broken.py", "exec")
                result.success = True
                result.metrics["compiles"] = 1.0
            except SyntaxError as e:
                result.success = False
                result.metrics["compiles"] = 0.0
                result.errors.append(f"Still has syntax error: {e}")
        else:
            result.errors.append("broken.py not found")
        return result


@ScenarioRegistry.register
class RepairLogicErrorScenario(BenchmarkScenario):
    @property
    def name(self): return "repair-logic-error"

    @property
    def category(self): return "repair_ability"

    @property
    def description(self): return "Measure ability to fix logical errors with test feedback"

    @property
    def difficulty(self): return 0.6

    def setup(self, work_dir: Path) -> dict:
        (work_dir / "calculator.py").write_text(
            "def add(a, b): return a + b\ndef subtract(a, b): return a - b\n"
            "def multiply(a, b): return a * b\n"
            "def divide(a, b): return a / b  # BUG: no zero division check\n"
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 0  # BUG: should be 1\n"
            "    return n * factorial(n - 1)\n"
            "def fibonacci(n):\n"
            "    if n <= 0:\n"
            "        return []\n"
            "    if n == 1:\n"
            "        return [0]\n"
            "    if n == 2:\n"
            "        return [0, 1, 1]  # BUG: should be [0, 1]\n"
            "    result = [0, 1]\n"
            "    for i in range(2, n):\n"
            "        result.append(result[i-1] + result[i-2])\n"
            "    return result\n"
        )
        (work_dir / "test_calculator.py").write_text(
            "from calculator import add, subtract, multiply, divide, factorial, fibonacci\n\n"
            "def test_add(): assert add(2, 3) == 5\n"
            "def test_subtract(): assert subtract(5, 3) == 2\n"
            "def test_multiply(): assert multiply(4, 3) == 12\n"
            "def test_divide(): assert divide(10, 2) == 5.0\n"
            "def test_divide_by_zero():\n"
            "    try:\n"
            "        divide(1, 0)\n"
            "        assert False, 'Should raise ZeroDivisionError'\n"
            "    except ZeroDivisionError:\n"
            "        pass\n"
            "def test_factorial():\n"
            "    assert factorial(0) == 1\n"
            "    assert factorial(5) == 120\n"
            "def test_fibonacci():\n"
            "    assert fibonacci(0) == []\n"
            "    assert fibonacci(1) == [0]\n"
            "    assert fibonacci(5) == [0, 1, 1, 2, 3]\n"
        )
        return {"file_count": 2, "bugs": ["divide by zero", "factorial(0)", "fibonacci(2)"]}

    def task_prompt(self, context: dict) -> str:
        return ("Fix all bugs in calculator.py. Run the tests with 'python test_calculator.py' "
                "to verify. There are exactly 3 bugs. Fix them all.")

    def evaluate(self, work_dir: Path, context: dict) -> ScenarioResult:
        result = ScenarioResult(scenario_name=self.name)
        source = work_dir / "calculator.py"
        if not source.exists():
            result.errors.append("calculator.py not found")
            return result

        content = source.read_text()
        try:
            import sys
            old_path = sys.path.copy()
            sys.path.insert(0, str(work_dir))
            try:
                from calculator import divide, factorial, fibonacci

                tests_passed = 0
                try:
                    assert divide(10, 2) == 5.0
                    tests_passed += 1
                except: pass

                try:
                    divide(1, 0)
                    result.errors.append("divide(1,0) should raise error")
                except ZeroDivisionError:
                    tests_passed += 1

                try:
                    assert factorial(0) == 1
                    tests_passed += 1
                except: pass

                try:
                    assert factorial(5) == 120
                    tests_passed += 1
                except: pass

                try:
                    assert fibonacci(2) == [0, 1]
                    tests_passed += 1
                except: pass

                try:
                    assert fibonacci(5) == [0, 1, 1, 2, 3]
                    tests_passed += 1
                except: pass

                result.success = tests_passed >= 5
                result.metrics["tests_passed"] = float(tests_passed)
                result.metrics["tests_total"] = 6.0
                result.repair_successes = tests_passed
                result.repair_attempts = 1

            finally:
                sys.path = old_path
                if "calculator" in sys.modules:
                    del sys.modules["calculator"]
        except Exception as e:
            result.errors.append(f"Evaluation error: {e}")
        return result
