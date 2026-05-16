"""WEEK 57: Raw 7B vs Lyme-Enhanced 7B.

The core experiment: Does Lyme compression improve model performance?
Compares raw context vs compressed context on coding tasks.
"""

import sys, time, json, subprocess, tempfile, os, textwrap
from pathlib import Path
sys.path.insert(0, "src")

from lyme.compression.codebase_compressor import CodebaseCompressor

# A small, self-contained test repo for compression comparison
TEST_REPO_FILES = {
    "main.py": """
from auth import login, require_auth
from storage import save_file, load_file
from models import User

app = FastAPI()

@app.get("/users")
@require_auth
def list_users():
    users = load_file("users.json") or []
    return {"users": users}

@app.post("/users")
@require_auth
def create_user(data: dict):
    user = User.from_dict(data)
    users = load_file("users.json") or []
    users.append(user.to_dict())
    save_file("users.json", users)
    return {"status": "created", "user": user.to_dict()}
""",
    "auth.py": """
import hashlib, os

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    salt, h = hashed.split(":")
    return h == hashlib.sha256((salt + password).encode()).hexdigest()

def require_auth(func):
    def wrapper(request, *args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return {"error": "unauthorized"}, 401
        return func(request, *args, **kwargs)
    return wrapper

def login(username: str, password: str) -> dict:
    users = {"admin": hash_password("secret123"), "user": hash_password("password456")}
    if username in users and verify_password(password, users[username]):
        return {"token": "fake-jwt-" + username, "user": username}
    return {"error": "invalid credentials"}
""",
    "storage.py": """
import json, os

DATA_DIR = "data"

def save_file(filename: str, data: list | dict) -> bool:
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    return True

def load_file(filename: str) -> list | dict | None:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def delete_file(filename: str) -> bool:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
""",
    "models.py": """
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class User:
    username: str
    email: str
    role: str = "viewer"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def to_dict(self):
        return asdict(self)

    def has_permission(self, action: str) -> bool:
        permissions = {"admin": ["read", "write", "delete"], "viewer": ["read"]}
        return action in permissions.get(self.role, [])
""",
    "test_api.py": """
from main import app

def test_list_users():
    response = app.get("/users")
    assert response.status_code == 200

def test_create_user():
    response = app.post("/users", json={"username": "test", "email": "test@test.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "created"
""",
}

# Tasks to evaluate context understanding
TASKS = [
    {
        "name": "architecture",
        "question": "Describe the architecture of this project. What are the main modules and how do they relate?",
        "answer_keywords": ["auth", "storage", "models", "main", "API"],
        "detail_keywords": ["FastAPI", "User", "authentication", "JSON", "dataclass"],
    },
    {
        "name": "bug-finding",
        "question": "Find potential bugs or security issues in the auth module. List each with location and severity.",
        "answer_keywords": ["hardcoded", "password", "security", "hash"],
        "detail_keywords": ["MD5", "JWT", "fake", "plaintext"],
    },
    {
        "name": "extension",
        "question": "Explain how to add a DELETE /users/{id} endpoint. What files would need to change?",
        "answer_keywords": ["main.py", "auth", "storage", "delete", "route"],
        "detail_keywords": ["require_auth", "delete_file", "User"],
    },
    {
        "name": "test-generation",
        "question": "Write a test for the login function that verifies correct and incorrect credentials.",
        "answer_keywords": ["login", "test", "assert", "valid", "invalid"],
        "detail_keywords": ["password", "credentials", "401", "token"],
    },
]


def create_test_repo(temp_dir: Path):
    """Create the test repository from file definitions."""
    for name, content in TEST_REPO_FILES.items():
        filepath = temp_dir / name
        filepath.write_text(textwrap.dedent(content).strip() + "\n")
    return temp_dir


def build_raw_context(repo_path: Path) -> str:
    """Build a raw context by concatenating all file contents."""
    parts = ["Here is the full source code of the project:\n"]
    for name in sorted(TEST_REPO_FILES.keys()):
        content = (repo_path / name).read_text()
        parts.append(f"--- {name} ---\n{content}\n")
    return "\n".join(parts)


