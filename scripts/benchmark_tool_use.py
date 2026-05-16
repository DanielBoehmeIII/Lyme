"""WEEK 59: Tool Use as Model Amplification.

Tests whether tools help small models compensate for weaker reasoning.
Compares: model-only reasoning, naive tool access, Lyme-controlled tool access.
"""

import sys, time, json, subprocess, tempfile, os, textwrap, ast
from pathlib import Path
from typing import List, Dict
sys.path.insert(0, "src")

from lyme_model.tools.registry import ToolRegistry, CORE_TOOLS, MINIMAL_TOOLS
from lyme_model.tools.dispatch import ToolDispatcher

# Test project with hidden info that requires tool use to discover
TEST_FILES = {
    "src/main.py": """
from auth import login, verify_token
from db import get_user, save_user
from utils import validate_email

def handle_login(request):
    email = request.get("email")
    password = request.get("password")
    if not validate_email(email):
        return {"error": "invalid email"}, 400
    user = get_user(email)
    if not user:
        return {"error": "user not found"}, 404
    if not login(email, password):
        return {"error": "wrong password"}, 401
    token = verify_token(user)
    return {"token": token, "user": user}, 200

def handle_signup(request):
    email = request.get("email")
    password = request.get("password")
    if not validate_email(email):
        return {"error": "invalid email"}, 400
    existing = get_user(email)
    if existing:
        return {"error": "user exists"}, 409
    user = save_user(email, password)
    token = verify_token(user)
    return {"token": token, "user": user}, 201
""",
    "src/auth.py": """
import hashlib, os, jwt

SECRET_KEY = "dev-secret-key-do-not-use-in-production"

def hash_password(password):
    salt = os.urandom(16).hex()
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(password, hashed):
    salt, h = hashed.split(":")
    return h == hashlib.sha256((salt + password).encode()).hexdigest()

def login(email, password):
    # This is intentionally simplified
    return password == "password123"

def verify_token(user):
    return jwt.encode({"user_id": user["id"]}, SECRET_KEY, algorithm="HS256")
""",
    "src/db.py": """
import json, os

DB_PATH = "data/users.json"

def get_user(email):
    if not os.path.exists(DB_PATH):
        return None
    with open(DB_PATH) as f:
        users = json.load(f)
    return users.get(email)

def save_user(email, password):
    hashed = __import__('auth', fromlist=['hash_password']).hash_password(password)
    user = {"id": len(email), "email": email, "password": hashed}
    if os.path.exists(DB_PATH):
        with open(DB_PATH) as f:
            users = json.load(f)
    else:
        users = {}
    users[email] = user
    os.makedirs("data", exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(users, f)
    return user
""",
    "src/utils.py": """
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_input(text):
    return text.strip()

def format_response(data, status=200):
    return {"data": data, "status": status}
""",
}

# Tasks that require tool use to answer correctly
TASKS = [
    {
        "name": "find-bug",
        "question": (
            "Find potential security issues in the 'login' function. "
            "Check what it actually does vs what it should do. "
            "Look at the implementation carefully."
        ),
        "expected_findings": [
            "password123",  # hardcoded password check
            "dev-secret-key",  # exposed secret
            "hash_password",  # password hashing exists but login doesn't use it
        ],
        "requires_tool": True,
    },
    {
        "name": "trace-flow",
        "question": (
            "Trace the full flow of a login request. "
            "What files are involved? What functions are called in order? "
            "List the call chain from handle_login to every function it calls."
        ),
        "expected_findings": [
            "auth.py", "db.py", "utils.py", "validate_email",
            "handle_login", "login", "get_user", "verify_token",
        ],
        "requires_tool": True,
    },
    {
        "name": "db-schema",
        "question": (
            "How is user data stored? What fields does a user record have? "
            "Where is the database file located? Is the storage approach safe?"
        ),
        "expected_findings": [
            "id", "email", "password", "JSON", "users.json",
            "plaintext", "hash",
        ],
        "requires_tool": True,
    },
]


def create_test_project(temp_dir: Path):
    repo = temp_dir / "testproject"
    for name, content in TEST_FILES.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n")
    return repo


def query_model(model_name: str, prompt: str, timeout: int = 90) -> dict:
    try:
        start = time.time()
        proc = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        return {"output": proc.stdout.strip(), "time_s": round(elapsed, 2)}
    except subprocess.TimeoutExpired:
        return {"output": "", "time_s": timeout, "error": "timeout"}
    except Exception as e:
        return {"output": "", "time_s": 0, "error": str(e)}


def evaluate_detailed(output: str, expected: list) -> dict:
    ol = output.lower()
    hits = sum(1 for kw in expected if kw.lower() in ol)
    return {"hit_count": hits, "total": len(expected), "score": round(hits / len(expected) * 100, 1)}


def build_naive_tool_prompt() -> str:
    """Full tool descriptions for naive access."""
    reg = ToolRegistry(CORE_TOOLS)
    return reg.prompt_for_model("7b")


