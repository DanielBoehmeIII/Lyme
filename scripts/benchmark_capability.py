"""WEEK 56: Local Model Capability Benchmark

Tests raw local model baselines on coding-agent tasks.
DO NOT claim improvement. This establishes the baseline.
"""

import sys, time, json, subprocess, tempfile, os, importlib
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, "src")

# Test tasks that work with raw model prompting
TASKS = [
    {
        "name": "repo-qa",
        "category": "repo_understanding",
        "description": "Answer questions about a repository",
        "prompt": (
            "I have a Python project with these files:\n"
            "- src/main.py (contains FastAPI app with /users and /items endpoints)\n"
            "- src/models.py (contains User and Item SQLAlchemy models)\n"
            "- src/database.py (contains database connection and session)\n"
            "- tests/test_api.py (contains test cases)\n\n"
            "Questions:\n"
            "1. What framework is used for the API?\n"
            "2. What database ORM is used?\n"
            "3. How many models are defined?\n"
            "4. What testing framework is used?\n\n"
            "Answer concisely with what you know."
        ),
        "eval": lambda output: (
            "fastapi" in output.lower() or "FastAPI" in output
        ),
        "expected": "fastapi, sqlalchemy, 2 models, pytest",
    },
    {
        "name": "bug-finding",
        "category": "bug_detection",
        "description": "Find bugs in a code snippet",
        "prompt": (
            "Find all bugs in this Python code:\n\n"
            "```python\n"
            "def calculate_average(numbers):\n"
            "    total = sum(numbers)\n"
            "    return total / len(numbers)\n\n"
            "def get_user(user_id, db):\n"
            "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
            "    return db.execute(query)\n\n"
            "def save_data(data, filename):\n"
            "    f = open(filename, 'w')\n"
            "    f.write(json.dumps(data))\n"
            "    return True\n"
            "```\n\n"
            "List each bug with its line and explanation."
        ),
        "eval": lambda output: (
            "zero" in output.lower() or "division" in output.lower() or "sql" in output.lower()
            or "injection" in output.lower() or "close" in output.lower()
            or "handle" in output.lower()
        ),
        "expected": "division by zero, SQL injection, file not closed",
    },
    {
        "name": "small-edit",
        "category": "code_generation",
        "description": "Write a function to add to an existing module",
        "prompt": (
            "I have a Python module with this function:\n\n"
            "```python\n"
            "def greet(name):\n"
            "    return f'Hello, {name}!'\n"
            "```\n\n"
            "Add a goodbye function that says goodbye to a name. "
            "Return ONLY the new function code, nothing else."
        ),
        "eval": lambda output: (
            "goodbye" in output.lower() or "bye" in output.lower()
        ),
        "expected": "def goodbye(name): return f'Goodbye, {name}!'",
    },
    {
        "name": "test-repair",
        "category": "testing",
        "description": "Fix broken test code",
        "prompt": (
            "This test has bugs. Fix it:\n\n"
            "```python\n"
            "from calculator import add, divide\n\n"
            "def test_add():\n"
            "    result = add(2, 3)\n"
            "    assert result == 6  # BUG: wrong expected value\n\n"
            "def test_divide():\n"
            "    result = divide(10, 0)  # BUG: division by zero\n"
            "    assert result == 2\n"
            "```\n\n"
            "Return the corrected test code."
        ),
        "eval": lambda output: (
            "assert result == 5" in output or "assert result == 5.0" in output
        ),
        "expected": "Fix assert result == 5, handle division by zero",
    },
    {
        "name": "hallucination-resistance",
        "category": "hallucination",
        "description": "Resist fabricating nonexistent API methods",
        "prompt": (
            "This is the only API available:\n\n"
            "```python\n"
            "class CloudClient:\n"
            "    def list_buckets(self):\n"
            "        return ['bucket1', 'bucket2']\n"
            "    def get_object(self, bucket, key):\n"
            "        return {'data': 'content'}\n"
            "```\n\n"
            "Write code to list all buckets and download all objects. "
            "CRITICAL: Only use methods that actually exist in CloudClient. "
            "Do NOT fabricate any methods."
        ),
        "eval": lambda output: (
            "list_buckets" in output and "get_object" in output
            and "list_objects" not in output
        ),
        "expected": "list_buckets + get_object, no fabricated methods",
    },
    {
        "name": "multi-file-reasoning",
        "category": "reasoning",
        "description": "Understand relationships across files",
        "prompt": (
            "Three files in a project:\n\n"
            "FILE auth.py:\n"
            "```python\n"
            "from models import User\n"
            "def login(username, password):\n"
            "    user = User.find_by_username(username)\n"
            "    return user.check_password(password)\n"
            "```\n\n"
            "FILE models.py:\n"
            "```python\n"
            "class User:\n"
            "    def __init__(self, username):\n"
            "        self.username = username\n"
            "        self.role = 'viewer'\n"
            "    @classmethod\n"
            "    def find_by_username(cls, username):\n"
            "        return cls(username)\n"
            "    def check_password(self, password):\n"
            "        return password == 'admin123'\n"
            "```\n\n"
            "FILE routes.py:\n"
            "```python\n"
            "from auth import login\n"
            "def handle_login(request):\n"
            "    result = login(request.username, request.password)\n"
            "    if result:\n"
            "        return 'Welcome admin!'\n"
            "    return 'Access denied'\n"
            "```\n\n"
            "Identify all security issues in this codebase. Be specific."
        ),
        "eval": lambda output: (
            "password" in output.lower() and (
                "hardcoded" in output.lower() or "plain" in output.lower()
                or "security" in output.lower() or "issue" in output.lower()
            )
        ),
        "expected": "Hardcoded password, no encryption, hardcoded admin message",
    },
]