def build_compressed_context(repo_path: Path) -> str:
    """Build a compressed context using the Lyme compression pipeline."""
    compressor = CodebaseCompressor()
    result = compressor.compress(str(repo_path))

    parts = []
    parts.append("Here is a compressed representation of the project:\n")

    # L1: File tree
    l1 = result.layer1_tree
    parts.append("--- FILE TREE ---")
    if "tree" in l1:
        parts.append(json.dumps(l1["tree"], indent=2)[:500])
    elif "structure" in l1:
        parts.append(json.dumps(l1["structure"], indent=2)[:500])
    else:
        parts.append(str(l1)[:500])

    # L2: API surface
    l2 = result.layer2_apis
    parts.append("\n--- API SURFACE ---")
    if "modules" in l2:
        modules = l2["modules"]
        for mod in modules:
            mod_path = mod.get("path", mod.get("file", "unknown"))
            mod_funcs = mod.get("functions", [])
            mod_classes = mod.get("classes", [])
            parts.append(f"File: {mod_path}")
            for cls in mod_classes:
                parts.append(f"  Class: {cls.get('name', '?')}")
                for method in cls.get("methods", []):
                    parts.append(f"    Method: {method.get('name', '?')}")
            for func in mod_funcs:
                parts.append(f"  Function: {func.get('name', '?')}")
    else:
        parts.append(str(l2)[:500])

    # L3: Subsystems
    l3 = result.layer3_subsystems
    parts.append("\n--- SUBSYSTEMS ---")
    if "clusters" in l3:
        for cluster in l3["clusters"]:
            parts.append(f"Subsystem: {cluster.get('name', '?')}")
            parts.append(f"  Files: {', '.join(cluster.get('files', []))[:200]}")
    else:
        parts.append(str(l3)[:500])

    # L4: Invariants
    l4 = result.layer4_invariants
    parts.append("\n--- INVARIANTS ---")
    if "invariants" in l4:
        for inv in l4["invariants"][:10]:
            parts.append(f"  {inv.get('description', str(inv)[:100])}")
    else:
        parts.append(str(l4)[:500])

    return "\n".join(parts)


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


def evaluate_task(output: str, task: dict) -> dict:
    output_lower = output.lower()
    keyword_hits = sum(1 for kw in task["answer_keywords"] if kw.lower() in output_lower)
    detail_hits = sum(1 for kw in task["detail_keywords"] if kw.lower() in output_lower)
    total = len(task["answer_keywords"]) + len(task["detail_keywords"])
    hits = keyword_hits + detail_hits
    return {
        "keyword_score": round(keyword_hits / len(task["answer_keywords"]) * 100, 1),
        "detail_score": round(detail_hits / len(task["detail_keywords"]) * 100, 1),
        "combined_score": round(hits / total * 100, 1),
        "output_length": len(output),
    }


def run_experiment():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "testrepo"
        repo_path.mkdir()
        create_test_repo(repo_path)

        # Generate contexts
        print("Generating raw context...")
        raw_ctx = build_raw_context(repo_path)
        raw_tokens = len(raw_ctx.split())

        print("Generating compressed context...")
        compressed_ctx = build_compressed_context(repo_path)
        compressed_tokens = len(compressed_ctx.split())

        models = ["deepseek-coder:6.7b", "llama3:8b"]
        results = {"contexts": {"raw_tokens": raw_tokens, "compressed_tokens": compressed_tokens}, "runs": []}

        for model in models:
            print(f"\n{'=' * 60}")
            print(f"MODEL: {model}")
            print(f"{'=' * 60}")

            for task in TASKS:
                print(f"\n  Task: {task['name']}")

                # RAW condition
                print(f"    RAW ({raw_tokens} tok)...", end=" ")
                raw_prompt = f"{raw_ctx}\n\nQuestion: {task['question']}\nAnswer:"
                raw_result = query_model(model, raw_prompt)
                raw_eval = evaluate_task(raw_result["output"], task)

                # COMPRESSED condition
                print(f"COMPRESSED ({compressed_tokens} tok)...", end=" ")
                comp_prompt = f"{compressed_ctx}\n\nQuestion: {task['question']}\nAnswer:"
                comp_result = query_model(model, comp_prompt)
                comp_eval = evaluate_task(comp_result["output"], task)

                improvement = comp_eval["combined_score"] - raw_eval["combined_score"]
                print(f"Raw: {raw_eval['combined_score']:.0f}% → Comp: {comp_eval['combined_score']:.0f}% ({improvement:+.0f}%)")

                results["runs"].append({
                    "model": model,
                    "task": task["name"],
                    "raw": {"score": raw_eval, "time_s": raw_result["time_s"]},
                    "compressed": {"score": comp_eval, "time_s": comp_result["time_s"]},
                    "improvement_pct": round(improvement, 1),
                })

        # Summary
        print(f"\n{'=' * 60}")
        print("EXPERIMENT SUMMARY")
        print(f"{'=' * 60}")
        print(f"Context reduction: {raw_tokens} → {compressed_tokens} tokens ({(1-compressed_tokens/raw_tokens)*100:.0f}% reduction)")
        print()

        for model in models:
            model_runs = [r for r in results["runs"] if r["model"] == model]
            avg_raw = sum(r["raw"]["score"]["combined_score"] for r in model_runs) / len(model_runs)
            avg_comp = sum(r["compressed"]["score"]["combined_score"] for r in model_runs) / len(model_runs)
            print(f"{model}:")
            print(f"  Raw avg:       {avg_raw:.1f}%")
            print(f"  Compressed avg: {avg_comp:.1f}%")
            print(f"  Improvement:    {avg_comp - avg_raw:+.1f}%")
            print()

        output_path = "lyme-output/sprint-weeks-53-72/compression-experiment-results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_path}")


if __name__ == "__main__":
    run_experiment()