def build_lyme_tool_prompt(task_type: str) -> str:
    """Minimal tool descriptions for Lyme-controlled access."""
    reg = ToolRegistry(MINIMAL_TOOLS)
    tools_for_task = {
        "find-bug": ["grep_search", "read_file", "think"],
        "trace-flow": ["read_file", "grep_search", "think"],
        "db-schema": ["read_file", "grep_search", "think"],
    }
    tool_names = tools_for_task.get(task_type, ["read_file", "grep_search", "think"])
    lines = ["Available tools (use when you need them):", ""]
    for name in tool_names:
        t = reg.get(name)
        if t:
            lines.append(t.to_prompt())
    lines.append("")
    lines.append('Use format: TOOL: name(param=value)')
    return "\n".join(lines)


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_project(Path(tmpdir))
        model_name = "deepseek-coder:6.7b"
        results = {"runs": []}

        # Read all files once for model-only and naive conditions
        all_files_content = ""
        for name, content in sorted(TEST_FILES.items()):
            all_files_content += f"--- {name} ---\n{content}\n"

        print("=" * 60)
        print("TOOL USE AMPLIFICATION EXPERIMENT (Week 59)")
        print("=" * 60)
        print(f"Model: {model_name}")
        print(f"Project: {len(TEST_FILES)} files")
        print()

        for task in TASKS:
            print(f"\n--- {task['name']} ---")

            # Condition 1: Model-only reasoning
            prompt = (
                f"Here is the complete codebase:\n\n{all_files_content}\n\n"
                f"Task: {task['question']}\n\n"
                "Answer based on your analysis of the code. Be specific."
            )
            result = query_model(model_name, prompt)
            eval_result = evaluate_detailed(result["output"], task["expected_findings"])
            cond1_status = "OK" if eval_result["score"] >= 50 else "WEAK"
            print(f"  Model-only     : {eval_result['score']:5.1f}% ({result['time_s']:5.1f}s) [{cond1_status}]")
            results["runs"].append({
                "task": task["name"], "condition": "model_only",
                "score": eval_result["score"], "time_s": result["time_s"],
                "hits": eval_result["hit_count"], "total": eval_result["total"],
            })

            # Condition 2: Naive tool access (all 10 tools)
            naive_tools = build_naive_tool_prompt()
            prompt = (
                f"Project structure:\n"
                f"  src/main.py, src/auth.py, src/db.py, src/utils.py\n\n"
                f"You have access to tools. Use them to investigate the codebase.\n\n"
                f"{naive_tools}\n\n"
                f"Task: {task['question']}\n\n"
                "Use tools to investigate, then provide your answer."
            )
            result = query_model(model_name, prompt)
            eval_result = evaluate_detailed(result["output"], task["expected_findings"])
            print(f"  Naive tools     : {eval_result['score']:5.1f}% ({result['time_s']:5.1f}s)")
            results["runs"].append({
                "task": task["name"], "condition": "naive_tools",
                "score": eval_result["score"], "time_s": result["time_s"],
                "hits": eval_result["hit_count"], "total": eval_result["total"],
            })

            # Condition 3: Lyme-controlled tools (minimal set)
            lyme_tools = build_lyme_tool_prompt(task["name"])
            prompt = (
                f"Project: testproject\n"
                f"  Files: src/main.py, src/auth.py, src/db.py, src/utils.py\n\n"
                f"{lyme_tools}\n\n"
                f"Task: {task['question']}\n\n"
                "Use tools to investigate, then provide your answer."
            )
            result = query_model(model_name, prompt)
            eval_result = evaluate_detailed(result["output"], task["expected_findings"])
            print(f"  Lyme tools      : {eval_result['score']:5.1f}% ({result['time_s']:5.1f}s)")
            results["runs"].append({
                "task": task["name"], "condition": "lyme_tools",
                "score": eval_result["score"], "time_s": result["time_s"],
                "hits": eval_result["hit_count"], "total": eval_result["total"],
            })

        # Summary
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        for cond in ["model_only", "naive_tools", "lyme_tools"]:
            runs = [r for r in results["runs"] if r["condition"] == cond]
            avg_score = sum(r["score"] for r in runs) / len(runs)
            avg_time = sum(r["time_s"] for r in runs) / len(runs)
            names = {"model_only": "Model Only", "naive_tools": "Naive Tools", "lyme_tools": "Lyme Tools"}
            print(f"  {names[cond]:15s}: avg {avg_score:5.1f}%  avg time {avg_time:5.1f}s")

        conds = ["model_only", "naive_tools", "lyme_tools"]
        print(f"\n  Best condition per task:")
        bests = {}
        for task in TASKS:
            task_runs = [r for r in results["runs"] if r["task"] == task["name"]]
            best = max(task_runs, key=lambda r: r["score"])
            bests[task["name"]] = best["condition"]
            print(f"    {task['name']:15s}: {best['condition']} ({best['score']:.0f}%)")

        outpath = "lyme-output/sprint-weeks-53-72/tool-amplification-results.json"
        with open(outpath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {outpath}")


if __name__ == "__main__":
    main()