def query_model(model_name: str, prompt: str, timeout: int = 60) -> Optional[str]:
    """Query a model via Ollama and return the output text."""
    try:
        start = time.time()
        proc = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        output = proc.stdout.strip()
        return {"output": output, "time_s": round(elapsed, 2), "tokens": len(output.split())}
    except subprocess.TimeoutExpired:
        return {"output": "", "time_s": timeout, "tokens": 0, "error": "timeout"}
    except Exception as e:
        return {"output": "", "time_s": 0, "tokens": 0, "error": str(e)}


def run_benchmark(models: List[str]) -> Dict:
    results = {"models": {}, "summary": {}}

    for model_name in models:
        print(f"\n{'=' * 60}")
        print(f"MODEL: {model_name}")
        print(f"{'=' * 60}")
        model_results = []

        for task in TASKS:
            print(f"  Task: {task['name']} ({task['category']})...", end=" ")
            sys.stdout.flush()

            result = query_model(model_name, task["prompt"])
            if result.get("error"):
                print(f"ERROR: {result['error']}")
                model_results.append({
                    "task": task["name"],
                    "category": task["category"],
                    "success": False,
                    "error": result["error"],
                    "time_s": result["time_s"],
                    "tokens": 0,
                })
                continue

            # Evaluate
            eval_result = task["eval"](result["output"])
            print(f"{'PASS' if eval_result else 'FAIL'} ({result['time_s']}s, {result['tokens']} tok)")

            model_results.append({
                "task": task["name"],
                "category": task["category"],
                "success": eval_result,
                "time_s": result["time_s"],
                "tokens": result["tokens"],
                "output_snippet": result["output"][:200],
            })

        # Per-model summary
        passed = sum(1 for r in model_results if r["success"])
        total = len(model_results)
        avg_time = sum(r["time_s"] for r in model_results) / total if total > 0 else 0
        avg_tokens = sum(r["tokens"] for r in model_results) / total if total > 0 else 0

        results["models"][model_name] = {
            "results": model_results,
            "summary": {
                "passed": passed,
                "total": total,
                "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
                "avg_time_s": round(avg_time, 1),
                "avg_tokens": round(avg_tokens, 0),
            }
        }
        print(f"\n  >>> {model_name}: {passed}/{total} passed ({passed/total*100:.0f}%)")

    # Cross-model summary
    print(f"\n{'=' * 60}")
    print("CROSS-MODEL COMPARISON")
    print(f"{'=' * 60}")
    print(f"{'Model':30s} {'Pass Rate':12s} {'Avg Time':10s} {'Avg Tokens':10s}")
    print("-" * 62)
    for model_name in models:
        s = results["models"][model_name]["summary"]
        print(f"{model_name:30s} {s['pass_rate']:5.1f}%       {s['avg_time_s']:5.1f}s    {s['avg_tokens']:5.0f}")

    # Per-task comparison
    print(f"\n{'=' * 60}")
    print("PER-TASK COMPARISON")
    print(f"{'=' * 60}")
    for task in TASKS:
        print(f"\n{task['name']} ({task['category']}):")
        for model_name in models:
            for r in results["models"][model_name]["results"]:
                if r["task"] == task["name"]:
                    status = "PASS" if r["success"] else "FAIL"
                    print(f"  {model_name:30s} {status:4s} ({r['time_s']:5.1f}s)")

    # Save
    output_path = "lyme-output/sprint-weeks-53-72/capability-benchmark-results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    models = ["deepseek-coder:6.7b", "llama3:8b", "gpt-oss:20b"]
    run_benchmark(models)
