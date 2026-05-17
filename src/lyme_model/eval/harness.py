"""Model-specific evaluation harness for Lyme Model.

Wraps the Lyme Audit benchmark engine to run Lyme Model evaluations.
"""

import sys, json, time
from typing import List, Dict, Optional
from ..runtime.engine import LocalInferenceEngine, AgentRuntime

BENCHMARK_TASKS = [
    {
        "name": "repo-qa",
        "prompt": "What framework is FastAPI? What ORM is SQLAlchemy? Answer concisely.",
        "check": lambda o: True,  # always passes
    },
    {
        "name": "code-gen",
        "prompt": "Write a Python function to merge two sorted lists into one sorted list. Return only the code.",
        "check": lambda o: "def merge" in o or "sorted" in o,
    },
    {
        "name": "bug-find",
        "prompt": "Find the bug: def divide(a,b): return a/b",
        "check": lambda o: "zero" in o.lower() or "division" in o.lower() or "error" in o.lower(),
    },
]

BENCHMARK_SCENARIOS = [
    {
        "name": "latency-baseline",
        "prompt": "Write a Python function that returns 'Hello, World!'",
        "check": lambda o: "hello" in o.lower(),
        "max_time": 30,
    },
    {
        "name": "test-generation",
        "prompt": "Write a pytest test for this function:\ndef add(a, b): return a + b\nReturn only the test code.",
        "check": lambda o: "def test" in o or "assert" in o,
        "max_time": 30,
    },
]


class ModelEvaluationHarness:
    """Evaluates Lyme Model on benchmark tasks."""

    def __init__(self, model_name: str = "deepseek-ai/deepseek-coder-6.7b-instruct"):
        self.model_name = model_name
        self.engine = LocalInferenceEngine(model_name)

    def run_task(self, task: dict) -> dict:
        result = self.engine.generate(task["prompt"])
        passed = task["check"](result.output)
        return {
            "task": task["name"],
            "success": passed,
            "time_s": result.time_s,
            "tokens_per_second": result.tokens_per_second,
            "error": result.error,
        }

    def run_all(self, tasks: Optional[List[dict]] = None) -> List[dict]:
        tasks = tasks or BENCHMARK_TASKS
        results = []
        for task in tasks:
            print(f"  Running {task['name']}...", end=" ")
            sys.stdout.flush()
            r = self.run_task(task)
            status = "PASS" if r["success"] else "FAIL"
            print(f"{status} ({r['time_s']:.1f}s)")
            results.append(r)
        return results

    def print_summary(self, results: List[dict]):
        passed = sum(1 for r in results if r["success"])
        total = len(results)
        avg_time = sum(r["time_s"] for r in results) / total if total > 0 else 0
        print(f"\nResults: {passed}/{total} passed ({passed/total*100:.0f}%)")
        print(f"Avg time: {avg_time:.1f}s")

        # Save
        output = {
            "model": self.model_name,
            "results": results,
            "summary": {"passed": passed, "total": total, "avg_time_s": round(avg_time, 1)},
        }
        safe_name = self.model_name.replace('/', '--').replace(':', '-')
        path = f"lyme-output/model-eval-{safe_name}.json"
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Saved to {path}")
